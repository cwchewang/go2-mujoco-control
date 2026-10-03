"""Sealed evidence and zero-launch regressions for the floor0 smoke reuse path."""

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import qualification as q
from . import mjpc_smoke_reuse as reuse
from .guards import zero_step_guard
from .integrity import digest
from .mjpc_floor_registration_diagnostic import validate_qualification_claim

SOURCE = reuse.ROOT / "_runs/mjpc_floor_registration_sustained_12s_qualification_20261003_r7"
MANIFEST = "b7567ac69bc7d29ed2bdb633f8b2e8cd711aa7a03e248c058b4110befad6dbad"


@unittest.skipUnless(SOURCE.is_dir(), "sealed Atlas r7 smoke is not present")
class SmokeReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory, cls.record, cls.physics, cls.reference = reuse.load_source(
            SOURCE, MANIFEST
        )
        cls.current = q.current_inputs()
        cls.native_fingerprint = reuse.matching_native_inputs(cls.record, cls.current)

    def reused_record(self):
        record = copy.deepcopy(self.record)
        record.update(
            qualification_inputs=copy.deepcopy(self.current),
            qualification_fingerprint=q.fingerprint(self.current),
            private_engineering_optimizer_calls=0,
            reused_private_engineering_optimizer_calls=1,
            smoke_provenance={
                "schema": 1,
                "mode": "sealed_smoke_reuse",
                "source_qualification": copy.deepcopy(self.reference),
                "source_smoke_accounting_sha256": digest(
                    SOURCE / "native-smoke-accounting.json"
                ),
                "native_inputs_fingerprint": self.native_fingerprint,
                "copied_log_sha256": {
                    name: digest(SOURCE / name) for name in reuse.SMOKE_LOGS[1:]
                },
                "source_optimizer_calls": 1,
                "new_optimizer_calls": 0,
            },
        )
        return record

    def test_actual_r7_and_current_smoke_inputs_match(self):
        self.assertEqual(digest(SOURCE / "manifest.json"), MANIFEST)
        self.assertEqual(self.physics["optimizer_calls"], 1)
        self.assertEqual(self.physics["private_step_upper_bound_max"], 4096)
        self.assertEqual(
            reuse.matching_native_inputs(self.record, self.current),
            self.native_fingerprint,
        )
        for name in (
            reuse.PRODUCER, reuse.CONSUMER,
            "tools/substrate/mjpc_smoke_reuse.py",
            "tools/substrate/test_mjpc_smoke_reuse.py",
        ):
            self.assertIn(name, self.current["tracked_files"])

    def test_hash_pin_and_modified_sealed_file_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "manifest pin"):
            reuse.load_source(SOURCE, "0" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            admission = directory / "admission.json"
            admission.write_text('{"status":"ENGINEERING_ADMITTED"}')
            manifest = directory / "manifest.json"
            manifest.write_text(json.dumps({"admission.json": digest(admission)}))
            pin = digest(manifest)
            admission.write_text('{"status":"FORGED"}')
            with self.assertRaises(ValueError):
                reuse.load_source(directory, pin)

    def test_budget_and_original_call_accounting_cannot_be_forged(self):
        for field, value in (
            ("private_step_upper_bound_max", 4095),
            ("private_step_upper_bound_max", 4096.0),
            ("optimizer_calls", 0),
            ("canonical_steps", 1),
        ):
            record = copy.deepcopy(self.record)
            record["physics_accounting"][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(
                ValueError, "accounting/profile"
            ):
                reuse.validate_source_record(record)
        for key in ("fd_call_count", "rollout_mj_step_count", "private_step_upper_bound_reserved"):
            record = copy.deepcopy(self.record)
            record["physics_accounting"]["accounting"][key] += 1
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "accounting/profile"):
                reuse.validate_source_record(record)
        record = copy.deepcopy(self.record)
        record["private_engineering_optimizer_calls"] = 0
        with self.assertRaisesRegex(ValueError, "accounting/profile"):
            reuse.validate_source_record(record)

    def test_consumer_identity_and_build_identity_are_required(self):
        for key in ("binary_sha256", "binary_build_identity"):
            record = copy.deepcopy(self.record)
            record["physics_accounting"][key] = "other-consumer"
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "consumer identity"):
                reuse.validate_source_record(record)

    def test_model_protocol_transport_binary_and_environment_drift_rejected(self):
        tracked = self.current["tracked_files"]
        protocol = next(
            name for name in tracked
            if "/protocols/" in name and "floor" in name and "12s" in name
        )
        mutations = (
            ("tracked_files", "unitree_robots/go2/phase2_flat.xml"),
            ("tracked_files", protocol),
            ("tracked_files", "tools/substrate/native_transport.py"),
            ("fd_fixed_controller", "binary_sha256"),
            ("runtime", "schema"),
        )
        for group, key in mutations:
            current = copy.deepcopy(self.current)
            current[group][key] = "changed"
            with self.subTest(group=group, key=key), self.assertRaisesRegex(
                ValueError, "inputs changed"
            ):
                reuse.matching_native_inputs(self.record, current)

    def test_capture_and_smoke_bodies_are_not_exempt_from_input_identity(self):
        for name, before, after in (
            (reuse.CONSUMER, "def capture(", "def changed_capture("),
            (reuse.PRODUCER, "controller.step(state, row", "controller.step(None, row"),
        ):
            source = (reuse.ROOT / name).read_text()
            self.assertIn(before, source)
            self.assertNotEqual(
                reuse.source_projection(source, name),
                reuse.source_projection(source.replace(before, after, 1), name),
            )

    def test_reuses_actual_runtime_and_logs_with_no_native_launch(self):
        with tempfile.TemporaryDirectory() as tmp, zero_step_guard(), patch(
            "tools.substrate.qualify_mjpc_diagnostic.smoke",
            side_effect=AssertionError("new smoke forbidden"),
        ), patch(
            "tools.substrate.native_mjpc.NativeMJPCController",
            side_effect=AssertionError("native launch forbidden"),
        ):
            output = Path(tmp)
            physics, provenance = reuse.reuse_smoke(
                SOURCE, MANIFEST, output, self.current
            )
            self.assertEqual(physics, self.physics)
            self.assertEqual(provenance["new_optimizer_calls"], 0)
            self.assertEqual(provenance["source_qualification"], self.reference)
            self.assertEqual(
                digest(output / "consumer-runtime/controller-runtime-identity.json"),
                self.physics["runtime_identity_sha256"],
            )
            for name in reuse.SMOKE_LOGS[1:]:
                self.assertEqual(digest(output / name), digest(SOURCE / name))
        self.assertEqual(digest(SOURCE / "manifest.json"), MANIFEST)

    def test_reuse_record_is_accepted_without_claiming_a_new_call(self):
        record = self.reused_record()
        self.assertTrue(reuse.validate_reuse_record(record))
        self.assertTrue(validate_qualification_claim(
            record, record["qualification"]["head"],
            self.physics["binary_sha256"], self.physics["runtime_identity_sha256"],
        ))

    def test_missing_or_conflicting_provenance_is_rejected(self):
        for mutation in (
            lambda r: r.update(private_engineering_optimizer_calls=1),
            lambda r: r.update(reused_private_engineering_optimizer_calls=2),
            lambda r: r["smoke_provenance"].update(new_optimizer_calls=1),
            lambda r: r["smoke_provenance"].update(native_inputs_fingerprint="wrong"),
            lambda r: r["smoke_provenance"].update(source_smoke_accounting_sha256="wrong"),
            lambda r: r["smoke_provenance"]["source_qualification"].update(producer_head="wrong"),
            lambda r: r["smoke_provenance"]["source_qualification"].update(manifest_sha256="0"*64),
        ):
            record = self.reused_record()
            mutation(record)
            with self.assertRaises(ValueError):
                reuse.validate_reuse_record(record)
        record = self.reused_record()
        del record["smoke_provenance"]
        with self.assertRaises(ValueError):
            validate_qualification_claim(
                record, record["qualification"]["head"],
                self.physics["binary_sha256"], self.physics["runtime_identity_sha256"],
            )

    def test_partial_reuse_arguments_fail_before_any_native_work(self):
        from .qualify_mjpc_diagnostic import qualify

        with patch("tools.substrate.qualify_mjpc_diagnostic.smoke",
                   side_effect=AssertionError("smoke forbidden")):
            with self.assertRaisesRegex(ValueError, "supplied together"):
                qualify(Path("/unused"), reuse_smoke_from=SOURCE)


if __name__ == "__main__":
    unittest.main()
