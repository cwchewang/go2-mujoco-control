"""Deterministic precheck that must pass before expensive review.

This module checks machine-decidable execution plumbing. It does not judge
scientific merit and never launches plant physics.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from tools.substrate.task import load_task
from tools.research.identity import PRAXIS_REPOSITORY, validate_execution_identity
from tools.research.review_contract import (
    DOMAINS,
    contract_hashes,
    inherited_approvals,
    load_manifest,
    routing,
)
from tools.substrate.integrity import strict_json

ROOT = Path(__file__).resolve().parents[2]


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=root,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def _check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    detail: Any,
) -> None:
    checks.append(
        {
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    )


def _run_command(
    argv: list[str],
    *,
    root: Path,
    timeout: int,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "argv": argv,
            "returncode": completed.returncode,
            "elapsed_s": time.monotonic() - started,
            "stdout_tail": (completed.stdout or "")[-2000:],
            "stderr_tail": (completed.stderr or "")[-2000:],
            "pass": completed.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "returncode": None,
            "elapsed_s": time.monotonic() - started,
            "stdout_tail": (exc.stdout or "")[-2000:]
            if isinstance(exc.stdout, str)
            else "",
            "stderr_tail": (exc.stderr or "")[-2000:]
            if isinstance(exc.stderr, str)
            else "",
            "pass": False,
            "timeout": True,
        }


def _identity_checks(task: dict[str, Any], head: str) -> dict[str, Any]:
    config = task["configuration"]
    praxis = config.get("praxis")
    if praxis is None:
        return {
            "configured": False,
            "exact_binding_pass": None,
            "wrong_issue_rejected": None,
            "wrong_task_path_rejected": None,
        }

    issue = praxis["issue_number"]
    task_path = praxis["task_path"]
    env = {
        "PRAXIS_REPOSITORY": PRAXIS_REPOSITORY,
        "PRAXIS_ISSUE_NUMBER": str(issue),
        "PRAXIS_TASK_BRANCH": config["branch"],
        "PRAXIS_TASK_COMMIT": head,
        "PRAXIS_TASK_PATH": task_path,
    }

    exact = validate_execution_identity(
        "",
        config["branch"],
        head,
        head,
        env,
        expected_issue_number=issue,
        expected_task_path=task_path,
    )
    wrong_issue_env = {**env, "PRAXIS_ISSUE_NUMBER": str(issue + 1)}
    wrong_issue = validate_execution_identity(
        "",
        config["branch"],
        head,
        head,
        wrong_issue_env,
        expected_issue_number=issue,
        expected_task_path=task_path,
    )
    wrong_path_env = {**env, "PRAXIS_TASK_PATH": task_path + ".wrong"}
    wrong_path = validate_execution_identity(
        "",
        config["branch"],
        head,
        head,
        wrong_path_env,
        expected_issue_number=issue,
        expected_task_path=task_path,
    )
    return {
        "configured": True,
        "exact_binding_pass": exact["pass"],
        "wrong_issue_rejected": not wrong_issue["pass"],
        "wrong_task_path_rejected": not wrong_path["pass"],
        "exact": exact,
        "wrong_issue": wrong_issue,
        "wrong_task_path": wrong_path,
    }


def run_precheck(
    *,
    task_path: Path,
    contract_path: Path | None = None,
    expected_praxis_issue_number: int | None = None,
    expected_praxis_task_path: str | None = None,
    receipt_paths: list[Path] | None = None,
    previous_contracts_path: Path | None = None,
    root: Path = ROOT,
    run_static_commands: bool = True,
) -> dict[str, Any]:
    root = Path(root).resolve()
    checks: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "schema": 1,
        "kind": "go2-review-precheck",
        "checks": checks,
        "physics_steps": 0,
        "scientific_attempts": 0,
    }

    try:
        task = load_task(task_path, root)
    except Exception as exc:
        _check(checks, "task_loader", False, type(exc).__name__ + ": " + str(exc))
        report["pass"] = False
        return report
    _check(checks, "task_loader", True, task["path"])
    report["task"] = task

    config = task["configuration"]
    selected_contract = contract_path or (
        root / config["review_contract"] if config.get("review_contract") else None
    )
    if selected_contract is None:
        _check(checks, "review_contract_configured", False, "missing review_contract")
        report["pass"] = False
        return report

    try:
        manifest = load_manifest(selected_contract, root)
        hashes = contract_hashes(selected_contract, root)
    except Exception as exc:
        _check(
            checks,
            "review_contract",
            False,
            type(exc).__name__ + ": " + str(exc),
        )
        report["pass"] = False
        return report
    _check(checks, "review_contract", True, manifest["path"])
    report["contracts"] = hashes

    praxis = config.get("praxis")
    if expected_praxis_issue_number is not None:
        actual = praxis.get("issue_number") if isinstance(praxis, dict) else None
        _check(
            checks,
            "expected_praxis_issue_number",
            actual == expected_praxis_issue_number,
            {"actual": actual, "expected": expected_praxis_issue_number},
        )
    if expected_praxis_task_path is not None:
        actual = praxis.get("task_path") if isinstance(praxis, dict) else None
        _check(
            checks,
            "expected_praxis_task_path",
            actual == expected_praxis_task_path,
            {"actual": actual, "expected": expected_praxis_task_path},
        )

    try:
        head = _git(root, "rev-parse", "HEAD")
        identity = _identity_checks(task, head)
        identity_pass = (
            not identity["configured"]
            or (
                identity["exact_binding_pass"]
                and identity["wrong_issue_rejected"]
                and identity["wrong_task_path_rejected"]
            )
        )
    except Exception as exc:
        identity = {"error": type(exc).__name__ + ": " + str(exc)}
        identity_pass = False
    _check(checks, "praxis_identity_contract", identity_pass, identity)
    report["identity"] = identity

    command_results: list[dict[str, Any]] = []
    if run_static_commands:
        for argv in manifest["precheck"]["commands"]:
            result = _run_command(
                argv,
                root=root,
                timeout=manifest["precheck"]["timeout_seconds"],
            )
            command_results.append(result)
            _check(
                checks,
                "static:" + " ".join(argv),
                result["pass"],
                {
                    "returncode": result.get("returncode"),
                    "elapsed_s": result["elapsed_s"],
                    "stdout_tail": result["stdout_tail"],
                    "stderr_tail": result["stderr_tail"],
                },
            )
    report["static_commands"] = command_results

    receipts: list[dict[str, Any]] = []
    for path in receipt_paths or []:
        try:
            value = strict_json(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("receipt must be an object")
            receipts.append(value)
        except Exception as exc:
            _check(
                checks,
                "receipt:" + str(path),
                False,
                type(exc).__name__ + ": " + str(exc),
            )

    if receipts:
        inheritance = inherited_approvals(
            receipts,
            hashes["contracts"],
            required_domains=DOMAINS,
        )
        report["approval_inheritance"] = inheritance
    else:
        report["approval_inheritance"] = {
            "pass": False,
            "inherited": {},
            "missing": list(DOMAINS),
            "rejected": [],
        }

    if previous_contracts_path is not None:
        previous = strict_json(previous_contracts_path.read_text(encoding="utf-8"))
        if isinstance(previous, dict) and "contracts" in previous:
            previous = previous["contracts"]
        report["routing"] = routing(previous, hashes["contracts"])

    report["pass"] = not any(item["status"] == "FAIL" for item in checks)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--expected-praxis-issue-number", type=int)
    parser.add_argument("--expected-praxis-task-path")
    parser.add_argument("--receipt", type=Path, action="append", default=[])
    parser.add_argument("--previous-contracts", type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--skip-static-commands", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_precheck(
        task_path=args.task,
        contract_path=args.contract,
        expected_praxis_issue_number=args.expected_praxis_issue_number,
        expected_praxis_task_path=args.expected_praxis_task_path,
        receipt_paths=args.receipt,
        previous_contracts_path=args.previous_contracts,
        root=args.repo_root,
        run_static_commands=not args.skip_static_commands,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
