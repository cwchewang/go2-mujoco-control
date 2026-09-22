"""One bounded episode. No CLI; the guarded launcher owns real-plant access."""

import math
import time
import numpy as np
from .clock import ControlClock
from .contracts import Proprioception
from .model import joint_layout


def command_at(protocol, tick):
    start, ramp = protocol["zero_command_ticks"], protocol["ramp_ticks"]
    scale = min(1.0, max(0.0, (tick - start) / ramp))
    return np.asarray(protocol["command"]) * scale


def safety(row, protocol):
    qpos, qvel = np.asarray(row["qpos"]), np.asarray(row["qvel"])
    if not np.isfinite(qpos).all() or not np.isfinite(qvel).all():
        return "nonfinite"
    if abs(np.linalg.norm(qpos[3:7]) - 1) > 1e-6:
        return "orientation"
    if row["warning_count"]:
        return "physics_warning"
    if row["forbidden_contacts"]:
        return "nonfoot_contact"
    t = protocol["thresholds"]
    tilt = math.acos(float(np.clip(1 - 2 * (qpos[4] ** 2 + qpos[5] ** 2), -1, 1)))
    if not t["height_min_m"] <= qpos[2] <= t["height_max_m"] or tilt > t["tilt_max_rad"]:
        return "posture"
    if abs(qpos[1] - row["initial_y"]) > t["lateral_max_m"]:
        return "lateral"
    return None


class MujocoPlant:
    def __init__(self, scene):
        import mujoco
        self.mj = mujoco
        self.model = mujoco.MjModel.from_xml_path(str(scene))
        self.data = mujoco.MjData(self.model)
        self.names, self.qadr, self.vadr = joint_layout(self.model)
        self.lower, self.upper = self.model.actuator_ctrlrange.T.copy()
        self.floor = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, "phase2_floor")
        self.feet = {
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, n): n
            for n in ("FR", "FL", "RR", "RL")
        }
        if self.floor < 0 or -1 in self.feet or len(self.feet) != 4:
            raise ValueError("flat support geometry missing")
        self.reset()

    def reset(self):
        key = self.mj.mj_name2id(self.model, self.mj.mjtObj.mjOBJ_KEY, "home")
        if key != 0:
            raise ValueError("home key mismatch")
        self.mj.mj_resetDataKeyframe(self.model, self.data, key)
        self.data.qvel[:] = 0
        self.data.ctrl[:] = 0  # home XML ctrl is not a torque command
        self.mj.mj_forward(self.model, self.data)
        self.steps = 0
        self.initial_y = float(self.data.qpos[1])

    def observe(self):
        d = self.data
        return Proprioception(self.names, d.qpos[self.qadr], d.qvel[self.vadr], d.qpos[3:7], d.qvel[3:6])

    def snapshot(self, tick):
        d = self.data
        supports, forbidden = set(), []
        for c in d.contact:
            if c.efc_address < 0:
                continue
            pair = {int(c.geom1), int(c.geom2)}
            if self.floor in pair and len(pair) == 2:
                other = next(iter(pair - {self.floor}))
                if other in self.feet:
                    supports.add(self.feet[other])
                else:
                    forbidden.append(sorted(pair))
            elif pair & set(self.feet) or any(self.model.geom_bodyid[g] != 0 for g in pair):
                forbidden.append(sorted(pair))
        return {
            "tick": tick, "sim_time_s": float(d.time),
            "qpos": d.qpos.tolist(), "qvel": d.qvel.tolist(),
            "initial_y": self.initial_y, "supports": sorted(supports),
            "forbidden_contacts": forbidden,
            "warning_count": int(sum(w.number for w in d.warning)),
        }

    def step(self, ctrl):
        self.data.ctrl[:] = ctrl
        self.mj.mj_step(self.model, self.data)
        self.steps += 1
        # mj_step's derived contacts precede its integrated qpos. Align all
        # logged state/contact fields at the endpoint before evaluating safety.
        self.mj.mj_forward(self.model, self.data)


def episode(plant, policy, protocol, emit, consume, *, monotonic=time.monotonic):
    """Capture t=0 through terminal state. PD is recomputed EVERY physics tick.

    emit must persist evidence; consume durably reserves the scientific attempt
    before the first post-handoff state/action row. No recovery/retry here.
    """
    plant.reset()
    policy.reset()
    clock = ControlClock(protocol["physics_period_s"], protocol["control_period_s"])
    start = monotonic()
    target = None
    consumed = False
    for tick in range(protocol["horizon_ticks"] + 1):
        row = plant.snapshot(tick)
        update = clock.observe(tick, row["sim_time_s"])
        row["failure"] = safety(row, protocol)
        row["action"] = None
        row["policy_wall_s"] = None
        row["command"] = command_at(protocol, tick).tolist()
        row["wall_time_s"] = monotonic() - start
        if row["wall_time_s"] >= protocol["wall_timeout_s"]:
            row["failure"] = row["failure"] or "wall_timeout"
        if tick == protocol["horizon_ticks"] or row["failure"]:
            row["terminal_reason"] = row["failure"] or "horizon"
            emit(row)
            return {"terminal_reason": row["terminal_reason"], "steps": tick, "attempt_consumed": consumed}
        obs = plant.observe()
        if update:
            before = monotonic()
            target = policy.act(obs, row["command"])
            row["policy_wall_s"] = monotonic() - before
        action = target.resolve(obs, plant.lower, plant.upper, plant.names)
        row["action"] = {k: v.tolist() for k, v in action.items()}
        row["target"] = {
            "joint_names": list(target.joint_names),
            **{k: getattr(target, k).tolist() for k in ("feedforward", "position_target", "velocity_target", "kp", "kd")},
        }
        row["terminal_reason"] = None
        if not consumed:
            consume()
            consumed = True
        emit(row)
        plant.step(action["ctrl"])
    raise AssertionError("unreachable episode exit")
