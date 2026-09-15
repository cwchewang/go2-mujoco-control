#!/usr/bin/env python3
"""Offline geometry-valid readjudication for the frozen known-step A capture.

This module only reads CSV, text, and metadata artifacts.  It never starts a
simulator, controller, runner, or other live process.
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
EXPECTED_RUNTIME_HEAD = "df5d7663adc9e96d153107e071d7b49676bcdad6"
HARD_POSTURE_RAD = math.radians(22.0)
STEP_EDGE_X_M = 0.80
FOOT_RADIUS_M = 0.022
FOOT_MARGIN_M = 0.001
CONTACT_RISK_X_M = STEP_EDGE_X_M - FOOT_RADIUS_M
CONTACT_RISK_Z_M = 0.05 + FOOT_RADIUS_M
CLEAN_BASE_X_M = 0.40
CLEAN_FOOT_X_M = 0.75
REQUIRED_COLUMNS = {
    "motion_stage",
    "state_tick_s",
    "world_base_x_m",
    "imu_roll_rad",
    "imu_pitch_rad",
    "known_step_feature_enabled",
    "wbc_full_srbd_ok",
    "wbc_full_id_ok",
    "wbc_full_eq_residual",
}
for _leg in LEGS:
    REQUIRED_COLUMNS.update(
        {
            f"known_step_{_leg}_actual_x_m",
            f"known_step_{_leg}_actual_z_m",
            f"known_step_{_leg}_adaptation_active",
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


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(value for value in values if math.isfinite(value))
    if not ordered:
        return None
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def extrema(values: Iterable[float]) -> dict[str, float | None]:
    finite = [value for value in values if math.isfinite(value)]
    return {
        "min": min(finite) if finite else None,
        "max": max(finite) if finite else None,
        "p95": percentile(finite, 0.95),
        "count": len(finite),
    }


def signed_and_absolute(values: Iterable[float]) -> dict[str, float | None]:
    finite = [value for value in values if math.isfinite(value)]
    return {
        "signed_min": min(finite) if finite else None,
        "signed_max": max(finite) if finite else None,
        "signed_p95": percentile(finite, 0.95),
        "absolute_max": max((abs(value) for value in finite), default=None),
        "absolute_p95": percentile((abs(value) for value in finite), 0.95),
        "count": len(finite),
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def read_key_values(path: Path) -> dict[str, str]:
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


def gate(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"gate": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def parse_protocol(run_dir: Path) -> dict[str, Any]:
    trace_path = run_dir / "lockstep_trace.csv"
    trace_rows = read_rows(trace_path) if trace_path.is_file() else []
    ticks = [number(row, "sim_tick_ms") for row in trace_rows]
    ticks = [value for value in ticks if value is not None]
    violations = [number(row, "violations") or 0.0 for row in trace_rows]
    fail_closed_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (run_dir / "controller.log", run_dir / "simulator.log")
        if path.is_file()
    ).upper()
    fail_closed_markers = [
        marker
        for marker in ("SIM_LOCKSTEP_FAIL_CLOSED", "LOCKSTEP_FAIL_CLOSED", "FAIL_CLOSED")
        if marker in fail_closed_text
    ]
    summary_text = (
        (run_dir / "controller.log").read_text(encoding="utf-8", errors="replace")
        if (run_dir / "controller.log").is_file()
        else ""
    )
    matches = re.findall(
        r"PAIRED_HIGHSTATE_SUMMARY\s+cycles=(\d+)\s+validation_failures=(\d+)\s+async_fallbacks=(\d+)",
        summary_text,
    )
    if matches:
        cycles, validation_failures, async_fallbacks = map(int, matches[-1])
    else:
        cycles = validation_failures = async_fallbacks = None
    tick_diffs = [b - a for a, b in zip(ticks, ticks[1:])]
    return {
        "trace_present": trace_path.is_file(),
        "trace_rows": len(trace_rows),
        "sim_tick_diffs_ms": sorted(set(tick_diffs)),
        "trace_violations": int(sum(value != 0 for value in violations)),
        "fail_closed_markers": fail_closed_markers,
        "paired_summary_present": bool(matches),
        "paired_cycles": cycles,
        "paired_validation_failures": validation_failures,
        "paired_async_fallbacks": async_fallbacks,
    }


def raw_artifact_hashes(root: Path, run_dir: Path) -> tuple[list[dict[str, Any]], bool]:
    frozen = root / "docs/validation/phase2_known_step_wallclock_repair_20260915/provenance.csv"
    expected: dict[str, str] = {}
    if frozen.is_file():
        for row in read_rows(frozen):
            artifact = row.get("artifact", "")
            if "/A/" in artifact and row.get("sha256"):
                expected[Path(artifact).name] = row["sha256"]
    records: list[dict[str, Any]] = []
    all_match = bool(expected)
    for name, expected_hash in sorted(expected.items()):
        path = run_dir / name
        actual_hash = sha256(path)
        matches = actual_hash == expected_hash
        all_match = all_match and matches
        records.append(
            {
                "scope": "raw_capture",
                "artifact": name,
                "path": str(path),
                "bytes": path.stat().st_size if path.is_file() else "MISSING",
                "sha256": actual_hash,
                "expected_sha256": expected_hash,
                "matches_frozen_provenance": matches,
            }
        )
    return records, all_match


def activity_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    corrected = [row for row in rows if number(row, "motion_stage") == 2.0]
    old = [
        row
        for row in corrected
        if truthy(row, "velocity_command_active")
    ]
    return {
        "old_predicate": "motion_stage == 2 AND velocity_command_active",
        "corrected_predicate": "motion_stage == 2",
        "old_active_rows": len(old),
        "corrected_active_rows": len(corrected),
        "velocity_command_active_rows": sum(truthy(row, "velocity_command_active") for row in rows),
    }


def clean_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    selected: list[dict[str, str]] = []
    missing_values = 0
    for row in rows:
        if number(row, "motion_stage") != 2.0:
            continue
        base_x = number(row, "world_base_x_m")
        foot_x = [number(row, f"known_step_{leg}_actual_x_m") for leg in LEGS]
        if base_x is None or any(value is None for value in foot_x):
            missing_values += 1
            continue
        if base_x <= CLEAN_BASE_X_M and all(value < CLEAN_FOOT_X_M for value in foot_x if value is not None):
            selected.append(row)
    return selected, missing_values


def posture_event(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        roll = number(row, "imu_roll_rad")
        pitch = number(row, "imu_pitch_rad")
        if roll is None or pitch is None:
            continue
        if abs(roll) > HARD_POSTURE_RAD or abs(pitch) > HARD_POSTURE_RAD:
            event: dict[str, Any] = {
                "event": "first_hard_posture_crossing",
                "raw_row_index": index,
                "state_time_s": number(row, "state_tick_s"),
                "roll_rad": roll,
                "pitch_rad": pitch,
                "base_x_m": number(row, "world_base_x_m"),
            }
            for leg in LEGS:
                event[f"{leg}_foot_x_m"] = number(row, f"known_step_{leg}_actual_x_m")
                event[f"{leg}_foot_z_m"] = number(row, f"known_step_{leg}_actual_z_m")
            return event
    return None


def contact_event(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    for index, row in enumerate(rows):
        candidates: list[dict[str, Any]] = []
        for leg in LEGS:
            foot_x = number(row, f"known_step_{leg}_actual_x_m")
            foot_z = number(row, f"known_step_{leg}_actual_z_m")
            if (
                foot_x is not None
                and foot_z is not None
                and foot_x >= CONTACT_RISK_X_M
                and foot_z <= CONTACT_RISK_Z_M
            ):
                candidates.append({"leg": leg, "foot_x_m": foot_x, "foot_z_m": foot_z})
        if candidates:
            first = candidates[0]
            return {
                "event": "first_plausible_contact_risk",
                "raw_row_index": index,
                "state_time_s": number(row, "state_tick_s"),
                "leg": first["leg"],
                "coincident_legs": [item["leg"] for item in candidates],
                "foot_x_m": first["foot_x_m"],
                "foot_z_m": first["foot_z_m"],
                "base_x_m": number(row, "world_base_x_m"),
                "x_threshold_m": CONTACT_RISK_X_M,
                "z_threshold_m": CONTACT_RISK_Z_M,
            }
    return None


def actual_extrema(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, float | None]]]:
    result: dict[str, dict[str, dict[str, float | None]]] = {}
    for leg in LEGS:
        result[leg] = {
            "x": extrema(number(row, f"known_step_{leg}_actual_x_m") for row in rows if number(row, f"known_step_{leg}_actual_x_m") is not None),
            "z": extrema(number(row, f"known_step_{leg}_actual_z_m") for row in rows if number(row, f"known_step_{leg}_actual_z_m") is not None),
        }
    return result


def solver_stats(rows: list[dict[str, str]]) -> dict[str, Any]:
    valid = []
    for row in rows:
        residual = number(row, "wbc_full_eq_residual")
        srbd = number(row, "wbc_full_srbd_ok")
        ident = number(row, "wbc_full_id_ok")
        if residual is not None and srbd is not None and ident is not None:
            valid.append((row, residual, srbd > 0.5, ident > 0.5))
    residuals = [abs(item[1]) for item in valid]
    return {
        "valid_rows": len(valid),
        "srbd_success_fraction": sum(item[2] for item in valid) / len(valid) if valid else None,
        "id_success_fraction": sum(item[3] for item in valid) / len(valid) if valid else None,
        "both_success_fraction": sum(item[2] and item[3] for item in valid) / len(valid) if valid else None,
        "all_srbd_ok": bool(valid) and all(item[2] for item in valid),
        "all_id_ok": bool(valid) and all(item[3] for item in valid),
        "residual": extrema(residuals),
    }


def chronology_rows(contact: dict[str, Any] | None, posture: dict[str, Any] | None, ordering: str, delta: float | None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if contact is not None:
        records.append({"event": "first_plausible_contact_risk", "ordering": ordering, "delta_hard_minus_risk_s": delta, **contact})
    else:
        records.append({"event": "first_plausible_contact_risk", "ordering": ordering, "delta_hard_minus_risk_s": delta, "status": "NOT_OBSERVED"})
    if posture is not None:
        records.append({"event": "first_hard_posture_crossing", "ordering": ordering, "delta_hard_minus_risk_s": delta, **posture})
    else:
        records.append({"event": "first_hard_posture_crossing", "ordering": ordering, "delta_hard_minus_risk_s": delta, "status": "NOT_OBSERVED"})
    records.append({"event": "ordering_summary", "ordering": ordering, "delta_hard_minus_risk_s": delta})
    return records


def classify(
    required_columns_ok: bool,
    clean_count: int,
    clean_span: float | None,
    health_ok: bool,
    contact: dict[str, Any] | None,
    posture: dict[str, Any] | None,
) -> str:
    if not required_columns_ok or clean_count < 250 or clean_span is None or clean_span < 0.50:
        return "INSUFFICIENT_EVIDENCE"
    if health_ok and contact and posture:
        risk_time = contact.get("state_time_s")
        posture_time = posture.get("state_time_s")
        if risk_time is not None and posture_time is not None and posture_time >= risk_time:
            return "PRECONTACT_BASELINE_HEALTHY_CONTACT_CONFOUNDED"
        if risk_time is not None and posture_time is not None and posture_time < risk_time:
            return "PRECONTACT_BASELINE_UNHEALTHY"
    if health_ok:
        return "PRECONTACT_BASELINE_HEALTHY_ORDER_UNRESOLVED"
    return "PRECONTACT_BASELINE_UNHEALTHY"


def render_results(
    path: Path,
    classification: str,
    run_dir: Path,
    expected_head: str,
    activity: dict[str, Any],
    clean_count: int,
    clean_span: float | None,
    health: dict[str, Any],
    gates: list[dict[str, Any]],
    contact: dict[str, Any] | None,
    posture: dict[str, Any] | None,
    ordering: str,
    delta: float | None,
    protocol: dict[str, Any],
    provenance_ok: bool,
    raw_hash_ok: bool,
) -> None:
    def val(value: Any) -> str:
        return "not observed" if value is None else str(value)

    gate_lines = "\n".join(f"- `{item['status']}` {item['gate']}: {item['detail']}" for item in gates)
    contact_line = "not observed"
    if contact:
        contact_line = (
            f"t={val(contact.get('state_time_s'))} s, leg={contact.get('leg')}, "
            f"foot=({val(contact.get('foot_x_m'))}, {val(contact.get('foot_z_m'))}) m, "
            f"base_x={val(contact.get('base_x_m'))} m; coincident legs={contact.get('coincident_legs')}"
        )
    posture_line = "not observed"
    if posture:
        feet = ", ".join(
            f"{leg}=({val(posture.get(f'{leg}_foot_x_m'))}, {val(posture.get(f'{leg}_foot_z_m'))})"
            for leg in LEGS
        )
        posture_line = (
            f"t={val(posture.get('state_time_s'))} s, roll={val(posture.get('roll_rad'))} rad, "
            f"pitch={val(posture.get('pitch_rad'))} rad, base_x={val(posture.get('base_x_m'))} m; {feet}"
        )
    gate_block = gate_lines or "(none)"
    text = f"""# Phase2 known-step pre-contact readjudication

