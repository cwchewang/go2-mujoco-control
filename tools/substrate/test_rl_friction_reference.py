"""Zero-physics checks for the prospective independent friction freeze."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from . import rl_friction_reference as prospective
from . import shared_campaign as shared


class FrozenProtocolTests(unittest.TestCase):
    def test_new_catalog_has_two_RL_challenges_and_sealed_pairing(self):
        plan = prospective.load_plan()
        items = prospective.arms(plan)
        self.assertEqual(
            [i["reference_baseline"] for i in items], ["rl_baseline_1", "rl_baseline_2"]
        )
        self.assertEqual({i["controller"] for i in items}, {"rl"})
        self.assertEqual({i["condition"] for i in items}, {"sliding_friction"})
        self.assertEqual(len(items), 2)
        old = shared.arms(shared.load_plan())
        self.assertEqual(len(old), 20)
        self.assertFalse({i["id"] for i in items} & {i["id"] for i in old})
        self.assertEqual(set(plan["controllers"]), {"rl"})
        self.assertFalse(hasattr(prospective, "capture"))

    def test_scientific_or_reference_drift_rejected_before_any_work(self):
        frozen = prospective.load_plan()["frozen"]
        mutations = [
            ("max_attempts", 3),
            ("physics_steps_max", 12001),
            ("physics_step_authorized", True),
            ("controller", "mjpc"),
            ("horizon_ticks", 6001),
            ("condition", {**frozen["condition"], "to": 0.2}),
            ("reference_capture_manifest_sha256", "0" * 64),
            ("reference_baselines", []),
            (
                "auxiliary_measurement",
                {**frozen["auxiliary_measurement"], "start_tick": 3500},
            ),
            ("retry", "one_recovery"),
        ]
        with tempfile.TemporaryDirectory() as temp:
            for key, value in mutations:
                with self.subTest(key=key):
                    altered = copy.deepcopy(frozen)
                    altered[key] = value
                    path = Path(temp) / (key + ".json")
                    path.write_text(json.dumps(altered))
                    with self.assertRaisesRegex(ValueError, "protocol drifted"):
                        prospective.load_plan(path)

    def test_actual_static_model_checkpoint_and_friction_inputs_are_ready(self):
        from .guards import zero_step_guard

        with zero_step_guard():
            plant, closure = prospective.static_inputs(prospective.load_plan())
        self.assertEqual(plant.steps, 0)
        self.assertEqual(plant.data.time, 0)
        self.assertIn("unitree_robots/go2/phase2_flat.xml", closure["files"])

    def test_inherited_task_safety_information_and_timing_unchanged(self):
        inherited = shared.load_plan()
        new = prospective.load_plan()
        self.assertEqual(new["task"].thresholds, inherited["task"].thresholds)
        self.assertEqual(new["task"].stop_on, inherited["task"].stop_on)
        self.assertEqual(new["task"].horizon_ticks, 6000)
        self.assertEqual(new["task"].measurement_start_tick, 1000)
        self.assertEqual(new["controllers"]["rl"], inherited["controllers"]["rl"])


def rows(vx=0.9, length=6001):
    return [
        {
            "tick": tick,
            "sim_time_s": tick * 0.002,
            "qpos": [0, 0, 0.3, 1, 0, 0, 0] + [0] * 12,
            "qvel": [vx if tick < 6000 else 999, 0, 0] + [0] * 15,
            "terminal_reason": "horizon" if tick == 6000 else None,
        }
        for tick in range(length)
    ]


class AuxiliaryWindowTests(unittest.TestCase):
    def test_half_open_window_excludes_before_onset_and_horizon_endpoint(self):
        trace = rows()
        for row in trace[:3000]:
            row["qvel"][0] = -7
        actual = prospective.auxiliary_window(trace)
        self.assertEqual(actual["measurement_samples"], 3000)
        self.assertEqual(actual["status"], "COMPLETE")
        self.assertAlmostEqual(actual["body_vx_mean_mps"], 0.9)
        self.assertAlmostEqual(actual["body_vx_mae_mps"], 0.1)
        self.assertFalse(actual["affects_primary_classification"])

    def test_incomplete_and_safety_windows_do_not_emit_partial_scores(self):
        for length in (0, 3001, 4100):
            with self.subTest(length=length):
                result = prospective.paired_auxiliary(rows(length=length), rows(vx=1.0))
                self.assertEqual(result["actual"]["status"], "NOT_MEASURABLE")
                self.assertIsNone(result["actual"]["body_vx_mean_mps"])
                self.assertIsNone(result["paired_mean_delta_mps"])
        trace = rows()
        trace[-1]["terminal_reason"] = "nonfoot_contact"
        self.assertIsNone(prospective.auxiliary_window(trace)["body_vx_mae_mps"])

    def test_paired_deltas_use_predeclared_window(self):
        result = prospective.paired_auxiliary(rows(vx=0.9), rows(vx=1.0))
        self.assertAlmostEqual(result["paired_mean_delta_mps"], -0.1)
        self.assertAlmostEqual(result["paired_mae_delta_mps"], 0.1)

    def test_rotated_body_velocity_is_not_world_velocity(self):
        trace = rows()
        for row in trace:
            row["qpos"][3:7] = [2**-0.5, 0, 0, 2**-0.5]
            row["qvel"][:3] = [0, 0.9, 0]
        self.assertAlmostEqual(
            prospective.auxiliary_window(trace)["body_vx_mean_mps"], 0.9
        )

    def test_missing_tick_or_nonfinite_state_rejected(self):
        trace = rows()
        trace[3000]["tick"] = 3001
        with self.assertRaisesRegex(ValueError, "tick sequence"):
            prospective.auxiliary_window(trace)
        trace = rows()
        trace[3100]["qvel"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "raw state invalid"):
            prospective.auxiliary_window(trace)


if __name__ == "__main__":
    unittest.main()
