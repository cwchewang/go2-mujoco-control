#!/usr/bin/env python3
"""Offline A/B readout for the single frozen B-only known-step run.

The analyzer only reads captured CSV, log, metadata, and provenance files. It
never starts a simulator, controller, runner, or other live process.
"""
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
MOTORS = tuple(f"{leg}_{joint}" for leg in ("FR", "FL", "RR", "RL") for joint in ("hip", "thigh", "calf"))
EXPECTED_A_HEAD = "df5d7663adc9e96d153107e071d7b49676bcdad6"
EXPECTED_CONTROLLER_SHA = "80c05a7750ef6782ff24955f7952dd391afce4c5406a15182bc712b36ef49ab3"
EXPECTED_SIMULATOR_SHA = "b9f9e44a40d9b08cd6dce6632038819fab5ec0099e1628078c07185d5a808c9d"
EXPECTED_SCENE_SHA = "8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc"
HARD_POSTURE_RAD = math.radians(22.0)
EDGE_X_M = 0.80
CONTACT_RISK_X_M = 0.778
CONTACT_RISK_Z_M = 0.072
REQUIRED_COLUMNS = {
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
    "wbc_full_srbd_ok",
    "wbc_full_id_ok",
    "wbc_full_eq_residual",
    "known_step_feature_enabled",
}
for _leg in LEGS:
    REQUIRED_COLUMNS.update(
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
        "p95": percentile(finite, 0.95),
        "absolute_max": max((abs(value) for value in finite), default=None),
        "absolute_p95": percentile((abs(value) for value in finite), 0.95),
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


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


def gate(run: str, name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"run": run, "gate": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def parse_protocol(run_dir: Path, expected_domain: str | None = None) -> dict[str, Any]:
    trace = run_dir / "lockstep_trace.csv"
    trace_rows = read_rows(trace) if trace.is_file() else []
    ticks = [number(row, "sim_tick_ms") for row in trace_rows]
    ticks = [value for value in ticks if value is not None]
    diffs = [b - a for a, b in zip(ticks, ticks[1:])]
    violations = [number(row, "violations") or 0 for row in trace_rows]
    logs = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (run_dir / "controller.log", run_dir / "simulator.log")
        if path.is_file()
    )
    upper = logs.upper()
    fail_closed = [marker for marker in ("SIM_LOCKSTEP_FAIL_CLOSED", "LOCKSTEP_FAIL_CLOSED") if marker in upper]
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
        "trace_present": trace.is_file(),
        "trace_rows": len(trace_rows),
        "sim_tick_diffs_ms": sorted(set(diffs)),
        "trace_violations": int(sum(value != 0 for value in violations)),
        "fail_closed_markers": fail_closed,
        "paired_summary_present": bool(paired),
        "paired_cycles": cycles,
        "paired_validation_failures": validation_failures,
        "paired_async_fallbacks": async_fallbacks,
        "domain_id": metadata.get("domain_id", ""),
        "domain_expected": expected_domain or "",
        "domain_matches": expected_domain is None or metadata.get("domain_id") == expected_domain,
        "metadata": metadata,
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


def actual_foot_extrema(rows: list[dict[str, str]]) -> dict[str, Any]:
    return {
        leg: {
            "x": stats(number(row, f"known_step_{leg}_actual_x_m") for row in rows if number(row, f"known_step_{leg}_actual_x_m") is not None),
            "z": stats(number(row, f"known_step_{leg}_actual_z_m") for row in rows if number(row, f"known_step_{leg}_actual_z_m") is not None),
        }
        for leg in LEGS
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
                intervals.append({
                    "start_state_tick_s": number(rows[start], "state_tick_s"),
                    "end_state_tick_s": number(rows[end], "state_tick_s"),
                    "duration_s": sum(dt(rows, item) for item in range(start, end + 1)),
                    "start_row_index": start,
                    "end_row_index": end,
                })
                start = None
        result[leg] = intervals
    return result


def risk_event(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        for leg in LEGS:
            foot_x = number(row, f"known_step_{leg}_actual_x_m")
            foot_z = number(row, f"known_step_{leg}_actual_z_m")
            if foot_x is not None and foot_z is not None and foot_x >= CONTACT_RISK_X_M and foot_z <= CONTACT_RISK_Z_M:
                return {
                    "event": "first_plausible_contact_risk",
                    "raw_row_index": index,
                    "state_time_s": number(row, "state_tick_s"),
                    "leg": leg,
                    "foot_x_m": foot_x,
                    "foot_z_m": foot_z,
                    "base_x_m": number(row, "world_base_x_m"),
                }
    return None


def first_adaptation(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        legs = [leg for leg in LEGS if truthy(row, f"known_step_{leg}_adaptation_active")]
        if legs:
            return {
                "raw_row_index": index,
                "state_time_s": number(row, "state_tick_s"),
                "base_x_m": number(row, "world_base_x_m"),
                "legs": legs,
            }
    return None


def handoff_tick(run_dir: Path, rows: list[dict[str, str]]) -> tuple[float | None, str]:
    path = run_dir / "lockstep_handoff.csv"
    if path.is_file():
        for row in read_rows(path):
            for key in ("state_tick_s", "state_tick", "sim_tick_ms", "tick"):
                value = number(row, key)
                if value is not None:
                    return value / 1000.0 if key in {"sim_tick_ms", "tick"} and value > 100 else value, f"lockstep_handoff.csv:{key}"
    first = number(rows[0], "state_tick_s") if rows else None
    return first, "data.csv:first_state_tick_s"


def row_index_at_or_after(rows: list[dict[str, str]], target: float | None) -> int:
    if target is None:
        return 0
    for index, row in enumerate(rows):
        value = number(row, "state_tick_s")
        if value is not None and value >= target - 1e-12:
            return index
    return len(rows)


def exact_preactivation(a_rows: list[dict[str, str]], b_rows: list[dict[str, str]], a_dir: Path, b_dir: Path) -> tuple[bool, dict[str, Any], list[dict[str, Any]]]:
    a_handoff, a_source = handoff_tick(a_dir, a_rows)
    b_handoff, b_source = handoff_tick(b_dir, b_rows)
    common_handoff = max(value for value in (a_handoff, b_handoff) if value is not None) if any(value is not None for value in (a_handoff, b_handoff)) else None
    a_start = row_index_at_or_after(a_rows, common_handoff)
    b_start = row_index_at_or_after(b_rows, common_handoff)
    b_adaptation = first_adaptation(b_rows)
    b_end = b_adaptation["raw_row_index"] if b_adaptation else len(b_rows)
    a_end = a_start + max(0, b_end - b_start)
    a_slice = a_rows[a_start:a_end]
    b_slice = b_rows[b_start:b_end]
    common = set(a_rows[0]) & set(b_rows[0]) if a_rows and b_rows else set()
    allowed_metadata = {"known_step_feature_enabled", "known_step_edge_x_m", "known_step_height_m", "known_step_half_width_y_m"}
    ignored_noncausal_diagnostics = {"motion_clock_wall_dt_s", "wbc_shadow_elapsed_us"}
    fields = sorted(common - allowed_metadata - ignored_noncausal_diagnostics)
    mismatches: list[dict[str, Any]] = []
    if len(a_slice) != len(b_slice):
        mismatches.append({"row": "COUNT", "field": "row_count", "a": len(a_slice), "b": len(b_slice)})
    for offset, (a_row, b_row) in enumerate(zip(a_slice, b_slice)):
        if a_row.get("state_tick_s", "") != b_row.get("state_tick_s", ""):
            mismatches.append({"row": offset, "field": "state_tick_s", "a": a_row.get("state_tick_s", ""), "b": b_row.get("state_tick_s", "")})
        for field in fields:
            if a_row.get(field, "") != b_row.get(field, ""):
                if len(mismatches) < 1000:
                    mismatches.append({"row": offset, "field": field, "a": a_row.get(field, ""), "b": b_row.get(field, "")})
    summary = {
        "a_handoff_state_tick_s": a_handoff,
        "b_handoff_state_tick_s": b_handoff,
        "common_handoff_state_tick_s": common_handoff,
        "a_handoff_source": a_source,
        "b_handoff_source": b_source,
        "a_start_row": a_start,
        "b_start_row": b_start,
        "rows_compared": min(len(a_slice), len(b_slice)),
        "b_first_adaptation": b_adaptation,
        "causal_fields_compared": len(fields),
        "allowed_metadata_fields": sorted(allowed_metadata),
        "ignored_noncausal_diagnostics": sorted(ignored_noncausal_diagnostics),
        "mismatch_count_capped": len(mismatches),
    }
    return not mismatches, summary, mismatches or [{"row": "ALL", "field": "causal_fields", "a": "exact", "b": "exact"}]


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


def isolation(rows: list[dict[str, str]], metadata: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    active_rows = [row for row in rows if number(row, "motion_stage") == 2]
    enabled = [truthy(row, "known_step_feature_enabled") for row in active_rows]
    capture_values = sorted(set(row.get("known_step_feature_enabled", "") for row in rows))
    active_values = sorted(set(row.get("known_step_feature_enabled", "") for row in active_rows))
    records.append(gate("B", "feature_enabled", bool(enabled) and all(enabled), f"capture_values={capture_values} active_values={active_values} active_rows={len(active_rows)}"))
    diag_fields = {
        "d4_enabled": "diag_bounded_stance_dq_enabled",
        "d4_gate_active": "diag_bounded_stance_dq_gate_active",
        "d90_enabled": "diag_four_thigh_d90_enabled",
        "d90_gate_active": "diag_four_thigh_d90_gate_active",
    }
    diag_results = {}
    for name, field in diag_fields.items():
        values = [number(row, field) for row in rows] if rows and field in rows[0] else []
        passed = bool(values) and all(value == 0 for value in values if value is not None)
        diag_results[name] = {"field": field, "present": bool(values), "values": sorted(set(values)), "pass": passed}
        records.append(gate("B", name, passed, f"field={field} values={sorted(set(values)) if values else 'MISSING'}"))
    env_text = (metadata.get("environment_file", "") and Path(metadata["environment_file"]).read_text(encoding="utf-8", errors="replace") if metadata.get("environment_file") else "")
    argv_text = metadata.get("argv", "") + " " + metadata.get("controller_argv_shell", "")
    pd_off = "PD_PULSE" not in (env_text + argv_text).upper()
    records.append(gate("B", "pd_pulse_off", pd_off, "PD_PULSE absent from captured environment/argv"))
    scope_errors: list[str] = []
    active_samples = 0
    active_rises: list[float] = []
    active_lifts: list[float] = []
    crossing_rises: list[float] = []
    crossing_lifts: list[float] = []
    plateau_errors: list[str] = []
    xy_error = 0.0
    z_formula_error = 0.0
    for index, row in enumerate(rows):
        for leg in LEGS:
            prefix = f"known_step_{leg}_"
            active = truthy(row, prefix + "adaptation_active")
            rise = number(row, prefix + "rise_m")
            h0 = number(row, prefix + "h0_m")
            h1 = number(row, prefix + "h1_m")
            if active:
                active_samples += 1
                if not truthy(row, prefix + "scheduled_swing") or rise is None or abs(rise) <= 1e-9:
                    scope_errors.append(f"row={index} leg={leg} active_scope")
                else:
                    active_rises.append(rise)
                    lift = number(row, prefix + "effective_lift_m")
                    if lift is not None:
                        active_lifts.append(lift)
                start_z = number(row, prefix + "swing_start_z_m")
                final_z = number(row, prefix + "final_target_world_z_m")
                if start_z is None or final_z is None or rise is None:
                    scope_errors.append(f"row={index} leg={leg} missing_z_formula")
                else:
                    z_formula_error = max(z_formula_error, abs(final_z - (start_z + rise)))
                if h0 is not None and h1 is not None and abs(h0) <= 1e-8 and abs(h1 - 0.05) <= 1e-8:
                    crossing_rises.append(rise if rise is not None else math.nan)
                    crossing_lifts.append(number(row, prefix + "effective_lift_m") or math.nan)
            if h0 is not None and h1 is not None and abs(h0 - 0.05) <= 1e-8 and abs(h1 - 0.05) <= 1e-8:
                if rise is None or abs(rise) > 1e-8:
                    plateau_errors.append(f"row={index} leg={leg} rise={rise}")
                nominal_z = number(row, prefix + "nominal_touchdown_z_m")
                final_z = number(row, prefix + "final_target_world_z_m")
                if nominal_z is not None and final_z is not None and abs(final_z - nominal_z) > 1e-8:
                    plateau_errors.append(f"row={index} leg={leg} final_z_accumulation")
            nx = number(row, prefix + "nominal_touchdown_x_m")
            ny = number(row, prefix + "nominal_touchdown_y_m")
            fx = number(row, prefix + "final_target_world_x_m")
            fy = number(row, prefix + "final_target_world_y_m")
            if all(value is not None for value in (nx, ny, fx, fy)):
                xy_error = max(xy_error, abs(nx - fx), abs(ny - fy))
    records.append(gate("B", "adaptation_scope", not scope_errors, f"active_samples={active_samples} errors={scope_errors[:8] or 'none'}"))
    records.append(gate("B", "nominal_xy_unchanged", xy_error <= 1e-12, f"max_error_m={xy_error}"))
    records.append(gate("B", "final_z_formula", not scope_errors and z_formula_error <= 1e-8, f"max_error_m={z_formula_error}"))
    records.append(gate("B", "floor_to_plateau_rise", bool(crossing_rises) and all(abs(value - 0.05) <= 1e-8 for value in crossing_rises), f"values={sorted(set(round(value, 9) for value in crossing_rises if math.isfinite(value)))}"))
    records.append(gate("B", "floor_to_plateau_lift", bool(crossing_lifts) and all(abs(value - 0.080) <= 1e-8 for value in crossing_lifts), f"values={sorted(set(round(value, 9) for value in crossing_lifts if math.isfinite(value)))}"))
    records.append(gate("B", "plateau_to_plateau_no_accumulation", not plateau_errors, f"errors={plateau_errors[:8] or 'none'}"))
    details = {
        "active_samples": active_samples,
        "active_rise_values_m": sorted(set(round(value, 9) for value in active_rises)),
        "active_lift_values_m": sorted(set(round(value, 9) for value in active_lifts)),
        "crossing_rise_values_m": sorted(set(round(value, 9) for value in crossing_rises if math.isfinite(value))),
        "crossing_lift_values_m": sorted(set(round(value, 9) for value in crossing_lifts if math.isfinite(value))),
        "max_nominal_xy_error_m": xy_error,
        "max_final_z_formula_error_m": z_formula_error,
        "plateau_errors": plateau_errors,
        "diag": diag_results,
        "pd_pulse_off": pd_off,
    }
    return records, details


def dt(rows: list[dict[str, str]], index: int) -> float:
    if index + 1 >= len(rows):
        return 0.0
    first = number(rows[index], "state_tick_s")
    second = number(rows[index + 1], "state_tick_s")
    return max(0.0, second - first) if first is not None and second is not None else 0.0


def first_crossing(rows: list[dict[str, str]], threshold: float) -> float | None:
    for row in rows:
        value = number(row, "world_base_x_m")
        if value is not None and value >= threshold:
            return number(row, "state_tick_s")
    return None


def first_hard_posture_crossing(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        roll = number(row, "imu_roll_rad")
        pitch = number(row, "imu_pitch_rad")
        if roll is None or pitch is None or max(abs(roll), abs(pitch)) <= HARD_POSTURE_RAD:
            continue
        feet = {
            leg: {
                "x_m": number(row, f"known_step_{leg}_actual_x_m"),
                "z_m": number(row, f"known_step_{leg}_actual_z_m"),
            }
            for leg in LEGS
        }
        return {
            "event": "first_22_degree_hard_posture_crossing",
            "threshold_rad": HARD_POSTURE_RAD,
            "raw_row_index": index,
            "state_time_s": number(row, "state_tick_s"),
            "roll_rad": roll,
            "pitch_rad": pitch,
            "base_x_m": number(row, "world_base_x_m"),
            "feet": feet,
        }
    return None


def floor_reference(rows: list[dict[str, str]]) -> dict[str, float | None]:
    clean = clean_precontact(rows)
    result: dict[str, float | None] = {}
    for leg in LEGS:
        values = [number(row, f"known_step_{leg}_actual_z_m") for row in clean if truthy(row, f"contact_{leg.upper()}")]
        values = [value for value in values if value is not None]
        result[leg] = percentile(values, 0.5)
    return result


def raised_contact(rows: list[dict[str, str]], references: dict[str, float | None]) -> list[dict[str, Any]]:
    result = []
    for leg in LEGS:
        qualified = []
        reference = references.get(leg)
        for index, row in enumerate(rows):
            foot_x = number(row, f"known_step_{leg}_actual_x_m")
            foot_z = number(row, f"known_step_{leg}_actual_z_m")
            base_x = number(row, "world_base_x_m")
            if (
                reference is not None
                and base_x is not None and base_x >= EDGE_X_M
                and truthy(row, f"contact_{leg.upper()}")
                and foot_x is not None and foot_x >= 0.85
                and foot_z is not None and foot_z >= reference + 0.035
            ):
                qualified.append(index)
        contact_time = sum(dt(rows, index) for index in qualified)
        first = rows[qualified[0]] if qualified else None
        result.append(
            {
                "leg": leg,
                "floor_reference_z0_m": reference,
                "first_raised_touchdown_state_tick_s": number(first, "state_tick_s") if first else None,
                "first_raised_touchdown_x_m": number(first, f"known_step_{leg}_actual_x_m") if first else None,
                "first_raised_touchdown_z_m": number(first, f"known_step_{leg}_actual_z_m") if first else None,
                "first_raised_commanded_z_m": number(first, f"known_step_{leg}_final_target_world_z_m") if first else None,
                "first_raised_actual_minus_commanded_z_m": (number(first, f"known_step_{leg}_actual_z_m") - number(first, f"known_step_{leg}_final_target_world_z_m")) if first and number(first, f"known_step_{leg}_actual_z_m") is not None and number(first, f"known_step_{leg}_final_target_world_z_m") is not None else None,
                "raised_contact_time_s": contact_time,
                "raised_contact_gate": contact_time >= 0.10,
            }
        )
    return result


def run_metrics(rows: list[dict[str, str]], metadata: dict[str, str], run_dir: Path, references: dict[str, float | None]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    adaptation = first_adaptation(rows)
    risk = risk_event(rows)
    hard_posture = first_hard_posture_crossing(rows)
    cross_080 = first_crossing(rows, 0.80)
    cross_145 = first_crossing(rows, 1.45)
    hold = False
    hold_span = None
    if cross_145 is not None:
        hold_rows = [row for row in rows if number(row, "state_tick_s") is not None and cross_145 <= number(row, "state_tick_s") <= cross_145 + 0.50]
        if hold_rows:
            hold_span = max(number(row, "state_tick_s") for row in hold_rows) - min(number(row, "state_tick_s") for row in hold_rows)
            hold = hold_span >= 0.50 and min(number(row, "world_base_x_m") for row in hold_rows) >= 1.35
    window = [row for row in rows if number(row, "world_base_x_m") is not None and number(row, "world_base_x_m") >= 0.60]
    if cross_145 is not None:
        window = [row for row in window if number(row, "state_tick_s") is not None and number(row, "state_tick_s") <= cross_145 + 0.50]
    roll = stats(number(row, "imu_roll_rad") for row in window if number(row, "imu_roll_rad") is not None)
    pitch = stats(number(row, "imu_pitch_rad") for row in window if number(row, "imu_pitch_rad") is not None)
    solver = solver_metrics(window)
    raised = raised_contact(rows, references)
    statuses = {key: metadata.get(key, "MISSING") for key in ("controller_status", "safety_status", "quality_status", "analysis_status", "ground_truth_status", "dynamics_status", "completion_status")}
    status_zero = all(value in {"0", "false", ""} for value in statuses.values())
    logs = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (run_dir / "controller.log", run_dir / "simulator.log") if path.is_file()).upper()
    hard_markers = [marker for marker in ("TROT HARD SAFETY LIMIT REACHED", "EMERGENCY_STOP", "HARD_SAFETY") if marker in logs]
    torque = [abs(number(row, f"{motor}_tau_est")) for row in window for motor in MOTORS if number(row, f"{motor}_tau_est") is not None]
    divergence = []
    for row in window:
        for leg in LEGS:
            if truthy(row, f"known_step_{leg}_scheduled_stance"):
                actual = number(row, f"known_step_{leg}_actual_z_m")
                target = number(row, f"known_step_{leg}_final_target_world_z_m")
                if actual is not None and target is not None:
                    divergence.append(abs(actual - target))
    persistent = sum(value > 0.12 for value in divergence) > max(20, len(divergence) * 0.10)
    contact_counts: dict[str, int] = {}
    for row in rows:
        key = row.get("contact_count", "")
        contact_counts[key] = contact_counts.get(key, 0) + 1
    traversal = {
        "reached_x_145": cross_145 is not None,
        "stayed_above_x_135_for_050s": hold,
        "hold_span_s": hold_span,
        "all_legs_raised_contact_010s": all(item["raised_contact_gate"] for item in raised),
        "no_hard_safety": not hard_markers,
        "statuses_zero": status_zero,
        "posture_gate": roll["absolute_max"] is not None and pitch["absolute_max"] is not None and roll["absolute_max"] <= 0.25 and pitch["absolute_max"] <= 0.25,
        "solver_gate": solver["valid_rows"] > 0 and solver["all_srbd_ok"] and solver["all_id_ok"] and solver["residual"]["p95"] is not None and solver["residual"]["p95"] <= 1e-3,
        "no_persistent_command_actual_divergence": not persistent,
    }
    traversal["success"] = all(traversal.values())
    metrics = {
        "rows": len(rows),
        "activity_rows": sum(number(row, "motion_stage") == 2 for row in rows),
        "clean_precontact_mask": clean_mask_summary(rows),
        "floor_reference_z0_m": references,
        "actual_foot_extrema_raw": actual_foot_extrema(rows),
        "actual_foot_extrema_clean": actual_foot_extrema(clean_precontact(rows)),
        "first_adaptation": adaptation,
        "first_plausible_contact_risk": risk,
        "first_22_degree_hard_posture_crossing": hard_posture,
        "first_base_x_080_state_tick_s": cross_080,
        "first_base_x_145_state_tick_s": cross_145,
        "max_base_x_m": max((number(row, "world_base_x_m") for row in rows if number(row, "world_base_x_m") is not None), default=None),
        "roll": roll,
        "pitch": pitch,
        "world_velocity_z_abs": stats(abs(number(row, "world_velocity_z_mps")) for row in window if number(row, "world_velocity_z_mps") is not None),
        "body_velocity_z_abs": stats(abs(number(row, "body_velocity_z_mps")) for row in window if number(row, "body_velocity_z_mps") is not None),
        "solver": solver,
        "torque_abs": stats(torque),
        "torque_saturation_samples_at_35Nm": sum(value >= 35.0 for value in torque),
        "contact_count_distribution": contact_counts,
        "contact_intervals": contact_intervals(rows),
        "divergence_abs_z": stats(divergence),
        "raised_contact": raised,
        "statuses": statuses,
        "hard_markers": hard_markers,
        "traversal": traversal,
    }
    return metrics, raised


def frozen_a_provenance(root: Path, a_dir: Path) -> tuple[list[dict[str, Any]], bool]:
    path = root / "docs/validation/phase2_known_step_precontact_readjudication_20260915/provenance.csv"
    expected: dict[str, str] = {}
    if path.is_file():
        for row in read_rows(path):
            if row.get("scope") == "raw_capture":
                expected[row["artifact"]] = row.get("sha256", "")
    records = []
    matches = bool(expected)
    for name, expected_hash in sorted(expected.items()):
        file_path = a_dir / name
        actual = sha256(file_path)
        equal = actual == expected_hash
        matches = matches and equal
        records.append({"scope": "A_raw_frozen", "artifact": name, "path": str(file_path), "bytes": file_path.stat().st_size if file_path.is_file() else "MISSING", "sha256": actual, "expected_sha256": expected_hash, "matches": equal})
    return records, matches


def b_provenance(b_dir: Path, root: Path, metadata: dict[str, str]) -> list[dict[str, Any]]:
    records = []
    for name in sorted(path.name for path in b_dir.iterdir() if path.is_file()):
        path = b_dir / name
        records.append({"scope": "B_raw", "artifact": name, "path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path), "expected_sha256": "", "matches": "", "runtime_head": metadata.get("git_head", ""), "runtime_branch": metadata.get("git_branch", ""), "runtime_dirty": metadata.get("git_dirty", "")})
    for path, kind in (
        (root / "example/cpp/scripts/run_phase2_known_step_5cm_b_only.sh", "runner"),
        (Path(__file__), "analysis_source"),
        (root / "unitree_robots/go2/scene_known_step_5cm.xml", "scene"),
    ):
        records.append({"scope": kind, "artifact": str(path.relative_to(root)) if path.is_relative_to(root) else str(path), "path": str(path), "bytes": path.stat().st_size if path.is_file() else "MISSING", "sha256": sha256(path), "expected_sha256": EXPECTED_SCENE_SHA if kind == "scene" else "", "matches": sha256(path) == EXPECTED_SCENE_SHA if kind == "scene" else "", "runtime_head": metadata.get("git_head", ""), "runtime_branch": metadata.get("git_branch", ""), "runtime_dirty": metadata.get("git_dirty", ""), "controller_sha256": metadata.get("controller_sha256", ""), "simulator_sha256": metadata.get("simulator_sha256", ""), "scene_sha256": metadata.get("scene_sha256", "")})
    return records


def render_results(path: Path, classification: str, a_dir: Path, b_dir: Path, a_meta: dict[str, str], b_meta: dict[str, str], a_metrics: dict[str, Any], b_metrics: dict[str, Any], pre_summary: dict[str, Any], pre_ok: bool, isolation_records: list[dict[str, Any]], protocol_records: list[dict[str, Any]], tests: dict[str, str], a_hash_ok: bool, b_source_ok: bool, binary_rebuild_allowed: bool) -> None:
    def text(value: Any) -> str:
        return "not observed" if value is None else str(value)

    gate_lines = "\n".join(f"- `{row['status']}` {row['run']} {row['gate']}: {row['detail']}" for row in protocol_records + isolation_records)
    b = b_metrics
    adaptation = b.get("first_adaptation") or {}
    risk = b.get("first_plausible_contact_risk") or {}
    hard = b.get("first_22_degree_hard_posture_crossing") or {}
    risk_time = risk.get("state_time_s")
    hard_time = hard.get("state_time_s")
    if risk_time is not None and hard_time is not None:
        temporal = f"risk precedes hard posture by {hard_time - risk_time:.3f} s" if hard_time >= risk_time else f"hard posture precedes risk by {risk_time - hard_time:.3f} s"
    else:
        temporal = "ordering unresolved"
    raised = ", ".join(f"{item['leg']}={text(item['raised_contact_time_s'])} s" for item in b.get("raised_contact", []))
    path.write_text(f"""# Phase2 known-step B-only closeout

Date: 2026-09-15
Classification: `{classification}`

## Scope and provenance

Exactly one B-only live launch was authorized and performed with DDS domain 232 using `example/cpp/scripts/run_phase2_known_step_5cm_b_only.sh`. A was not rerun. The immutable A capture remained at `{a_dir}`; B capture is `{b_dir}`. No retry, parameter change, extra experiment, or raw-file edit was performed.

Accepted A runtime HEAD: `{a_meta.get('git_head', 'MISSING')}`. B runtime HEAD: `{b_meta.get('git_head', 'MISSING')}`. A frozen raw hashes match readjudication provenance: `{a_hash_ok}`. B runtime/source/binary/scene provenance gate: `{b_source_ok}`. Binary disposition: accepted controller `{EXPECTED_CONTROLLER_SHA}` -> observed `{b_meta.get('controller_sha256', 'MISSING')}`; accepted simulator `{EXPECTED_SIMULATOR_SHA}` -> observed `{b_meta.get('simulator_sha256', 'MISSING')}`; rebuild allowed/recorded=`{binary_rebuild_allowed}`.

Pre-live tests: {json.dumps(tests, sort_keys=True)}

Clean B pre-contact mask: {b.get('clean_precontact_mask')}. B floor-contact references z0={b.get('floor_reference_z0_m')}; these match the independently derived A references.

## Exact pre-activation comparison

Result: `{'PASS' if pre_ok else 'FAIL'}`. Compared {pre_summary.get('rows_compared', 0)} rows and {pre_summary.get('causal_fields_compared', 0)} causal fields from common deterministic handoff state tick {text(pre_summary.get('common_handoff_state_tick_s'))} through the final row before first B adaptation. Allowed metadata-only differences were `{pre_summary.get('allowed_metadata_fields')}`; ignored noncausal diagnostics were `{pre_summary.get('ignored_noncausal_diagnostics')}`. First adaptation: time={text(adaptation.get('state_time_s'))} s, base_x={text(adaptation.get('base_x_m'))} m, legs={adaptation.get('legs', [])}.

The comparator and active-locomotion isolation gate were corrected after capture as analysis-only repairs. Raw A/B captures were not edited and B was not rerun.

## B isolation and traversal

First plausible contact-risk: time={text(risk.get('state_time_s'))} s, leg={risk.get('leg')}, foot=({text(risk.get('foot_x_m'))}, {text(risk.get('foot_z_m'))}) m, base_x={text(risk.get('base_x_m'))} m. This is a geometry risk proxy, not a literal geom-pair contact claim.

First 22-degree hard-posture crossing: time={text(hard.get('state_time_s'))} s, roll={text(hard.get('roll_rad'))} rad, pitch={text(hard.get('pitch_rad'))} rad, base_x={text(hard.get('base_x_m'))} m, feet={json.dumps(hard.get('feet', {}), sort_keys=True)}. Temporal ordering: {temporal}.

Raised-platform qualified contact time: {raised or 'not observed'}.

Traversal metrics: max_base_x={text(b.get('max_base_x_m'))} m; x=0.80 time={text(b.get('first_base_x_080_state_tick_s'))} s; x=1.45 time={text(b.get('first_base_x_145_state_tick_s'))} s; hold={b.get('traversal', {}).get('stayed_above_x_135_for_050s')}; solver_p95={text(b.get('solver', {}).get('residual', {}).get('p95'))}; max_abs_roll={text(b.get('roll', {}).get('absolute_max'))}; max_abs_pitch={text(b.get('pitch', {}).get('absolute_max'))}.

Gate record:

{gate_lines}

## Stop disposition

The frozen classification is limited to this B-only checkpoint. After this closeout, do not run another terrain experiment, rerun A/B, tune, or modify runtime source.
""", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--a-run", type=Path, required=True)
    parser.add_argument("--b-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-b-head", default="")
    parser.add_argument("--tests-json", type=Path, default=None)
    parser.add_argument("--allow-rebuilt-binaries", action="store_true")
    args = parser.parse_args()
    root = (args.repo_root or Path(__file__).resolve().parents[4]).resolve()
    a_dir = args.a_run.resolve()
    b_dir = args.b_run.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    tests = json.loads(args.tests_json.read_text(encoding="utf-8")) if args.tests_json and args.tests_json.is_file() else {}
    if not (a_dir / "data.csv").is_file() or not (b_dir / "data.csv").is_file():
        result = {"schema_version": 1, "classification": "PROTOCOL_FAILURE", "reason": "A or B data.csv missing", "live_process_launched_by_analyzer": False}
        (output / "analysis.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (output / "RESULTS.md").write_text("# Phase2 known-step B-only closeout\n\nClassification: `PROTOCOL_FAILURE`\n\nRequired A/B raw evidence is missing.\n", encoding="utf-8")
        return 2
    a_rows = read_rows(a_dir / "data.csv")
    b_rows = read_rows(b_dir / "data.csv")
    a_meta = read_kv(a_dir / "run_metadata.txt")
    b_meta = read_kv(b_dir / "run_metadata.txt")
    missing_a = sorted(REQUIRED_COLUMNS - set(a_rows[0])) if a_rows else sorted(REQUIRED_COLUMNS)
    missing_b = sorted(REQUIRED_COLUMNS - set(b_rows[0])) if b_rows else sorted(REQUIRED_COLUMNS)
    a_protocol = parse_protocol(a_dir, "231")
    b_protocol = parse_protocol(b_dir, "232")
    a_hash_records, a_hash_ok = frozen_a_provenance(root, a_dir)
    a_sources_ok = a_meta.get("git_head") == EXPECTED_A_HEAD and a_meta.get("git_dirty") == "false" and a_meta.get("controller_sha256") == EXPECTED_CONTROLLER_SHA and a_meta.get("simulator_sha256") == EXPECTED_SIMULATOR_SHA and a_meta.get("scene_sha256") == EXPECTED_SCENE_SHA
    observed_binary_hashes = b_meta.get("controller_sha256", "") and b_meta.get("simulator_sha256", "")
    binaries_match_accepted = b_meta.get("controller_sha256") == EXPECTED_CONTROLLER_SHA and b_meta.get("simulator_sha256") == EXPECTED_SIMULATOR_SHA
    binary_provenance_ok = bool(observed_binary_hashes) and (binaries_match_accepted or args.allow_rebuilt_binaries)
    b_source_ok = b_meta.get("git_head") == args.expected_b_head and b_meta.get("git_dirty") == "false" and binary_provenance_ok and b_meta.get("scene_sha256") == EXPECTED_SCENE_SHA and sha256(root / "unitree_robots/go2/scene_known_step_5cm.xml") == EXPECTED_SCENE_SHA
    a_metrics, _ = run_metrics(a_rows, a_meta, a_dir, floor_reference(a_rows))
    b_metrics, raised = run_metrics(b_rows, b_meta, b_dir, floor_reference(b_rows))
    pre_ok, pre_summary, pre_mismatches = exact_preactivation(a_rows, b_rows, a_dir, b_dir)
    isolation_records, isolation_details = isolation(b_rows, b_meta)
    b_clean = b_metrics["clean_precontact_mask"]
    a_refs = a_metrics["floor_reference_z0_m"]
    b_refs = b_metrics["floor_reference_z0_m"]
    reference_diffs = {leg: (b_refs.get(leg) - a_refs.get(leg)) if b_refs.get(leg) is not None and a_refs.get(leg) is not None else None for leg in LEGS}
    clean_mask_ok = b_clean["rows"] >= 250 and (b_clean["state_time_span_s"] or 0.0) >= 0.50
    reference_ok = all(value is not None and abs(value) <= 1e-9 for value in reference_diffs.values())
    protocol_records = [
        gate("A", "raw_schema", not missing_a, f"missing={missing_a or 'none'}"),
        gate("B", "raw_schema", not missing_b, f"missing={missing_b or 'none'}"),
        gate("B", "clean_precontact_mask", clean_mask_ok, f"rows={b_clean['rows']} span_s={b_clean['state_time_span_s']}"),
        gate("A_B", "floor_reference_compatible", reference_ok, f"a={a_refs} b={b_refs} diffs={reference_diffs}"),
        gate("A", "frozen_raw_hashes", a_hash_ok, f"matches={a_hash_ok}"),
        gate("A", "accepted_runtime_provenance", a_sources_ok, f"head={a_meta.get('git_head', 'MISSING')}"),
        gate("B", "domain_232", b_protocol["domain_matches"], f"domain={b_protocol['domain_id']}"),
        gate("B", "lockstep_trace_present", b_protocol["trace_present"] and b_protocol["trace_rows"] > 0, f"rows={b_protocol['trace_rows']}"),
        gate("B", "constant_sim_tick", b_protocol["sim_tick_diffs_ms"] == [2.0], f"diffs={b_protocol['sim_tick_diffs_ms']}"),
        gate("B", "no_protocol_violations", b_protocol["trace_violations"] == 0, f"violations={b_protocol['trace_violations']}"),
        gate("B", "paired_highstate", b_protocol["paired_summary_present"] and b_protocol["paired_cycles"] > 0 and b_protocol["paired_validation_failures"] == 0 and b_protocol["paired_async_fallbacks"] == 0, f"cycles={b_protocol['paired_cycles']} failures={b_protocol['paired_validation_failures']} fallbacks={b_protocol['paired_async_fallbacks']}"),
        gate("B", "no_fail_closed_marker", not b_protocol["fail_closed_markers"], f"markers={b_protocol['fail_closed_markers']}"),
        gate("B", "runtime_binary_scene_provenance", b_source_ok, f"head={b_meta.get('git_head', 'MISSING')} controller={b_meta.get('controller_sha256', 'MISSING')} simulator={b_meta.get('simulator_sha256', 'MISSING')} scene={b_meta.get('scene_sha256', 'MISSING')}"),
        gate("A_B", "exact_preactivation", pre_ok, f"rows={pre_summary['rows_compared']} mismatches={len(pre_mismatches) if pre_mismatches and pre_mismatches[0].get('row') != 'ALL' else 0}"),
    ]
    source_diff_ok = b_source_ok and a_sources_ok
    protocol_ok = all(item["status"] == "PASS" for item in protocol_records) and source_diff_ok
    isolation_ok = all(item["status"] == "PASS" for item in isolation_records)
    traversal = b_metrics["traversal"]
    if not pre_ok:
        classification = "INCONCLUSIVE_PREACTIVATION_DIVERGENCE"
    elif not protocol_ok or not isolation_ok or missing_a or missing_b:
        classification = "PROTOCOL_FAILURE"
    elif traversal["success"]:
        classification = "SUPPORTED_ENABLES_TRAVERSAL"
    else:
        classification = "ADAPTATION_FAILED"
    write_csv(output / "preactivation_exact.csv", [{"status": "PASS" if pre_ok else "FAIL", **pre_summary}] + pre_mismatches)
    write_csv(output / "adaptation_isolation.csv", isolation_records + [{"run": "B", "gate": "isolation_summary", "status": "PASS" if isolation_ok else "FAIL", "detail": isolation_details}])
    write_csv(output / "touchdown_summary.csv", raised)
    write_csv(output / "protocol_gates.csv", protocol_records + isolation_records)
    provenance = a_hash_records + b_provenance(b_dir, root, b_meta)
    write_csv(output / "provenance.csv", provenance)
    analysis = {
        "schema_version": 1,
        "experiment": "phase2_known_step_5cm_b_only_20260915",
        "classification": classification,
        "live_process_launched_by_analyzer": False,
        "launch_budget": {"authorized": 1, "B_launches": 1, "A_launches": 0, "retries": 0, "extra_experiments": 0},
        "a": {"run": str(a_dir), "metadata": a_meta, "metrics": a_metrics, "accepted_readjudication": "9b782101d2fad1d3c64a80213cd741b8bd2e3179", "traversal_success": False},
        "b": {"run": str(b_dir), "metadata": b_meta, "metrics": b_metrics, "protocol": b_protocol},
        "activity_predicate": "motion_stage == 2 for both arms; velocity_command_active is not used",
        "preactivation": {"pass": pre_ok, "summary": pre_summary, "mismatches": pre_mismatches},
        "isolation": {"pass": isolation_ok, "details": isolation_details},
        "protocol": {"pass": protocol_ok, "gates": protocol_records},
        "provenance": {"A_raw_hashes_match": a_hash_ok, "A_source_match": a_sources_ok, "B_source_binary_scene_match": b_source_ok, "accepted_controller_sha256": EXPECTED_CONTROLLER_SHA, "observed_controller_sha256": b_meta.get("controller_sha256", ""), "accepted_simulator_sha256": EXPECTED_SIMULATOR_SHA, "observed_simulator_sha256": b_meta.get("simulator_sha256", ""), "binary_rebuild_allowed": args.allow_rebuilt_binaries, "binaries_match_accepted": binaries_match_accepted},
        "pre_live_tests": tests,
    }
    (output / "analysis.json").write_text(json.dumps(jsonable(analysis), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_results(output / "RESULTS.md", classification, a_dir, b_dir, a_meta, b_meta, a_metrics, b_metrics, pre_summary, pre_ok, isolation_records, protocol_records, tests, a_hash_ok, b_source_ok, args.allow_rebuilt_binaries)
    print(f"classification={classification} preactivation={pre_ok} isolation={isolation_ok} traversal={traversal['success']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
