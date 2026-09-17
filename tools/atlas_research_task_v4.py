#!/usr/bin/env python3
"""Two-phase Luna worker with a trusted host-experiment capability."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import atlas_host_experiment as host
import atlas_research_task as base
import atlas_research_task_v2 as v2
import atlas_research_task_v3 as v3


WORKER_VERSION = 4
MODEL = base.MODEL
POST_HOST_ALLOWED_PREFIXES = (
    "docs/validation/",
    "example/cpp/tools/analysis/",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _task_manifest(repo: Path, task_commit: str, task_path: str) -> dict[str, Any] | None:
    try:
        return host.load_manifest_from_task_commit(repo, task_commit, task_path)
    except host.HostExperimentError as exc:
        raise base.ResearchTaskError(str(exc)) from exc


def _prompt_prepare(
    *, branch: str, task_path: str, task_commit: str, reference_worktree: Path
) -> str:
    return f"""You are the Luna preparation/analysis worker for one Go2 research task.

Task identity:
- branch: {branch}
- exact task commit: {task_commit}
- task document: {task_path}

Read, in order:
1. git show origin/main:AGENTS.md
2. git show origin/main:docs/research/SOP.md
3. {task_path}
4. the exact parent evidence referenced by the task

This task contains a frozen ATLAS_HOST_EXPERIMENT manifest. The trusted Atlas
wrapper, not you, owns the live MuJoCo/DDS launch. In this preparation phase:

- perform all authorized code changes, builds, unit tests, deterministic offline
  checks, and pre-live preparation that can run inside the workspace sandbox;
- DO NOT launch MuJoCo, DDS, a controller/simulator pair, or any live scientific
  capture yourself;
- DO NOT change the frozen host manifest or substitute another live command;
- DO NOT push or write Git metadata; the trusted wrapper will commit the exact
  candidate after this phase;
- preserve historical raw evidence under the read-only reference tree:
  {reference_worktree}

When preparation is complete, stop normally. Do not invent a live result or a
final live classification; the same thread will be resumed after host execution.
"""


def _prompt_analyze(
    *, task_path: str, candidate_commit: str, host_record: dict[str, Any]
) -> str:
    tracked = host_record.get("tracked_record", "")
    run_dir = host_record.get("run_dir", "")
    launched = host_record.get("launched")
    return f"""Resume this same research task after trusted host execution.

The live/host phase is complete and MUST NOT be rerun from the sandbox.
Candidate commit actually presented to the host: {candidate_commit}
Trusted host execution record: {tracked}
Raw run directory: {run_dir}
Host launched: {launched}
Host return code: {host_record.get('returncode')}
Host error: {host_record.get('error')}

Re-read {task_path}, the trusted host record, and the raw evidence it indexes.
Now perform deterministic analysis and write the task-required closeout.

Separate your reasoning in the artifacts into:
1. host/raw FACTS;
2. DERIVED METRICS with reproducible calculation/provenance;
3. LUNA INTERPRETATION / classification.

