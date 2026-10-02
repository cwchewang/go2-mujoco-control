"""Candidate baseline loader and zero-integration raw-state performance replay."""

from dataclasses import replace
from pathlib import Path
import math
import numpy as np

from .aligned_anchor import load_anchor
from .bounded_conditions import IDS
from .evaluator import CanonicalEvaluator
from .integrity import digest, strict_json

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = Path(__file__).with_name("protocols") / "shared_baseline_probes_v1.json"


def load_plan(path=DEFAULT_PLAN):
    raw = strict_json(Path(path).read_text())
    exact = {
        "schema": 1,
        "id": "shared-baseline-probes-v1",
        "mode": "candidate_preparation",
        "self_authorizes_physics": False,
        "baseline_attempts": 4,
        "challenge_attempts_max": 16,
        "max_attempts": 20,
        "horizon_ticks": 6000,
        "measurement_start_tick": 1000,
        "measurement_end_tick_exclusive": 6000,
        "replicates": 2,
        "physics_steps_max": 120000,
        "repeat_absolute_tolerance": 1e-9,
        "retry": "none",
        "safety_execution_evidence_failure": "stop_campaign",
        "horizon_performance_failure": "retain_and_continue",
        "stage3_gate": "two_valid_passing_repeatable_own_baselines",
        "live_readiness": "NOT_READY_REQUIRES_CAPTURE_RUNNER_AND_DUAL_REVIEW",
    }
    for key, expected in exact.items():
        if type(raw.get(key)) is not type(expected) or raw[key] != expected:
            raise ValueError("candidate baseline plan drifted: " + key)
    anchor_path = ROOT / raw["anchor"]
    if digest(anchor_path) != raw["anchor_sha256"]:
        raise ValueError("anchor identity drifted")
    anchor = load_anchor(anchor_path)
    task = replace(
        anchor["task"],
        task_id=raw["id"],
        horizon_ticks=raw["horizon_ticks"],
        measurement_start_tick=raw["measurement_start_tick"],
    )
    if raw["performance"] != {
        "body_vx_mean_min_mps": 0.8,
        "body_vx_mae_max_mps": 0.2,
        "episode_lateral_max_m": 0.3,
        "episode_yaw_max_rad": 0.3,
    }:
        raise ValueError("candidate operational thresholds drifted")
    expected_cards = {
        "sliding_friction": {
            "variable": "four_foot_geom_sliding_friction",
            "from": 0.8,
            "to": 0.3,
            "start_tick": 3000,
            "end_tick_exclusive": 6000,
            "interface": "canonical_model.geom_friction[feet,0]",
            "evidence": "active_foot_floor_contact_friction",
        },
        "observation_delay": {
            "variable": "measurement_transport_delay_s",
            "from": 0.0,
            "to": 0.02,
            "start_tick": 0,
            "end_tick_exclusive": 6000,
            "interface": "bounded_immutable_state_buffer",
            "evidence": "sample_available_controller_times_and_payload",
        },
        "decision_period": {
            "variable": "controller_decision_period_s",
            "from": 0.02,
            "to": 0.04,
            "start_tick": 0,
            "end_tick_exclusive": 6000,
            "interface": "TimingSpec_control_period",
            "evidence": "actual_policy_update_and_native_replan_ticks",
        },
        "lateral_force": {
            "variable": "base_world_y_force_N",
            "from": 0.0,
            "to": 50.0,
            "start_tick": 3000,
            "end_tick_exclusive": 3100,
            "interface": "data.xfrc_applied[base_link]",
            "evidence": "actual_applied_world_wrench_each_tick",
        },
    }
    if any(
        isinstance(value, bool)
        for card in raw["conditions"].values()
        for value in card.values()
    ):
        raise ValueError("condition card cannot contain booleans")
    if raw["conditions"] != expected_cards or set(raw["conditions"]) != set(IDS):
        raise ValueError("bounded condition cards drifted")
    return {**anchor, "raw": raw, "task": task}


