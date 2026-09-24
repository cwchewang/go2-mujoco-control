"""Separate engineering admission from a frozen scientific experiment."""

import math
import re
from .contracts import vector


def validate_capture_contract(contract):
    required = (
        "reviewed_by",
        "model_sha256",
        "backend_sha256",
        "information_regime",
        "start_state",
        "command",
        "horizon_s",
        "repeat_count",
        "thresholds",
        "support_semantics",
        "control_period_s",
    )
    missing = [k for k in required if k not in contract or contract[k] is None]
    if missing:
        raise ValueError("unfrozen capture fields: " + ", ".join(missing))
    for k in ("horizon_s", "control_period_s"):
        if (
            type(contract[k]) not in (float, int)
            or not math.isfinite(contract[k])
            or contract[k] <= 0
        ):
            raise ValueError("invalid " + k)
    if type(contract["repeat_count"]) is not int or contract["repeat_count"] < 1:
        raise ValueError("invalid repeat count")
    if (
        not contract["reviewed_by"]
        or not contract["thresholds"]
        or not contract["start_state"]
    ):
        raise ValueError("review, thresholds and start state must be frozen")
    if contract["information_regime"] not in (
        "proprioceptive",
        "known_model_oracle",
        "declared_perception",
    ):
        raise ValueError("undeclared information regime")
    if contract["support_semantics"] not in ("traverse", "mandatory_support"):
        raise ValueError("undeclared support semantics")
    for k in ("model_sha256", "backend_sha256"):
        if not isinstance(contract[k], str) or not re.fullmatch(
            "[0-9a-f]{64}", contract[k]
        ):
            raise ValueError("invalid " + k)
    if (
        not isinstance(contract["reviewed_by"], str)
        or not contract["reviewed_by"].strip()
    ):
        raise ValueError("review identity missing")
    if not isinstance(contract["start_state"], dict):
        raise ValueError("start state must contain qpos and qvel")
    qpos = vector(contract["start_state"].get("qpos"), 19, "initial qpos")
    if not math.isclose(sum(float(x * x) for x in qpos[3:7]), 1.0, abs_tol=2e-6):
        raise ValueError("initial quaternion is not normalized")
    vector(contract["start_state"].get("qvel"), 18, "initial qvel")
    vector(contract["command"], 3, "command")
    if not isinstance(contract["thresholds"], dict) or any(
        not isinstance(v, (float, int))
        or isinstance(v, bool)
        or not math.isfinite(v)
        or v < 0
        for v in contract["thresholds"].values()
    ):
        raise ValueError("threshold values must be finite nonnegative numbers")
    if contract["control_period_s"] > contract["horizon_s"]:
        raise ValueError("control period exceeds horizon")
    if contract["support_semantics"] == "mandatory_support":
        names = contract.get("required_supports")
        if (
            not isinstance(names, list)
            or not names
            or any(type(n) is not str or not n for n in names)
            or len(set(names)) != len(names)
        ):
            raise ValueError("mandatory support set must contain unique names")
    # Completeness only. This function neither approves nor launches a run.
    return True


def summarize_frames(
    frames, period_s, support_semantics="traverse", required_supports=()
):
    if (
        not frames
        or type(period_s) not in (float, int)
        or not math.isfinite(period_s)
        or period_s <= 0
    ):
        raise ValueError("empty evidence or invalid period")
    if support_semantics not in ("traverse", "mandatory_support"):
        raise ValueError("invalid support semantics")
    if not isinstance(required_supports, (tuple, list)):
        raise ValueError("required supports must be a sequence of names")
    if support_semantics == "mandatory_support" and not required_supports:
        raise ValueError("mandatory support set is empty")
    if len(set(required_supports)) != len(required_supports) or any(
        type(v) is not str or not v for v in required_supports
    ):
        raise ValueError("invalid required supports")
    first_failure, supports, previous = None, set(), None
    start_time = frames[0]["sim_time_s"]
    for index, row in enumerate(frames):
        if not isinstance(row, dict):
            raise ValueError("frame must be an object")
        if "task_complete" in row and type(row["task_complete"]) is not bool:
            raise ValueError("task_complete must be a boolean")
        if "supports" in row and (
            not isinstance(row["supports"], list)
            or any(type(v) is not str or not v for v in row["supports"])
        ):
            raise ValueError("supports must be a list of names")
        for key in ("failure", "terminal_reason"):
            if row.get(key) is not None and (type(row[key]) is not str or not row[key]):
                raise ValueError("invalid " + key)
        if index < len(frames) - 1 and (
            row.get("terminal_reason") or row.get("task_complete")
        ):
            raise ValueError("evidence continues after termination")
        if (
            type(row["sim_time_s"]) not in (float, int)
            or row["sim_time_s"] < 0
            or row["sequence"] < 0
        ):
            raise ValueError("invalid sequence/time")
        if not math.isclose(
            row["sim_time_s"], start_time + index * period_s, abs_tol=1e-9, rel_tol=0
        ):
            raise ValueError("cumulative clock drift")
        if type(row["sequence"]) is not int or not math.isfinite(row["sim_time_s"]):
            raise ValueError("invalid sequence/time")
        if previous is not None and (
            row["sequence"] != previous["sequence"] + 1
            or not math.isclose(
                row["sim_time_s"] - previous["sim_time_s"],
                period_s,
                abs_tol=1e-9,
                rel_tol=1e-7,
            )
        ):
            raise ValueError("duplicate, skipped or misaligned evidence tick")
        if first_failure is None and row.get("failure"):
            first_failure = {"sequence": row["sequence"], "reason": row["failure"]}
        supports.update(row.get("supports", []))
        previous = row
    missing = (
        sorted(set(required_supports) - supports)
        if support_semantics == "mandatory_support"
        else []
    )
    return {
        "first_failure": first_failure,
        "terminal_reason": frames[-1].get("terminal_reason"),
        "task_complete": bool(frames[-1].get("task_complete"))
        and not missing
        and first_failure is None,
        "missing_supports": missing,
        "frames": len(frames),
    }
