"""Shared project-level Git identity rules for Go2 scientific execution."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

PRAXIS_REPOSITORY = "cwchewang/go2-mujoco-control"
PRAXIS_ENVIRONMENT_KEYS = (
    "PRAXIS_REPOSITORY",
    "PRAXIS_ISSUE_NUMBER",
    "PRAXIS_TASK_BRANCH",
    "PRAXIS_TASK_COMMIT",
    "PRAXIS_TASK_PATH",
)


def validate_execution_identity(
    actual_branch: str,
    expected_branch: str,
    actual_head: str,
    expected_head: str,
    environment: Mapping[str, str | None],
    *,
    expected_issue_number: int | str | None = None,
    expected_task_path: str | None = None,
) -> dict[str, Any]:
    """Accept named branches or an exact five-field Praxis-bound detached HEAD.

    Named-branch manual execution keeps its existing path when no Praxis
    identity is supplied. If any Praxis value is supplied, all five values must
    be present. Detached execution additionally requires trusted expected
    issue-number and task-path values supplied by tracked task metadata.
    """
    values = {
        key: (environment.get(key) or "").strip() for key in PRAXIS_ENVIRONMENT_KEYS
    }
    present = any(values.values())
    missing = [key for key, value in values.items() if not value]
    expected_issue = (
        str(expected_issue_number) if expected_issue_number is not None else None
    )
    expected_path = expected_task_path.strip() if expected_task_path else None
    expected_values = {
        "PRAXIS_REPOSITORY": PRAXIS_REPOSITORY,
        "PRAXIS_TASK_BRANCH": expected_branch,
        "PRAXIS_TASK_COMMIT": expected_head,
    }
    if expected_issue is not None:
        expected_values["PRAXIS_ISSUE_NUMBER"] = expected_issue
    if expected_path is not None:
        expected_values["PRAXIS_TASK_PATH"] = expected_path
    mismatches = {
        key: {"actual": values[key], "expected": expected}
        for key, expected in expected_values.items()
        if values[key] and values[key] != expected
    }
    expected_transport_identity_complete = (
        expected_issue is not None and expected_path is not None
    )
    binding_valid = (
        present
        and not missing
        and not mismatches
        and expected_transport_identity_complete
    )
    head_matches = bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)) and (
        actual_head == expected_head
    )
    named_branch_matches = bool(actual_branch) and actual_branch == expected_branch

    if actual_branch:
        binding_check_pass = not present or binding_valid
        identity_pass = named_branch_matches and binding_check_pass
    else:
        binding_check_pass = binding_valid
        identity_pass = binding_valid and head_matches

    mode = "named" if actual_branch else "detached"
    return {
        "mode": mode,
        "actual_branch": actual_branch,
        "expected_branch": expected_branch,
        "actual_head": actual_head,
        "expected_head": expected_head,
        "head_matches": head_matches,
        "pass": identity_pass,
        "praxis_binding": {
            "present": present,
            "complete": not missing,
            "expected_transport_identity_complete": expected_transport_identity_complete,
            "valid": binding_valid,
            "check_pass": binding_check_pass,
            "missing": missing,
            "mismatches": mismatches,
        },
    }
