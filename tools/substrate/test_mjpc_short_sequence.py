"""Zero-physics contracts for the sequential MJPC observer."""

import copy
import runpy
import unittest

from . import fd_duplicate_diagnostic as d
from . import mjpc_short_sequence as sequence


class ShortSequenceContractTest(unittest.TestCase):
    def test_real_old_a_inputs_are_complete_and_consecutive(self):
        if not d.CAPTURE.exists():
            self.skipTest("sealed old-A capture is not present in this checkout")
        source = sequence.load_sequence(d.CAPTURE)
        rows = source["inputs"]
        self.assertEqual([row["tick"] for row in rows], list(range(11)))
        self.assertEqual(
            [row["replan"] for row in rows], [tick in (0, 10) for tick in range(11)]
        )
        for row in rows:
            self.assertAlmostEqual(row["time_s"], row["tick"] * 0.002, places=12)
        self.assertEqual(len({row["input_sha256"] for row in rows}), 11)
        self.assertEqual(
            source["source_raw_sha256"],
            "9a4f2711f558b80ac58c803406971f43be7c44f4c5e64f7a50c728e2a7440e55",
        )
        self.assertEqual(len(sequence.validate_sequence_bundle(source)), 11)
        changed = copy.deepcopy(source)
        changed["inputs"][5]["qpos"][0] += 1e-4
        with self.assertRaisesRegex(ValueError, "integrity mismatch"):
            sequence.validate_sequence_bundle(changed)

    def test_plan_is_four_fresh_processes_eight_optimizer_calls(self):
        trials = sequence.sequence_trials()
        self.assertEqual(len(trials), 4)
        self.assertEqual(
            {(x["variant"], x["repeat"]) for x in trials},
            {(v, r) for v in ("original", "fixed") for r in (1, 2)},
        )
        self.assertEqual(len(trials) * 2, 8)
        self.assertEqual(len(trials) * 2 * d.RESERVATION, d.TOTAL_RESERVED)

    def test_packet_can_replay_logged_nonreplan_ticks(self):
        anchor = {
            "time_s": 0.002,
            "command": [0.0, 0.0, 0.0],
            "qpos": [0.0] * 19,
            "qvel": [0.0] * 18,
        }
        self.assertTrue(d._packet(anchor).startswith("step 1 "))
        self.assertTrue(d._packet(anchor, replan=False).startswith("step 0 "))

    def trace(self, variant, call_index=1):
        knots = [*range(35), 34, 35] if variant == "original" else list(range(36))
        events = []
        for t, knot in enumerate(knots):
            events.append(
                {
                    "t": knot,
                    "worker": t % 4,
                    "call_index": call_index,
                    "start_ns": t * 10 + 1,
                    "end_ns": t * 10 + 2,
                    "warmstart_before_fnv1a64": "0123456789abcdef",
                    "warmstart_before_norm": 0.0,
                    "warmstart_before_max_abs": 0.0,
                    "warmstart_after_fnv1a64": "fedcba9876543210",
                    "warmstart_after_norm": 1.0,
                    "warmstart_after_max_abs": 0.5,
                }
            )
        return {
            "call_index": call_index,
            "events": events,
            "index_count": len(knots),
            "jacobian_t34_fnv1a64": "0123456789abcdef",
        }

    def test_trace_summary_schema_for_both_variants(self):
        for variant in ("original", "fixed"):
            with self.subTest(variant=variant):
                sequence.validate_warmstart_trace(self.trace(variant), variant, 1)

    def test_trace_summary_rejects_missing_or_nonfinite_warmstart(self):
        trace = self.trace("fixed")
        del trace["events"][0]["warmstart_after_fnv1a64"]
        with self.assertRaisesRegex(ValueError, "warmstart hash"):
            sequence.validate_warmstart_trace(trace, "fixed", 1)
        trace = self.trace("fixed")
        trace["events"][0]["warmstart_before_norm"] = float("nan")
        with self.assertRaisesRegex(ValueError, "warmstart norm"):
            sequence.validate_warmstart_trace(trace, "fixed", 1)

    def test_pair_comparison_reports_differences_without_rejecting_them(self):
        results = []
        for variant in ("original", "fixed"):
            for repeat in (1, 2):
                inputs = []
                for tick in range(11):
                    summary = None
                    cost = 0.0
                    q_des = [0.0] * 12
                    if tick in (0, 10):
                        cost = 1.0 + (0.1 if variant == "original" else 0.0)
                        summary = {
                            "candidate_id": 3,
                            "cost": cost,
                            "policy_hash": "0123456789abcdef",
                            "trajectory_hash": "fedcba9876543210",
                            "jacobian_t34_fnv1a64": "0123456789abcdef",
                            "t34_workers": [0, 1] if variant == "original" else [0],
                            "worker_warmstart": {"pre": [], "post": []},
                        }
                    inputs.append(
                        {
                            "tick": tick,
                            "input_sha256": f"{tick:064x}",
                            "cost": cost,
                            "q_des": q_des,
                            "replan_summary": summary,
                        }
                    )
                results.append(
                    {
                        "variant": variant,
                        "repeat": repeat,
                        "source_raw_sha256": "a" * 64,
                        "inputs": inputs,
                    }
                )
        compared = sequence.compare_sequence_trials(results)
        self.assertEqual(compared["optimizer_calls"], 8)
        self.assertEqual(compared["private_configured_reservation"], 32768)
        self.assertFalse(
            compared["comparisons"][0]["pairs"]["cross_variant"]["within_1e_9"]
        )
        self.assertEqual(
            compared["comparisons"][0]["per_run"]["original_repeat1"]["t34_workers"],
            [0, 1],
        )

    def test_native_instrumentation_is_summary_only_and_does_not_reset_warmstart(self):
        root = d.ROOT
        patcher = runpy.run_path(
            str(
                root
                / "tools/substrate/native/patch_mjpc_model_derivatives_diagnostic.py"
            )
        )
        upstream = (
            root / ".substrate/mjpc/mjpc/planners/model_derivatives.cc"
        ).read_bytes()
        original = patcher["render"](upstream, False)
        fixed = patcher["render"](upstream, True)
        for generated in (original, fixed):
            self.assertIn("warmstart_before_fnv1a64", generated)
            self.assertIn("warmstart_after_fnv1a64", generated)
            self.assertIn("g_fd_call_index", generated)
            self.assertNotIn("mju_zero(d->qacc_warmstart", generated)
        header = (root / "tools/substrate/native/diagnostic.h").read_text()
        controller = (root / "tools/substrate/native/controller.cc").read_text()
        self.assertIn("pre_worker_warmstart_", header)
        self.assertIn("selected_trajectory", header)
        self.assertIn("diagnostic_->BeginCall(planner_)", controller)
        self.assertIn("pool_(4)", controller)

    def test_policy_trajectory_summary_schema(self):
        summary = {
            "horizon": 36,
            "dim_state": 37,
            "dim_action": 12,
            "finite": True,
            "return_finite": True,
            "total_return": 0.0,
            "fnv1a64": "0123456789abcdef",
        }
        candidate = {
            "planner_history": {
                "call_index": 2,
                "pre_policy": copy.deepcopy(summary),
                "pre_previous_policy": copy.deepcopy(summary),
                "post_policy": copy.deepcopy(summary),
                "selected_trajectory": copy.deepcopy(summary),
                "worker_warmstart": {
                    "pre": [
                        {
                            "worker": i,
                            "finite": True,
                            "norm": 0.0,
                            "max_abs": 0.0,
                            "fnv1a64": "0123456789abcdef",
                        }
                        for i in range(4)
                    ],
                    "post": [
                        {
                            "worker": i,
                            "finite": True,
                            "norm": 0.0,
                            "max_abs": 0.0,
                            "fnv1a64": "0123456789abcdef",
                        }
                        for i in range(4)
                    ],
                },
            }
        }
        sequence.validate_planner_history(candidate, 2)
        candidate["planner_history"]["post_policy"]["finite"] = False
        with self.assertRaisesRegex(ValueError, "post_policy"):
            sequence.validate_planner_history(candidate, 2)


if __name__ == "__main__":
    unittest.main()
