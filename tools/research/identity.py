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
) -> dict[str, Any]:
    """Accept named branches or an exact, complete Praxis-bound detached HEAD.

    Named-branch manual execution keeps its existing path when no Praxis
    identity is supplied. If any Praxis value is supplied, the whole binding
    must be present and the repository, logical branch, and frozen commit must
    agree. Detached execution always requires that complete binding and an
    exact current HEAD.
    """
    values = {
        key: (environment.get(key) or "").strip()
        for key in PRAXIS_ENVIRONMENT_KEYS
    }
    present = any(values.values())
    missing = [key for key, value in values.items() if not value]
    expected_values = {
        "PRAXIS_REPOSITORY": PRAXIS_REPOSITORY,
        "PRAXIS_TASK_BRANCH": expected_branch,
        "PRAXIS_TASK_COMMIT": expected_head,
    }
    mismatches = {
        key: {"actual": values[key], "expected": expected}
        for key, expected in expected_values.items()
        if values[key] and values[key] != expected
    }
    binding_valid = present and not missing and not mismatches
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
            "valid": binding_valid,
            "check_pass": binding_check_pass,
            "missing": missing,
            "mismatches": mismatches,
        },
    }
