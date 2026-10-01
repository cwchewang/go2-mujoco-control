import json
import unittest
import numpy as np
from .evaluator import CanonicalEvaluator
from .specs import TaskSpec, TaskThresholds, specs_from_legacy_protocol


class EvaluatorContractTest(unittest.TestCase):
    def task(self, **overrides):
        v = dict(
            task_id="test",
            command_target=np.array([1.0, 0.0, 0.0]),
            command_frame="controller_native",
            zero_command_ticks=0,
            ramp_ticks=1,
            horizon_ticks=2,
            measurement_start_tick=1,
            support_semantics="traverse",
            required_supports=(),
            stop_on=(
                "nonfinite",
                "orientation",
                "physics_warning",
                "nonfoot_contact",
                "posture",
                "lateral",
            ),
            thresholds=TaskThresholds(1.0, 0.1, 0.2, 0.6, 0.16, 0.55),
        )
        v.update(overrides)
        return TaskSpec(**v)

    def row(self, tick, x, vx, **overrides):
        r = {
            "tick": tick,
            "sim_time_s": tick * 0.002,
            "qpos": [x, 0.0, 0.27, 1.0, 0.0, 0.0, 0.0] + [0.0] * 12,
            "qvel": [vx, 0.0, 0.0] + [0.0] * 15,
            "warning_count": 0,
            "forbidden_contacts": [],
            "supports": ["FL", "FR", "RL", "RR"],
            "failure": "controller_label_ignored",
            "terminal_reason": "controller_label_ignored",
        }
        r.update(overrides)
        return r

    def test_raw_evidence_drives_success_not_controller_labels(self):
        rows = [self.row(0, 0, 0), self.row(1, 0.6, 1), self.row(2, 1.2, 1)]
        result = CanonicalEvaluator(self.task(), 0.002).evaluate(rows)
        self.assertEqual((result.verdict, result.terminal_reason), ("PASS", "horizon"))
        self.assertIsNone(result.first_failure)
        self.assertAlmostEqual(result.progress_m, 1.2)
        self.assertAlmostEqual(result.vx_mae_mps, 0.0)
        json.dumps(result.as_dict())

    def test_physical_failure_is_recomputed_and_terminal(self):
        rows = [self.row(0, 0, 0), self.row(1, 0.1, 1, forbidden_contacts=[[0, 5]])]
        result = CanonicalEvaluator(self.task(), 0.002).evaluate(rows)
        self.assertEqual(result.first_failure, {"tick": 1, "reason": "nonfoot_contact"})
        self.assertEqual(result.verdict, "FAIL")
        with self.assertRaisesRegex(ValueError, "continues after physical failure"):
            CanonicalEvaluator(self.task(), 0.002).evaluate(
                rows + [self.row(2, 0.2, 1)]
            )

    def test_nonfinite_is_classified_not_trusted_to_controller(self):
        q = [0.1, 0, 0.27, 1, 0, 0, 0] + [0] * 12
        q[0] = float("nan")
        result = CanonicalEvaluator(self.task(), 0.002).evaluate(
            [self.row(0, 0, 0, qpos=q)]
        )
        self.assertEqual(result.first_failure, {"tick": 0, "reason": "nonfinite"})
        self.assertIsNone(result.progress_m)

    def test_mandatory_support_is_outcome_semantics(self):
        task = self.task(
            support_semantics="mandatory_support", required_supports=("top",)
        )
        rows = [
            self.row(0, 0, 0, supports=[]),
            self.row(1, 0.6, 1, supports=[]),
            self.row(2, 1.2, 1, supports=[]),
        ]
        result = CanonicalEvaluator(task, 0.002).evaluate(rows)
        self.assertEqual((result.verdict, result.missing_supports), ("FAIL", ("top",)))

    def test_legacy_protocol_mapping_preserves_schedule(self):
        from pathlib import Path

        p = json.loads(
            (Path(__file__).parent / "protocols/rl_flat_v1.json").read_text()
        )
        task, scenario = specs_from_legacy_protocol(p)
        self.assertEqual(task.task_id, p["id"])
        self.assertEqual(task.command_frame, "controller_native")
        self.assertEqual(scenario.scene, p["scene"])
        self.assertEqual(
            [task.command_at(t)[0] for t in (0, 499, 500, 750, 1000)],
            [0, 0, 0, 0.075, 0.15],
        )


if __name__ == "__main__":
    unittest.main()
