import unittest
import numpy as np
from .clock import TimingSpec
from .contracts import InformationSpec, POLICY_JOINTS, Proprioception, WholeBodyState


class InformationAndTimingSpecTest(unittest.TestCase):
    def proprio(self):
        return Proprioception(
            POLICY_JOINTS,
            np.zeros(12),
            np.zeros(12),
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.zeros(3),
        )

    def test_information_latency_age_and_model_access(self):
        p = self.proprio()
        spec = InformationSpec("proprioceptive", "none", latency_s=0.02)
        packet = spec.deliver(p, 1.0, 1.05)
        self.assertAlmostEqual(packet.available_time_s, 1.02)
        self.assertAlmostEqual(packet.age_s, 0.05)
        with self.assertRaisesRegex(ValueError, "not yet available"):
            spec.deliver(p, 1.0, 1.01)
        whole = WholeBodyState(p, [0, 0, 0], [0, 0, 0], 2.0)
        spec = InformationSpec("whole_body_state", "evaluation_model")
        self.assertIs(spec.deliver(whole, 2.0, 2.0).payload, whole)
        with self.assertRaises(ValueError):
            spec.deliver(p, 2.0, 2.0)

    def test_information_rejects_undeclared_semantics(self):
        with self.assertRaises(ValueError):
            InformationSpec("proprioceptive", "secret_model")
        with self.assertRaises(ValueError):
            InformationSpec("proprioceptive", "none", noise_model="gaussian")

    def test_timing_offline_and_realtime(self):
        offline = TimingSpec(0.002, 0.02)
        self.assertEqual(offline.decimation, 10)
        self.assertEqual(offline.solve_outcome(100.0), "unbounded_offline")
        realtime = TimingSpec(0.002, 0.02, "real_time", 0.01, "hold_previous")
        self.assertEqual(realtime.solve_outcome(0.009), "fresh_action")
        self.assertEqual(realtime.solve_outcome(0.011), "hold_previous")
        self.assertTrue(realtime.clock().observe(0, 0.0))

    def test_timing_rejects_fake_realtime(self):
        bad = (
            dict(physics_period_s=0.003, control_period_s=0.02),
            dict(
                physics_period_s=0.002,
                control_period_s=0.02,
                compute_semantics="real_time",
            ),
            dict(
                physics_period_s=0.002,
                control_period_s=0.02,
                compute_semantics="real_time",
                solve_budget_s=0.03,
                overrun_behavior="fail",
            ),
            dict(physics_period_s=0.002, control_period_s=0.02, solve_budget_s=0.01),
        )
        for kwargs in bad:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                TimingSpec(**kwargs)


if __name__ == "__main__":
    unittest.main()
