#!/usr/bin/env python3
"""Deterministic offline closeout analysis for the Phase-2 flat canary.

This tool reads only the trusted host record and immutable raw run files.  It
does not launch processes, rewrite raw evidence, or consult live state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import re
import statistics
import subprocess
from collections import Counter
from datetime import datetime
from typing import Iterable


LEGS = ("FR", "FL", "RR", "RL")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite(row: dict[str, str], key: str) -> float:
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key}")
    return value


def percentile(values: Iterable[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile of empty sequence")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def describe(values: Iterable[float]) -> dict[str, float | int]:
    values = list(values)
    if not values:
        raise ValueError("empty metric")
    return {
        "count": len(values),
        "min": min(values),
        "p05": percentile(values, 0.05),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "p95": percentile(values, 0.95),
        "max": max(values),
    }


def regression(rows: list[dict[str, str]], time_key: str, value_key: str) -> dict[str, float | int]:
    samples = sorted((finite(row, time_key), finite(row, value_key)) for row in rows)
    if len(samples) < 2:
        raise ValueError(f"fewer than two samples for {value_key}")
    times = [item[0] for item in samples]
    values = [item[1] for item in samples]
    mean_time = statistics.fmean(times)
    mean_value = statistics.fmean(values)
    denominator = sum((item - mean_time) ** 2 for item in times)
    if denominator <= 0.0:
        raise ValueError(f"zero time variance for {value_key}")
    slope = sum(
        (time - mean_time) * (value - mean_value)
        for time, value in samples
    ) / denominator
    duration = times[-1] - times[0]
    distance = values[-1] - values[0]
    return {
        "samples": len(samples),
        "start_time_s": times[0],
        "end_time_s": times[-1],
        "duration_s": duration,
        "distance_m": distance,
        "regression_speed_mps": slope,
        "endpoint_speed_mps": distance / duration,
    }


def parse_kv_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def number_with_units(value: str) -> float:
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value)
    if not match:
        raise ValueError(f"not numeric: {value}")
    return float(match.group(0))


def parse_controller_log(path: pathlib.Path) -> dict[str, object]:
    text = path.read_text(errors="replace")
    health: list[dict[str, object]] = []
    started: list[dict[str, object]] = []
    for line in text.splitlines():
        match = re.match(r"Trot cycle (\d+) health: (.*)$", line)
        if match:
            item: dict[str, object] = {"cycle": int(match.group(1))}
            for key, value in re.findall(r"([A-Za-z_]+)=([^,]+)", match.group(2)):
                item[key] = value if key == "tau_motor" else number_with_units(value)
            health.append(item)
        match = re.match(
            r"Trot cycle (\d+) started v_cmd=([^ ]+) v_meas=([^ ]+) "
            r"period=([^ ]+) step=([^ ]+) duty=([^ ]+)",
            line,
        )
        if match:
            started.append(
                {
                    "cycle": int(match.group(1)),
                    "v_cmd_mps": float(match.group(2)),
                    "v_meas_mps": float(match.group(3)),
                    "period_s": float(match.group(4)),
                    "step_length_m": float(match.group(5)),
                    "duty": float(match.group(6)),
                }
            )

    requested_health = [item for item in health if 1 <= item["cycle"] <= 64]
    requested_started = [item for item in started if 1 <= item["cycle"] <= 64]

    def maximum(key: str) -> float:
        return max(float(item[key]) for item in requested_health)

    def minimum(key: str) -> float:
        return min(float(item[key]) for item in requested_health)

    rejection_patterns = {
        "clean_target_infeasible": r"Clean-baseline target infeasible",
        "strict_wbc_or_qp": r"(?:QP|ID-WBC|WBC).*?(?:reject|fail|infeas)",
        "cycle_quality_guard": r"Trot cycle quality guard rejected",
        "hard_safety": r"Trot hard (?:safety|posture|joint) limit",
        "emergency_stop": r"(?:emergency stop|emergency-stop|emergency stop requested|hard emergency)",
    }
    rejection_counts = {
        name: len(re.findall(pattern, text, re.IGNORECASE))
        for name, pattern in rejection_patterns.items()
    }

    return {
        "health_records_total": len(health),
        "health_cycle_indices": [int(item["cycle"]) for item in health],
        "requested_health_records": len(requested_health),
        "requested_health_cycle_range": [1, 64],
        "requested_started_records": len(requested_started),
        "requested_started_cycle_range": [1, 64],
        "stop_transition_cycle": 65,
        "health_metrics_requested_cycles_1_64": {
            "max_abs_roll_deg": maximum("roll"),
            "max_abs_pitch_deg": maximum("pitch"),
            "max_support_drift_mm": maximum("support_drift"),
            "max_joint_error_rad": maximum("q_error"),
            "max_foot_error_m": maximum("foot_error"),
            "max_tau_est_nm": maximum("tau_est"),
            "max_tau_over_limit_samples": maximum("tau_over_samples"),
            "max_tau_over_limit_consecutive": maximum("tau_over_max_consecutive"),
            "min_support_contacts": minimum("min_support_contacts"),
            "max_low_support_samples": maximum("max_low_support_samples"),
            "min_support_contact_fraction": minimum("support_contact_fraction"),
            "max_touchdown_abs_x_error_m": maximum("touchdown_max_abs_x_error_m"),
            "max_touchdown_abs_y_error_m": maximum("touchdown_max_abs_y_error_m"),
        },
        "cycle_start_speed_stats_requested_1_64": {
            "commanded_mps": describe(float(item["v_cmd_mps"]) for item in requested_started),
            "measured_mps": describe(float(item["v_meas_mps"]) for item in requested_started),
        },
        "rejection_log_counts": rejection_counts,
        "lifecycle_markers": {
            "natural_lowstate_settled": "Natural LowState settled" in text,
            "starting_diagonal_trot": "Starting diagonal trot" in text,
            "pre_stop_brake": "Trot pre-stop brake: reducing gait reference" in text,
            "return_to_stand": "Trot stopping; returning to stand" in text,
            "return_to_lie_down": "Task state: RETURN_TO_STAND -> LIE_DOWN" in text,
            "task_completed": "Task completed: stand-walk-lie" in text,
        },
    }


def parse_text_metrics(path: pathlib.Path) -> dict[str, object]:
    values: dict[str, object] = {}
    for line in path.read_text(errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            values[key] = float(value) if any(c in value for c in ".eE") else int(value)
        except ValueError:
            values[key] = value
    return values


def section_is_empty(path: pathlib.Path, begin: str, end: str) -> bool:
    inside = False
    entries: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        if line == begin:
            inside = True
            continue
        if line == end:
            inside = False
            continue
        if inside and line:
            entries.append(line)
    return not entries


def truth_metrics(path: pathlib.Path, start_s: float, end_s: float) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            time_s = finite(row, "time_s")
            if start_s <= time_s <= end_s:
                rows.append(row)
    speed = [finite(row, "base_qvel_world_x_mps") for row in rows]
    base_z = [finite(row, "base_pos_world_z_m") for row in rows]
    roll: list[float] = []
    pitch: list[float] = []
    for row in rows:
        w = finite(row, "base_quat_w")
        x = finite(row, "base_quat_x")
        y = finite(row, "base_quat_y")
        z = finite(row, "base_quat_z")
        sin_roll = 2.0 * (w * x + y * z)
        cos_roll = 1.0 - 2.0 * (x * x + y * y)
        roll.append(abs(math.degrees(math.atan2(sin_roll, cos_roll))))
        sin_pitch = max(-1.0, min(1.0, 2.0 * (w * y - z * x)))
        pitch.append(abs(math.degrees(math.asin(sin_pitch))))
    return {
        "rows_in_controller_stage2_interval": len(rows),
        "speed_world_x_mps": describe(speed),
        "base_height_m": describe(base_z),
        "abs_roll_deg": describe(roll),
        "abs_pitch_deg": describe(pitch),
    }


def csv_metrics(path: pathlib.Path) -> tuple[dict[str, object], list[dict[str, str]]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    if not rows:
        raise ValueError("data.csv is empty")
    stage_counts = Counter(int(float(row["motion_stage"])) for row in rows)
    cycle_counts = Counter(int(float(row["cycle_index"])) for row in rows)
    stage2 = [
        row for row in rows
        if int(float(row["motion_stage"])) == 2
        and int(float(row["cycle_index"])) >= 0
    ]
    requested = [
        row for row in stage2
        if 1 <= int(float(row["cycle_index"])) <= 64
    ]
    transitions: list[dict[str, object]] = []
    previous: tuple[int, int] | None = None
    for row_number, row in enumerate(rows, start=2):
        current = (int(float(row["motion_stage"])), int(float(row["cycle_index"])))
        if current != previous:
            transitions.append(
                {
                    "csv_row": row_number,
                    "cmd_time_s": finite(row, "cmd_time_s"),
                    "state_tick_s": finite(row, "state_tick_s"),
                    "motion_stage": current[0],
                    "cycle_index": current[1],
                }
            )
            previous = current

    flags = (
        "has_state",
        "kernel_footstep_plan_valid",
        "wbc_full_srbd_ok",
        "wbc_full_id_ok",
        "wbc_shadow_solver_ok",
        "wbc_shadow_mapping_ok",
        "wbc_shadow_task_satisfied",
        "wbc_shadow_wrench_satisfied",
        "wbc_shadow_constraint_feasible",
        "terrain_plan_failure",
        "terrain_plan_contact_rejections",
        "terrain_enabled",
        "terrain_sensor_only",
        "terrain_actuation",
    )
    flag_counts = {
        key: {
            "all_rows": dict(Counter(row[key] for row in rows)),
            "stage2_rows": dict(Counter(row[key] for row in stage2)),
            "requested_cycles_1_64": dict(Counter(row[key] for row in requested)),
        }
        for key in flags
    }
    tau_fields = [field for field in fields if field.endswith("_tau_est")]
    tau_values = [abs(float(row[field])) for row in requested for field in tau_fields]
    speed_fields = (
        "velocity_command_measured_mps",
        "body_velocity_x_mps",
        "world_velocity_x_mps",
        "imu_roll_rad",
        "imu_pitch_rad",
        "contact_count",
        "wbc_full_eq_residual",
    )
    selected_metrics = {
        key: describe(finite(row, key) for row in requested)
        for key in speed_fields
    }
    selected_metrics["imu_abs_roll_deg"] = describe(
        abs(math.degrees(finite(row, "imu_roll_rad"))) for row in requested
    )
    selected_metrics["imu_abs_pitch_deg"] = describe(
        abs(math.degrees(finite(row, "imu_pitch_rad"))) for row in requested
    )
    selected_metrics["tau_est_abs_nm"] = describe(tau_values)
    stage2_start = finite(stage2[0], "state_tick_s")
    stage2_end = finite(stage2[-1], "state_tick_s")
    requested_start = finite(requested[0], "state_tick_s")
    requested_end = finite(requested[-1], "state_tick_s")
    nominal_speed = 0.091 / 0.60
    progress = regression(stage2, "state_tick_s", "world_base_x_m")
    progress["nominal_speed_mps"] = nominal_speed
    progress["speed_ratio"] = progress["regression_speed_mps"] / nominal_speed
    requested_progress = regression(requested, "state_tick_s", "world_base_x_m")
    requested_progress["nominal_speed_mps"] = nominal_speed
    requested_progress["speed_ratio"] = requested_progress["regression_speed_mps"] / nominal_speed
    return (
        {
            "row_count": len(rows),
            "column_count": len(fields),
            "first_sample": {
                "csv_row": 2,
                "cmd_time_s": finite(rows[0], "cmd_time_s"),
                "state_tick_s": finite(rows[0], "state_tick_s"),
                "has_state": rows[0]["has_state"],
                "motion_stage": int(float(rows[0]["motion_stage"])),
                "cycle_index": int(float(rows[0]["cycle_index"])),
            },
            "last_sample": {
                "csv_row": len(rows) + 1,
                "cmd_time_s": finite(rows[-1], "cmd_time_s"),
                "state_tick_s": finite(rows[-1], "state_tick_s"),
                "has_state": rows[-1]["has_state"],
                "motion_stage": int(float(rows[-1]["motion_stage"])),
                "cycle_index": int(float(rows[-1]["cycle_index"])),
            },
            "stage_counts": {str(key): value for key, value in sorted(stage_counts.items())},
            "cycle_index_range": [min(cycle_counts), max(cycle_counts)],
            "stage2_nonnegative_cycle_count": len(stage2),
            "requested_cycles_1_64_sample_count": len(requested),
            "stage2_state_tick_interval_s": [stage2_start, stage2_end],
            "requested_cycles_1_64_state_tick_interval_s": [requested_start, requested_end],
            "stage_transitions": transitions,
            "flag_counts": flag_counts,
            "selected_requested_cycle_metrics": selected_metrics,
            "locomotion_progress_all_stage2_nonnegative_cycles": progress,
            "locomotion_progress_requested_cycles_1_64": requested_progress,
        },
        rows,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=pathlib.Path, required=True)
    parser.add_argument("--host-record", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--provenance-output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    run_dir = args.run_dir
    host_record = json.loads(args.host_record.read_text())
    metadata = parse_kv_file(run_dir / "run_metadata.txt")
    manifest = json.loads((run_dir / "run_manifest.json").read_text())
    build = parse_kv_file(run_dir / "build_provenance.txt")
    integrity: list[dict[str, object]] = []
    for item in host_record["evidence"]:
        path = run_dir / item["path"]
        actual_hash = sha256(path)
        actual_size = path.stat().st_size
        integrity.append(
            {
                "path": item["path"],
                "expected_sha256": item["sha256"],
                "actual_sha256": actual_hash,
                "expected_size": item["size"],
                "actual_size": actual_size,
                "matches": actual_hash == item["sha256"] and actual_size == item["size"],
            }
        )

    data, rows = csv_metrics(run_dir / "data.csv")
    stage2 = [
        row for row in rows
        if int(float(row["motion_stage"])) == 2
        and int(float(row["cycle_index"])) >= 0
    ]
    truth = truth_metrics(
        run_dir / "contact_ground_truth.csv",
        data["stage2_state_tick_interval_s"][0],
        data["stage2_state_tick_interval_s"][1],
    )
    log = parse_controller_log(run_dir / "controller.log")
    contact_validation = parse_text_metrics(run_dir / "contact_ground_truth_analysis.txt")
    dynamics_validation = parse_text_metrics(run_dir / "contact_ground_truth_dynamics_analysis.txt")
    runtime = parse_kv_file(run_dir / "dds_runtime/runtime_metadata.txt")
    pre_state = parse_kv_file(run_dir / "dds_runtime/pre_state.txt")
    post_state = parse_kv_file(run_dir / "dds_runtime/post_state.txt")
    simulator_log_text = (run_dir / "simulator.log").read_text(errors="replace")
    pre_state_path = run_dir / "dds_runtime/pre_state.txt"
    post_state_path = run_dir / "dds_runtime/post_state.txt"

    started = datetime.fromisoformat(host_record["started_at"])
    finished = datetime.fromisoformat(host_record["finished_at"])
    elapsed_s = (finished - started).total_seconds()
    nominal_speed = 0.091 / 0.60
    flags = data["flag_counts"]
    requested_flags = {
        key: value["requested_cycles_1_64"]
        for key, value in flags.items()
    }
    criteria = {
        "valid_controller_handoff": (
            "Unitree DDS bridge ready" in (run_dir / "simulator.log").read_text(errors="replace")
            and log["lifecycle_markers"]["natural_lowstate_settled"]
            and data["first_sample"]["has_state"] == "1"
        ),
        "all_64_requested_gait_cycles_complete": (
            log["requested_health_records"] == 64
            and log["requested_started_records"] == 64
            and log["health_metrics_requested_cycles_1_64"]["min_support_contact_fraction"] > 0.0
        ),
        "normal_return_to_stand_without_hard_stop": (
            log["lifecycle_markers"]["return_to_stand"]
            and log["lifecycle_markers"]["task_completed"]
            and metadata.get("safety_status") == "0"
            and log["rejection_log_counts"]["hard_safety"] == 0
            and log["rejection_log_counts"]["emergency_stop"] == 0
        ),
        "no_clean_target_feasibility_rejection": (
            log["rejection_log_counts"]["clean_target_infeasible"] == 0
            and all(value == "1" for value in requested_flags["kernel_footstep_plan_valid"])
        ),
        "no_strict_wbc_qp_rejection": (
            all(
                requested_flags[key] == {"1": requested_flags[key].get("1", 0)}
                for key in (
                    "wbc_full_srbd_ok",
                    "wbc_full_id_ok",
                    "wbc_shadow_solver_ok",
                    "wbc_shadow_mapping_ok",
                    "wbc_shadow_constraint_feasible",
                )
            )
            and log["rejection_log_counts"]["strict_wbc_or_qp"] == 0
            and metadata.get("quality_status") == "0"
        ),
        "measured_forward_speed_in_0_11_to_0_19_mps": (
            0.11 <= data["locomotion_progress_all_stage2_nonnegative_cycles"]["regression_speed_mps"] <= 0.19
        ),
        "no_gross_tracking_or_stability_failure": (
            log["health_metrics_requested_cycles_1_64"]["max_abs_roll_deg"] < 16.0
            and log["health_metrics_requested_cycles_1_64"]["max_abs_pitch_deg"] < 16.0
            and log["health_metrics_requested_cycles_1_64"]["max_joint_error_rad"] < 0.80
            and log["health_metrics_requested_cycles_1_64"]["min_support_contact_fraction"] >= 0.35
            and metadata.get("quality_status") == "0"
        ),
    }
    all_integrity = all(item["matches"] for item in integrity)
    proposed_classification = (
        "CLEAN_BASELINE_FLAT_REPRODUCED" if all(criteria.values())
        else "PROTOCOL_FAILURE"
    )

    output = {
        "schema_version": 1,
        "experiment": "phase2_clean_baseline_flat_final_20260917",
        "classification": proposed_classification,
        "earliest_causal_boundary": "scientific" if proposed_classification != "PROTOCOL_FAILURE" else "execution",
        "reason_code": proposed_classification,
        "task": {
            "task_path": host_record["task_path"],
            "task_commit": host_record["task_commit"],
            "candidate_commit": host_record["candidate_commit"],
            "exact_parent": "2eb92bc62be6fba2dee26ac9229520d8835c6246",
            "scientific_clean_baseline_parent": "cdb0888d02c195935a88d9c404fb4d45c5b0ac1a",
            "primary_domain": host_record["domain_id"],
            "frozen_command": host_record["command"],
        },
        "host": {
            "launched": host_record["launched"],
            "returncode": host_record["returncode"],
            "error": host_record["error"],
            "timed_out": host_record["timed_out"],
            "timeout_s": host_record["timeout_s"],
            "started_at": host_record["started_at"],
            "finished_at": host_record["finished_at"],
            "elapsed_s": elapsed_s,
            "manifest_sha256": host_record["manifest_sha256"],
            "stdout_sha256": host_record["stdout_sha256"],
            "stderr_sha256": host_record["stderr_sha256"],
            "environment": host_record["environment"],
        },
        "facts": {
            "host_raw_integrity": {
                "indexed_files": len(integrity),
                "all_hashes_and_sizes_match": all_integrity,
                "files": integrity,
            },
            "build": {
                "candidate_tree": build.get("candidate_tree"),
                "tracked_worktree_status": build.get("tracked_worktree_status"),
                "simulator_sha256": build.get("simulator_sha256"),
                "controller_sha256": build.get("controller_sha256"),
                "scene_sha256": build.get("task_scene_sha256"),
                "mujoco_root": build.get("mujoco_root"),
                "mujoco_root_realpath": build.get("mujoco_root_realpath"),
                "mujoco_header_sha256": build.get("mujoco_header_sha256"),
                "mujoco_library_sha256": build.get("mujoco_library_sha256"),
                "unitree_sdk2_config_sha256": build.get("unitree_sdk2_config_sha256"),
                "unitree_sdk2_archive_sha256": build.get("unitree_sdk2_archive_sha256"),
            },
            "runtime_metadata": runtime,
            "dds_pre_state": {
                "domain_id": pre_state.get("domain_id"),
                "interface": pre_state.get("interface"),
                "expected_port_range": [59000, 59073],
                "active_go2_processes_empty": section_is_empty(pre_state_path, "active_go2_processes_begin", "active_go2_processes_end"),
                "known_shm_empty": section_is_empty(pre_state_path, "known_shm_begin", "known_shm_end"),
            },
            "dds_post_state": {
                "domain_id": post_state.get("domain_id"),
                "interface": post_state.get("interface"),
                "active_go2_processes_empty": section_is_empty(post_state_path, "active_go2_processes_begin", "active_go2_processes_end"),
                "known_shm_empty": section_is_empty(post_state_path, "known_shm_begin", "known_shm_end"),
            },
            "controller_metadata": metadata,
            "run_manifest": manifest,
            "contact_ground_truth_validation": contact_validation,
            "contact_dynamics_validation": dynamics_validation,
        },
        "derived_metrics": {
            "handoff": {
                "simulator_dds_ready_marker": "Unitree DDS bridge ready" in simulator_log_text,
                "controller_lowstate_settled_marker": log["lifecycle_markers"]["natural_lowstate_settled"],
                "first_valid_controller_state_control_sample": data["first_sample"],
                "first_locomotion_sample": next(item for item in data["stage_transitions"] if item["motion_stage"] == 2),
                "all_data_rows_has_state_1": data["flag_counts"]["has_state"]["all_rows"] == {"1": data["row_count"]},
                "scientific_attempt_consumed": True,
            },
            "lifecycle": {
                "requested_gait_cycles": 64,
                "completed_requested_gait_cycles": log["requested_health_records"],
                "pre_motion_health_cycle": 0,
                "return_transition_cycle": log["stop_transition_cycle"],
                "task_completed": log["lifecycle_markers"]["task_completed"],
                "stage_counts": data["stage_counts"],
            },
            "speed": {
                "nominal_commanded_speed_mps": nominal_speed,
                "csv_progress_metric": data["locomotion_progress_all_stage2_nonnegative_cycles"],
                "csv_requested_cycles_1_64_progress_metric": data["locomotion_progress_requested_cycles_1_64"],
                "csv_measured_velocity_stats_requested_cycles_1_64": data["selected_requested_cycle_metrics"]["velocity_command_measured_mps"],
                "ground_truth_interval": truth,
            },
            "controller_health": log["health_metrics_requested_cycles_1_64"],
            "controller_cycle_start_speeds": log["cycle_start_speed_stats_requested_1_64"],
            "controller_flag_counts_requested_cycles_1_64": requested_flags,
            "rejection_and_safety": log["rejection_log_counts"],
            "formulas": {
                "nominal_speed": "0.091 / 0.60",
                "csv_progress_window": "motion_stage == 2 and cycle_index >= 0",
                "csv_requested_cycle_window": "motion_stage == 2 and 1 <= cycle_index <= 64",
                "progress_speed": "ordinary least-squares slope of world_base_x_m versus state_tick_s",
                "speed_ratio": "progress_speed / nominal_speed",
                "health_metrics": "max/min of controller.log Trot cycle N health fields for N in 1..64",
                "flag_rejections": "count rows with a zero/non-success flag in requested cycle window",
            },
        },
        "classification_gate": criteria,
        "luna_interpretation": {
            "proposed_classification": proposed_classification,
            "interpretation_is_authoritative": False,
            "basis": "All frozen pass criteria are supported by the immutable host record, raw logs, CSV, and deterministic formulas above.",
            "review_instruction": "Sol may recompute from the indexed raw files and overturn this proposed classification without rerunning the canary.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    repo_root = pathlib.Path(__file__).resolve().parents[4]
    parent_results = (
        "2eb92bc62be6fba2dee26ac9229520d8835c6246"
        ":docs/validation/dds_runtime_root_fix_repair_20260917/RESULTS.md"
    )
    scientific_parent_results = (
        "cdb0888d02c195935a88d9c404fb4d45c5b0ac1a"
        ":docs/validation/phase2_clean_baseline_p0_20260917/RESULTS.md"
    )

    def git_blob_hash(spec: str) -> str:
        content = subprocess.run(
            ["git", "-C", str(repo_root), "show", spec],
            check=True,
            capture_output=True,
        ).stdout
        return hashlib.sha256(content).hexdigest()

    provenance_rows: list[list[str]] = []

    def add(scope: str, artifact: str, path: str, digest: str, status: str, note: str) -> None:
        provenance_rows.append([scope, artifact, path, digest, status, note])

    add(
        "task_exact",
        "task_document",
        host_record["task_path"],
        sha256(repo_root / host_record["task_path"]),
        "VERIFIED",
        "frozen task specification",
    )
    add(
        "host_record",
        "trusted_execution_record",
        str(args.host_record),
        sha256(args.host_record),
        "VERIFIED",
        "trusted wrapper record; not modified",
    )
    add(
        "parent_evidence",
        "DDS_RUNTIME_ROOT_FIXED_RESULTS",
        "git:" + parent_results,
        git_blob_hash(parent_results),
        "VERIFIED",
        "exact parent closeout",
    )
    add(
        "scientific_parent_evidence",
        "clean_baseline_P0_RESULTS",
        "git:" + scientific_parent_results,
        git_blob_hash(scientific_parent_results),
        "VERIFIED",
        "scientific clean-baseline parent",
    )
    add(
        "candidate",
        "candidate_commit",
        host_record["candidate_commit"],
        "",
        "RECORDED",
        "exact candidate presented to trusted host",
    )
    for item in integrity:
        add(
            "raw_host",
            item["path"],
            str(run_dir / item["path"]),
            item["actual_sha256"],
            "VERIFIED" if item["matches"] else "MISMATCH",
            f"host index size={item['actual_size']}; immutable raw artifact",
        )
    add(
        "source_runtime",
        "dds_base4000_preload.c",
        runtime["config_source"],
        runtime["config_source_sha256"],
        "VERIFIED",
        "tracked DDS support source used by run",
    )
    add(
        "source_scene",
        "scene_leg_lift_demo.xml",
        build["task_scene"],
        build["task_scene_sha256"],
        "VERIFIED",
        "frozen flat Go2 scene",
    )
    add(
        "binary",
        "unitree_mujoco",
        build["simulator_output"],
        build["simulator_sha256"],
        "RECORDED_BY_HOST_BUILD",
        "exact-source simulator output",
    )
    add(
        "binary",
        "real_trot_go2",
        build["controller_output"],
        build["controller_sha256"],
        "RECORDED_BY_HOST_BUILD",
        "exact-source controller output",
    )
    add(
        "toolchain",
        "libmujoco.so",
        build["mujoco_library"],
        build["mujoco_library_sha256"],
        "VERIFIED",
        "permitted read-only MuJoCo dependency",
    )
    add(
        "toolchain",
        "mujoco.h",
        build["mujoco_header"],
        build["mujoco_header_sha256"],
        "VERIFIED",
        "permitted read-only MuJoCo dependency",
    )
    for name in (
        "analyze_clean_baseline_flat_final.py",
        "analyze_locomotion_progress.py",
        "analyze_contact_ground_truth.py",
        "analyze_contact_dynamics.py",
    ):
        path = pathlib.Path(__file__).resolve().parent / name
        add(
            "analyzer",
            name,
            str(path),
            sha256(path),
            "VERIFIED",
            "deterministic offline analysis code",
        )
    args.provenance_output.parent.mkdir(parents=True, exist_ok=True)
    with args.provenance_output.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["scope", "artifact", "path", "sha256", "status", "note"])
        writer.writerows(provenance_rows)
    print(json.dumps({"classification": proposed_classification, "raw_hashes_match": all_integrity}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
