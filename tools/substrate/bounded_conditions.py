"""Four prospective single-strength conditions; no launch or integration entry."""

from collections import deque
from dataclasses import replace
import math
import hashlib
import json
import numpy as np

from .contracts import (
    InformationSpec,
    TimedObservation,
    WholeBodyState,
    POLICY_JOINTS,
    reorder,
)


IDS = ("sliding_friction", "observation_delay", "decision_period", "lateral_force")


def payload_digest(payload):
    """Canonical named-state-v1 wire evidence; no simulator handles."""
    p = payload.proprioception if isinstance(payload, WholeBodyState) else payload
    p.validate()
    proprio = {
        "joint_names": list(POLICY_JOINTS),
        "position": reorder(p.position, p.joint_names, POLICY_JOINTS).tolist(),
        "velocity": reorder(p.velocity, p.joint_names, POLICY_JOINTS).tolist(),
        "quaternion_wxyz": p.quaternion_wxyz.tolist(),
        "angular_velocity_body": p.angular_velocity_body.tolist(),
    }
    if isinstance(payload, WholeBodyState):
        record = {
            "kind": "whole_body_state",
            "proprioception": proprio,
            "base_position_world": payload.base_position_world.tolist(),
            "linear_velocity_world": payload.linear_velocity_world.tolist(),
            "time_s": payload.time_s,
        }
    else:
        record = {"kind": "proprioceptive", **proprio}
    return hashlib.sha256(
        json.dumps(
            record, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def condition_specs(name, information, timing):
    if name not in IDS:
        raise ValueError("unknown bounded condition")
    if information.latency_s != 0 or timing.compute_semantics != "offline_unbounded":
        raise ValueError("conditions require the zero-latency offline baseline")
    if timing.physics_period_s != 0.002 or timing.control_period_s != 0.02:
        raise ValueError("baseline timing drifted")
    if name == "observation_delay":
        information = replace(information, latency_s=0.02)
    if name == "decision_period":
        # RL has one decision/target cadence; MJPC retains its fast feedback.
        feedback = 0.04 if information.observation == "proprioceptive" else 0.002
        timing = replace(timing, control_period_s=0.04, feedback_period_s=feedback)
    return information, timing


class BoundedCondition:
    """Explicit observation age, clock adaptation, and owned plant interventions."""

    def __init__(self, name):
        if name not in IDS:
            raise ValueError("unknown bounded condition")
        self.name = name

    def reset(self, plant, information, timing):
        if not isinstance(information, InformationSpec):
            raise ValueError("condition requires InformationSpec")
        expected_latency = 0.02 if self.name == "observation_delay" else 0
        if information.latency_s != expected_latency:
            raise ValueError("condition latency drifted")
        expected_control = 0.04 if self.name == "decision_period" else 0.02
        expected_feedback = (
            expected_control if information.observation == "proprioceptive" else 0.002
        )
        if (
            timing.physics_period_s != 0.002
            or timing.control_period_s != expected_control
            or timing.feedback_period_s != expected_feedback
        ):
            raise ValueError("condition timing drifted")
        self.information = information
        self.history = deque(maxlen=11)
        self.last_tick = -1
        self.switched = False
        self.contact_samples = 0
        self.force_ticks = 0
        self.delayed_updates = 0
        self.initial = self.payload(plant)
        if self.name == "sliding_friction":
            self.feet = tuple(plant.feet)
            if (
                len(self.feet) != 4
                or not np.allclose(
                    plant.model.geom_friction[list(self.feet)],
                    [0.8, 0.02, 0.01],
                    rtol=0,
                    atol=1e-12,
                )
                or np.any(
                    plant.model.geom_priority[list(self.feet)]
                    <= plant.model.geom_priority[plant.floor]
                )
                or np.any(plant.model.geom_condim[list(self.feet)] != 6)
            ):
                raise ValueError("baseline foot contact semantics drifted")
            from .model import physical_fingerprint

            self.before_fingerprint = physical_fingerprint(plant.model)
            self.after_fingerprint = self.before_fingerprint
        if self.name == "lateral_force":
            self.body = plant.mj.mj_name2id(
                plant.model, plant.mj.mjtObj.mjOBJ_BODY, "base_link"
            )
            if self.body < 1 or np.any(plant.data.xfrc_applied):
                raise ValueError(
                    "force hook requires named base and zero external forces"
                )
            self.last_force = np.zeros(6)
        return self.initial

    def payload(self, plant):
        if self.information.observation == "proprioceptive":
            return plant.observe()
        return plant.whole_body_state()

    def sample(self, plant, tick, time_s):
        if type(tick) is not int or tick != self.last_tick + 1:
            raise ValueError("condition sampling tick gap")
        if not math.isclose(time_s, tick * 0.002, rel_tol=0, abs_tol=1e-9):
            raise ValueError("condition sample clock drifted")
        self.last_tick = tick
        if self.name == "observation_delay":
            self.history.append((tick, self.payload(plant)))

    def deliver(self, plant, tick, time_s):
        seeded = self.name == "observation_delay" and tick < 10
        if self.name != "observation_delay":
            timed = self.information.deliver(self.payload(plant), time_s, time_s)
        elif seeded:
            # Initial reset is explicitly available at boot; no negative-time samples.
            timed = TimedObservation(self.initial, 0.0, 0.0, time_s)
        else:
            sample_tick, payload = self.history[0]
            if sample_tick != tick - 10:
                raise ValueError("delayed sample missing")
            timed = self.information.deliver(payload, sample_tick * 0.002, time_s)
            self.delayed_updates += 1
        controller_payload = timed.payload
        if isinstance(controller_payload, WholeBodyState):
            # Native planning uses the CURRENT control clock with old measurements.
            # The original sample time remains in the immutable TimedObservation.
            controller_payload = replace(controller_payload, time_s=time_s)
        metadata = {
            "format": "normalized-named-state-v1",
            "initial_state_seed": seeded,
            "source_tick": int(round(timed.sample_time_s / 0.002)),
            "source_payload_sha256": payload_digest(timed.payload),
            "controller_payload_sha256": payload_digest(controller_payload),
            "controller_payload_time_s": (
                controller_payload.time_s
                if isinstance(controller_payload, WholeBodyState)
                else None
            ),
        }
        return timed, controller_payload, metadata

    def before_step(self, plant, tick):
        record = {"id": self.name, "tick": tick}
        if self.name == "sliding_friction":
            if tick >= 3000 and not self.switched:
                plant.model.geom_friction[list(self.feet), 0] = 0.3
                plant.mj.mj_forward(plant.model, plant.data)
                self.switched = True
                from .model import physical_fingerprint

                self.after_fingerprint = physical_fingerprint(plant.model)
            contacts = []
            for c in plant.data.contact:
                pair = {int(c.geom1), int(c.geom2)}
                if c.efc_address < 0 or plant.floor not in pair:
                    continue
                foot = next(iter(pair - {plant.floor}), None)
                if foot not in self.feet:
                    continue
                expected = [0.3 if self.switched else 0.8] * 2 + [0.02, 0.01, 0.01]
                if c.dim != 6 or not np.allclose(
                    c.friction, expected, rtol=0, atol=1e-12
                ):
                    raise ValueError("actual contact friction did not match condition")
                contacts.append(
                    {
                        "foot_geom": foot,
                        "foot_name": plant.feet[foot],
                        "friction": c.friction.tolist(),
                    }
                )
            if self.switched:
                self.contact_samples += len(contacts)
            record.update(switched=self.switched, actual_contacts=contacts)
        elif self.name == "lateral_force":
            if not np.array_equal(plant.data.xfrc_applied[self.body], self.last_force):
                raise ValueError("owned force row changed outside hook")
            other = plant.data.xfrc_applied.copy()
            other[self.body] = 0
            if np.any(other):
                raise ValueError("unexpected external force outside owned base")
            force = np.zeros(6)
            if 3000 <= tick < 3100:
                force[1] = 50.0
                self.force_ticks += 1
            plant.data.xfrc_applied[self.body] = force
            self.last_force = force
            record["applied_world_wrench"] = plant.data.xfrc_applied[self.body].tolist()
        return record

    def complete(self):
        if self.name == "lateral_force" and self.force_ticks != 100:
            raise ValueError("force interval incomplete")
        if self.name == "observation_delay" and self.delayed_updates == 0:
            raise ValueError("no delayed controller sample observed")
        result = {
            "id": self.name,
            "changed_contact_samples": self.contact_samples,
            "force_ticks": self.force_ticks,
            "nominal_applied_impulse_Ns": self.force_ticks * 0.002 * 50.0,
            "delayed_updates": self.delayed_updates,
        }
        if self.name == "sliding_friction":
            result.update(
                physical_sha256_before=self.before_fingerprint,
                physical_sha256_after=self.after_fingerprint,
                private_controller_model_changed=False,
            )
        return result

    def finish(self, plant):
        if self.name == "lateral_force":
            plant.data.xfrc_applied[self.body] = 0
