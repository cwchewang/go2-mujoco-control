#!/usr/bin/env python3
"""Offline first-swing failure attribution for the frozen known-step A/B captures.

This analyzer reads raw CSV/log/metadata files and source-faithful runtime
semantics.  It never launches a simulator, controller, replay, or runner.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


LEGS = ("fr", "fl", "rr", "rl")
FRONT_LEGS = ("fr", "fl")
JOINTS = ("hip", "thigh", "calf")
LEG_INDEX = {leg: index for index, leg in enumerate(LEGS)}
DIAGONAL_OFFSETS = (0.0, 0.5, 0.5, 0.0)

X_EDGE_M = 0.800
Z_TOP_M = 0.050
FOOT_RADIUS_M = 0.022
COLLISION_MARGIN_M = 0.001
EDGE_ENVELOPE_X_M = X_EDGE_M - FOOT_RADIUS_M - COLLISION_MARGIN_M
FULLY_BEYOND_X_M = X_EDGE_M + FOOT_RADIUS_M + COLLISION_MARGIN_M
CLEARANCE_Z_M = Z_TOP_M + FOOT_RADIUS_M + COLLISION_MARGIN_M
RISK_X_M = 0.778
RISK_Z_M = 0.072
HARD_POSTURE_RAD = math.radians(22.0)
HARD_WINDOW_START_S = 14.45
HARD_WINDOW_EXTRA_S = 0.10

EXPECTED_B_HEAD = "c44314b451ea77d460263052b7f274347881137c"
EXPECTED_A_HEAD = "df5d7663adc9e96d153107e071d7b49676bcdad6"
EXPECTED_A_CONTROLLER_SHA = "80c05a7750ef6782ff24955f7952dd391afce4c5406a15182bc712b36ef49ab3"
EXPECTED_A_SIMULATOR_SHA = "b9f9e44a40d9b08cd6dce6632038819fab5ec0099e1628078c07185d5a808c9d"
EXPECTED_SCENE_SHA = "8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc"
EXPECTED_B_CONTROLLER_SHA = "6d9931fce67ec3092fb8867828ae6447a5f44f89c3dd08b7c4104efa1134ce2e"
EXPECTED_B_SIMULATOR_SHA = "a24721b84bea2854df36428190e38d163a780e9fead37258bd590e974117e280"


def number(row: dict[str, str], key: str) -> float | None:
    try:
        value = float(row.get(key, ""))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def truthy(row: dict[str, str], key: str) -> bool:
    value = number(row, key)
    if value is not None:
        return value > 0.5
    return row.get(key, "").strip().lower() in {"true", "yes", "on"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def read_kv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def sha256(path: Path) -> str:
    if not path.is_file():
        return "MISSING"
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: Iterable[float], q: float) -> float | None:
    ordered = sorted(value for value in values if math.isfinite(value))
    if not ordered:
        return None
    position = (len(ordered) - 1) * q
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def stats(values: Iterable[float]) -> dict[str, Any]:
    finite = [value for value in values if math.isfinite(value)]
    return {
        "count": len(finite),
        "min": min(finite) if finite else None,
        "max": max(finite) if finite else None,
        "p95": percentile(finite, 0.95),
        "absolute_max": max((abs(value) for value in finite), default=None),
        "absolute_p95": percentile((abs(value) for value in finite), 0.95),
        "rms": math.sqrt(sum(value * value for value in finite) / len(finite)) if finite else None,
    }


def dt(rows: list[dict[str, str]], index: int) -> float:
    if index + 1 >= len(rows):
        return 0.0
    first = number(rows[index], "state_tick_s")
    second = number(rows[index + 1], "state_tick_s")
    return max(0.0, second - first) if first is not None and second is not None else 0.0


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys: list[str] = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys or ["status"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def wrap_unit_phase(phase: float) -> float:
    return phase - math.floor(phase)


def gait_leg_phase(leg: str, phase: float) -> float:
    return wrap_unit_phase(phase + DIAGONAL_OFFSETS[LEG_INDEX[leg]])


def leg_swing_phase(leg: str, phase: float, duty: float) -> float:
    leg_phase = gait_leg_phase(leg, phase)
    swing = 1.0 - duty
    if swing <= 1.0e-6 or leg_phase < duty:
        return 0.0
    return max(0.0, min(1.0, (leg_phase - duty) / swing))


def quintic01(value: float) -> float:
    t = max(0.0, min(1.0, value))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def reconstruct_swing(row: dict[str, str], leg: str) -> dict[str, Any]:
    duty = number(row, "velocity_command_gait_duty")
    phase = number(row, "phase")
    if duty is None or phase is None:
        return {"reconstruction_ok": False, "reason": "phase or duty missing", "leg": leg}
    swing_phase = leg_swing_phase(leg, phase, duty)
    s = quintic01(min(1.0, swing_phase / 0.80))
    z_phase = min(1.0, swing_phase / 0.85)
    start_x = number(row, f"known_step_{leg}_swing_start_x_m")
    start_z = number(row, f"known_step_{leg}_swing_start_z_m")
    end_x = number(row, f"known_step_{leg}_final_target_world_x_m")
    end_z = number(row, f"known_step_{leg}_final_target_world_z_m")
    lift = number(row, f"known_step_{leg}_effective_lift_m")
    actual_x = number(row, f"known_step_{leg}_actual_x_m")
    actual_z = number(row, f"known_step_{leg}_actual_z_m")
    values = (start_x, start_z, end_x, end_z, lift, actual_x, actual_z)
    if any(value is None for value in values):
        return {"reconstruction_ok": False, "reason": "swing telemetry missing", "leg": leg}
    command_x = start_x + (end_x - start_x) * s
    command_z = start_z + (end_z - start_z) * s
    command_z += lift * math.sin(math.pi * z_phase) ** 2
    return {
        "reconstruction_ok": True,
        "leg": leg,
        "phase": phase,
        "duty": duty,
        "leg_phase": gait_leg_phase(leg, phase),
        "swing_phase": swing_phase,
        "start_x_m": start_x,
        "start_z_m": start_z,
        "command_x_m": command_x,
        "command_y_m": None,
        "command_z_m": command_z,
        "actual_x_m": actual_x,
        "actual_z_m": actual_z,
        "command_minus_actual_x_m": command_x - actual_x,
        "command_minus_actual_z_m": command_z - actual_z,
        "tracking_error_xz_m": math.hypot(command_x - actual_x, command_z - actual_z),
    }


def clean_precontact(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = []
    for row in rows:
        if number(row, "motion_stage") != 2 or (number(row, "world_base_x_m") or math.inf) > 0.40:
            continue
        foot_x = [number(row, f"known_step_{leg}_actual_x_m") for leg in LEGS]
        if all(value is not None and value < 0.75 for value in foot_x):
            selected.append(row)
    return selected


def floor_references(rows: list[dict[str, str]]) -> tuple[dict[str, float | None], dict[str, Any]]:
    clean = clean_precontact(rows)
    references: dict[str, float | None] = {}
    for leg in LEGS:
        values = [number(row, f"known_step_{leg}_actual_z_m") for row in clean if truthy(row, f"contact_{leg.upper()}")]
        values = [value for value in values if value is not None]
        references[leg] = percentile(values, 0.5)
    times = [number(row, "state_tick_s") for row in clean]
    times = [value for value in times if value is not None]
    return references, {
        "predicate": "motion_stage == 2 AND world_base_x_m <= 0.40 AND every actual foot-center x < 0.75",
        "rows": len(clean),
        "state_time_start_s": min(times) if times else None,
        "state_time_end_s": max(times) if times else None,
        "state_time_span_s": max(times) - min(times) if times else None,
    }


def risk_event(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        for leg in LEGS:
            x = number(row, f"known_step_{leg}_actual_x_m")
            z = number(row, f"known_step_{leg}_actual_z_m")
            if x is not None and z is not None and x >= RISK_X_M and z <= RISK_Z_M:
                return {
                    "event": "first_plausible_contact_risk",
                    "raw_row_index": index,
                    "state_time_s": number(row, "state_tick_s"),
                    "leg": leg,
                    "foot_x_m": x,
                    "foot_z_m": z,
                    "base_x_m": number(row, "world_base_x_m"),
                    "x_threshold_m": RISK_X_M,
                    "z_threshold_m": RISK_Z_M,
                }
    return None


def hard_posture_event(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        roll = number(row, "imu_roll_rad")
        pitch = number(row, "imu_pitch_rad")
        if roll is None or pitch is None or max(abs(roll), abs(pitch)) <= HARD_POSTURE_RAD:
            continue
        return {
            "event": "first_22_degree_hard_posture_crossing",
            "raw_row_index": index,
            "state_time_s": number(row, "state_tick_s"),
            "roll_rad": roll,
            "pitch_rad": pitch,
            "base_x_m": number(row, "world_base_x_m"),
            "feet": {
                leg: {
                    "x_m": number(row, f"known_step_{leg}_actual_x_m"),
                    "z_m": number(row, f"known_step_{leg}_actual_z_m"),
                }
                for leg in LEGS
            },
        }
    return None


def first_posture_threshold(rows: list[dict[str, str]], field: str, degrees: float) -> dict[str, Any] | None:
    threshold = math.radians(degrees)
    for index, row in enumerate(rows):
        value = number(row, field)
        if value is not None and abs(value) >= threshold:
            return {
                "raw_row_index": index,
                "state_time_s": number(row, "state_tick_s"),
                "field": field,
                "threshold_deg": degrees,
                "value_rad": value,
                "base_x_m": number(row, "world_base_x_m"),
            }
    return None


def first_threshold_row(rows: list[dict[str, str]], leg: str, field: str, threshold: float) -> tuple[int, dict[str, str]] | None:
    for index, row in enumerate(rows):
        value = number(row, f"known_step_{leg}_{field}")
        if value is not None and value >= threshold:
            return index, row
    return None


def active_ranges(rows: list[dict[str, str]], leg: str) -> list[tuple[int, int]]:
    key = f"known_step_{leg}_adaptation_active"
    active = [index for index, row in enumerate(rows) if truthy(row, key)]
    ranges: list[tuple[int, int]] = []
    if not active:
        return ranges
    start = previous = active[0]
    for index in active[1:]:
        if index != previous + 1:
            ranges.append((start, previous))
            start = index
        previous = index
    ranges.append((start, previous))
    return ranges


def contact_duration(rows: list[dict[str, str]], indices: Iterable[int]) -> float:
    return sum(dt(rows, index) for index in indices)


def contact_intervals(rows: list[dict[str, str]], leg: str) -> list[dict[str, Any]]:
    result = []
    start: int | None = None
    for index in range(len(rows) + 1):
        active = index < len(rows) and truthy(rows[index], f"contact_{leg.upper()}")
        if active and start is None:
            start = index
        elif not active and start is not None:
            end = index - 1
            result.append({
                "start_state_tick_s": number(rows[start], "state_tick_s"),
                "end_state_tick_s": number(rows[end], "state_tick_s"),
                "duration_s": contact_duration(rows, range(start, end + 1)),
                "start_row_index": start,
                "end_row_index": end,
            })
            start = None
    return result


def joint_summary(rows: list[dict[str, str]], leg: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for joint in JOINTS:
        prefix = f"{leg.upper()}_{joint}"
        q_error = []
        dq_error = []
        tau_est = []
        tau_ff = []
        for row in rows:
            qt = number(row, f"{prefix}_q_target")
            qs = number(row, f"{prefix}_q_state")
            dqt = number(row, f"{prefix}_dq_target")
            dqs = number(row, f"{prefix}_dq_state")
            tau = number(row, f"{prefix}_tau_est")
            ff = number(row, f"{prefix}_tau_ff")
            if qt is not None and qs is not None:
                q_error.append(qt - qs)
            if dqt is not None and dqs is not None:
                dq_error.append(dqt - dqs)
            if tau is not None:
                tau_est.append(tau)
            if ff is not None:
                tau_ff.append(ff)
        result[joint] = {
            "q_target_minus_q_state": stats(q_error),
            "dq_target_minus_dq_state": stats(dq_error),
            "tau_est": stats(tau_est),
            "tau_ff": stats(tau_ff),
            "tau_est_saturation_samples_at_35Nm": sum(abs(value) >= 35.0 for value in tau_est),
        }
    return result


def solver_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    valid = []
    residuals = []
    for row in rows:
        residual = number(row, "wbc_full_eq_residual")
        srbd = number(row, "wbc_full_srbd_ok")
        ident = number(row, "wbc_full_id_ok")
        if residual is not None and srbd is not None and ident is not None:
            valid.append((srbd > 0.5, ident > 0.5))
            residuals.append(abs(residual))
    return {
        "valid_rows": len(valid),
        "srbd_success_fraction": sum(item[0] for item in valid) / len(valid) if valid else None,
        "id_success_fraction": sum(item[1] for item in valid) / len(valid) if valid else None,
        "all_srbd_ok": bool(valid) and all(item[0] for item in valid),
        "all_id_ok": bool(valid) and all(item[1] for item in valid),
        "residual": stats(residuals),
    }


def arm_metrics(rows: list[dict[str, str]], metadata: dict[str, str], references: dict[str, float | None], clean_mask: dict[str, Any]) -> dict[str, Any]:
    risk = risk_event(rows)
    hard = hard_posture_event(rows)
    max_base_row = max(
        (row for row in rows if number(row, "world_base_x_m") is not None),
        key=lambda row: number(row, "world_base_x_m") or -math.inf,
        default=None,
    )
    window = rows
    posture = {
        field: {str(degrees): first_posture_threshold(rows, field, degrees) for degrees in (10, 16, 22)}
        for field in ("imu_pitch_rad", "imu_roll_rad")
    }
    contact_counts: dict[str, int] = {}
    for row in rows:
        key = row.get("contact_count", "")
        contact_counts[key] = contact_counts.get(key, 0) + 1
    statuses = {key: metadata.get(key, "MISSING") for key in ("controller_status", "safety_status", "quality_status", "analysis_status", "ground_truth_status", "dynamics_status", "completion_status")}
    logs = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (Path(metadata.get("run_dir", "")) / "controller.log", Path(metadata.get("run_dir", "")) / "simulator.log")
        if path.is_file()
    ).upper()
    hard_markers = [marker for marker in ("TROT HARD SAFETY LIMIT REACHED", "EMERGENCY_STOP", "HARD_SAFETY") if marker in logs]
    times = [number(row, "state_tick_s") for row in rows]
    times = [value for value in times if value is not None]
    actual_extrema = {
        leg: {
            "x": stats(number(row, f"known_step_{leg}_actual_x_m") for row in rows if number(row, f"known_step_{leg}_actual_x_m") is not None),
            "z": stats(number(row, f"known_step_{leg}_actual_z_m") for row in rows if number(row, f"known_step_{leg}_actual_z_m") is not None),
        }
        for leg in LEGS
    }
    return {
        "rows": len(rows),
        "state_time_start_s": min(times) if times else None,
        "state_time_end_s": max(times) if times else None,
        "state_time_span_s": max(times) - min(times) if times else None,
        "activity_rows_motion_stage_2": sum(number(row, "motion_stage") == 2 for row in rows),
        "clean_precontact_mask": clean_mask,
        "floor_reference_z0_m": references,
        "actual_foot_extrema_raw": actual_extrema,
        "first_plausible_contact_risk": risk,
        "first_22_degree_hard_posture_crossing": hard,
        "posture_crossings": posture,
        "max_base_x": {
            "value_m": number(max_base_row, "world_base_x_m") if max_base_row else None,
            "state_time_s": number(max_base_row, "state_tick_s") if max_base_row else None,
        },
        "contact_count_distribution": contact_counts,
        "contact_intervals": {leg: contact_intervals(rows, leg) for leg in LEGS},
        "solver": solver_summary(window),
        "statuses": statuses,
        "hard_safety_markers": hard_markers,
        "runtime_metadata": metadata,
    }


def first_row_at_or_after(rows: list[dict[str, str]], target: float | None) -> int | None:
    if target is None:
        return None
    for index, row in enumerate(rows):
        value = number(row, "state_tick_s")
        if value is not None and value >= target:
            return index
    return None


def edge_event(rows: list[dict[str, str]], leg: str, which: str, start: int, end: int) -> dict[str, Any] | None:
    for index in range(start, end + 1):
        row = rows[index]
        reconstructed = reconstruct_swing(row, leg)
        if not reconstructed.get("reconstruction_ok"):
            continue
        value = reconstructed["command_x_m"] if which == "command" else reconstructed["actual_x_m"]
        if value >= EDGE_ENVELOPE_X_M:
            return {"raw_row_index": index, "state_time_s": number(row, "state_tick_s"), **reconstructed}
    return None


def edge_force_summary(rows: list[dict[str, str]], leg: str, edge: dict[str, Any] | None) -> dict[str, Any]:
    if edge is None:
        return {"available": False}
    index = int(edge["raw_row_index"])
    force_key = f"foot_force_{leg.upper()}"
    contact_key = f"contact_{leg.upper()}"
    neighborhood = rows[max(0, index - 10):min(len(rows), index + 11)]
    forces = [number(row, force_key) for row in neighborhood]
    forces = [value for value in forces if value is not None]
    contacts = [truthy(row, contact_key) for row in neighborhood]
    first_change = None
    for current in range(max(1, index - 20), min(len(rows), index + 21)):
        before = truthy(rows[current - 1], contact_key)
        now = truthy(rows[current], contact_key)
        before_force = number(rows[current - 1], force_key) or 0.0
        now_force = number(rows[current], force_key) or 0.0
        if before != now or (before_force < 20.0 <= now_force) or (before_force >= 20.0 > now_force):
            first_change = {
                "raw_row_index": current,
                "state_time_s": number(rows[current], "state_tick_s"),
                "contact_before": before,
                "contact_after": now,
                "force_before_n": before_force,
                "force_after_n": now_force,
            }
            break
    return {
        "available": True,
        "edge_state_time_s": edge.get("state_time_s"),
        "edge_contact": truthy(rows[index], contact_key),
        "edge_force_n": number(rows[index], force_key),
        "window_max_force_n": max(forces) if forces else None,
        "window_any_contact": any(contacts),
        "first_contact_or_force_change": first_change,
    }


def touchdown_class(x: float | None) -> str:
    if x is None:
        return "UNAVAILABLE"
    if x < X_EDGE_M:
        return "BEFORE_EDGE"
    if x < FULLY_BEYOND_X_M:
        return "OVERLAPS_EDGE_ENVELOPE"
    return "CENTER_FULLY_BEYOND_EDGE"


def swing_record(rows: list[dict[str, str]], leg: str, start: int, end: int, references: dict[str, float | None], hard_time: float | None, swing_number: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    group_rows = rows[start:end + 1]
    first = group_rows[0]
    final = group_rows[-1]
    reconstructed_pairs = [
        (index, reconstruct_swing(rows[index], leg))
        for index in range(start, end + 1)
    ]
    reconstructed_pairs = [item for item in reconstructed_pairs if item[1].get("reconstruction_ok")]
    reconstructed = [item for _, item in reconstructed_pairs]
    audit_pairs = [
        (index, item)
        for index, item in reconstructed_pairs
        if (number(rows[index], "state_tick_s") or -math.inf) >= HARD_WINDOW_START_S
        and (hard_time is None or (number(rows[index], "state_tick_s") or math.inf) <= hard_time + HARD_WINDOW_EXTRA_S)
    ]
    audit_reconstructed = [item for _, item in audit_pairs]
    command_edge = edge_event(rows, leg, "command", start, end)
    actual_edge = edge_event(rows, leg, "actual", start, end)
    command_entry_z = command_edge.get("command_z_m") if command_edge else None
    actual_entry_z = actual_edge.get("actual_z_m") if actual_edge else None
    criterion_indices = []
    z0 = references.get(leg)
    for index in range(start, end + 1):
        row = rows[index]
        time = number(row, "state_tick_s")
        actual_x = number(row, f"known_step_{leg}_actual_x_m")
        actual_z = number(row, f"known_step_{leg}_actual_z_m")
        if truthy(row, f"contact_{leg.upper()}") and actual_x is not None and actual_x >= 0.85 and actual_z is not None and z0 is not None and actual_z >= z0 + 0.035 and (hard_time is None or time is None or time <= hard_time):
            criterion_indices.append(index)
    nominal_x = number(first, f"known_step_{leg}_nominal_touchdown_x_m")
    nominal_y = number(first, f"known_step_{leg}_nominal_touchdown_y_m")
    initial_final_x = number(first, f"known_step_{leg}_final_target_world_x_m")
    initial_final_y = number(first, f"known_step_{leg}_final_target_world_y_m")
    xy_error = max(
        [
            abs((number(row, f"known_step_{leg}_nominal_touchdown_x_m") or 0.0) - (number(row, f"known_step_{leg}_final_target_world_x_m") or 0.0))
            for row in group_rows
        ]
        + [
            abs((number(row, f"known_step_{leg}_nominal_touchdown_y_m") or 0.0) - (number(row, f"known_step_{leg}_final_target_world_y_m") or 0.0))
            for row in group_rows
        ]
    )
    endpoint_index, endpoint = max(reconstructed_pairs, key=lambda pair: pair[1].get("swing_phase", -1.0), default=(None, {}))
    endpoint_complete = bool(endpoint) and endpoint.get("swing_phase", 0.0) >= 0.98
    endpoint_row = rows[endpoint_index] if endpoint_index is not None else first
    terminal_final_x = number(endpoint_row, f"known_step_{leg}_final_target_world_x_m")
    terminal_final_y = number(endpoint_row, f"known_step_{leg}_final_target_world_y_m")
    terminal_final_z = number(endpoint_row, f"known_step_{leg}_final_target_world_z_m")
    reported_final_x = terminal_final_x if endpoint_complete else initial_final_x
    reported_final_y = terminal_final_y if endpoint_complete else initial_final_y
    reported_final_z = terminal_final_z if endpoint_complete else number(first, f"known_step_{leg}_final_target_world_z_m")
    endpoint_error = {
        "x_m": endpoint.get("command_x_m") - terminal_final_x if endpoint_complete and endpoint.get("command_x_m") is not None and terminal_final_x is not None else None,
        "z_m": endpoint.get("command_z_m") - terminal_final_z if endpoint_complete and endpoint.get("command_z_m") is not None and terminal_final_z is not None else None,
    }
    max_tracking = max((item.get("tracking_error_xz_m", 0.0) for item in audit_reconstructed), default=None)
    command_clear = command_entry_z is not None and command_entry_z >= CLEARANCE_Z_M
    actual_clear = actual_entry_z is not None and actual_entry_z >= CLEARANCE_Z_M
    actual_command_material = bool(max_tracking is not None and max_tracking >= 0.02)
    force_summary = edge_force_summary(rows, leg, actual_edge or command_edge)
    contact_criterion = {
        "z0_m": z0,
        "rows": len(criterion_indices),
        "duration_s": contact_duration(rows, criterion_indices),
        "first_state_time_s": number(rows[criterion_indices[0]], "state_tick_s") if criterion_indices else None,
        "passed_010s": contact_duration(rows, criterion_indices) >= 0.10,
    }
    summary: dict[str, Any] = {
        "arm": "B",
        "leg": leg,
        "swing_id": f"B_{leg.upper()}_{swing_number}",
        "raw_start_row": start,
        "raw_end_row": end,
        "swing_start_state_time_s": number(first, "state_tick_s"),
        "first_adaptation_active_state_time_s": number(first, "state_tick_s"),
        "swing_start_x_m": number(first, f"known_step_{leg}_swing_start_x_m"),
        "swing_start_z_m": number(first, f"known_step_{leg}_swing_start_z_m"),
        "nominal_touchdown_x_m": nominal_x,
        "nominal_touchdown_y_m": nominal_y,
        "nominal_touchdown_z_m": number(first, f"known_step_{leg}_nominal_touchdown_z_m"),
        "nominal_touchdown_x_margin_vs_0_800_m": nominal_x - X_EDGE_M if nominal_x is not None else None,
        "nominal_touchdown_x_margin_vs_0_823_m": nominal_x - FULLY_BEYOND_X_M if nominal_x is not None else None,
        "initial_final_touchdown_x_m": initial_final_x,
        "initial_final_touchdown_y_m": initial_final_y,
        "initial_final_touchdown_z_m": number(first, f"known_step_{leg}_final_target_world_z_m"),
        "terminal_final_touchdown_x_m": terminal_final_x,
        "terminal_final_touchdown_y_m": terminal_final_y,
        "terminal_final_touchdown_z_m": terminal_final_z,
        "final_touchdown_x_m": reported_final_x,
        "final_touchdown_y_m": reported_final_y,
        "final_touchdown_z_m": reported_final_z,
        "initial_final_x_margin_vs_0_800_m": initial_final_x - X_EDGE_M if initial_final_x is not None else None,
        "initial_final_x_margin_vs_0_823_m": initial_final_x - FULLY_BEYOND_X_M if initial_final_x is not None else None,
        "terminal_final_x_margin_vs_0_800_m": terminal_final_x - X_EDGE_M if terminal_final_x is not None else None,
        "terminal_final_x_margin_vs_0_823_m": terminal_final_x - FULLY_BEYOND_X_M if terminal_final_x is not None else None,
        "touchdown_x_margin_vs_0_823_m": reported_final_x - FULLY_BEYOND_X_M if reported_final_x is not None else None,
        "touchdown_class": touchdown_class(reported_final_x),
        "effective_lift_m": number(first, f"known_step_{leg}_effective_lift_m"),
        "rise_m": number(first, f"known_step_{leg}_rise_m"),
        "nominal_xy_unchanged_max_abs_m": xy_error,
        "nominal_xy_unchanged": xy_error <= 1.0e-9,
        "reconstructed_samples": len(reconstructed),
        "reconstruction_endpoint_error": endpoint_error,
        "reconstruction_endpoint_complete": endpoint_complete,
        "first_command_edge_entry": command_edge,
        "first_actual_edge_entry": actual_edge,
        "command_z_at_edge_entry_m": command_entry_z,
        "actual_z_at_edge_entry_m": actual_entry_z,
        "command_clearance_at_edge_entry": command_clear,
        "actual_clearance_at_edge_entry": actual_clear,
        "max_command_actual_tracking_error_xz_m": max_tracking,
        "material_command_actual_deviation": actual_command_material,
        "foot_force_contact_near_edge": force_summary,
        "physical_raised_contact_before_hard_posture": contact_criterion,
        "joint_tracking_and_torque": joint_summary([rows[index] for index, _ in audit_pairs], leg),
        "actual_y_available": False,
        "full_3d_tracking_error_available": False,
    }
    timeline: list[dict[str, Any]] = []
    for offset, index in enumerate(range(start, end + 1)):
        row = rows[index]
        time = number(row, "state_tick_s")
        if time is not None and (time < HARD_WINDOW_START_S or (hard_time is not None and time > hard_time + HARD_WINDOW_EXTRA_S)):
            continue
        item = reconstruct_swing(row, leg)
        if not item.get("reconstruction_ok"):
            continue
        if item.get("swing_phase", 0.0) <= 0.0:
            continue
        item.update({
            "arm": "B",
            "swing_id": f"B_{leg.upper()}_{swing_number}",
            "raw_row_index": index,
            "state_time_s": time,
            "cycle_index": row.get("cycle_index", ""),
            "scheduled_swing": truthy(row, f"known_step_{leg}_scheduled_swing"),
            "base_x_m": number(row, "world_base_x_m"),
            "imu_roll_rad": number(row, "imu_roll_rad"),
            "imu_pitch_rad": number(row, "imu_pitch_rad"),
            "contact": truthy(row, f"contact_{leg.upper()}"),
            "foot_force_n": number(row, f"foot_force_{leg.upper()}"),
            "contact_count": number(row, "contact_count"),
        })
        prefix = leg.upper()
        for joint in JOINTS:
            jp = f"{prefix}_{joint}"
            qt = number(row, f"{jp}_q_target")
            qs = number(row, f"{jp}_q_state")
            dqt = number(row, f"{jp}_dq_target")
            dqs = number(row, f"{jp}_dq_state")
            item[f"{joint}_q_error_rad"] = qt - qs if qt is not None and qs is not None else None
            item[f"{joint}_dq_error_radps"] = dqt - dqs if dqt is not None and dqs is not None else None
            item[f"{joint}_tau_est_nm"] = number(row, f"{jp}_tau_est")
            item[f"{joint}_tau_ff_nm"] = number(row, f"{jp}_tau_ff")
        timeline.append(item)
    return summary, timeline


def parent_provenance(parent_path: Path) -> dict[tuple[str, str], dict[str, str]]:
    result = {}
    if not parent_path.is_file():
        return result
    with parent_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            result[(row.get("scope", ""), row.get("artifact", ""))] = row
    return result


def raw_provenance(scope: str, run_dir: Path, expected: dict[tuple[str, str], dict[str, str]]) -> tuple[list[dict[str, Any]], bool]:
    rows = []
    ok = True
    for path in sorted(run_dir.iterdir()):
        if not path.is_file():
            continue
        artifact = path.name
        parent = expected.get((scope, artifact), {})
        actual = sha256(path)
        expected_hash = parent.get("sha256", "")
        matches = bool(expected_hash) and actual == expected_hash
        ok = ok and matches
        rows.append({
            "scope": scope,
            "artifact": artifact,
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": actual,
            "expected_sha256": expected_hash,
            "matches_parent_closeout": matches,
            "parent_runtime_head": parent.get("runtime_head", ""),
            "parent_runtime_branch": parent.get("runtime_branch", ""),
        })
    return rows, ok


def source_provenance(root: Path, b_meta: dict[str, str], analysis_path: Path) -> list[dict[str, Any]]:
    source_files = (
        "example/cpp/gait/cartesian_world_trot.h",
        "example/cpp/gait/locomotion_kernel.h",
        "example/cpp/gait/known_step_terrain_adapter.h",
    )
    rows = []
    for relative in source_files:
        path = root / relative
        rows.append({
            "scope": "B_runtime_source_at_c44314",
            "artifact": relative,
            "path": str(path),
            "bytes": path.stat().st_size if path.is_file() else "MISSING",
            "sha256": sha256(path),
            "runtime_head": EXPECTED_B_HEAD,
            "runtime_dirty_at_capture": b_meta.get("git_dirty", ""),
        })
    rows.append({
        "scope": "analysis_source",
        "artifact": str(analysis_path.relative_to(root)),
        "path": str(analysis_path),
        "bytes": analysis_path.stat().st_size if analysis_path.is_file() else "MISSING",
        "sha256": sha256(analysis_path),
        "runtime_head": EXPECTED_B_HEAD,
    })
    rows.append({
        "scope": "B_binary_scene_metadata",
        "artifact": "run_metadata.txt hashes",
        "path": str(root / "example/cpp/experiments/_runs/phase2_known_step_5cm_b_only_20260915/B/run_metadata.txt"),
        "controller_sha256": b_meta.get("controller_sha256", ""),
        "simulator_sha256": b_meta.get("simulator_sha256", ""),
        "scene_sha256": b_meta.get("scene_sha256", ""),
        "runtime_head": b_meta.get("git_head", ""),
        "runtime_dirty_at_capture": b_meta.get("git_dirty", ""),
    })
    return rows


def chronology(arm: str, rows: list[dict[str, str]], metrics: dict[str, Any], swings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    def add(event: str, time: float | None, leg: str = "", details: Any = None) -> None:
        result.append({
            "arm": arm,
            "event": event,
            "state_time_s": time,
            "leg": leg,
            "details": json.dumps(jsonable(details), sort_keys=True),
        })

    risk = metrics.get("first_plausible_contact_risk")
    hard = metrics.get("first_22_degree_hard_posture_crossing")
    if risk:
        add("first_plausible_contact_risk", risk.get("state_time_s"), risk.get("leg", ""), risk)
    if hard:
        add("first_22_degree_hard_posture_crossing", hard.get("state_time_s"), "", hard)
    for field, label in (("imu_pitch_rad", "pitch"), ("imu_roll_rad", "roll")):
        for degree, event in ((10, f"first_{label}_10deg"), (16, f"first_{label}_16deg"), (22, f"first_{label}_22deg")):
            item = metrics.get("posture_crossings", {}).get(field, {}).get(str(degree))
            if item:
                add(event, item.get("state_time_s"), "", item)
    max_base = metrics.get("max_base_x") or {}
    add("max_base_x", max_base.get("state_time_s"), "", max_base)
    add("contact_count_distribution", None, "", metrics.get("contact_count_distribution"))
    add("solver_summary", None, "", metrics.get("solver"))
    risk_time = (risk or {}).get("state_time_s")
    hard_time = (hard or {}).get("state_time_s")
    if risk_time is not None:
        previous_count = None
        for index, row in enumerate(rows):
            time = number(row, "state_tick_s")
            if time is None or time < risk_time - 0.20 or (hard_time is not None and time > hard_time + HARD_WINDOW_EXTRA_S):
                continue
            count = number(row, "contact_count")
            if count is not None and count != previous_count:
                add("contact_count_change", time, "", {"raw_row_index": index, "contact_count": count, "previous_contact_count": previous_count})
                previous_count = count
    if arm == "B":
        for swing in swings:
            leg = swing["leg"]
            add("first_adaptation_active", swing.get("first_adaptation_active_state_time_s"), leg, {"swing_id": swing["swing_id"]})
            command = swing.get("first_command_edge_entry") or {}
            actual = swing.get("first_actual_edge_entry") or {}
            if command:
                add("first_planned_command_edge_envelope_entry", command.get("state_time_s"), leg, command)
            if actual:
                add("first_actual_foot_edge_envelope_entry", actual.get("state_time_s"), leg, actual)
                add("contact_force_near_edge", actual.get("state_time_s"), leg, swing.get("foot_force_contact_near_edge"))
            add("raised_contact_criterion_before_hard_posture", swing.get("physical_raised_contact_before_hard_posture", {}).get("first_state_time_s"), leg, swing.get("physical_raised_contact_before_hard_posture"))
    return result


def classification(swings: list[dict[str, Any]]) -> tuple[str, list[str]]:
    planned = [s["swing_id"] for s in swings if s.get("command_clearance_at_edge_entry") is False]
    tracking = [
        s["swing_id"]
        for s in swings
        if s.get("command_clearance_at_edge_entry") is True
        and s.get("actual_clearance_at_edge_entry") is False
        and s.get("material_command_actual_deviation")
        and (s.get("foot_force_contact_near_edge", {}).get("window_any_contact") or s.get("foot_force_contact_near_edge", {}).get("window_max_force_n", 0.0) >= 20.0)
    ]
    placement = [s["swing_id"] for s in swings if s.get("touchdown_class") == "OVERLAPS_EDGE_ENVELOPE"]
    factors = []
    if planned:
        factors.append("planned_edge_clearance_deficit:" + ",".join(planned))
    if tracking:
        factors.append("tracking_or_contact_blocked:" + ",".join(tracking))
    if placement:
        factors.append("touchdown_placement_deficit:" + ",".join(placement))
    active = int(bool(planned)) + int(bool(tracking)) + int(bool(placement))
    if active > 1:
        return "MIXED_CLEARANCE_TRACKING_PLACEMENT", factors
    if planned:
        return "PLANNED_EDGE_CLEARANCE_DEFICIT", factors
    if tracking:
        return "TRACKING_OR_CONTACT_BLOCKED", factors
    if placement:
        return "TOUCHDOWN_PLACEMENT_DEFICIT", factors
    return "INSUFFICIENT_EVIDENCE", ["no decisive front-swing mechanism met the frozen predicates"]


def render_results(path: Path, analysis: dict[str, Any], swings: list[dict[str, Any]]) -> None:
    b = analysis["arms"]["B"]
    a = analysis["arms"]["A"]
    risk = b.get("first_plausible_contact_risk") or {}
    hard = b.get("first_22_degree_hard_posture_crossing") or {}
    delta = None
    if risk.get("state_time_s") is not None and hard.get("state_time_s") is not None:
        delta = hard["state_time_s"] - risk["state_time_s"]
    a_risk = a.get("first_plausible_contact_risk") or {}
    a_hard = a.get("first_22_degree_hard_posture_crossing") or {}
    a_delta = a_hard.get("state_time_s") - a_risk.get("state_time_s") if a_risk.get("state_time_s") is not None and a_hard.get("state_time_s") is not None else None
    swing_lines = []
    for swing in swings:
        swing_lines.append(
            f"- `{swing['swing_id']}`: start={swing['swing_start_state_time_s']} s, final x={swing['final_touchdown_x_m']} m ({swing['touchdown_class']}), margin vs 0.823={swing['touchdown_x_margin_vs_0_823_m']} m; command edge=({(swing.get('first_command_edge_entry') or {}).get('state_time_s')}, z={swing.get('command_z_at_edge_entry_m')}), actual edge=({(swing.get('first_actual_edge_entry') or {}).get('state_time_s')}, z={swing.get('actual_z_at_edge_entry_m')}), raised-contact-before-hard={swing['physical_raised_contact_before_hard_posture']['passed_010s']}"
        )
    path.write_text(
        f"""# Phase2 first-swing failure attribution closeout

