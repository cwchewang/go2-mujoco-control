import copy
import json
import tempfile
import unittest
from pathlib import Path
from tools.substrate.contracts import MOTOR_JOINTS
from tools.substrate.integrity import digest, verify_bundle
from tools.substrate.qualify_mjpc_diagnostic import smoke_state_from_anchor
from tools.substrate.mjpc_floor_registration_diagnostic import (
    ROOT,
    assert_only_floor_z_changed,
    protocol,
    protocol_12s,
    validate_qualification_claim,
)


class FloorRegistrationDiffTests(unittest.TestCase):
    def test_protocol_is_two_fresh_repeat_slots_and_floor_only(self):
        value = protocol()
        self.assertEqual(value["repeats"], 2)
        self.assertEqual(value["attempts_per_repeat"], 1)
        self.assertEqual(value["max_attempts"], 2)
        self.assertEqual(value["capture_native_controller_processes_per_repeat_max"], 1)
        self.assertEqual(value["capture_native_controller_processes_campaign_max"], 2)
        self.assertEqual(value["construction_handshake_native_processes_max"], 1)
        self.assertEqual(value["private_step_upper_bound_total_max"], 1228800)
        self.assertEqual(value["canonical_steps_max"], 1500)
        self.assertEqual(
            value["intervention"]["field"], "private_task_flat.floor.pos.z"
        )
        self.assertIn("not future rollout", value["prediction_contact_semantics"])

    def test_12s_protocol_is_one_slot_and_one_capture_process(self):
        value = protocol_12s()
        self.assertEqual(value["repeats"], 1)
        self.assertEqual(value["max_attempts"], 1)
        self.assertEqual(
            value["campaign_identity"], "prepared packet SHA-256; single allowed slot 1"
        )
        self.assertEqual(value["capture_native_controller_processes_campaign_max"], 1)
        self.assertEqual(value["private_step_upper_bound_total_max"], 2457600)

    def test_smoke_anchor_maps_qpos_and_qvel_to_motor_order(self):
        row = {
            "qpos": [0.0, 0.0, 0.27, 1.0, 0.0, 0.0, 0.0]
            + [float(i) for i in range(12)],
            "qvel": [float(i) for i in range(18)],
            "sim_time_s": 0.0,
        }
        state = smoke_state_from_anchor(row)
        self.assertEqual(
            state.qpos(MOTOR_JOINTS).tolist(),
            [0.0, 0.0, 0.27, 1.0, 0.0, 0.0, 0.0]
            + [row["qpos"][i] for i in [10, 11, 12, 7, 8, 9, 16, 17, 18, 13, 14, 15]],
        )
        self.assertEqual(
            state.qvel(MOTOR_JOINTS).tolist(),
            [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
            + [row["qvel"][i] for i in [9, 10, 11, 6, 7, 8, 15, 16, 17, 12, 13, 14]],
        )

    def qualification_record(self):
        return {
            "qualification_profile": "mjpc_floor_registration_sustained_12s_v1",
            "qualification": {
                "head": "h",
                "clean_head": True,
                "development": False,
            },
            "qualification_inputs": {"fd_fixed_controller": {"binary_sha256": "b"}},
            "canonical_physics_steps": 0,
            "scientific_attempts": 0,
            "private_engineering_optimizer_calls": 1,
            "physics_accounting": {
                "binary_sha256": "b",
                "runtime_identity_sha256": "r",
                "canonical_steps": 0,
                "scientific_attempts": 0,
                "optimizer_calls": 1,
                "private_step_upper_bound_max": 4096,
            },
        }

    def test_qualification_claim_binds_exact_consumer_binary_and_runtime(self):
        record = self.qualification_record()
        self.assertTrue(validate_qualification_claim(record, "h", "b", "r"))
        with self.assertRaisesRegex(ValueError, "exact floor0 consumer"):
            validate_qualification_claim(record, "h", "other", "r")

    def test_qualification_budget_requires_real_nested_integer_and_consistent_alias(
        self,
    ):
        original = self.qualification_record()
        self.assertNotIn("private_step_upper_bound_max", original)
        self.assertTrue(validate_qualification_claim(original, "h", "b", "r"))
        alias = copy.deepcopy(original)
        alias["private_step_upper_bound_max"] = 4096
        self.assertTrue(validate_qualification_claim(alias, "h", "b", "r"))
        cases = []
        for value in (None, 4095, 4097, 4096.0, True, "4096"):
            record = copy.deepcopy(original)
            record["physics_accounting"]["private_step_upper_bound_max"] = value
            cases.append(("nested_" + repr(value), record))
        for value in (None, 4095, 4097, 4096.0, True, "4096"):
            record = copy.deepcopy(original)
            record["private_step_upper_bound_max"] = value
            cases.append(("alias_" + repr(value), record))
        missing = copy.deepcopy(alias)
        del missing["physics_accounting"]["private_step_upper_bound_max"]
        cases.append(("top_level_cannot_replace_missing_nested", missing))
        conflict = copy.deepcopy(alias)
        conflict["physics_accounting"]["private_step_upper_bound_max"] = 4095
        cases.append(("conflicting_nested_and_top_level", conflict))
        for name, record in cases:
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(ValueError, "exact floor0 consumer"),
            ):
                validate_qualification_claim(record, "h", "b", "r")

    def test_other_qualification_requirements_still_fail_closed(self):
        paths = (
            ("qualification_profile",),
            ("qualification", "head"),
            ("qualification", "clean_head"),
            ("qualification", "development"),
            ("canonical_physics_steps",),
            ("scientific_attempts",),
            ("private_engineering_optimizer_calls",),
            ("qualification_inputs", "fd_fixed_controller", "binary_sha256"),
            ("physics_accounting", "binary_sha256"),
            ("physics_accounting", "runtime_identity_sha256"),
            ("physics_accounting", "canonical_steps"),
            ("physics_accounting", "scientific_attempts"),
            ("physics_accounting", "optimizer_calls"),
        )
        for path in paths:
            for mutation in ("missing", "wrong"):
                record = self.qualification_record()
                parent = record
                for name in path[:-1]:
                    parent = parent[name]
                if mutation == "missing":
                    del parent[path[-1]]
                else:
                    value = parent[path[-1]]
                    parent[path[-1]] = (
                        not value
                        if type(value) is bool
                        else value + 1
                        if type(value) is int
                        else "wrong-identity"
                    )
                with (
                    self.subTest(path=path, mutation=mutation),
                    self.assertRaisesRegex(ValueError, "exact floor0 consumer"),
                ):
                    validate_qualification_claim(record, "h", "b", "r")

    @unittest.skipUnless(
        (
            ROOT
            / "_runs/mjpc_floor_registration_sustained_12s_qualification_20261003_r7"
        ).is_dir(),
        "sealed Atlas r7 receipt is not present",
    )
    def test_original_sealed_r7_json_is_accepted_without_top_level_alias(self):
        directory = (
            ROOT
            / "_runs/mjpc_floor_registration_sustained_12s_qualification_20261003_r7"
        )
        before = digest(directory / "manifest.json")
        self.assertEqual(
            before,
            "b7567ac69bc7d29ed2bdb633f8b2e8cd711aa7a03e248c058b4110befad6dbad",
        )
        record = verify_bundle(directory)
        raw_record = json.loads((directory / "admission.json").read_text())
        self.assertEqual(record, raw_record)
        self.assertNotIn("private_step_upper_bound_max", raw_record)
        self.assertTrue(
            validate_qualification_claim(
                raw_record,
                "347fe5afee826b66f431d4ba5670d580b8141dc2",
                "f5338a116da71083996b5000a2aea8c42fa1f1eb074f443e63a12b9c8ec3c05d",
                "075616dd01231d8e682a8f97c62de0329740cef15ca1245e526f172058f383c7",
            )
        )
        self.assertEqual(digest(directory / "manifest.json"), before)

    def test_accepts_only_floor_height_change(self):
        a = '<mujoco><worldbody><geom name="floor" type="plane" pos="0 0 -0.01" size="1 1 0.1"/><body name="robot"/></worldbody></mujoco>'
        b = a.replace('pos="0 0 -0.01"', 'pos="0 0 0"')
        with tempfile.TemporaryDirectory() as td:
            x, y = Path(td) / "a.xml", Path(td) / "b.xml"
            x.write_text(a)
            y.write_text(b)
            self.assertTrue(assert_only_floor_z_changed(x, y)["other_xml_values_equal"])

    def test_rejects_another_model_change(self):
        a = '<mujoco><worldbody><geom name="floor" type="plane" pos="0 0 -0.01" size="1 1 0.1"/></worldbody></mujoco>'
        b = a.replace('pos="0 0 -0.01"', 'pos="0 0 0"').replace(
            'size="1 1 0.1"', 'size="2 1 0.1"'
        )
        with tempfile.TemporaryDirectory() as td:
            x, y = Path(td) / "a.xml", Path(td) / "b.xml"
            x.write_text(a)
            y.write_text(b)
            with self.assertRaises(ValueError):
                assert_only_floor_z_changed(x, y)


if __name__ == "__main__":
    unittest.main()
