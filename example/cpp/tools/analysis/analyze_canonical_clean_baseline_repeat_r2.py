#!/usr/bin/env python3
"""Deterministic offline closeout analysis for canonical clean-baseline R2.

This tool reads the trusted host record, the frozen task, and immutable raw run
artifacts.  It never launches a process and never writes inside the raw run.
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


TASK_PATH = "docs/research/TASK_CANONICAL_CLEAN_BASELINE_REPEAT_R2_20260917.md"
TASK_COMMIT = "4db0ef4d852be844814fd96d63198cbddaa5412b"
CANONICAL_MAIN = "e30782ad916ef1614a877d7a3c122f62682c8f19"
PARENT_RESULT_COMMIT = "8b189c1bd7dab761c014f1db98e1223f3d73120d"
PARENT_RESULT_PATH = (
    "docs/validation/phase2_clean_baseline_flat_final_20260917/RESULTS.md"
)
NOMINAL_SPEED = 0.091 / 0.60
REQUESTED_CYCLES = range(1, 65)
LEGS = ("FR", "FL", "RR", "RL")
AXES = ("x", "y", "z")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha(root: pathlib.Path, spec: str) -> str:
    content = subprocess.run(
        ["git", "-C", str(root), "show", spec],
        check=True,
        capture_output=True,
    ).stdout
    return hashlib.sha256(content).hexdigest()


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


def regression(
    rows: list[dict[str, str]], time_key: str, value_key: str
) -> dict[str, float | int]:
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
        "nominal_speed_mps": NOMINAL_SPEED,
        "speed_ratio": slope / NOMINAL_SPEED,
    }


def parse_kv_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


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


def number_with_units(value: str) -> float:
    match = re.search(
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value
    )
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
        return max(abs(float(item[key])) for item in requested_health)

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
    stop_cycles = [item["cycle"] for item in started if item["cycle"] > 64]

    return {
        "health_records_total": len(health),
        "health_cycle_indices": [int(item["cycle"]) for item in health],
        "requested_health_records": len(requested_health),
        "requested_health_cycle_indices": [int(item["cycle"]) for item in requested_health],
        "requested_started_records": len(requested_started),
        "requested_started_cycle_indices": [int(item["cycle"]) for item in requested_started],
        "stop_transition_cycle": max(stop_cycles) if stop_cycles else None,
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
            "model_loaded": "WBC-FULL: 18-DoF MJCF model loaded" in text,
            "simulator_dds_ready": False,
            "natural_lowstate_settled": "Natural LowState settled" in text,
            "starting_diagonal_trot": "Starting diagonal trot" in text,
            "pre_stop_brake": "Trot pre-stop brake: reducing gait reference" in text,
            "return_to_stand": "Trot stopping; returning to stand" in text,
            "return_to_lie_down": "Task state: RETURN_TO_STAND -> LIE_DOWN" in text,
            "task_completed": "Task completed: stand-walk-lie" in text,
        },
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
    tau_fields = [field for field in fields if field.endswith("_tau_est")]
    selected_metrics["tau_est_abs_nm"] = describe(
        abs(float(row[field])) for row in requested for field in tau_fields
    )
    nominal = NOMINAL_SPEED
    progress = regression(stage2, "state_tick_s", "world_base_x_m")
    requested_progress = regression(requested, "state_tick_s", "world_base_x_m")
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
            "stage2_state_tick_interval_s": [
                finite(stage2[0], "state_tick_s"),
                finite(stage2[-1], "state_tick_s"),
            ],
            "requested_cycles_1_64_state_tick_interval_s": [
                finite(requested[0], "state_tick_s"),
                finite(requested[-1], "state_tick_s"),
            ],
            "stage_transitions": transitions,
            "flag_counts": flag_counts,
            "selected_requested_cycle_metrics": selected_metrics,
            "locomotion_progress_all_stage2_nonnegative_cycles": progress,
            "locomotion_progress_requested_cycles_1_64": requested_progress,
            "nominal_speed_mps": nominal,
        },
        rows,
    )


def contact_and_dynamics_metrics(
    path: pathlib.Path, start_s: float, end_s: float
) -> dict[str, object]:
    rows = 0
    times: list[float] = []
    steps: list[int] = []
    dts: list[float] = []
    contact_grf_z: list[float] = []
    negative_contact_grf_z = 0
    max_contact_grf_norm = 0.0
    truth_speed: list[float] = []
    truth_height: list[float] = []
    truth_roll: list[float] = []
    truth_pitch: list[float] = []
    masses: list[float] = []
    gravity_samples: list[dict[str, float]] = []
    residual_norms: list[float] = []
    residual_components: list[tuple[float, dict[str, float]]] = []
    previous_velocity: dict[str, float] | None = None
    previous_gravity: dict[str, float] | None = None
    previous_total_grf: dict[str, float] | None = None
    previous_mass: float | None = None
    previous_time: float | None = None
    errors: list[str] = []

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("contact CSV has no header")
        for row_number, row in enumerate(reader, start=2):
            try:
                time_s = float(row["time_s"])
                step_index = int(row["step_index"])
                mass = float(row["total_mass_kg"])
                velocity = {
                    axis: float(row[f"subtree_linvel_world_{axis}_mps"])
                    for axis in AXES
                }
                gravity = {
                    axis: float(row[f"gravity_world_{axis}_mps2"])
                    for axis in AXES
                }
                total_grf = {
                    axis: float(row[f"total_contact_grf_world_{axis}_N"])
                    for axis in AXES
                }
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"row {row_number}: invalid dynamics sample: {exc}")
                continue
            values = [time_s, mass, *velocity.values(), *gravity.values(), *total_grf.values()]
            if not all(math.isfinite(value) for value in values):
                errors.append(f"row {row_number}: non-finite dynamics sample")
                continue
            if mass <= 0.0:
                errors.append(f"row {row_number}: non-positive total mass")
            if times and time_s <= times[-1]:
                errors.append(f"row {row_number}: time is not strictly increasing")
            if steps and step_index != steps[-1] + 1:
                errors.append(f"row {row_number}: step index jump {steps[-1]}->{step_index}")
            if times:
                dts.append(time_s - times[-1])
            rows += 1
            times.append(time_s)
            steps.append(step_index)
            masses.append(mass)
            gravity_samples.append(gravity)

            for leg in LEGS:
                grf = {
                    axis: float(row[f"{leg}_contact_grf_world_{axis}_N"])
                    for axis in AXES
                }
                if not all(math.isfinite(value) for value in grf.values()):
                    errors.append(f"row {row_number} {leg}: non-finite contact GRF")
                max_contact_grf_norm = max(
                    max_contact_grf_norm,
                    math.sqrt(sum(grf[axis] ** 2 for axis in AXES)),
                )
                if float(row[f"{leg}_touch_N"]) > 5.0:
                    contact_grf_z.append(grf["z"])
                    if grf["z"] < -1e-6:
                        negative_contact_grf_z += 1

            if start_s <= time_s <= end_s:
                w, x, y, z = (
                    float(row[key])
                    for key in ("base_quat_w", "base_quat_x", "base_quat_y", "base_quat_z")
                )
                sin_roll = 2.0 * (w * x + y * z)
                cos_roll = 1.0 - 2.0 * (x * x + y * y)
                sin_pitch = max(-1.0, min(1.0, 2.0 * (w * y - z * x)))
                truth_speed.append(float(row["base_qvel_world_x_mps"]))
                truth_height.append(float(row["base_pos_world_z_m"]))
                truth_roll.append(abs(math.degrees(math.atan2(sin_roll, cos_roll))))
                truth_pitch.append(abs(math.degrees(math.asin(sin_pitch))))

            if (
                previous_velocity is not None
                and previous_gravity is not None
                and previous_total_grf is not None
                and previous_mass is not None
                and previous_time is not None
            ):
                dt = time_s - previous_time
                if dt <= 0.0:
                    errors.append(f"row {row_number}: non-positive forward-difference interval")
                acceleration = {
                    axis: (velocity[axis] - previous_velocity[axis]) / dt
                    for axis in AXES
                }
                expected = {
                    axis: previous_mass
                    * (acceleration[axis] - previous_gravity[axis])
                    for axis in AXES
                }
                residual = {
                    axis: previous_total_grf[axis] - expected[axis]
                    for axis in AXES
                }
                norm = math.sqrt(sum(residual[axis] ** 2 for axis in AXES))
                residual_norms.append(norm)
                residual_components.append((previous_time, residual))
            previous_velocity = velocity
            previous_gravity = gravity
            previous_total_grf = total_grf
            previous_mass = mass
            previous_time = time_s
            if len(errors) > 20:
                break

    if errors:
        raise ValueError("contact/dynamics validation errors: " + "; ".join(errors[:20]))
    if len(times) < 2 or not truth_speed:
        raise ValueError("insufficient contact/dynamics samples")
    sorted_norms = sorted(residual_norms)
    p95_index = int(0.95 * (len(sorted_norms) - 1))
    max_index = max(range(len(residual_norms)), key=residual_norms.__getitem__)
    max_time, max_components = residual_components[max_index]
    first_gravity = gravity_samples[0]
    gravity_drift = max(
        abs(sample[axis] - first_gravity[axis])
        for sample in gravity_samples
        for axis in AXES
    )
    p95_residual = sorted_norms[p95_index]
    dynamics = {
        "rows": rows,
        "balance_samples": len(residual_norms),
        "time_span_s": times[-1] - times[0],
        "median_dt_s": statistics.median(dts),
        "total_mass_min_kg": min(masses),
        "total_mass_max_kg": max(masses),
        "gravity_world_mps2": [first_gravity[axis] for axis in AXES],
        "gravity_drift_mps2": gravity_drift,
        "p95_force_balance_residual_N": p95_residual,
        "rms_force_balance_residual_N": math.sqrt(
            sum(value ** 2 for value in residual_norms) / len(residual_norms)
        ),
        "max_force_balance_component_residual_N": max(
            abs(value) for _, residual in residual_components for value in residual.values()
        ),
        "max_force_balance_residual_norm_N": residual_norms[max_index],
        "max_residual_time_s": max_time,
        "max_residual_components_N": [max_components[axis] for axis in AXES],
        "force_balance_tolerance_N": 10.0,
        "validation": "PASS" if p95_residual <= 10.0 else "FAIL",
    }
    contact = {
        "rows": rows,
        "time_span_s": times[-1] - times[0],
        "median_dt_s": statistics.median(dts),
        "contact_samples": len(contact_grf_z),
        "min_contact_grf_z_N": min(contact_grf_z),
        "max_contact_grf_z_N": max(contact_grf_z),
        "max_contact_grf_norm_N": max_contact_grf_norm,
        "negative_contact_grf_z_samples": negative_contact_grf_z,
        "validation": "PASS" if negative_contact_grf_z == 0 else "FAIL",
    }
    truth = {
        "rows_in_controller_stage2_interval": len(truth_speed),
        "speed_world_x_mps": describe(truth_speed),
        "base_height_m": describe(truth_height),
        "abs_roll_deg": describe(truth_roll),
        "abs_pitch_deg": describe(truth_pitch),
    }
    return {
        "contact_validation_recomputed": contact,
        "dynamics_validation_recomputed": dynamics,
        "ground_truth_interval": truth,
    }


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


def extract_manifest(task_text: str) -> dict[str, object]:
    match = re.search(
        r"<!--\s*ATLAS_HOST_EXPERIMENT\s*(\{.*?\})\s*ATLAS_HOST_EXPERIMENT\s*-->",
        task_text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError("task has no frozen ATLAS_HOST_EXPERIMENT manifest")
    return json.loads(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=pathlib.Path, required=True)
    parser.add_argument("--host-record", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--provenance-output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parents[4]
    run_dir = args.run_dir
    host_record = json.loads(args.host_record.read_text())
    task_text = (root / TASK_PATH).read_text()
    task_manifest = extract_manifest(task_text)
    if host_record["task_commit"] != TASK_COMMIT:
        raise ValueError("host record task commit mismatch")
    if host_record["candidate_commit"] != TASK_COMMIT:
        raise ValueError("host record candidate commit mismatch")
    if host_record["command"] != task_manifest["command"]:
        raise ValueError("host command differs from frozen task manifest")
    normalized_manifest = json.dumps(
        task_manifest, sort_keys=True, separators=(",", ":")
    ) + "\n"
    manifest_sha = hashlib.sha256(normalized_manifest.encode()).hexdigest()
    if host_record["manifest_sha256"] != manifest_sha:
        raise ValueError("host manifest hash mismatch")

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
    all_integrity = all(item["matches"] for item in integrity)

    metadata = parse_kv_file(run_dir / "run_metadata.txt")
    build = parse_kv_file(run_dir / "build_provenance.txt")
    manifest = json.loads((run_dir / "run_manifest.json").read_text())
    candidate_parent = subprocess.run(
        ["git", "-C", str(root), "show", "-s", "--format=%P", TASK_COMMIT],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    canonical_tree = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{CANONICAL_MAIN}^{{tree}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    candidate_tree = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{TASK_COMMIT}^{{tree}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    runtime_surfaces_match = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "diff",
            "--quiet",
            CANONICAL_MAIN,
            TASK_COMMIT,
            "--",
            "example/cpp",
            "simulate",
            "unitree_robots",
        ],
        check=False,
    ).returncode == 0
    runtime = parse_kv_file(run_dir / "dds_runtime/runtime_metadata.txt")
    pre_state = parse_kv_file(run_dir / "dds_runtime/pre_state.txt")
    post_state = parse_kv_file(run_dir / "dds_runtime/post_state.txt")
    pre_state_path = run_dir / "dds_runtime/pre_state.txt"
    post_state_path = run_dir / "dds_runtime/post_state.txt"
    simulator_text = (run_dir / "simulator.log").read_text(errors="replace")
    controller = parse_controller_log(run_dir / "controller.log")
    data, data_rows = csv_metrics(run_dir / "data.csv")
    contact = contact_and_dynamics_metrics(
        run_dir / "contact_ground_truth.csv",
        data["stage2_state_tick_interval_s"][0],
        data["stage2_state_tick_interval_s"][1],
    )
    contact_reported = parse_text_metrics(run_dir / "contact_ground_truth_analysis.txt")
    dynamics_reported = parse_text_metrics(
        run_dir / "contact_ground_truth_dynamics_analysis.txt"
    )
    requested_flags = {
        key: value["requested_cycles_1_64"]
        for key, value in data["flag_counts"].items()
    }
    elapsed_s = (
        datetime.fromisoformat(host_record["finished_at"])
        - datetime.fromisoformat(host_record["started_at"])
    ).total_seconds()
    statuses_zero = all(
        metadata.get(key) == "0"
        for key in (
            "controller_status",
            "safety_status",
            "quality_status",
            "analysis_status",
            "ground_truth_status",
            "dynamics_status",
            "completion_status",
            "terrain_analysis_status",
        )
    )
    requested_sample_count = data["requested_cycles_1_64_sample_count"]
    all_one = lambda key: requested_flags[key] == {"1": requested_sample_count}
    health = controller["health_metrics_requested_cycles_1_64"]
    criteria = {
        "valid_controller_handoff": (
            host_record["launched"] is True
            and host_record["returncode"] == 0
            and host_record["error"] is None
            and host_record["timed_out"] is False
            and "Unitree DDS bridge ready" in simulator_text
            and controller["lifecycle_markers"]["model_loaded"]
            and controller["lifecycle_markers"]["natural_lowstate_settled"]
            and data["first_sample"]["has_state"] == "1"
        ),
        "all_64_requested_gait_cycles_complete": (
            controller["requested_health_records"] == 64
            and controller["requested_started_records"] == 64
            and controller["requested_health_cycle_indices"] == list(REQUESTED_CYCLES)
            and controller["requested_started_cycle_indices"] == list(REQUESTED_CYCLES)
            and health["min_support_contact_fraction"] > 0.0
        ),
        "normal_return_to_stand_without_hard_stop": (
            controller["lifecycle_markers"]["return_to_stand"]
            and controller["lifecycle_markers"]["return_to_lie_down"]
            and controller["lifecycle_markers"]["task_completed"]
            and statuses_zero
            and controller["rejection_log_counts"]["hard_safety"] == 0
            and controller["rejection_log_counts"]["emergency_stop"] == 0
        ),
        "no_clean_target_feasibility_rejection": (
            controller["rejection_log_counts"]["clean_target_infeasible"] == 0
            and all_one("kernel_footstep_plan_valid")
        ),
        "no_strict_wbc_qp_rejection": (
            all_one("wbc_full_srbd_ok")
            and all_one("wbc_full_id_ok")
            and all_one("wbc_shadow_solver_ok")
            and all_one("wbc_shadow_mapping_ok")
            and all_one("wbc_shadow_constraint_feasible")
            and controller["rejection_log_counts"]["strict_wbc_or_qp"] == 0
            and metadata.get("quality_status") == "0"
        ),
        "measured_forward_speed_in_0_11_to_0_19_mps": (
            0.11
            <= data["locomotion_progress_all_stage2_nonnegative_cycles"]["regression_speed_mps"]
            <= 0.19
        ),
        "no_gross_tracking_or_stability_failure": (
            health["max_abs_roll_deg"] < 16.0
            and health["max_abs_pitch_deg"] < 16.0
            and health["max_joint_error_rad"] < 0.80
            and health["min_support_contact_fraction"] >= 0.35
            and metadata.get("quality_status") == "0"
        ),
    }
    protocol_ok = all_integrity and criteria["valid_controller_handoff"] and statuses_zero
    if all(criteria.values()):
        proposed_classification = "CLEAN_BASELINE_FLAT_REPRODUCED"
        boundary = "scientific"
    elif not protocol_ok:
        proposed_classification = "PROTOCOL_FAILURE"
        boundary = "execution"
    elif not criteria["no_clean_target_feasibility_rejection"]:
        proposed_classification = "CLEAN_BASELINE_TARGET_FEASIBILITY_FAIL"
        boundary = "scientific"
    elif not criteria["no_strict_wbc_qp_rejection"]:
        proposed_classification = "CLEAN_BASELINE_WBC_STRICT_FAIL"
        boundary = "scientific"
    else:
        proposed_classification = "CLEAN_BASELINE_TRACKING_OR_STABILITY_FAIL"
        boundary = "scientific"

    output = {
        "schema_version": 1,
        "experiment": "canonical_clean_baseline_repeatability_20260917_R2",
        "classification": proposed_classification,
        "earliest_causal_boundary": boundary,
        "reason_code": proposed_classification,
        "task": {
            "task_path": TASK_PATH,
            "task_commit": TASK_COMMIT,
            "candidate_commit": host_record["candidate_commit"],
            "canonical_main": CANONICAL_MAIN,
            "accepted_predecessor_flat_result": "8b189c1bd7dab761c014f1db98e1223f3d73120d",
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
                "scene_file": build.get("task_scene"),
                "mujoco_root": build.get("mujoco_root"),
                "mujoco_root_realpath": build.get("mujoco_root_realpath"),
                "mujoco_header_sha256": build.get("mujoco_header_sha256"),
                "mujoco_library_sha256": build.get("mujoco_library_sha256"),
                "unitree_sdk2_config_sha256": build.get("unitree_sdk2_config_sha256"),
                "unitree_sdk2_archive_sha256": build.get("unitree_sdk2_archive_sha256"),
            },
            "source_freeze": {
                "canonical_main": CANONICAL_MAIN,
                "canonical_main_tree": canonical_tree,
                "candidate_commit": TASK_COMMIT,
                "candidate_parent": candidate_parent,
                "candidate_tree": candidate_tree,
                "candidate_runtime_surfaces_match_canonical": runtime_surfaces_match,
                "host_tracked_worktree_status": build.get("tracked_worktree_status"),
            },
            "runtime_metadata": runtime,
            "dds_pre_state": {
                "domain_id": pre_state.get("domain_id"),
                "interface": pre_state.get("interface"),
                "expected_port_range": [59000, 59073],
                "active_go2_processes_empty": section_is_empty(
                    pre_state_path, "active_go2_processes_begin", "active_go2_processes_end"
                ),
                "known_shm_empty": section_is_empty(
                    pre_state_path, "known_shm_begin", "known_shm_end"
                ),
            },
            "dds_post_state": {
                "domain_id": post_state.get("domain_id"),
                "interface": post_state.get("interface"),
                "active_go2_processes_empty": section_is_empty(
                    post_state_path, "active_go2_processes_begin", "active_go2_processes_end"
                ),
                "known_shm_empty": section_is_empty(
                    post_state_path, "known_shm_begin", "known_shm_end"
                ),
            },
            "controller_metadata": metadata,
            "run_manifest": manifest,
            "contact_ground_truth_validation_reported": contact_reported,
            "contact_dynamics_validation_reported": dynamics_reported,
            "simulator_lifecycle": {
                "dds_ready_marker": "Unitree DDS bridge ready" in simulator_text,
                "shutdown_marker": "SIGNAL: shutdown requested" in simulator_text,
            },
        },
        "derived_metrics": {
            "handoff": {
                "simulator_dds_ready_marker": "Unitree DDS bridge ready" in simulator_text,
                "controller_lowstate_settled_marker": controller["lifecycle_markers"]["natural_lowstate_settled"],
                "first_valid_controller_state_control_sample": data["first_sample"],
                "first_locomotion_sample": next(
                    item for item in data["stage_transitions"] if item["motion_stage"] == 2
                ),
                "all_data_rows_has_state_1": data["flag_counts"]["has_state"]["all_rows"]
                == {"1": data["row_count"]},
                "scientific_attempt_consumed": True,
            },
            "lifecycle": {
                "requested_gait_cycles": 64,
                "completed_requested_gait_cycles": controller["requested_health_records"],
                "pre_motion_health_cycle": 0,
                "return_transition_cycle": controller["stop_transition_cycle"],
                "task_completed": controller["lifecycle_markers"]["task_completed"],
                "stage_counts": data["stage_counts"],
            },
            "csv": data,
            "speed": {
                "nominal_commanded_speed_mps": NOMINAL_SPEED,
                "csv_progress_metric": data["locomotion_progress_all_stage2_nonnegative_cycles"],
                "csv_requested_cycles_1_64_progress_metric": data["locomotion_progress_requested_cycles_1_64"],
                "csv_measured_velocity_stats_requested_cycles_1_64": data["selected_requested_cycle_metrics"]["velocity_command_measured_mps"],
                "ground_truth_interval": contact["ground_truth_interval"],
            },
            "controller_health": health,
            "controller_cycle_start_speeds": controller["cycle_start_speed_stats_requested_1_64"],
            "controller_flag_counts_requested_cycles_1_64": requested_flags,
            "rejection_and_safety": {
                "controller_log": controller["rejection_log_counts"],
                "data_flag_counts": requested_flags,
                "max_tau_over_limit_samples": health["max_tau_over_limit_samples"],
                "max_tau_over_limit_consecutive": health["max_tau_over_limit_consecutive"],
            },
            "contact_and_dynamics": contact,
            "formulas": {
                "nominal_speed": "0.091 / 0.60",
                "csv_progress_window": "motion_stage == 2 and cycle_index >= 0",
                "csv_requested_cycle_window": "motion_stage == 2 and 1 <= cycle_index <= 64",
                "progress_speed": "ordinary least-squares slope of world_base_x_m versus state_tick_s",
                "speed_ratio": "progress_speed / nominal_speed",
                "health_metrics": "max absolute or min of controller.log Trot cycle N health fields for N in 1..64",
                "flag_counts": "raw value counts in all, stage-2, and requested-cycle CSV windows",
                "contact_validation": "recompute touch-threshold contact GRF checks over every contact CSV row",
                "dynamics_validation": "forward-difference subtree velocity and compare total contact GRF to m*(a-g), p95 discrete index",
            },
        },
        "classification_gate": criteria,
        "luna_interpretation": {
            "proposed_classification": proposed_classification,
            "interpretation_is_authoritative": False,
            "basis": "All frozen gates are evaluated from the immutable host record and raw evidence using this deterministic offline analyzer.",
            "review_instruction": "Sol may independently recompute from the indexed raw files and overturn this interpretation without rerunning the canary.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")

    provenance_rows: list[list[str]] = []

    def add(scope: str, artifact: str, path: str, digest: str, status: str, note: str) -> None:
        provenance_rows.append([scope, artifact, path, digest, status, note])

    add("task_exact", "task_document", TASK_PATH, sha256(root / TASK_PATH), "VERIFIED", "frozen task specification")
    add("host_record", "trusted_execution_record", str(args.host_record), sha256(args.host_record), "VERIFIED", "trusted wrapper record; not modified")
    add("parent_evidence", "accepted_flat_baseline_RESULTS", f"git:{PARENT_RESULT_COMMIT}:{PARENT_RESULT_PATH}", git_blob_sha(root, f"{PARENT_RESULT_COMMIT}:{PARENT_RESULT_PATH}"), "VERIFIED", "accepted predecessor closeout")
    add("canonical_source", "canonical_main_commit", CANONICAL_MAIN, "", "RECORDED", "protected canonical baseline source identity")
    add("candidate", "candidate_commit", TASK_COMMIT, "", "RECORDED", "exact candidate presented to trusted host")
    for item in integrity:
        add("raw_host", item["path"], str(run_dir / item["path"]), item["actual_sha256"], "VERIFIED" if item["matches"] else "MISMATCH", f"host index size={item['actual_size']}; immutable raw artifact")
    add("source_runtime", "dds_base4000_preload.c", runtime["config_source"], runtime["config_source_sha256"], "VERIFIED", "tracked DDS support source used by run")
    add("source_scene", "scene_leg_lift_demo.xml", build["task_scene"], build["task_scene_sha256"], "VERIFIED", "frozen flat Go2 scene")
    add("binary", "unitree_mujoco", build["simulator_output"], build["simulator_sha256"], "RECORDED_BY_HOST_BUILD", "exact-source simulator output")
    add("binary", "real_trot_go2", build["controller_output"], build["controller_sha256"], "RECORDED_BY_HOST_BUILD", "exact-source controller output")
    add("toolchain", "libmujoco.so", build["mujoco_library"], build["mujoco_library_sha256"], "VERIFIED", "permitted read-only MuJoCo dependency")
    add("toolchain", "mujoco.h", build["mujoco_header"], build["mujoco_header_sha256"], "VERIFIED", "permitted read-only MuJoCo dependency")
    add("analyzer", pathlib.Path(__file__).name, str(pathlib.Path(__file__)), sha256(pathlib.Path(__file__)), "VERIFIED", "deterministic offline analysis code")
    add("analyzer", "analyze_contact_ground_truth.py", str(root / "example/cpp/tools/analysis/analyze_contact_ground_truth.py"), sha256(root / "example/cpp/tools/analysis/analyze_contact_ground_truth.py"), "VERIFIED", "independent contact validation implementation")
    add("analyzer", "analyze_contact_dynamics.py", str(root / "example/cpp/tools/analysis/analyze_contact_dynamics.py"), sha256(root / "example/cpp/tools/analysis/analyze_contact_dynamics.py"), "VERIFIED", "independent dynamics validation implementation")
    add("derived", "analysis.json", str(args.output), sha256(args.output), "GENERATED", "deterministic analysis output")

    args.provenance_output.parent.mkdir(parents=True, exist_ok=True)
    with args.provenance_output.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["scope", "artifact", "path", "sha256", "status", "note"])
        writer.writerows(provenance_rows)
    print(json.dumps({"classification": proposed_classification, "raw_hashes_match": all_integrity, "indexed_files": len(integrity)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
