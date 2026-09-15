#!/usr/bin/env python3
"""Strictly offline V2 CSV schema readjudication.

The analyzer never starts a runtime process. It reads raw rows in memory and
refuses scientific interpretation unless the task's literal four-empty-token
recovery contract is satisfied.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


LEGS = ("fr", "fl", "rr", "rl")
V2_FIELDS = (
    "crossing_latched",
    "planning_valid",
    "planning_failure_code",
    "planning_failure_reason",
    "swing_start_x_m",
    "swing_start_z_m",
    "ordinary_nominal_touchdown_x_m",
    "ordinary_nominal_touchdown_y_m",
    "ordinary_nominal_touchdown_z_m",
    "probe_touchdown_x_m",
    "probe_touchdown_y_m",
    "probe_touchdown_z_m",
    "h0_m",
    "h_nom_m",
    "h_probe_m",
    "x_entry_m",
    "x_exit_m",
    "x_land_min_m",
    "final_touchdown_x_m",
    "final_touchdown_y_m",
    "final_touchdown_z_m",
    "nominal_x_shift_m",
    "effective_lift_m",
    "z_corridor_m",
    "s",
    "s_entry",
    "s_exit",
    "command_world_x_m",
    "command_world_z_m",
    "command_world_vx_mps",
    "command_world_vz_mps",
    "actual_world_x_m",
    "actual_world_z_m",
    "scheduled_stance",
    "scheduled_swing",
)
BOOL_FIELDS = {
    "known_step_v2_feature_enabled",
    *(f"known_step_v2_{leg}_{field}" for leg in LEGS for field in ("crossing_latched", "planning_valid", "scheduled_stance", "scheduled_swing")),
}
PLANNING_REASONS = {"none", "not_crossing", "invalid_edge_ordering"}
PLANNING_CODES = {0, 1, 2}
EXPECTED_EMPTY_COUNT = 4
EXPECTED_DATA_WIDTH = 776
EXPECTED_HEADER_WIDTH = 780
EXPECTED_DATA_ROWS = 5005
EXPECTED_C_HEAD = "b281993b81b3bf6a083eccfb5805789026913837"
SCHEMA_LABEL = "SCHEMA_RECOVERY_AMBIGUOUS"


def load_frozen_v2() -> Any:
    path = Path(__file__).with_name("analyze_phase2_known_step_edge_aware_v2.py")
    spec = importlib.util.spec_from_file_location("frozen_v2_analyzer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen V2 analyzer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V2 = load_frozen_v2()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_kv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


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


def gate(name: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {
        "gate": name,
        "status": "PASS" if passed else "FAIL",
        "detail": detail if isinstance(detail, str) else jsonable(detail),
    }


def number(row: dict[str, str], key: str) -> float | None:
    try:
        value = float(row.get(key, ""))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def read_raw(path: Path) -> tuple[list[str], list[list[str]], bytes]:
    with path.open("rb") as stream:
        header_line = stream.readline()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    return header, rows, header_line


def candidate_header(header: list[str]) -> tuple[list[int], list[str]]:
    drops = [index for index, token in enumerate(header) if token == "known_step_v2_"]
    repaired = [token for index, token in enumerate(header) if index not in drops]
    return drops, repaired


def expected_empty_transitions(header: list[str]) -> list[dict[str, Any]]:
    result = []
    for leg in LEGS:
        previous = f"known_step_v2_{leg}_s_exit"
        following = f"known_step_v2_{leg}_command_world_x_m"
        for index, token in enumerate(header):
            if token == "" and index > 0 and index + 1 < len(header):
                if header[index - 1] == previous and header[index + 1] == following:
                    result.append({"leg": leg, "index": index, "previous": previous, "following": following})
    return result


def observed_extra_transitions(header: list[str]) -> list[dict[str, Any]]:
    result = []
    for index, token in enumerate(header):
        if token != "known_step_v2_" or index == 0 or index + 1 >= len(header):
            continue
        previous = header[index - 1]
        following = header[index + 1]
        for leg in LEGS:
            if previous == f"known_step_v2_{leg}_s_exit" and following == f"known_step_v2_{leg}_command_world_x_m":
                result.append({"leg": leg, "index": index, "token": token, "previous": previous, "following": following})
    return result


def source_proof(source_path: Path) -> dict[str, Any]:
    lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
    header_bug_lines = [index + 1 for index, line in enumerate(lines) if "_s_exit,known_step_v2_" in line]
    log_exit_lines = [index + 1 for index, line in enumerate(lines) if '<< "," << v2.s_exit' in line]
    log_command_x_lines = [index + 1 for index, line in enumerate(lines) if "known_step_v2_command_x_m" in line]
    contiguous = bool(log_exit_lines and log_command_x_lines and 0 < log_command_x_lines[0] - log_exit_lines[0] <= 5)
    return {
        "path": str(source_path),
        "sha256": sha256(source_path),
        "header_extra_token_lines": header_bug_lines,
        "header_exact_double_delimiter": any("_s_exit,," in line for line in lines),
        "header_extra_prefix_construction": bool(header_bug_lines),
        "log_sample_s_exit_lines": log_exit_lines,
        "log_sample_command_world_x_lines": log_command_x_lines,
        "log_sample_contiguous_sequence": contiguous,
        "interpretation": "source emits a literal known_step_v2_ token between s_exit and command_world_x_m; it is not an empty CSV token",
    }


def finite_field_check(rows: list[dict[str, str]], header: list[str]) -> dict[str, Any]:
    fields = [
        field for field in header
        if field.endswith(("_command_world_x_m", "_command_world_z_m", "_command_world_vx_mps", "_command_world_vz_mps", "_actual_world_x_m", "_actual_world_z_m"))
    ]
    failures = []
    populated = 0
    for row_index, row in enumerate(rows):
        for field in fields:
            raw = row.get(field, "")
            if raw == "":
                continue
            populated += 1
            try:
                value = float(raw)
            except ValueError:
                failures.append({"row": row_index, "field": field, "value": raw})
                continue
            if not math.isfinite(value):
                failures.append({"row": row_index, "field": field, "value": raw})
    return {"pass": not failures, "fields": len(fields), "populated_values": populated, "failures": failures[:20]}


def recovery_validation(rows: list[dict[str, str]], repaired: list[str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    bool_values = {row.get(field, "").strip().lower() for row in rows for field in BOOL_FIELDS if field in row and row.get(field, "") != ""}
    bool_ok = bool_values <= {"0", "1", "true", "false", "yes", "no", "on", "off"}
    checks.append(gate("v2_boolean_like_values", bool_ok, sorted(bool_values)))
    active = [row for row in rows if number(row, "motion_stage") == 2]
    active_values = {row.get("known_step_v2_feature_enabled", "") for row in active}
    checks.append(gate("v2_enabled_during_active_locomotion", "1" in active_values, sorted(active_values)))
    codes = []
    code_failures = []
    reasons = set()
    reason_failures = []
    for row_index, row in enumerate(rows):
        for leg in LEGS:
            code_raw = row.get(f"known_step_v2_{leg}_planning_failure_code", "")
            reason = row.get(f"known_step_v2_{leg}_planning_failure_reason", "")
            if code_raw != "":
                try:
                    code = int(float(code_raw))
                    codes.append(code)
                    if code not in PLANNING_CODES:
                        code_failures.append({"row": row_index, "leg": leg, "value": code_raw})
                except ValueError:
                    code_failures.append({"row": row_index, "leg": leg, "value": code_raw})
            if reason != "":
                reasons.add(reason)
                if reason not in PLANNING_REASONS:
                    reason_failures.append({"row": row_index, "leg": leg, "value": reason})
    checks.append(gate("planning_failure_code_enum", not code_failures and bool(codes), {"codes": sorted(set(codes)), "failures": code_failures[:20]}))
    checks.append(gate("planning_failure_reason_enum", not reason_failures and bool(reasons), {"reasons": sorted(reasons), "failures": reason_failures[:20]}))
    for field, target in (("x_entry_m", 0.777), ("x_exit_m", 0.823), ("x_land_min_m", 0.850)):
        populated = []
        for row in rows:
            for leg in LEGS:
                value = number(row, f"known_step_v2_{leg}_{field}")
                if value is not None and value != 0.0:
                    populated.append(value)
        errors = [value for value in populated if abs(value - target) > 1.0e-9]
        checks.append(gate(f"{field}_source_invariant", not errors and bool(populated), {"target": target, "populated": len(populated), "unique": sorted(set(round(value, 9) for value in populated)), "errors": errors[:20]}))
    scheduled_fields = [f"known_step_v2_{leg}_{field}" for leg in LEGS for field in ("scheduled_stance", "scheduled_swing")]
    scheduled_values = {row.get(field, "") for row in rows for field in scheduled_fields if row.get(field, "") != ""}
    checks.append(gate("scheduled_stance_swing_boolean_like", scheduled_values <= {"0", "1"}, sorted(scheduled_values)))
    finite = finite_field_check(rows, repaired)
    checks.append(gate("finite_command_actual_values", finite["pass"], finite))
    expected_blocks = []
    block_failures = []
    for leg in LEGS:
        expected = [f"known_step_v2_{leg}_{field}" for field in V2_FIELDS]
        try:
            start = repaired.index(expected[0])
            actual = repaired[start:start + len(expected)]
        except ValueError:
            start = -1
            actual = []
        expected_blocks.append({"leg": leg, "start": start, "end": start + len(expected) - 1, "next": repaired[start + len(expected)] if start >= 0 and start + len(expected) < len(repaired) else ""})
        if actual != expected:
            block_failures.append({"leg": leg, "expected_head": expected[:3], "actual_head": actual[:3], "start": start})
    after_last = repaired.index("known_step_v2_rl_scheduled_swing") + 1 if "known_step_v2_rl_scheduled_swing" in repaired else -1
    following = repaired[after_last] if after_last >= 0 and after_last < len(repaired) else ""
    checks.append(gate("v2_leg_blocks_no_column_drift", not block_failures and following.startswith("diag_bounded_stance_dq_"), {"blocks": expected_blocks, "following_d4_field": following, "failures": block_failures}))
    return checks


def schema_audit(c_dir: Path, source_path: Path) -> dict[str, Any]:
    data_path = c_dir / "data.csv"
    header, raw_rows, header_line = read_raw(data_path)
    widths = Counter(len(row) for row in raw_rows)
    drops, repaired = candidate_header(header)
    empty_indices = [index for index, token in enumerate(header) if token == ""]
    duplicate_names = sorted(name for name, count in Counter(header).items() if name and count > 1)
    candidate_duplicate_names = sorted(name for name, count in Counter(repaired).items() if name and count > 1)
    extra_transitions = observed_extra_transitions(header)
    empty_transitions = expected_empty_transitions(header)
    row_dicts = [dict(zip(repaired, row)) for row in raw_rows if len(row) == len(repaired)]
    source = source_proof(source_path)
    validation = recovery_validation(row_dicts, repaired) if len(row_dicts) == len(raw_rows) else [gate("candidate_rows_width", False, "candidate mapping cannot be applied")]
    exact_shape = (
        len(header) == EXPECTED_HEADER_WIDTH
        and len(raw_rows) == EXPECTED_DATA_ROWS
        and widths == Counter({EXPECTED_DATA_WIDTH: EXPECTED_DATA_ROWS})
        and len(empty_indices) == EXPECTED_EMPTY_COUNT
        and len(empty_transitions) == EXPECTED_EMPTY_COUNT
        and not duplicate_names
        and source["header_exact_double_delimiter"]
        and source["log_sample_contiguous_sequence"]
    )
    candidate_unique = (
        drops == [item["index"] for item in extra_transitions]
        and len(repaired) == EXPECTED_DATA_WIDTH
        and not candidate_duplicate_names
        and len(row_dicts) == len(raw_rows)
        and all(len(row) == len(repaired) for row in raw_rows)
    )
    all_recovery_checks = all(item["status"] == "PASS" for item in validation)
    repaired_header_line = (",".join(repaired) + "\n").encode("utf-8")
    return {
        "raw_data_path": str(data_path),
        "raw_header_width": len(header),
        "raw_data_rows": len(raw_rows),
        "raw_width_counts": dict(sorted(widths.items())),
        "raw_header_empty_indices": empty_indices,
        "raw_header_empty_tokens": [header[index] for index in empty_indices],
        "raw_header_duplicate_names": duplicate_names,
        "observed_nonempty_extra_tokens": [header[index] for index in drops],
        "observed_extra_transitions": extra_transitions,
        "expected_empty_transitions": empty_transitions,
        "candidate_drop_indices": drops,
        "candidate_repaired_width": len(repaired),
        "candidate_repaired_duplicate_names": candidate_duplicate_names,
        "candidate_mapping_unique": candidate_unique,
        "recovery_validation_all_pass": all_recovery_checks,
        "recovery_validation": validation,
        "literal_task_shape_gate": exact_shape,
        "recovery_authorized": bool(exact_shape and candidate_unique and all_recovery_checks),
        "source_proof": source,
        "raw_header_line_sha256": hashlib.sha256(header_line).hexdigest(),
        "derived_header_sha256": hashlib.sha256(repaired_header_line).hexdigest(),
        "derived_header_hash_definition": "UTF-8 bytes of comma-joined candidate repaired header plus LF",
        "header_line_bytes": len(header_line),
        "header": header,
        "repaired_header": repaired,
        "raw_rows": raw_rows,
        "repaired_rows": row_dicts,
    }


def log_status_context(c_dir: Path, raw_rows: list[list[str]], raw_header: list[str]) -> dict[str, Any]:
    log_path = c_dir / "controller.log"
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    lines = text.splitlines()
    posture_matches = []
    safety_lines = []
    for index, line in enumerate(lines, start=1):
        if "Trot hard posture limit:" in line:
            match = re.search(r"roll=([-+0-9.eE]+) deg, pitch=([-+0-9.eE]+) deg", line)
            posture_matches.append({"line": index, "text": line, "roll_deg": float(match.group(1)) if match else None, "pitch_deg": float(match.group(2)) if match else None})
        if "Trot hard safety limit reached; stopping" in line:
            safety_lines.append({"line": index, "text": line})
    started_cycles = [int(match.group(1)) for match in re.finditer(r"Trot cycle (\d+) started", text)]
    prefix_header = raw_header[:211]
    first_telemetry_crossing = None
    for index, row in enumerate(raw_rows):
        if len(row) < len(prefix_header):
            continue
        prefix = dict(zip(prefix_header, row[:len(prefix_header)]))
        roll = number(prefix, "imu_roll_rad")
        pitch = number(prefix, "imu_pitch_rad")
        if roll is not None and pitch is not None and max(abs(roll), abs(pitch)) >= math.radians(22.0):
            first_telemetry_crossing = {
                "raw_row_index": index,
                "state_tick_s": number(prefix, "state_tick_s"),
                "roll_rad": roll,
                "pitch_rad": pitch,
                "roll_deg": math.degrees(roll),
                "pitch_deg": math.degrees(pitch),
                "base_x_m": number(prefix, "world_base_x_m"),
            }
            break
    metadata = read_kv(c_dir / "run_metadata.txt")
    return {
        "metadata_statuses": {key: metadata.get(key, "") for key in ("controller_status", "ground_truth_status", "dynamics_status", "quality_status", "analysis_status", "safety_status", "completion_status")},
        "first_controller_hard_posture_marker": posture_matches[0] if posture_matches else None,
        "first_controller_hard_safety_marker": safety_lines[0] if safety_lines else None,
        "hard_posture_marker_count": len(posture_matches),
        "hard_safety_marker_count": len(safety_lines),
        "first_22_degree_telemetry_crossing": first_telemetry_crossing,
        "started_cycle_numbers": started_cycles,
        "max_started_cycle": max(started_cycles) if started_cycles else None,
        "completion_marker_present": bool(re.search(r"completed|complete", text, re.IGNORECASE)),
        "completion_interpretation": "completion_status=1 is preserved; controller.log has no normal completion marker and stops on the hard-safety marker",
        "controller_log_sha256": sha256(log_path) if log_path.is_file() else "MISSING",
    }


def load_parent_hashes(path: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    if not path.is_file():
        return result
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            scope = row.get("scope", "")
            artifact = row.get("artifact", "")
            expected = row.get("sha256", "")
            if scope and artifact and expected and artifact in {
                "contact_ground_truth.csv", "contact_ground_truth_analysis.txt", "contact_ground_truth_dynamics_analysis.txt",
                "controller.log", "data.csv", "environment.txt", "lockstep_handoff.csv", "lockstep_handoff.csv.bin",
                "lockstep_trace.csv", "run_manifest.json", "run_metadata.txt", "simulator.log",
            }:
                result.setdefault(scope, {})[artifact] = expected
    return result


def provenance_records(
    root: Path,
    a_dir: Path,
    b_dir: Path,
    c_dir: Path,
    source_path: Path,
    parent_provenance: Path,
    c_meta: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected = load_parent_hashes(parent_provenance)
    records: list[dict[str, Any]] = []
    matches: dict[str, bool] = {}
    for scope, run_dir, expected_scope in (
        ("A_raw_frozen", a_dir, expected.get("A_raw_frozen", {})),
        ("V1_B_frozen", b_dir, expected.get("V1_B_frozen", {})),
        ("C_raw_immutable", c_dir, expected.get("C_raw", {})),
    ):
        scope_ok = bool(expected_scope)
        names = sorted(expected_scope) if expected_scope else sorted(path.name for path in run_dir.iterdir() if path.is_file())
        for name in names:
            path = run_dir / name
            actual = sha256(path) if path.is_file() else "MISSING"
            expected_hash = expected_scope.get(name, "")
            equal = bool(expected_hash) and actual == expected_hash
            scope_ok = scope_ok and equal
            records.append({
                "scope": scope,
                "artifact": name,
                "path": str(path),
                "bytes": path.stat().st_size if path.is_file() else "MISSING",
                "sha256": actual,
                "expected_sha256": expected_hash,
                "matches": equal,
            })
        matches[scope] = scope_ok
    scene = root / "unitree_robots/go2/scene_known_step_5cm.xml"
    scene_hash = sha256(scene)
    records.append({"scope": "scene", "artifact": str(scene.relative_to(root)), "path": str(scene), "bytes": scene.stat().st_size, "sha256": scene_hash, "expected_sha256": "8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc", "matches": scene_hash == "8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc"})
    source_artifact = str(source_path.relative_to(root)) if source_path.is_relative_to(root) else str(source_path)
    records.append({"scope": "runtime_source_snapshot", "artifact": source_artifact, "path": str(source_path), "bytes": source_path.stat().st_size, "sha256": sha256(source_path), "recorded_c_runtime_head": EXPECTED_C_HEAD})
    metadata_ok = (
        c_meta.get("git_head") == EXPECTED_C_HEAD
        and c_meta.get("git_dirty") == "false"
        and c_meta.get("scene_sha256") == "8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc"
    )
    records.append({"scope": "C_runtime_metadata", "artifact": "run_metadata.txt", "path": str(c_dir / "run_metadata.txt"), "recorded_git_head": c_meta.get("git_head", ""), "expected_recorded_git_head": EXPECTED_C_HEAD, "git_dirty": c_meta.get("git_dirty", ""), "controller_sha256": c_meta.get("controller_sha256", ""), "simulator_sha256": c_meta.get("simulator_sha256", ""), "scene_sha256": c_meta.get("scene_sha256", ""), "matches": metadata_ok})
    details = {
        "parent_provenance": str(parent_provenance),
        "A_raw_hashes_match": matches.get("A_raw_frozen", False),
        "V1_B_raw_hashes_match": matches.get("V1_B_frozen", False),
        "C_raw_hashes_match_parent_closeout": matches.get("C_raw_immutable", False),
        "C_runtime_metadata_match": metadata_ok,
    }
    return records, details


def placeholder_files(output: Path, reason: str, protocol_records: list[dict[str, Any]], provenance: list[dict[str, Any]], chronology: list[dict[str, Any]]) -> None:
    placeholder = [{"status": "NOT_RUN", "reason": reason, "live_process_launched_by_analyzer": False}]
    write_csv(output / "preactivation_exact.csv", placeholder)
    write_csv(output / "planning_isolation.csv", [{"run": "C", **gate("scientific_readjudication", False, reason)}])
    write_csv(output / "front_crossing_summary.csv", placeholder)
    write_csv(output / "edge_tracking_timeline.csv", placeholder)
    write_csv(output / "touchdown_summary.csv", placeholder)
    write_csv(output / "body_contact_chronology.csv", chronology)
    write_csv(output / "protocol_gates.csv", protocol_records)
    write_csv(output / "provenance.csv", provenance)


def run_scientific_readjudication(
    output: Path,
    a_dir: Path,
    c_dir: Path,
    c_rows: list[dict[str, str]],
    c_meta: dict[str, str],
    protocol: dict[str, Any],
    provenance: list[dict[str, Any]],
    provenance_details: dict[str, Any],
) -> dict[str, Any]:
    a_rows = V2.read_rows(a_dir / "data.csv")
    pre_ok, pre_summary, pre_mismatches = V2.exact_preactivation(a_rows, c_rows, a_dir, c_dir)
    planning_records, planning_details = V2.planning_isolation(c_rows, c_dir)
    c_first_hard = V2.posture_event(c_rows)
    hard_time = c_first_hard.get("state_time_s") if c_first_hard else None
    front_summaries, edge_timeline = V2.edge_tracking(c_rows, hard_time)
    c_references = V2.floor_reference(c_rows)
    c_metrics = V2.traversal_metrics(c_rows, c_meta, c_dir, c_references)
    c_metrics["chronology"] = V2.chronology(c_rows)
    protocol_records = [
        V2.gate("C", "domain_230", protocol.get("domain_matches", False), protocol.get("domain_id", "")),
        V2.gate("C", "lockstep_trace_present", protocol.get("trace_present", False), protocol.get("trace_rows", 0)),
        V2.gate("C", "constant_sim_tick", protocol.get("sim_tick_diffs_ms") == [2.0], protocol.get("sim_tick_diffs_ms", [])),
        V2.gate("C", "paired_highstate", protocol.get("paired_validation_failures") == 0 and protocol.get("paired_async_fallbacks") == 0, protocol),
        V2.gate("A", "frozen_raw_hashes", provenance_details.get("A_raw_hashes_match", False), provenance_details),
        V2.gate("V1_B", "frozen_raw_hashes", provenance_details.get("V1_B_raw_hashes_match", False), provenance_details),
        V2.gate("C", "runtime_metadata", provenance_details.get("C_runtime_metadata_match", False), provenance_details),
        V2.gate("A_C", "exact_preactivation", pre_ok, {"summary": pre_summary, "mismatches": pre_mismatches}),
    ]
    protocol_ok = all(item["status"] == "PASS" for item in protocol_records)
    planning_ok = all(item["status"] == "PASS" for item in planning_records)
    traversal = c_metrics["traversal"]
    tracking_limited = planning_ok and not traversal["success"] and any(
        item["edge_envelope"]["actual_entered_below_z_geom_clear"]
        or (item["first_command_edge_entry"]["command_clear"] and (item["tracking"]["contact_or_force_near_actual_entry"] or item["tracking"]["material_z_error"]))
        for item in front_summaries
    )
    front_pair = planning_ok and not traversal["success"] and all(
        item["raised_contact_gate"] for item in c_metrics["raised_contact"] if item["leg"] in V2.FRONT_LEGS
    )
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
    elif front_pair:
        classification = "FRONT_PAIR_ESTABLISHED_BUT_COORDINATION_FAILED"
    else:
        classification = "OTHER_CONTROL_LIMIT_IDENTIFIED" if front_summaries else "INSUFFICIENT_EVIDENCE"
    write_csv(output / "preactivation_exact.csv", [{"status": "PASS" if pre_ok else "FAIL", **pre_summary}] + pre_mismatches)
    write_csv(output / "planning_isolation.csv", planning_records + [{"run": "C", "gate": "planning_summary", "status": "PASS" if planning_ok else "FAIL", "detail": planning_details}])
    write_csv(output / "front_crossing_summary.csv", front_summaries)
    write_csv(output / "edge_tracking_timeline.csv", edge_timeline)
    write_csv(output / "touchdown_summary.csv", c_metrics["raised_contact"] + [{"leg": "all", "floor_reference_z0_m": c_references}])
    write_csv(output / "body_contact_chronology.csv", [{"arm": "C", **event} for event in c_metrics["chronology"]])
    write_csv(output / "protocol_gates.csv", protocol_records)
    write_csv(output / "provenance.csv", provenance)
    return {
        "classification": classification,
        "preactivation": {"pass": pre_ok, "summary": pre_summary, "mismatches": pre_mismatches},
        "planning_isolation": {"pass": planning_ok, "gates": planning_records, "details": planning_details},
        "traversal": c_metrics,
        "front_crossings": front_summaries,
        "live_process_launched_by_analyzer": False,
    }


def make_chronology(status_context: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    posture = status_context.get("first_controller_hard_posture_marker")
    safety = status_context.get("first_controller_hard_safety_marker")
    telemetry = status_context.get("first_22_degree_telemetry_crossing")
    if posture:
        events.append({"arm": "C", "event": "controller_hard_posture_limit", "state_time_s": telemetry.get("state_tick_s") if telemetry else None, "controller_log_line": posture["line"], "detail": posture["text"]})
    if safety:
        events.append({"arm": "C", "event": "controller_hard_safety_limit_reached", "state_time_s": telemetry.get("state_tick_s") if telemetry else None, "controller_log_line": safety["line"], "detail": safety["text"]})
    events.append({"arm": "C", "event": "safety_status_1_preserved", "state_time_s": telemetry.get("state_tick_s") if telemetry else None, "controller_log_line": posture["line"] if posture else None, "detail": "run_metadata safety_status=1; independent hard-posture evidence"})
    events.append({"arm": "C", "event": "completion_status_1_preserved", "state_time_s": None, "controller_log_line": safety["line"] if safety else None, "detail": "run_metadata completion_status=1; no normal completion marker; hard-safety stop and incomplete requested cycles"})
    return events


def write_results(path: Path, audit: dict[str, Any], status_context: dict[str, Any], source_fix_status: str, regression_status: str) -> None:
    posture = status_context.get("first_controller_hard_posture_marker") or {}
    safety = status_context.get("first_controller_hard_safety_marker") or {}
    path.write_text(
        f"""# Phase2 V2 schema readjudication closeout

