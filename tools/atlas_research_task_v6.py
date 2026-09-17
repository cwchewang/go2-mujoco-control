#!/usr/bin/env python3
"""Concurrent-safe Atlas research worker.

Different tasks may prepare/analyze concurrently. A per-task lock prevents duplicate
execution, while the shared host-live lock is held only around trusted host
capabilities such as MuJoCo/DDS execution.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import atlas_host_experiment as host
import atlas_research_task as base
import atlas_research_task_v2 as v2
import atlas_research_task_v3 as v3
import atlas_research_task_v4 as v4

WORKER_VERSION = 6
PROGRESS_PREFIX = "ATLAS_PROGRESS "
SAFE_PROGRESS_KEYS = {
    "status",
    "branch",
    "task_commit",
    "candidate_commit",
    "result_commit",
    "scientific_attempt_consumed",
    "host_return_code",
    "last_event",
}


def _emit_progress(status: str, **fields: Any) -> None:
    payload: dict[str, Any] = {"status": status}
    for key, value in fields.items():
        if key in SAFE_PROGRESS_KEYS and value is not None:
            payload[key] = value
    print(PROGRESS_PREFIX + json.dumps(payload, sort_keys=True), flush=True)


@contextmanager
def _exclusive_lock(path: Path, *, blocking: bool) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.flock(handle.fileno(), flags)
        except BlockingIOError as exc:
            raise base.ResearchTaskError(
                f"this Atlas task is already running: {path.name}"
            ) from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _task_lock_path(state_root: Path, task_commit: str) -> Path:
    return state_root / "locks" / f"{task_commit}.lock"


def _verify_remote_task(
    repo: Path,
    *,
    branch: str,
    task_path: str,
    task_commit: str,
) -> None:
    """Verify the frozen pointer; dispatcher may have already serialized fetch."""
    if not repo.is_dir():
        raise base.ResearchTaskError(f"Atlas repository anchor is missing: {repo}")
    if os.environ.get("ATLAS_DISPATCH_PREFETCHED") != "1":
        base._git(repo, "fetch", "origin", "--prune")
    remote_ref = f"refs/remotes/origin/{branch}"
    remote_tip = base._git(repo, "rev-parse", "--verify", remote_ref)
    if remote_tip != task_commit:
        raise base.ResearchTaskError(
            f"remote branch moved: expected {task_commit}, found {remote_tip}"
        )
    base._git(repo, "cat-file", "-e", f"{task_commit}^{{commit}}")
    shown = base._run(
        ["git", "show", f"{task_commit}:{task_path}"],
        cwd=repo,
        check=False,
    )
    if shown.returncode:
        raise base.ResearchTaskError(
            f"task file does not exist at task_commit: {task_path}"
        )
    if not shown.stdout.lstrip().startswith("#"):
        raise base.ResearchTaskError("task file is not a Markdown task document")
    base._git(repo, "show", "origin/main:AGENTS.md")
    base._git(repo, "show", "origin/main:docs/research/SOP.md")


def _write_existing_push_request(
    *,
    args: argparse.Namespace,
    repo: Path,
    worktree: Path,
    state_path: Path,
    state: dict[str, Any],
) -> str:
    result_commit = state.get("result_commit")
    if not isinstance(result_commit, str) or not base.COMMIT_RE.fullmatch(result_commit):
        raise base.ResearchTaskError("stored local result commit is invalid")
    base._write_push_request(
        output_dir=args.output_dir,
        repo=repo,
        worktree=worktree,
        branch=args.branch,
        task_path=args.task_path,
        task_commit=args.task_commit,
        result_commit=result_commit,
        state_path=state_path,
    )
    _emit_progress(
        "analyzing",
        branch=args.branch,
        task_commit=args.task_commit,
        result_commit=result_commit,
        last_event="local closeout ready for trusted push",
    )
    print(result_commit)
    return result_commit


def _run_offline_task(
    args: argparse.Namespace,
    *,
    repo: Path,
    worktree_root: Path,
    state_root: Path,
) -> int:
    _verify_remote_task(
        repo,
        branch=args.branch,
        task_path=args.task_path,
        task_commit=args.task_commit,
    )
    worktree = base._prepare_worktree(repo, worktree_root, args.task_commit)
    state_path = base._state_path(state_root, args.task_commit)
    state = base._load_state(state_path)

    if state.get("status") == "pushed":
        result_commit = state.get("result_commit")
        if isinstance(result_commit, str):
            _emit_progress(
                "complete",
                branch=args.branch,
                task_commit=args.task_commit,
                result_commit=result_commit,
                last_event="result already pushed",
            )
            print(result_commit)
            return 0
    if state.get("status") == "complete_local":
        _write_existing_push_request(
            args=args,
            repo=repo,
            worktree=worktree,
            state_path=state_path,
            state=state,
        )
        return 0

    state.update(
        {
            "schema_version": 6,
            "branch": args.branch,
            "task_path": args.task_path,
            "task_commit": args.task_commit,
            "worktree": str(worktree),
            "status": "preparing",
        }
    )
    base._write_state(state_path, state)
    _emit_progress(
        "preparing",
        branch=args.branch,
        task_commit=args.task_commit,
        last_event="Luna offline preparation/analysis started",
    )

    v2._codex_command = v3._codex_command
    return_code, thread_id = v3._run_codex(
        worktree=worktree,
        prompt=v2._prompt(
            branch=args.branch,
            task_path=args.task_path,
            task_commit=args.task_commit,
            reference_worktree=repo,
        ),
        output_dir=args.output_dir,
        state_path=state_path,
        state=state,
    )
    state["thread_id"] = thread_id
    state["worker_version"] = v2.WORKER_VERSION
    if return_code:
        state["status"] = "failed"
        base._write_state(state_path, state)
        _emit_progress(
            "failed",
            branch=args.branch,
            task_commit=args.task_commit,
            last_event=f"Luna exited {return_code}",
        )
        raise base.ResearchTaskError(
            f"codex exec failed with exit code {return_code}; see worker logs"
        )

    result_commit, staged_paths = v2._trusted_commit(worktree, args.task_path)
    validated_commit, changed = base._validate_closeout(worktree, args.task_commit)
    if validated_commit != result_commit:
        raise base.ResearchTaskError("trusted closeout validation moved HEAD")
    state.update(
        {
            "status": "complete_local",
            "result_commit": result_commit,
            "changed_paths": changed,
            "staged_paths": staged_paths,
        }
    )
    base._write_state(state_path, state)
    base._write_push_request(
        output_dir=args.output_dir,
        repo=repo,
        worktree=worktree,
        branch=args.branch,
        task_path=args.task_path,
        task_commit=args.task_commit,
        result_commit=result_commit,
        state_path=state_path,
    )
    _emit_progress(
        "analyzing",
        branch=args.branch,
        task_commit=args.task_commit,
        result_commit=result_commit,
        last_event="offline closeout ready for trusted push",
    )
    print(result_commit)
    return 0


def _run_host_task(
    args: argparse.Namespace,
    *,
    repo: Path,
    worktree_root: Path,
    state_root: Path,
    host_lock_path: Path,
    manifest: dict[str, Any],
) -> int:
    _verify_remote_task(
        repo,
        branch=args.branch,
        task_path=args.task_path,
        task_commit=args.task_commit,
    )
    worktree = base._prepare_worktree(repo, worktree_root, args.task_commit)
    state_path = base._state_path(state_root, args.task_commit)
    state = base._load_state(state_path)

    if state.get("status") == "pushed":
        result_commit = state.get("result_commit")
        if isinstance(result_commit, str):
            _emit_progress(
                "complete",
                branch=args.branch,
                task_commit=args.task_commit,
                result_commit=result_commit,
                last_event="result already pushed",
            )
            print(result_commit)
            return 0
    if state.get("status") == "complete_local":
        _write_existing_push_request(
            args=args,
            repo=repo,
            worktree=worktree,
            state_path=state_path,
            state=state,
        )
        return 0

    state.update(
        {
            "schema_version": 6,
            "worker_version": WORKER_VERSION,
            "branch": args.branch,
            "task_path": args.task_path,
            "task_commit": args.task_commit,
            "worktree": str(worktree),
        }
    )
    base._write_state(state_path, state)

    host_record = v4._load_record_from_state(worktree, state)
    candidate_commit = state.get("candidate_commit")

    if host_record is None:
        state["status"] = "preparing"
        base._write_state(state_path, state)
        _emit_progress(
            "preparing",
            branch=args.branch,
            task_commit=args.task_commit,
            last_event="Luna preparation started",
        )
        return_code, thread_id = v4._run_codex_phase(
            worktree=worktree,
            prompt=v4._prompt_prepare(
                branch=args.branch,
                task_path=args.task_path,
                task_commit=args.task_commit,
                reference_worktree=repo,
            ),
            output_dir=args.output_dir,
            state_path=state_path,
            state=state,
        )
        state["thread_id"] = thread_id
        if return_code:
            state["status"] = "failed_prepare"
            base._write_state(state_path, state)
            _emit_progress(
                "failed",
                branch=args.branch,
                task_commit=args.task_commit,
                last_event=f"Luna preparation exited {return_code}",
            )
            raise base.ResearchTaskError(
                f"Luna preparation failed with exit code {return_code}; see worker logs"
            )
        candidate_commit = v4._trusted_commit_if_dirty(
            worktree, args.task_path, phase="candidate"
        )
        state["candidate_commit"] = candidate_commit
        state["status"] = "candidate_committed"
        base._write_state(state_path, state)
        _emit_progress(
            "candidate_committed",
            branch=args.branch,
            task_commit=args.task_commit,
            candidate_commit=candidate_commit,
            last_event="candidate frozen for trusted host",
        )

        state["status"] = "waiting_for_host"
        base._write_state(state_path, state)
        _emit_progress(
            "waiting_for_host",
            branch=args.branch,
            task_commit=args.task_commit,
            candidate_commit=candidate_commit,
            last_event="waiting for exclusive host-live capability",
        )
        with _exclusive_lock(host_lock_path, blocking=True):
            state["status"] = "host_running"
            base._write_state(state_path, state)
            _emit_progress(
                "host_running",
                branch=args.branch,
                task_commit=args.task_commit,
                candidate_commit=candidate_commit,
                scientific_attempt_consumed=False,
                last_event="trusted host capability acquired",
            )
            try:
                host_record = host.execute_manifest(
                    repo=repo,
                    worktree=worktree,
                    task_commit=args.task_commit,
                    candidate_commit=candidate_commit,
                    task_path=args.task_path,
                    manifest=manifest,
                    output_dir=args.output_dir,
                )
            except host.HostExperimentError as exc:
                _emit_progress(
                    "failed",
                    branch=args.branch,
                    task_commit=args.task_commit,
                    candidate_commit=candidate_commit,
                    last_event=str(exc)[:300],
                )
                raise base.ResearchTaskError(str(exc)) from exc

        state["host_record"] = host_record
        state["status"] = "host_completed"
        base._write_state(state_path, state)
        _emit_progress(
            "host_completed",
            branch=args.branch,
            task_commit=args.task_commit,
            candidate_commit=candidate_commit,
            scientific_attempt_consumed=bool(host_record.get("launched")),
            host_return_code=host_record.get("returncode"),
            last_event="trusted host capability released",
        )

    if not isinstance(candidate_commit, str):
        candidate_commit = state.get("candidate_commit")
    if not isinstance(candidate_commit, str):
        raise base.ResearchTaskError("candidate_commit missing after host phase")
    if not isinstance(host_record, dict):
        raise base.ResearchTaskError("host record missing after host phase")
    if not host.verify_host_record(worktree, host_record):
        raise base.ResearchTaskError("host facts/raw evidence failed integrity verification")

    state["status"] = "analyzing"
    base._write_state(state_path, state)
    _emit_progress(
        "analyzing",
        branch=args.branch,
        task_commit=args.task_commit,
        candidate_commit=candidate_commit,
        host_return_code=host_record.get("returncode"),
        last_event="Luna post-host analysis started",
    )
    return_code, thread_id = v4._run_codex_phase(
        worktree=worktree,
        prompt=v4._prompt_analyze(
            task_path=args.task_path,
            candidate_commit=candidate_commit,
            host_record=host_record,
        ),
        output_dir=args.output_dir,
        state_path=state_path,
        state=state,
    )
    state["thread_id"] = thread_id
    if return_code:
        state["status"] = "failed_analysis"
        base._write_state(state_path, state)
        _emit_progress(
            "failed",
            branch=args.branch,
            task_commit=args.task_commit,
            candidate_commit=candidate_commit,
            last_event=f"Luna analysis exited {return_code}",
        )
        raise base.ResearchTaskError(
            f"Luna analysis failed with exit code {return_code}; host experiment will not be rerun"
        )
    if not host.verify_host_record(worktree, host_record):
        raise base.ResearchTaskError("Luna modified trusted host facts or raw evidence")
    v4._validate_post_host_scope(
        worktree, candidate_commit, str(host_record.get("tracked_record", ""))
    )

    result_commit = v4._trusted_commit_if_dirty(worktree, args.task_path, phase="final")
    if result_commit == candidate_commit:
        raise base.ResearchTaskError("analysis phase produced no closeout changes")
    validated_commit, changed = base._validate_closeout(worktree, args.task_commit)
    if validated_commit != result_commit:
        raise base.ResearchTaskError("trusted closeout validation moved HEAD")

    state.update(
        {
            "status": "complete_local",
            "result_commit": result_commit,
            "changed_paths": changed,
            "candidate_commit": candidate_commit,
            "host_record": host_record,
        }
    )
    base._write_state(state_path, state)
    base._write_push_request(
        output_dir=args.output_dir,
        repo=repo,
        worktree=worktree,
        branch=args.branch,
        task_path=args.task_path,
        task_commit=args.task_commit,
        result_commit=result_commit,
        state_path=state_path,
    )
    _emit_progress(
        "analyzing",
        branch=args.branch,
        task_commit=args.task_commit,
        candidate_commit=candidate_commit,
        result_commit=result_commit,
        host_return_code=host_record.get("returncode"),
        last_event="closeout ready for trusted push",
    )
    print(result_commit)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--task-path", required=True)
    parser.add_argument("--task-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    base._validate_request(args.branch, args.task_path, args.task_commit)
    repo, worktree_root, state_root, host_lock_path = base._paths()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if os.environ.get("ATLAS_DISPATCH_PREFETCHED") != "1":
        base._git(repo, "fetch", "origin", "--prune")
    manifest = v4._task_manifest(repo, args.task_commit, args.task_path)

    with _exclusive_lock(
        _task_lock_path(state_root, args.task_commit),
        blocking=False,
    ):
        if manifest is None:
            return _run_offline_task(
                args,
                repo=repo,
                worktree_root=worktree_root,
                state_root=state_root,
            )
        return _run_host_task(
            args,
            repo=repo,
            worktree_root=worktree_root,
            state_root=state_root,
            host_lock_path=host_lock_path,
            manifest=manifest,
        )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except base.ResearchTaskError as exc:
        _emit_progress("failed", last_event=str(exc)[:300])
        print(f"research task failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
