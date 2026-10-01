import unittest
import numpy as np

from .clock import TimingSpec
from .contracts import (
    MOTOR_JOINTS,
    POLICY_JOINTS,
    Proprioception,
    WholeBodyState,
    reorder,
)
from .native_mjpc import (
    cadence_tick,
    parse_step_response,
    sample_command,
    step_packet,
    validate_ready,
)


class NativeMJPCProtocolTest(unittest.TestCase):
    def ready(self, **updates):
        value = {
            "ready": True,
            "protocol": 3,
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
            "ground_miss_handling": "rollout_warning_failure",
            "warning_channel": "stderr",
            "joint_names": list(MOTOR_JOINTS),
            "position_lower": [-2.0] * 12,
            "position_upper": [2.0] * 12,
            "kp": [60.0] * 12,
            "kd": [5.0] * 12,
        }
        value.update(updates)
        return value

    def state(self, time_s=1.25):
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
            time_s,
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

    def test_ready_rejects_ground_failure_or_warning_channel_drift(self):
        for fields in (
            {"ground_miss_handling": "ignore"},
            {"warning_channel": "stdout"},
        ):
            with self.assertRaises(ValueError):
                validate_ready(self.ready(**fields))

    def test_planning_and_feedback_cadence_are_distinct(self):
        timing = TimingSpec(0.002, 0.02, feedback_period_s=0.002)
        self.assertEqual(cadence_tick(0.0, timing), (0, True))
        self.assertEqual(cadence_tick(0.002, timing, 0), (1, False))
        self.assertEqual(cadence_tick(0.018, timing, 8), (9, False))
        self.assertEqual(cadence_tick(0.020, timing, 9), (10, True))
        with self.assertRaisesRegex(ValueError, "physics clock"):
            cadence_tick(0.003, timing, 0)
        with self.assertRaisesRegex(ValueError, "missing, duplicate"):
            cadence_tick(0.006, timing, 1)

    def test_command_is_sampled_only_on_replan_ticks(self):
        requested, sampled = sample_command([1.0, 0.0, 0.0], True)
        np.testing.assert_array_equal(requested, sampled)
        requested, held = sample_command([0.8, 0.0, 0.1], False, sampled)
        np.testing.assert_array_equal(requested, [0.8, 0.0, 0.1])
        np.testing.assert_array_equal(held, [1.0, 0.0, 0.0])
        with self.assertRaisesRegex(ValueError, "previously sampled"):
            sample_command([1.0, 0.0, 0.0], False)

    def test_step_packet_reconstructs_source_joint_order(self):
        state = self.state()
        packet = step_packet(state, [1.0, 0.0, 0.2], MOTOR_JOINTS, replan=True)
        fields = packet.split()
        self.assertEqual(fields[:2], ["step", "1"])
        values = np.asarray([float(x) for x in fields[2:]])
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

    def test_step_response_separates_plan_and_feedback_cost(self):
        action, meta = parse_step_response(
            {
                "ok": True,
                "time_s": 1.25,
                "cost": 3.0,
                "replanned": True,
                "planning_compute_us": 1200,
                "action_compute_us": 40,
                "q_des": [0.0] * 12,
            },
            1.25,
            True,
        )
        np.testing.assert_array_equal(action, np.zeros(12))
        self.assertEqual(meta["planning_compute_s"], 0.0012)
        self.assertAlmostEqual(meta["action_compute_s"], 0.00004)

        _, held = parse_step_response(
            {
                "ok": True,
                "time_s": 1.252,
                "cost": 3.0,
                "replanned": False,
                "planning_compute_us": 0,
                "action_compute_us": 30,
                "q_des": [0.0] * 12,
            },
            1.252,
            False,
        )
        self.assertFalse(held["replanned"])
        with self.assertRaises(ValueError):
            parse_step_response(
                {
                    "ok": True,
                    "time_s": 1.252,
                    "cost": 3.0,
                    "replanned": False,
                    "planning_compute_us": 1,
                    "action_compute_us": 30,
                    "q_des": [0.0] * 12,
                },
                1.252,
                False,
            )


if __name__ == "__main__":
    unittest.main()
