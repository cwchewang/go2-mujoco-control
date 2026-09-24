"""Review inheritance and explicit start-record validation; no runner imports."""

from __future__ import annotations

import re

from tools.research.review_contract import validate_receipt


def _legacy_review(review, head):
    if (
        not isinstance(review, dict)
        or set(review) != {"head", "science", "execution"}
        or review["head"] != head
    ):
        raise ValueError("review must bind exact launch HEAD")
    identities = []
    for role in ("science", "execution"):
        item = review[role]
        if (
            not isinstance(item, dict)
            or item.get("verdict") != "APPROVED"
            or not isinstance(item.get("reviewer"), str)
            or not item["reviewer"].strip()
            or not isinstance(item.get("evidence"), str)
            or not item["evidence"].strip()
        ):
            raise ValueError("missing independent " + role + " review")
        identities.append(item["reviewer"])
    if len(set(identities)) != 2:
        raise ValueError("science and execution reviewers must differ")


def validate_review(review, head, contracts=None):
    """Validate either legacy exact-HEAD review or schema-2 contract approvals.

    Schema 2 treats target_head as provenance. Approval validity is keyed to the
    reviewed contract digest, so an execution-only HEAD change does not
    invalidate an unchanged science approval.
    """
    if not isinstance(review, dict) or review.get("schema") != 2:
        return _legacy_review(review, head)

    allowed = {"schema", "target_head", "science", "execution"}
    if set(review) != allowed:
        raise ValueError("invalid schema-2 review bundle")
    target_head = review["target_head"]
    if not isinstance(target_head, str) or not re.fullmatch(r"[0-9a-f]{40}", target_head):
        raise ValueError("schema-2 review requires target_head provenance")
    if not isinstance(contracts, dict):
        raise ValueError("schema-2 review requires current contract hashes")

    science = validate_receipt(
        review["science"],
        contracts,
        required_domains=["science"],
    )
    execution = validate_receipt(
        review["execution"],
        contracts,
        required_domains=["execution"],
    )
    if science["reviewer"].strip() == execution["reviewer"].strip():
        raise ValueError("science and execution reviewers must differ")


def validate_authorization(value, prepared):
    expected = {
        "action": "START_FORMAL_CAPTURE",
        "head": prepared["head"],
        "protocol_sha256": prepared["protocol_sha256"],
        "prepared_manifest_sha256": prepared["prepared_manifest_sha256"],
        "max_attempts": prepared.get("max_attempts", 3),
    }
    if type(expected["max_attempts"]) is not int or expected["max_attempts"] < 1:
        raise ValueError("invalid attempt budget")
    if not isinstance(value, dict) or any(
        type(value.get(k)) is not type(v) or value[k] != v for k, v in expected.items()
    ):
        raise ValueError(
            "explicit start authorization does not match prepared checkpoint"
        )
    if (
        value.get("authorized_by") != "user"
        or not isinstance(value.get("user_instruction"), str)
        or not value["user_instruction"].strip()
    ):
        raise ValueError(
            "record the actual user instruction to start; preparation is not authorization"
        )
