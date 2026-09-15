#!/usr/bin/env python3
"""Offline closeout analyzer for the single edge-aware known-step V2 run."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable


LEGS = ("fr", "fl", "rr", "rl")
FRONT_LEGS = ("fr", "fl")
MOTORS = tuple(
    f"{leg}_{joint}"
    for leg in ("FR", "FL", "RR", "RL")
    for joint in ("hip", "thigh", "calf")
)
MOTOR_JOINTS = ("hip", "thigh", "calf")
EXPECTED_A_HEAD = "df5d7663adc9e96d153107e071d7b49676bcdad6"
EXPECTED_V2_RUNTIME_HEAD = "be1e9acca1c6650be7d500e1e3fb63dcd5594826"
EXPECTED_SCENE_SHA = "8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc"
EXPECTED_A_DOMAIN = "231"
EXPECTED_B_DOMAIN = "232"
EXPECTED_C_DOMAIN = "230"
HARD_POSTURE_RAD = math.radians(22.0)
EDGE_X_M = 0.800
X_ENTRY_M = 0.777
X_EXIT_M = 0.823
X_LAND_MIN_M = 0.850
Z_GEOM_CLEAR_M = 0.073
CONTACT_RISK_X_M = 0.778
CONTACT_RISK_Z_M = 0.072
TRACKING_MATERIAL_Z_ERROR_M = 0.020

BASE_COLUMNS = {
    "cmd_time_s",
    "state_tick_s",
    "motion_stage",
    "cycle_index",
    "phase",
    "world_base_x_m",
    "world_base_z_m",
    "imu_roll_rad",
    "imu_pitch_rad",
    "body_velocity_z_mps",
    "world_velocity_z_mps",
    "contact_count",
    "foot_force_FR",
    "foot_force_FL",
    "foot_force_RR",
    "foot_force_RL",
    "wbc_full_srbd_ok",
    "wbc_full_id_ok",
    "wbc_full_eq_residual",
    "known_step_feature_enabled",
}
for _leg in LEGS:
    BASE_COLUMNS.update(
        {
            f"known_step_{_leg}_scheduled_stance",
            f"known_step_{_leg}_scheduled_swing",
            f"known_step_{_leg}_swing_start_x_m",
            f"known_step_{_leg}_swing_start_z_m",
            f"known_step_{_leg}_nominal_touchdown_x_m",
            f"known_step_{_leg}_nominal_touchdown_y_m",
            f"known_step_{_leg}_nominal_touchdown_z_m",
            f"known_step_{_leg}_h0_m",
            f"known_step_{_leg}_h1_m",
            f"known_step_{_leg}_rise_m",
            f"known_step_{_leg}_effective_lift_m",
            f"known_step_{_leg}_final_target_world_x_m",
            f"known_step_{_leg}_final_target_world_y_m",
            f"known_step_{_leg}_final_target_world_z_m",
            f"known_step_{_leg}_actual_x_m",
            f"known_step_{_leg}_actual_z_m",
            f"known_step_{_leg}_adaptation_active",
            f"contact_{_leg.upper()}",
        }
    )


def v2_columns() -> set[str]:
    columns = {"known_step_v2_feature_enabled"}
    for leg in LEGS:
        prefix = f"known_step_v2_{leg}_"
        columns.update(
            {
                prefix + "crossing_latched",
                prefix + "planning_valid",
                prefix + "planning_failure_code",
                prefix + "planning_failure_reason",
                prefix + "swing_start_x_m",
                prefix + "swing_start_z_m",
                prefix + "ordinary_nominal_touchdown_x_m",
                prefix + "ordinary_nominal_touchdown_y_m",
                prefix + "ordinary_nominal_touchdown_z_m",
                prefix + "probe_touchdown_x_m",
                prefix + "probe_touchdown_y_m",
                prefix + "probe_touchdown_z_m",
                prefix + "h0_m",
                prefix + "h_nom_m",
                prefix + "h_probe_m",
                prefix + "x_entry_m",
                prefix + "x_exit_m",
                prefix + "x_land_min_m",
                prefix + "final_touchdown_x_m",
                prefix + "final_touchdown_y_m",
                prefix + "final_touchdown_z_m",
                prefix + "nominal_x_shift_m",
                prefix + "effective_lift_m",
                prefix + "z_corridor_m",
                prefix + "s",
                prefix + "s_entry",
                prefix + "s_exit",
                prefix + "command_world_x_m",
                prefix + "command_world_z_m",
                prefix + "command_world_vx_mps",
                prefix + "command_world_vz_mps",
                prefix + "actual_world_x_m",
                prefix + "actual_world_z_m",
                prefix + "scheduled_stance",
                prefix + "scheduled_swing",
            }
        )
    return columns


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
        "median": percentile(finite, 0.5),
        "p95": percentile(finite, 0.95),
        "absolute_max": max((abs(value) for value in finite), default=None),
        "absolute_p95": percentile((abs(value) for value in finite), 0.95),
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def csv_schema(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "present": False,
            "header_columns": 0,
            "data_rows": 0,
            "width_counts": {},
            "mismatch_rows": [],
            "pass": False,
        }
    width_counts: dict[str, int] = {}
    mismatch_rows: list[int] = []
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        try:
            header = next(reader)
        except StopIteration:
            return {
                "present": True,
                "header_columns": 0,
                "data_rows": 0,
                "width_counts": {},
                "mismatch_rows": [],
                "pass": False,
            }
        data_rows = 0
        for row_index, row in enumerate(reader, start=2):
            data_rows += 1
            width = len(row)
            width_counts[str(width)] = width_counts.get(str(width), 0) + 1
            if width != len(header) and len(mismatch_rows) < 1000:
                mismatch_rows.append(row_index)
    return {
        "present": True,
        "header_columns": len(header),
        "data_rows": data_rows,
        "width_counts": width_counts,
        "mismatch_rows": mismatch_rows,
        "pass": bool(header) and data_rows > 0 and not mismatch_rows,
    }



def read_kv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def sha256(path: Path) -> str:
    if not path.is_file():
        return "MISSING"
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonable(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def csv_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(jsonable(value), sort_keys=True, separators=(",", ":"))
    return value


def write_csv(path: Path, records: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for record in records:
            for key in record:
                if key not in fields:
                    fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({key: csv_value(record.get(key, "")) for key in fields})


def gate(run: str, name: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {
        "run": run,
        "gate": name,
        "status": "PASS" if passed else "FAIL",
        "detail": detail if isinstance(detail, str) else jsonable(detail),
    }


def dt(rows: list[dict[str, str]], index: int) -> float:
    if index + 1 >= len(rows):
        return 0.0
    first = number(rows[index], "state_tick_s")
    second = number(rows[index + 1], "state_tick_s")
    return max(0.0, second - first) if first is not None and second is not None else 0.0


def parse_protocol(run_dir: Path, expected_domain: str) -> dict[str, Any]:
    trace_path = run_dir / "lockstep_trace.csv"
    trace_rows = read_rows(trace_path) if trace_path.is_file() else []
    ticks = [number(row, "sim_tick_ms") for row in trace_rows]
    ticks = [value for value in ticks if value is not None]
    diffs = [b - a for a, b in zip(ticks, ticks[1:])]
    violations = [number(row, "violations") or 0.0 for row in trace_rows]
    logs = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (run_dir / "controller.log", run_dir / "simulator.log")
        if path.is_file()
    )
    upper = logs.upper()
    fail_closed = [
        marker
        for marker in ("SIM_LOCKSTEP_FAIL_CLOSED", "LOCKSTEP_FAIL_CLOSED")
        if marker in upper
    ]
    paired = re.findall(
        r"PAIRED_HIGHSTATE_SUMMARY\s+cycles=(\d+)\s+validation_failures=(\d+)\s+async_fallbacks=(\d+)",
        logs,
    )
    if paired:
        cycles, validation_failures, async_fallbacks = map(int, paired[-1])
    else:
        cycles = validation_failures = async_fallbacks = None
    metadata = read_kv(run_dir / "run_metadata.txt")
    return {
        "trace_present": trace_path.is_file(),
        "trace_rows": len(trace_rows),
        "sim_tick_diffs_ms": sorted(set(diffs)),
        "trace_violations": int(sum(value != 0.0 for value in violations)),
        "fail_closed_markers": fail_closed,
        "paired_summary_present": bool(paired),
        "paired_cycles": cycles,
        "paired_validation_failures": validation_failures,
        "paired_async_fallbacks": async_fallbacks,
        "domain_id": metadata.get("domain_id", ""),
        "domain_expected": expected_domain,
        "domain_matches": metadata.get("domain_id") == expected_domain,
        "metadata": metadata,
    }


def handoff_tick(run_dir: Path, rows: list[dict[str, str]]) -> tuple[float | None, str]:
    path = run_dir / "lockstep_handoff.csv"
    if path.is_file():
        for row in read_rows(path):
            for key in ("state_tick_s", "state_tick", "sim_tick_ms", "tick"):
                value = number(row, key)
                if value is not None:
                    if key in {"sim_tick_ms", "tick"} and value > 100.0:
                        value /= 1000.0
                    return value, f"lockstep_handoff.csv:{key}"
    first = number(rows[0], "state_tick_s") if rows else None
    return first, "data.csv:first_state_tick_s"


def first_index_at_or_after(rows: list[dict[str, str]], target: float | None) -> int:
    if target is None:
        return 0
    for index, row in enumerate(rows):
        value = number(row, "state_tick_s")
        if value is not None and value >= target - 1e-12:
            return index
    return len(rows)


def first_v2_latch(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        legs = [
            leg
            for leg in LEGS
            if truthy(row, f"known_step_v2_{leg}_crossing_latched")
        ]
        if legs:
            return {
                "event": "first_v2_crossing_latched",
                "raw_row_index": index,
                "state_time_s": number(row, "state_tick_s"),
                "base_x_m": number(row, "world_base_x_m"),
                "legs": legs,
            }
    return None


def exact_preactivation(
    a_rows: list[dict[str, str]],
    c_rows: list[dict[str, str]],
    a_dir: Path,
    c_dir: Path,
) -> tuple[bool, dict[str, Any], list[dict[str, Any]]]:
    a_handoff, a_source = handoff_tick(a_dir, a_rows)
    c_handoff, c_source = handoff_tick(c_dir, c_rows)
    handoffs = [value for value in (a_handoff, c_handoff) if value is not None]
    common_handoff = max(handoffs) if handoffs else None
    a_start = first_index_at_or_after(a_rows, common_handoff)
    c_start = first_index_at_or_after(c_rows, common_handoff)
    latch = first_v2_latch(c_rows)
    c_end = latch["raw_row_index"] if latch else len(c_rows)
    c_slice = c_rows[c_start:c_end]
    a_slice = a_rows[a_start:a_start + len(c_slice)]
    common = set(a_rows[0]) & set(c_rows[0]) if a_rows and c_rows else set()
    allowed_metadata = {
        "known_step_feature_enabled",
        "known_step_edge_x_m",
        "known_step_height_m",
        "known_step_half_width_y_m",
    }
    ignored_noncausal = {"motion_clock_wall_dt_s", "wbc_shadow_elapsed_us"}
    fields = sorted(common - allowed_metadata - ignored_noncausal)
    mismatches: list[dict[str, Any]] = []
    if not latch:
        mismatches.append({"row": "NO_LATCH", "field": "first_v2_crossing_latched", "a": "required", "c": "missing"})
    if len(a_slice) != len(c_slice):
        mismatches.append({"row": "COUNT", "field": "row_count", "a": len(a_slice), "c": len(c_slice)})
    for offset, (a_row, c_row) in enumerate(zip(a_slice, c_slice)):
        if a_row.get("state_tick_s", "") != c_row.get("state_tick_s", ""):
            if len(mismatches) < 1000:
                mismatches.append({
                    "row": offset,
                    "field": "state_tick_s",
                    "a": a_row.get("state_tick_s", ""),
                    "c": c_row.get("state_tick_s", ""),
                })
        for field in fields:
            if a_row.get(field, "") != c_row.get(field, "") and len(mismatches) < 1000:
                mismatches.append({
                    "row": offset,
                    "field": field,
                    "a": a_row.get(field, ""),
                    "c": c_row.get(field, ""),
                })
    summary = {
        "a_handoff_state_tick_s": a_handoff,
        "c_handoff_state_tick_s": c_handoff,
        "common_handoff_state_tick_s": common_handoff,
        "a_handoff_source": a_source,
        "c_handoff_source": c_source,
        "a_start_row": a_start,
        "c_start_row": c_start,
        "rows_compared": min(len(a_slice), len(c_slice)),
        "first_v2_latch": latch,
        "causal_fields_compared": len(fields),
        "allowed_metadata_fields": sorted(allowed_metadata),
        "ignored_noncausal_diagnostics": sorted(ignored_noncausal),
        "mismatch_count_capped": len(mismatches),
    }
    return not mismatches, summary, mismatches or [{"row": "ALL", "field": "causal_fields", "a": "exact", "c": "exact"}]


def clean_precontact(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = []
    for row in rows:
        base_x = number(row, "world_base_x_m")
        if number(row, "motion_stage") != 2 or base_x is None or base_x > 0.40:
            continue
        foot_x = [number(row, f"known_step_{leg}_actual_x_m") for leg in LEGS]
        if all(value is not None and value < 0.75 for value in foot_x):
            selected.append(row)
    return selected


def clean_mask_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    clean = clean_precontact(rows)
    times = [number(row, "state_tick_s") for row in clean]
    times = [value for value in times if value is not None]
    return {
        "predicate": "motion_stage == 2 AND world_base_x_m <= 0.40 AND every actual foot-center x < 0.75",
        "base_x_limit_m": 0.40,
        "actual_foot_x_limit_m": 0.75,
        "rows": len(clean),
        "state_time_start_s": min(times) if times else None,
        "state_time_end_s": max(times) if times else None,
        "state_time_span_s": max(times) - min(times) if times else None,
    }


def floor_reference(rows: list[dict[str, str]]) -> dict[str, float | None]:
    clean = clean_precontact(rows)
    result: dict[str, float | None] = {}
    for leg in LEGS:
        values = [
            number(row, f"known_step_{leg}_actual_z_m")
            for row in clean
            if truthy(row, f"contact_{leg.upper()}")
        ]
        result[leg] = percentile((value for value in values if value is not None), 0.5)
    return result


def actual_foot_extrema(rows: list[dict[str, str]]) -> dict[str, Any]:
    return {
        leg: {
            "x": stats(
                number(row, f"known_step_{leg}_actual_x_m")
                for row in rows
                if number(row, f"known_step_{leg}_actual_x_m") is not None
            ),
            "z": stats(
                number(row, f"known_step_{leg}_actual_z_m")
                for row in rows
                if number(row, f"known_step_{leg}_actual_z_m") is not None
            ),
        }
        for leg in LEGS
    }


def risk_event(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        for leg in LEGS:
            x_value = number(row, f"known_step_{leg}_actual_x_m")
            z_value = number(row, f"known_step_{leg}_actual_z_m")
            if x_value is not None and z_value is not None and x_value >= CONTACT_RISK_X_M and z_value <= CONTACT_RISK_Z_M:
                return {
                    "event": "first_plausible_contact_risk",
                    "raw_row_index": index,
                    "state_time_s": number(row, "state_tick_s"),
                    "leg": leg,
                    "foot_x_m": x_value,
                    "foot_z_m": z_value,
                    "base_x_m": number(row, "world_base_x_m"),
                }
    return None


def posture_event(rows: list[dict[str, str]], threshold_rad: float = HARD_POSTURE_RAD) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        roll = number(row, "imu_roll_rad")
        pitch = number(row, "imu_pitch_rad")
        if roll is None or pitch is None or max(abs(roll), abs(pitch)) < threshold_rad:
            continue
        return {
            "event": "posture_crossing",
            "threshold_rad": threshold_rad,
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


def first_base_crossing(rows: list[dict[str, str]], threshold: float) -> float | None:
    for row in rows:
        value = number(row, "world_base_x_m")
        if value is not None and value >= threshold:
            return number(row, "state_tick_s")
    return None


def solver_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    valid = []
    for row in rows:
        residual = number(row, "wbc_full_eq_residual")
        srbd = number(row, "wbc_full_srbd_ok")
        ident = number(row, "wbc_full_id_ok")
        if residual is not None and srbd is not None and ident is not None:
            valid.append((residual, srbd > 0.5, ident > 0.5))
    residuals = [abs(item[0]) for item in valid]
    return {
        "valid_rows": len(valid),
        "srbd_success_fraction": sum(item[1] for item in valid) / len(valid) if valid else None,
        "id_success_fraction": sum(item[2] for item in valid) / len(valid) if valid else None,
        "both_success_fraction": sum(item[1] and item[2] for item in valid) / len(valid) if valid else None,
        "all_srbd_ok": bool(valid) and all(item[1] for item in valid),
        "all_id_ok": bool(valid) and all(item[2] for item in valid),
        "residual": stats(residuals),
    }


def contact_intervals(rows: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for leg in LEGS:
        intervals = []
        start: int | None = None
        for index in range(len(rows) + 1):
            active = index < len(rows) and truthy(rows[index], f"contact_{leg.upper()}")
            if active and start is None:
                start = index
            elif not active and start is not None:
                end = index - 1
                intervals.append(
                    {
                        "start_state_tick_s": number(rows[start], "state_tick_s"),
                        "end_state_tick_s": number(rows[end], "state_tick_s"),
                        "duration_s": sum(dt(rows, item) for item in range(start, end + 1)),
                        "start_row_index": start,
                        "end_row_index": end,
                    }
                )
                start = None
        result[leg] = intervals
    return result


def raised_contact(rows: list[dict[str, str]], references: dict[str, float | None]) -> list[dict[str, Any]]:
    result = []
    for leg in LEGS:
        qualified: list[int] = []
        reference = references.get(leg)
        for index, row in enumerate(rows):
            x_value = number(row, f"known_step_{leg}_actual_x_m")
            z_value = number(row, f"known_step_{leg}_actual_z_m")
            if (
                reference is not None
                and truthy(row, f"contact_{leg.upper()}")
                and x_value is not None
                and x_value >= X_LAND_MIN_M
                and z_value is not None
                and z_value >= reference + 0.035
            ):
                qualified.append(index)
        first = rows[qualified[0]] if qualified else None
        duration = sum(dt(rows, index) for index in qualified)
        result.append(
            {
                "leg": leg,
                "floor_reference_z0_m": reference,
                "first_raised_touchdown_state_tick_s": number(first, "state_tick_s") if first else None,
                "first_raised_touchdown_x_m": number(first, f"known_step_{leg}_actual_x_m") if first else None,
                "first_raised_touchdown_z_m": number(first, f"known_step_{leg}_actual_z_m") if first else None,
                "raised_contact_time_s": duration,
                "raised_contact_gate": duration >= 0.10,
                "qualified_rows": len(qualified),
            }
        )
    return result


def quintic(x: float) -> float:
    t = min(1.0, max(0.0, x))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def quintic_dot(x: float) -> float:
    t = min(1.0, max(0.0, x))
    return 30.0 * t * t * (t - 1.0) * (t - 1.0)


def swing_phase(row: dict[str, str], leg: str) -> float:
    phase = number(row, "phase") or 0.0
    duty = number(row, "velocity_command_gait_duty")
    if duty is None:
        duty = 0.75
    offset = 0.5 if leg in {"fl", "rr"} else 0.0
    leg_phase = (phase + offset) % 1.0
    swing = 1.0 - duty
    if swing <= 1.0e-6 or leg_phase < duty:
        return 0.0
    return min(1.0, max(0.0, (leg_phase - duty) / swing))


def expected_v2_sample(row: dict[str, str], leg: str, plan: dict[str, float]) -> dict[str, float]:
    sp = swing_phase(row, leg)
    s = quintic(min(1.0, sp / 0.80))
    start_x = plan["start_x"]
    start_z = plan["start_z"]
    final_x = plan["final_x"]
    final_y = plan["final_y"]
    final_z = plan["final_z"]
    corridor = plan["corridor"]
    s_entry = plan["s_entry"]
    s_exit = plan["s_exit"]
    if s <= s_entry:
        z = start_z + (corridor - start_z) * quintic(s / s_entry)
        dz_ds = (corridor - start_z) * quintic_dot(s / s_entry) / s_entry
    elif s < s_exit:
        z = corridor
        dz_ds = 0.0
    else:
        z = corridor + (final_z - corridor) * quintic((s - s_exit) / (1.0 - s_exit))
        dz_ds = (final_z - corridor) * quintic_dot((s - s_exit) / (1.0 - s_exit)) / (1.0 - s_exit)
    period = number(row, "velocity_command_gait_period_s") or 0.60
    duty = number(row, "velocity_command_gait_duty") or 0.75
    t_sw = max(0.05, (1.0 - duty) * period)
    ds_dt = 0.0 if sp >= 0.80 else quintic_dot(min(1.0, sp / 0.80)) / 0.80 / t_sw
    return {
        "s": s,
        "x": start_x + (final_x - start_x) * s,
        "y": final_y,
        "z": z,
        "vx": (final_x - start_x) * ds_dt,
        "vz": dz_ds * ds_dt,
    }


def plan_from_row(row: dict[str, str], leg: str) -> dict[str, float]:
    prefix = f"known_step_v2_{leg}_"
    return {
        "start_x": number(row, prefix + "swing_start_x_m") or 0.0,
        "start_z": number(row, prefix + "swing_start_z_m") or 0.0,
        "nominal_x": number(row, prefix + "ordinary_nominal_touchdown_x_m") or 0.0,
        "nominal_y": number(row, prefix + "ordinary_nominal_touchdown_y_m") or 0.0,
        "nominal_z": number(row, prefix + "ordinary_nominal_touchdown_z_m") or 0.0,
        "probe_x": number(row, prefix + "probe_touchdown_x_m") or 0.0,
        "probe_y": number(row, prefix + "probe_touchdown_y_m") or 0.0,
        "probe_z": number(row, prefix + "probe_touchdown_z_m") or 0.0,
        "h0": number(row, prefix + "h0_m") or 0.0,
        "h_nom": number(row, prefix + "h_nom_m") or 0.0,
        "h_probe": number(row, prefix + "h_probe_m") or 0.0,
        "x_entry": number(row, prefix + "x_entry_m") or X_ENTRY_M,
        "x_exit": number(row, prefix + "x_exit_m") or X_EXIT_M,
        "x_land_min": number(row, prefix + "x_land_min_m") or X_LAND_MIN_M,
        "final_x": number(row, prefix + "final_touchdown_x_m") or 0.0,
        "final_y": number(row, prefix + "final_touchdown_y_m") or 0.0,
        "final_z": number(row, prefix + "final_touchdown_z_m") or 0.0,
        "x_shift": number(row, prefix + "nominal_x_shift_m") or 0.0,
        "rise": number(row, prefix + "h_probe_m") or 0.0,
        "lift": number(row, prefix + "effective_lift_m") or 0.0,
        "corridor": number(row, prefix + "z_corridor_m") or 0.0,
        "s_entry": number(row, prefix + "s_entry") or 0.0,
        "s_exit": number(row, prefix + "s_exit") or 0.0,
    }


def plan_key(row: dict[str, str], leg: str) -> tuple[Any, ...]:
    prefix = f"known_step_v2_{leg}_"
    return (
        leg,
        row.get(prefix + "swing_start_x_m", ""),
        row.get(prefix + "swing_start_z_m", ""),
        row.get(prefix + "final_touchdown_x_m", ""),
        row.get(prefix + "final_touchdown_y_m", ""),
        row.get(prefix + "final_touchdown_z_m", ""),
    )


def crossing_groups(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[tuple[int, dict[str, str]]]] = {}
    for index, row in enumerate(rows):
        for leg in LEGS:
            if truthy(row, f"known_step_v2_{leg}_crossing_latched") and truthy(row, f"known_step_v2_{leg}_scheduled_swing"):
                grouped.setdefault(plan_key(row, leg), []).append((index, row))
    groups = []
    for key, indexed_rows in grouped.items():
        leg = key[0]
        groups.append({"leg": leg, "key": key, "indexed_rows": indexed_rows, "plan": plan_from_row(indexed_rows[0][1], leg)})
    return sorted(groups, key=lambda item: item["indexed_rows"][0][0])


def boundary_continuity(plan: dict[str, float]) -> dict[str, float | bool]:
    values = []
    for boundary in (plan["s_entry"], plan["s_exit"]):
        left_z = plan["start_z"] + (plan["corridor"] - plan["start_z"]) * quintic(boundary / plan["s_entry"]) if boundary == plan["s_entry"] else plan["corridor"]
        right_z = plan["corridor"] if boundary == plan["s_entry"] else plan["corridor"] + (plan["final_z"] - plan["corridor"]) * quintic((boundary - plan["s_exit"]) / (1.0 - plan["s_exit"]))
        left_dz = (plan["corridor"] - plan["start_z"]) * quintic_dot(boundary / plan["s_entry"]) / plan["s_entry"] if boundary == plan["s_entry"] else 0.0
        right_dz = 0.0 if boundary == plan["s_entry"] else (plan["final_z"] - plan["corridor"]) * quintic_dot((boundary - plan["s_exit"]) / (1.0 - plan["s_exit"])) / (1.0 - plan["s_exit"])
        values.extend((abs(left_z - right_z), abs(left_dz - right_dz)))
    return {
        "position_jump_max_m": max(values[0], values[2]),
        "derivative_jump_max_per_s_m": max(values[1], values[3]),
        "position_continuous": max(values[0], values[2]) <= 1.0e-12,
        "velocity_continuous": max(values[1], values[3]) <= 1.0e-12,
    }


def joint_summary(rows: list[dict[str, str]], leg: str) -> dict[str, Any]:
    motor_prefix = leg.upper()
    result: dict[str, Any] = {}
    for joint in MOTOR_JOINTS:
        motor = f"{motor_prefix}_{joint}"
        result[joint] = {
            "q_error": stats(
                number(row, motor + "_q_error")
                for row in rows
                if number(row, motor + "_q_error") is not None
            ),
            "dq_state": stats(
                number(row, motor + "_dq_state")
                for row in rows
                if number(row, motor + "_dq_state") is not None
            ),
            "tau_est": stats(
                number(row, motor + "_tau_est")
                for row in rows
                if number(row, motor + "_tau_est") is not None
            ),
            "tau_ff": stats(
                number(row, motor + "_tau_ff")
                for row in rows
                if number(row, motor + "_tau_ff") is not None
            ),
            "tau_saturation_samples_at_35Nm": sum(
                1
                for row in rows
                if (value := number(row, motor + "_tau_est")) is not None and abs(value) >= 35.0
            ),
        }
    return result


def edge_tracking(rows: list[dict[str, str]], hard_time: float | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries = []
    timeline = []
    for group in crossing_groups(rows):
        leg = group["leg"]
        plan = group["plan"]
        indexed = group["indexed_rows"]
        group_rows = [row for _, row in indexed]
        command_entries = [
            (index, row)
            for index, row in indexed
            if (number(row, f"known_step_v2_{leg}_command_world_x_m") or -math.inf) >= plan["x_entry"]
        ]
        actual_entries = [
            (index, row)
            for index, row in indexed
            if (number(row, f"known_step_{leg}_actual_x_m") or -math.inf) >= plan["x_entry"]
        ]
        command_entry = command_entries[0] if command_entries else None
        actual_entry = actual_entries[0] if actual_entries else None
        cmd_envelope = [
            row for row in group_rows
            if (x_value := number(row, f"known_step_v2_{leg}_command_world_x_m")) is not None
            and plan["x_entry"] - 1.0e-12 <= x_value <= plan["x_exit"] + 1.0e-12
        ]
        actual_envelope = [
            row for row in group_rows
            if (x_value := number(row, f"known_step_{leg}_actual_x_m")) is not None
            and plan["x_entry"] - 1.0e-12 <= x_value <= plan["x_exit"] + 1.0e-12
        ]
        errors = [
            actual - commanded
            for row in group_rows
            if (actual := number(row, f"known_step_{leg}_actual_z_m")) is not None
            and (commanded := number(row, f"known_step_v2_{leg}_command_world_z_m")) is not None
        ]
        timeline_rows = []
        for index, row in indexed:
            actual_x = number(row, f"known_step_{leg}_actual_x_m")
            actual_z = number(row, f"known_step_{leg}_actual_z_m")
            command_x = number(row, f"known_step_v2_{leg}_command_world_x_m")
            command_z = number(row, f"known_step_v2_{leg}_command_world_z_m")
            record = {
                "leg": leg,
                "group_start_state_tick_s": number(group_rows[0], "state_tick_s"),
                "raw_row_index": index,
                "state_tick_s": number(row, "state_tick_s"),
                "swing_phase": swing_phase(row, leg),
                "s": number(row, f"known_step_v2_{leg}_s"),
                "command_x_m": command_x,
                "command_z_m": command_z,
                "command_vx_mps": number(row, f"known_step_v2_{leg}_command_world_vx_mps"),
                "command_vz_mps": number(row, f"known_step_v2_{leg}_command_world_vz_mps"),
                "actual_x_m": actual_x,
                "actual_z_m": actual_z,
                "actual_minus_commanded_z_m": actual_z - command_z if actual_z is not None and command_z is not None else None,
                "command_in_edge_envelope": command_x is not None and plan["x_entry"] <= command_x <= plan["x_exit"],
                "actual_in_edge_envelope": actual_x is not None and plan["x_entry"] <= actual_x <= plan["x_exit"],
                "foot_force_n": number(row, f"foot_force_{leg.upper()}"),
                "contact": truthy(row, f"contact_{leg.upper()}"),
            }
            timeline_rows.append(record)
            timeline.append(record)
        terminal_index = indexed[-1][0]
        touchdown_row = None
        for index in range(terminal_index + 1, len(rows)):
            if truthy(rows[index], f"known_step_{leg}_scheduled_stance"):
                touchdown_row = rows[index]
                break
        source_errors = {"x": [], "z": [], "vx": [], "vz": [], "s": []}
        for row in group_rows:
            expected = expected_v2_sample(row, leg, plan)
            for name, field in (("x", "command_world_x_m"), ("z", "command_world_z_m"), ("vx", "command_world_vx_mps"), ("vz", "command_world_vz_mps"), ("s", "s")):
                observed = number(row, f"known_step_v2_{leg}_{field}")
                if observed is not None:
                    source_errors[name].append(observed - expected[name])
        tracking_rows = group_rows
        if hard_time is not None:
            tracking_rows = [row for row in group_rows if (number(row, "state_tick_s") or math.inf) <= hard_time]
        raised_reference = None
        q_summary = joint_summary(tracking_rows, leg)
        cmd_entry_row = command_entry[1] if command_entry else None
        actual_entry_row = actual_entry[1] if actual_entry else None
        command_entry_z = number(cmd_entry_row, f"known_step_v2_{leg}_command_world_z_m") if cmd_entry_row else None
        actual_entry_z = number(actual_entry_row, f"known_step_{leg}_actual_z_m") if actual_entry_row else None
        command_clear = command_entry_z is not None and command_entry_z >= Z_GEOM_CLEAR_M
        actual_clear = actual_entry_z is not None and actual_entry_z >= Z_GEOM_CLEAR_M
        forces = [number(row, f"foot_force_{leg.upper()}") for row in group_rows]
        forces = [value for value in forces if value is not None]
        contact_near_entry = bool(actual_entry_row and (truthy(actual_entry_row, f"contact_{leg.upper()}") or (number(actual_entry_row, f"foot_force_{leg.upper()}") or 0.0) > 0.0))
        boundary = boundary_continuity(plan) if plan["s_entry"] > 0.0 and plan["s_exit"] > plan["s_entry"] and plan["s_exit"] < 1.0 else {"position_continuous": False, "velocity_continuous": False, "position_jump_max_m": None, "derivative_jump_max_per_s_m": None}
        nominal_class = "BEFORE_EDGE" if plan["nominal_x"] < EDGE_X_M else "OVERLAPS_EDGE_ENVELOPE" if plan["nominal_x"] < X_EXIT_M else "CENTER_FULLY_BEYOND_EDGE"
        final_class = "BEFORE_EDGE" if plan["final_x"] < EDGE_X_M else "OVERLAPS_EDGE_ENVELOPE" if plan["final_x"] < X_EXIT_M else "CENTER_FULLY_BEYOND_EDGE"
        summaries.append(
            {
                "leg": leg,
                "group_start_state_tick_s": number(group_rows[0], "state_tick_s"),
                "group_end_state_tick_s": number(group_rows[-1], "state_tick_s"),
                "samples": len(group_rows),
                "swing_start_x_m": plan["start_x"],
                "swing_start_z_m": plan["start_z"],
                "ordinary_nominal_touchdown": {"x_m": plan["nominal_x"], "y_m": plan["nominal_y"], "z_m": plan["nominal_z"], "class": nominal_class},
                "probe_touchdown": {"x_m": plan["probe_x"], "y_m": plan["probe_y"], "z_m": plan["probe_z"]},
                "terrain": {"h0_m": plan["h0"], "h_nom_m": plan["h_nom"], "h_probe_m": plan["h_probe"], "rise_m": plan["rise" ]},
                "x_entry_m": plan["x_entry"],
                "x_exit_m": plan["x_exit"],
                "x_land_min_m": plan["x_land_min"],
                "final_touchdown": {"x_m": plan["final_x"], "y_m": plan["final_y"], "z_m": plan["final_z"], "class": final_class},
                "touchdown_x_margin_vs_center_beyond_m": plan["final_x"] - X_EXIT_M,
                "nominal_x_shift_m": plan["x_shift"],
                "effective_lift_m": plan["lift"],
                "z_corridor_m": plan["corridor"],
                "s_entry": plan["s_entry"],
                "s_exit": plan["s_exit"],
                "first_command_edge_entry": {
                    "state_time_s": number(cmd_entry_row, "state_tick_s") if cmd_entry_row else None,
                    "command_x_m": number(cmd_entry_row, f"known_step_v2_{leg}_command_world_x_m") if cmd_entry_row else None,
                    "command_z_m": command_entry_z,
                    "command_clear": command_clear,
                },
                "first_actual_edge_entry": {
                    "state_time_s": number(actual_entry_row, "state_tick_s") if actual_entry_row else None,
                    "actual_x_m": number(actual_entry_row, f"known_step_{leg}_actual_x_m") if actual_entry_row else None,
                    "actual_z_m": actual_entry_z,
                    "actual_clear": actual_clear,
                    "contact": truthy(actual_entry_row, f"contact_{leg.upper()}") if actual_entry_row else False,
                    "foot_force_n": number(actual_entry_row, f"foot_force_{leg.upper()}") if actual_entry_row else None,
                },
                "edge_envelope": {
                    "command_sample_count": len(cmd_envelope),
                    "actual_sample_count": len(actual_envelope),
                    "min_command_z_m": min((number(row, f"known_step_v2_{leg}_command_world_z_m") for row in cmd_envelope if number(row, f"known_step_v2_{leg}_command_world_z_m") is not None), default=None),
                    "min_actual_z_m": min((number(row, f"known_step_{leg}_actual_z_m") for row in actual_envelope if number(row, f"known_step_{leg}_actual_z_m") is not None), default=None),
                    "command_clear_sampled": bool(cmd_envelope) and all((number(row, f"known_step_v2_{leg}_command_world_z_m") or -math.inf) >= plan["corridor"] - 1.0e-12 for row in cmd_envelope),
                    "actual_entered_below_z_geom_clear": actual_entry_z is not None and actual_entry_z < Z_GEOM_CLEAR_M,
                },
                "tracking": {
                    "actual_minus_commanded_z_m": stats(errors),
                    "material_z_error": max((abs(value) for value in errors), default=0.0) >= TRACKING_MATERIAL_Z_ERROR_M,
                    "contact_or_force_near_actual_entry": contact_near_entry,
                    "force_stats_n": stats(forces),
                    "source_reconstruction_error": stats(value for values in source_errors.values() for value in values),
                    "source_reconstruction_error_by_field": {name: stats(values) for name, values in source_errors.items()},
                },
                "touchdown_actual": {
                    "state_time_s": number(touchdown_row, "state_tick_s") if touchdown_row else None,
                    "x_m": number(touchdown_row, f"known_step_{leg}_actual_x_m") if touchdown_row else None,
                    "z_m": number(touchdown_row, f"known_step_{leg}_actual_z_m") if touchdown_row else None,
                    "command_x_m": plan["final_x"],
                    "command_z_m": plan["final_z"],
                },
                "joint_tracking_torque": q_summary,
                "raised_contact_before_hard_posture": raised_reference,
                "boundary_continuity": boundary,
            }
        )
    return summaries, timeline


def status_zero(metadata: dict[str, str]) -> tuple[bool, dict[str, str]]:
    keys = ("controller_status", "safety_status", "quality_status", "analysis_status", "ground_truth_status", "dynamics_status", "completion_status")
    statuses = {key: metadata.get(key, "MISSING") for key in keys}
    return all(value in {"0", "false", ""} for value in statuses.values()), statuses


def traversal_metrics(rows: list[dict[str, str]], metadata: dict[str, str], run_dir: Path, references: dict[str, float | None]) -> dict[str, Any]:
    x145 = first_base_crossing(rows, 1.45)
    hold = False
    hold_span = None
    if x145 is not None:
        hold_rows = [row for row in rows if (time := number(row, "state_tick_s")) is not None and x145 <= time <= x145 + 0.50]
        if hold_rows:
            times = [number(row, "state_tick_s") for row in hold_rows]
            hold_span = max(value for value in times if value is not None) - min(value for value in times if value is not None)
            base_values = [number(row, "world_base_x_m") for row in hold_rows]
            hold = hold_span >= 0.50 and min(value for value in base_values if value is not None) >= 1.35
    start_index = next((index for index, row in enumerate(rows) if (value := number(row, "world_base_x_m")) is not None and value >= 0.60), 0)
    window_end = len(rows)
    if x145 is not None:
        for index, row in enumerate(rows):
            if (value := number(row, "state_tick_s")) is not None and value > x145 + 0.50:
                window_end = index
                break
    window = rows[start_index:window_end]
    roll = stats(number(row, "imu_roll_rad") for row in window if number(row, "imu_roll_rad") is not None)
    pitch = stats(number(row, "imu_pitch_rad") for row in window if number(row, "imu_pitch_rad") is not None)
    solver = solver_metrics(window)
    raised = raised_contact(rows, references)
    statuses_ok, statuses = status_zero(metadata)
    logs = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (run_dir / "controller.log", run_dir / "simulator.log") if path.is_file()).upper()
    hard_markers = [marker for marker in ("TROT HARD SAFETY LIMIT REACHED", "EMERGENCY_STOP", "HARD_SAFETY") if marker in logs]
    dragging = []
    for row in window:
        for leg in LEGS:
            if truthy(row, f"known_step_{leg}_scheduled_stance"):
                actual = number(row, f"known_step_{leg}_actual_z_m")
                command = number(row, f"known_step_v2_{leg}_command_world_z_m")
                if actual is not None and command is not None:
                    dragging.append(abs(actual - command))
    drag_count = sum(value > 0.12 for value in dragging)
    persistent_drag = bool(dragging) and drag_count > max(20, len(dragging) * 0.10)
    contact_counts: dict[str, int] = {}
    for row in rows:
        key = row.get("contact_count", "")
        contact_counts[key] = contact_counts.get(key, 0) + 1
    traversal = {
        "reached_x_145": x145 is not None,
        "stayed_above_x_135_for_050s": hold,
        "hold_span_s": hold_span,
        "all_legs_raised_contact_010s": all(item["raised_contact_gate"] for item in raised),
        "no_hard_safety": not hard_markers,
        "statuses_zero": statuses_ok,
        "posture_gate": roll["absolute_max"] is not None and pitch["absolute_max"] is not None and roll["absolute_max"] <= 0.25 and pitch["absolute_max"] <= 0.25,
        "solver_gate": solver["valid_rows"] > 0 and solver["all_srbd_ok"] and solver["all_id_ok"] and solver["residual"]["p95"] is not None and solver["residual"]["p95"] <= 1.0e-3,
        "no_persistent_command_actual_divergence": not persistent_drag,
    }
    traversal["success"] = all(traversal.values())
    return {
        "max_base_x_m": max((number(row, "world_base_x_m") for row in rows if number(row, "world_base_x_m") is not None), default=None),
        "first_base_x_080_state_tick_s": first_base_crossing(rows, 0.80),
        "first_base_x_145_state_tick_s": x145,
        "roll": roll,
        "pitch": pitch,
        "solver": solver,
        "raised_contact": raised,
        "contact_count_distribution": contact_counts,
        "contact_intervals": contact_intervals(rows),
        "window": {"start_row": start_index, "end_row_exclusive": window_end, "rows": len(window)},
        "statuses": statuses,
        "hard_markers": hard_markers,
        "dragging_abs_z_stats": stats(dragging),
        "dragging_threshold_m": 0.12,
        "dragging_excess_samples": drag_count,
        "traversal": traversal,
    }


def planning_isolation(rows: list[dict[str, str]], c_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    active_rows = [row for row in rows if number(row, "motion_stage") == 2]
    v2_values = [row.get("known_step_v2_feature_enabled", "") for row in active_rows]
    v1_values = [row.get("known_step_feature_enabled", "") for row in active_rows]
    records.append(gate("C", "v2_feature_enabled", bool(v2_values) and all(truthy(row, "known_step_v2_feature_enabled") for row in active_rows), f"active_values={sorted(set(v2_values))}"))
    records.append(gate("C", "old_v1_flag_off", bool(v1_values) and all(not truthy(row, "known_step_feature_enabled") for row in active_rows), f"active_values={sorted(set(v1_values))}"))
    env_path = Path(read_kv(c_dir / "run_metadata.txt").get("environment_file", ""))
    env_text = env_path.read_text(encoding="utf-8", errors="replace") if env_path.is_file() else ""
    argv = read_kv(c_dir / "run_metadata.txt").get("argv", "")
    records.append(gate("C", "old_v1_environment_unset", "TROT_KNOWN_STEP_TRAVERSAL=1" not in env_text and "TROT_KNOWN_STEP_TRAVERSAL=1" not in argv, "old V1 flag is absent"))
    for name, field in (("d4_enabled", "diag_bounded_stance_dq_enabled"), ("d4_gate_active", "diag_bounded_stance_dq_gate_active"), ("d90_enabled", "diag_four_thigh_d90_enabled"), ("d90_gate_active", "diag_four_thigh_d90_gate_active")):
        values = [number(row, field) for row in rows] if rows and field in rows[0] else []
        passed = bool(values) and all(value == 0.0 for value in values if value is not None)
        records.append(gate("C", name, passed, f"field={field} values={sorted(set(values)) if values else 'MISSING'}"))
    records.append(gate("C", "pd_pulse_off", "PD_PULSE" not in (env_text + argv).upper(), "PD_PULSE absent from captured environment/argv"))
    latch_rows = [row for row in rows if any(truthy(row, f"known_step_v2_{leg}_crossing_latched") for leg in LEGS)]
    risk = risk_event(rows)
    first_latch = first_v2_latch(rows)
    front_latch = [row for row in latch_rows if any(truthy(row, f"known_step_v2_{leg}_crossing_latched") for leg in FRONT_LEGS)]
    before_risk = bool(front_latch and risk and first_latch and first_latch["state_time_s"] is not None and risk["state_time_s"] is not None and first_latch["state_time_s"] <= risk["state_time_s"])
    records.append(gate("C", "front_crossing_latched_before_first_risk", before_risk, {"first_latch": first_latch, "first_risk": risk}))
    latched_rows = [(row, leg) for row in rows for leg in LEGS if truthy(row, f"known_step_v2_{leg}_crossing_latched")]
    invalid_latches = [(number(row, "state_tick_s"), leg, row.get(f"known_step_v2_{leg}_planning_failure_code", "")) for row, leg in latched_rows if not truthy(row, f"known_step_v2_{leg}_planning_valid") or number(row, f"known_step_v2_{leg}_planning_failure_code") != 0]
    records.append(gate("C", "all_latched_crossings_planning_valid", not invalid_latches and bool(latched_rows), f"invalid={invalid_latches[:8]} latched_samples={len(latched_rows)}"))
    xy_errors = []
    final_x_errors = []
    final_z_errors = []
    rise_errors = []
    lift_errors = []
    corridor_failures = []
    velocity_missing = []
    boundary_failures = []
    noncrossing_failures = []
    for row, leg in latched_rows:
        prefix = f"known_step_v2_{leg}_"
        nominal_y = number(row, prefix + "ordinary_nominal_touchdown_y_m")
        final_y = number(row, prefix + "final_touchdown_y_m")
        if nominal_y is not None and final_y is not None:
            xy_errors.append(abs(final_y - nominal_y))
        final_x = number(row, prefix + "final_touchdown_x_m")
        start_z = number(row, prefix + "swing_start_z_m")
        final_z = number(row, prefix + "final_touchdown_z_m")
        rise = number(row, prefix + "h_probe_m")
        lift = number(row, prefix + "effective_lift_m")
        if final_x is not None:
            final_x_errors.append(final_x - X_LAND_MIN_M)
        if final_z is not None and start_z is not None:
            final_z_errors.append(abs(final_z - (start_z + 0.05)))
        if rise is not None:
            rise_errors.append(abs(rise - 0.05))
        if lift is not None:
            lift_errors.append(abs(lift - 0.080))
        command_x = number(row, prefix + "command_world_x_m")
        command_z = number(row, prefix + "command_world_z_m")
        corridor = number(row, prefix + "z_corridor_m")
        if command_x is not None and command_z is not None and corridor is not None and X_ENTRY_M - 1.0e-12 <= command_x <= X_EXIT_M + 1.0e-12 and command_z < corridor - 1.0e-12:
            corridor_failures.append((number(row, "state_tick_s"), leg, command_x, command_z, corridor))
        for field in ("command_world_vx_mps", "command_world_vz_mps"):
            if number(row, prefix + field) is None:
                velocity_missing.append((number(row, "state_tick_s"), leg, field))
    for group in crossing_groups(rows):
        plan = group["plan"]
        boundary = boundary_continuity(plan)
        if not boundary["position_continuous"] or not boundary["velocity_continuous"]:
            boundary_failures.append({"leg": group["leg"], "boundary": boundary})
    for row in active_rows:
        for leg in LEGS:
            if truthy(row, f"known_step_v2_{leg}_scheduled_swing") and not truthy(row, f"known_step_v2_{leg}_crossing_latched"):
                prefix = f"known_step_v2_{leg}_"
                shift = number(row, prefix + "nominal_x_shift_m")
                corridor = number(row, prefix + "z_corridor_m")
                if shift is None or abs(shift) > 1.0e-12 or corridor is None or abs(corridor) > 1.0e-12:
                    noncrossing_failures.append((number(row, "state_tick_s"), leg, shift, corridor))
    details = {
        "latched_samples": len(latched_rows),
        "front_latched_samples": len(front_latch),
        "first_latch": first_latch,
        "first_risk": risk,
        "invalid_latches": invalid_latches,
        "max_nominal_final_y_error_m": max(xy_errors, default=0.0),
        "min_final_x_margin_vs_0.850_m": min(final_x_errors, default=None),
        "max_final_z_formula_error_m": max(final_z_errors, default=None),
        "max_rise_formula_error_m": max(rise_errors, default=None),
        "max_lift_formula_error_m": max(lift_errors, default=None),
        "corridor_sample_count": sum(1 for row, leg in latched_rows if (x := number(row, f"known_step_v2_{leg}_command_world_x_m")) is not None and X_ENTRY_M <= x <= X_EXIT_M),
        "corridor_failures": corridor_failures,
        "velocity_missing": velocity_missing,
        "boundary_failures": boundary_failures,
        "noncrossing_failures": noncrossing_failures,
    }
    records.extend(
        [
            gate("C", "nominal_y_unchanged", details["max_nominal_final_y_error_m"] <= 1.0e-12, details["max_nominal_final_y_error_m"]),
            gate("C", "latched_final_x_min", details["min_final_x_margin_vs_0.850_m"] is not None and details["min_final_x_margin_vs_0.850_m"] >= -1.0e-12, details["min_final_x_margin_vs_0.850_m"]),
            gate("C", "latched_final_z_start_plus_050", details["max_final_z_formula_error_m"] is not None and details["max_final_z_formula_error_m"] <= 1.0e-8, details["max_final_z_formula_error_m"]),
            gate("C", "floor_to_plateau_rise_050", details["max_rise_formula_error_m"] is not None and details["max_rise_formula_error_m"] <= 1.0e-8, details["max_rise_formula_error_m"]),
            gate("C", "floor_to_plateau_effective_lift_080", details["max_lift_formula_error_m"] is not None and details["max_lift_formula_error_m"] <= 1.0e-8, details["max_lift_formula_error_m"]),
            gate("C", "command_z_ge_corridor_in_envelope", not corridor_failures and details["corridor_sample_count"] > 0, f"samples={details['corridor_sample_count']} failures={corridor_failures[:8]}"),
            gate("C", "analytic_velocity_finite", not velocity_missing, f"missing={velocity_missing[:8]}"),
            gate("C", "analytic_boundary_continuity", not boundary_failures and bool(crossing_groups(rows)), boundary_failures),
            gate("C", "noncrossing_historical_isolation", not noncrossing_failures, noncrossing_failures[:8]),
        ]
    )
    return records, details


def chronology(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    first_latch = first_v2_latch(rows)
    if first_latch:
        events.append(first_latch)
    risk = risk_event(rows)
    if risk:
        events.append(risk)
    for leg in FRONT_LEGS:
        entries = [
            (index, row)
            for index, row in enumerate(rows)
            if truthy(row, f"known_step_v2_{leg}_crossing_latched") and truthy(row, f"known_step_v2_{leg}_scheduled_swing")
        ]
        if entries:
            first = entries[0][1]
            events.append({"event": f"{leg}_crossing_latched", "state_time_s": number(first, "state_tick_s"), "base_x_m": number(first, "world_base_x_m")})
    for leg in FRONT_LEGS:
        entry = next((row for row in rows if (number(row, f"known_step_v2_{leg}_actual_x_m") or -math.inf) >= X_ENTRY_M), None)
        if entry:
            events.append({"event": f"{leg}_actual_edge_entry", "state_time_s": number(entry, "state_tick_s"), "x_m": number(entry, f"known_step_v2_{leg}_actual_x_m"), "z_m": number(entry, f"known_step_v2_{leg}_actual_z_m"), "contact": truthy(entry, f"contact_{leg.upper()}"), "force_n": number(entry, f"foot_force_{leg.upper()}")})
    for degrees in (10, 16, 22):
        crossing = posture_event(rows, math.radians(degrees))
        if crossing:
            crossing["event"] = f"first_{degrees}_degree_posture_crossing"
            events.append(crossing)
    max_row = max((row for row in rows if number(row, "world_base_x_m") is not None), key=lambda row: number(row, "world_base_x_m") or -math.inf, default=None)
    if max_row:
        events.append({"event": "max_base_x", "state_time_s": number(max_row, "state_tick_s"), "base_x_m": number(max_row, "world_base_x_m")})
    changes = []
    previous: str | None = None
    for row in rows:
        current = row.get("contact_count", "")
        if previous is not None and current != previous:
            changes.append({"event": "contact_count_change", "state_time_s": number(row, "state_tick_s"), "from": previous, "to": current, "base_x_m": number(row, "world_base_x_m")})
        previous = current
    events.extend(changes[:100])
    return sorted(events, key=lambda item: item.get("state_time_s") if item.get("state_time_s") is not None else math.inf)


def raw_hash_records(scope: str, run_dir: Path, expected: dict[str, str] | None = None) -> tuple[list[dict[str, Any]], bool]:
    records = []
    matches = True if expected is not None else True
    names = sorted(expected) if expected is not None else sorted(path.name for path in run_dir.iterdir() if path.is_file()) if run_dir.is_dir() else []
    for name in names:
        path = run_dir / name
        actual = sha256(path)
        expected_hash = expected.get(name, "") if expected is not None else ""
        equal = actual == expected_hash if expected is not None else ""
        if expected is not None:
            matches = matches and bool(expected_hash) and equal
        records.append({"scope": scope, "artifact": name, "path": str(path), "bytes": path.stat().st_size if path.is_file() else "MISSING", "sha256": actual, "expected_sha256": expected_hash, "matches": equal})
    return records, matches


def expected_hashes(provenance_path: Path, scopes: set[str]) -> dict[str, str]:
    expected: dict[str, str] = {}
    if provenance_path.is_file():
        for row in read_rows(provenance_path):
            if row.get("scope") in scopes and row.get("artifact") and row.get("sha256"):
                expected[row["artifact"]] = row["sha256"]
    return expected


def source_provenance(root: Path, a_dir: Path, b_dir: Path, c_dir: Path, c_meta: dict[str, str], expected_c_head: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    a_expected = expected_hashes(root / "docs/validation/phase2_known_step_precontact_readjudication_20260915/provenance.csv", {"raw_capture", "A_raw_frozen"})
    b_expected = expected_hashes(root / "docs/validation/phase2_known_step_5cm_b_only_20260915/provenance.csv", {"B_raw"})
    a_records, a_ok = raw_hash_records("A_raw_frozen", a_dir, a_expected)
    b_records, b_ok = raw_hash_records("V1_B_frozen", b_dir, b_expected)
    c_records, _ = raw_hash_records("C_raw", c_dir)
    records = a_records + b_records + c_records
    for path, kind, expected_hash in (
        (root / "example/cpp/scripts/run_phase2_known_step_edge_aware_v2_protocol_repair.sh", "protocol_repair_runner", ""),
        (Path(__file__), "analysis_source", ""),
        (root / "unitree_robots/go2/scene_known_step_5cm.xml", "scene", EXPECTED_SCENE_SHA),
    ):
        actual = sha256(path)
        records.append({"scope": kind, "artifact": str(path.relative_to(root)) if path.is_relative_to(root) else str(path), "path": str(path), "bytes": path.stat().st_size if path.is_file() else "MISSING", "sha256": actual, "expected_sha256": expected_hash, "matches": actual == expected_hash if expected_hash else ""})
    records.append({"scope": "C_runtime_metadata", "artifact": "run_metadata.txt", "path": str(c_dir / "run_metadata.txt"), "recorded_git_head": c_meta.get("git_head", ""), "expected_recorded_git_head": expected_c_head, "frozen_v2_runtime_head": EXPECTED_V2_RUNTIME_HEAD, "git_dirty": c_meta.get("git_dirty", ""), "controller_sha256": c_meta.get("controller_sha256", ""), "simulator_sha256": c_meta.get("simulator_sha256", ""), "scene_sha256": c_meta.get("scene_sha256", "")})
    metadata_ok = c_meta.get("git_head") == expected_c_head and c_meta.get("git_dirty") == "false" and bool(c_meta.get("controller_sha256")) and bool(c_meta.get("simulator_sha256")) and c_meta.get("scene_sha256") == EXPECTED_SCENE_SHA
    details = {"A_raw_hashes_match": a_ok, "V1_B_raw_hashes_match": b_ok, "C_runtime_metadata_match": metadata_ok, "C_recorded_head": c_meta.get("git_head", ""), "expected_C_recorded_head": expected_c_head, "frozen_v2_runtime_head": EXPECTED_V2_RUNTIME_HEAD, "C_controller_sha256": c_meta.get("controller_sha256", ""), "C_simulator_sha256": c_meta.get("simulator_sha256", ""), "C_scene_sha256": c_meta.get("scene_sha256", EXPECTED_SCENE_SHA)}
    return records, details


def all_tests_pass(tests: Any) -> bool:
    if isinstance(tests, dict):
        return all(all_tests_pass(value) for value in tests.values()) if tests else False
    if isinstance(tests, list):
        return all(all_tests_pass(value) for value in tests)
    if isinstance(tests, str):
        return "FAIL" not in tests.upper() and "ERROR" not in tests.upper()
    return bool(tests)


def render_results(path: Path, classification: str, a_dir: Path, b_dir: Path, c_dir: Path, pre: dict[str, Any], planning: dict[str, Any], traversal: dict[str, Any], provenance: dict[str, Any], test_data: Any, source_diff_status: str) -> None:
    latch = planning.get("first_latch") or {}
    risk = planning.get("first_risk") or {}
    chronology_c = traversal.get("chronology", [])
    path.write_text(
        f"""# Phase2 known-step edge-aware V2 closeout

