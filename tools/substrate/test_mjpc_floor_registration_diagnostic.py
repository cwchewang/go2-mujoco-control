import tempfile
import unittest
from pathlib import Path
from tools.substrate.mjpc_floor_registration_diagnostic import (
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
        self.assertEqual(value["campaign_identity"], "prepared packet SHA-256; single allowed slot 1")
        self.assertEqual(value["capture_native_controller_processes_campaign_max"], 1)
        self.assertEqual(value["private_step_upper_bound_total_max"], 2457600)

    def test_qualification_claim_binds_exact_consumer_binary_and_runtime(self):
        record = {
            "qualification_profile": "mjpc_floor_registration_sustained_12s_v1",
            "qualification": {
                "head": "h",
                "clean_head": True,
                "development": False,
            },
            "qualification_inputs": {
                "fd_fixed_controller": {"binary_sha256": "b"}
            },
            "canonical_physics_steps": 0,
            "scientific_attempts": 0,
            "private_engineering_optimizer_calls": 1,
            "private_step_upper_bound_max": 4096,
            "physics_accounting": {
                "binary_sha256": "b",
                "runtime_identity_sha256": "r",
                "canonical_steps": 0,
                "scientific_attempts": 0,
                "optimizer_calls": 1,
                "private_step_upper_bound_max": 4096,
            },
        }
        self.assertTrue(validate_qualification_claim(record, "h", "b", "r"))
        with self.assertRaisesRegex(ValueError, "exact floor0 consumer"):
            validate_qualification_claim(record, "h", "other", "r")

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
