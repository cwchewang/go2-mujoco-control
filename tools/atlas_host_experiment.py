#!/usr/bin/env python3
"""Execute one frozen host experiment outside the Codex/Luna sandbox."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_RE = re.compile(
    r"<!--\s*ATLAS_HOST_EXPERIMENT\s*(\{.*?\})\s*ATLAS_HOST_EXPERIMENT\s*-->",
    re.DOTALL,
)
RUN_PREFIX = Path("example/cpp/experiments/_runs")
ALLOWED_SCRIPT_PREFIXES = (
    Path("example/cpp/scripts"),
    Path("example/cpp/tools"),
)
ALLOWED_DIRECT_PREFIXES = (
    Path("example/cpp/build"),
    Path("simulate/build"),
)
SECRET_KEY_FRAGMENTS = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
ENV_PREFIXES = ("TROT_", "CYCLONEDDS_", "MUJOCO_", "UNITREE_")
ENV_EXACT = {"LD_LIBRARY_PATH"}


class HostExperimentError(ValueError):
    """A frozen host experiment manifest or execution request is invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_relative(value: str, *, field: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise HostExperimentError(f"{field} must be a normalized relative path")
    normalized = Path(*path.parts)
    if str(normalized) != value.rstrip("/"):
        raise HostExperimentError(f"{field} must be normalized")
    return normalized


def _under(path: Path, prefix: Path) -> bool:
    try:
        path.relative_to(prefix)
        return True
    except ValueError:
        return False


def extract_manifest(task_text: str) -> dict[str, Any] | None:
    matches = MANIFEST_RE.findall(task_text)
    if not matches:
        return None
    if len(matches) != 1:
        raise HostExperimentError("task must contain at most one ATLAS_HOST_EXPERIMENT block")
    try:
        manifest = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise HostExperimentError(f"host manifest JSON is invalid: {exc.msg}") from exc
    if not isinstance(manifest, dict):
        raise HostExperimentError("host manifest must be a JSON object")
    return validate_manifest(manifest)


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "command",
        "domain_id",
        "run_dir",
        "timeout_s",
        "environment",
    }
    unknown = sorted(set(manifest) - allowed)
    if unknown:
        raise HostExperimentError(f"unsupported host manifest fields: {', '.join(unknown)}")
    if manifest.get("schema_version") != 1:
        raise HostExperimentError("host manifest schema_version must be 1")

    command = manifest.get("command")
    if (
        not isinstance(command, list)
        or len(command) < 2
        or not all(isinstance(item, str) and item for item in command)
    ):
        raise HostExperimentError("command must be an argv array with at least two strings")
    if any("\x00" in item for item in command):
        raise HostExperimentError("command contains NUL")

    executable = command[0]
    if executable in {"bash", "python3"}:
        if command[1].startswith("-"):
            raise HostExperimentError("shell/interpreter options are not allowed before the runner path")
        runner = _normalized_relative(command[1], field="command runner")
        if not any(_under(runner, prefix) for prefix in ALLOWED_SCRIPT_PREFIXES):
            raise HostExperimentError("runner must live under example/cpp/scripts or example/cpp/tools")
    else:
        direct = _normalized_relative(executable, field="command executable")
        if not any(_under(direct, prefix) for prefix in ALLOWED_DIRECT_PREFIXES):
            raise HostExperimentError("direct executable must live under an approved build directory")

    domain_id = manifest.get("domain_id")
    if not isinstance(domain_id, int) or isinstance(domain_id, bool) or not (0 <= domain_id <= 232):
        raise HostExperimentError("domain_id must be an integer in [0, 232]")
    if "--domain-id" not in command:
        raise HostExperimentError("command must carry the explicit --domain-id from the manifest")
    domain_index = command.index("--domain-id")
    if domain_index + 1 >= len(command) or command[domain_index + 1] != str(domain_id):
        raise HostExperimentError("command --domain-id does not match manifest domain_id")

    run_dir = _normalized_relative(str(manifest.get("run_dir", "")), field="run_dir")
    if not _under(run_dir, RUN_PREFIX):
        raise HostExperimentError("run_dir must live under example/cpp/experiments/_runs")

    if executable in {"bash", "python3"} and runner.name in {
        "run_trot.sh",
        "run_trot_exact_source.sh",
    }:
        if len(command) < 4:
            raise HostExperimentError(
                "Go2 trot runner command must include timeout and experiment path"
            )
        experiment_arg = _normalized_relative(
            command[3], field="command experiment path"
        )
        if _under(experiment_arg, RUN_PREFIX):
            expected_run_dir = experiment_arg
        elif _under(experiment_arg, Path("_runs")):
            expected_run_dir = Path("example/cpp/experiments") / experiment_arg
        else:
            expected_run_dir = RUN_PREFIX / experiment_arg
        if expected_run_dir != run_dir:
            raise HostExperimentError(
                "command experiment path does not resolve to manifest run_dir"
            )

    timeout_s = manifest.get("timeout_s", 1800)
    if not isinstance(timeout_s, int) or isinstance(timeout_s, bool) or not (1 <= timeout_s <= 7200):
        raise HostExperimentError("timeout_s must be an integer in [1, 7200]")

    environment = manifest.get("environment", {})
    if not isinstance(environment, dict):
        raise HostExperimentError("environment must be an object")
    clean_env: dict[str, str] = {}
    for key, value in environment.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise HostExperimentError("environment keys and values must be strings")
        upper = key.upper()
        if any(fragment in upper for fragment in SECRET_KEY_FRAGMENTS):
            raise HostExperimentError(f"secret-bearing environment key is not allowed: {key}")
        if key not in ENV_EXACT and not key.startswith(ENV_PREFIXES):
            raise HostExperimentError(f"unsupported host environment key: {key}")
        clean_env[key] = value

    return {
        "schema_version": 1,
        "command": list(command),
        "domain_id": domain_id,
        "run_dir": str(run_dir),
        "timeout_s": timeout_s,
        "environment": clean_env,
    }


