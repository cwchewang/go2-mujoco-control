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


class FailureAndLoaderTests(unittest.TestCase):
    def test_error_or_malformed_response_keeps_reservation_unverified(self):
        import json

        for response in (
            {"ok": False},
            {"ok": True, "replanned": True, "diagnostic": {}},
            {"ok": True, "replanned": True, "diagnostic": {"policy_id": True}},
        ):
            with tempfile.TemporaryDirectory() as folder:
                sub = Path(folder) / "original_repeat1"
                sub.mkdir()
                (sub / "optimizer-attempts.jsonl").write_text(
                    '{"reserved_upper_bound":4096}\n'
                )
                (sub / "native.jsonl").write_text(
                    json.dumps({"tick": 0, "response": response}) + "\n"
                )
                result = observer.partial_accounting(folder)
                self.assertEqual(result["reserved_optimizer_calls"], 1)
                self.assertEqual(result["completed_optimizer_calls"], 0)
                self.assertEqual(result["unverified_reserved_upper"], 4096)
                self.assertFalse(result["accounting_complete"])
                self.assertTrue(result["accounting_errors"])

    def test_loader_controller_and_direct_controller_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            proc = Path(folder)
            for pid, executable, args in (
                (
                    11,
                    "ld-linux-x86-64.so.2",
                    [
                        "loader",
                        "--library-path",
                        "lib",
                        "/sealed/go2_mjpc_controller_fd_original",
                    ],
                ),
                (12, "go2_mjpc_controller", ["controller"]),
                (13, "ld-linux-x86-64.so.2", ["loader", "/usr/bin/ordinary"]),
            ):
                sub = proc / str(pid)
                sub.mkdir()
                (sub / "exe").symlink_to(proc / executable)
                (sub / "cmdline").write_bytes(
                    b"\0".join(a.encode() for a in args) + b"\0"
                )
            self.assertEqual(
                {r["pid"] for r in observer.live_controller_processes(proc)}, {11, 12}
            )
