"""Persistent native MJPC controller process for prospective shared evaluation."""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

import numpy as np

from .build_identity import cache_values, verify_controller
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
        "protocol": 2,
        "nq": 19,
        "nv": 18,
        "nu": 12,
        "planner": "MJPC iLQG",
        "source_nominal_biastype": "mjBIAS_NONE",
        "compatibility_correction": "private_model_mjBIAS_AFFINE",
        "canonical_evaluation_plant_modified": False,
        "gait_switch": "Manual",
        "gait": "Trot",
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


def step_packet(state, command, joint_names):
    if not isinstance(state, WholeBodyState):
        raise ValueError("native MJPC requires WholeBodyState")
    state.validate()
    command = vector(command, 3, "controller command")
    qpos = state.qpos(joint_names)
    qvel = state.qvel(joint_names)
    values = [state.time_s, *command, *qpos, *qvel]
    return "step " + " ".join(format(float(value), ".17g") for value in values)


def parse_step_response(value, expected_time):
    if not isinstance(value, dict):
        raise ValueError("native MJPC response must be an object")
    if value.get("ok") is not True:
        message = value.get("error")
        if not isinstance(message, str) or not message:
            message = "native MJPC controller rejected step"
        raise RuntimeError(message)
    time_s = value.get("time_s")
    cost = value.get("cost")
    compute_us = value.get("compute_us")
    if (
        isinstance(time_s, bool)
        or not isinstance(time_s, (int, float))
        or not math.isfinite(time_s)
        or not math.isclose(time_s, expected_time, rel_tol=0, abs_tol=1e-9)
        or isinstance(cost, bool)
        or not isinstance(cost, (int, float))
        or not math.isfinite(cost)
        or type(compute_us) not in (int, float)
        or isinstance(compute_us, bool)
        or not math.isfinite(compute_us)
        or compute_us < 0
    ):
        raise ValueError("invalid native MJPC step metadata")
    return vector(value.get("q_des"), 12, "native MJPC q_des"), {
        "time_s": float(time_s),
        "cost": float(cost),
        "compute_s": float(compute_us) * 1e-6,
    }


class NativeMJPCController:
    def __init__(self, binary, *, popen=subprocess.Popen):
        self.binary = Path(binary).resolve(strict=True)
        self.build_identity = verify_controller(self.binary)
        cache = cache_values(self.binary.parent)
        source = Path(cache["MJPC_SOURCE_DIR"]).resolve(strict=True)
        self.task_xml = source / "mjpc/tasks/quadruped/task_flat.xml"
        if not self.task_xml.is_file():
            raise ValueError("pinned QuadrupedFlat task XML is missing")
        self.process = popen(
            [str(self.binary), str(self.task_xml)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._closed = False
        ready = self._read_json()
        self.joint_names, self.actuator_spec = validate_ready(ready)
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
        }

    def _read_json(self):
        line = self.process.stdout.readline()
        if not line:
            code = self.process.poll()
            detail = self.process.stderr.read() if code is not None else ""
            raise RuntimeError(
                "native MJPC controller closed output"
                + (f": {detail.strip()}" if detail.strip() else "")
            )
        try:
            return json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("native MJPC emitted invalid JSON") from error

    def _request(self, line):
        if self._closed or self.process.poll() is not None:
            raise RuntimeError("native MJPC controller is not running")
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()
        return self._read_json()

    def reset(self, observation):
        if not isinstance(observation, WholeBodyState):
            raise ValueError("native MJPC reset requires WholeBodyState")
        observation.validate()
        response = self._request("reset")
        if response != {"ok": True, "reset": True}:
            raise RuntimeError("native MJPC reset failed")
        self._diagnostics.pop("last_step", None)

    def step(self, observation, command):
        packet = step_packet(observation, command, self.joint_names)
        response = self._request(packet)
        action, metadata = parse_step_response(response, observation.time_s)
        self._diagnostics["last_step"] = metadata
        return action

    def diagnostics(self):
        return json.loads(json.dumps(self._diagnostics))

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.process.poll() is None:
            try:
                self.process.stdin.write("quit\n")
                self.process.stdin.flush()
                self.process.wait(timeout=2)
            except Exception:
                self.process.kill()
                self.process.wait(timeout=2)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