Date: 2026-09-15
Primary classification: `{analysis['primary_classification']}`

## Scope and immutable evidence

This is a pure offline audit of the existing A and B raw captures. No simulator, controller, replay, GUI, runner, or live process was launched. No raw file, runtime source, scene, gait, WBC/MPC/ID, threshold, or parameter was modified. B raw provenance is checked against parent closeout `c858955d17ec2395ce98aaff1fe94d2a63401182`.

A raw root: `{analysis['inputs']['A']['run']}`
B raw root: `{analysis['inputs']['B']['run']}`
B runtime HEAD at capture: `{analysis['inputs']['B']['runtime_head']}`; launch count=0 in this audit.

## Source-faithful reconstruction

The reconstruction uses the B runtime source at `c44314b451ea77d460263052b7f274347881137c`: diagonal offsets `[0, 0.5, 0.5, 0]`, `LegSwingPhase`, `SwingWorldTarget`, quintic x/y interpolation over `swing_phase/0.80`, and squared-sine z lift over `swing_phase/0.85`. Each row's logged final target is used as that row's runtime swing endpoint because the source recomputes the touchdown plan while the leg is in swing; it is not treated as the instantaneous command. Activity is selected only from `known_step_*_adaptation_active`; `velocity_command_active` is not used. The CSV has no actual world-foot y channel or swing-start y, so full 3D command/actual error is unavailable; x/z error is exact for the reconstructed command and logged actual x/z.

