#!/usr/bin/env python3
"""Run one trusted repository-defined research task with Codex Luna on Atlas."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
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
BUNDLE_REF = "refs/atlas/result"


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


def _git(
    repo: Path,
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> str:
    return _run(["git", *args], cwd=repo, check=check, env=env).stdout.strip()


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
    task_root = Path(
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
    return repo, task_root, state_root, lock_path


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


def _fetch_remote_state(repo: Path, branch: str) -> tuple[str, str]:
    if not repo.is_dir():
        raise ResearchTaskError(f"Atlas repository anchor is missing: {repo}")
    _git(repo, "fetch", "origin", "--prune")
    main_tip = _git(repo, "rev-parse", "--verify", "refs/remotes/origin/main")
    branch_tip = _git(
        repo,
        "rev-parse",
        "--verify",
        f"refs/remotes/origin/{branch}",
    )
    return main_tip, branch_tip


def _verify_task_source(
    repo: Path,
    *,
    task_path: str,
    task_commit: str,
) -> None:
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
    if not shown.stdout.lstrip().startswith("#"):
        raise ResearchTaskError("task file is not a Markdown task document")
    _git(repo, "show", "refs/remotes/origin/main:AGENTS.md")
    _git(repo, "show", "refs/remotes/origin/main:docs/research/SOP.md")


def _copy_git_identity(anchor: Path, task_repo: Path) -> None:
    for key in ("user.name", "user.email"):
        value = _run(
            ["git", "config", "--get", key],
            cwd=anchor,
            check=False,
        ).stdout.strip()
        if value:
            _git(task_repo, "config", key, value)


def _prepare_task_repo(
    anchor: Path,
    task_root: Path,
    *,
    branch: str,
    task_commit: str,
    main_tip: str,
) -> Path:
    task_root.mkdir(parents=True, exist_ok=True)
    task_repo = task_root / f"{task_commit[:16]}.repo"
    remote_url = _git(anchor, "remote", "get-url", "origin")

    if task_repo.exists():
        if not (task_repo / ".git").is_dir():
            raise ResearchTaskError(
                f"existing task path is not an isolated Git repository: {task_repo}"
            )
        head = _git(task_repo, "rev-parse", "HEAD")
        ancestor = _run(
            ["git", "merge-base", "--is-ancestor", task_commit, head],
            cwd=task_repo,
            check=False,
        )
        if ancestor.returncode:
            raise ResearchTaskError(
                f"existing task repository is unrelated to task_commit: {task_repo}"
            )
        current_branch = _git(task_repo, "branch", "--show-current")
        if current_branch != branch:
            if _git(task_repo, "status", "--porcelain"):
                raise ResearchTaskError(
                    "existing task repository is dirty on an unexpected branch"
                )
            _git(task_repo, "checkout", "-B", branch, head)
        _git(task_repo, "remote", "set-url", "origin", remote_url)
        _git(task_repo, "update-ref", "refs/remotes/origin/main", main_tip)
        _git(
            task_repo,
            "update-ref",
            f"refs/remotes/origin/{branch}",
            task_commit,
        )
        return task_repo

    tmp = task_root / f".{task_commit[:16]}.prepare-{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        _run(
            ["git", "clone", "--shared", "--no-checkout", str(anchor), str(tmp)],
            cwd=task_root,
        )
        _git(tmp, "remote", "set-url", "origin", remote_url)
        _git(tmp, "update-ref", "refs/remotes/origin/main", main_tip)
        _git(tmp, "update-ref", f"refs/remotes/origin/{branch}", task_commit)
        _git(tmp, "checkout", "-B", branch, task_commit)
        _git(tmp, "branch", "--set-upstream-to", f"origin/{branch}", branch)
        _copy_git_identity(anchor, tmp)
        if _git(tmp, "status", "--porcelain"):
            raise ResearchTaskError("new isolated task repository is unexpectedly dirty")
        tmp.rename(task_repo)
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        raise
    return task_repo


def _file_fingerprint(path: Path) -> str:
    if path.is_symlink():
        return "symlink:" + os.readlink(path)
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "non-file"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _security_fingerprint(task_repo: Path) -> str:
    git_dir = task_repo / ".git"
    if not git_dir.is_dir() or git_dir.is_symlink():
        raise ResearchTaskError("isolated task repository .git must be a real directory")

    items: dict[str, str] = {}
    for relative in (
        "config",
        "config.worktree",
        "objects/info/alternates",
    ):
        items[relative] = _file_fingerprint(git_dir / relative)

    for dirname in ("hooks", "info"):
        root = git_dir / dirname
        if not root.exists():
            items[dirname + "/"] = "missing"
            continue
        for path in sorted(root.rglob("*")):
            relative = str(path.relative_to(git_dir))
            if path.is_dir() and not path.is_symlink():
                continue
            items[relative] = _file_fingerprint(path)

    payload = json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


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

Trusted setup already completed before this sandbox started:
- `git fetch origin --prune` was run on the trusted Atlas repository anchor;
- `origin/{branch}` was verified to equal the exact task commit above;
- `origin/main`, the task document, AGENTS.md, and the canonical SOP were verified;
- this is an isolated per-task Git repository with writable local Git metadata.

Do not repeat remote fetches. Do not change Git remotes, Git config, Git hooks, or
Git credentials. Network publication is owned by the trusted wrapper.

Repository protocol:
1. Read `git show origin/main:AGENTS.md`.
2. Read `git show origin/main:docs/research/SOP.md`.
3. Read `{task_path}` from this exact task repository.
4. Read the exact parent evidence referenced by the task before acting.

Execute the task end-to-end, including every conditional step already authorized
by the task. Do not stop for routine implementation choices. Stop only at a
task-defined or SOP-defined veto/decision boundary.

Historical ignored raw evidence may exist under this read-only reference
worktree:
{reference_worktree}
You may read from it when the task needs prior raw evidence. Never modify,
delete, rename, or overwrite anything there.

Infrastructure guardrails:
- Do not modify `.github/**` or `tools/atlas_*`.
- Do not alter scientific scope beyond the task.
- Do not push, fetch, or publish anything to GitHub.
- Preserve raw `_runs` evidence exactly after capture begins.
- If a live run is authorized, follow the task and SOP preflight/run budget
  exactly.
- You may create local Git commits as required by the task/SOP. The trusted
  wrapper, not you, performs the final remote push.
- Do not leave background processes running after closeout.

At closeout, write the task-required tracked artifacts, commit all intended
tracked changes in this task repository, leave the repository clean, and stop.
Any task wording that says to push is satisfied later by the trusted wrapper;
do not treat the lack of push credentials as a veto.

Your final response should contain only the resulting commit SHA or a concise
scientific/SOP veto reason if the task correctly stops without a closeout commit.
"""