def load_manifest_from_task_commit(
    repo: Path,
    task_commit: str,
    task_path: str,
) -> dict[str, Any] | None:
    completed = subprocess.run(
        ["git", "show", f"{task_commit}:{task_path}"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise HostExperimentError("cannot read frozen task document from task commit")
    return extract_manifest(completed.stdout)


def snapshot_tree(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            records.append({"path": relative, "type": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            records.append(
                {
                    "path": relative,
                    "type": "file",
                    "size": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )
    return records


def verify_snapshot(root: Path, expected: list[dict[str, Any]]) -> bool:
    return snapshot_tree(root) == expected


def _sanitized_host_env(overrides: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ACTIONS_RUNTIME_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_URL",
    ):
        env.pop(key, None)
    env.update(overrides)
    return env


def execute_manifest(
    *,
    repo: Path,
    worktree: Path,
    task_commit: str,
    candidate_commit: str,
    task_path: str,
    manifest: dict[str, Any],
    output_dir: Path,
    approval_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = validate_manifest(manifest)
    output_dir.mkdir(parents=True, exist_ok=True)

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != candidate_commit:
        raise HostExperimentError("candidate worktree HEAD does not match candidate_commit")
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        raise HostExperimentError("candidate worktree has tracked changes before host execution")

    run_dir_rel = Path(manifest["run_dir"])
    run_dir = worktree / run_dir_rel
    if run_dir.exists():
        raise HostExperimentError("host run_dir already exists")

    command = list(manifest["command"])
    runner_path = command[1] if command[0] in {"bash", "python3"} else command[0]
    if not (worktree / runner_path).exists():
        raise HostExperimentError(f"host runner/executable is missing: {runner_path}")

    stdout_path = output_dir / "host-experiment.stdout.log"
    stderr_path = output_dir / "host-experiment.stderr.log"
    lock_path = Path("/tmp/go2_mujoco_experiment.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    record: dict[str, Any] = {
        "schema_version": 1,
        "task_commit": task_commit,
        "task_path": task_path,
        "candidate_commit": candidate_commit,
        "manifest_sha256": _sha256_bytes(
            (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ),
        "command": command,
        "domain_id": manifest["domain_id"],
        "run_dir": manifest["run_dir"],
        "timeout_s": manifest["timeout_s"],
        "environment": manifest["environment"],
        "approval_receipt": approval_receipt,
        "started_at": None,
        "finished_at": None,
        "launched": False,
        "timed_out": False,
        "returncode": None,
        "error": None,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "stdout_sha256": None,
        "stderr_sha256": None,
        "evidence": [],
    }

    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            record["error"] = "global experiment lock is busy"
        else:
            env = _sanitized_host_env(manifest["environment"])
            record["started_at"] = _utc_now()
            record["launched"] = True
            try:
                with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
                    "w", encoding="utf-8"
                ) as stderr_file:
                    completed = subprocess.run(
                        command,
                        cwd=worktree,
                        env=env,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        text=True,
                        timeout=manifest["timeout_s"],
                        check=False,
                    )
                record["returncode"] = completed.returncode
            except subprocess.TimeoutExpired:
                record["timed_out"] = True
                record["error"] = "host experiment timed out"
            except OSError as exc:
                record["error"] = f"host launch failed: {exc}"
            finally:
                record["finished_at"] = _utc_now()

    if stdout_path.is_file():
        record["stdout_sha256"] = _sha256_file(stdout_path)
    if stderr_path.is_file():
        record["stderr_sha256"] = _sha256_file(stderr_path)
    record["evidence"] = snapshot_tree(run_dir)

    tracked_record = worktree / "docs" / "research" / "evidence" / "atlas_host" / f"{task_commit}.json"
    tracked_record.parent.mkdir(parents=True, exist_ok=True)
    tracked_record.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record["tracked_record"] = tracked_record.relative_to(worktree).as_posix()
    record["tracked_record_sha256"] = _sha256_file(tracked_record)

    (output_dir / "host-experiment.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return record


def verify_host_record(worktree: Path, record: dict[str, Any]) -> bool:
    tracked = worktree / str(record.get("tracked_record", ""))
    if not tracked.is_file():
        return False
    if _sha256_file(tracked) != record.get("tracked_record_sha256"):
        return False
    run_dir = worktree / str(record.get("run_dir", ""))
    evidence = record.get("evidence")
    return isinstance(evidence, list) and verify_snapshot(run_dir, evidence)


if __name__ == "__main__":
    raise SystemExit("atlas_host_experiment is invoked by the trusted research worker")
