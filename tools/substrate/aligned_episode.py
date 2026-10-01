"""Shared episode semantics for prospective aligned captures."""

import json
import math
import numpy as np

from .clock import TimingSpec
from .contracts import InformationSpec, TorqueCommand
from .evaluator import CanonicalEvaluator
from .specs import TaskSpec


def _payload(plant, info):
    if info.observation == "proprioceptive":
        return plant.observe()
    if info.observation == "whole_body_state":
        return plant.whole_body_state()
    raise ValueError("unsupported aligned observation regime")


def _target_record(target):
    if not isinstance(target, TorqueCommand):
        raise ValueError("controller adapter must return TorqueCommand")
    return {
        "joint_names": list(target.joint_names),
        **{
            name: getattr(target, name).tolist()
            for name in (
                "feedforward",
                "position_target",
                "velocity_target",
                "kp",
                "kd",
            )
        },
    }


def run_aligned_episode(plant, controller, task, information, timing, emit, consume):
    if not isinstance(task, TaskSpec):
        raise ValueError("aligned episode requires TaskSpec")
    if not isinstance(information, InformationSpec):
        raise ValueError("aligned episode requires InformationSpec")
    if not isinstance(timing, TimingSpec):
        raise ValueError("aligned episode requires TimingSpec")
    if information.latency_s != 0:
        raise ValueError("aligned episode has no delayed-observation transport yet")
    if timing.compute_semantics != "offline_unbounded":
        raise ValueError("aligned episode only implements offline_unbounded compute")
    if not math.isclose(
        float(plant.model.opt.timestep),
        timing.physics_period_s,
        rel_tol=0,
        abs_tol=1e-12,
    ):
        raise ValueError("plant and controller physics periods differ")

    plant.reset()
    if plant.steps != 0 or not math.isclose(float(plant.data.time), 0.0, abs_tol=1e-12):
        raise ValueError("aligned reset must start at tick zero")

    initial = _payload(plant, information)
    controller.reset(information.deliver(initial, 0.0, 0.0).payload)
    evaluator = CanonicalEvaluator(task, timing.physics_period_s)
    clock = timing.feedback_clock()
    target = None
    consumed = False

    for tick in range(task.horizon_ticks + 1):
        row = plant.snapshot(tick)
        update = clock.observe(tick, row["sim_time_s"])
        failure = evaluator.failure(row, plant.initial_y)
        command = task.command_at(tick)
        row.update(
            failure=failure,
            command=command.tolist(),
            controller_update=False,
            information=None,
            controller_diagnostics=None,
            target=None,
            action=None,
            terminal_reason=None,
        )
        if failure is not None or tick == task.horizon_ticks:
            row["terminal_reason"] = failure or "horizon"
            if failure == "nonfinite":
                # JSON null preserves invalid state positions without nonfinite JSON.
                # The canonical replay converts those nulls back to nonfinite floats.
                for field in ("qpos", "qvel"):
                    row[field] = [
                        float(value) if math.isfinite(float(value)) else None
                        for value in row[field]
                    ]
            emit(row)
            return {
                "terminal_reason": row["terminal_reason"],
                "steps": tick,
                "attempt_consumed": consumed,
            }

        if update:
            payload = _payload(plant, information)
            timed = information.deliver(payload, row["sim_time_s"], row["sim_time_s"])
            target = controller.step(timed.payload, command)
            if not isinstance(target, TorqueCommand):
                raise ValueError("controller adapter must return TorqueCommand")
            diagnostics = controller.diagnostics()
            if not isinstance(diagnostics, dict):
                raise ValueError("controller diagnostics must be a dict")
            try:
                json.dumps(diagnostics, allow_nan=False)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "controller diagnostics must be finite JSON"
                ) from error
            row["controller_update"] = True
            row["information"] = {
                "observation": information.observation,
                "model_access": information.model_access,
                "sample_time_s": timed.sample_time_s,
                "available_time_s": timed.available_time_s,
                "controller_time_s": timed.controller_time_s,
                "age_s": timed.age_s,
            }
            row["controller_diagnostics"] = diagnostics

        if target is None:
            raise ValueError("feedback clock did not produce an initial action")

        action = target.resolve(plant.observe(), plant.lower, plant.upper, plant.names)
        row["target"] = _target_record(target)
        row["action"] = {
            key: value.tolist() if isinstance(value, np.ndarray) else value
            for key, value in action.items()
        }
        if not consumed:
            consume()
            consumed = True
        emit(row)
        plant.step(action["ctrl"])

    raise AssertionError("unreachable aligned episode exit")


def replay_aligned_rows(rows, task, physics_period_s):
    return CanonicalEvaluator(task, physics_period_s).evaluate(rows).as_dict()
