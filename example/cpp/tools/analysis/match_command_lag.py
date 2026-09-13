#!/usr/bin/env python3
"""Match simulator snapshot controls to causal-past controller LowCmd rows."""

from __future__ import annotations

import argparse
import csv
import json
import math
import struct
from bisect import bisect_left, bisect_right
from pathlib import Path


MOTORS = 12
MOTOR_LABELS = ["FR_hip", "FR_thigh", "FR_calf", "FL_hip", "FL_thigh", "FL_calf", "RR_hip", "RR_thigh", "RR_calf", "RL_hip", "RL_thigh", "RL_calf"]
START_ACTIVE_S = 31.90
JOINT_QPOS_INDICES = [10, 11, 12, 7, 8, 9, 16, 17, 18, 13, 14, 15]
JOINT_QVEL_INDICES = [9, 10, 11, 6, 7, 8, 15, 16, 17, 12, 13, 14]
END_ACTIVE_S = 33.00
WINDOW_S = 0.050
CTRL_TOL_NM = 1e-5
HEADER_FMT = "<8s9I3d"
FIXED_RECORD_FMT = "<Qq3d3iI"
MAGIC = b"GO2PDSNP"


def llround_ms(value: float) -> int:
    return math.floor(value * 1000.0 + 0.5)


def finite(row: dict[str, str], key: str) -> float:
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key}")
    return value


def read_closure(path: Path) -> tuple[list[dict], dict[int, dict], list[int]]:
    rows: list[dict] = []
    by_tick: dict[int, dict] = {}
    duplicate_ticks: list[int] = []
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        for raw in reader:
            try:
                row = {
                    "active_time_s": finite(raw, "active_relative_time_s"),
                    "state_time_s": finite(raw, "state_tick_s"),
                    "target_velocity_mps": finite(raw, "velocity_requested_mps"),
                    "applied_velocity_mps": finite(raw, "velocity_applied_mps"),
                    "measured_velocity_mps": finite(raw, "velocity_measured_mps"),
                    "roll_rad": finite(raw, "roll_rad"),
                    "pitch_rad": finite(raw, "pitch_rad"),
                    "controller_contact_mask": int(
                        round(finite(raw, "solver_contact_mask"))
                    ),
                    "physical_contact_mask": int(
                        round(finite(raw, "physical_contact_mask"))
                    ),
                    "q_des": [],
                    "dq_des": [],
                    "kp": [],
                    "kd": [],
                    "tau_ff": [],
                }
                for motor in range(MOTORS):
                    prefix = f"motor_{motor}_"
                    row["q_des"].append(finite(raw, prefix + "q_des"))
                    row["dq_des"].append(finite(raw, prefix + "dq_des"))
                    row["kp"].append(finite(raw, prefix + "kp"))
                    row["kd"].append(finite(raw, prefix + "kd"))
                    row["tau_ff"].append(finite(raw, prefix + "tau_ff"))
            except (KeyError, ValueError):
                continue
            row["state_tick_ms"] = llround_ms(row["state_time_s"])
            rows.append(row)
            if row["state_tick_ms"] in by_tick:
                duplicate_ticks.append(row["state_tick_ms"])
            else:
                by_tick[row["state_tick_ms"]] = row
    rows.sort(key=lambda item: item["state_time_s"])
    return rows, by_tick, duplicate_ticks


