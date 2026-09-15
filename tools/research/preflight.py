#!/usr/bin/env python3
"""Fail-closed preflight for expensive Go2 research runs.

The tool checks execution integrity, not scientific merit. The current task/SOP
owns scientific variables and classifications.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


DEFAULT_PROCESS_NAMES = ("unitree_mujoco", "real_trot_go2", "run_trot.sh")
LINUX_SAFE_DOMAIN_RANGES = ((0, 101), (215, 232))
REVIEW_SURFACES = {"runtime", "runner", "logger", "schema", "scene", "analyzer"}


def command(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def shell_command(text: str, cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["bash", "-lc", text],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    detail: Any,
    *,
    severity: str = "hard",
) -> None:
    checks.append(
        {
            "name": name,
            "status": "PASS" if passed else ("WARN" if severity == "warn" else "FAIL"),
            "severity": severity,
            "detail": detail,
        }
    )


def dds_ports(domain: int, participant: int = 0) -> dict[str, int]:
    # DDSI-RTPS well-known UDP port mapping used by CycloneDDS/ROS 2 defaults.
    pb, dg, pg = 7400, 250, 2
    return {
        "discovery_multicast": pb + dg * domain,
        "user_multicast": pb + dg * domain + 1,
        "discovery_unicast": pb + dg * domain + 10 + pg * participant,
        "user_unicast": pb + dg * domain + 11 + pg * participant,
    }


def domain_in_linux_safe_pool(domain: int) -> bool:
    return any(lo <= domain <= hi for lo, hi in LINUX_SAFE_DOMAIN_RANGES)


def read_ephemeral_range() -> tuple[int, int] | None:
    path = Path("/proc/sys/net/ipv4/ip_local_port_range")
    try:
        lo, hi = (int(value) for value in path.read_text().split()[:2])
        return lo, hi
    except (OSError, ValueError):
        return None


def runner_domains(text: str) -> list[int]:
    values: list[int] = []
    for line in text.splitlines():
        code = line.split("#", 1)[0]
        values.extend(
            int(value)
            for value in re.findall(r"--domain-id(?:\s+|=)([0-9]+)", code)
        )
    return values


def parent_pid(pid: int) -> int | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split()
        return int(fields[3]) if len(fields) > 3 else None
    except (OSError, ValueError):
        return None


def ancestor_pids(pid: int) -> set[int]:
    ancestors: set[int] = set()
    current = parent_pid(pid)
    while current and current > 1 and current not in ancestors:
        ancestors.add(current)
        current = parent_pid(current)
    return ancestors


def process_argv_matches(argv: list[str], names: tuple[str, ...]) -> list[str]:
    # Match executable/script basenames, not arbitrary substrings. This avoids
    # flagging the shell that invoked preflight just because a path appears in
    # its argument string.
    basenames = {Path(token).name for token in argv[:4] if token}
    return [name for name in names if name in basenames]


def find_processes(names: tuple[str, ...]) -> list[dict[str, Any]]:
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return []
    own_pid = os.getpid()
    excluded = {own_pid} | ancestor_pids(own_pid)
    found: list[dict[str, Any]] = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in excluded:
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        argv = [
            token.decode("utf-8", errors="replace")
            for token in raw.split(b"\0")
            if token
        ]
        if not argv:
            continue
        matches = process_argv_matches(argv, names)
        if matches:
            found.append({"pid": pid, "matches": matches, "argv": argv[:8]})
    return found


def domain_lock_free(domain: int) -> tuple[bool, str]:
    path = Path(f"/tmp/unitree_mujoco_run_trot_domain_{domain}.lock")
    handle = path.open("a+")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False, str(path)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True, str(path)
    finally:
        handle.close()


def parse_hash_requirement(raw: str, repo: Path) -> tuple[Path, str]:
    if "=" not in raw:
        raise ValueError(f"hash requirement must be PATH=SHA256, got: {raw}")
    left, expected = raw.rsplit("=", 1)
    path = Path(left)
    if not path.is_absolute():
        path = repo / path
    return path.resolve(), expected.lower()


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-head", help="optional exact task/prepared HEAD")
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--domain", type=int, required=True)
    parser.add_argument(
        "--dds-policy",
        choices=("linux-safe", "spec-only"),
        default="linux-safe",
        help="linux-safe also avoids the standard Linux ephemeral-port region",
    )
    parser.add_argument("--baseline-runner", type=Path)
    parser.add_argument(
        "--changed-surface",
        action="append",
        choices=tuple(sorted(REVIEW_SURFACES)),
        default=[],
        help="repeat for execution surfaces changed since the accepted baseline",
    )
    parser.add_argument("--requires-sol-review", action="store_true")
    parser.add_argument("--approved-head", help="exact HEAD approved by Sol for live")
    parser.add_argument("--require-file", action="append", default=[])
    parser.add_argument("--hash", dest="hash_requirements", action="append", default=[])
    parser.add_argument("--test", action="append", default=[], help="no-live/build test command; repeatable")
    parser.add_argument("--process-name", action="append", default=[])
    parser.add_argument("--output", type=Path, help="JSON report; use stdout or an ignored/out-of-repo path for final arming")
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    runner = (args.runner if args.runner.is_absolute() else repo / args.runner).resolve()
    run_dir = (args.run_dir if args.run_dir.is_absolute() else repo / args.run_dir).resolve()
    baseline_runner = None
    if args.baseline_runner:
        baseline_runner = (
            args.baseline_runner
            if args.baseline_runner.is_absolute()
            else repo / args.baseline_runner
        ).resolve()

    checks: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "schema_version": 1,
        "experiment_id": args.experiment_id,
        "repo_root": str(repo),
        "checks": checks,
        "changed_surfaces": sorted(set(args.changed_surface)),
    }

    git_rc, head, git_err = command(["git", "rev-parse", "HEAD"], repo)
    branch_rc, branch, branch_err = command(["git", "branch", "--show-current"], repo)
    status_rc, status, status_err = command(["git", "status", "--porcelain"], repo)
    add_check(checks, "git_head_readable", git_rc == 0, head if git_rc == 0 else git_err)
    add_check(
        checks,
        "expected_branch",
        branch_rc == 0 and branch == args.expected_branch,
        {"actual": branch, "expected": args.expected_branch, "stderr": branch_err},
    )
    if args.expected_head:
        add_check(
            checks,
            "expected_head",
            git_rc == 0 and head == args.expected_head,
            {"actual": head, "expected": args.expected_head},
        )
    add_check(checks, "worktree_clean", status_rc == 0 and status == "", status if status else status_err)
    report["git"] = {"head": head, "branch": branch, "clean": status_rc == 0 and status == ""}

    runner_exists = runner.is_file()
    add_check(checks, "runner_exists", runner_exists, str(runner))
    runner_text = ""
    if runner_exists:
        runner_text = runner.read_text(encoding="utf-8", errors="replace")
        syntax_rc, _, syntax_err = command(["bash", "-n", str(runner)], repo)
        add_check(checks, "runner_bash_syntax", syntax_rc == 0, syntax_err or "bash -n PASS")
        domains = runner_domains(runner_text)
        add_check(
            checks,
            "runner_domain_matches",
            domains == [args.domain],
            {"runner_domains": domains, "expected": args.domain},
        )
    else:
        add_check(checks, "runner_bash_syntax", False, "runner missing")
        add_check(checks, "runner_domain_matches", False, "runner missing")

    in_spec_range = 0 <= args.domain <= 232
    ports = dds_ports(args.domain) if args.domain >= 0 else {}
    ports_legal = bool(ports) and all(0 <= value <= 65535 for value in ports.values())
    add_check(checks, "dds_domain_spec_range", in_spec_range, {"domain": args.domain, "allowed": [0, 232]})
    add_check(checks, "dds_rtps_ports_legal", ports_legal, ports)
    if args.dds_policy == "linux-safe":
        add_check(
            checks,
            "dds_linux_safe_pool",
            domain_in_linux_safe_pool(args.domain),
            {"domain": args.domain, "allowed_ranges": list(LINUX_SAFE_DOMAIN_RANGES)},
        )
    ephemeral = read_ephemeral_range()
    if ephemeral and ports:
        lo, hi = ephemeral
        overlap = {name: port for name, port in ports.items() if lo <= port <= hi}
        add_check(
            checks,
            "dds_ephemeral_port_overlap",
            not overlap,
            {"ephemeral_range": [lo, hi], "overlap": overlap},
            severity="hard" if args.dds_policy == "linux-safe" else "warn",
        )
    else:
        add_check(
            checks,
            "dds_ephemeral_port_range_readable",
            ephemeral is not None,
            ephemeral or "unavailable",
            severity="warn",
        )

    lock_ok, lock_path = domain_lock_free(args.domain)
    add_check(checks, "dds_domain_lock_free", lock_ok, lock_path)
    add_check(checks, "run_directory_fresh", not run_dir.exists(), str(run_dir))

    names = tuple(args.process_name) if args.process_name else DEFAULT_PROCESS_NAMES
    processes = find_processes(names)
    add_check(checks, "no_stale_runtime_process", not processes, processes)

    for raw in args.require_file:
        path = Path(raw)
        if not path.is_absolute():
            path = repo / path
        add_check(checks, f"required_file:{raw}", path.is_file(), str(path.resolve()))

    for raw in args.hash_requirements:
        try:
            path, expected = parse_hash_requirement(raw, repo)
            actual = sha256(path) if path.is_file() else "MISSING"
            add_check(
                checks,
                f"hash:{path}",
                actual == expected,
                {"actual": actual, "expected": expected},
            )
        except ValueError as exc:
            add_check(checks, f"hash:{raw}", False, str(exc))

    runner_diff = ""
    if baseline_runner is not None:
        if baseline_runner.is_file() and runner.is_file():
            diff_rc, diff_out, diff_err = command(
                ["git", "diff", "--no-index", "--", str(baseline_runner), str(runner)],
                repo,
            )
            # git diff --no-index returns 1 when files differ, 0 when identical.
            diff_valid = diff_rc in (0, 1)
            runner_diff = diff_out
            add_check(
                checks,
                "baseline_runner_diff_generated",
                diff_valid,
                diff_err or ("identical" if diff_rc == 0 else "different; diff recorded"),
            )
        else:
            add_check(
                checks,
                "baseline_runner_diff_generated",
                False,
                {"baseline": str(baseline_runner), "runner": str(runner)},
            )
    report["runner_diff"] = runner_diff

    test_results: list[dict[str, Any]] = []
    for index, test in enumerate(args.test, start=1):
        rc, stdout, stderr = shell_command(test, repo)
        result = {
            "index": index,
            "command": test,
            "return_code": rc,
            "stdout": stdout,
            "stderr": stderr,
        }
        test_results.append(result)
        add_check(checks, f"test_{index}", rc == 0, result)
    report["tests"] = test_results

    changed = set(args.changed_surface)
    if changed:
        add_check(
            checks,
            "changed_surface_has_no_live_test",
            bool(args.test),
            {"changed_surfaces": sorted(changed), "test_count": len(args.test)},
        )

    runner_changed = bool(runner_diff)
    review_required = bool(args.requires_sol_review or changed or runner_changed)
    report["sol_review"] = {
        "required": review_required,
        "approved_head": args.approved_head,
        "current_head": head,
        "triggered_by_runner_diff": runner_changed,
    }
    if review_required:
        add_check(
            checks,
            "sol_review_exact_head",
            bool(args.approved_head) and git_rc == 0 and args.approved_head == head,
            {"approved_head": args.approved_head, "current_head": head},
        )
    else:
        add_check(
            checks,
            "sol_review_exact_head",
            True,
            "not required for this frozen execution surface",
        )

    output: Path | None = None
    if args.output:
        output = (args.output if args.output.is_absolute() else repo / args.output).resolve()
        if inside(output, repo):
            rel = output.relative_to(repo)
            ignore_rc, _, _ = command(["git", "check-ignore", "-q", "--", str(rel)], repo)
            add_check(
                checks,
                "output_preserves_clean_worktree",
                ignore_rc == 0,
                {"output": str(output), "inside_repo": True, "gitignored": ignore_rc == 0},
            )
        else:
            add_check(
                checks,
                "output_preserves_clean_worktree",
                True,
                {"output": str(output), "inside_repo": False},
            )

    hard_failures = [
        item for item in checks if item["severity"] == "hard" and item["status"] == "FAIL"
    ]
    warnings = [item for item in checks if item["status"] == "WARN"]
    report["pass"] = not hard_failures
    report["hard_failure_count"] = len(hard_failures)
    report["warning_count"] = len(warnings)

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
