"""Named boundaries; no simulator handles are exposed to proprioceptive policies."""

from dataclasses import dataclass
import json
from typing import Protocol, runtime_checkable
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
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf":
        raise ValueError(f"{name}: expected numeric values, not booleans/strings")
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f"{name}: expected {size} finite values")
    return result.copy()


def reorder(values, source, target):
    source, target = tuple(source), tuple(target)
    if any(not isinstance(name, str) or not name for name in source + target):
        raise ValueError("joint names must be nonempty strings")
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

    def __post_init__(self):
        object.__setattr__(self, "joint_names", tuple(self.joint_names))
        for name, size in (
            ("position", 12),
            ("velocity", 12),
            ("quaternion_wxyz", 4),
            ("angular_velocity_body", 3),
        ):
            value = vector(getattr(self, name), size, name)
            object.__setattr__(
                self, name, np.frombuffer(value.tobytes(), dtype=np.float64)
            )

    def validate(self):
        reorder(self.position, self.joint_names, POLICY_JOINTS)
        vector(self.velocity, 12, "joint velocity")
        q = vector(self.quaternion_wxyz, 4, "quaternion")
        if abs(np.linalg.norm(q) - 1) > 1e-6:
            raise ValueError("quaternion must be normalized")
        vector(self.angular_velocity_body, 3, "angular velocity")


@dataclass(frozen=True)
class WholeBodyState:
    """Explicit full-state information packet for model-based controllers."""

    proprioception: Proprioception
    base_position_world: np.ndarray
    linear_velocity_world: np.ndarray
    time_s: float

    def __post_init__(self):
        self.proprioception.validate()
        for name in ("base_position_world", "linear_velocity_world"):
            value = vector(getattr(self, name), 3, name)
            object.__setattr__(
                self, name, np.frombuffer(value.tobytes(), dtype=np.float64)
            )
        if (
            isinstance(self.time_s, (bool, np.bool_))
            or not isinstance(self.time_s, (int, float, np.integer, np.floating))
            or not np.isfinite(self.time_s)
            or self.time_s < 0
        ):
            raise ValueError("time_s must be a finite nonnegative scalar")
        object.__setattr__(self, "time_s", float(self.time_s))

    def qpos(self, target_joint_names):
        p = self.proprioception
        return np.concatenate(
            (
                self.base_position_world,
                p.quaternion_wxyz,
                reorder(p.position, p.joint_names, target_joint_names),
            )
        )

    def qvel(self, target_joint_names):
        p = self.proprioception
        return np.concatenate(
            (
                self.linear_velocity_world,
                p.angular_velocity_body,
                reorder(p.velocity, p.joint_names, target_joint_names),
            )
        )


@dataclass(frozen=True)
class TorqueCommand:
    joint_names: tuple
    feedforward: np.ndarray
    position_target: np.ndarray
    velocity_target: np.ndarray
    kp: np.ndarray
    kd: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "joint_names", tuple(self.joint_names))
        for name in ("feedforward", "position_target", "velocity_target", "kp", "kd"):
            value = vector(getattr(self, name), 12, name)
            object.__setattr__(
                self, name, np.frombuffer(value.tobytes(), dtype=np.float64)
            )

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


@dataclass(frozen=True)
class PositionPDActuatorSpec:
    """Source-controller position action semantics, independent of the evaluation plant."""

    joint_names: tuple
    position_lower: np.ndarray
    position_upper: np.ndarray
    kp: np.ndarray
    kd: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "joint_names", tuple(self.joint_names))
        if (
            len(self.joint_names) != 12
            or len(set(self.joint_names)) != 12
            or set(self.joint_names) != set(POLICY_JOINTS)
        ):
            raise ValueError("unexpected position-controller joint set")
        for name in ("position_lower", "position_upper", "kp", "kd"):
            value = vector(getattr(self, name), 12, name)
            object.__setattr__(
                self, name, np.frombuffer(value.tobytes(), dtype=np.float64)
            )
        if (self.position_lower >= self.position_upper).any():
            raise ValueError("invalid source position range")
        if (self.kp <= 0).any() or (self.kd < 0).any():
            raise ValueError("invalid source PD gain")

    def command(self, position_target):
        raw = vector(position_target, 12, "position target")
        clipped = np.clip(raw, self.position_lower, self.position_upper)
        return (
            TorqueCommand(
                self.joint_names,
                np.zeros(12),
                clipped,
                np.zeros(12),
                self.kp,
                self.kd,
            ),
            {
                "position_target_unclipped": raw,
                "position_target": clipped,
                "position_saturated": (raw < self.position_lower)
                | (raw > self.position_upper),
            },
        )


@runtime_checkable
class ControllerAdapter(Protocol):
    """Minimal evaluator-facing controller boundary."""

    def reset(self, observation): ...

    def step(self, observation, command): ...

    def diagnostics(self): ...


class PositionTargetControllerAdapter:
    """Wrap a controller whose native action is desired joint position."""

    def __init__(self, controller, actuator_spec, action_joint_names):
        self.controller = controller
        self.actuator_spec = actuator_spec
        self.action_joint_names = tuple(action_joint_names)
        reorder(np.zeros(12), self.action_joint_names, actuator_spec.joint_names)
        self._diagnostics = {}

    def reset(self, observation):
        observation.validate()
        reset = getattr(self.controller, "reset", None)
        if reset is not None:
            reset(observation)
        self._diagnostics = {}

    def step(self, observation, command):
        observation.validate()
        raw = vector(
            self.controller.step(observation, command), 12, "controller action"
        )
        ordered = reorder(raw, self.action_joint_names, self.actuator_spec.joint_names)
        torque, actuator = self.actuator_spec.command(ordered)
        self._diagnostics = {
            "source_action_joint_names": self.action_joint_names,
            "source_actuator_joint_names": self.actuator_spec.joint_names,
            **actuator,
        }
        return torque

    def diagnostics(self):
        result = {}
        diagnostics = getattr(self.controller, "diagnostics", None)
        if diagnostics is not None:
            value = diagnostics()
            if not isinstance(value, dict):
                raise ValueError("controller diagnostics must be a dict")
            try:
                json.dumps(value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "controller diagnostics must be JSON-serializable"
                ) from error
            result["controller"] = dict(value)
        result["adapter"] = {
            key: value.tolist() if isinstance(value, np.ndarray) else value
            for key, value in self._diagnostics.items()
        }
        return result
