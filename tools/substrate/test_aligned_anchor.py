import copy
import unittest

import numpy as np

from .aligned_anchor import LOCK, load_anchor, validate_anchor
from .contracts import (
    POLICY_JOINTS,
    ControllerAdapter,
    Proprioception,
    ProprioceptivePolicyAdapter,
    TorqueCommand,
)
from .integrity import strict_json


class FakePolicy:
    def reset(self):
        self.reset_count = getattr(self, "reset_count", 0) + 1

    def act(self, observation, command):
        return TorqueCommand(
            POLICY_JOINTS,
            np.zeros(12),
            np.zeros(12),
            np.zeros(12),
            np.zeros(12),
            np.zeros(12),
        )


class AlignedAnchorTest(unittest.TestCase):
    def obs(self):
        return Proprioception(
            POLICY_JOINTS,
            np.zeros(12),
            np.zeros(12),
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.zeros(3),
        )

    def test_rl_adapter_satisfies_shared_controller_protocol(self):
        policy = FakePolicy()
        adapter = ProprioceptivePolicyAdapter(policy)
        self.assertIsInstance(adapter, ControllerAdapter)
        obs = self.obs()
        adapter.reset(obs)
        result = adapter.step(obs, [1.0, 0.0, 0.0])
        self.assertIsInstance(result, TorqueCommand)
        self.assertEqual(policy.reset_count, 1)
        self.assertEqual(adapter.diagnostics()["information_regime"], "proprioceptive")

    def test_anchor_is_frozen_and_physics_disabled(self):
        anchor = load_anchor()
        self.assertFalse(anchor["raw"]["physics_step_authorized"])
        self.assertEqual(anchor["raw"]["scientific_attempts_authorized"], 0)
        self.assertEqual(anchor["task"].command_frame, "body")
        self.assertEqual(anchor["task"].longitudinal_metric, "body_vx")
        self.assertEqual(anchor["task"].horizon_ticks, 500)
        self.assertEqual(anchor["controllers"]["rl"]["timing"].feedback_period_s, 0.02)
        self.assertEqual(
            anchor["controllers"]["mjpc"]["timing"].feedback_period_s, 0.002
        )

    def test_authorization_or_source_drift_fails_closed(self):
        anchor = load_anchor()
        lock = strict_json(LOCK.read_text())

        raw = copy.deepcopy(anchor["raw"])
        raw["physics_step_authorized"] = True
        with self.assertRaisesRegex(ValueError, "must not authorize physics"):
            validate_anchor(raw, lock)

        raw = copy.deepcopy(anchor["raw"])
        raw["scientific_attempts_authorized"] = False
        with self.assertRaisesRegex(ValueError, "scientific attempts"):
            validate_anchor(raw, lock)

        raw = copy.deepcopy(anchor["raw"])
        raw["task"]["horizon_ticks"] = 501
        with self.assertRaisesRegex(ValueError, "task definition"):
            validate_anchor(raw, lock)

        raw = copy.deepcopy(anchor["raw"])
        raw["controllers"]["rl"]["source_commit"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "RL source commit"):
            validate_anchor(raw, lock)

        raw = copy.deepcopy(anchor["raw"])
        raw["controllers"]["mjpc"]["timing"]["compute_semantics"] = "real_time"
        raw["controllers"]["mjpc"]["timing"]["solve_budget_s"] = 0.02
        raw["controllers"]["mjpc"]["timing"]["overrun_behavior"] = "fail"
        with self.assertRaisesRegex(ValueError, "offline_unbounded"):
            validate_anchor(raw, lock)


if __name__ == "__main__":
    unittest.main()
