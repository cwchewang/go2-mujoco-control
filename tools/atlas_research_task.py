#!/usr/bin/env python3
"""Run one trusted repository-defined research task with Codex Luna on Atlas."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

MODEL = "gpt-5.6-luna"
BRANCH_RE = re.compile(r"^research/[A-Za-z0-9._/-]+$")
TASK_RE = re.compile(r"^docs/research/TASK_[A-Za-z0-9_.-]+\.md$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_CHANGED_PREFIXES = (
    ".github/",
    "tools/atlas_",
)
MAX_LOG_TAIL_CHARS = 8000


class ResearchTaskError(RuntimeError):
    """The task cannot be executed safely or did not close out correctly."""


def _run(
    argv: list[str],
    *,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if check and completed.returncode:
        output = (completed.stdout + completed.stderr).strip()
        tail = output[-MAX_LOG_TAIL_CHARS:] if output else "no command output"
        raise ResearchTaskError(
            f"{argv[0]} failed with exit code {completed.returncode}: {tail}"
        )
    return completed


def _git(repo: Path, *args: str, check: bool = True) -> str:
    return _run(["git", *args], cwd=repo, check=check).stdout.strip()


def _validate_request(branch: str, task_path: str, task_commit: str) -> None:
    if not BRANCH_RE.fullmatch(branch) or ".." in branch or "//" in branch:
        raise ResearchTaskError("branch must be a normalized research/* branch")
    if not TASK_RE.fullmatch(task_path) or ".." in task_path:
        raise ResearchTaskError("task_path must be docs/research/TASK_*.md")
    if not COMMIT_RE.fullmatch(task_commit):
        raise ResearchTaskError("task_commit must be a full 40-character lowercase SHA")


def _paths() -> tuple[Path, Path, Path, Path]:
    home = Path.home()
    repo = Path(
        os.environ.get(
            "GO2_ATLAS_REPO",
            home / "dev" / "go2-workspace" / "current",
        )
    ).expanduser()
    worktree_root = Path(
        os.environ.get(
            "GO2_AGENT_WORKTREE_ROOT",
            home / "dev" / "go2-agent" / "tasks",
        )
    ).expanduser()
    state_root = Path(
        os.environ.get(
            "GO2_AGENT_STATE_ROOT",
            home / ".local" / "state" / "go2-research-worker",
        )
    ).expanduser()
    lock_path = Path(
        os.environ.get("GO2_RESEARCH_WORKER_LOCK", "/tmp/go2_research_worker.lock")
    )
    return repo, worktree_root, state_root, lock_path


def _state_path(state_root: Path, task_commit: str) -> Path:
    return state_root / f"{task_commit}.json"


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchTaskError(f"cannot read worker state {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ResearchTaskError(f"worker state is not an object: {path}")
    return data


def _write_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _verify_remote_task(
    repo: Path,
    *,
    branch: str,
    task_path: str,
    task_commit: str,
) -> None:
    if not repo.is_dir():
        raise ResearchTaskError(f"Atlas repository anchor is missing: {repo}")
    _git(repo, "fetch", "origin", "--prune")
    remote_ref = f"refs/remotes/origin/{branch}"
    remote_tip = _git(repo, "rev-parse", "--verify", remote_ref)
    if remote_tip != task_commit:
        raise ResearchTaskError(
            f"remote branch moved: expected {task_commit}, found {remote_tip}"
        )
    _git(repo, "cat-file", "-e", f"{task_commit}^{{commit}}")
    shown = _run(
        ["git", "show", f"{task_commit}:{task_path}"],
        cwd=repo,
        check=False,
    )
    if shown.returncode:
        raise ResearchTaskError(
            f"task file does not exist at task_commit: {task_path}"
        )
    task_text = shown.stdout
    if not task_text.lstrip().startswith("#"):
        raise ResearchTaskError("task file is not a Markdown task document")
    _git(repo, "show", "origin/main:AGENTS.md")
    _git(repo, "show", "origin/main:docs/research/SOP.md")


def _prepare_worktree(
    repo: Path,
    worktree_root: Path,
    task_commit: str,
) -> Path:
    worktree_root.mkdir(parents=True, exist_ok=True)
    worktree = worktree_root / task_commit[:16]
    if worktree.exists():
        inside = _run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=worktree,
            check=False,
        )
        if inside.returncode or inside.stdout.strip() != "true":
            raise ResearchTaskError(
                f"existing task path is not a Git worktree: {worktree}"
            )
        head = _git(worktree, "rev-parse", "HEAD")
        if head == task_commit:
            return worktree
        base_ok = _run(
            ["git", "merge-base", "--is-ancestor", task_commit, head],
            cwd=worktree,
            check=False,
        )
        if base_ok.returncode == 0:
            return worktree
        raise ResearchTaskError(
            f"existing task worktree is unrelated to task_commit: {worktree}"
        )
    _run(
        ["git", "worktree", "add", "--detach", str(worktree), task_commit],
        cwd=repo,
    )
    return worktree


def _bootstrap_prompt(
    *,
    branch: str,
    task_path: str,
    task_commit: str,
    reference_worktree: Path,
) -> str:
    return f"""You are the unattended execution worker for one Go2 research task.

