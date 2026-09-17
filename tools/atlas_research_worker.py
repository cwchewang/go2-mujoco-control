#!/usr/bin/env python3
"""Run one repository-defined research task with Codex/Luna on Atlas.

This module is invoked only by the trusted main-branch Atlas dispatcher. The
research agent never receives GitHub write credentials; it works in a detached
worktree and leaves commit/push transport to the wrapper.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path, PurePosixPath
from typing import Any


MODEL = "gpt-5.6-luna"
MODEL_REASONING_EFFORT = "xhigh"
MIN_CODEX_VERSION = (0, 154, 0)
CODEX_TIMEOUT_S = 13_200
BRANCH_RE = re.compile(r"^research/[A-Za-z0-9._/-]+$")
TASK_RE = re.compile(r"^docs/research/TASK_[A-Z0-9_]+\.md$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
VERSION_RE = re.compile(r"codex-cli\s+(\d+)\.(\d+)\.(\d+)")
MAIN_BRANCH_RE = re.compile(r"^- Branch:\s+\[`([^`]+)`\]", re.MULTILINE)
MAIN_TASK_RE = re.compile(r"^- Task:\s+\[`([^`]+)`\]", re.MULTILINE)

FORBIDDEN_EXACT = {
    "AGENTS.md",
    "CURRENT.md",
    "docs/research/SOP.md",
}
FORBIDDEN_PREFIXES = (
    ".github/",
    "tools/atlas_",
)


class ResearchTaskError(RuntimeError):
    """The research worker cannot safely execute the requested task."""


def validate_research_parameters(parameters: dict[str, Any]) -> dict[str, str]:
    """Validate and normalize the only accepted research-task request shape."""
    expected = {"branch", "task_path", "task_commit"}
    unknown = sorted(set(parameters) - expected)
    missing = sorted(expected - set(parameters))
    if unknown:
        raise ResearchTaskError(
            "unsupported research-task parameters: " + ", ".join(unknown)
        )
    if missing:
        raise ResearchTaskError(
            "missing research-task parameters: " + ", ".join(missing)
        )

    branch = parameters.get("branch")
    task_path = parameters.get("task_path")
    task_commit = parameters.get("task_commit")
    if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
        raise ResearchTaskError("branch must be a conservative research/* ref")
    if any(token in branch for token in ("..", "//", "@{")) or branch.endswith("/"):
        raise ResearchTaskError("branch contains an unsafe git-ref sequence")
    if not isinstance(task_path, str) or not TASK_RE.fullmatch(task_path):
        raise ResearchTaskError(
            "task_path must match docs/research/TASK_[A-Z0-9_]+.md"
        )
    pure = PurePosixPath(task_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ResearchTaskError("task_path must be repository-relative")
    if not isinstance(task_commit, str) or not SHA_RE.fullmatch(task_commit):
        raise ResearchTaskError("task_commit must be a full 40-hex commit SHA")
    return {
        "branch": branch,
        "task_path": task_path,
        "task_commit": task_commit.lower(),
    }


def parse_main_current(text: str) -> tuple[str, str]:
    """Return the active branch and task basename from main/CURRENT.md."""
    branch_match = MAIN_BRANCH_RE.search(text)
    task_match = MAIN_TASK_RE.search(text)
    if not branch_match or not task_match:
        raise ResearchTaskError("origin/main:CURRENT.md is missing branch/task pointers")
    return branch_match.group(1), task_match.group(1)


def validate_changed_paths(paths: list[str], task_path: str) -> None:
    """Prevent the research agent from changing its own authority/transport."""
    for raw in paths:
        path = raw.replace("\\", "/").lstrip("./")
        if path == task_path:
            raise ResearchTaskError("research agent modified its immutable task file")
        if path in FORBIDDEN_EXACT:
            raise ResearchTaskError(f"research agent modified protected file: {path}")
        if any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            raise ResearchTaskError(f"research agent modified protected path: {path}")


def _workspace_root() -> Path:
    configured = os.environ.get("ATLAS_GO2_WORKSPACE_ROOT")
    return Path(configured).expanduser() if configured else Path.home() / "dev" / "go2-workspace"


def _state_root() -> Path:
    configured = os.environ.get("ATLAS_RESEARCH_STATE_ROOT")
    root = (
        Path(configured).expanduser()
        if configured
        else Path.home() / ".local" / "state" / "go2-atlas-research"
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def _state_path(task_commit: str) -> Path:
    return _state_root() / f"{task_commit}.json"


def _load_state(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchTaskError(f"cannot read worker state {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResearchTaskError(f"worker state is not an object: {path}")
    return value


def _write_state(path: Path, value: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def mark_state_completed(task_commit: str, result_commit: str) -> None:
    """Called by the credentialed push wrapper after remote verification."""
    path = _state_path(task_commit)
    state = _load_state(path) or {}
    state.update(
        {
            "status": "completed",
            "task_commit": task_commit,
            "result_commit": result_commit,
            "completed_unix_s": time.time(),
        }
    )
    _write_state(path, state)


def _run(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int = 180,
    env: dict[str, str] | None = None,
) -> str:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode:
        tail = output[-6000:] if output else "no command output"
        raise ResearchTaskError(
            f"command failed ({completed.returncode}): {' '.join(argv[:4])}: {tail}"
        )
    return output


def _git(cwd: Path, *args: str, timeout: int = 180) -> str:
    return _run(["git", *args], cwd=cwd, timeout=timeout)


def _codex_binary() -> Path:
    candidate = Path.home() / ".local" / "bin" / "codex"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return candidate
    found = shutil.which("codex")
    if not found:
        raise ResearchTaskError("codex executable not found")
    return Path(found)


def _verify_codex(codex: Path) -> str:
    version_text = _run([str(codex), "--version"], cwd=Path.home(), timeout=30)
    match = VERSION_RE.search(version_text)
    if not match:
        raise ResearchTaskError(f"cannot parse Codex version: {version_text}")
    version = tuple(int(item) for item in match.groups())
    if version < MIN_CODEX_VERSION:
        required = ".".join(str(item) for item in MIN_CODEX_VERSION)
        raise ResearchTaskError(
            f"Codex {version_text} is too old; require at least {required}"
        )
    return version_text


def _verify_request_against_remote(
    current: Path,
    *,
    branch: str,
    task_path: str,
    task_commit: str,
) -> None:
    _git(current, "fetch", "origin", "--prune", timeout=300)
    main_current = _git(current, "show", "origin/main:CURRENT.md")
    active_branch, active_task = parse_main_current(main_current)
    if active_branch != branch:
        raise ResearchTaskError(
            f"request branch {branch} is not origin/main CURRENT branch {active_branch}"
        )
    if active_task != Path(task_path).name:
        raise ResearchTaskError(
            f"request task {Path(task_path).name} is not origin/main CURRENT task {active_task}"
        )

    remote_ref = f"refs/remotes/origin/{branch}"
    remote_sha = _git(current, "rev-parse", "--verify", remote_ref).lower()
    if remote_sha != task_commit:
        raise ResearchTaskError(
            f"remote branch moved: expected {task_commit}, found {remote_sha}"
        )
    _git(current, "cat-file", "-e", f"{task_commit}^{{commit}}")
    _git(current, "show", f"{task_commit}:{task_path}")


def _prepare_worktree(
    current: Path,
    task_commit: str,
    state: dict[str, Any] | None,
) -> tuple[Path, Path, list[str]]:
    workspace_root = _workspace_root()
    task_root = workspace_root / "agent-tasks" / task_commit
    task_root.parent.mkdir(parents=True, exist_ok=True)

    if task_root.exists():
        if not (task_root / ".git").exists():
            raise ResearchTaskError(f"existing task path is not a git worktree: {task_root}")
    else:
        _git(current, "worktree", "prune")
        _git(current, "worktree", "add", "--detach", str(task_root), task_commit, timeout=300)

    head = _git(task_root, "rev-parse", "HEAD").lower()
    state_status = (state or {}).get("status")
    prepared_commit = (state or {}).get("result_commit")
    if state_status == "prepared" and isinstance(prepared_commit, str):
        if head != prepared_commit.lower():
            raise ResearchTaskError("prepared worktree HEAD does not match saved result commit")
    elif head != task_commit:
        raise ResearchTaskError(
            f"task worktree HEAD changed unexpectedly: {head} != {task_commit}"
        )

    shared_runs = current / "example" / "cpp" / "experiments" / "_runs"
    shared_runs.mkdir(parents=True, exist_ok=True)
    local_runs = task_root / "example" / "cpp" / "experiments" / "_runs"
    local_runs.mkdir(parents=True, exist_ok=True)

    if state and isinstance(state.get("evidence_names"), list):
        evidence_names = [str(item) for item in state["evidence_names"]]
    else:
        evidence_names = sorted(item.name for item in shared_runs.iterdir())

    for name in evidence_names:
        source = shared_runs / name
        target = local_runs / name
        if not source.exists() and not source.is_symlink():
            raise ResearchTaskError(f"shared evidence disappeared: {source}")
        if os.path.lexists(target):
            if not target.is_symlink() or target.resolve() != source.resolve():
                raise ResearchTaskError(
                    f"task evidence overlay changed an existing entry: {target}"
                )
            continue
        target.symlink_to(source, target_is_directory=source.is_dir())

    return task_root, shared_runs, evidence_names


def _verify_evidence_overlay(
    task_root: Path,
    shared_runs: Path,
    evidence_names: list[str],
) -> list[Path]:
    local_runs = task_root / "example" / "cpp" / "experiments" / "_runs"
    original = set(evidence_names)
    for name in evidence_names:
        source = shared_runs / name
        target = local_runs / name
        if not target.is_symlink() or target.resolve() != source.resolve():
            raise ResearchTaskError(
                f"agent altered the read-only parent evidence overlay: {name}"
            )

    new_entries: list[Path] = []
    for item in local_runs.iterdir():
        if item.name in original:
            continue
        if item.is_symlink():
            raise ResearchTaskError(
                f"new raw evidence entry may not be an arbitrary symlink: {item.name}"
            )
        new_entries.append(item)
    return sorted(new_entries, key=lambda path: path.name)


def _publish_new_evidence(
    task_root: Path,
    shared_runs: Path,
    new_entries: list[Path],
) -> list[str]:
    published: list[str] = []
    for item in new_entries:
        destination = shared_runs / item.name
        if os.path.lexists(destination):
            raise ResearchTaskError(
                f"refusing to overwrite existing shared raw evidence: {destination}"
            )
        shutil.move(str(item), str(destination))
        item.symlink_to(destination, target_is_directory=destination.is_dir())
        published.append(item.name)
    return published


def _changed_paths(worktree: Path) -> list[str]:
    paths: set[str] = set()
    for args in (
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        output = _git(worktree, *args)
        paths.update(line.strip() for line in output.splitlines() if line.strip())
    return sorted(paths)


def _tail(path: Path, limit: int = 6000) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-limit:]


def _run_codex(
    *,
    codex: Path,
    worktree: Path,
    task_path: str,
    output_dir: Path,
    resume: bool,
) -> tuple[int, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "codex.log"
    if resume:
        prompt = f"""Continue the same repository research task after an interrupted or failed automation attempt.