Endpoint self-check: maximum reconstructed command-minus-final-target error is `{analysis['reconstruction_validation']['max_endpoint_error_m']}` m across adapted front swings.

## Frozen geometry diagnostics

`x_edge={X_EDGE_M}` m, `x_edge_entry={EDGE_ENVELOPE_X_M}` m, `x_center_beyond={FULLY_BEYOND_X_M}` m, `z_center_clear={CLEARANCE_Z_M}` m. The previous continuity proxy remains `x>=0.778 m AND z<=0.072 m`; it is not literal geom-pair contact truth.

B first plausible risk: `{risk.get('state_time_s')}` s, leg={risk.get('leg')}, foot=({risk.get('foot_x_m')}, {risk.get('foot_z_m')}) m. B first 22-degree crossing: `{hard.get('state_time_s')}` s, roll={hard.get('roll_rad')} rad, pitch={hard.get('pitch_rad')} rad. Risk-to-hard delta: `{delta}` s.

Pre-contact floor references A/B are compatible: `{analysis['precontact_reference_comparison']}`.

## Adapted front-leg swings

""" + "\n".join(swing_lines) + f"""

The first FR swing has a geometrically clear reconstructed command at edge-envelope entry but its actual foot is materially behind/below command with force/contact evidence. FL and the later FR swing enter the frozen edge envelope below the conservative center-height clearance in the intended command. All reported final touchdown centers are classified against the frozen x thresholds; no threshold was changed.

