#!/usr/bin/env python3
"""Resume the v2 Luna worker with trusted-wrapper validation context."""

from __future__ import annotations

from typing import Any
from pathlib import Path

import atlas_research_task as base
import atlas_research_task_v2 as v2


_RESUME_VALIDATION_CONTEXT = ""
_ORIGINAL_CODEX_COMMAND = v2._codex_command
_ORIGINAL_RUN_CODEX = v2._run_codex


def _codex_command(codex_bin: str, thread_id: str | None, prompt: str) -> list[str]:
    command = _ORIGINAL_CODEX_COMMAND(codex_bin, thread_id, prompt)
    if thread_id:
        # v2 builds resume as: codex exec resume <id> <exec-options> <prompt>.
        # Codex CLI 0.154.0 expects exec-level options before the resume
        # subcommand: codex exec <exec-options> resume <id> <prompt>.
        if len(command) < 6 or command[2] != "resume" or command[3] != thread_id:
            raise base.ResearchTaskError("unexpected Codex resume command shape")
        command = [
            command[0],
            command[1],
            *command[4:-1],
            "resume",
            thread_id,
            command[-1],
        ]
    if thread_id and _RESUME_VALIDATION_CONTEXT:
        command[-1] += (
            "\n\nThe trusted wrapper rejected the previous closeout after your turn. "
            "Do not rerun any live experiment or repeat scientific capture. "
            "Preserve the existing scientific result and fix only the mechanical "
            "closeout/validation problem below, then rerun the required checks:\n\n"
            + _RESUME_VALIDATION_CONTEXT
        )
    return command


def _run_codex(
    *,
    worktree: Path,
    prompt: str,
    output_dir: Path,
    state_path: Path,
    state: dict[str, Any],
) -> tuple[int, str | None]:
    global _RESUME_VALIDATION_CONTEXT
    _RESUME_VALIDATION_CONTEXT = ""

    if isinstance(state.get("thread_id"), str):
        check = base._run(
            ["git", "diff", "--cached", "--check"],
            cwd=worktree,
            check=False,
        )
        detail = (check.stdout + check.stderr).strip()
        if check.returncode and detail:
            _RESUME_VALIDATION_CONTEXT = detail[-8000:]

    try:
        return _ORIGINAL_RUN_CODEX(
            worktree=worktree,
            prompt=prompt,
            output_dir=output_dir,
            state_path=state_path,
            state=state,
        )
    finally:
        _RESUME_VALIDATION_CONTEXT = ""


def main() -> int:
    # Keep worker semantic version 2 so an interrupted v2 task resumes the exact
    # same Codex thread. This shim changes only recovery context after a trusted
    # wrapper validation failure.
    v2._codex_command = _codex_command
    v2._run_codex = _run_codex
    return v2.main()


if __name__ == "__main__":
    raise SystemExit(main())