def replay_baseline(rows, plan):
    task = plan["task"]
    if not rows or not np.allclose(
        rows[0]["qpos"][3:7], [1, 0, 0, 0], rtol=0, atol=1e-12
    ):
        raise ValueError("baseline initial heading drifted")
    oracle = CanonicalEvaluator(task, plan["physics_period_s"]).evaluate(rows).as_dict()
    if oracle["first_failure"] is not None:
        return {
            "classification": "SAFETY_STOP",
            "canonical": oracle,
            "performance": None,
        }
    if oracle["terminal_reason"] != "horizon":
        return {
            "classification": "INCOMPLETE",
            "canonical": oracle,
            "performance": None,
        }
    start, end = task.measurement_start_tick, task.horizon_ticks
    velocities = []
    lateral, yaw = [], []
    initial_y = rows[0]["qpos"][1]
    for row in rows:
        tick = row["tick"]
        if not np.allclose(row["command"], task.command_at(tick), rtol=0, atol=1e-12):
            raise ValueError("logged command drifted")
        q = np.asarray(row["qpos"], dtype=float)
        v = np.asarray(row["qvel"], dtype=float)
        w, x, y, z = q[3:7]
        lateral.append(abs(float(q[1] - initial_y)))
        yaw.append(abs(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))))
        if start <= tick < end:
            # Scalar raw-state algebra, independent of evaluator velocity helper.
            velocities.append(
                (w * w + x * x - y * y - z * z) * v[0]
                + 2 * (x * y + w * z) * v[1]
                + 2 * (x * z - w * y) * v[2]
            )
    if len(velocities) != end - start:
        raise ValueError("half-open performance sample count drifted")
    metrics = {
        "body_vx_mean_mps": float(np.mean(velocities)),
        "body_vx_mae_mps": float(np.mean(np.abs(np.asarray(velocities) - 1.0))),
        "episode_lateral_max_m": max(lateral),
        "episode_yaw_max_rad": max(yaw),
        "measurement_samples": len(velocities),
        "measurement_window": "[2,12)",
        "endpoint_in_performance_mean": False,
    }
    t = plan["raw"]["performance"]
    passed = (
        metrics["body_vx_mean_mps"] >= t["body_vx_mean_min_mps"]
        and metrics["body_vx_mae_mps"] <= t["body_vx_mae_max_mps"]
        and metrics["episode_lateral_max_m"] <= t["episode_lateral_max_m"]
        and metrics["episode_yaw_max_rad"] <= t["episode_yaw_max_rad"]
    )
    return {
        "classification": "PASS" if passed else "PERFORMANCE_FAIL",
        "canonical": oracle,
        "performance": metrics,
    }


def repeat_difference(first, second):
    """Two traces only; exclude wall-time diagnostics, retain raw dynamics/actions."""
    if len(first) != len(second):
        raise ValueError("repeat frame counts differ")
    maximum = 0.0
    for a, b in zip(first, second):
        if a["tick"] != b["tick"] or a["terminal_reason"] != b["terminal_reason"]:
            raise ValueError("repeat tick/terminal mismatch")
        for field in ("qpos", "qvel"):
            va, vb = (
                np.asarray(a[field], dtype=float),
                np.asarray(b[field], dtype=float),
            )
            if (
                va.shape != vb.shape
                or not np.isfinite(va).all()
                or not np.isfinite(vb).all()
            ):
                raise ValueError("invalid repeated state")
            maximum = max(maximum, float(np.max(np.abs(va - vb))))
        if (a["action"] is None) != (b["action"] is None):
            raise ValueError("repeat action presence mismatch")
        if a["action"] is not None:
            va, vb = np.asarray(a["action"]["ctrl"]), np.asarray(b["action"]["ctrl"])
            if (
                va.shape != (12,)
                or vb.shape != (12,)
                or not np.isfinite([va, vb]).all()
            ):
                raise ValueError("invalid repeated control")
            maximum = max(maximum, float(np.max(np.abs(va - vb))))
    return {
        "maximum_absolute_state_control_difference": maximum,
        "repeatable": maximum <= 1e-9,
    }
