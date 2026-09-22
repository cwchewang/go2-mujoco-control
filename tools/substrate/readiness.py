"""Exact-head review and explicit start-record validation; no runner imports."""


def validate_review(review, head):
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


def validate_authorization(value, prepared):
    expected = {
        "action": "START_FORMAL_CAPTURE",
        "head": prepared["head"],
        "protocol_sha256": prepared["protocol_sha256"],
        "prepared_manifest_sha256": prepared["prepared_manifest_sha256"],
        "max_attempts": 3,
    }
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