Before acting, re-read `origin/main:AGENTS.md`, `origin/main:CURRENT.md`, `origin/main:docs/research/SOP.md`, and `{task_path}` plus the exact parent evidence referenced by that task. Inspect all existing worktree changes and local `_runs` before deciding what remains.

Do not repeat or replace a scientifically consumed live attempt. The task and SOP run-budget/veto rules remain binding. Fix only execution or closeout work that is still authorized, then finish the task end-to-end.

Automation transport rule: do not commit or push. The trusted Atlas wrapper will validate, commit, and push after you finish. Do not modify AGENTS.md, CURRENT.md, docs/research/SOP.md, the task file, `.github/**`, or `tools/atlas_*`.
"""
    else:
        prompt = f"""Execute the current Go2 research task end-to-end as the Atlas research worker.

Read in this order before acting:
1. `git show origin/main:AGENTS.md`
2. `git show origin/main:CURRENT.md`
3. `git show origin/main:docs/research/SOP.md`
4. `{task_path}` in this checkout
5. the exact parent/closeout evidence referenced by the task

Follow the complete task decision tree without asking the user for routine decisions. Do not broaden the scientific intervention, change frozen variables, or spend a live-run budget not explicitly authorized by the task. If a task-defined stop/veto condition occurs, close out exactly as instructed and stop; do not improvise a replacement experiment.

