#!/usr/bin/env python3
"""Push a prepared Atlas research result without exposing credentials to Codex."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from atlas_research_worker import (
    BRANCH_RE,
    SHA_RE,
    ResearchTaskError,
    mark_state_completed,
)


class PushError(RuntimeError):
    """A prepared research result failed the final credentialed push gate."""


def _run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 180,
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
        raise PushError(
            f"command failed ({completed.returncode}): {' '.join(argv[:4])}: "
            + (output[-6000:] if output else "no command output")
        )
    return output


def _load_result(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PushError(f"cannot read dispatcher result: {exc}") from exc
    if not isinstance(value, dict):
        raise PushError("dispatcher result is not an object")
    return value


def _research_details(result: dict[str, Any]) -> dict[str, Any] | None:
    if result.get("status") != "success":
        return None
    details = result.get("details")
    if not isinstance(details, dict) or details.get("kind") != "research-task":
        return None
    return details


def _validate_details(details: dict[str, Any]) -> tuple[str, str, str, Path]:
    branch = details.get("branch")
    task_commit = details.get("task_commit")
    result_commit = details.get("result_commit")
    worktree = details.get("worktree")
    if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
        raise PushError("prepared result has invalid research branch")
    if any(token in branch for token in ("..", "//", "@{")) or branch.endswith("/"):
        raise PushError("prepared result has unsafe research branch")
    for label, value in (("task_commit", task_commit), ("result_commit", result_commit)):
        if not isinstance(value, str) or not SHA_RE.fullmatch(value):
            raise PushError(f"prepared result has invalid {label}")
    if not isinstance(worktree, str) or not worktree:
        raise PushError("prepared result is missing worktree")
    return branch, task_commit.lower(), result_commit.lower(), Path(worktree)


def _askpass_env(token: str, helper: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_ASKPASS"] = str(helper)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["ATLAS_GITHUB_TOKEN"] = token
    return env


def _remote_sha(remote_url: str, branch: str, *, cwd: Path, env: dict[str, str]) -> str:
    output = _run(
        ["git", "-c", "core.hooksPath=/dev/null", "ls-remote", remote_url, f"refs/heads/{branch}"],
        cwd=cwd,
        env=env,
    )
    if not output:
        raise PushError(f"remote branch does not exist: {branch}")
    return output.split()[0].lower()


def _append_summary(summary_path: Path | None, lines: list[str]) -> None:
    if summary_path is None:
        return
    with summary_path.open("a", encoding="utf-8") as handle:
        handle.write("\n## Research push\n\n")
        for line in lines:
            handle.write(f"- {line}\n")


def _update_result(path: Path, details: dict[str, Any]) -> None:
    value = _load_result(path)
    value_details = value.get("details")
    if isinstance(value_details, dict):
        value_details.update(details)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    result = _load_result(args.result)
    details = _research_details(result)
    if details is None or not details.get("push_required"):
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for the final push step")
    if not repository or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise SystemExit("GITHUB_REPOSITORY is invalid")

    try:
        branch, task_commit, result_commit, worktree = _validate_details(details)
        if not (worktree / ".git").exists():
            raise PushError(f"prepared worktree is missing: {worktree}")

        head = _run(["git", "rev-parse", "HEAD"], cwd=worktree).lower()
        if head != result_commit:
            raise PushError(f"prepared HEAD {head} != result commit {result_commit}")
        status = _run(["git", "status", "--porcelain"], cwd=worktree)
        if status:
            raise PushError("prepared worktree is dirty before push")
        parent_check = subprocess.run(
            ["git", "merge-base", "--is-ancestor", task_commit, result_commit],
            cwd=worktree,
            check=False,
        )
        if parent_check.returncode != 0:
            raise PushError("result commit is not a descendant of the authorized task commit")

        remote_url = f"https://github.com/{repository}.git"
        with tempfile.TemporaryDirectory(prefix="atlas-askpass-") as tmpdir:
            helper = Path(tmpdir) / "askpass.sh"
            helper.write_text(
                "#!/bin/sh\n"
                "case \"$1\" in\n"
                "  *Username*) printf '%s\\n' 'x-access-token' ;;\n"
                "  *Password*) printf '%s\\n' \"$ATLAS_GITHUB_TOKEN\" ;;\n"
                "  *) exit 1 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            helper.chmod(0o700)
            env = _askpass_env(token, helper)

            remote_before = _remote_sha(remote_url, branch, cwd=worktree, env=env)
            if remote_before != task_commit:
                raise PushError(
                    f"remote branch moved during execution: expected {task_commit}, found {remote_before}"
                )

            _run(
                [
                    "git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "push",
                    f"--force-with-lease=refs/heads/{branch}:{task_commit}",
                    remote_url,
                    f"HEAD:refs/heads/{branch}",
                ],
                cwd=worktree,
                env=env,
                timeout=300,
            )
            remote_after = _remote_sha(remote_url, branch, cwd=worktree, env=env)
            if remote_after != result_commit:
                raise PushError(
                    f"remote verification failed: expected {result_commit}, found {remote_after}"
                )

        mark_state_completed(task_commit, result_commit)
        details["push_required"] = False
        details["pushed"] = True
        details["remote_result_commit"] = result_commit
        _update_result(
            args.result,
            {
                "push_required": False,
                "pushed": True,
                "remote_result_commit": result_commit,
            },
        )
        _append_summary(
            args.summary,
            [f"Branch: `{branch}`", f"Result commit: `{result_commit}`"],
        )

        # Cleanup is deliberately best-effort and happens only after the remote
        # result is verified. Failure to prune a local build cache must not turn
        # a successful scientific push into a failed checkpoint.
        workspace_root = Path(os.environ.get("ATLAS_GO2_WORKSPACE_ROOT", "")).expanduser()
        current = (
            workspace_root / "current"
            if str(workspace_root) not in ("", ".")
            else Path.home() / "dev" / "go2-workspace" / "current"
        )
        if (current / ".git").exists():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=current,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=current,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        return 0
    except (OSError, subprocess.SubprocessError, PushError, ResearchTaskError) as exc:
        _append_summary(args.summary, [f"Push failed: {exc}"])
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