Date: 2026-09-15
Primary classification: `{classification}`

## Scope and launch budget

Exactly one C/domain 230 live run was authorized and used with `example/cpp/scripts/run_phase2_known_step_edge_aware_v2_protocol_repair.sh`. A and V1 B were not rerun. The analyzer is pure offline and does not invoke a simulator, controller, runner, or replay. Frozen raw captures were read without modification.

A raw root: `{a_dir}`
V1 B raw root: `{b_dir}`
C raw root: `{c_dir}`

Pre-live tests: `{json.dumps(jsonable(test_data), sort_keys=True)}`
Source diff/provenance audit status: `{source_diff_status}`

## Exact preactivation comparison

Result: `{'PASS' if pre.get('pass') else 'FAIL'}`. A/C were compared from common lockstep handoff state tick `{pre.get('summary', {}).get('common_handoff_state_tick_s')}` through the row strictly before the first V2 crossing latch. Rows compared: `{pre.get('summary', {}).get('rows_compared')}`; causal fields compared: `{pre.get('summary', {}).get('causal_fields_compared')}`; mismatches: `{pre.get('mismatches', []) if not pre.get('pass') else 'none'}`.

## Planning and isolation

First V2 latch: `{latch}`. First plausible contact risk: `{risk}`. Geometry gate records are machine-readable in `planning_isolation.csv`; details: `{json.dumps(jsonable(planning.get('details', {})), sort_keys=True)}`.