Date: 2026-09-15
Classification: `{classification}`

## Evidence boundary

This is a pure offline readjudication of the frozen A capture at `{run_dir}`. No simulator, controller, B arm, runner, or live process was launched. Raw capture bytes were not modified. Runtime source, terrain adapter, scene, gait, WBC/MPC/ID, and thresholds were not modified.

Frozen runtime provenance: `git_head={expected_head}`; raw hashes match the prior wall-clock-repair provenance: `{raw_hash_ok}`; runtime metadata/source hashes match: `{provenance_ok}`.

## Corrected activity predicate and clean mask

The old analyzer used `{activity['old_predicate']}` and selected {activity['old_active_rows']} rows. This checkpoint uses `{activity['corrected_predicate']}` and selects {activity['corrected_active_rows']} rows; `velocity_command_active` is not an activity gate because this full2 capture has no runtime velocity command.

Clean pre-contact is `motion_stage == 2`, `world_base_x_m <= 0.40 m`, and every actual foot-center x `< 0.75 m`. It contains {clean_count} rows with state-time span {val(clean_span)} s.

## Clean pre-contact health

- roll: signed min/max/p95 = {val(health['roll']['signed_min'])}/{val(health['roll']['signed_max'])}/{val(health['roll']['signed_p95'])} rad; absolute max/p95 = {val(health['roll']['absolute_max'])}/{val(health['roll']['absolute_p95'])} rad
- pitch: signed min/max/p95 = {val(health['pitch']['signed_min'])}/{val(health['pitch']['signed_max'])}/{val(health['pitch']['signed_p95'])} rad; absolute max/p95 = {val(health['pitch']['absolute_max'])}/{val(health['pitch']['absolute_p95'])} rad
- WBC valid rows={health['solver']['valid_rows']}; SRBD success={val(health['solver']['srbd_success_fraction'])}; ID success={val(health['solver']['id_success_fraction'])}; equality residual p95={val(health['solver']['residual']['p95'])}
- adaptation enabled samples={health['adaptation_enabled_samples']}; adaptation-active samples={health['adaptation_active_samples']}; protocol/paired checks={health['protocol_ok']}

