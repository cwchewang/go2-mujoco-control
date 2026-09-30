import copy
import unittest

from tools.substrate.mjpc_comparator import (
    EXPECTED_MUJOCO_VERSION,
    EXPECTED_SOURCE_COMMIT,
    STRICT_ALIASING_FLAG,
    validate_actuator_semantics,
    validate_compatibility_metadata,
    validate_source_commit,
    validate_source_lock,
)


def actuator_fixture():
    return (
        [[60.0] + [0.0] * 9 for _ in range(12)],
        [[0.0, -60.0, -5.0] + [0.0] * 7 for _ in range(12)],
        [0] * 12,
    )


def metadata_fixture():
    return {
        "schema_version": 1,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "mujoco_version": EXPECTED_MUJOCO_VERSION,
        "compiler_flags": [STRICT_ALIASING_FLAG],
        "task": "QuadrupedFlat",
        "compatibility": {
            "source_validated": True,
            "source_gainprm": 60,
            "source_biasprm": [0, -60, -5],
            "source_biastype": "mjBIAS_NONE",
            "correction": "actuator biastype=mjBIAS_AFFINE",
            "correction_scope": "ephemeral comparator model copy only",
            "canonical_evaluation_plant_modified": False,
        },
        "command": {
            "mode": "Walk",
            "gait_switch": "Manual",
            "gait": "Trot",
            "walk_speed_mps": 1,
            "walk_turn_radps": 0,
            "argv": ["probe", "task_flat.xml"],
        },
        "timing": {
            "home_hold_simulated_seconds": 1.0,
            "agent_probe_simulated_seconds": 0.5,
            "agent_probe_wall_seconds": 2.0,
            "planning_wall_seconds": 1.0,
        },
        "home_hold": {"height_min_m": 0.27, "xy_displacement_m": 0.0},
        "agent_probe": {"height_final_m": 0.27, "displacement_xy_m": 0.1},
        "nonfinite_status": "all_checked_values_finite",
        "task_model": {
            "task_xml_sha256": "a" * 64,
            "go2_xml_sha256": "b" * 64,
        },
    }


class MjpcComparatorTests(unittest.TestCase):
    def test_source_lock_requires_frozen_pins(self):
        validate_source_lock(
            {"mjpc": {"commit": EXPECTED_SOURCE_COMMIT}, "mujoco": "3.3.6"}
        )
        changed_commit = {
            "mjpc": {"commit": "0" * 40},
            "mujoco": "3.3.6",
        }
        with self.assertRaisesRegex(ValueError, "source pin drift"):
            validate_source_lock(changed_commit)
        with self.assertRaisesRegex(ValueError, "MuJoCo pin drift"):
            validate_source_lock(
                {"mjpc": {"commit": EXPECTED_SOURCE_COMMIT}, "mujoco": "3.3.5"}
            )

    def test_checkout_commit_must_match_pinned_source(self):
        validate_source_commit(EXPECTED_SOURCE_COMMIT, EXPECTED_SOURCE_COMMIT)
        with self.assertRaisesRegex(ValueError, "checkout commit mismatch"):
            validate_source_commit("0" * 40, EXPECTED_SOURCE_COMMIT)

    def test_nominal_actuator_semantics_match_before_correction(self):
        validate_actuator_semantics(*actuator_fixture())

    def test_actuator_semantic_drift_fails_closed(self):
        gain, bias, biastype = actuator_fixture()
        gain_drift = copy.deepcopy(gain)
        gain_drift[3][0] = 59.0
        with self.assertRaisesRegex(ValueError, "gainprm"):
            validate_actuator_semantics(gain_drift, bias, biastype)

        bias_drift = copy.deepcopy(bias)
        bias_drift[5][2] = -4.0
        with self.assertRaisesRegex(ValueError, "biasprm"):
            validate_actuator_semantics(gain, bias_drift, biastype)

        affine_drift = biastype.copy()
        affine_drift[7] = 1
        with self.assertRaisesRegex(ValueError, "non-affine"):
            validate_actuator_semantics(gain, bias, affine_drift)

        with self.assertRaisesRegex(ValueError, "actuator count"):
            validate_actuator_semantics(gain[:-1], bias[:-1], biastype[:-1])

    def test_required_compatibility_metadata_is_complete(self):
        validate_compatibility_metadata(metadata_fixture())

    def test_metadata_rejects_missing_aliasing_flag(self):
        metadata = metadata_fixture()
        metadata["compiler_flags"] = []
        with self.assertRaisesRegex(ValueError, "fno-strict-aliasing"):
            validate_compatibility_metadata(metadata)

    def test_metadata_rejects_canonical_plant_correction(self):
        metadata = metadata_fixture()
        metadata["compatibility"]["canonical_evaluation_plant_modified"] = True
        with self.assertRaisesRegex(ValueError, "canonical evaluation plant"):
            validate_compatibility_metadata(metadata)

    def test_metadata_rejects_command_drift(self):
        metadata = metadata_fixture()
        metadata["command"]["walk_speed_mps"] = 0.5
        with self.assertRaisesRegex(ValueError, "walk_speed_mps"):
            validate_compatibility_metadata(metadata)


if __name__ == "__main__":
    unittest.main()
