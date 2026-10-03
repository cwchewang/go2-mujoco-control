import tempfile
import unittest
from pathlib import Path
from tools.substrate.mjpc_floor_registration_diagnostic import (
    assert_only_floor_z_changed,
    protocol,
)


class FloorRegistrationDiffTests(unittest.TestCase):
    def test_protocol_is_single_attempt_and_floor_only(self):
        value = protocol()
        self.assertEqual(value["max_attempts"], 1)
        self.assertEqual(value["canonical_steps_max"], 1500)
        self.assertEqual(
            value["intervention"]["field"], "private_task_flat.floor.pos.z"
        )
        self.assertEqual(value["native_controller_processes_max"], 1)
        self.assertIn("not future rollout", value["prediction_contact_semantics"])

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