def _codex_command(codex_bin: str, thread_id: str | None) -> list[str]:
    if thread_id:
        return [
            codex_bin,
            "exec",
            "resume",
            thread_id,
            "--json",
            "-c",
            f'model="{MODEL}"',
            "-c",
            'sandbox_mode="workspace-write"',
            "-c",
            'model_reasoning_effort="xhigh"',
            (
                "Resume this same repository research task. Re-read the task and "
                "current repository state, continue from the last safe point, "
                "and finish every already-authorized step. Do not fetch or push."
            ),
        ]
    return [
        codex_bin,
        "exec",
        "--model",
        MODEL,
        "--sandbox",
        "workspace-write",
        "--json",
        "-c",
        'model_reasoning_effort="xhigh"',
    ]


def _codex_env(reference_worktree: Path) -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if key == "GIT_CONFIG_COUNT" or key.startswith("GIT_CONFIG_KEY_") or \
                key.startswith("GIT_CONFIG_VALUE_"):
            env.pop(key, None)
    for key in ("GITHUB_TOKEN", "GH_TOKEN", "SSH_AUTH_SOCK"):
        env.pop(key, None)
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "/bin/false"
    env["SSH_ASKPASS"] = "/bin/false"
    env["GIT_SSH_COMMAND"] = "/bin/false"
    env["GO2_REFERENCE_WORKTREE"] = str(reference_worktree)
    return env


def _run_codex(
    *,
    task_repo: Path,
    prompt: str,
    output_dir: Path,
    state_path: Path,
    state: dict[str, Any],
    reference_worktree: Path,
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

    discovered_thread = thread_id
    with stdout_path.open("a", encoding="utf-8") as stdout_file, \
            stderr_path.open("a", encoding="utf-8") as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=task_repo,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
            bufsize=1,
            env=_codex_env(reference_worktree),
        )
        assert process.stdout is not None
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
                started = event["thread_id"]
                if thread_id and started != thread_id:
                    process.terminate()
                    process.wait(timeout=10)
                    raise ResearchTaskError(
                        "Codex resume started a different thread instead of the stored task thread"
                    )
                discovered_thread = started
                state["thread_id"] = started
                state["status"] = "running"
                _write_state(state_path, state)
        return_code = process.wait()
    return return_code, discovered_thread


def _changed_paths(task_repo: Path, task_commit: str) -> list[str]:
    text = _git(
        task_repo,
        "diff",
        "--name-only",
        f"{task_commit}..HEAD",
        "--",
    )
    return [line for line in text.splitlines() if line]


def _validate_closeout(
    task_repo: Path,
    *,
    branch: str,
    task_commit: str,
) -> tuple[str, list[str]]:
    current_branch = _git(task_repo, "branch", "--show-current")
    if current_branch != branch:
        raise ResearchTaskError(
            f"Luna left task repository on unexpected branch: {current_branch or 'DETACHED'}"
        )
    head = _git(task_repo, "rev-parse", "HEAD")
    if head == task_commit:
        raise ResearchTaskError("Luna completed without creating a closeout commit")
    ancestor = _run(
        ["git", "merge-base", "--is-ancestor", task_commit, head],
        cwd=task_repo,
        check=False,
    )
    if ancestor.returncode:
        raise ResearchTaskError("result HEAD is not descended from task_commit")
    status = _git(task_repo, "status", "--porcelain")
    if status:
        raise ResearchTaskError(
            "Luna left tracked or untracked task-repository changes after closeout"
        )
    _git(task_repo, "diff", "--check", task_commit, head)
    changed = _changed_paths(task_repo, task_commit)
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


