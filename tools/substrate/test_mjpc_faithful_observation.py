"""No-native checks of scope, repeated inputs and review binding."""

import tempfile
import unittest
from pathlib import Path
from tools.substrate import mjpc_faithful_observation as observer
from tools.substrate.integrity import write_new


class FaithfulObserverTests(unittest.TestCase):
    def test_scope_is_four_original_calls_not_legacy_eight_call_batch(self):
        self.assertEqual(observer.DESIGN["variant"], "original")
        self.assertEqual(observer.DESIGN["replan_ticks"], [0, 10])
        self.assertEqual(observer.DESIGN["optimizer_calls_max"], 4)
        self.assertEqual(observer.DESIGN["private_reserved_max"], 16384)
        self.assertEqual(observer.DESIGN["canonical_integration_steps"], 0)

    def test_comparison_preserves_differences_and_rejects_unequal_inputs(self):
        rows = [
            {
                "input_sha256": str(i),
                "q_des": [0.0] * 12,
                "cost": 0.1,
                "replan_summary": None,
            }
            for i in range(11)
        ]
        import copy

        pair = [
            {"variant": "original", "repeat": i, "inputs": copy.deepcopy(rows)}
            for i in (1, 2)
        ]
        pair[1]["inputs"][10]["q_des"][2] = 0.01
        self.assertEqual(observer.compare(pair)[10]["max_abs_q_des_difference"], 0.01)
        pair[1]["inputs"][1]["input_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "external inputs"):
            observer.compare(pair)

    def test_current_independent_review_binding_rejects_stale_or_failed_verdict(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "review.json"
            preflight = {"head": "current", "packet_sha256": "packet"}
            value = {
                "role": "science",
                "verdict": "PASS",
                "head": "stale",
                "packet_sha256": "packet",
                "reviewer": "independent",
                "rationale": "reviewed",
            }
            write_new(p, value)
            with self.assertRaisesRegex(ValueError, "review binding"):
                observer.review(p, "science", preflight)


class PartialAccountingTests(unittest.TestCase):
    def test_reserved_unreturned_call_is_explicitly_incomplete(self):
        with tempfile.TemporaryDirectory() as folder:
            sub = Path(folder) / "original_repeat1"
            sub.mkdir()
            (sub / "optimizer-attempts.jsonl").write_text(
                '{"reserved_upper_bound":4096}\n'
            )
            result = observer.partial_accounting(folder)
            self.assertEqual(result["reserved_optimizer_calls"], 1)
            self.assertEqual(result["completed_optimizer_calls"], 0)
            self.assertEqual(result["private_reserved"], 4096)
            self.assertFalse(result["accounting_complete"])