def read_controller(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        for raw in reader:
            try:
                row = {
                    "cmd_time_s": finite(raw, "cmd_time_s"),
                    "state_time_s": finite(raw, "state_tick_s"),
                    "active_time_s": finite(raw, "diag_active_relative_time_s"),
                    "q_des": [],
                    "dq_des": [],
                    "kp": [],
                    "kd": [],
                    "tau_ff": [],
                }
                for label in MOTOR_LABELS:
                    row["q_des"].append(finite(raw, label + "_q_target"))
                    row["dq_des"].append(finite(raw, label + "_dq_target"))
                    row["kp"].append(finite(raw, label + "_kp"))
                    row["kd"].append(finite(raw, label + "_kd"))
                    row["tau_ff"].append(finite(raw, label + "_tau_ff"))
            except (KeyError, ValueError):
                continue
            row["state_tick_ms"] = llround_ms(row["state_time_s"])
            rows.append(row)
    rows.sort(key=lambda item: (item["state_time_s"], item["cmd_time_s"]))
    return rows


def read_snapshots(path: Path) -> tuple[dict, list[dict]]:
    with path.open("rb") as stream:
        header_raw = stream.read(struct.calcsize(HEADER_FMT))
        if len(header_raw) != struct.calcsize(HEADER_FMT):
            raise ValueError("truncated snapshot header")
        (
            magic,
            version,
            mujoco_version,
            mjt_num_bytes,
            state_sig,
            state_size,
            nq,
            nv,
            na,
            nu,
            time_start_s,
            time_end_s,
            timestep_s,
        ) = struct.unpack(HEADER_FMT, header_raw)
        if magic != MAGIC or version != 1 or mjt_num_bytes != 8:
            raise ValueError("unsupported snapshot header")
        record_fmt_size = struct.calcsize(FIXED_RECORD_FMT)
        state_fmt = f"<{state_size}d"
        state_bytes = struct.calcsize(state_fmt)
        records = []
        while True:
            fixed = stream.read(record_fmt_size)
            if not fixed:
                break
            if len(fixed) != record_fmt_size:
                raise ValueError("truncated snapshot record")
            (
                record_index,
                state_tick_ms,
                time_s,
                qvel0,
                live_qacc0,
                live_ncon,
                live_nefc,
                live_contact_mask,
                stored_state_size,
            ) = struct.unpack(FIXED_RECORD_FMT, fixed)
            if stored_state_size != state_size:
                raise ValueError("snapshot state size mismatch")
            state_raw = stream.read(state_bytes)
            if len(state_raw) != state_bytes:
                raise ValueError("truncated snapshot state")
            state = struct.unpack(state_fmt, state_raw)
            records.append(
                {
                    "record_index": record_index,
                    "state_tick_ms": state_tick_ms,
                    "time_s": time_s,
                    "qvel0": qvel0,
                    "live_qacc0": live_qacc0,
                    "live_ncon": live_ncon,
                    "live_nefc": live_nefc,
                    "live_contact_mask": live_contact_mask,
                    "state": state,
                }
            )
    header = {
        "mujoco_version": mujoco_version,
        "state_sig": state_sig,
        "state_size": state_size,
        "nq": nq,
        "nv": nv,
        "na": na,
        "nu": nu,
        "time_start_s": time_start_s,
        "time_end_s": time_end_s,
        "timestep_s": timestep_s,
    }
    return header, records


def quantile(values: list[float], fraction: float) -> float:
    values = sorted(values)
    if not values:
        return math.nan
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--closure", type=Path, required=True)
    parser.add_argument("--controller", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    closure_rows, closure_by_tick, duplicate_ticks = read_closure(args.closure)
    controller_rows = read_controller(args.controller)
    header, snapshots = read_snapshots(args.snapshots)
    if header["nq"] != 19 or header["nv"] != 18 or header["nu"] != MOTORS:
        raise ValueError(f"unexpected snapshot signature: {header}")

    target_pairs = []
    clock_offsets = []
    for snapshot in snapshots:
        selection = closure_by_tick.get(snapshot["state_tick_ms"])
        if selection is None:
            continue
        if not (START_ACTIVE_S <= selection["active_time_s"] < END_ACTIVE_S):
            continue
        target_pairs.append((snapshot, selection))
        clock_offsets.append(snapshot["time_s"] - selection["state_time_s"])
    clock_offset_s = quantile(clock_offsets, 0.5) if clock_offsets else math.nan

    candidate_times = [row["state_time_s"] + clock_offset_s for row in controller_rows]
    output_rows = []
    no_candidate = 0
    for snapshot, selection in target_pairs:
        snapshot_state = snapshot["state"]
        qpos_start = 1
        qvel_start = qpos_start + header["nq"]
        # Snapshot state uses XML body order; bridge sensordata uses sensor order.
        q_snapshot = [snapshot_state[qpos_start + index] for index in JOINT_QPOS_INDICES]
        dq_snapshot = [snapshot_state[qvel_start + index] for index in JOINT_QVEL_INDICES]
        ctrl_start = (
            qvel_start + header["nv"] + header["na"] + header["nv"]
        )
        actual_ctrl = list(snapshot_state[ctrl_start : ctrl_start + header["nu"]])
        left = bisect_left(candidate_times, snapshot["time_s"] - WINDOW_S)
        right = bisect_right(candidate_times, snapshot["time_s"] + 1e-12)
        scored = []
        for index in range(left, right):
            candidate = controller_rows[index]
            reconstructed = [
                candidate["tau_ff"][motor]
                + candidate["kp"][motor]
                * (candidate["q_des"][motor] - q_snapshot[motor])
                + candidate["kd"][motor]
                * (candidate["dq_des"][motor] - dq_snapshot[motor])
                for motor in range(MOTORS)
            ]
            errors = [
                reconstructed[motor] - actual_ctrl[motor] for motor in range(MOTORS)
            ]
            max_abs = max(abs(value) for value in errors)
            l2 = math.sqrt(sum(value * value for value in errors))
            scored.append((max_abs, l2, candidate, reconstructed))
        scored.sort(key=lambda item: (item[0], item[1], item[2]["state_time_s"]))
        if not scored:
            no_candidate += 1
            continue
        best = scored[0]
        second = scored[1] if len(scored) > 1 else None
        best_max, best_l2, candidate, reconstructed = best
        row = {
            "target_active_time_s": selection["active_time_s"],
            "snapshot_sim_time_s": snapshot["time_s"],
            "snapshot_state_tick_ms": snapshot["state_tick_ms"],
            "snapshot_index": snapshot["record_index"],
            "nominal_clock_offset_ms": clock_offset_s * 1000.0,
            "matched_controller_cmd_time_s": candidate["cmd_time_s"],
            "matched_controller_state_time_s": candidate["state_time_s"],
            "matched_controller_state_tick_ms": candidate["state_tick_ms"],
            "matched_controller_active_time_s": candidate["active_time_s"],
            "command_age_ms": snapshot["time_s"]
            - (candidate["state_time_s"] + clock_offset_s),
            "matched_tick_delta": snapshot["state_tick_ms"] - candidate["state_tick_ms"],
            "candidate_count": len(scored),
            "best_max_abs_ctrl_error_Nm": best_max,
            "best_l2_ctrl_error_Nm": best_l2,
            "second_best_max_abs_ctrl_error_Nm": (
                second[0] if second is not None else math.nan
            ),
            "second_best_l2_ctrl_error_Nm": (
                second[1] if second is not None else math.nan
            ),
            "second_best_command_age_ms": (
                snapshot["time_s"]
                - (second[2]["state_time_s"] + clock_offset_s)
                if second is not None
                else math.nan
            ),
            "selection_velocity_target_mps": selection["target_velocity_mps"],
            "selection_velocity_applied_mps": selection["applied_velocity_mps"],
            "selection_velocity_measured_mps": selection["measured_velocity_mps"],
            "selection_roll_rad": selection["roll_rad"],
            "selection_pitch_rad": selection["pitch_rad"],
            "selection_controller_contact_mask": selection["controller_contact_mask"],
            "selection_physical_contact_mask": selection["physical_contact_mask"],
            "snapshot_qvel0_mps": snapshot["qvel0"],
            "snapshot_live_qacc0_mps2": snapshot["live_qacc0"],
        }
        for motor in range(MOTORS):
            row[f"snapshot_q_{motor}"] = q_snapshot[motor]
            row[f"snapshot_dq_{motor}"] = dq_snapshot[motor]
            row[f"matched_q_des_{motor}"] = candidate["q_des"][motor]
            row[f"matched_dq_des_{motor}"] = candidate["dq_des"][motor]
            row[f"matched_kp_{motor}"] = candidate["kp"][motor]
            row[f"matched_kd_{motor}"] = candidate["kd"][motor]
            row[f"matched_tau_ff_{motor}"] = candidate["tau_ff"][motor]
            row[f"snapshot_ctrl_{motor}"] = actual_ctrl[motor]
            row[f"reconstructed_ctrl_{motor}"] = reconstructed[motor]
        output_rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(output_rows[0]) if output_rows else [
        "target_active_time_s",
        "snapshot_sim_time_s",
        "snapshot_state_tick_ms",
    ]
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)

    residuals = [row["best_max_abs_ctrl_error_Nm"] for row in output_rows]
    lags = [row["command_age_ms"] for row in output_rows]
    tick_histogram: dict[str, int] = {}
    for row in output_rows:
        key = str(row["matched_tick_delta"])
        tick_histogram[key] = tick_histogram.get(key, 0) + 1
    pass_count = sum(value <= CTRL_TOL_NM for value in residuals)
    summary = {
        "snapshot_header": header,
        "raw_snapshot_records": len(snapshots),
        "closure_rows": len(closure_rows),
        "duplicate_closure_tick_count": len(duplicate_ticks),
        "target_snapshot_count": len(target_pairs),
        "matched_snapshot_count": len(output_rows),
        "no_candidate_count": no_candidate,
        "active_window_s": [START_ACTIVE_S, END_ACTIVE_S],
        "causal_window_s": WINDOW_S,
        "clock_offset_ms_median": clock_offset_s * 1000.0,
        "clock_offset_ms_p95_abs": (
            quantile([abs(value) * 1000.0 for value in clock_offsets], 0.95)
            if clock_offsets
            else math.nan
        ),
        "best_max_abs_ctrl_error_Nm": {
            "min": min(residuals) if residuals else math.nan,
            "median": quantile(residuals, 0.5),
            "p95": quantile(residuals, 0.95),
            "max": max(residuals) if residuals else math.nan,
        },
        "strong_gate": {
            "threshold_Nm": CTRL_TOL_NM,
            "pass_count": pass_count,
            "pass_fraction": pass_count / len(residuals) if residuals else 0.0,
            "required_fraction": 0.95,
        },
        "lag_ms": {
            "min": min(lags) if lags else math.nan,
            "p05": quantile(lags, 0.05),
            "median": quantile(lags, 0.5),
            "p95": quantile(lags, 0.95),
            "max": max(lags) if lags else math.nan,
        },
        "matched_tick_delta_histogram": dict(
            sorted(tick_histogram.items(), key=lambda item: int(item[0]))
        ),
    }
    print(json.dumps(summary, sort_keys=True, allow_nan=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
