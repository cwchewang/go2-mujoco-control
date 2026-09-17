#!/usr/bin/env python3
"""Deterministic offline closeout for canonical clean-baseline repeat R3.

This analyzer reads the trusted host record and immutable raw artifacts only.
It does not launch a simulator/controller, modify raw evidence, or consult
live state.
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


ROOT = pathlib.Path(__file__).resolve().parents[4]
LEGS = ("FR", "FL", "RR", "RL")
REQUESTED_FLAGS = (
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


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def kv(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def finite(row: dict[str, str], key: str) -> float:
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key}")
    return value


def number(value: str) -> float:
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value)
    if not match:
        raise ValueError(f"not numeric: {value}")
    return float(match.group(0))


def percentile(values: list[float], fraction: float) -> float:
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


def describe(values: list[float]) -> dict[str, float | int]:
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


def ols(rows: list[dict[str, str]], time_key: str, value_key: str) -> dict[str, float | int]:
    samples = sorted((finite(row, time_key), finite(row, value_key)) for row in rows)
    if len(samples) < 2:
        raise ValueError(f"fewer than two samples for {value_key}")
    times = [sample[0] for sample in samples]
    values = [sample[1] for sample in samples]
    mean_time = statistics.fmean(times)
    mean_value = statistics.fmean(values)
    denominator = sum((time - mean_time) ** 2 for time in times)
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


def parse_text_metrics(path: pathlib.Path) -> dict[str, object]:
    result: dict[str, object] = {}
    for line in path.read_text(errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            result[key] = float(value) if any(c in value for c in ".eE") else int(value)
        except ValueError:
            result[key] = value
    return result


def section_empty(path: pathlib.Path, begin: str, end: str) -> bool:
    inside = False
    entries: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        if line == begin:
            inside = True
        elif line == end:
            inside = False
        elif inside and line:
            entries.append(line)
    return not entries


def parse_controller_log(path: pathlib.Path) -> dict[str, object]:
    text = path.read_text(errors="replace")
    health: list[dict[str, object]] = []
    started: list[dict[str, object]] = []
    for line in text.splitlines():
        match = re.match(r"Trot cycle (\d+) health: (.*)$", line)
        if match:
            item: dict[str, object] = {"cycle": int(match.group(1))}
            for key, value in re.findall(r"([A-Za-z_]+)=([^,]+)", match.group(2)):
                item[key] = value if key == "tau_motor" else number(value)
            health.append(item)
        match = re.match(
            r"Trot cycle (\d+) started v_cmd=([^ ]+) v_meas=([^ ]+) "
            r"period=([^ ]+) step=([^ ]+) duty=([^ ]+)",
            line,
        )
        if match:
            started.append({
                "cycle": int(match.group(1)),
                "v_cmd_mps": float(match.group(2)),
                "v_meas_mps": float(match.group(3)),
                "period_s": float(match.group(4)),
                "step_length_m": float(match.group(5)),
                "duty": float(match.group(6)),
            })

    requested_health = [item for item in health if 1 <= item["cycle"] <= 64]
    requested_started = [item for item in started if 1 <= item["cycle"] <= 64]

    def max_abs(key: str) -> float:
        return max(abs(float(item[key])) for item in requested_health)

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
    markers = {
        "natural_lowstate_settled": "Natural LowState settled" in text,
        "starting_diagonal_trot": "Starting diagonal trot" in text,
        "pre_stop_brake": "Trot pre-stop brake: reducing gait reference" in text,
        "return_to_stand": "Trot stopping; returning to stand" in text,
        "return_to_lie_down": "Task state: RETURN_TO_STAND -> LIE_DOWN" in text,
        "task_completed": "Task completed: stand-walk-lie" in text,
    }
    return {
        "health_records_total": len(health),
        "health_cycle_indices": [int(item["cycle"]) for item in health],
        "started_records_total": len(started),
        "started_cycle_indices": [int(item["cycle"]) for item in started],
        "requested_health_records": len(requested_health),
        "requested_started_records": len(requested_started),
        "requested_cycle_range": [1, 64],
        "stop_transition_cycle": max((int(item["cycle"]) for item in started), default=None),
        "health_metrics_requested_cycles_1_64": {
            "max_abs_roll_deg": max_abs("roll"),
            "max_abs_pitch_deg": max_abs("pitch"),
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
            "commanded_mps": describe([float(item["v_cmd_mps"]) for item in requested_started]),
            "measured_mps": describe([float(item["v_meas_mps"]) for item in requested_started]),
        },
        "rejection_log_counts": rejection_counts,
        "lifecycle_markers": markers,
    }


def truth_metrics(path: pathlib.Path, start_s: float, end_s: float) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
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
        roll.append(abs(math.degrees(math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y)))))
        pitch_arg = max(-1.0, min(1.0, 2.0 * (w * y - z * x)))
        pitch.append(abs(math.degrees(math.asin(pitch_arg))))
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
    for csv_row, row in enumerate(rows, start=2):
        current = (int(float(row["motion_stage"])), int(float(row["cycle_index"])))
        if current != previous:
            transitions.append({
                "csv_row": csv_row,
                "cmd_time_s": finite(row, "cmd_time_s"),
                "state_tick_s": finite(row, "state_tick_s"),
                "motion_stage": current[0],
                "cycle_index": current[1],
            })
            previous = current

    flag_counts = {
        key: {
            "all_rows": dict(Counter(row[key] for row in rows)),
            "stage2_rows": dict(Counter(row[key] for row in stage2)),
            "requested_cycles_1_64": dict(Counter(row[key] for row in requested)),
        }
        for key in REQUESTED_FLAGS
    }
    selected_keys = (
        "velocity_command_measured_mps",
        "body_velocity_x_mps",
        "world_velocity_x_mps",
        "contact_count",
        "wbc_full_eq_residual",
    )
    selected = {
        key: describe([finite(row, key) for row in requested])
        for key in selected_keys
    }
    selected["imu_abs_roll_deg"] = describe(
        [abs(math.degrees(finite(row, "imu_roll_rad"))) for row in requested]
    )
    selected["imu_abs_pitch_deg"] = describe(
        [abs(math.degrees(finite(row, "imu_pitch_rad"))) for row in requested]
    )
    tau_fields = [field for field in fields if field.endswith("_tau_est")]
    selected["tau_est_abs_nm"] = describe(
        [abs(float(row[field])) for row in requested for field in tau_fields]
    )

    nominal_speed = 0.091 / 0.60
    progress = ols(stage2, "state_tick_s", "world_base_x_m")
    progress["nominal_speed_mps"] = nominal_speed
    progress["speed_ratio"] = progress["regression_speed_mps"] / nominal_speed
    requested_progress = ols(requested, "state_tick_s", "world_base_x_m")
    requested_progress["nominal_speed_mps"] = nominal_speed
    requested_progress["speed_ratio"] = requested_progress["regression_speed_mps"] / nominal_speed
    data = {
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
        "stage2_state_tick_interval_s": [finite(stage2[0], "state_tick_s"), finite(stage2[-1], "state_tick_s")],
        "requested_cycles_1_64_state_tick_interval_s": [finite(requested[0], "state_tick_s"), finite(requested[-1], "state_tick_s")],
        "stage_transitions": transitions,
        "flag_counts": flag_counts,
        "selected_requested_cycle_metrics": selected,
        "locomotion_progress_all_stage2_nonnegative_cycles": progress,
        "locomotion_progress_requested_cycles_1_64": requested_progress,
    }
    return data, rows


def git_blob_sha(spec: str) -> str:
    content = subprocess.run(
        ["git", "-C", str(ROOT), "show", spec],
        check=True,
        capture_output=True,
    ).stdout
    return hashlib.sha256(content).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=pathlib.Path, required=True)
    parser.add_argument("--host-record", type=pathlib.Path, required=True)
    parser.add_argument("--task", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--provenance-output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    run_dir = args.run_dir
    host = json.loads(args.host_record.read_text())
    task_text = args.task.read_text()
    manifest_match = re.search(r"<!-- ATLAS_HOST_EXPERIMENT\s*(\{.*?\})\s*ATLAS_HOST_EXPERIMENT -->", task_text, re.S)
    task_manifest = json.loads(manifest_match.group(1)) if manifest_match else None
    metadata = kv(run_dir / "run_metadata.txt")
    run_manifest = json.loads((run_dir / "run_manifest.json").read_text())
    build = kv(run_dir / "build_provenance.txt")
    runtime = kv(run_dir / "dds_runtime/runtime_metadata.txt")
    pre_state = run_dir / "dds_runtime/pre_state.txt"
    post_state = run_dir / "dds_runtime/post_state.txt"
    simulator_log = (run_dir / "simulator.log").read_text(errors="replace")
    controller_log = parse_controller_log(run_dir / "controller.log")

    integrity: list[dict[str, object]] = []
    expected_paths = {item["path"] for item in host["evidence"]}
    for item in host["evidence"]:
        path = run_dir / item["path"]
        actual_size = path.stat().st_size
        actual_hash = sha256(path)
        integrity.append({
            "path": item["path"],
            "expected_sha256": item["sha256"],
            "actual_sha256": actual_hash,
            "expected_size": item["size"],
            "actual_size": actual_size,
            "matches": actual_hash == item["sha256"] and actual_size == item["size"],
        })
    actual_paths = {
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file()
    }
    all_integrity = all(item["matches"] for item in integrity) and actual_paths == expected_paths
    if not all_integrity:
        raise RuntimeError("raw evidence does not exactly match trusted host index")

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
    contact_validation = parse_text_metrics(run_dir / "contact_ground_truth_analysis.txt")
    dynamics_validation = parse_text_metrics(run_dir / "contact_ground_truth_dynamics_analysis.txt")
    requested_flags = {
        key: value["requested_cycles_1_64"]
        for key, value in data["flag_counts"].items()
    }
    health = controller_log["health_metrics_requested_cycles_1_64"]
    markers = controller_log["lifecycle_markers"]
    statuses_ok = all(metadata.get(key) == "0" for key in (
        "controller_status", "safety_status", "quality_status", "analysis_status",
        "ground_truth_status", "dynamics_status", "completion_status",
    ))
    requested_set = set(range(1, 65))
    started_set = set(controller_log["started_cycle_indices"])
    health_set = {
        cycle for cycle in controller_log["health_cycle_indices"]
        if 1 <= cycle <= 64
    }
    requested_rows_have_state = requested_flags["has_state"] == {"1": len([row for row in rows if int(float(row["motion_stage"])) == 2 and 1 <= int(float(row["cycle_index"])) <= 64])}
    target_flags_ok = (
        requested_flags["kernel_footstep_plan_valid"] == {"1": len([row for row in rows if int(float(row["motion_stage"])) == 2 and 1 <= int(float(row["cycle_index"])) <= 64])}
        and requested_flags["terrain_plan_failure"] == {"0.000000000": len([row for row in rows if int(float(row["motion_stage"])) == 2 and 1 <= int(float(row["cycle_index"])) <= 64])}
        and requested_flags["terrain_plan_contact_rejections"] == {"0": len([row for row in rows if int(float(row["motion_stage"])) == 2 and 1 <= int(float(row["cycle_index"])) <= 64])}
    )
    wbc_keys = (
        "wbc_full_srbd_ok", "wbc_full_id_ok", "wbc_shadow_solver_ok",
        "wbc_shadow_mapping_ok", "wbc_shadow_task_satisfied",
        "wbc_shadow_wrench_satisfied", "wbc_shadow_constraint_feasible",
    )
    wbc_flags_ok = all(requested_flags[key] == {"1": len([row for row in rows if int(float(row["motion_stage"])) == 2 and 1 <= int(float(row["cycle_index"])) <= 64])} for key in wbc_keys)
    progress = data["locomotion_progress_all_stage2_nonnegative_cycles"]
    criteria = {
        "valid_controller_handoff": (
            "Unitree DDS bridge ready" in simulator_log
            and markers["natural_lowstate_settled"]
            and data["first_sample"]["has_state"] == "1"
            and requested_rows_have_state
        ),
        "all_64_requested_gait_cycles_complete": (
            health_set == requested_set
            and started_set >= requested_set
            and controller_log["requested_health_records"] == 64
            and controller_log["requested_started_records"] == 64
        ),
        "normal_return_to_stand_without_hard_stop": (
            markers["return_to_stand"]
            and markers["return_to_lie_down"]
            and markers["task_completed"]
            and statuses_ok
            and controller_log["rejection_log_counts"]["hard_safety"] == 0
            and controller_log["rejection_log_counts"]["emergency_stop"] == 0
        ),
        "no_clean_target_feasibility_rejection": (
            controller_log["rejection_log_counts"]["clean_target_infeasible"] == 0
            and target_flags_ok
        ),
        "no_strict_wbc_qp_rejection": (
            wbc_flags_ok
            and controller_log["rejection_log_counts"]["strict_wbc_or_qp"] == 0
            and metadata.get("quality_status") == "0"
        ),
        "measured_forward_speed_in_0_11_to_0_19_mps": (
            0.11 <= progress["regression_speed_mps"] <= 0.19
        ),
        "no_gross_tracking_or_stability_failure": (
            health["max_abs_roll_deg"] < 16.0
            and health["max_abs_pitch_deg"] < 16.0
            and health["max_joint_error_rad"] < 0.80
            and health["min_support_contact_fraction"] >= 0.35
            and metadata.get("quality_status") == "0"
        ),
    }
    protocol_ok = (
        host["candidate_commit"] == "ba4d7ff8a865bd31f826e972b48105876ffa0640"
        and host["task_commit"] == host["candidate_commit"]
        and host["launched"] is True
        and host["returncode"] == 0
        and host["error"] is None
        and host["timed_out"] is False
        and metadata.get("git_head") == host["candidate_commit"]
        and metadata.get("git_dirty") == "false"
        and run_manifest["repository"]["git_commit"] == host["candidate_commit"]
        and task_manifest is not None
        and host["command"] == task_manifest["command"]
        and host["domain_id"] == task_manifest["domain_id"] == 220
        and all_integrity
    )
    if not protocol_ok:
        classification = "PROTOCOL_FAILURE"
        boundary = "execution"
    elif not criteria["valid_controller_handoff"] or not criteria["all_64_requested_gait_cycles_complete"] or not criteria["normal_return_to_stand_without_hard_stop"]:
        classification = "PROTOCOL_FAILURE"
        boundary = "execution"
    elif not criteria["no_clean_target_feasibility_rejection"]:
        classification = "CLEAN_BASELINE_TARGET_FEASIBILITY_FAIL"
        boundary = "scientific"
    elif not criteria["no_strict_wbc_qp_rejection"]:
        classification = "CLEAN_BASELINE_WBC_STRICT_FAIL"
        boundary = "scientific"
    elif not criteria["measured_forward_speed_in_0_11_to_0_19_mps"] or not criteria["no_gross_tracking_or_stability_failure"]:
        classification = "CLEAN_BASELINE_TRACKING_OR_STABILITY_FAIL"
        boundary = "scientific"
    else:
        classification = "CLEAN_BASELINE_FLAT_REPRODUCED"
        boundary = "scientific"

    host_elapsed = (
        datetime.fromisoformat(host["finished_at"]) - datetime.fromisoformat(host["started_at"])
    ).total_seconds()
    output = {
        "schema_version": 1,
        "experiment": "canonical_clean_baseline_repeatability_20260917",
        "replicate": "R3 / 3",
        "classification": classification,
        "earliest_causal_boundary": boundary,
        "reason_code": classification,
        "task": {
            "task_path": host["task_path"],
            "task_commit": host["task_commit"],
            "candidate_commit": host["candidate_commit"],
            "canonical_main": "e30782ad916ef1614a877d7a3c122f62682c8f19",
            "accepted_predecessor": "8b189c1bd7dab761c014f1db98e1223f3d73120d",
            "primary_domain": host["domain_id"],
            "frozen_command": host["command"],
        },
        "host": {
            "launched": host["launched"],
            "returncode": host["returncode"],
            "error": host["error"],
            "timed_out": host["timed_out"],
            "timeout_s": host["timeout_s"],
            "started_at": host["started_at"],
            "finished_at": host["finished_at"],
            "elapsed_s": host_elapsed,
            "manifest_sha256": host["manifest_sha256"],
            "stdout_sha256": host["stdout_sha256"],
            "stderr_sha256": host["stderr_sha256"],
            "environment": host["environment"],
        },
        "facts": {
            "host_raw_integrity": {
                "indexed_files": len(integrity),
                "all_hashes_and_sizes_match": all_integrity,
                "files": integrity,
            },
            "source_and_build": {
                "candidate_sha": build.get("candidate_sha"),
                "candidate_tree": build.get("candidate_tree"),
                "tracked_worktree_status": build.get("tracked_worktree_status"),
                "task_scene": build.get("task_scene"),
                "task_scene_sha256": build.get("task_scene_sha256"),
                "simulator_sha256": build.get("simulator_sha256"),
                "controller_sha256": build.get("controller_sha256"),
                "mujoco_root": build.get("mujoco_root"),
                "mujoco_root_realpath": build.get("mujoco_root_realpath"),
                "mujoco_header_sha256": build.get("mujoco_header_sha256"),
                "mujoco_library_sha256": build.get("mujoco_library_sha256"),
                "unitree_sdk2_config_sha256": build.get("unitree_sdk2_config_sha256"),
                "unitree_sdk2_archive_sha256": build.get("unitree_sdk2_archive_sha256"),
                "exact_source_wrapper_sha256": build.get("exact_source_wrapper_sha256"),
            },
            "run_manifest": run_manifest,
            "run_metadata": metadata,
            "simulator_log_facts": {
                "mujoco_version_marker": "MuJoCo version 3.3.6" in simulator_log,
                "dds_ready_marker": "Unitree DDS bridge ready" in simulator_log,
                "shutdown_marker": "SIGNAL: shutdown requested" in simulator_log,
            },
            "dds_runtime": runtime,
            "dds_pre_state": {
                "domain_id": kv(pre_state).get("domain_id"),
                "interface": kv(pre_state).get("interface"),
                "expected_port_range": [59000, 59073],
                "active_go2_processes_empty": section_empty(pre_state, "active_go2_processes_begin", "active_go2_processes_end"),
                "known_shm_empty": section_empty(pre_state, "known_shm_begin", "known_shm_end"),
            },
            "dds_post_state": {
                "domain_id": kv(post_state).get("domain_id"),
                "interface": kv(post_state).get("interface"),
                "active_go2_processes_empty": section_empty(post_state, "active_go2_processes_begin", "active_go2_processes_end"),
                "known_shm_empty": section_empty(post_state, "known_shm_begin", "known_shm_end"),
            },
            "controller_log": controller_log,
            "contact_ground_truth_validation": contact_validation,
            "contact_dynamics_validation": dynamics_validation,
        },
        "derived_metrics": {
            "handoff": {
                "simulator_dds_ready_marker": "Unitree DDS bridge ready" in simulator_log,
                "controller_lowstate_settled_marker": controller_log["lifecycle_markers"]["natural_lowstate_settled"],
                "first_valid_controller_state_control_sample": data["first_sample"],
                "first_locomotion_sample": next(item for item in data["stage_transitions"] if item["motion_stage"] == 2),
                "all_data_rows_has_state_1": data["flag_counts"]["has_state"]["all_rows"] == {"1": data["row_count"]},
                "scientific_attempt_consumed": True,
            },
            "lifecycle": {
                "requested_gait_cycles": 64,
                "completed_requested_gait_cycles": controller_log["requested_health_records"],
                "pre_motion_health_cycle": 0,
                "return_transition_cycle": controller_log["stop_transition_cycle"],
                "task_completed": controller_log["lifecycle_markers"]["task_completed"],
                "stage_counts": data["stage_counts"],
                "csv_rows": data["row_count"],
                "csv_columns": data["column_count"],
            },
            "speed": {
                "nominal_commanded_speed_mps": 0.091 / 0.60,
                "csv_progress_metric": data["locomotion_progress_all_stage2_nonnegative_cycles"],
                "csv_requested_cycles_1_64_progress_metric": data["locomotion_progress_requested_cycles_1_64"],
                "csv_measured_velocity_stats_requested_cycles_1_64": data["selected_requested_cycle_metrics"]["velocity_command_measured_mps"],
                "ground_truth_interval": truth,
            },
            "controller_health": health,
            "controller_cycle_start_speeds": controller_log["cycle_start_speed_stats_requested_1_64"],
            "controller_flag_counts_requested_cycles_1_64": requested_flags,
            "csv_selected_requested_cycle_metrics": data["selected_requested_cycle_metrics"],
            "rejection_and_safety": controller_log["rejection_log_counts"],
            "formulas": {
                "nominal_speed": "0.091 / 0.60",
                "csv_progress_window": "motion_stage == 2 and cycle_index >= 0",
                "csv_requested_cycle_window": "motion_stage == 2 and 1 <= cycle_index <= 64",
                "progress_speed": "ordinary least-squares slope of world_base_x_m versus state_tick_s",
                "speed_ratio": "progress_speed / nominal_speed",
                "health_metrics": "max/min of controller.log Trot cycle N health fields for N in 1..64; roll/pitch use max absolute value",
                "flag_counts": "Counter of raw CSV string values in each selected window",
                "contact_truth_window": "contact_ground_truth.time_s within the CSV stage-2 state_tick interval",
                "gross_tracking_gate": "max abs roll/pitch < 16 deg, max joint error < 0.80 rad, min support fraction >= 0.35, quality_status == 0",
            },
        },
        "classification_gate": criteria,
        "luna_interpretation": {
            "proposed_classification": classification,
            "interpretation_is_authoritative": False,
            "basis": "Proposed solely from the immutable trusted record, indexed raw artifacts, and deterministic calculations in the analysis helper.",
            "review_instruction": "Sol must independently recompute from the indexed raw files and may overturn this interpretation without rerunning the canary.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")

    provenance: list[list[str]] = []

    def add(scope: str, artifact: str, path: str, digest: str, status: str, note: str) -> None:
        provenance.append([scope, artifact, path, digest, status, note])

    add("task_exact", "task_document", host["task_path"], sha256(ROOT / host["task_path"]), "VERIFIED", "frozen task specification")
    add("host_record", "trusted_execution_record", str(args.host_record), sha256(args.host_record), "VERIFIED", "trusted wrapper record; not modified")
    add("parent_evidence", "accepted_predecessor_RESULTS", "git:8b189c1bd7dab761c014f1db98e1223f3d73120d:docs/validation/phase2_clean_baseline_flat_final_20260917/RESULTS.md", git_blob_sha("8b189c1bd7dab761c014f1db98e1223f3d73120d:docs/validation/phase2_clean_baseline_flat_final_20260917/RESULTS.md"), "VERIFIED", "accepted predecessor flat result referenced by task")
    add("canonical_source", "canonical_main_commit", "git:e30782ad916ef1614a877d7a3c122f62682c8f19", "", "RECORDED", "frozen source baseline")
    add("candidate", "candidate_commit", host["candidate_commit"], "", "RECORDED", "exact candidate presented to trusted host")
    for item in integrity:
        add("raw_host", item["path"], str(run_dir / item["path"]), item["actual_sha256"], "VERIFIED", f"host index size={item['actual_size']}; immutable raw artifact")
    add("source_runtime", "dds_base4000_preload.c", runtime["config_source"], runtime["config_source_sha256"], "VERIFIED", "tracked DDS support source used by run")
    add("source_scene", "scene_leg_lift_demo.xml", build["task_scene"], build["task_scene_sha256"], "VERIFIED", "frozen flat Go2 scene")
    for key, label in (("simulator_output", "unitree_mujoco"), ("controller_output", "real_trot_go2"), ("mujoco_library", "libmujoco.so"), ("mujoco_header", "mujoco.h"), ("unitree_sdk2_archive", "unitree_sdk2.a"), ("unitree_sdk2_config", "unitree_sdk2Config.cmake")):
        digest_key = {
            "simulator_output": "simulator_sha256",
            "controller_output": "controller_sha256",
            "mujoco_library": "mujoco_library_sha256",
            "mujoco_header": "mujoco_header_sha256",
            "unitree_sdk2_archive": "unitree_sdk2_archive_sha256",
            "unitree_sdk2_config": "unitree_sdk2_config_sha256",
        }[key]
        if build.get(key) and build.get(digest_key):
            add("binary" if key.endswith("output") else "toolchain", label, build[key], build[digest_key], "RECORDED_BY_HOST_BUILD" if key.endswith("output") else "VERIFIED", "host-recorded exact build/dependency identity")
    add("analyzer", "analyze_canonical_clean_baseline_repeat_r3.py", str(pathlib.Path(__file__).resolve()), sha256(pathlib.Path(__file__).resolve()), "VERIFIED", "deterministic offline analysis helper")
    args.provenance_output.parent.mkdir(parents=True, exist_ok=True)
    with args.provenance_output.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["scope", "artifact", "path", "sha256", "status", "note"])
        writer.writerows(provenance)
    print(json.dumps({"classification": classification, "raw_hashes_match": all_integrity, "indexed_files": len(integrity)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
