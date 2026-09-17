#!/usr/bin/env python3
"""Atlas dispatcher shim using the current trusted research worker semantics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import atlas_dispatch as legacy


def _research_task_current(
    repo_root: Path,
    parameters: dict[str, str],
    output_dir: Path,
) -> dict[str, Any]:
    argv = [
        "python3",
        "tools/atlas_research_task_v4.py",
        "--branch",
        parameters["branch"],
        "--task-path",
        parameters["task_path"],
        "--task-commit",
        parameters["task_commit"],
        "--output-dir",
        str(output_dir),
    ]
    result_commit = legacy._run(argv, repo_root, timeout=21_600).splitlines()[-1].strip()
    push_request = output_dir / "research-push.json"
    if not push_request.is_file():
        raise legacy.TaskError("research-task completed without a trusted push request")
    try:
        push_data = json.loads(push_request.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise legacy.TaskError(f"research push request is invalid: {exc}") from exc
    if not isinstance(push_data, dict) or push_data.get("result_commit") != result_commit:
        raise legacy.TaskError("research push request does not match worker result")
    return {
        "branch": parameters["branch"],
        "task_path": parameters["task_path"],
        "task_commit": parameters["task_commit"],
        "result_commit": result_commit,
        "codex_log": "codex.ndjson",
        "codex_stderr": "codex.stderr.log",
        "host_experiment": "host-experiment.json",
        "worker_version": 4,
        "worker_impl": 4,
    }


def main() -> int:
    legacy._research_task = _research_task_current
    return legacy.main()


if __name__ == "__main__":
    raise SystemExit(main())
