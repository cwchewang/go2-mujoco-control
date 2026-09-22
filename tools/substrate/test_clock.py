import unittest
from .clock import ControlClock


class ClockContract(unittest.TestCase):
    def test_exact_50_hz_from_500_hz(self):
        clock = ControlClock(0.002, 0.02)
        due = [tick for tick in range(1000) if clock.observe(tick, tick * 0.002)]
        self.assertEqual(due, list(range(0, 1000, 10)))

    def test_reset_and_duplicate_gap_rejection(self):
        clock = ControlClock(0.002, 0.02)
        self.assertTrue(clock.observe(0, 0.0))
        for tick in (0, 2, True):
            with self.assertRaises(ValueError):
                clock.observe(tick, 0.002)
        clock.reset()
        self.assertTrue(clock.observe(0, 0.0))

    def test_invalid_clock_periods(self):
        for physics, control in (
            (0, 0.02),
            (0.003, 0.02),
            (0.002, True),
            (0.002, float("nan")),
        ):
            with self.assertRaises(ValueError):
                ControlClock(physics, control)

    def test_time_drift_rejected_before_advancing(self):
        clock = ControlClock(0.002, 0.02)
        clock.observe(0, 0.0)
        with self.assertRaises(ValueError):
            clock.observe(1, 0.0021)
        self.assertFalse(clock.observe(1, 0.002))


if __name__ == "__main__":
    unittest.main()
