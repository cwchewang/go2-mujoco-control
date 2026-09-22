"""Native model checks, run separately from dependency-light hosted CI."""

import tempfile
import unittest
from pathlib import Path
import mujoco
import numpy as np
from .contracts import MOTOR_JOINTS
from .model import physical_fingerprint, joint_layout, decorate_mjpc

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "unitree_robots/go2/phase2_flat.xml"


class NativeBoundary(unittest.TestCase):
    def test_named_joints_and_model_limits(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        names, qadr, vadr = joint_layout(model)
        self.assertEqual(names, MOTOR_JOINTS)
        self.assertEqual(qadr[:3], [10, 11, 12])
        self.assertEqual(vadr[:3], [9, 10, 11])
        np.testing.assert_allclose(model.actuator_ctrlrange[:3, 1], [40.0, 40.0, 45.43])

    def test_decorated_physics_identical(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "task.xml"
            decorate_mjpc(SCENE, f)
            decorated = mujoco.MjModel.from_xml_path(str(f))
            self.assertEqual(
                physical_fingerprint(model), physical_fingerprint(decorated)
            )
            self.assertEqual(
                int(decorated.sensor_type[0]), int(mujoco.mjtSensor.mjSENS_USER)
            )
            self.assertEqual(sum(decorated.sensor_dim[:5]), 31)

    def test_friction_or_actuator_drift_detected(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        original = physical_fingerprint(model)
        model.geom_friction[0, 0] *= 0.5
        self.assertNotEqual(original, physical_fingerprint(model))
        model.actuator_gainprm[0, 0] = 2
        with self.assertRaises(ValueError):
            joint_layout(model)
        model.actuator_gainprm[0, 0] = 1
        model.actuator_forcelimited[0] = True
        with self.assertRaises(ValueError):
            joint_layout(model)


if __name__ == "__main__":
    unittest.main()
