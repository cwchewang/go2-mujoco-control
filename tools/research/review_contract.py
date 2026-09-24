"""Project-owned review contract hashing and approval inheritance.

Praxis may enforce that this machinery passed, but Go2 owns the scientific,
execution, and evidence contract definitions in tracked manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

from tools.substrate.integrity import strict_json

ROOT = Path(__file__).resolve().parents[2]
DOMAINS = ("science", "execution", "evidence")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tracked_file(root: Path, raw: str) -> Path:
    if not isinstance(raw, str) or not raw or ".." in Path(raw).parts:
        raise ValueError("contract file path must be a nonempty repository-relative path")
    path = (root / raw).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("contract file does not exist inside repository: " + raw)
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", path.relative_to(root).as_posix()],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return path


def _domain_spec(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} contract must be an object")
    allowed = {"files", "json_files", "values"}
    if set(value) - allowed:
        raise ValueError(f"{name} contract has unknown fields")
    files = value.get("files", [])
    json_files = value.get("json_files", [])
    values = value.get("values", {})
    if (
        not isinstance(files, list)
        or not all(isinstance(item, str) and item for item in files)
        or len(files) != len(set(files))
    ):
        raise ValueError(f"{name}.files must be unique nonempty paths")
    if (
        not isinstance(json_files, list)
        or not all(isinstance(item, str) and item for item in json_files)
        or len(json_files) != len(set(json_files))
    ):
        raise ValueError(f"{name}.json_files must be unique nonempty paths")
    if set(files) & set(json_files):
        raise ValueError(f"{name} contract cannot list a file in both modes")
    try:
        _canonical(values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}.values must be finite JSON") from exc
    return {"files": files, "json_files": json_files, "values": values}


def load_manifest(path: Path | str, root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    path = _tracked_file(root, str(Path(path).as_posix()))
    value = strict_json(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("review contract manifest must be an object")
    allowed = {"schema", "name", "domains", "precheck"}
    if set(value) - allowed or value.get("schema") != 1:
        raise ValueError("invalid review contract manifest schema")
    if not isinstance(value.get("name"), str) or not value["name"].strip():
        raise ValueError("review contract manifest requires a name")
    domains = value.get("domains")
    if not isinstance(domains, dict) or set(domains) != set(DOMAINS):
        raise ValueError("review contract manifest must define science/execution/evidence")
    normalized_domains = {
        name: _domain_spec(domains[name], name=name) for name in DOMAINS
    }
    precheck = value.get("precheck", {})
    if not isinstance(precheck, dict) or set(precheck) - {"commands", "timeout_seconds"}:
        raise ValueError("invalid precheck definition")
    commands = precheck.get("commands", [])
    if (
        not isinstance(commands, list)
        or not all(
            isinstance(command, list)
            and command
            and all(isinstance(part, str) and part for part in command)
            for command in commands
        )
    ):
        raise ValueError("precheck.commands must be arrays of argv strings")
    timeout = precheck.get("timeout_seconds", 120)
    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise ValueError("precheck timeout must be an integer in [1, 600]")
    return {
        "schema": 1,
        "name": value["name"].strip(),
        "path": path.relative_to(root).as_posix(),
        "domains": normalized_domains,
        "precheck": {"commands": commands, "timeout_seconds": timeout},
    }


def _hash_domain(spec: dict[str, Any], root: Path) -> tuple[str, dict[str, Any]]:
    raw_files: list[dict[str, str]] = []
    json_files: list[dict[str, str]] = []
    for raw in spec["files"]:
        path = _tracked_file(root, raw)
        raw_files.append({"path": raw, "sha256": _sha256(path.read_bytes())})
    for raw in spec["json_files"]:
        path = _tracked_file(root, raw)
        parsed = strict_json(path.read_text(encoding="utf-8"))
        json_files.append({"path": raw, "sha256": _sha256(_canonical(parsed))})
    payload = {
        "files": raw_files,
        "json_files": json_files,
        "values": spec["values"],
    }
    return _sha256(_canonical(payload)), payload


def contract_hashes(path: Path | str, root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    manifest = load_manifest(path, root)
    hashes: dict[str, str] = {}
    details: dict[str, Any] = {}
    for domain in DOMAINS:
        hashes[domain], details[domain] = _hash_domain(
            manifest["domains"][domain], root
        )
    return {
        "schema": 1,
        "manifest": manifest["path"],
        "manifest_name": manifest["name"],
        "manifest_sha256": _sha256(
            _canonical(
                {
                    "schema": manifest["schema"],
                    "name": manifest["name"],
                    "domains": manifest["domains"],
                }
            )
        ),
        "contracts": hashes,
        "details": details,
    }


def changed_domains(previous: dict[str, str], current: dict[str, str]) -> list[str]:
    if set(previous) != set(DOMAINS) or set(current) != set(DOMAINS):
        raise ValueError("contract maps must contain science/execution/evidence")
    for value in [*previous.values(), *current.values()]:
        if not isinstance(value, str) or not HEX64.fullmatch(value):
            raise ValueError("contract hashes must be lowercase SHA-256")
    return [domain for domain in DOMAINS if previous[domain] != current[domain]]


def _nonempty_evidence(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return False


def validate_receipt(
    receipt: dict[str, Any],
    current_contracts: dict[str, str],
    *,
    required_domains: Iterable[str],
) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise ValueError("approval receipt must be an object")
    allowed = {
        "schema",
        "verdict",
        "reviewer",
        "reviewed_domains",
        "contracts",
        "target_head",
        "evidence",
        "summary",
    }
    if set(receipt) - allowed or receipt.get("schema") != 1:
        raise ValueError("invalid approval receipt schema")
    if receipt.get("verdict") != "APPROVED":
        raise ValueError("approval receipt is not APPROVED")
    reviewer = receipt.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("approval receipt requires reviewer identity")
    reviewed = receipt.get("reviewed_domains")
    if (
        not isinstance(reviewed, list)
        or not reviewed
        or len(reviewed) != len(set(reviewed))
        or any(domain not in DOMAINS for domain in reviewed)
    ):
        raise ValueError("approval receipt has invalid reviewed_domains")
    contracts = receipt.get("contracts")
    if not isinstance(contracts, dict) or set(contracts) != set(reviewed):
        raise ValueError("approval receipt contracts must match reviewed_domains")
    for domain, value in contracts.items():
        if not isinstance(value, str) or not HEX64.fullmatch(value):
            raise ValueError("approval receipt contains invalid contract hash")
        if current_contracts.get(domain) != value:
            raise ValueError(domain + " approval is stale")
    required = list(required_domains)
    if any(domain not in DOMAINS for domain in required):
        raise ValueError("unknown required review domain")
    missing = [domain for domain in required if domain not in reviewed]
    if missing:
        raise ValueError("approval receipt does not cover: " + ", ".join(missing))
    target_head = receipt.get("target_head")
    if target_head is not None and (
        not isinstance(target_head, str) or not HEX40.fullmatch(target_head)
    ):
        raise ValueError("target_head provenance must be a 40-character SHA")
    if not _nonempty_evidence(receipt.get("evidence")):
        raise ValueError("approval receipt requires evidence")
    summary = receipt.get("summary")
    if summary is not None and (not isinstance(summary, str) or not summary.strip()):
        raise ValueError("approval receipt summary must be nonempty when present")
    return receipt


def inherited_approvals(
    receipts: Iterable[dict[str, Any]],
    current_contracts: dict[str, str],
    *,
    required_domains: Iterable[str] = DOMAINS,
) -> dict[str, Any]:
    required = list(required_domains)
    inherited: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            rejected.append({"receipt": str(index), "reason": "not an object"})
            continue
        reviewed = receipt.get("reviewed_domains")
        if not isinstance(reviewed, list):
            rejected.append({"receipt": str(index), "reason": "missing reviewed_domains"})
            continue
        for domain in reviewed:
            if domain not in required or domain in inherited:
                continue
            try:
                validate_receipt(receipt, current_contracts, required_domains=[domain])
            except ValueError as exc:
                rejected.append(
                    {"receipt": str(index), "domain": str(domain), "reason": str(exc)}
                )
            else:
                inherited[domain] = receipt
    missing = [domain for domain in required if domain not in inherited]
    return {
        "pass": not missing,
        "inherited": {
            domain: {
                "reviewer": value["reviewer"],
                "target_head": value.get("target_head"),
                "contract_hash": value["contracts"][domain],
            }
            for domain, value in inherited.items()
        },
        "missing": missing,
        "rejected": rejected,
    }


def routing(previous: dict[str, str], current: dict[str, str]) -> dict[str, Any]:
    changed = changed_domains(previous, current)
    return {
        "changed_domains": changed,
        "reviews_required": changed,
        "unchanged_domains": [domain for domain in DOMAINS if domain not in changed],
    }


def _load_json(path: Path) -> Any:
    return strict_json(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    hashes = sub.add_parser("hashes")
    hashes.add_argument("manifest", type=Path)
    hashes.add_argument("--repo-root", type=Path, default=ROOT)

    route = sub.add_parser("route")
    route.add_argument("manifest", type=Path)
    route.add_argument("--previous", type=Path, required=True)
    route.add_argument("--repo-root", type=Path, default=ROOT)

    validate = sub.add_parser("validate")
    validate.add_argument("manifest", type=Path)
    validate.add_argument("receipt", type=Path)
    validate.add_argument("--domain", action="append", choices=DOMAINS, required=True)
    validate.add_argument("--repo-root", type=Path, default=ROOT)

    args = parser.parse_args()
    current = contract_hashes(args.manifest, args.repo_root)
    if args.command == "hashes":
        print(json.dumps(current, indent=2, sort_keys=True))
        return 0
    if args.command == "route":
        previous = _load_json(args.previous)
        if isinstance(previous, dict) and "contracts" in previous:
            previous = previous["contracts"]
        print(
            json.dumps(
                routing(previous, current["contracts"]),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    receipt = _load_json(args.receipt)
    validate_receipt(
        receipt,
        current["contracts"],
        required_domains=args.domain,
    )
    print(json.dumps({"pass": True, "domains": args.domain}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