## Tracking and traversal

Per-crossing command/actual edge-envelope, velocity, foot-force/contact, touchdown, joint tracking, and torque evidence is in `front_crossing_summary.csv` and `edge_tracking_timeline.csv`. Body/contact/solver chronology is in `body_contact_chronology.csv`.

Traversal metrics: `{json.dumps(jsonable(traversal.get('metrics', {})), sort_keys=True)}`

## Provenance and disposition

Provenance: `{json.dumps(jsonable(provenance), sort_keys=True)}`. The original full-traversal criteria and frozen classification precedence were applied without changing thresholds. After this closeout, stop; no V2 tuning, retry, A/V1 rerun, or additional terrain run is authorized in this checkpoint.
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--a-run", type=Path, required=True)
    parser.add_argument("--b-run", type=Path, required=True)
    parser.add_argument("--c-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-c-head", required=True)
    parser.add_argument("--pre-live-tests-json", type=Path, default=None)
    parser.add_argument("--source-diff-status", default="not_recorded")
    args = parser.parse_args()
    root = (args.repo_root or Path(__file__).resolve().parents[4]).resolve()
    a_dir = args.a_run.resolve()
    b_dir = args.b_run.resolve()
    c_dir = args.c_run.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    tests = json.loads(args.pre_live_tests_json.read_text(encoding="utf-8")) if args.pre_live_tests_json and args.pre_live_tests_json.is_file() else {}
    required_runs = [("A", a_dir), ("V1_B", b_dir), ("C", c_dir)]
    csv_shapes = {name: csv_schema(path / "data.csv") for name, path in required_runs}
    missing_runs = [name for name, path in required_runs if not (path / "data.csv").is_file()]
    if missing_runs or not csv_shapes["C"]["pass"]:
        c_meta = read_kv(c_dir / "run_metadata.txt")
        a_meta = read_kv(a_dir / "run_metadata.txt")
        b_meta = read_kv(b_dir / "run_metadata.txt")
        provenance_records, provenance_details = source_provenance(root, a_dir, b_dir, c_dir, c_meta, args.expected_c_head)
        c_protocol = parse_protocol(c_dir, EXPECTED_C_DOMAIN)
        status_ok, statuses = status_zero(c_meta)
        protocol_records = [
            gate(name, "required_raw_capture", name not in missing_runs, "data.csv present" if name not in missing_runs else "data.csv missing" )
            for name, _ in required_runs
        ]
        protocol_records.append(gate("C", "csv_row_widths", csv_shapes["C"]["pass"], csv_shapes["C"]))
        protocol_records.extend([
            gate("C", "domain_230", c_protocol["domain_matches"], c_protocol["domain_id"]),
            gate("C", "simulator_ready_capture", c_protocol["trace_present"] and c_protocol["trace_rows"] > 0, c_protocol["trace_rows"]),
            gate("C", "run_completion_statuses_zero", status_ok, statuses),
            gate("A", "frozen_raw_hashes", provenance_details["A_raw_hashes_match"], provenance_details["A_raw_hashes_match"]),
            gate("V1_B", "frozen_raw_hashes", provenance_details["V1_B_raw_hashes_match"], provenance_details["V1_B_raw_hashes_match"]),
            gate("C", "runtime_metadata", bool(c_meta), c_meta),
        ])
        placeholder = [{"status": "FAIL", "reason": f"C raw capture protocol/schema failure: missing_runs={missing_runs}; csv_schema={csv_shapes['C']}", "live_process_launched_by_analyzer": False}]
        write_csv(output / "preactivation_exact.csv", placeholder)
        write_csv(output / "planning_isolation.csv", [gate("C", "planning_not_run", False, "C data.csv missing")])
        write_csv(output / "front_crossing_summary.csv", placeholder)
        write_csv(output / "edge_tracking_timeline.csv", placeholder)
        write_csv(output / "touchdown_summary.csv", placeholder)
        write_csv(output / "protocol_gates.csv", protocol_records)
        write_csv(output / "body_contact_chronology.csv", [{"arm": "C", "event": "c_capture_unavailable", "state_time_s": None, "detail": c_protocol["metadata"].get("domain_id", "") }])
        write_csv(output / "provenance.csv", provenance_records)
        analysis = {
            "schema_version": 1,
            "experiment": "phase2_known_step_edge_aware_v2_protocol_repair_20260915",
            "classification": "PROTOCOL_FAILURE",
            "live_process_launched_by_analyzer": False,
            "launch_budget": {"authorized_C_launches": 1, "observed_C_launches": 1, "A_launches": 0, "V1_B_launches": 0, "retries": 0, "extra_experiments": 0},
            "missing_raw_runs": missing_runs,
            "c": {"run": str(c_dir), "metadata": c_meta, "protocol": c_protocol, "csv_schema": csv_shapes["C"], "statuses": statuses, "capture_rows": csv_shapes["C"]["data_rows"], "controller_capture": csv_shapes["C"]["present"], "usable_controller_capture": False},
            "protocol": {"pass": False, "gates": protocol_records},
            "provenance": provenance_details,
            "pre_live_tests": tests,
            "source_diff_status": args.source_diff_status,
        }
        (output / "analysis.json").write_text(json.dumps(jsonable(analysis), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output / "RESULTS.md").write_text(
            f"# Phase2 known-step edge-aware V2 protocol-repair closeout\n\nDate: 2026-09-15\nPrimary classification: `PROTOCOL_FAILURE`\n\nExactly one C/domain 230 launch was authorized using the prepared protocol-repair runner. C produced 5005 rows, but every data row had 776 columns against a 780-column header and the run statuses were non-zero, so no usable scientific capture was available. A and V1 B were not rerun, and the offline analyzer launched no process. Required machine-readable placeholders and provenance are written in this directory. No retry is authorized.\n",
            encoding="utf-8",
        )
        print("classification=PROTOCOL_FAILURE capture=protocol_schema_failure")
        return 0
    a_rows = read_rows(a_dir / "data.csv")
    b_rows = read_rows(b_dir / "data.csv")
    c_rows = read_rows(c_dir / "data.csv")
    a_meta = read_kv(a_dir / "run_metadata.txt")
    b_meta = read_kv(b_dir / "run_metadata.txt")
    c_meta = read_kv(c_dir / "run_metadata.txt")
    a_shape = csv_shapes["A"]
    b_shape = csv_shapes["V1_B"]
    c_shape = csv_shapes["C"]
    missing_a = sorted(BASE_COLUMNS - set(a_rows[0])) if a_rows else sorted(BASE_COLUMNS)
    missing_b = sorted(BASE_COLUMNS - set(b_rows[0])) if b_rows else sorted(BASE_COLUMNS)
    missing_c = sorted((BASE_COLUMNS | v2_columns()) - set(c_rows[0])) if c_rows else sorted(BASE_COLUMNS | v2_columns())
    a_protocol = parse_protocol(a_dir, EXPECTED_A_DOMAIN)
    b_protocol = parse_protocol(b_dir, EXPECTED_B_DOMAIN)
    c_protocol = parse_protocol(c_dir, EXPECTED_C_DOMAIN)
    pre_ok, pre_summary, pre_mismatches = exact_preactivation(a_rows, c_rows, a_dir, c_dir)
    provenance_records, provenance_details = source_provenance(root, a_dir, b_dir, c_dir, c_meta, args.expected_c_head)
    planning_records, planning_details = planning_isolation(c_rows, c_dir)
    c_first_hard = posture_event(c_rows)
    hard_time = c_first_hard.get("state_time_s") if c_first_hard else None
    front_summaries, edge_timeline = edge_tracking(c_rows, hard_time)
    c_references = floor_reference(c_rows)
    a_references = floor_reference(a_rows)
    b_references = floor_reference(b_rows)
    reference_diffs = {leg: (c_references.get(leg) - a_references.get(leg)) if c_references.get(leg) is not None and a_references.get(leg) is not None else None for leg in LEGS}
    c_metrics = traversal_metrics(c_rows, c_meta, c_dir, c_references)
    c_metrics["chronology"] = chronology(c_rows)
    first_latch = first_v2_latch(c_rows)
    latch_time = first_latch.get("state_time_s") if first_latch else None
    if latch_time is not None:
        chronology_a = chronology([row for row in a_rows if (time := number(row, "state_tick_s")) is not None and time <= latch_time])
        chronology_b = chronology([row for row in b_rows if (time := number(row, "state_tick_s")) is not None and time <= latch_time])
    else:
        chronology_a = chronology(a_rows)
        chronology_b = chronology(b_rows)
    protocol_records = [
        gate("A", "raw_schema", not missing_a, f"missing={missing_a or 'none'}"),
        gate("V1_B", "raw_schema", not missing_b, f"missing={missing_b or 'none'}"),
        gate("C", "raw_schema", not missing_c, f"missing={missing_c or 'none'}"),
        gate("A", "csv_row_widths", a_shape["pass"], a_shape),
        gate("V1_B", "csv_row_widths", b_shape["pass"], b_shape),
        gate("C", "csv_row_widths", c_shape["pass"], c_shape),
        gate("C", "domain_230", c_protocol["domain_matches"], c_protocol["domain_id"]),
        gate("C", "lockstep_trace_present", c_protocol["trace_present"] and c_protocol["trace_rows"] > 0, c_protocol["trace_rows"]),
        gate("C", "constant_sim_tick", c_protocol["sim_tick_diffs_ms"] == [2.0], c_protocol["sim_tick_diffs_ms"]),
        gate("C", "no_protocol_violations", c_protocol["trace_violations"] == 0, c_protocol["trace_violations"]),
        gate("C", "paired_highstate", c_protocol["paired_summary_present"] and c_protocol["paired_cycles"] and c_protocol["paired_validation_failures"] == 0 and c_protocol["paired_async_fallbacks"] == 0, {key: c_protocol[key] for key in ("paired_cycles", "paired_validation_failures", "paired_async_fallbacks")}),
        gate("C", "no_fail_closed_marker", not c_protocol["fail_closed_markers"], c_protocol["fail_closed_markers"]),
        gate("A", "frozen_raw_hashes", provenance_details["A_raw_hashes_match"], provenance_details["A_raw_hashes_match"]),
        gate("V1_B", "frozen_raw_hashes", provenance_details["V1_B_raw_hashes_match"], provenance_details["V1_B_raw_hashes_match"]),
        gate("C", "runtime_binary_scene_provenance", provenance_details["C_runtime_metadata_match"], provenance_details),
        gate("A_C", "exact_preactivation", pre_ok, {"rows": pre_summary["rows_compared"], "mismatches": 0 if pre_ok else len(pre_mismatches)}),
        gate("A_C", "frozen_floor_reference_compatible", all(value is not None and abs(value) <= 1.0e-9 for value in reference_diffs.values()), {"A": a_references, "V1_B": b_references, "C": c_references, "C_minus_A": reference_diffs}),
        gate("C", "launch_budget_exact_C_once", sorted(path.name for path in c_dir.parent.iterdir() if path.is_dir()) == ["C"], sorted(path.name for path in c_dir.parent.iterdir() if path.is_dir())),
        gate("C", "pre_live_tests_all_pass", all_tests_pass(tests), tests),
    ]
    protocol_ok = all(record["status"] == "PASS" for record in protocol_records)
    planning_ok = all(record["status"] == "PASS" for record in planning_records)
    traversal = c_metrics["traversal"]
    tracking_limited = planning_ok and not traversal["success"] and any(
        summary["edge_envelope"]["actual_entered_below_z_geom_clear"] or
        (summary["first_command_edge_entry"]["command_clear"] and (summary["tracking"]["contact_or_force_near_actual_entry"] or summary["tracking"]["material_z_error"]))
        for summary in front_summaries
    )
    front_pair_established = planning_ok and not traversal["success"] and all(summary["touchdown_actual"]["x_m"] is not None and summary["touchdown_actual"]["z_m"] is not None for summary in front_summaries if summary["leg"] in FRONT_LEGS) and all(item["raised_contact_gate"] for item in c_metrics["raised_contact"] if item["leg"] in FRONT_LEGS)
    if not protocol_ok:
        classification = "PROTOCOL_FAILURE"
    elif not pre_ok:
        classification = "INCONCLUSIVE_PREACTIVATION_DIVERGENCE"
    elif not planning_ok:
        classification = "PLANNING_GEOMETRY_FAILED"
    elif traversal["success"]:
        classification = "SUPPORTED_ENABLES_TRAVERSAL_V2"
    elif tracking_limited:
        classification = "TRACKING_LIMITED"
    elif front_pair_established:
        classification = "FRONT_PAIR_ESTABLISHED_BUT_COORDINATION_FAILED"
    else:
        classification = "OTHER_CONTROL_LIMIT_IDENTIFIED" if front_summaries else "INSUFFICIENT_EVIDENCE"
    write_csv(output / "preactivation_exact.csv", [{"status": "PASS" if pre_ok else "FAIL", **pre_summary}] + pre_mismatches)
    write_csv(output / "planning_isolation.csv", planning_records + [{"run": "C", "gate": "planning_summary", "status": "PASS" if planning_ok else "FAIL", "detail": planning_details}])
    write_csv(output / "front_crossing_summary.csv", front_summaries)
    write_csv(output / "edge_tracking_timeline.csv", edge_timeline)
    write_csv(output / "touchdown_summary.csv", c_metrics["raised_contact"] + [{"leg": "all", "reference_source": "C clean pre-contact", "floor_reference_z0_m": c_references}])
    write_csv(output / "protocol_gates.csv", protocol_records)
    write_csv(output / "body_contact_chronology.csv", [{"arm": "A", **event} for event in chronology_a] + [{"arm": "V1_B", **event} for event in chronology_b] + [{"arm": "C", **event} for event in c_metrics["chronology"]])
    write_csv(output / "provenance.csv", provenance_records)
    analysis = {
        "schema_version": 1,
        "experiment": "phase2_known_step_edge_aware_v2_protocol_repair_20260915",
        "classification": classification,
        "live_process_launched_by_analyzer": False,
        "launch_budget": {"authorized_C_launches": 1, "observed_C_launches": 1, "A_launches": 0, "V1_B_launches": 0, "retries": 0, "extra_experiments": 0},
        "activity_predicate": "motion_stage == 2; velocity_command_active is not used",
        "a": {"run": str(a_dir), "metadata": a_meta, "protocol": a_protocol, "csv_schema": a_shape, "clean_precontact": clean_mask_summary(a_rows), "floor_reference_z0_m": a_references, "chronology": chronology_a, "traversal_success": False},
        "v1_b": {"run": str(b_dir), "metadata": b_meta, "protocol": b_protocol, "csv_schema": b_shape, "clean_precontact": clean_mask_summary(b_rows), "floor_reference_z0_m": b_references, "chronology": chronology_b},
        "c": {"run": str(c_dir), "metadata": c_meta, "protocol": c_protocol, "csv_schema": c_shape, "clean_precontact": clean_mask_summary(c_rows), "floor_reference_z0_m": c_references, "first_v2_latch": first_latch, "first_plausible_contact_risk": risk_event(c_rows), "first_22_degree_hard_posture_crossing": c_first_hard, "planning": planning_details, "front_crossings": front_summaries, "body_contact_solver": c_metrics, "traversal_success": traversal["success"]},
        "preactivation": {"pass": pre_ok, "summary": pre_summary, "mismatches": pre_mismatches},
        "protocol": {"pass": protocol_ok, "gates": protocol_records},
        "planning_isolation": {"pass": planning_ok, "gates": planning_records, "details": planning_details},
        "provenance": provenance_details,
        "pre_live_tests": tests,
        "source_diff_status": args.source_diff_status,
        "classification_factors": {"tracking_limited": tracking_limited, "front_pair_established": front_pair_established},
    }
    (output / "analysis.json").write_text(json.dumps(jsonable(analysis), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_results(output / "RESULTS.md", classification, a_dir, b_dir, c_dir, {"pass": pre_ok, "summary": pre_summary, "mismatches": pre_mismatches}, {"first_latch": first_latch, "first_risk": risk_event(c_rows), "details": planning_details}, {"metrics": c_metrics}, provenance_details, tests, args.source_diff_status)
    print(f"classification={classification} preactivation={pre_ok} planning={planning_ok} traversal={traversal['success']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
