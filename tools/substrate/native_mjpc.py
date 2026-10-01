"""Persistent native MJPC controller process for prospective shared evaluation."""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

import numpy as np

from .build_identity import cache_values, verify_controller
from .clock import TimingSpec
from .native_transport import NativeTransport
from .contracts import (
    POLICY_JOINTS,
    PositionPDActuatorSpec,
    WholeBodyState,
    vector,
)


def validate_ready(value):
    if not isinstance(value, dict) or value.get("ready") is not True:
        raise ValueError("native MJPC controller did not report ready")
    exact = {
        "protocol": 3,
        "nq": 19,
        "nv": 18,
        "nu": 12,
        "planner": "MJPC iLQG",
        "source_nominal_biastype": "mjBIAS_NONE",
        "compatibility_correction": "private_model_mjBIAS_AFFINE",
        "canonical_evaluation_plant_modified": False,
        "gait_switch": "Manual",
        "gait": "Trot",
        "ground_miss_handling": "rollout_warning_failure",
        "warning_channel": "stderr",
        "policy_freshness": "current_candidate_required",
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            raise ValueError(f"native MJPC ready field drifted: {key}")
    planner_dt = value.get("planner_dt")
    horizon = value.get("horizon_steps")
    if (
        isinstance(planner_dt, bool)
        or not isinstance(planner_dt, (int, float))
        or not math.isfinite(planner_dt)
        or planner_dt <= 0
        or type(horizon) is not int
        or horizon < 2
    ):
        raise ValueError("invalid native MJPC planner timing")
    names = tuple(value.get("joint_names", ()))
    if len(names) != 12 or len(set(names)) != 12 or set(names) != set(POLICY_JOINTS):
        raise ValueError("native MJPC joint identity drifted")
    spec = PositionPDActuatorSpec(
        names,
        value.get("position_lower"),
        value.get("position_upper"),
        value.get("kp"),
        value.get("kd"),
    )
    if not np.allclose(spec.kp, 60.0, rtol=0, atol=1e-12) or not np.allclose(
        spec.kd, 5.0, rtol=0, atol=1e-12
    ):
        raise ValueError("native MJPC source PD gains drifted")
    return names, spec


def cadence_tick(time_s, timing, last_tick=None):
    if not isinstance(timing, TimingSpec):
        raise ValueError("native MJPC requires TimingSpec")
    if (
        isinstance(time_s, bool)
        or not isinstance(time_s, (int, float, np.integer, np.floating))
        or not math.isfinite(time_s)
        or time_s < 0
    ):
        raise ValueError("controller time must be finite nonnegative")
    tick = int(round(float(time_s) / timing.physics_period_s))
    if not math.isclose(
        float(time_s),
        tick * timing.physics_period_s,
        rel_tol=0,
        abs_tol=1e-9,
    ):
        raise ValueError("controller time is off the physics clock")
    if tick % timing.feedback_decimation:
        raise ValueError("controller step is off the feedback cadence")
    if last_tick is not None and tick != last_tick + timing.feedback_decimation:
        raise ValueError("missing, duplicate or reordered feedback tick")
    return tick, tick % timing.decimation == 0


def sample_command(command, replan, held_command=None):
    requested = vector(command, 3, "controller command")
    if type(replan) is not bool:
        raise ValueError("replan flag must be boolean")
    if replan:
        return requested, requested.copy()
    if held_command is None:
        raise ValueError("feedback step requires a previously sampled command")
    held = vector(held_command, 3, "held controller command")
    return requested, held


def step_packet(state, command, joint_names, *, replan):
    if not isinstance(state, WholeBodyState):
        raise ValueError("native MJPC requires WholeBodyState")
    if type(replan) is not bool:
        raise ValueError("replan flag must be boolean")
    state.validate()
    command = vector(command, 3, "controller command")
    qpos = state.qpos(joint_names)
    qvel = state.qvel(joint_names)
    values = [state.time_s, *command, *qpos, *qvel]
    return (
        "step "
        + ("1 " if replan else "0 ")
        + " ".join(format(float(value), ".17g") for value in values)
    )


def parse_step_response(value, expected_time, expected_replan):
    if not isinstance(value, dict):
        raise ValueError("native MJPC response must be an object")
    if value.get("ok") is not True:
        message = value.get("error")
        if not isinstance(message, str) or not message:
            message = "native MJPC controller rejected step"
        raise RuntimeError(message)
    time_s = value.get("time_s")
    cost = value.get("cost")
    replanned = value.get("replanned")
    planning_us = value.get("planning_compute_us")
    action_us = value.get("action_compute_us")
    if (
        isinstance(time_s, bool)
        or not isinstance(time_s, (int, float))
        or not math.isfinite(time_s)
        or not math.isclose(time_s, expected_time, rel_tol=0, abs_tol=1e-9)
        or isinstance(cost, bool)
        or not isinstance(cost, (int, float))
        or not math.isfinite(cost)
        or type(replanned) is not bool
        or replanned is not expected_replan
        or value.get("current_rollout_valid") is not True
        or type(planning_us) not in (int, float)
        or isinstance(planning_us, bool)
        or not math.isfinite(planning_us)
        or planning_us < 0
        or type(action_us) not in (int, float)
        or isinstance(action_us, bool)
        or not math.isfinite(action_us)
        or action_us < 0
        or (not replanned and planning_us != 0)
    ):
        raise ValueError("invalid native MJPC step metadata")
    return vector(value.get("q_des"), 12, "native MJPC q_des"), {
        "time_s": float(time_s),
        "cost": float(cost),
        "replanned": replanned,
        "current_rollout_valid": True,
        "planning_compute_s": float(planning_us) * 1e-6,
        "action_compute_s": float(action_us) * 1e-6,
    }


class NativeMJPCController:
    def __init__(
        self,
        binary,
        timing,
        *,
        popen=subprocess.Popen,
        stderr_log_path=None,
        startup_timeout_s=10.0,
        response_timeout_s=30.0,
    ):
        if not isinstance(timing, TimingSpec):
            raise ValueError("native MJPC controller requires TimingSpec")
        self.timing = timing
        self.binary = Path(binary).resolve(strict=True)
        self.build_identity = verify_controller(self.binary)
        cache = cache_values(self.binary.parent)
        source = Path(cache["MJPC_SOURCE_DIR"]).resolve(strict=True)
        self.task_xml = source / "mjpc/tasks/quadruped/task_flat.xml"
        if not self.task_xml.is_file():
            raise ValueError("pinned QuadrupedFlat task XML is missing")
        self._transport = NativeTransport(
            [str(self.binary), str(self.task_xml)],
            popen=popen,
            stderr_log_path=stderr_log_path,
        )
        self.process = self._transport.process
        self._closed = False
        self._requires_reset = False
        self._response_timeout_s = response_timeout_s
        self._last_feedback_tick = None
        self._held_command = None
        try:
            ready = self._transport.read_json(startup_timeout_s)
            self.joint_names, self.actuator_spec = validate_ready(ready)
        except Exception:
            self.close()
            raise
        self.ready = ready
        self._diagnostics = {
            "planner": ready["planner"],
            "planner_dt_s": float(ready["planner_dt"]),
            "horizon_steps": int(ready["horizon_steps"]),
            "source_nominal_biastype": ready["source_nominal_biastype"],
            "compatibility_correction": ready["compatibility_correction"],
            "canonical_evaluation_plant_modified": False,
            "gait_switch": ready["gait_switch"],
            "gait": ready["gait"],
            "ground_miss_handling": ready["ground_miss_handling"],
            "warning_channel": ready["warning_channel"],
            "policy_freshness": ready["policy_freshness"],
            "control_period_s": timing.control_period_s,
            "feedback_period_s": timing.feedback_period_s,
            "compute_semantics": timing.compute_semantics,
        }

    def _request(self, line):
        return self._transport.request(line, self._response_timeout_s)

    def reset(self, observation):
        if not isinstance(observation, WholeBodyState):
            raise ValueError("native MJPC reset requires WholeBodyState")
        observation.validate()
        response = self._request("reset")
        if response != {"ok": True, "reset": True}:
            raise RuntimeError("native MJPC reset failed")
        self._requires_reset = False
        self._last_feedback_tick = None
        self._held_command = None
        self._diagnostics.pop("last_step", None)

    def step(self, observation, command):
        if self._requires_reset:
            raise RuntimeError("native MJPC requires reset after failed step")
        tick, replan = cadence_tick(
            observation.time_s, self.timing, self._last_feedback_tick
        )
        requested, sampled = sample_command(command, replan, self._held_command)
        packet = step_packet(observation, sampled, self.joint_names, replan=replan)
        try:
            response = self._request(packet)
            action, metadata = parse_step_response(response, observation.time_s, replan)
        except Exception:
            self._requires_reset = True
            raise
        self._last_feedback_tick = tick
        if replan:
            self._held_command = sampled.copy()
        metadata["requested_command"] = requested.tolist()
        metadata["sampled_command"] = sampled.tolist()
        metadata["command_sampled"] = replan
        self._diagnostics["last_step"] = metadata
        return action

    def diagnostics(self):
        result = json.loads(json.dumps(self._diagnostics))
        result["transport"] = self._transport.diagnostics()
        return result

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._transport.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
