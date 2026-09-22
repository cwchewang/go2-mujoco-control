"""Exact discrete cadence for future runners; no simulation or wall-clock pacing."""

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