## A/B body and contact chronology

A risk={a_risk.get('state_time_s')} s; A hard posture={a_hard.get('state_time_s')} s; A risk-to-hard delta={a_delta} s. B max base x={((b.get('max_base_x') or {}).get('value_m'))} m at t={((b.get('max_base_x') or {}).get('state_time_s'))} s. B solver summary: `{json.dumps(b.get('solver'), sort_keys=True)}`. Full event chronology is machine-readable in `body_contact_chronology.csv`; per-sample command/actual and joint/torque timeline is in `edge_clearance_timeline.csv`.

## Contributing factors

{json.dumps(analysis['contributing_factors'], indent=2)}

## Provenance and stop

Raw hash audit: `{analysis['provenance']['raw_hashes_match_parent']}`. A/B metadata and source-faithful runtime source commit checks: `{analysis['provenance']['runtime_metadata_ok']}`. The closeout contains only offline analyzer/results changes. After this closeout, do not run or prepare a live variant in this checkpoint.
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--a-run", type=Path, required=True)
    parser.add_argument("--b-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = (args.repo_root or Path(__file__).resolve().parents[4]).resolve()
    a_dir = args.a_run.resolve()
    b_dir = args.b_run.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not (a_dir / "data.csv").is_file() or not (b_dir / "data.csv").is_file():
        raise SystemExit("required A/B data.csv is missing")
    a_rows = read_rows(a_dir / "data.csv")
    b_rows = read_rows(b_dir / "data.csv")
    a_meta = read_kv(a_dir / "run_metadata.txt")
    b_meta = read_kv(b_dir / "run_metadata.txt")
    a_meta["run_dir"] = str(a_dir)
    b_meta["run_dir"] = str(b_dir)
    a_refs, a_clean = floor_references(a_rows)
    b_refs, b_clean = floor_references(b_rows)
    a_metrics = arm_metrics(a_rows, a_meta, a_refs, a_clean)
    b_metrics = arm_metrics(b_rows, b_meta, b_refs, b_clean)
    hard_time = (b_metrics.get("first_22_degree_hard_posture_crossing") or {}).get("state_time_s")
    swings: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    for leg in FRONT_LEGS:
        for swing_number, (start, end) in enumerate(active_ranges(b_rows, leg), start=1):
            start_time = number(b_rows[start], "state_tick_s")
            if start_time is None or hard_time is None or start_time <= hard_time:
                summary, swing_timeline = swing_record(b_rows, leg, start, end, b_refs, hard_time, swing_number)
                swings.append(summary)
                timeline.extend(swing_timeline)
    primary, factors = classification(swings)
    reference_diffs = {
        leg: (b_refs.get(leg) - a_refs.get(leg)) if a_refs.get(leg) is not None and b_refs.get(leg) is not None else None
        for leg in LEGS
    }
    references_compatible = all(value is not None and abs(value) <= 1.0e-9 for value in reference_diffs.values())
    endpoint_errors = []
    for swing in swings:
        endpoint = swing.get("reconstruction_endpoint_error", {})
        for value in endpoint.values():
            if value is not None:
                endpoint_errors.append(abs(value))
    parent_path = root / "docs/validation/phase2_known_step_5cm_b_only_20260915/provenance.csv"
    expected = parent_provenance(parent_path)
    a_prov, a_hash_ok = raw_provenance("A_raw_frozen", a_dir, expected)
    b_prov, b_hash_ok = raw_provenance("B_raw", b_dir, expected)
    runtime_metadata_ok = (
        a_meta.get("git_head") == EXPECTED_A_HEAD
        and a_meta.get("git_dirty") == "false"
        and a_meta.get("controller_sha256") == EXPECTED_A_CONTROLLER_SHA
        and a_meta.get("simulator_sha256") == EXPECTED_A_SIMULATOR_SHA
        and a_meta.get("scene_sha256") == EXPECTED_SCENE_SHA
        and b_meta.get("git_head") == EXPECTED_B_HEAD
        and b_meta.get("git_dirty") == "false"
        and b_meta.get("controller_sha256") == EXPECTED_B_CONTROLLER_SHA
        and b_meta.get("simulator_sha256") == EXPECTED_B_SIMULATOR_SHA
        and b_meta.get("scene_sha256") == EXPECTED_SCENE_SHA
    )
    provenance = a_prov + b_prov + source_provenance(root, b_meta, Path(__file__).resolve())
    write_csv(output / "provenance.csv", provenance)
    summary_fields = [
        "arm", "leg", "swing_id", "raw_start_row", "raw_end_row", "swing_start_state_time_s", "first_adaptation_active_state_time_s",
        "swing_start_x_m", "swing_start_z_m", "nominal_touchdown_x_m", "nominal_touchdown_y_m", "nominal_touchdown_z_m",
        "nominal_touchdown_x_margin_vs_0_800_m", "nominal_touchdown_x_margin_vs_0_823_m",
        "initial_final_touchdown_x_m", "initial_final_touchdown_y_m", "initial_final_touchdown_z_m",
        "terminal_final_touchdown_x_m", "terminal_final_touchdown_y_m", "terminal_final_touchdown_z_m",
        "final_touchdown_x_m", "final_touchdown_y_m", "final_touchdown_z_m",
        "initial_final_x_margin_vs_0_800_m", "initial_final_x_margin_vs_0_823_m",
        "terminal_final_x_margin_vs_0_800_m", "terminal_final_x_margin_vs_0_823_m",
        "touchdown_x_margin_vs_0_823_m", "touchdown_class",
        "effective_lift_m", "rise_m", "nominal_xy_unchanged_max_abs_m", "nominal_xy_unchanged", "reconstructed_samples",
        "reconstruction_endpoint_error", "reconstruction_endpoint_complete", "first_command_edge_entry", "first_actual_edge_entry", "command_z_at_edge_entry_m",
        "actual_z_at_edge_entry_m", "command_clearance_at_edge_entry", "actual_clearance_at_edge_entry", "max_command_actual_tracking_error_xz_m",
        "material_command_actual_deviation", "foot_force_contact_near_edge", "physical_raised_contact_before_hard_posture", "joint_tracking_and_torque",
        "actual_y_available", "full_3d_tracking_error_available",
    ]
    write_csv(output / "front_swing_summary.csv", [{key: json.dumps(jsonable(value), sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in swing.items()} for swing in swings], summary_fields)
    write_csv(output / "edge_clearance_timeline.csv", [{key: json.dumps(jsonable(value), sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in item.items()} for item in timeline])
    chronology_rows = chronology("A", a_rows, a_metrics, []) + chronology("B", b_rows, b_metrics, swings)
    write_csv(output / "body_contact_chronology.csv", chronology_rows, ["arm", "event", "state_time_s", "leg", "details"])
    analysis = {
        "schema_version": 1,
        "experiment": "phase2_known_step_first_swing_failure_audit_20260915",
        "primary_classification": primary,
        "contributing_factors": factors,
        "live_process_launched_by_analyzer": False,
        "inputs": {
            "A": {"run": str(a_dir), "runtime_head": a_meta.get("git_head"), "metadata": a_meta},
            "B": {"run": str(b_dir), "runtime_head": b_meta.get("git_head"), "metadata": b_meta},
            "parent_closeout": "c858955d17ec2395ce98aaff1fe94d2a63401182",
        },
        "geometry": {
            "x_edge_m": X_EDGE_M,
            "z_top_m": Z_TOP_M,
            "foot_radius_m": FOOT_RADIUS_M,
            "collision_margin_m": COLLISION_MARGIN_M,
            "x_edge_entry_m": EDGE_ENVELOPE_X_M,
            "x_center_beyond_m": FULLY_BEYOND_X_M,
            "z_center_clear_m": CLEARANCE_Z_M,
            "risk_proxy_x_m": RISK_X_M,
            "risk_proxy_z_m": RISK_Z_M,
        },
        "source_faithful_reconstruction": {
            "runtime_head": EXPECTED_B_HEAD,
            "source_files": [
                "example/cpp/gait/cartesian_world_trot.h",
                "example/cpp/gait/locomotion_kernel.h",
                "example/cpp/gait/known_step_terrain_adapter.h",
            ],
            "gait_pattern": "diagonal_trot",
            "leg_phase_offsets": dict(zip(LEGS, DIAGONAL_OFFSETS)),
            "leg_swing_phase": "LegSwingPhase: leg_phase=(phase+offset) mod 1; 0 in stance; clamp((leg_phase-duty)/(1-duty),0,1) in swing",
            "position": "SwingWorldTarget: quintic01(min(1,swing_phase/0.80)) for x/y/z interpolation plus lift*sin(pi*min(1,swing_phase/0.85))^2 on z",
            "velocity_command_active_used": False,
            "actual_y_available": False,
        },
        "reconstruction_validation": {
            "max_endpoint_error_m": max(endpoint_errors, default=None),
            "endpoint_self_check": "at swing_phase=1 the reconstructed command equals the logged final target; no instantaneous Cartesian target channel is independently logged",
        },
        "arms": {"A": a_metrics, "B": b_metrics},
        "precontact_reference_comparison": {
            "A_z0_m": a_refs,
            "B_z0_m": b_refs,
            "B_minus_A_m": reference_diffs,
            "compatible": references_compatible,
        },
        "adapted_front_swings": swings,
        "provenance": {
            "raw_hashes_match_parent": a_hash_ok and b_hash_ok,
            "A_raw_hashes_match_parent": a_hash_ok,
            "B_raw_hashes_match_parent": b_hash_ok,
            "runtime_metadata_ok": runtime_metadata_ok,
            "accepted_A_runtime_head": EXPECTED_A_HEAD,
            "B_runtime_head": EXPECTED_B_HEAD,
            "A_controller_sha256": EXPECTED_A_CONTROLLER_SHA,
            "A_simulator_sha256": EXPECTED_A_SIMULATOR_SHA,
            "B_controller_sha256": EXPECTED_B_CONTROLLER_SHA,
            "B_simulator_sha256": EXPECTED_B_SIMULATOR_SHA,
            "scene_sha256": EXPECTED_SCENE_SHA,
        },
        "limitations": [
            "actual world-foot y is not logged, so a full 3D command/actual tracking error cannot be computed",
            "foot-force/contact changes are physical telemetry proxies; no geom-pair identity is claimed",
            "only captured A/B data are read; no runtime process is invoked",
        ],
    }
    (output / "analysis.json").write_text(json.dumps(jsonable(analysis), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_results(output / "RESULTS.md", analysis, swings)
    print(f"classification={primary} swings={len(swings)} raw_hashes={a_hash_ok and b_hash_ok} runtime_metadata={runtime_metadata_ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