Task identity:
- branch: {branch}
- exact task commit: {task_commit}
- task document: {task_path}

Repository protocol:
1. Read the current trusted rules with:
   git show origin/main:AGENTS.md
2. Read the canonical research SOP with:
   git show origin/main:docs/research/SOP.md
3. Read {task_path} from this exact task worktree.
4. Read the exact parent evidence referenced by the task before acting.

Execute the task end-to-end, including every conditional step the task already
authorizes. Do not stop for routine implementation choices. Stop only at a
task-defined or SOP-defined veto/decision boundary.

Historical ignored raw evidence may exist under this read-only reference
worktree:
{reference_worktree}
You may read from it when the task needs prior raw evidence. Never modify,
delete, rename, or overwrite anything there.

Infrastructure guardrails:
- Do not modify .github/** or tools/atlas_*.
- Do not alter the scientific scope beyond the task.
- Do not push to GitHub.
- Preserve raw _runs evidence exactly after capture begins.
- If a live run is authorized, follow the task and SOP preflight/run budget
  exactly.

At closeout, write the task-required tracked artifacts, commit all intended
tracked changes in this worktree, leave the worktree clean, and then stop.
Your final response should contain only the resulting commit SHA or a concise
veto/failure reason if the task correctly stops without a commit.
"""


def _codex_command(codex_bin: str, thread_id: str | None) -> list[str]:
    base = [
        codex_bin,
        "exec",
        "--model",
        MODEL,
        "--sandbox",
        "workspace-write",
        "--json",
        "--full-auto",
        "-c",
        'model_reasoning_effort="xhigh"',
    ]
    if thread_id:
        return [
            *base,
            "resume",
            thread_id,
            (
                "Resume the same repository research task. Re-read the task and "
                "current worktree state, continue from the last safe point, and "
                "finish the authorized task. Do not push."
            ),
        ]
    return base


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
        raise ResearchTaskError("codex executable was not found in PATH")

    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "codex.ndjson"
    stderr_path = output_dir / "codex.stderr.log"
    thread_id = state.get("thread_id")
    if thread_id is not None and not isinstance(thread_id, str):
        raise ResearchTaskError("stored thread_id is invalid")

    command = _codex_command(codex_bin, thread_id)
    if not thread_id:
        command.append(prompt)

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

    with stdout_path.open("a", encoding="utf-8") as stdout_file, \
            stderr_path.open("a", encoding="utf-8") as stderr_file:
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
                state["status"] = "running"
                _write_state(state_path, state)
        return_code = process.wait()
    return return_code, discovered_thread


def _changed_paths(worktree: Path, task_commit: str) -> list[str]:
    text = _git(
        worktree,
        "diff",
        "--name-only",
        f"{task_commit}..HEAD",
        "--",
    )
    return [line for line in text.splitlines() if line]


def _validate_closeout(worktree: Path, task_commit: str) -> tuple[str, list[str]]:
    head = _git(worktree, "rev-parse", "HEAD")
    if head == task_commit:
        raise ResearchTaskError("Luna completed without creating a closeout commit")
    ancestor = _run(
        ["git", "merge-base", "--is-ancestor", task_commit, head],
        cwd=worktree,
        check=False,
    )
    if ancestor.returncode:
        raise ResearchTaskError("result HEAD is not descended from task_commit")
    status = _git(worktree, "status", "--porcelain")
    if status:
        raise ResearchTaskError(
            "Luna left tracked or untracked worktree changes after closeout"
        )
    _git(worktree, "diff", "--check", task_commit, head)
    changed = _changed_paths(worktree, task_commit)
    if not changed:
        raise ResearchTaskError("closeout commit contains no changed paths")
    for path in changed:
        if any(path.startswith(prefix) for prefix in FORBIDDEN_CHANGED_PREFIXES):
            raise ResearchTaskError(
                f"research worker modified protected infrastructure path: {path}"
            )
        if path.startswith("example/cpp/experiments/_runs/"):
            raise ResearchTaskError(f"research worker tracked raw run evidence: {path}")
    return head, changed


def _write_push_request(
    *,
    output_dir: Path,
    repo: Path,
    worktree: Path,
    branch: str,
    task_path: str,
    task_commit: str,
    result_commit: str,
    state_path: Path,
) -> None:
    payload = {
        "schema_version": 1,
        "repo": str(repo),
        "worktree": str(worktree),
        "branch": branch,
        "task_path": task_path,
        "task_commit": task_commit,
        "result_commit": result_commit,
        "state_path": str(state_path),
    }
    (output_dir / "research-push.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--task-path", required=True)
    parser.add_argument("--task-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    _validate_request(args.branch, args.task_path, args.task_commit)
    repo, worktree_root, state_root, lock_path = _paths()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ResearchTaskError(
                "another Atlas research worker is already running"
            ) from exc

        _verify_remote_task(
            repo,
            branch=args.branch,
            task_path=args.task_path,
            task_commit=args.task_commit,
        )
        worktree = _prepare_worktree(repo, worktree_root, args.task_commit)
        state_path = _state_path(state_root, args.task_commit)
        state = _load_state(state_path)

        if state.get("status") == "pushed":
            remote_tip = _git(repo, "rev-parse", f"refs/remotes/origin/{args.branch}")
            result_commit = state.get("result_commit")
            if isinstance(result_commit, str) and remote_tip == result_commit:
                print(result_commit)
                return 0

        if state.get("status") == "complete_local":
            result_commit = state.get("result_commit")
            if not isinstance(result_commit, str) or not COMMIT_RE.fullmatch(result_commit):
                raise ResearchTaskError("stored local result commit is invalid")
            _write_push_request(
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
                "schema_version": 1,
                "branch": args.branch,
                "task_path": args.task_path,
                "task_commit": args.task_commit,
                "worktree": str(worktree),
                "status": "starting",
            }
        )
        _write_state(state_path, state)

        prompt = _bootstrap_prompt(
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
        if return_code:
            state["status"] = "failed"
            _write_state(state_path, state)
            raise ResearchTaskError(
                f"codex exec failed with exit code {return_code}; see worker logs"
            )

        result_commit, changed = _validate_closeout(worktree, args.task_commit)
        state.update(
            {
                "status": "complete_local",
                "result_commit": result_commit,
                "changed_paths": changed,
            }
        )
        _write_state(state_path, state)
        _write_push_request(
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
    except ResearchTaskError as exc:
        print(f"research task failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
