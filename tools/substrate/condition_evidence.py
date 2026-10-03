"""Independent reconstruction of delivered packets and paired pre-exposure prefixes."""

import hashlib
import json
import math

from .contracts import POLICY_JOINTS


def _close(a, b):
    return math.isclose(float(a), float(b), rel_tol=0, abs_tol=1e-9)


def _hash(record):
    return hashlib.sha256(
        json.dumps(
            record, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _raw_payload(row, whole_body, controller_time=None):
    # The locked canonical model's raw state order is checked during preparation.
    q, v = row["qpos"], row["qvel"]
    proprio = {
        "joint_names": list(POLICY_JOINTS),
        "position": q[7:],
        "velocity": v[6:],
        "quaternion_wxyz": q[3:7],
        "angular_velocity_body": v[3:6],
    }
    if not whole_body:
        return {"kind": "proprioceptive", **proprio}
    return {
        "kind": "whole_body_state",
        "proprioception": proprio,
        "base_position_world": q[:3],
        "linear_velocity_world": v[:3],
        "time_s": row["sim_time_s"] if controller_time is None else controller_time,
    }


def _prefix_difference(a, b):
    maximum = 0.0

    def compare(left, right):
        nonlocal maximum
        if isinstance(left, dict):
            if not isinstance(right, dict) or set(left) != set(right):
                raise ValueError("paired prefix shape differs")
            for key in left:
                compare(left[key], right[key])
        elif isinstance(left, list):
            if not isinstance(right, list) or len(left) != len(right):
                raise ValueError("paired prefix shape differs")
            for x, y in zip(left, right):
                compare(x, y)
        elif type(left) in (int, float) and not isinstance(left, bool):
            if (
                type(right) not in (int, float)
                or not math.isfinite(left)
                or not math.isfinite(right)
            ):
                raise ValueError("invalid paired prefix number")
            maximum = max(maximum, abs(left - right))
        elif left != right:
            raise ValueError("paired prefix categorical value differs")

    fields = (
        "qpos",
        "qvel",
        "command",
        "controller_update",
        "information",
        "target",
        "action",
    )
    for x, y in zip(a, b):
        for key in fields:
            compare(x[key], y[key])
    return maximum


def verify_condition(rows, baseline_rows, name, controller, plan, baseline_sha256):
    if name not in plan["raw"]["conditions"] or controller not in ("rl", "mjpc"):
        raise ValueError("unknown condition/controller")
    whole_body = controller == "mjpc"
    horizon = plan["task"].horizon_ticks
    terminal = rows[-1]["terminal_reason"]
    onset = plan["raw"]["conditions"][name]["start_tick"]
    # Physical inputs are set AFTER the onset snapshot and safety check; that
    # snapshot/action must still match the paired unperturbed reference.
    end = min(onset + 1, len(rows) - 1) if onset else min(1, len(rows) - 1)
    prefix_maximum = _prefix_difference(rows[:end], baseline_rows[:end])
    prefix_valid = prefix_maximum <= plan["raw"]["repeat_absolute_tolerance"]
    if not prefix_valid and terminal == "horizon":
        raise ValueError("paired pre-exposure prefix is not equivalent")
    packets, candidates = 0, []
    setting_seen = False
    feedback_ticks = (
        20
        if name == "decision_period" and not whole_body
        else (1 if whole_body else 10)
    )
    planning_ticks = 20 if name == "decision_period" else 10
    for row in rows[:-1]:
        tick = row["tick"]
        update = row["controller_update"]
        if type(update) is not bool or update != (tick % feedback_ticks == 0):
            raise ValueError("actual feedback/policy update clock differs")
        if update:
            source_tick = max(0, tick - 10) if name == "observation_delay" else tick
            seeded = name == "observation_delay" and tick < 10
            metadata, information = row["condition_observation"], row["information"]
            if (
                metadata.get("format") != "normalized-named-state-v1"
                or metadata.get("source_tick") != source_tick
                or type(metadata.get("source_tick")) is not int
                or metadata.get("initial_state_seed") is not seeded
            ):
                raise ValueError("delivered packet source/format drifted")
            source = rows[source_tick]
            if metadata.get("source_payload_sha256") != _hash(
                _raw_payload(source, whole_body)
            ):
                raise ValueError(
                    "delivered measurement hash does not match original state"
                )
            if metadata.get("controller_payload_sha256") != _hash(
                _raw_payload(
                    source, whole_body, row["sim_time_s"] if whole_body else None
                )
            ):
                raise ValueError("retimed controller packet hash differs")
            expected_available = (
                0.0
                if seeded
                else source["sim_time_s"] + (0.02 if name == "observation_delay" else 0)
            )
            if (
                not _close(information["sample_time_s"], source["sim_time_s"])
                or not _close(information["available_time_s"], expected_available)
                or not _close(information["controller_time_s"], row["sim_time_s"])
                or not _close(
                    information["age_s"], row["sim_time_s"] - source["sim_time_s"]
                )
            ):
                raise ValueError("delivered information age/clock differs")
            if whole_body:
                if not _close(metadata["controller_payload_time_s"], row["sim_time_s"]):
                    raise ValueError("native clock was delayed")
                diagnostics = row["controller_diagnostics"]["controller"]
                last = diagnostics["last_step"]
                replan = tick % planning_ticks == 0
                if (
                    last["replanned"] is not replan
                    or not _close(
                        diagnostics["control_period_s"], planning_ticks * 0.002
                    )
                    or not _close(diagnostics["feedback_period_s"], 0.002)
                ):
                    raise ValueError("actual native planning/feedback cadence differs")
                for key in ("sampled_command", "requested_command"):
                    values = last[key]
                    if (
                        not isinstance(values, list)
                        or len(values) != 3
                        or any(
                            type(value) not in (int, float) or not math.isfinite(value)
                            for value in values
                        )
                    ):
                        raise ValueError(
                            "native command must contain three finite numbers"
                        )
                latest = tick - tick % planning_ticks
                if any(
                    not _close(x, y)
                    for x, y in zip(
                        last["sampled_command"], plan["task"].command_at(latest)
                    )
                ):
                    raise ValueError("native command sampling differs")
                if any(
                    not _close(x, y)
                    for x, y in zip(last["requested_command"], row["command"])
                ):
                    raise ValueError("native current requested command differs")
            packets += 1
            if name == "observation_delay" and source_tick < tick:
                candidates.append(tick)
                setting_seen = True
        condition = row["condition"]
        if condition["id"] != name or condition["tick"] != tick:
            raise ValueError("condition record identity differs")
        if name == "sliding_friction":
            switched = tick >= onset
            if condition["switched"] is not switched:
                raise ValueError("friction setting time differs")
            setting_seen |= switched
            expected = [0.3 if switched else 0.8] * 2 + [0.02, 0.01, 0.01]
            for contact in condition["actual_contacts"]:
                if contact["foot_name"] not in ("FL", "FR", "RL", "RR"):
                    raise ValueError("unexpected exposed foot")
                if len(contact["friction"]) != 5 or any(
                    not _close(x, y) for x, y in zip(contact["friction"], expected)
                ):
                    raise ValueError("actual contact friction differs")
            if switched and condition["actual_contacts"]:
                candidates.append(tick)
        elif name == "lateral_force":
            force = [0, 50, 0, 0, 0, 0] if onset <= tick < 3100 else [0] * 6
            if condition["applied_world_wrench"] != force:
                raise ValueError("actual force pulse differs")
            if force[1]:
                candidates.append(tick)
                setting_seen = True
        elif name == "decision_period":
            setting_seen = True
            if tick % 10 == 0 and tick % 20 != 0:
                # Native feedback continues; its replan at this tick is absent.
                if not whole_body or update:
                    candidates.append(tick)
    # A logged setting alone does not prove any input reached a completed step.
    confirmed = [tick + 1 for tick in candidates if tick + 1 < len(rows)]
    exposed = bool(confirmed)
    complete = terminal == "horizon" and rows[-1]["tick"] == horizon
    if complete and name == "lateral_force" and len(candidates) != 100:
        raise ValueError("full force pulse evidence incomplete")
    if exposed:
        status = "EXPOSED_COMPLETE" if complete else "EXPOSED_STOP"
    else:
        status = "NOT_EXPOSED_HORIZON" if complete else "PRE_EXPOSURE_STOP"
    return {
        "paired_baseline_sha256": baseline_sha256,
        "paired_prefix_through_tick": end - 1,
        "paired_prefix_maximum_difference": prefix_maximum,
        "paired_prefix_valid": prefix_valid,
        "payload_packets_independently_checked": packets,
        "card_setting_observed": setting_seen,
        "actual_exposure_observed": exposed,
        "first_confirmed_exposure_state_tick": min(confirmed) if confirmed else None,
        "exposure_status": status,
        "effective_complete_horizon": complete and exposed and prefix_valid,
        "metric_scope": "whole_episode_operational; no recovery_time_or_post6s_claim",
    }
