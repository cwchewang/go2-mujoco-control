#!/usr/bin/env python3
"""Run the frozen shared-transfer campaign from qualification through verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[3]
VENV_PYTHON = ROOT / ".substrate/venv-reliable/bin/python"
TASK = ROOT / "tools/substrate/tasks/rl_shared_transfer_combination_v1.json"
PROTOCOL = ROOT / "tools/substrate/protocols/rl_shared_transfer_combination_v1.json"
REVIEW_RE = {
    "reviewer": re.compile(r"^Reviewer identity:\s*`([^`]+)`\s*$", re.MULTILINE),
    "head": re.compile(r"^Target HEAD:\s*`([0-9a-f]{40})`\s*$", re.MULTILINE),
    "verdict": re.compile(r"^Verdict:\s*`(APPROVED|VETO)`\s*$", re.MULTILINE),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(argv: list[str], *, log_root: Path, name: str, env: dict[str, str]) -> str:
    completed = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    (log_root / f"{name}.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (log_root / f"{name}.stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"{name} failed with exit code {completed.returncode}")
    return completed.stdout


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_review(remote_branch: str, path: str, expected_head: str) -> dict[str, str]:
    ref = f"origin/{remote_branch}"
    commit = git("rev-parse", ref)
    text = subprocess.check_output(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT, text=True
    )
    values: dict[str, str] = {}
    for key, pattern in REVIEW_RE.items():
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"{key} missing from review {remote_branch}")
        values[key] = match.group(1)
    if values["head"] != expected_head:
        raise RuntimeError(f"review {remote_branch} targets another HEAD")
    if values["verdict"] != "APPROVED":
        raise RuntimeError(f"review {remote_branch} vetoed execution")
    return {
        "reviewer": values["reviewer"],
        "verdict": "APPROVED",
        "evidence": f"{remote_branch}@{commit}:{path}",
        "commit": commit,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-id", required=True, type=int)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--science-ref", required=True)
    parser.add_argument("--science-path", required=True)
    parser.add_argument("--execution-ref", required=True)
    parser.add_argument("--execution-path", required=True)
    parser.add_argument("--user-instruction", required=True)
    args = parser.parse_args()

    run_root = (ROOT / args.run_dir).resolve()
    if not run_root.is_relative_to((ROOT / "example/cpp/experiments/_runs").resolve()):
        raise RuntimeError("run directory is outside the approved raw evidence root")
    if run_root.exists():
        raise RuntimeError("formal run directory already exists")
    run_root.mkdir(parents=True)

    if not VENV_PYTHON.is_file():
        raise RuntimeError("reliable substrate Python is unavailable")
    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    task = json.loads(TASK.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if task["branch"] != branch:
        raise RuntimeError("tracked task branch does not match current branch")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked worktree is dirty before formal execution")

    science = load_review(args.science_ref, args.science_path, head)
    execution = load_review(args.execution_ref, args.execution_path, head)
    if science["reviewer"] == execution["reviewer"]:
        raise RuntimeError("science and execution reviewers must differ")
    review_json = {
        "head": head,
        "science": {
            "reviewer": science["reviewer"],
            "verdict": "APPROVED",
            "evidence": science["evidence"],
        },
        "execution": {
            "reviewer": execution["reviewer"],
            "verdict": "APPROVED",
            "evidence": execution["evidence"],
        },
    }
    review_path = run_root / "review.json"
    review_path.write_text(
        json.dumps(review_json, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    child_env = dict(os.environ)
    child_env.pop("PYTHONPATH", None)
    child_env["PYTHONNOUSERSITE"] = "1"
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"

    mujoco_root = Path.home() / ".mujoco/mujoco-3.3.6"
    if not (mujoco_root / "include/mujoco/mujoco.h").is_file():
        raise RuntimeError("trusted MuJoCo 3.3.6 SDK is unavailable")
    run(
        [
            "cmake",
            "-S",
            "example/cpp",
            "-B",
            ".substrate/controller-reliable",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DGO2_MUJOCO_ROOT={mujoco_root}",
        ],
        log_root=run_root,
        name="controller_cache",
        env=child_env,
    )

    qualification = run_root / "qualification"
    run(
        [
            str(VENV_PYTHON),
            "-m",
            "tools.substrate.qualify",
            "--output",
            str(qualification),
        ],
        log_root=run_root,
        name="qualification",
        env=child_env,
    )

    prepared = run_root / "prepared"
    run(
        [
            str(VENV_PYTHON),
            "-m",
            "tools.substrate.baseline",
            "prepare",
            "--task",
            str(TASK),
            "--review",
            str(review_path),
            "--qualification",
            str(qualification),
            "--output",
            str(prepared),
        ],
        log_root=run_root,
        name="prepare",
        env=child_env,
    )
    prepared_manifest = sha256(prepared / "manifest.json")

    authorization = {
        "action": "START_FORMAL_CAPTURE",
        "head": head,
        "protocol_sha256": sha256(PROTOCOL),
        "prepared_manifest_sha256": prepared_manifest,
        "max_attempts": protocol["max_attempts"],
        "authorized_by": "user",
        "user_instruction": args.user_instruction,
    }
    authorization_path = run_root / "authorization.json"
    authorization_path.write_text(
        json.dumps(authorization, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    capture = run_root / "capture"
    run(
        [
            str(VENV_PYTHON),
            "-m",
            "tools.substrate.baseline",
            "capture",
            "--task",
            str(TASK),
            "--prepared",
            str(prepared),
            "--authorization",
            str(authorization_path),
            "--output",
            str(capture),
        ],
        log_root=run_root,
        name="capture",
        env=child_env,
    )

    verification = run_root / "verification"
    run(
        [
            str(VENV_PYTHON),
            "-m",
            "tools.substrate.baseline",
            "verify",
            "--capture",
            str(capture),
            "--prepared",
            str(prepared),
            "--output",
            str(verification),
        ],
        log_root=run_root,
        name="verification",
        env=child_env,
    )

    ledger = ROOT / "_runs/substrate_attempts" / protocol["id"]
    if not ledger.is_dir():
        raise RuntimeError("campaign ledger is missing after capture")
    ledger_archive = run_root / "ledger"
    shutil.copytree(ledger, ledger_archive)

    verification_manifest = json.loads(
        (verification / "manifest.json").read_text(encoding="utf-8")
    )
    capture_manifest = json.loads(
        (capture / "manifest.json").read_text(encoding="utf-8")
    )
    summary = {
        "schema": 1,
        "head": head,
        "branch": branch,
        "domain_id": args.domain_id,
        "science_review": science,
        "execution_review": execution,
        "authorization": authorization,
        "qualification_manifest_sha256": sha256(qualification / "manifest.json"),
        "prepared_manifest_sha256": prepared_manifest,
        "capture_manifest_sha256": sha256(capture / "manifest.json"),
        "verification_manifest_sha256": sha256(verification / "manifest.json"),
        "capture_status": capture_manifest.get("status"),
        "capability_status": capture_manifest.get("capability_status"),
        "attempts": capture_manifest.get("attempts"),
        "live_runs": capture_manifest.get("live_runs"),
        "verification": verification_manifest.get("verification"),
        "verification_consumed": verification_manifest.get("consumed"),
        "external_ledger_checked": verification_manifest.get("external_ledger_checked"),
    }
    (run_root / "formal-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