def _create_bundle(
    *,
    task_repo: Path,
    output_dir: Path,
    task_commit: str,
    result_commit: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = output_dir / "research-result.bundle"
    if bundle_path.exists():
        bundle_path.unlink()
    _git(task_repo, "update-ref", BUNDLE_REF, result_commit)
    try:
        _git(
            task_repo,
            "bundle",
            "create",
            str(bundle_path),
            BUNDLE_REF,
            f"^{task_commit}",
        )
        _git(task_repo, "bundle", "verify", str(bundle_path))
    finally:
        _git(task_repo, "update-ref", "-d", BUNDLE_REF, check=False)
    if not bundle_path.is_file() or bundle_path.stat().st_size == 0:
        raise ResearchTaskError("result bundle was not created")
    return bundle_path


def _write_push_request(
    *,
    output_dir: Path,
    repo: Path,
    task_repo: Path,
    branch: str,
    task_path: str,
    task_commit: str,
    result_commit: str,
    state_path: Path,
) -> None:
    bundle_path = _create_bundle(
        task_repo=task_repo,
        output_dir=output_dir,
        task_commit=task_commit,
        result_commit=result_commit,
    )
    payload = {
        "schema_version": 2,
        "repo": str(repo),
        "worktree": str(task_repo),
        "branch": branch,
        "task_path": task_path,
        "task_commit": task_commit,
        "result_commit": result_commit,
        "bundle_path": str(bundle_path),
        "bundle_ref": BUNDLE_REF,
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
    repo, task_root, state_root, lock_path = _paths()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    state_path = _state_path(state_root, args.task_commit)

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ResearchTaskError(
                "another Atlas research worker is already running"
            ) from exc

        state = _load_state(state_path)
        main_tip, remote_tip = _fetch_remote_state(repo, args.branch)

        if state.get("status") == "pushed":
            result_commit = state.get("result_commit")
            if isinstance(result_commit, str) and remote_tip == result_commit:
                print(result_commit)
                return 0

        if remote_tip != args.task_commit:
            raise ResearchTaskError(
                f"remote branch moved: expected {args.task_commit}, found {remote_tip}"
            )
        _verify_task_source(
            repo,
            task_path=args.task_path,
            task_commit=args.task_commit,
        )
        task_repo = _prepare_task_repo(
            repo,
            task_root,
            branch=args.branch,
            task_commit=args.task_commit,
            main_tip=main_tip,
        )

        baseline_security = state.get("security_fingerprint")
        current_security = _security_fingerprint(task_repo)
        if baseline_security is not None and baseline_security != current_security:
            raise ResearchTaskError(
                "isolated task repository Git security metadata changed between runs"
            )
        if baseline_security is None:
            baseline_security = current_security
            state["security_fingerprint"] = baseline_security

        if state.get("status") == "complete_local":
            result_commit, changed = _validate_closeout(
                task_repo,
                branch=args.branch,
                task_commit=args.task_commit,
            )
            if result_commit != state.get("result_commit"):
                raise ResearchTaskError("stored local result commit no longer matches task repository")
            state["changed_paths"] = changed
            _write_state(state_path, state)
            _write_push_request(
                output_dir=args.output_dir,
                repo=repo,
                task_repo=task_repo,
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
                "branch": args.branch,
                "task_path": args.task_path,
                "task_commit": args.task_commit,
                "task_repo": str(task_repo),
                "status": "starting",
                "security_fingerprint": baseline_security,
            }
        )
        _write_state(state_path, state)

        prompt = _bootstrap_prompt(
            branch=args.branch,
            task_path=args.task_path,
            task_commit=args.task_commit,
            reference_worktree=repo,
        )
        stored_thread = state.get("thread_id")
        return_code, thread_id = _run_codex(
            task_repo=task_repo,
            prompt=prompt,
            output_dir=args.output_dir,
            state_path=state_path,
            state=state,
            reference_worktree=repo,
        )
        if stored_thread and thread_id != stored_thread:
            raise ResearchTaskError("Codex resume did not preserve task thread identity")
        state["thread_id"] = thread_id
        if return_code:
            state["status"] = "failed"
            _write_state(state_path, state)
            raise ResearchTaskError(
                f"codex exec failed with exit code {return_code}; see worker logs"
            )

        if _security_fingerprint(task_repo) != baseline_security:
            state["status"] = "failed"
            _write_state(state_path, state)
            raise ResearchTaskError(
                "Luna modified protected Git config/hooks/info metadata"
            )

        result_commit, changed = _validate_closeout(
            task_repo,
            branch=args.branch,
            task_commit=args.task_commit,
        )
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
            task_repo=task_repo,
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
