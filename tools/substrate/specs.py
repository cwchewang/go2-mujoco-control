"""Explicit task/scenario semantics for prospective shared evaluation."""

from dataclasses import dataclass
import re
import numpy as np
from .contracts import vector
from .model import physical_fingerprint


@dataclass(frozen=True)
class TaskThresholds:
    progress_min_m: float
    vx_mae_max_mps: float
    lateral_max_m: float
    tilt_max_rad: float
    height_min_m: float
    height_max_m: float

    def __post_init__(self):
        for n in self.__dataclass_fields__:
            v = getattr(self, n)
            if (
                isinstance(v, bool)
                or not isinstance(v, (int, float, np.integer, np.floating))
                or not np.isfinite(v)
                or v < 0
            ):
                raise ValueError("task thresholds must be finite nonnegative numbers")
            object.__setattr__(self, n, float(v))
        if self.height_min_m >= self.height_max_m:
            raise ValueError("height threshold range is empty")


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    command_target: np.ndarray
    command_frame: str
    zero_command_ticks: int
    ramp_ticks: int
    horizon_ticks: int
    measurement_start_tick: int
    support_semantics: str
    required_supports: tuple
    stop_on: tuple
    thresholds: TaskThresholds
    longitudinal_metric: str = "world_vx"

    def __post_init__(self):
        if not isinstance(self.task_id, str) or not self.task_id:
            raise ValueError("task_id required")
        command = vector(self.command_target, 3, "command_target")
        object.__setattr__(
            self, "command_target", np.frombuffer(command.tobytes(), dtype=np.float64)
        )
        if self.command_frame not in ("controller_native", "world", "body"):
            raise ValueError("unsupported command frame")
        for n in (
            "zero_command_ticks",
            "ramp_ticks",
            "horizon_ticks",
            "measurement_start_tick",
        ):
            if type(getattr(self, n)) is not int or getattr(self, n) < 0:
                raise ValueError("task ticks must be nonnegative integers")
        if self.ramp_ticks < 1 or self.measurement_start_tick > self.horizon_ticks:
            raise ValueError("invalid task timing")
        if self.support_semantics not in ("traverse", "mandatory_support"):
            raise ValueError("unsupported support semantics")
        supports = tuple(self.required_supports)
        if any(type(x) is not str or not x for x in supports) or len(
            set(supports)
        ) != len(supports):
            raise ValueError("required supports must be unique names")
        if self.support_semantics == "mandatory_support" and not supports:
            raise ValueError("mandatory support task requires supports")
        object.__setattr__(self, "required_supports", supports)
        stops = tuple(self.stop_on)
        if any(type(x) is not str or not x for x in stops) or len(set(stops)) != len(
            stops
        ):
            raise ValueError("stop_on must contain unique names")
        object.__setattr__(self, "stop_on", stops)
        if not isinstance(self.thresholds, TaskThresholds):
            raise ValueError("thresholds must be TaskThresholds")
        if self.longitudinal_metric not in ("world_vx", "body_vx"):
            raise ValueError("unsupported longitudinal metric")
        if self.command_frame == "world" and self.longitudinal_metric != "world_vx":
            raise ValueError("world-frame command requires world_vx metric")
        if self.command_frame == "body" and self.longitudinal_metric != "body_vx":
            raise ValueError("body-frame command requires body_vx metric")

    def command_at(self, tick):
        if type(tick) is not int or tick < 0:
            raise ValueError("tick must be nonnegative")
        scale = min(1.0, max(0.0, (tick - self.zero_command_ticks) / self.ramp_ticks))
        return self.command_target * scale


@dataclass(frozen=True)
class ScenarioIntervention:
    geom_names: tuple
    attribute: str
    expected: object

    def __post_init__(self):
        names = tuple(self.geom_names)
        if (
            len(names) != 2
            or len(set(names)) != 2
            or any(type(x) is not str or not x for x in names)
        ):
            raise ValueError("effective contact verification requires two geom names")
        object.__setattr__(self, "geom_names", names)
        if self.attribute == "contact_friction":
            value = vector(self.expected, 5, "effective contact friction")
            object.__setattr__(
                self, "expected", np.frombuffer(value.tobytes(), dtype=np.float64)
            )
        elif self.attribute == "contact_dim":
            if type(self.expected) is not int or self.expected not in (1, 3, 4, 6):
                raise ValueError("invalid effective contact dim")
        else:
            raise ValueError("unsupported effective contact attribute")

    def verify(self, model, data):
        import mujoco

        ids = []
        for name in self.geom_names:
            gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)
            if gid < 0:
                raise ValueError("contact intervention geom missing")
            ids.append(gid)
        target = set(ids)
        contacts = [c for c in data.contact if {int(c.geom1), int(c.geom2)} == target]
        if not contacts:
            raise ValueError("effective contact pair is not active")
        for contact in contacts:
            if self.attribute == "contact_friction":
                if not np.allclose(contact.friction, self.expected, rtol=0, atol=1e-12):
                    raise ValueError("effective contact friction mismatch")
            elif int(contact.dim) != self.expected:
                raise ValueError("effective contact dim mismatch")
        return True


@dataclass(frozen=True)
class ScenarioSpec:
    scene: str
    reset: str
    physical_sha256: str | None = None
    interventions: tuple = ()

    def __post_init__(self):
        if (
            not isinstance(self.scene, str)
            or not self.scene
            or self.scene.startswith("/")
            or ".." in self.scene.split("/")
        ):
            raise ValueError("scene must be repository-relative")
        if not isinstance(self.reset, str) or not self.reset:
            raise ValueError("reset required")
        if self.physical_sha256 is not None and (
            not isinstance(self.physical_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", self.physical_sha256)
        ):
            raise ValueError("invalid physical fingerprint")
        items = tuple(self.interventions)
        if any(not isinstance(x, ScenarioIntervention) for x in items):
            raise ValueError("invalid intervention")
        object.__setattr__(self, "interventions", items)

    def verify_model(self, model, data=None):
        if (
            self.physical_sha256 is not None
            and physical_fingerprint(model) != self.physical_sha256
        ):
            raise ValueError("scenario physical fingerprint mismatch")
        if self.interventions and data is None:
            raise ValueError("contact data required to verify effective interventions")
        for item in self.interventions:
            item.verify(model, data)
        return True


def specs_from_legacy_protocol(p):
    task = TaskSpec(
        task_id=p["id"],
        command_target=p["command"],
        command_frame="controller_native",
        zero_command_ticks=p["zero_command_ticks"],
        ramp_ticks=p["ramp_ticks"],
        horizon_ticks=p["horizon_ticks"],
        measurement_start_tick=p["measurement_start_tick"],
        support_semantics=p["support_semantics"],
        required_supports=tuple(p.get("required_supports", ())),
        stop_on=tuple(p["stop_on"]),
        thresholds=TaskThresholds(**p["thresholds"]),
    )
    return task, ScenarioSpec(scene=p["scene"], reset=p["reset"])
