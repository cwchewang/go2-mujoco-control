import unittest
import numpy as np

from .contracts import (
    MOTOR_JOINTS,
    POLICY_JOINTS,
    Proprioception,
    WholeBodyState,
    reorder,
)
from .native_mjpc import parse_step_response, step_packet, validate_ready


class NativeMJPCProtocolTest(unittest.TestCase):
    def ready(self, **updates):
        value = {
            "ready": True,
            "protocol": 2,
            "nq": 19,
            "nv": 18,
            "nu": 12,
            "planner": "MJPC iLQG",
            "planner_dt": 0.01,
            "horizon_steps": 36,
            "source_nominal_biastype": "mjBIAS_NONE",
            "compatibility_correction": "private_model_mjBIAS_AFFINE",
            "canonical_evaluation_plant_modified": False,
            "gait_switch": "Manual",
            "gait": "Trot",
            "joint_names": list(MOTOR_JOINTS),
            "position_lower": [-2.0] * 12,
            "position_upper": [2.0] * 12,
            "kp": [60.0] * 12,
            "kd": [5.0] * 12,
        }
        value.update(updates)
        return value

    def state(self):
        p = Proprioception(
            POLICY_JOINTS,
            np.arange(12.0) / 10,
            np.arange(12.0) / 20,
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.array([0.1, 0.2, 0.3]),
        )
        return WholeBodyState(
            p,
            np.array([1.0, 2.0, 3.0]),
            np.array([0.4, 0.5, 0.6]),
            1.25,
        )

    def test_ready_metadata_builds_explicit_pd_spec(self):
        names, spec = validate_ready(self.ready())
        self.assertEqual(names, MOTOR_JOINTS)
        np.testing.assert_array_equal(spec.kp, np.full(12, 60.0))
        np.testing.assert_array_equal(spec.kd, np.full(12, 5.0))

    def test_ready_rejects_compatibility_or_gain_drift(self):
        with self.assertRaises(ValueError):
            validate_ready(self.ready(compatibility_correction="silent_patch"))
        with self.assertRaisesRegex(ValueError, "PD gains"):
            validate_ready(self.ready(kp=[59.0] * 12))

    def test_step_packet_reconstructs_source_joint_order(self):
        state = self.state()
        packet = step_packet(state, [1.0, 0.0, 0.2], MOTOR_JOINTS)
        fields = packet.split()
        self.assertEqual(fields[0], "step")
        values = np.asarray([float(x) for x in fields[1:]])
        self.assertEqual(values.shape, (41,))
        np.testing.assert_allclose(values[0:4], [1.25, 1.0, 0.0, 0.2])
        qpos = values[4:23]
        qvel = values[23:41]
        np.testing.assert_allclose(qpos[:7], [1, 2, 3, 1, 0, 0, 0])
        np.testing.assert_allclose(
            qpos[7:],
            reorder(state.proprioception.position, POLICY_JOINTS, MOTOR_JOINTS),
        )
        np.testing.assert_allclose(qvel[:6], [0.4, 0.5, 0.6, 0.1, 0.2, 0.3])
        np.testing.assert_allclose(
            qvel[6:],
            reorder(state.proprioception.velocity, POLICY_JOINTS, MOTOR_JOINTS),
        )

    def test_step_response_is_fail_closed(self):
        action, meta = parse_step_response(
            {
                "ok": True,
                "time_s": 1.25,
                "cost": 3.0,
                "compute_us": 1200,
                "q_des": [0.0] * 12,
            },
            1.25,
        )
        np.testing.assert_array_equal(action, np.zeros(12))
        self.assertEqual(meta["compute_s"], 0.0012)
        with self.assertRaises(RuntimeError):
            parse_step_response({"ok": False, "error": "planner failed"}, 1.25)
        with self.assertRaises(ValueError):
            parse_step_response(
                {
                    "ok": True,
                    "time_s": 1.25,
                    "cost": float("nan"),
                    "compute_us": 1,
                    "q_des": [0.0] * 12,
                },
                1.25,
            )


if __name__ == "__main__":
    unittest.main()