Your interpretation is not authoritative: Sol must be able to independently
recompute facts/metrics and overturn your conclusion from the submitted evidence.
Do not modify the trusted host record, raw _runs evidence, runtime/controller
source, tests, or launch scripts after the host run. Analysis-only helper code may
be added only under example/cpp/tools/analysis/ when genuinely needed.
Do not run another live experiment. Do not push or write Git metadata.
Run closeout checks and stop with intended tracked closeout changes uncommitted.
"""


def _codex_command(codex_bin: str, thread_id: str | None, prompt: str) -> list[str]:
    common = [
        "--model",
        MODEL,
        "--sandbox",
        "workspace-write",
        "--json",
        "-c",
        'model_reasoning_effort="xhigh"',
    ]
    if thread_id:
        return [codex_bin, "exec", *common, "resume", thread_id, prompt]
    return [codex_bin, "exec", *common, prompt]


def _run_codex_phase(
    *,
    worktree: Path,
    prompt: str,
    output_dir: Path,
    state_path: Path,
    state: dict[str, Any],
) -> tuple[int, str | None]:
    codex_bin = os.environ.get("CODEX_BIN") or shutil.which("codex")
    if not codex_bin:
        raise base.ResearchTaskError("codex executable was not found in PATH")
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "codex.ndjson"
    stderr_path = output_dir / "codex.stderr.log"
    thread_id = state.get("thread_id")
    if thread_id is not None and not isinstance(thread_id, str):
        raise base.ResearchTaskError("stored thread_id is invalid")

    child_env = os.environ.copy()
    for key in ("GITHUB_TOKEN", "GH_TOKEN", "ACTIONS_RUNTIME_TOKEN"):
        child_env.pop(key, None)
    child_env["GO2_REFERENCE_WORKTREE"] = str(
        Path(os.environ.get("GO2_ATLAS_REPO", Path.home() / "dev" / "go2-workspace" / "current"))
    )

    command = _codex_command(codex_bin, thread_id, prompt)
    with stdout_path.open("a", encoding="utf-8") as stdout_file, stderr_path.open(
        "a", encoding="utf-8"
    ) as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=worktree,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
            bufsize=1,
            env=child_env,
        )
        assert process.stdout is not None
        discovered = thread_id
        for line in process.stdout:
            stdout_file.write(line)
            stdout_file.flush()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(event, dict)
                and event.get("type") == "thread.started"
                and isinstance(event.get("thread_id"), str)
            ):
                discovered = event["thread_id"]
                state["thread_id"] = discovered
                state["worker_version"] = WORKER_VERSION
                base._write_state(state_path, state)
        return process.wait(), discovered


def _normalize_closeout_text(worktree: Path) -> None:
    for relative in v2._working_tree_paths(worktree):
        if not relative.startswith("docs/validation/") or not relative.endswith(".md"):
            continue
        path = worktree / relative
        if not path.is_file():
            continue
        lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _trusted_commit_if_dirty(worktree: Path, task_path: str, *, phase: str) -> str:
    paths = v2._working_tree_paths(worktree)
    if not paths:
        return base._git(worktree, "rev-parse", "HEAD")
    v2._validate_paths(paths)
    if phase == "final":
        _normalize_closeout_text(worktree)
        paths = v2._working_tree_paths(worktree)
        v2._validate_paths(paths)
    base._run(["git", "add", "-A", "--", *paths], cwd=worktree)
    base._git(worktree, "diff", "--cached", "--check")
    staged = [
        line
        for line in base._git(worktree, "diff", "--cached", "--name-only", "--").splitlines()
        if line
    ]
    v2._validate_paths(staged)
    stem = Path(task_path).stem
    message = (
        f"research: prepare host experiment {stem}"
        if phase == "candidate"
        else f"research: close unattended {stem}"
    )
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Atlas Luna Worker",
            "GIT_AUTHOR_EMAIL": "atlas-luna@localhost",
            "GIT_COMMITTER_NAME": "Atlas Luna Worker",
            "GIT_COMMITTER_EMAIL": "atlas-luna@localhost",
        }
    )
    base._run(["git", "commit", "-m", message], cwd=worktree, env=env)
    if base._git(worktree, "status", "--porcelain", "--untracked-files=no"):
        raise base.ResearchTaskError("trusted commit left tracked worktree changes")
    return base._git(worktree, "rev-parse", "HEAD")


def _tracked_diff_paths(worktree: Path, base_commit: str) -> list[str]:
    text = base._git(worktree, "diff", "--name-only", f"{base_commit}..HEAD", "--")
    return [line for line in text.splitlines() if line]


def _validate_post_host_scope(worktree: Path, candidate_commit: str, host_record_path: str) -> None:
    for path in v2._working_tree_paths(worktree):
        if path == host_record_path:
            continue
        if not any(path.startswith(prefix) for prefix in POST_HOST_ALLOWED_PREFIXES):
            raise base.ResearchTaskError(
                f"post-host Luna changed non-analysis path after scientific execution: {path}"
            )
    for path in _tracked_diff_paths(worktree, candidate_commit):
        if path == host_record_path:
            continue
        if not any(path.startswith(prefix) for prefix in POST_HOST_ALLOWED_PREFIXES):
            raise base.ResearchTaskError(
                f"post-host commit history changed non-analysis path: {path}"
            )


def _load_record_from_state(worktree: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    record = state.get("host_record")
    if not isinstance(record, dict):
        return None
    if not host.verify_host_record(worktree, record):
        raise base.ResearchTaskError("trusted host record/raw evidence changed after host execution")
    return record


def _run_host_task(args: Any) -> int:
    base._validate_request(args.branch, args.task_path, args.task_commit)
    repo, worktree_root, state_root, lock_path = base._paths()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = _task_manifest(repo, args.task_commit, args.task_path)
    if manifest is None:
        return v3.main()

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise base.ResearchTaskError("another Atlas research worker is already running") from exc

        base._verify_remote_task(
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
                print(result_commit)
                return 0
        if state.get("status") == "complete_local":
            result_commit = state.get("result_commit")
            if not isinstance(result_commit, str):
                raise base.ResearchTaskError("stored result commit is invalid")
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
            print(result_commit)
            return 0

        state.update(
            {
                "schema_version": 4,
                "worker_version": WORKER_VERSION,
                "branch": args.branch,
                "task_path": args.task_path,
                "task_commit": args.task_commit,
                "worktree": str(worktree),
            }
        )
        base._write_state(state_path, state)

        host_record = _load_record_from_state(worktree, state)
        candidate_commit = state.get("candidate_commit")

        if host_record is None:
            state["status"] = "preparing"
            base._write_state(state_path, state)
            prompt = _prompt_prepare(
                branch=args.branch,
                task_path=args.task_path,
                task_commit=args.task_commit,
                reference_worktree=repo,
            )
            return_code, thread_id = _run_codex_phase(
                worktree=worktree,
                prompt=prompt,
                output_dir=args.output_dir,
                state_path=state_path,
                state=state,
            )
            state["thread_id"] = thread_id
            if return_code:
                state["status"] = "failed_prepare"
                base._write_state(state_path, state)
                raise base.ResearchTaskError(
                    f"Luna preparation failed with exit code {return_code}; see worker logs"
                )
            candidate_commit = _trusted_commit_if_dirty(
                worktree, args.task_path, phase="candidate"
            )
            state["candidate_commit"] = candidate_commit
            state["status"] = "candidate_committed"
            base._write_state(state_path, state)

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
                raise base.ResearchTaskError(str(exc)) from exc
            state["host_record"] = host_record
            state["status"] = "host_completed"
            base._write_state(state_path, state)

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
        return_code, thread_id = _run_codex_phase(
            worktree=worktree,
            prompt=_prompt_analyze(
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
            raise base.ResearchTaskError(
                f"Luna analysis failed with exit code {return_code}; host experiment will not be rerun"
            )

        if not host.verify_host_record(worktree, host_record):
            raise base.ResearchTaskError("Luna modified trusted host facts or raw evidence")
        _validate_post_host_scope(
            worktree, candidate_commit, str(host_record.get("tracked_record", ""))
        )

        result_commit = _trusted_commit_if_dirty(worktree, args.task_path, phase="final")
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
        print(result_commit)
        return 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--task-path", required=True)
    parser.add_argument("--task-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    return _run_host_task(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except base.ResearchTaskError as exc:
        print(f"research task failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
