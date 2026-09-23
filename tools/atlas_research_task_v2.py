#!/usr/bin/env python3
"""Run one unattended Go2 research task; trusted wrapper owns Git commit/push."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import atlas_research_task as base

WORKER_VERSION = 2
MODEL = base.MODEL


def _prompt(
    *, branch: str, task_path: str, task_commit: str, reference_worktree: Path
) -> str:
    return f"""You are the unattended execution worker for one Go2 research task.

Task identity:
- branch: {branch}
- exact task commit: {task_commit}
- task document: {task_path}

Read, in order:
1. git show origin/main:AGENTS.md
2. git show origin/main:docs/research/SOP.md
3. {task_path}
4. the exact parent evidence referenced by the task

Execute every conditional step already authorized by the task. Stop only at a
task-defined or SOP-defined veto/decision boundary. Do not broaden scientific
scope.

Historical ignored raw evidence may exist under this read-only reference tree:
{reference_worktree}
You may read it when needed, but never modify, delete, rename, or overwrite it.

Infrastructure guardrails:
- Do not modify .github/** or tools/atlas_*.
- Do not push to GitHub.
- Do not run git add, git commit, git reset, git checkout, or other commands that
  write Git metadata. The trusted Atlas wrapper owns staging and commit after
  your work is validated.
- Preserve raw _runs evidence exactly after capture begins.
- If a live run is authorized, obey the task and SOP preflight/run budget.

At closeout, write only the task-required repository files, run the checks the
task requires plus `git diff --check` and `git status --porcelain`, then stop
with the intended working-tree changes still present. If the task text asks you
to commit, treat that as a mechanical step delegated to the trusted wrapper.
Your final response should be a concise success summary or veto reason.
"""


def _codex_command(codex_bin: str, thread_id: str | None, prompt: str) -> list[str]:
    common = [
        "--model",
        MODEL,
        "--sandbox",
        "workspace-write",
        "--json",
        "-c",
        'model_reasoning_effort="max"',
    ]
    if thread_id:
        return [
            codex_bin,
            "exec",
            "resume",
            thread_id,
            *common,
            (
                "Resume this same repository task. The trusted wrapper now owns "
                "git staging/commit/push, so do not write Git metadata. Re-read "
                "the task and working-tree state, finish the authorized work, "
                "run task-required checks plus git diff --check and git status "
                "--porcelain, then stop with intended file changes uncommitted."
            ),
        ]
    return [codex_bin, "exec", *common, prompt]


def _run_codex(
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
    if state.get("worker_version") != WORKER_VERSION:
        # An older worker may have left a thread with obsolete closeout semantics.
        thread_id = None
        state.pop("thread_id", None)
    if thread_id is not None and not isinstance(thread_id, str):
        raise base.ResearchTaskError("stored thread_id is invalid")

    command = _codex_command(codex_bin, thread_id, prompt)
    child_env = os.environ.copy()
    child_env.pop("GITHUB_TOKEN", None)
    child_env.pop("GH_TOKEN", None)
    child_env["GO2_REFERENCE_WORKTREE"] = str(
        Path(
            os.environ.get(
                "GO2_ATLAS_REPO",
                Path.home() / "dev" / "go2-workspace" / "current",
            )
        )
    )

    with (
        stdout_path.open("a", encoding="utf-8") as stdout_file,
        stderr_path.open("a", encoding="utf-8") as stderr_file,
    ):
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
        discovered_thread = thread_id
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
                discovered_thread = event["thread_id"]
                state["thread_id"] = discovered_thread
                state["worker_version"] = WORKER_VERSION
                state["status"] = "running"
                base._write_state(state_path, state)
        return_code = process.wait()
    return return_code, discovered_thread


def _working_tree_paths(worktree: Path) -> list[str]:
    paths: set[str] = set()
    for argv in (
        ["git", "diff", "--name-only", "--"],
        ["git", "diff", "--cached", "--name-only", "--"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        result = base._run(argv, cwd=worktree)
        paths.update(line for line in result.stdout.splitlines() if line)
    return sorted(paths)


def _validate_paths(paths: list[str]) -> None:
    if not paths:
        raise base.ResearchTaskError("Luna completed without repository changes")
    for path in paths:
        if path.startswith(".github/") or path.startswith("tools/atlas_"):
            raise base.ResearchTaskError(
                f"research worker modified protected infrastructure path: {path}"
            )
        if path.startswith("example/cpp/experiments/_runs/"):
            raise base.ResearchTaskError(
                f"research worker modified raw run evidence path: {path}"
            )


def _normalize_closeout_markdown(worktree: Path, paths: list[str]) -> None:
    for relative in paths:
        if not relative.startswith("docs/validation/") or not relative.endswith(".md"):
            continue
        path = worktree / relative
        if not path.is_file():
            continue
        lines = [
            line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()
        ]
        while lines and not lines[-1]:
            lines.pop()
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _trusted_commit(worktree: Path, task_path: str) -> tuple[str, list[str]]:
    paths = _working_tree_paths(worktree)
    _validate_paths(paths)
    _normalize_closeout_markdown(worktree, paths)
    paths = _working_tree_paths(worktree)
    _validate_paths(paths)

    # Stage exactly the validated paths. This runs outside the Codex sandbox, so
    # shared-worktree Git metadata is writable by the trusted runner process.
    base._run(["git", "add", "-A", "--", *paths], cwd=worktree)
    base._git(worktree, "diff", "--cached", "--check")

    staged = [
        line
        for line in base._git(
            worktree, "diff", "--cached", "--name-only", "--"
        ).splitlines()
        if line
    ]
    _validate_paths(staged)
    if sorted(staged) != sorted(paths):
        raise base.ResearchTaskError(
            "trusted staging set differs from validated working-tree paths"
        )

    stem = Path(task_path).stem
    message = f"research: close unattended {stem}"
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
    head = base._git(worktree, "rev-parse", "HEAD")
    if base._git(worktree, "status", "--porcelain"):
        raise base.ResearchTaskError("trusted commit left the task worktree dirty")
    return head, staged


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--task-path", required=True)
    parser.add_argument("--task-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    base._validate_request(args.branch, args.task_path, args.task_commit)
    repo, worktree_root, state_root, lock_path = base._paths()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise base.ResearchTaskError(
                "another Atlas research worker is already running"
            ) from exc

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
            remote_tip = base._git(
                repo, "rev-parse", f"refs/remotes/origin/{args.branch}"
            )
            result_commit = state.get("result_commit")
            if isinstance(result_commit, str) and remote_tip == result_commit:
                print(result_commit)
                return 0

        if state.get("status") == "complete_local":
            result_commit = state.get("result_commit")
            if not isinstance(result_commit, str) or not base.COMMIT_RE.fullmatch(
                result_commit
            ):
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
            print(result_commit)
            return 0

        state.update(
            {
                "schema_version": 2,
                "worker_version": WORKER_VERSION,
                "branch": args.branch,
                "task_path": args.task_path,
                "task_commit": args.task_commit,
                "worktree": str(worktree),
                "status": "starting",
            }
        )
        base._write_state(state_path, state)

        prompt = _prompt(
            branch=args.branch,
            task_path=args.task_path,
            task_commit=args.task_commit,
            reference_worktree=repo,
        )
        return_code, thread_id = _run_codex(
            worktree=worktree,
            prompt=prompt,
            output_dir=args.output_dir,
            state_path=state_path,
            state=state,
        )
        state["thread_id"] = thread_id
        state["worker_version"] = WORKER_VERSION
        if return_code:
            state["status"] = "failed"
            base._write_state(state_path, state)
            raise base.ResearchTaskError(
                f"codex exec failed with exit code {return_code}; see worker logs"
            )

        result_commit, staged_paths = _trusted_commit(worktree, args.task_path)
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
        print(result_commit)
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except base.ResearchTaskError as exc:
        print(f"research task failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
