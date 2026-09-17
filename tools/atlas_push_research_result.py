#!/usr/bin/env python3
"""Push a locally validated Atlas research result with the workflow token."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

BRANCH_RE = re.compile(r"^research/[A-Za-z0-9._/-]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_OUTPUT_CHARS = 8000


class PushError(RuntimeError):
    """The local result cannot be pushed safely."""


def _run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
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
        tail = output[-MAX_OUTPUT_CHARS:] if output else "no command output"
        raise PushError(
            f"{argv[0]} failed with exit code {completed.returncode}: {tail}"
        )
    return completed


def _git(repo: Path, *args: str) -> str:
    return _run(["git", *args], cwd=repo).stdout.strip()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PushError(f"cannot read push request {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PushError("push request is not a JSON object")
    return data


def _validate_payload(data: dict[str, Any]) -> tuple[Path, Path, str, str, str, Path]:
    branch = data.get("branch")
    task_commit = data.get("task_commit")
    result_commit = data.get("result_commit")
    repo = data.get("repo")
    worktree = data.get("worktree")
    state_path = data.get("state_path")
    if (
        not isinstance(branch, str)
        or not BRANCH_RE.fullmatch(branch)
        or ".." in branch
        or "//" in branch
    ):
        raise PushError("invalid research branch in push request")
    for label, value in (
        ("task_commit", task_commit),
        ("result_commit", result_commit),
    ):
        if not isinstance(value, str) or not COMMIT_RE.fullmatch(value):
            raise PushError(f"invalid {label} in push request")
    if not isinstance(repo, str) or not isinstance(worktree, str):
        raise PushError("push request is missing repository paths")
    if not isinstance(state_path, str):
        raise PushError("push request is missing state_path")
    return (
        Path(repo),
        Path(worktree),
        branch,
        task_commit,
        result_commit,
        Path(state_path),
    )


def _update_state(path: Path, result_commit: str) -> None:
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}
        if isinstance(loaded, dict):
            data = loaded
    data["status"] = "pushed"
    data["result_commit"] = result_commit
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not token:
        raise PushError("GITHUB_TOKEN is required for the trusted push step")
    if not repository or "/" not in repository:
        raise PushError("GITHUB_REPOSITORY is missing or invalid")

    repo, worktree, branch, task_commit, result_commit, state_path = _validate_payload(
        _load_json(args.request)
    )
    if not repo.is_dir() or not worktree.is_dir():
        raise PushError("repository or task worktree no longer exists")

    local_head = _git(worktree, "rev-parse", "HEAD")
    if local_head != result_commit:
        raise PushError(
            f"task worktree moved after validation: expected {result_commit}, found {local_head}"
        )
    ancestor = _run(
        ["git", "merge-base", "--is-ancestor", task_commit, result_commit],
        cwd=worktree,
        check=False,
    )
    if ancestor.returncode:
        raise PushError("result commit is not descended from task commit")
    if _git(worktree, "status", "--porcelain"):
        raise PushError("task worktree became dirty after validation")

    _git(repo, "fetch", "origin", "--prune")
    remote_ref = f"refs/remotes/origin/{branch}"
    remote_tip = _git(repo, "rev-parse", "--verify", remote_ref)
    if remote_tip == result_commit:
        _update_state(state_path, result_commit)
        print(result_commit)
        return 0
    if remote_tip != task_commit:
        raise PushError(
            f"remote branch moved during task execution: expected {task_commit}, found {remote_tip}"
        )

    auth = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    env = os.environ.copy()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.extraHeader"
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {auth}"
    remote_url = f"https://github.com/{repository}.git"
    lease = f"refs/heads/{branch}:{task_commit}"
    refspec = f"{result_commit}:refs/heads/{branch}"
    _run(
        [
            "git",
            "push",
            f"--force-with-lease={lease}",
            remote_url,
            refspec,
        ],
        cwd=worktree,
        env=env,
    )
    _git(repo, "fetch", "origin", "--prune")
    pushed_tip = _git(repo, "rev-parse", "--verify", remote_ref)
    if pushed_tip != result_commit:
        raise PushError(
            f"push completed but remote verification failed: found {pushed_tip}"
        )
    _update_state(state_path, result_commit)
    print(result_commit)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PushError as exc:
        print(f"research result push failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
