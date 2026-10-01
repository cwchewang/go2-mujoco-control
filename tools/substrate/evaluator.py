"""Controller-independent physical oracle for prospective shared evaluation."""

from dataclasses import dataclass
import math
import numpy as np
from .contracts import vector
from .specs import TaskSpec


@dataclass(frozen=True)
class EvaluationResult:
    verdict: str
    terminal_reason: str
    first_failure: dict | None
    progress_m: float | None
    vx_mae_mps: float | None
    missing_supports: tuple
    frames: int

    def as_dict(self):
        return {
            "verdict": self.verdict,
            "terminal_reason": self.terminal_reason,
            "first_failure": self.first_failure,
            "progress_m": self.progress_m,
            "vx_mae_mps": self.vx_mae_mps,
            "missing_supports": list(self.missing_supports),
            "frames": self.frames,
        }


class CanonicalEvaluator:
    def __init__(self, task: TaskSpec, physics_period_s: float):
        self.task = task
        if (
            type(physics_period_s) not in (float, int)
            or isinstance(physics_period_s, bool)
            or not math.isfinite(physics_period_s)
            or physics_period_s <= 0
        ):
            raise ValueError("physics period must be finite positive")
        self.physics_period_s = float(physics_period_s)

    def failure(self, row, initial_y):
        qpos = np.asarray(row["qpos"], dtype=np.float64)
        qvel = np.asarray(row["qvel"], dtype=np.float64)
        if qpos.shape != (19,) or qvel.shape != (18,):
            raise ValueError("invalid raw state shape")
        if not np.isfinite(qpos).all() or not np.isfinite(qvel).all():
            return "nonfinite"
        if not math.isclose(float(np.dot(qpos[3:7], qpos[3:7])), 1.0, abs_tol=2e-6):
            return "orientation" if "orientation" in self.task.stop_on else None
        if type(row["warning_count"]) is not int or row["warning_count"] < 0:
            raise ValueError("invalid warning count")
        if row["warning_count"] and "physics_warning" in self.task.stop_on:
            return "physics_warning"
        forbidden = row["forbidden_contacts"]
        if not isinstance(forbidden, list):
            raise ValueError("forbidden_contacts must be a list")
        if forbidden and "nonfoot_contact" in self.task.stop_on:
            return "nonfoot_contact"
        t = self.task.thresholds
        tilt = math.acos(float(np.clip(1 - 2 * (qpos[4] ** 2 + qpos[5] ** 2), -1, 1)))
        if (
            not t.height_min_m <= qpos[2] <= t.height_max_m or tilt > t.tilt_max_rad
        ) and "posture" in self.task.stop_on:
            return "posture"
        if (
            abs(float(qpos[1]) - initial_y) > t.lateral_max_m
            and "lateral" in self.task.stop_on
        ):
            return "lateral"
        return None

    def evaluate(self, rows):
        if not rows:
            raise ValueError("empty evaluation evidence")
        initial = np.asarray(rows[0]["qpos"], dtype=np.float64)
        if initial.shape != (19,):
            raise ValueError("invalid initial qpos shape")
        initial_x, initial_y = float(initial[0]), float(initial[1])
        first_failure = None
        errors = []
        supports = set()
        last_tick = -1
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError("evaluation frame must be an object")
            tick = row["tick"]
            if type(tick) is not int or tick != index:
                raise ValueError("missing, duplicate or reordered evaluation tick")
            expected = tick * self.physics_period_s
            sim = row["sim_time_s"]
            if (
                type(sim) not in (float, int)
                or isinstance(sim, bool)
                or not math.isfinite(sim)
                or not math.isclose(sim, expected, rel_tol=0, abs_tol=1e-9)
            ):
                raise ValueError("evaluation clock mismatch")
            reason = self.failure(row, initial_y)
            qvel = None if reason == "nonfinite" else vector(row["qvel"], 18, "qvel")
            if first_failure is None and reason is not None:
                first_failure = {"tick": tick, "reason": reason}
            raw_supports = row.get("supports", [])
            if not isinstance(raw_supports, list) or any(
                type(x) is not str or not x for x in raw_supports
            ):
                raise ValueError("supports must be a list of names")
            supports.update(raw_supports)
            if tick >= self.task.measurement_start_tick and qvel is not None:
                errors.append(
                    abs(float(qvel[0]) - float(self.task.command_at(tick)[0]))
                )
            last_tick = tick
            if first_failure is not None:
                if index != len(rows) - 1:
                    raise ValueError("evidence continues after physical failure")
                break
        terminal = (
            first_failure["reason"]
            if first_failure is not None
            else (
                "horizon"
                if last_tick == self.task.horizon_ticks
                else "incomplete_evidence"
            )
        )
        final = np.asarray(rows[-1]["qpos"], dtype=np.float64)
        progress = (
            float(final[0] - initial_x)
            if final.shape == (19,) and np.isfinite(final).all()
            else None
        )
        mae = float(np.mean(errors)) if errors else None
        missing = (
            tuple(sorted(set(self.task.required_supports) - supports))
            if self.task.support_semantics == "mandatory_support"
            else ()
        )
        t = self.task.thresholds
        passed = (
            first_failure is None
            and terminal == "horizon"
            and progress is not None
            and progress >= t.progress_min_m
            and mae is not None
            and mae <= t.vx_mae_max_mps
            and not missing
        )
        return EvaluationResult(
            "PASS" if passed else "FAIL",
            terminal,
            first_failure,
            progress,
            mae,
            missing,
            len(rows),
        )
