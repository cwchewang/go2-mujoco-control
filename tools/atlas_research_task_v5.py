#!/usr/bin/env python3
"""Fetch the frozen task commit before v4 host-manifest discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import atlas_research_task as base
import atlas_research_task_v4 as v4


_ORIGINAL_TASK_MANIFEST = v4._task_manifest


def _task_manifest(
    repo: Path,
    task_commit: str,
    task_path: str,
) -> dict[str, Any] | None:
    # The GitHub Actions checkout is intentionally pinned to trusted main and
    # the persistent Atlas anchor may not yet know a newly-created research
    # task commit. Fetch refs before `git show <task_commit>:<task_path>`.
    # v4 will still perform its full branch/tip verification immediately
    # afterwards; this fetch only makes the frozen object discoverable.
    base._git(repo, "fetch", "origin", "--prune")
    return _ORIGINAL_TASK_MANIFEST(repo, task_commit, task_path)


def main() -> int:
    v4._task_manifest = _task_manifest
    return v4.main()


if __name__ == "__main__":
    raise SystemExit(main())
