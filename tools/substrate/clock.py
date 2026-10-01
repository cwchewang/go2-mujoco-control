"""Exact discrete cadence for future runners; no simulation or wall-clock pacing."""

from dataclasses import dataclass
from fractions import Fraction
import math


class ControlClock:
    def __init__(self, physics_period_s, control_period_s):
        for value in (physics_period_s, control_period_s):
            if (
                type(value) not in (float, int)
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError("clock periods must be finite positive numbers")
        ratio = Fraction(str(control_period_s)) / Fraction(str(physics_period_s))
        if ratio.denominator != 1:
            raise ValueError(
                "control period must be an integer number of physics ticks"
            )
        self.decimation = int(ratio)
        self.period = float(physics_period_s)
        self.reset()

    def reset(self):
        self.next_tick = 0

    def observe(self, tick, sim_time_s):
        if type(tick) is not int or tick != self.next_tick:
            raise ValueError("duplicate, missing or out-of-order physics tick")
        if (
            type(sim_time_s) not in (float, int)
            or not math.isfinite(sim_time_s)
            or not math.isclose(sim_time_s, tick * self.period, rel_tol=0, abs_tol=1e-9)
        ):
            raise ValueError("simulation time does not match integer tick")
        self.next_tick += 1
        return tick % self.decimation == 0


@dataclass(frozen=True)
class TimingSpec:
    physics_period_s: float
    control_period_s: float
    compute_semantics: str = "offline_unbounded"
    solve_budget_s: float | None = None
    overrun_behavior: str = "not_applicable"
    feedback: str = "zero_order_hold"

    def __post_init__(self):
        for name in ("physics_period_s", "control_period_s"):
            value = getattr(self, name)
            if (
                type(value) not in (float, int)
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError("timing periods must be finite positive numbers")
            object.__setattr__(self, name, float(value))
        ratio = Fraction(str(self.control_period_s)) / Fraction(
            str(self.physics_period_s)
        )
        if ratio.denominator != 1:
            raise ValueError(
                "control period must be an integer number of physics ticks"
            )
        if self.feedback != "zero_order_hold":
            raise ValueError("unsupported feedback semantics")
        if self.compute_semantics == "offline_unbounded":
            if (
                self.solve_budget_s is not None
                or self.overrun_behavior != "not_applicable"
            ):
                raise ValueError(
                    "offline_unbounded cannot declare realtime budget/overrun"
                )
        elif self.compute_semantics == "real_time":
            if (
                type(self.solve_budget_s) not in (float, int)
                or isinstance(self.solve_budget_s, bool)
                or not math.isfinite(self.solve_budget_s)
                or self.solve_budget_s <= 0
                or self.solve_budget_s > self.control_period_s
            ):
                raise ValueError(
                    "real_time requires solve budget within control period"
                )
            if self.overrun_behavior not in ("hold_previous", "fail"):
                raise ValueError("real_time requires explicit overrun behavior")
            object.__setattr__(self, "solve_budget_s", float(self.solve_budget_s))
        else:
            raise ValueError("unsupported compute semantics")

    @property
    def decimation(self):
        return int(
            Fraction(str(self.control_period_s)) / Fraction(str(self.physics_period_s))
        )

    def solve_outcome(self, elapsed_s):
        if (
            type(elapsed_s) not in (float, int)
            or isinstance(elapsed_s, bool)
            or not math.isfinite(elapsed_s)
            or elapsed_s < 0
        ):
            raise ValueError("solve time must be finite nonnegative")
        if self.compute_semantics == "offline_unbounded":
            return "unbounded_offline"
        if elapsed_s <= self.solve_budget_s:
            return "fresh_action"
        return (
            "hold_previous"
            if self.overrun_behavior == "hold_previous"
            else "timeout_failure"
        )

    def clock(self):
        return ControlClock(self.physics_period_s, self.control_period_s)
