#!/usr/bin/env python3
"""Deterministic offline closeout analysis for canonical clean-baseline R1.

This tool reads the trusted host record, immutable raw artifacts, the frozen
task, and Git object metadata.  It never launches a process and never edits
the raw run directory.
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


CANONICAL_MAIN = "e30782ad916ef1614a877d7a3c122f62682c8f19"
TASK_COMMIT = "28f883496bd2d64d610ce0d023f2daf7ceea393d"
TASK_PATH = "docs/research/TASK_CANONICAL_CLEAN_BASELINE_REPEAT_R1_20260917.md"
PARENT_COMMIT = "8b189c1bd7dab761c014f1db98e1223f3d73120d"
PARENT_RESULTS = (
    "docs/validation/phase2_clean_baseline_flat_final_20260917/RESULTS.md"
)
PARENT_ANALYZER = (
    "example/cpp/tools/analysis/analyze_clean_baseline_flat_final.py"
)
RUN_REL = "example/cpp/experiments/_runs/canonical_clean_baseline_repeatability_20260917/R1"
NOMINAL_SPEED = 0.091 / 0.60
LEGS = ("FR", "FL", "RR", "RL")

FROZEN_COMMAND = [
    "bash",
    "example/cpp/scripts/run_trot_exact_source.sh",
    "90",
    "_runs/canonical_clean_baseline_repeatability_20260917/R1",
    "--controller-duration",
    "70",
    "--task",
    "stand-walk-lie",
    "--kernel",
    "raibert-trot",
    "--period",
    "0.60",
    "--duty",
    "0.75",
    "--step-length",
    "0.091",
    "--foot-lift",
    "0.020",
    "--kp",
    "63",
    "--kd",
    "2.8",
    "--raibert-velocity-gain",
    "0.05",
    "--raibert-max-adjustment",
    "0.010",
    "--world-feedback-max",
    "0.060",
    "--world-feedback-slew",
    "0.004",
    "--clean-baseline",
    "--tau-limit",
    "35",
    "--max-cycles",
    "64",
    "--headless",
    "--domain-id",
    "220",
]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha256(repo: pathlib.Path, spec: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "show", spec],
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def parse_kv(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


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


def ols(rows: list[dict[str, str]], time_key: str, value_key: str) -> dict[str, float | int]:
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


def number(value: str) -> float:
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
                item[key] = value if key == "tau_motor" else number(value)
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
        return max(abs(float(item[key])) if key in {"roll", "pitch"} else float(item[key]) for item in requested_health)

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
        "started_records_total": len(started),
        "started_cycle_indices": [int(item["cycle"]) for item in started],
        "requested_health_records": len(requested_health),
        "requested_started_records": len(requested_started),
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
            "simulator_dds_ready": "Unitree DDS bridge ready" in (path.parent / "simulator.log").read_text(errors="replace"),
            "natural_lowstate_settled": "Natural LowState settled" in text,
            "starting_diagonal_trot": "Starting diagonal trot" in text,
            "pre_stop_brake": "Trot pre-stop brake: reducing gait reference" in text,
            "return_to_stand": "Trot stopping; returning to stand" in text,
            "return_to_lie_down": "Task state: RETURN_TO_STAND -> LIE_DOWN" in text,
            "task_completed": "Task completed: stand-walk-lie" in text,
        },
        "text": text,
    }


def parse_data(path: pathlib.Path) -> dict[str, object]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    if not rows:
        raise ValueError("data.csv is empty")
    if any(None in row for row in rows):
        raise ValueError("data.csv contains a row with extra columns")

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
    selected_names = (
        "velocity_command_measured_mps",
        "body_velocity_x_mps",
        "world_velocity_x_mps",
        "contact_count",
        "wbc_full_eq_residual",
    )
    selected = {
        key: describe(finite(row, key) for row in requested)
        for key in selected_names
    }
    selected["imu_abs_roll_deg"] = describe(
        abs(math.degrees(finite(row, "imu_roll_rad"))) for row in requested
    )
    selected["imu_abs_pitch_deg"] = describe(
        abs(math.degrees(finite(row, "imu_pitch_rad"))) for row in requested
    )
    selected["tau_est_abs_nm"] = describe(tau_values)

    progress = ols(stage2, "state_tick_s", "world_base_x_m")
    progress["nominal_speed_mps"] = NOMINAL_SPEED
    progress["speed_ratio"] = progress["regression_speed_mps"] / NOMINAL_SPEED
    requested_progress = ols(requested, "state_tick_s", "world_base_x_m")
    requested_progress["nominal_speed_mps"] = NOMINAL_SPEED
    requested_progress["speed_ratio"] = requested_progress["regression_speed_mps"] / NOMINAL_SPEED

    return {
        "row_count": len(rows),
        "column_count": len(fields),
        "field_names_sha256": hashlib.sha256("\n".join(fields).encode()).hexdigest(),
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
    }, rows


def parse_truth(path: pathlib.Path, start_s: float, end_s: float) -> dict[str, object]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    interval = [row for row in rows if start_s <= float(row["time_s"]) <= end_s]
    speed = [finite(row, "base_qvel_world_x_mps") for row in interval]
    height = [finite(row, "base_pos_world_z_m") for row in interval]
    return {
        "rows_total": len(rows),
        "rows_in_controller_stage2_interval": len(interval),
        "speed_world_x_mps": describe(speed),
        "base_height_m": describe(height),
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


def section_empty(path: pathlib.Path, begin: str, end: str) -> bool:
    inside = False
    for line in path.read_text(errors="replace").splitlines():
        if line == begin:
            inside = True
        elif line == end:
            inside = False
        elif inside and line:
            return False
    return True


def source_identity(repo: pathlib.Path) -> dict[str, object]:
    surfaces = ["example/cpp/", "simulate/", "unitree_robots/"]
    results: dict[str, object] = {}
    all_unchanged = True
    for surface in surfaces:
        diff = subprocess.run(
            ["git", "-C", str(repo), "diff", "--quiet", CANONICAL_MAIN, TASK_COMMIT, "--", surface],
            check=False,
        )
        names = subprocess.run(
            ["git", "-C", str(repo), "diff", "--name-status", CANONICAL_MAIN, TASK_COMMIT, "--", surface],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        unchanged = diff.returncode == 0
        results[surface.rstrip("/")] = {"unchanged": unchanged, "diff_name_status": names}
        all_unchanged = all_unchanged and unchanged
    results["all_unchanged"] = all_unchanged
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=pathlib.Path, required=True)
    parser.add_argument("--host-record", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--provenance-output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    repo = pathlib.Path(__file__).resolve().parents[4]
    run_dir = args.run_dir
    host = json.loads(args.host_record.read_text())
    metadata = parse_kv(run_dir / "run_metadata.txt")
    manifest = json.loads((run_dir / "run_manifest.json").read_text())
    build = parse_kv(run_dir / "build_provenance.txt")
    runtime = parse_kv(run_dir / "dds_runtime/runtime_metadata.txt")
    pre_state = parse_kv(run_dir / "dds_runtime/pre_state.txt")
    post_state = parse_kv(run_dir / "dds_runtime/post_state.txt")
    data, data_rows = parse_data(run_dir / "data.csv")
    truth = parse_truth(
        run_dir / "contact_ground_truth.csv",
        data["stage2_state_tick_interval_s"][0],
        data["stage2_state_tick_interval_s"][1],
    )
    log = parse_controller_log(run_dir / "controller.log")
    contact_validation = parse_text_metrics(run_dir / "contact_ground_truth_analysis.txt")
    dynamics_validation = parse_text_metrics(run_dir / "contact_ground_truth_dynamics_analysis.txt")

    integrity: list[dict[str, object]] = []
    for item in host["evidence"]:
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

    source_hashes = {
        "dds_config_source": sha256(repo / "example/cpp/scripts/dds_base4000_preload.c"),
        "scene": sha256(repo / "unitree_robots/go2/scene_leg_lift_demo.xml"),
        "runner": sha256(repo / "example/cpp/scripts/run_trot.sh"),
        "exact_source_wrapper": sha256(repo / "example/cpp/scripts/run_trot_exact_source.sh"),
    }
    source_check = source_identity(repo)
    raw_ok = all(item["matches"] for item in integrity)
    host_ok = (
        host["candidate_commit"] == TASK_COMMIT
        and host["task_commit"] == TASK_COMMIT
        and host["launched"] is True
        and host["returncode"] == 0
        and host["error"] is None
        and host["timed_out"] is False
    )
    manifest_ok = (
        host["command"] == FROZEN_COMMAND
        and host["domain_id"] == 220
        and host["run_dir"] == RUN_REL
        and host["timeout_s"] == 600
        and host["environment"] == {
            "MUJOCO_ROOT": "/home/che/.mujoco/mujoco-3.3.6",
            "LD_LIBRARY_PATH": "/home/che/.mujoco/mujoco-3.3.6/lib",
        }
    )
    build_ok = (
        build.get("candidate_sha") == TASK_COMMIT
        and build.get("tracked_worktree_status") == "clean"
        and build.get("task_scene_sha256") == source_hashes["scene"]
        and build.get("canonical_runner_sha256") == source_hashes["runner"]
        and build.get("exact_source_wrapper_sha256") == source_hashes["exact_source_wrapper"]
    )
    metadata_ok = all(metadata.get(key) == "0" for key in (
        "controller_status", "safety_status", "quality_status", "completion_status",
        "dynamics_status", "ground_truth_status", "analysis_status",
    ))
    requested_flags = {
        key: value["requested_cycles_1_64"]
        for key, value in data["flag_counts"].items()
    }
    all_requested_started = log["requested_started_records"] == 64 and [
        item for item in log["started_cycle_indices"] if 1 <= item <= 64
    ] == list(range(1, 65))
    all_requested_health = log["requested_health_records"] == 64 and [
        item for item in log["health_cycle_indices"] if 1 <= item <= 64
    ] == list(range(1, 65))
    handoff = (
        log["lifecycle_markers"]["simulator_dds_ready"]
        and log["lifecycle_markers"]["natural_lowstate_settled"]
        and data["first_sample"]["has_state"] == "1"
        and data["first_sample"]["motion_stage"] == 0
        and data["first_sample"]["cycle_index"] == -1
    )
    target_fail = (
        log["rejection_log_counts"]["clean_target_infeasible"] > 0
        or requested_flags["kernel_footstep_plan_valid"] != {"1": data["requested_cycles_1_64_sample_count"]}
    )
    wbc_fail = (
        log["rejection_log_counts"]["strict_wbc_or_qp"] > 0
        or metadata.get("quality_status") != "0"
        or any(requested_flags[key] != {"1": data["requested_cycles_1_64_sample_count"]} for key in (
            "wbc_full_srbd_ok", "wbc_full_id_ok", "wbc_shadow_solver_ok",
            "wbc_shadow_mapping_ok", "wbc_shadow_constraint_feasible",
        ))
    )
    health = log["health_metrics_requested_cycles_1_64"]
    lifecycle_ok = (
        log["lifecycle_markers"]["pre_stop_brake"]
        and log["lifecycle_markers"]["return_to_stand"]
        and log["lifecycle_markers"]["return_to_lie_down"]
        and log["lifecycle_markers"]["task_completed"]
        and log["rejection_log_counts"]["hard_safety"] == 0
        and log["rejection_log_counts"]["emergency_stop"] == 0
        and metadata.get("safety_status") == "0"
    )
    gross_tracking_ok = (
        health["max_abs_roll_deg"] < 16.0
        and health["max_abs_pitch_deg"] < 16.0
        and health["max_joint_error_rad"] < 0.80
        and health["min_support_contact_fraction"] >= 0.35
        and metadata.get("quality_status") == "0"
    )
    criteria = {
        "candidate_and_host_record_valid": host_ok and raw_ok and manifest_ok and build_ok,
        "source_identity_unchanged_from_canonical_main": source_check["all_unchanged"],
        "valid_controller_handoff": handoff,
        "all_64_requested_gait_cycles_complete": all_requested_started and all_requested_health,
        "normal_return_to_stand_lifecycle_without_hard_or_emergency_stop": lifecycle_ok,
        "no_clean_target_feasibility_rejection": not target_fail,
        "no_strict_wbc_qp_rejection": not wbc_fail,
        "measured_forward_speed_in_0_11_to_0_19_mps": 0.11 <= data["locomotion_progress_all_stage2_nonnegative_cycles"]["regression_speed_mps"] <= 0.19,
        "no_gross_tracking_or_stability_failure": gross_tracking_ok,
        "contact_and_dynamics_validation_pass": contact_validation.get("validation") == "PASS" and dynamics_validation.get("validation") == "PASS",
        "run_status_fields_zero": metadata_ok,
    }

    if not criteria["candidate_and_host_record_valid"] or not criteria["source_identity_unchanged_from_canonical_main"] or not handoff:
        classification = "PROTOCOL_FAILURE"
        boundary = "execution"
    elif target_fail:
        classification = "CLEAN_BASELINE_TARGET_FEASIBILITY_FAIL"
        boundary = "scientific"
    elif wbc_fail:
        classification = "CLEAN_BASELINE_WBC_STRICT_FAIL"
        boundary = "scientific"
    elif not all(criteria[key] for key in (
        "all_64_requested_gait_cycles_complete",
        "normal_return_to_stand_lifecycle_without_hard_or_emergency_stop",
        "measured_forward_speed_in_0_11_to_0_19_mps",
        "no_gross_tracking_or_stability_failure",
    )):
        classification = "CLEAN_BASELINE_TRACKING_OR_STABILITY_FAIL"
        boundary = "scientific"
    else:
        classification = "CLEAN_BASELINE_FLAT_REPRODUCED"
        boundary = "scientific"

    started = datetime.fromisoformat(host["started_at"])
    finished = datetime.fromisoformat(host["finished_at"])
    elapsed_s = (finished - started).total_seconds()
    output = {
        "schema_version": 1,
        "suite_id": "canonical_clean_baseline_repeatability_20260917",
        "replicate": "R1 / 3",
        "classification": classification,
        "earliest_causal_boundary": boundary,
        "reason_code": classification,
        "task": {
            "task_path": TASK_PATH,
            "task_commit": TASK_COMMIT,
            "candidate_commit": TASK_COMMIT,
            "canonical_main": CANONICAL_MAIN,
            "accepted_predecessor_commit": PARENT_COMMIT,
            "accepted_predecessor_results": PARENT_RESULTS,
            "frozen_command": FROZEN_COMMAND,
            "nominal_speed_mps": NOMINAL_SPEED,
        },
        "host": {
            "launched": host["launched"],
            "returncode": host["returncode"],
            "error": host["error"],
            "timed_out": host["timed_out"],
            "timeout_s": host["timeout_s"],
            "started_at": host["started_at"],
            "finished_at": host["finished_at"],
            "elapsed_s": elapsed_s,
            "manifest_sha256": host["manifest_sha256"],
            "stdout_sha256": host["stdout_sha256"],
            "stderr_sha256": host["stderr_sha256"],
            "environment": host["environment"],
        },
        "facts": {
            "source_identity": source_check,
            "manifest_matches_frozen_task": manifest_ok,
            "build_provenance": build,
            "source_hashes_recomputed": source_hashes,
            "runtime_metadata": runtime,
            "dds_pre_state": {
                "domain_id": pre_state.get("domain_id"),
                "interface": pre_state.get("interface"),
                "active_go2_processes_empty": section_empty(run_dir / "dds_runtime/pre_state.txt", "active_go2_processes_begin", "active_go2_processes_end"),
                "known_shm_empty": section_empty(run_dir / "dds_runtime/pre_state.txt", "known_shm_begin", "known_shm_end"),
                "expected_port_range": [59000, 59073],
            },
            "dds_post_state": {
                "domain_id": post_state.get("domain_id"),
                "interface": post_state.get("interface"),
                "active_go2_processes_empty": section_empty(run_dir / "dds_runtime/post_state.txt", "active_go2_processes_begin", "active_go2_processes_end"),
                "known_shm_empty": section_empty(run_dir / "dds_runtime/post_state.txt", "known_shm_begin", "known_shm_end"),
            },
            "controller_metadata": metadata,
            "run_manifest": manifest,
            "contact_ground_truth_validation": contact_validation,
            "contact_dynamics_validation": dynamics_validation,
        },
        "derived_metrics": {
            "raw_integrity": {
                "indexed_files": len(integrity),
                "all_hashes_and_sizes_match": raw_ok,
                "files": integrity,
            },
            "handoff": {
                "simulator_dds_ready_marker": log["lifecycle_markers"]["simulator_dds_ready"],
                "controller_lowstate_settled_marker": log["lifecycle_markers"]["natural_lowstate_settled"],
                "first_valid_controller_state_control_sample": data["first_sample"],
                "first_locomotion_sample": next(item for item in data["stage_transitions"] if item["motion_stage"] == 2),
                "all_data_rows_has_state_1": data["flag_counts"]["has_state"]["all_rows"] == {"1": data["row_count"]},
                "scientific_attempt_consumed": handoff,
            },
            "lifecycle": {
                "requested_gait_cycles": 64,
                "completed_requested_gait_cycles": log["requested_health_records"],
                "started_requested_gait_cycles": log["requested_started_records"],
                "health_cycle_indices": log["health_cycle_indices"],
                "started_cycle_indices": log["started_cycle_indices"],
                "stage_counts": data["stage_counts"],
                "markers": log["lifecycle_markers"],
            },
            "speed": {
                "nominal_commanded_speed_mps": NOMINAL_SPEED,
                "csv_progress_metric": data["locomotion_progress_all_stage2_nonnegative_cycles"],
                "csv_requested_cycles_1_64_progress_metric": data["locomotion_progress_requested_cycles_1_64"],
                "csv_measured_velocity_stats_requested_cycles_1_64": data["selected_requested_cycle_metrics"]["velocity_command_measured_mps"],
                "ground_truth_interval": truth,
            },
            "controller_health": log["health_metrics_requested_cycles_1_64"],
            "controller_cycle_start_speeds": log["cycle_start_speed_stats_requested_1_64"],
            "controller_flag_counts_requested_cycles_1_64": requested_flags,
            "data_csv": data,
            "rejection_and_safety": log["rejection_log_counts"],
            "contact_ground_truth_analysis": contact_validation,
            "contact_dynamics_analysis": dynamics_validation,
            "formulas": {
                "nominal_speed": "0.091 / 0.60",
                "csv_progress_window": "motion_stage == 2 and cycle_index >= 0",
                "csv_requested_cycle_window": "motion_stage == 2 and 1 <= cycle_index <= 64",
                "progress_speed": "ordinary least-squares slope of world_base_x_m versus state_tick_s, sorted by state_tick_s",
                "speed_ratio": "progress_speed / nominal_speed",
                "health_metrics": "max/min of controller.log Trot cycle N health fields for N in 1..64",
                "flag_rejections": "requested-cycle flag counters; success flags must be exactly {1: sample_count}",
                "gross_tracking_guard": "accepted predecessor offline guard: roll/pitch < 16 deg, joint error < 0.80 rad, support fraction >= 0.35, quality_status=0",
            },
        },
        "classification_gate": criteria,
        "luna_interpretation": {
            "proposed_classification": classification,
            "interpretation_is_authoritative": False,
            "basis": "The proposed classification is derived from immutable host/raw evidence and the formulas recorded above.",
            "review_instruction": "Sol may independently recompute analysis.json from the indexed raw files and overturn this proposal without rerunning R1.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")

    provenance: list[list[str]] = []

    def add(scope: str, artifact: str, path: str, digest: str, status: str, note: str) -> None:
        provenance.append([scope, artifact, path, digest, status, note])

    add("task_exact", "task_document", TASK_PATH, sha256(repo / TASK_PATH), "VERIFIED", "frozen task specification")
    add("host_record", "trusted_execution_record", str(args.host_record), sha256(args.host_record), "VERIFIED", "trusted host record; not modified")
    add("parent_evidence", "accepted_predecessor_RESULTS", f"git:{PARENT_COMMIT}:{PARENT_RESULTS}", git_blob_sha256(repo, f"{PARENT_COMMIT}:{PARENT_RESULTS}"), "VERIFIED", "exact accepted predecessor closeout")
    add("parent_analyzer", "accepted_stage2_OLS_analyzer", f"git:{PARENT_COMMIT}:{PARENT_ANALYZER}", git_blob_sha256(repo, f"{PARENT_COMMIT}:{PARENT_ANALYZER}"), "VERIFIED", "method reference for deterministic stage-2 OLS")
    add("candidate", "candidate_commit", TASK_COMMIT, "", "RECORDED", "exact candidate presented to trusted host")
    add("source_identity", "example/cpp", f"git:{CANONICAL_MAIN}..{TASK_COMMIT}:example/cpp", "", "VERIFIED" if source_check["example/cpp"]["unchanged"] else "MISMATCH", "byte-for-byte source-surface comparison")
    add("source_identity", "simulate", f"git:{CANONICAL_MAIN}..{TASK_COMMIT}:simulate", "", "VERIFIED" if source_check["simulate"]["unchanged"] else "MISMATCH", "byte-for-byte source-surface comparison")
    add("source_identity", "unitree_robots", f"git:{CANONICAL_MAIN}..{TASK_COMMIT}:unitree_robots", "", "VERIFIED" if source_check["unitree_robots"]["unchanged"] else "MISMATCH", "byte-for-byte source-surface comparison")
    for item in integrity:
        add("raw_host", item["path"], str(run_dir / item["path"]), item["actual_sha256"], "VERIFIED" if item["matches"] else "MISMATCH", f"host index size={item['actual_size']}; immutable raw artifact")
    add("source_runtime", "dds_base4000_preload.c", "example/cpp/scripts/dds_base4000_preload.c", source_hashes["dds_config_source"], "VERIFIED" if source_hashes["dds_config_source"] == runtime.get("config_source_sha256") else "MISMATCH", "DDS support source used by host run")
    add("source_scene", "scene_leg_lift_demo.xml", "unitree_robots/go2/scene_leg_lift_demo.xml", source_hashes["scene"], "VERIFIED" if source_hashes["scene"] == build.get("task_scene_sha256") else "MISMATCH", "frozen flat Go2 scene")
    for key in ("runner", "exact_source_wrapper"):
        add("launcher", key, "example/cpp/scripts/run_trot.sh" if key == "runner" else "example/cpp/scripts/run_trot_exact_source.sh", source_hashes[key], "VERIFIED", "host-recorded launcher identity")
    for key in ("simulator_sha256", "controller_sha256"):
        add("binary", key, build.get("simulator_output" if key == "simulator_sha256" else "controller_output", ""), build.get(key, ""), "RECORDED_BY_HOST_BUILD", "exact-source host build output")
    add("analyzer", "analyze_clean_baseline_repeat_r1.py", str(pathlib.Path(__file__)), sha256(pathlib.Path(__file__)), "VERIFIED", "deterministic offline analysis helper")
    args.provenance_output.parent.mkdir(parents=True, exist_ok=True)
    with args.provenance_output.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["scope", "artifact", "path", "sha256", "status", "note"])
        writer.writerows(provenance)
    print(json.dumps({"classification": classification, "raw_hashes_match": raw_ok, "source_identity_unchanged": source_check["all_unchanged"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
