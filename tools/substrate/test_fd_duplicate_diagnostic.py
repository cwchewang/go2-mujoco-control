import json
from contextlib import nullcontext
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.substrate import fd_duplicate_diagnostic as d


class FDDuplicateDiagnosticTest(unittest.TestCase):
    def test_derived_private_bounds(self):
        self.assertEqual(
            d.derive_bounds(),
            {
                "old_fd_calls": 37,
                "fixed_fd_calls": 36,
                "old_fd_upper": 1801,
                "fixed_fd_upper": 1752,
                "rollout_steps": 700,
                "one_old_call": 2501,
                "one_fixed_call": 2452,
                "eight_call_total": 19812,
                "eight_call_reservation": 32768,
            },
        )

    def test_protocol_matches_the_private_bound_and_no_canonical_steps(self):
        protocol = json.loads(d.PROTOCOL.read_text())
        self.assertEqual(protocol["optimizer_calls_max"], 8)
        self.assertEqual(protocol["private_total_upper_bound"], 19812)
        self.assertEqual(protocol["private_total_reserved_upper_bound"], 32768)
        self.assertEqual(protocol["canonical_integration_steps"], 0)
        self.assertEqual(protocol["anchors"], [0, 10])
        self.assertEqual(protocol["variants"], ["original", "fixed"])
        self.assertEqual(protocol["workers"], 4)
        d.validate_protocol(protocol)
        protocol["private_total_upper_bound"] = 999
        with self.assertRaisesRegex(ValueError, "protocol/source"):
            d.validate_protocol(protocol)

    def test_trial_matrix_is_exactly_eight_fresh_calls(self):
        plan = d.trial_plan()
        self.assertEqual(len(plan), 8)
        self.assertEqual(plan[0], {"tick": 0, "repeat": 1, "variant": "original"})
        self.assertEqual(plan[-1], {"tick": 10, "repeat": 2, "variant": "fixed"})

    def test_duplicate_anchor_is_rejected(self):
        row = {
            "tick": 0,
            "controller_update": True,
            "failure": None,
            "warning_count": 0,
            "terminal_reason": None,
            "sim_time_s": 0.0,
            "qpos": [0.0] * 19,
            "qvel": [0.0] * 18,
            "command": [0.0] * 3,
        }
        with self.assertRaisesRegex(ValueError, "duplicate raw planner anchor"):
            d.anchors_from_raw_rows([row, row])

    def test_missing_anchor_is_rejected(self):
        row = {
            "tick": 0,
            "controller_update": True,
            "failure": None,
            "warning_count": 0,
            "terminal_reason": None,
            "sim_time_s": 0.0,
            "qpos": [0.0] * 19,
            "qvel": [0.0] * 18,
            "command": [0.0] * 3,
        }
        with self.assertRaisesRegex(ValueError, "tick 0/10"):
            d.anchors_from_raw_rows([row])

    def test_generator_preserves_old_schedule_and_traces_both_variants(self):
        source = d.ROOT / ".substrate/mjpc/mjpc/planners/model_derivatives.cc"
        script = (
            d.ROOT / "tools/substrate/native/patch_mjpc_model_derivatives_diagnostic.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "original.cc"
            fixed = Path(tmp) / "fixed.cc"
            subprocess.run(
                [sys.executable, str(script), str(source), str(original), str(fixed)],
                check=True,
                capture_output=True,
                text=True,
            )
            old = original.read_text()
            new = fixed.read_text()
        self.assertIn("legacy_indices.push_back(t)", old)
        self.assertIn("ModelDerivativeEvaluateIndices(T, skip)", new)
        for rendered in (old, new):
            self.assertIn("pool.WaitCount(count_before + evaluate_.size())", rendered)
            self.assertIn("jacobian_t34_fnv1a64", rendered)
            self.assertIn(
                "fd_events[slot] = {t, worker, call_index, start_ns, "
                "FDTraceNowNs(), before, after};",
                rendered,
            )

    def test_run_records_stay_outside_real_prepared_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = root / "prepared"
            with d.EvidenceRun(
                prepared, {"operation": "fd_duplicate_diagnostic_prepare"}
            ) as record:
                d.write_new(
                    prepared / "protocol.json", json.loads(d.PROTOCOL.read_text())
                )
                d.write_new(prepared / "inputs.json", {"fixture": "raw-anchor-record"})
                d.write_new(
                    prepared / "binary-identities.json", {"fixture": "paired-binaries"}
                )
                record.result.update(
                    status="ENGINEERING_ADMITTED",
                    scope="private_fd_duplicate_prepare",
                    head="fixture-head",
                )
            self.assertEqual(
                d.verify_manifest(prepared)["status"], "ENGINEERING_ADMITTED"
            )
            manifest_hash = d.digest(prepared / "manifest.json")
            expected_files = {
                "admission.json",
                "binary-identities.json",
                "inputs.json",
                "protocol.json",
                "started.json",
                "manifest.json",
            }
            self.assertEqual({p.name for p in prepared.iterdir()}, expected_files)

            defaults = d.default_run_record_paths(prepared)
            self.assertTrue(
                all(
                    not Path(v).resolve().is_relative_to(prepared.resolve())
                    for v in defaults.values()
                )
            )
            records = defaults["review"].parent
            records.mkdir()
            d.write_new(defaults["review"], {"head": "fixture-head"})
            d.write_new(defaults["authorization"], {"action": "fixture-only"})
            self.assertEqual(d.digest(prepared / "manifest.json"), manifest_hash)
            self.assertEqual(
                d.verify_manifest(prepared)["status"], "ENGINEERING_ADMITTED"
            )

            external_review = defaults["review"]
            external_auth = defaults["authorization"]
            external_output = defaults["output"]
            unsafe_paths = [
                ("review", prepared / "nested-review.json"),
                ("authorization", prepared / "nested-authorization.json"),
                ("output", prepared / "nested-result"),
            ]
            for slot, unsafe in unsafe_paths:
                paths = {
                    "review": external_review,
                    "authorization": external_auth,
                    "output": external_output,
                }
                paths[slot] = unsafe
                with (
                    self.subTest(slot=slot),
                    patch.object(d, "experiment_lock", return_value=nullcontext()),
                ):
                    with self.assertRaisesRegex(
                        ValueError, slot + " path must be outside"
                    ):
                        d.run(
                            prepared,
                            paths["review"],
                            paths["authorization"],
                            paths["output"],
                        )
                self.assertFalse(unsafe.exists())
                self.assertEqual(d.digest(prepared / "manifest.json"), manifest_hash)
                self.assertEqual(
                    d.verify_manifest(prepared)["status"], "ENGINEERING_ADMITTED"
                )
                self.assertEqual({p.name for p in prepared.iterdir()}, expected_files)

    def test_authorization_negative_case_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "explicit future user authorization"):
            d.validate_authorization({}, "head", "manifest")


if __name__ == "__main__":
    unittest.main()
