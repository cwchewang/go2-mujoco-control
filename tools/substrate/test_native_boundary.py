"""Native model checks, run separately from dependency-light hosted CI."""

import tempfile
import unittest
from pathlib import Path
import mujoco
import numpy as np
from .contracts import MOTOR_JOINTS, Proprioception
from .model import (
    physical_fingerprint,
    joint_layout,
    decorate_mjpc,
    position_pd_actuator_spec,
)

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

    def _position_pd_model(self, *, affine=True):
        bodies = []
        actuators = []
        for i, name in enumerate(MOTOR_JOINTS):
            bodies.append(
                f'<body name="b{i}" pos="{i * 0.1} 0 0">'
                f'<joint name="{name}" type="hinge"/>'
                '<geom type="sphere" size="0.01" mass="0.1"/>'
                "</body>"
            )
            bias = ' biastype="affine"' if affine else ""
            actuators.append(
                f'<general name="a{i}" joint="{name}" ctrllimited="true" '
                f'ctrlrange="-2 2" gainprm="60"{bias} biasprm="0 -60 -5"/>'
            )
        return mujoco.MjModel.from_xml_string(
            '<mujoco><option gravity="0 0 0"/><worldbody>'
            + "".join(bodies)
            + "</worldbody><actuator>"
            + "".join(actuators)
            + "</actuator></mujoco>"
        )

    def test_position_pd_source_semantics_match_mujoco_force(self):
        model = self._position_pd_model()
        spec = position_pd_actuator_spec(model)
        self.assertEqual(spec.joint_names, MOTOR_JOINTS)
        np.testing.assert_array_equal(spec.kp, np.full(12, 60.0))
        np.testing.assert_array_equal(spec.kd, np.full(12, 5.0))
        data = mujoco.MjData(model)
        data.qpos[:] = np.linspace(-0.2, 0.2, 12)
        data.qvel[:] = np.linspace(0.1, -0.1, 12)
        target = np.linspace(-3, 3, 12)
        data.ctrl[:] = np.clip(target, -2, 2)
        mujoco.mj_forward(model, data)
        observation = Proprioception(
            MOTOR_JOINTS,
            data.qpos.copy(),
            data.qvel.copy(),
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.zeros(3),
        )
        command, source = spec.command(target)
        resolved = command.resolve(
            observation,
            np.full(12, -1e6),
            np.full(12, 1e6),
            MOTOR_JOINTS,
        )
        np.testing.assert_allclose(resolved["pd"], data.qfrc_actuator, atol=1e-12)
        np.testing.assert_array_equal(source["position_target"], data.ctrl)

    def test_missing_affine_bias_type_rejected(self):
        with self.assertRaisesRegex(ValueError, "not affine"):
            position_pd_actuator_spec(self._position_pd_model(affine=False))

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