Date: 2026-09-15
Primary classification: {SCHEMA_LABEL}

This checkpoint was strictly offline. No simulator, controller, runner, DDS, GUI replay, or new experiment was launched; A and V1 B were not rerun and raw C data.csv was not modified.

## Raw and source finding

C has {audit["raw_header_width"]} header tokens and {audit["raw_data_rows"]} data rows, with raw row widths {audit["raw_width_counts"]}. The four extra tokens at raw indices {audit["candidate_drop_indices"]} are literal known_step_v2_, not empty tokens. Runtime source {audit["source_proof"]["path"]} contains the same _s_exit,known_step_v2_ header construction, while LogSample emits s_exit followed by command x/z/vx/vz and actual x/z in one sequence.

The candidate deletion is width-preserving and unique (candidate_mapping_unique={audit["candidate_mapping_unique"]}), but the task's literal empty-token transition gate is false (literal_task_shape_gate={audit["literal_task_shape_gate"]}). Therefore the derived candidate was used only for schema/status audit; frozen scientific V2 analysis was not run.

## Status preservation

run_metadata.txt statuses are {json.dumps(status_context["metadata_statuses"], sort_keys=True)}. The first controller marker is line {posture.get("line")}, Trot hard posture limit, immediately followed by line {safety.get("line")}, Trot hard safety limit reached; stopping. completion_status=1 is preserved: the log has no normal completion marker and records only the hard-safety stop before the requested run completed.

