"""Named boundaries; no simulator handles are exposed to proprioceptive policies."""

from dataclasses import dataclass
import numpy as np

POLICY_JOINTS = tuple(
    f"{leg}_{joint}_joint"
    for leg in ("FL", "FR", "RL", "RR")
    for joint in ("hip", "thigh", "calf")
)
MOTOR_JOINTS = tuple(
    f"{leg}_{joint}_joint"
    for leg in ("FR", "FL", "RR", "RL")
    for joint in ("hip", "thigh", "calf")
)


def vector(value, size, name):
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f"{name}: expected {size} finite values")
    return result.copy()


def reorder(values, source, target):
    source, target = tuple(source), tuple(target)
    if (
        len(set(source)) != len(source)
        or len(set(target)) != len(target)
        or set(source) != set(target)
    ):
        raise ValueError("joint names must be unique and describe the same joints")
    a = vector(values, len(source), "joint vector")
    return a[[source.index(name) for name in target]]


@dataclass(frozen=True)
class Proprioception:
    # MuJoCo free-joint rotational velocity is in the local body frame.
    joint_names: tuple
    position: np.ndarray
    velocity: np.ndarray
    quaternion_wxyz: np.ndarray
    angular_velocity_body: np.ndarray

    def validate(self):
        reorder(self.position, self.joint_names, POLICY_JOINTS)
        vector(self.velocity, 12, "joint velocity")
        q = vector(self.quaternion_wxyz, 4, "quaternion")
        if abs(np.linalg.norm(q) - 1) > 1e-6:
            raise ValueError("quaternion must be normalized")
        vector(self.angular_velocity_body, 3, "angular velocity")


@dataclass(frozen=True)
class TorqueCommand:
    joint_names: tuple
    feedforward: np.ndarray
    position_target: np.ndarray
    velocity_target: np.ndarray
    kp: np.ndarray
    kd: np.ndarray

    def resolve(self, observation, lower, upper, target_names):
        observation.validate()
        ff, qref, dqref, kp, kd = [
            reorder(v, self.joint_names, target_names)
            for v in (
                self.feedforward,
                self.position_target,
                self.velocity_target,
                self.kp,
                self.kd,
            )
        ]
        if (kp < 0).any() or (kd < 0).any():
            raise ValueError("negative PD gain")
        q = reorder(observation.position, observation.joint_names, target_names)
        dq = reorder(observation.velocity, observation.joint_names, target_names)
        lo, hi = vector(lower, 12, "lower"), vector(upper, 12, "upper")
        if (lo >= hi).any():
            raise ValueError("invalid actuator range")
        pd = kp * (qref - q) + kd * (dqref - dq)
        total = vector(ff + pd, 12, "total torque")
        return {
            "feedforward": ff,
            "pd": pd,
            "total_unclipped": total,
            "ctrl": np.clip(total, lo, hi),
            "saturated": (total < lo) | (total > hi),
        }