The local `example/cpp/experiments/_runs/` contains a read-only view of existing parent evidence plus space for this task's new raw runs. Preserve parent evidence exactly.

Automation transport rule: do not commit or push. The trusted Atlas wrapper will validate, commit, and push after you finish. Do not modify AGENTS.md, CURRENT.md, docs/research/SOP.md, the task file, `.github/**`, or `tools/atlas_*`.
"""

    command = [
        str(codex),
        "exec",
        "--model",
        MODEL,
        "--sandbox",
        "workspace-write",
        "-c",
        f"model_reasoning_effort={MODEL_REASONING_EFFORT}",
        "-C",
        str(worktree),
    ]
    if resume:
        command.extend(["resume", "--last", prompt])
    else:
        command.append(prompt)

    env = os.environ.copy()
    for secret_name in ("GITHUB_TOKEN", "GH_TOKEN"):
        env.pop(secret_name, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    with log_path.open("a", encoding="utf-8") as log:
        if resume:
            log.write("\n\n===== RESUME ATTEMPT =====\n")
        process = subprocess.Popen(
            command,
            cwd=worktree,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            return_code = process.wait(timeout=CODEX_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=15)
            raise ResearchTaskError(
                f"Codex exceeded {CODEX_TIMEOUT_S} seconds; worktree preserved for resume"
            )
    return return_code, _tail(log_path)


def _commit_result(worktree: Path, task_path: str) -> str:
    head_before = _git(worktree, "rev-parse", "HEAD").lower()
    changed = _changed_paths(worktree)
    if not changed:
        raise ResearchTaskError("research task produced no trackable closeout/change")
    validate_changed_paths(changed, task_path)
    _git(worktree, "diff", "--check")
    _git(worktree, "diff", "--cached", "--check")

    _git(worktree, "add", "-A")
    _git(worktree, "diff", "--cached", "--check")
    staged = _git(worktree, "diff", "--cached", "--name-only").splitlines()
    validate_changed_paths([item for item in staged if item], task_path)
    if not staged:
        raise ResearchTaskError("no staged research result after validation")

    subject = Path(task_path).stem
    if subject.startswith("TASK_"):
        subject = subject[5:]
    subject = subject.lower().replace("_", "-")[:60]
    _run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Atlas Luna Worker",
            "-c",
            "user.email=atlas-luna@users.noreply.github.com",
            "commit",
            "-m",
            f"research: complete {subject}",
        ],
        cwd=worktree,
        timeout=300,
    )
    result_commit = _git(worktree, "rev-parse", "HEAD").lower()
    if result_commit == head_before:
        raise ResearchTaskError("wrapper commit did not advance HEAD")
    if _git(worktree, "status", "--porcelain"):
        raise ResearchTaskError("worktree is not clean after wrapper commit")
    return result_commit


def run_research_task(
    parameters: dict[str, Any],
    *,
    output_dir: Path,
) -> dict[str, Any]:
    """Execute or resume one research task and prepare one result commit."""
    request = validate_research_parameters(parameters)
    branch = request["branch"]
    task_path = request["task_path"]
    task_commit = request["task_commit"]
    state_path = _state_path(task_commit)
    state = _load_state(state_path)

    if state and state.get("status") == "completed":
        if state.get("branch") != branch or state.get("task_path") != task_path:
            raise ResearchTaskError("completed task state does not match request identity")
        return {
            "kind": "research-task",
            "deduplicated": True,
            "push_required": False,
            "branch": branch,
            "task_path": task_path,
            "task_commit": task_commit,
            "result_commit": state.get("result_commit"),
        }

    lock_path = _state_root() / "worker.lock"
    with lock_path.open("w", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

        state = _load_state(state_path)
        if state and state.get("status") == "completed":
            return {
                "kind": "research-task",
                "deduplicated": True,
                "push_required": False,
                "branch": branch,
                "task_path": task_path,
                "task_commit": task_commit,
                "result_commit": state.get("result_commit"),
            }

        workspace_root = _workspace_root()
        current = workspace_root / "current"
        if not (current / ".git").exists():
            raise ResearchTaskError(f"canonical current worktree not found: {current}")

        _verify_request_against_remote(
            current,
            branch=branch,
            task_path=task_path,
            task_commit=task_commit,
        )
        worktree, shared_runs, evidence_names = _prepare_worktree(
            current, task_commit, state
        )

        if state and state.get("status") == "prepared":
            result_commit = state.get("result_commit")
            if not isinstance(result_commit, str) or not SHA_RE.fullmatch(result_commit):
                raise ResearchTaskError("prepared state is missing a valid result commit")
            if _git(worktree, "status", "--porcelain"):
                raise ResearchTaskError("prepared worktree is unexpectedly dirty")
            return {
                "kind": "research-task",
                "deduplicated": False,
                "resumed": True,
                "push_required": True,
                "branch": branch,
                "task_path": task_path,
                "task_commit": task_commit,
                "result_commit": result_commit.lower(),
                "worktree": str(worktree),
                "state_path": str(state_path),
            }

        codex = _codex_binary()
        codex_version = _verify_codex(codex)
        attempts = int((state or {}).get("attempts", 0)) + 1
        resume = bool(state and state.get("status") in {"running", "failed"})
        running_state = {
            "status": "running",
            "branch": branch,
            "task_path": task_path,
            "task_commit": task_commit,
            "worktree": str(worktree),
            "evidence_names": evidence_names,
            "attempts": attempts,
            "model": MODEL,
            "codex_version": codex_version,
            "started_unix_s": time.time(),
        }
        _write_state(state_path, running_state)

        return_code, codex_tail = _run_codex(
            codex=codex,
            worktree=worktree,
            task_path=task_path,
            output_dir=output_dir,
            resume=resume,
        )
        if return_code:
            failed_state = dict(running_state)
            failed_state.update(
                {
                    "status": "failed",
                    "last_error": f"codex exited {return_code}",
                    "failed_unix_s": time.time(),
                }
            )
            _write_state(state_path, failed_state)
            raise ResearchTaskError(
                f"Codex exited {return_code}; worktree preserved for resume. Tail:\n{codex_tail}"
            )

        try:
            new_evidence = _verify_evidence_overlay(
                worktree, shared_runs, evidence_names
            )
            published_evidence = _publish_new_evidence(
                worktree, shared_runs, new_evidence
            )

            head_now = _git(worktree, "rev-parse", "HEAD").lower()
            if head_now != task_commit:
                raise ResearchTaskError(
                    "research agent committed directly; wrapper-owned transport was violated"
                )
            result_commit = _commit_result(worktree, task_path)
        except Exception as exc:
            failed_state = dict(running_state)
            failed_state.update(
                {
                    "status": "failed",
                    "last_error": str(exc),
                    "failed_unix_s": time.time(),
                }
            )
            _write_state(state_path, failed_state)
            raise

        prepared_state = dict(running_state)
        prepared_state.update(
            {
                "status": "prepared",
                "result_commit": result_commit,
                "published_evidence": published_evidence,
                "prepared_unix_s": time.time(),
            }
        )
        _write_state(state_path, prepared_state)

        return {
            "kind": "research-task",
            "deduplicated": False,
            "resumed": resume,
            "push_required": True,
            "branch": branch,
            "task_path": task_path,
            "task_commit": task_commit,
            "result_commit": result_commit,
            "worktree": str(worktree),
            "state_path": str(state_path),
            "model": MODEL,
            "codex_version": codex_version,
            "published_evidence": published_evidence,
            "codex_tail": codex_tail,
        }