Gate disposition:

{gate_block}

## Contact-risk chronology

First `plausible_contact_risk` (not literal geom-pair contact): {contact_line}

First raw 22-degree hard-posture crossing: {posture_line}

Ordering: `{ordering}`; hard-posture time minus risk time = `{val(delta)}` s.

## Stop disposition

This result does not authorize B or any follow-up runtime experiment. It is a readjudication of the old base-x proxy and the activity predicate only; any favorable result may be used by the planner/reviewer to prepare a separately preregistered checkpoint.
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-runtime-head", default=EXPECTED_RUNTIME_HEAD)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[4]
    run_dir = args.runs_root.resolve() / "A"
    output = args.output_dir.resolve()
    data_path = run_dir / "data.csv"
    metadata_path = run_dir / "run_metadata.txt"
    output.mkdir(parents=True, exist_ok=True)

    if not data_path.is_file() or not metadata_path.is_file():
        result = {
            "schema_version": 1,
            "classification": "INSUFFICIENT_EVIDENCE",
            "reason": "frozen A data.csv or run_metadata.txt is missing",
            "raw_capture": str(run_dir),
            "live_process_launched_by_analyzer": False,
        }
        (output / "analysis.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (output / "RESULTS.md").write_text("# Phase2 known-step pre-contact readjudication\n\nClassification: `INSUFFICIENT_EVIDENCE`\n\nFrozen A evidence is missing. No live process was launched.\n", encoding="utf-8")
        return 2

    rows = read_rows(data_path)
    columns = set(rows[0]) if rows else set()
    missing_columns = sorted(REQUIRED_COLUMNS - columns)
    activity = activity_summary(rows)
    clean, clean_missing_values = clean_rows(rows)
    state_times = [number(row, "state_tick_s") for row in clean]
    state_times = [value for value in state_times if value is not None]
    clean_span = max(state_times) - min(state_times) if state_times else None
    metadata = read_key_values(metadata_path)
    protocol = parse_protocol(run_dir)
    solver = solver_stats(clean)
    roll = signed_and_absolute(number(row, "imu_roll_rad") for row in clean if number(row, "imu_roll_rad") is not None)
    pitch = signed_and_absolute(number(row, "imu_pitch_rad") for row in clean if number(row, "imu_pitch_rad") is not None)
    contact = contact_event(rows)
    posture = posture_event(rows)
    raw_hash_records, raw_hash_ok = raw_artifact_hashes(root, run_dir)

    frozen_provenance = root / "docs/validation/phase2_known_step_wallclock_repair_20260915/provenance.csv"
    expected_source: dict[str, str] = {}
    if frozen_provenance.is_file():
        for record in read_rows(frozen_provenance):
            artifact = record.get("artifact", "")
            if "/A/" not in artifact and record.get("kind") in {"controller_binary", "simulator_binary", "scene"}:
                expected_source[Path(artifact).name] = record.get("sha256", "")
    runtime_hashes_ok = all(
        metadata.get(key, "") == expected_source.get(filename, "") != ""
        for key, filename in (
            ("controller_sha256", "real_trot_go2"),
            ("simulator_sha256", "unitree_mujoco"),
            ("scene_sha256", "scene_known_step_5cm.xml"),
        )
    )
    source_provenance_ok = (
        metadata.get("git_head") == args.expected_runtime_head
        and metadata.get("git_dirty") == "false"
        and runtime_hashes_ok
        and raw_hash_ok
    )
    protocol_ok = (
        protocol["trace_present"]
        and protocol["trace_rows"] > 0
        and protocol["trace_violations"] == 0
        and not protocol["fail_closed_markers"]
        and protocol["paired_summary_present"]
        and protocol["paired_cycles"] > 0
        and protocol["paired_validation_failures"] == 0
        and protocol["paired_async_fallbacks"] == 0
    )
    adaptation_enabled_samples = sum(truthy(row, "known_step_feature_enabled") for row in rows)
    adaptation_active_samples = sum(
        truthy(row, f"known_step_{leg}_adaptation_active") for row in rows for leg in LEGS
    )
    hard_in_clean = any(
        number(row, "imu_roll_rad") is not None
        and number(row, "imu_pitch_rad") is not None
        and (abs(number(row, "imu_roll_rad")) > HARD_POSTURE_RAD or abs(number(row, "imu_pitch_rad")) > HARD_POSTURE_RAD)
        for row in clean
    )
    health = {
        "roll": roll,
        "pitch": pitch,
        "solver": solver,
        "adaptation_enabled_samples": adaptation_enabled_samples,
        "adaptation_active_samples": adaptation_active_samples,
        "hard_posture_rows": int(hard_in_clean),
        "protocol_ok": protocol_ok,
        "protocol": protocol,
        "actual_foot_extrema_clean": actual_extrema(clean),
        "actual_foot_extrema_raw": actual_extrema(rows),
    }
    gates = [
        gate("required_columns", not missing_columns, f"missing={missing_columns or 'none'}"),
        gate("clean_row_count", len(clean) >= 250, f"rows={len(clean)} required>=250"),
        gate("clean_state_time_span", clean_span is not None and clean_span >= 0.50, f"span_s={clean_span} required>=0.50"),
        gate("known_step_adaptation_disabled", adaptation_enabled_samples == 0 and adaptation_active_samples == 0, f"enabled={adaptation_enabled_samples} active={adaptation_active_samples}"),
        gate("roll_abs_max", roll["absolute_max"] is not None and roll["absolute_max"] <= 0.25, f"max_abs_rad={roll['absolute_max']}"),
        gate("pitch_abs_max", pitch["absolute_max"] is not None and pitch["absolute_max"] <= 0.25, f"max_abs_rad={pitch['absolute_max']}"),
        gate("clean_no_22_degree_crossing", not hard_in_clean, f"crossing_rows={int(hard_in_clean)}"),
        gate("wbc_solver_valid_rows", solver["valid_rows"] >= 100, f"valid_rows={solver['valid_rows']} required>=100"),
        gate("wbc_solver_success", solver["all_srbd_ok"] and solver["all_id_ok"], f"srbd={solver['srbd_success_fraction']} id={solver['id_success_fraction']}"),
        gate("wbc_equality_residual_p95", solver["residual"]["p95"] is not None and solver["residual"]["p95"] <= 1e-3, f"p95={solver['residual']['p95']} required<=1e-3"),
        gate("lockstep_and_paired_highstate", protocol_ok, json.dumps(protocol, sort_keys=True)),
        gate("runtime_and_raw_provenance", source_provenance_ok, f"runtime_head={metadata.get('git_head', 'MISSING')} raw_hashes_match={raw_hash_ok} source_hashes_match={runtime_hashes_ok}"),
    ]
    health_ok = all(item["status"] == "PASS" for item in gates)
    if contact and posture and contact.get("state_time_s") is not None and posture.get("state_time_s") is not None:
        delta = posture["state_time_s"] - contact["state_time_s"]
        if delta >= 0:
            ordering = "first_plausible_contact_risk_at_or_before_first_hard_posture_crossing"
        else:
            ordering = "first_hard_posture_crossing_before_first_plausible_contact_risk"
    else:
        delta = None
        ordering = "unresolved_missing_event"
    classification = classify(
        not missing_columns,
        len(clean),
        clean_span,
        health_ok,
        contact,
        posture,
    )

    health_records: list[dict[str, Any]] = []
    for item in gates:
        health_records.append({"scope": "gate", "metric": item["gate"], "value": item["status"], "status": item["status"], "detail": item["detail"]})
    scalar_metrics = {
        "raw_rows": len(rows),
        "old_active_rows": activity["old_active_rows"],
        "corrected_active_rows": activity["corrected_active_rows"],
        "clean_rows": len(clean),
        "clean_missing_value_rows": clean_missing_values,
        "clean_state_time_start_s": min(state_times) if state_times else None,
        "clean_state_time_end_s": max(state_times) if state_times else None,
        "clean_state_time_span_s": clean_span,
        "adaptation_enabled_samples": adaptation_enabled_samples,
        "adaptation_active_samples": adaptation_active_samples,
        "hard_posture_threshold_rad": HARD_POSTURE_RAD,
        "wbc_valid_rows": solver["valid_rows"],
        "wbc_eq_residual_p95": solver["residual"]["p95"],
        "paired_highstate_cycles": protocol["paired_cycles"],
        "paired_highstate_validation_failures": protocol["paired_validation_failures"],
        "paired_highstate_async_fallbacks": protocol["paired_async_fallbacks"],
    }
    for metric, value in scalar_metrics.items():
        health_records.append({"scope": "clean_precontact_or_capture", "metric": metric, "value": value, "status": "INFO", "detail": ""})
    for name, values in (("roll", roll), ("pitch", pitch)):
        for metric, value in values.items():
            health_records.append({"scope": "clean_precontact", "metric": f"{name}_{metric}", "value": value, "status": "INFO", "detail": "rad"})
    for leg in LEGS:
        for axis in ("x", "z"):
            values = health["actual_foot_extrema_clean"][leg][axis]
            for metric, value in values.items():
                health_records.append({"scope": "clean_precontact", "metric": f"{leg}_actual_{axis}_{metric}", "value": value, "status": "INFO", "detail": "m"})
    write_csv(output / "precontact_health.csv", health_records, ["scope", "metric", "value", "status", "detail"])
    write_csv(output / "contact_risk_chronology.csv", chronology_rows(contact, posture, ordering, delta))

    provenance_records = list(raw_hash_records)
    for filename, kind in (
        ("data.csv", "raw_capture"),
        ("run_metadata.txt", "raw_metadata"),
        ("lockstep_trace.csv", "raw_capture"),
        ("lockstep_handoff.csv", "raw_capture"),
        ("run_manifest.json", "raw_metadata"),
    ):
        if not any(row.get("artifact") == filename for row in provenance_records):
            provenance_records.append({
                "scope": "raw_capture",
                "artifact": filename,
                "path": str(run_dir / filename),
                "bytes": (run_dir / filename).stat().st_size if (run_dir / filename).is_file() else "MISSING",
                "sha256": sha256(run_dir / filename),
                "expected_sha256": "not_recorded",
                "matches_frozen_provenance": False,
            })
    for path, kind in (
        (Path(__file__), "analysis_source"),
        (root / "docs/research/PHASE1_AGENT_CONTRACT.md", "contract"),
        (root / "docs/research/TASK_PHASE2_KNOWN_STEP_PRECONTACT_READJUDICATION_20260915.md", "task"),
    ):
        provenance_records.append({
            "scope": kind,
            "artifact": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "path": str(path),
            "bytes": path.stat().st_size if path.is_file() else "MISSING",
            "sha256": sha256(path),
            "expected_sha256": "",
            "matches_frozen_provenance": "",
            "runtime_head": metadata.get("git_head", ""),
            "runtime_branch": metadata.get("git_branch", ""),
            "runtime_dirty": metadata.get("git_dirty", ""),
            "controller_sha256": metadata.get("controller_sha256", ""),
            "simulator_sha256": metadata.get("simulator_sha256", ""),
            "scene_sha256": metadata.get("scene_sha256", ""),
        })
    write_csv(output / "provenance.csv", provenance_records)

    analysis = {
        "schema_version": 1,
        "experiment": "phase2_known_step_precontact_readjudication_20260915",
        "classification": classification,
        "raw_capture": str(run_dir),
        "raw_capture_scope": "A only",
        "live_process_launched_by_analyzer": False,
        "no_B_launch": True,
        "runtime_source_changed": False,
        "runtime_head_expected": args.expected_runtime_head,
        "runtime_metadata": metadata,
        "activity": activity,
        "clean_precontact_mask": {
            "predicate": "motion_stage == 2 AND world_base_x_m <= 0.40 AND every actual foot-center x < 0.75",
            "base_x_limit_m": CLEAN_BASE_X_M,
            "actual_foot_x_limit_m": CLEAN_FOOT_X_M,
            "rows": len(clean),
            "state_time_start_s": min(state_times) if state_times else None,
            "state_time_end_s": max(state_times) if state_times else None,
            "state_time_span_s": clean_span,
        },
        "health_gate_pass": health_ok,
        "health": health,
        "gates": gates,
        "chronology": {
            "contact_risk": contact,
            "hard_posture": posture,
            "ordering": ordering,
            "delta_hard_minus_risk_s": delta,
            "contact_risk_definition": "actual foot-center x >= 0.778 m and z <= 0.072 m",
            "literal_contact_claim": False,
        },
        "provenance": {
            "raw_hashes_match_frozen_wallclock_closeout": raw_hash_ok,
            "runtime_source_hashes_match": runtime_hashes_ok,
            "runtime_and_raw_provenance_gate": source_provenance_ok,
        },
    }
    (output / "analysis.json").write_text(json.dumps(jsonable(analysis), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_results(
        output / "RESULTS.md",
        classification,
        run_dir,
        args.expected_runtime_head,
        activity,
        len(clean),
        clean_span,
        health,
        gates,
        contact,
        posture,
        ordering,
        delta,
        protocol,
        source_provenance_ok,
        raw_hash_ok,
    )
    print(f"classification={classification} clean_rows={len(clean)} clean_span_s={clean_span} health_gate={health_ok} ordering={ordering}")
    return 0 if classification != "INSUFFICIENT_EVIDENCE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