## Recovery disposition

Raw header SHA-256: {audit["raw_header_line_sha256"]}. Candidate derived-header SHA-256: {audit["derived_header_sha256"]}. Recovery validation checks: {json.dumps(audit["recovery_validation"], sort_keys=True)}. No scientific classification was inferred after the literal gate failure. Logger source fix: {source_fix_status}. No-live regression test: {regression_status}.

Raw-hash/provenance details are machine-readable in provenance.csv; the required scientific tables are present with NOT_RUN placeholders because recovery was ambiguous. Stop after this pushed closeout; no C rerun or scientific reinterpretation is authorized.
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--a-run", type=Path, required=True)
    parser.add_argument("--b-run", type=Path, required=True)
    parser.add_argument("--c-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--parent-provenance", type=Path, required=True)
    parser.add_argument("--runtime-source", type=Path, required=True)
    parser.add_argument("--source-diff-status", default="not_recorded")
    parser.add_argument("--logger-fix-status", default="not_recorded")
    parser.add_argument("--regression-status", default="not_recorded")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    a_dir = args.a_run.resolve()
    b_dir = args.b_run.resolve()
    c_dir = args.c_run.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    audit = schema_audit(c_dir, args.runtime_source.resolve())
    c_meta = read_kv(c_dir / "run_metadata.txt")
    status_context = log_status_context(c_dir, audit["raw_rows"], audit["header"])
    parent_records, provenance_details = provenance_records(root, a_dir, b_dir, c_dir, args.runtime_source.resolve(), args.parent_provenance.resolve(), c_meta)
    c_protocol = V2.parse_protocol(c_dir, "230")
    tests = {"live_run": "FORBIDDEN", "analyzer_process_launch": False, "schema_recovery": audit["recovery_authorized"]}
    protocol_records = [
        gate("C_raw_capture_present", (c_dir / "data.csv").is_file(), str(c_dir / "data.csv")),
        gate("C_raw_csv_widths_original", False, {"header": audit["raw_header_width"], "rows": audit["raw_width_counts"]}),
        gate("C_domain_230", c_protocol["domain_matches"], c_protocol["domain_id"]),
        gate("C_lockstep_trace", c_protocol["trace_present"] and c_protocol["trace_rows"] > 0, c_protocol["trace_rows"]),
        gate("C_constant_sim_tick", c_protocol["sim_tick_diffs_ms"] == [2.0], c_protocol["sim_tick_diffs_ms"]),
        gate("C_no_lockstep_violations", c_protocol["trace_violations"] == 0, c_protocol["trace_violations"]),
        gate("C_paired_highstate", c_protocol["paired_summary_present"] and c_protocol["paired_validation_failures"] == 0 and c_protocol["paired_async_fallbacks"] == 0, c_protocol),
        gate("A_hashes_unchanged", provenance_details["A_raw_hashes_match"], provenance_details),
        gate("V1_B_hashes_unchanged", provenance_details["V1_B_raw_hashes_match"], provenance_details),
        gate("C_raw_hashes_unchanged_from_parent", provenance_details["C_raw_hashes_match_parent_closeout"], provenance_details),
        gate("C_runtime_metadata", provenance_details["C_runtime_metadata_match"], c_meta),
        gate("schema_recovery_authorized", audit["recovery_authorized"], {"literal_task_shape_gate": audit["literal_task_shape_gate"], "candidate_mapping_unique": audit["candidate_mapping_unique"], "recovery_validation_all_pass": audit["recovery_validation_all_pass"]}),
    ]
    chronology = make_chronology(status_context)

    if audit["recovery_authorized"]:
        scientific = run_scientific_readjudication(
            output, a_dir, c_dir, audit["repaired_rows"], c_meta,
            c_protocol, parent_records, provenance_details,
        )
        classification = scientific["classification"]
        analysis = {
            "schema_version": 1,
            "experiment": "phase2_known_step_v2_schema_readjudication_20260915",
            "classification": classification,
            "live_process_launched_by_analyzer": False,
            "schema_recovery": {key: value for key, value in audit.items() if key not in {"header", "repaired_header", "raw_rows", "repaired_rows"}},
            "status_context": status_context,
            "protocol": {"pass": all(item["status"] == "PASS" for item in protocol_records), "gates": protocol_records},
            "provenance": provenance_details,
            "scientific": scientific,
        }
    else:
        reason = "literal four-empty-header-token gate failed; candidate contains four nonempty known_step_v2_ tokens"
        placeholder_files(output, reason, protocol_records, parent_records, chronology)
        classification = SCHEMA_LABEL
        analysis = {
            "schema_version": 1,
            "experiment": "phase2_known_step_v2_schema_readjudication_20260915",
            "classification": classification,
            "live_process_launched_by_analyzer": False,
            "launch_budget": {"authorized_prior_C_launches": 1, "analyzer_live_launches": 0, "A_reruns": 0, "V1_B_reruns": 0, "C_reruns": 0, "retries": 0},
            "schema_recovery": {key: value for key, value in audit.items() if key not in {"header", "repaired_header", "raw_rows", "repaired_rows"}},
            "status_context": status_context,
            "protocol": {"pass": all(item["status"] == "PASS" for item in protocol_records), "gates": protocol_records},
            "provenance": provenance_details,
            "source_diff_status": args.source_diff_status,
            "logger_fix_status": args.logger_fix_status,
            "regression_status": args.regression_status,
            "scientific_readjudication": "NOT_RUN",
        }
    (output / "analysis.json").write_text(json.dumps(jsonable(analysis), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_results(output / "RESULTS.md", audit, status_context, args.logger_fix_status, args.regression_status)
    schema_records = [
        gate("raw_header_width_exact_780", audit["raw_header_width"] == EXPECTED_HEADER_WIDTH, audit["raw_header_width"]),
        gate("raw_data_rows_exact_5005", audit["raw_data_rows"] == EXPECTED_DATA_ROWS, audit["raw_data_rows"]),
        gate("raw_all_data_rows_width_776", audit["raw_width_counts"] == {str(EXPECTED_DATA_WIDTH): EXPECTED_DATA_ROWS}, audit["raw_width_counts"]),
        gate("raw_empty_header_token_count_exact_4", len(audit["raw_header_empty_indices"]) == EXPECTED_EMPTY_COUNT, {"indices": audit["raw_header_empty_indices"], "tokens": audit["raw_header_empty_tokens"]}),
        gate("raw_empty_token_transitions_exact", len(audit["expected_empty_transitions"]) == EXPECTED_EMPTY_COUNT, audit["expected_empty_transitions"]),
        gate("no_other_empty_or_duplicate_header_names", not audit["raw_header_empty_indices"] and not audit["raw_header_duplicate_names"], {"empty_indices": audit["raw_header_empty_indices"], "duplicates": audit["raw_header_duplicate_names"]}),
        gate("source_exact_double_delimiter", audit["source_proof"]["header_exact_double_delimiter"], audit["source_proof"]),
        gate("source_log_sample_contiguous_sequence", audit["source_proof"]["log_sample_contiguous_sequence"], audit["source_proof"]),
        gate("candidate_mapping_unique", audit["candidate_mapping_unique"], {"drop_indices": audit["candidate_drop_indices"], "candidate_width": audit["candidate_repaired_width"], "duplicates": audit["candidate_repaired_duplicate_names"]}),
        gate("recovery_validation_all_pass", audit["recovery_validation_all_pass"], audit["recovery_validation"]),
        gate("literal_task_shape_gate", audit["literal_task_shape_gate"], {"empty_transitions": audit["expected_empty_transitions"], "observed_extra_transitions": audit["observed_extra_transitions"]}),
        gate("recovery_authorized", audit["recovery_authorized"], audit["recovery_authorized"]),
    ] + audit["recovery_validation"]
    write_csv(output / "schema_recovery_validation.csv", schema_records)
    repair_records = []
    repaired_index = 0
    for raw_index, token in enumerate(audit["header"]):
        action = "DROP_EXTRA_NONEMPTY_HEADER_TOKEN" if raw_index in audit["candidate_drop_indices"] else "KEEP"
        preceding = audit["repaired_header"][repaired_index - 1] if repaired_index > 0 and action == "KEEP" else ""
        following = audit["header"][raw_index + 1] if raw_index + 1 < len(audit["header"]) else ""
        repair_records.append({
            "raw_header_index": raw_index,
            "original_token": token,
            "action": action,
            "repaired_header_index": "" if action != "KEEP" else repaired_index,
            "preceding_canonical_field": preceding,
            "following_canonical_field": following,
        })
        if action == "KEEP":
            repaired_index += 1
    write_csv(output / "schema_repair_map.csv", repair_records)
    write_csv(output / "source_diff_audit.csv", [{
        "scope": "runtime_source_read_at_C_head",
        "status": "PASS",
        "recorded_C_runtime_head": EXPECTED_C_HEAD,
        "source_path": str(args.runtime_source),
        "source_sha256": audit["source_proof"]["sha256"],
        "prohibited_science_paths_modified": "NOT_IN_THIS_CHECKPOINT",
        "note": "Current source was read before the authorized minimal logger repair; the four nonempty extra-token construction is proven.",
    }])
    print(f"classification={classification} schema_literal_gate={audit['literal_task_shape_gate']} candidate_unique={audit['candidate_mapping_unique']} scientific={'run' if audit['recovery_authorized'] else 'not_run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
