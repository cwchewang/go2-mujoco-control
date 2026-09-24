"""Tracked task metadata owns branch identity; protocol owns scientific budget."""

from pathlib import Path
import re
import subprocess
from .integrity import digest, strict_json

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASK = ROOT / "tools/substrate/tasks/rl_flat_v1.json"


def load_task(path, root=ROOT):
    path, root = Path(path).resolve(), Path(root).resolve()
    if not path.is_relative_to(root):
        raise ValueError("task must be tracked inside repository")
    relative = path.relative_to(root).as_posix()
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=root,
        check=True,
        capture_output=True,
    )
    value = strict_json(path.read_text())
    required = {"schema", "branch", "protocol", "protocol_sha256", "diff_base"}
    allowed = required | {"praxis", "review_contract"}
    if (
        not required.issubset(value)
        or set(value) - allowed
        or type(value["schema"]) is not int
        or value["schema"] != 1
    ):
        raise ValueError("invalid task schema")
    if not isinstance(value["branch"], str) or not value["branch"]:
        raise ValueError("task branch required")
    subprocess.run(
        ["git", "check-ref-format", "--branch", value["branch"]],
        cwd=root,
        check=True,
        capture_output=True,
    )
    protocol = (root / value["protocol"]).resolve()
    if (
        not protocol.is_relative_to(root / "tools/substrate/protocols")
        or protocol.suffix != ".json"
        or not protocol.is_file()
    ):
        raise ValueError("protocol must belong to qualified protocol directory")
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", protocol.relative_to(root).as_posix()],
        cwd=root,
        check=True,
        capture_output=True,
    )
    if digest(protocol) != value["protocol_sha256"]:
        raise ValueError("task protocol hash mismatch")
    budget = strict_json(protocol.read_text()).get("max_attempts")
    if type(budget) is not int or budget < 1:
        raise ValueError("protocol requires positive integer attempt budget")
    if not isinstance(value["diff_base"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", value["diff_base"]
    ):
        raise ValueError("task requires exact parent commit")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", value["diff_base"], "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
    )

    praxis = value.get("praxis")
    if praxis is not None:
        if not isinstance(praxis, dict) or set(praxis) != {
            "issue_number",
            "task_path",
        }:
            raise ValueError("invalid Praxis task identity binding")
        issue_number = praxis["issue_number"]
        task_path = praxis["task_path"]
        if type(issue_number) is not int or issue_number < 1:
            raise ValueError("Praxis issue number must be a positive integer")
        if not isinstance(task_path, str) or not task_path.endswith(".md"):
            raise ValueError("Praxis task path must be a tracked Markdown path")
        candidate = (root / task_path).resolve()
        if (
            not candidate.is_relative_to(root)
            or not candidate.is_file()
            or ".." in Path(task_path).parts
        ):
            raise ValueError("Praxis task path is invalid")
        subprocess.run(
            [
                "git",
                "ls-files",
                "--error-unmatch",
                candidate.relative_to(root).as_posix(),
            ],
            cwd=root,
            check=True,
            capture_output=True,
        )

    review_contract = value.get("review_contract")
    if review_contract is not None:
        if not isinstance(review_contract, str) or not review_contract.endswith(".json"):
            raise ValueError("review contract path must be a JSON file")
        contract_path = (root / review_contract).resolve()
        contract_root = (root / "tools/research/review_contracts").resolve()
        if (
            not contract_path.is_relative_to(contract_root)
            or not contract_path.is_file()
            or ".." in Path(review_contract).parts
        ):
            raise ValueError("review contract path is invalid")
        subprocess.run(
            [
                "git",
                "ls-files",
                "--error-unmatch",
                contract_path.relative_to(root).as_posix(),
            ],
            cwd=root,
            check=True,
            capture_output=True,
        )

    return {"path": relative, "sha256": digest(path), "configuration": value}
