import json
import unittest
from pathlib import Path
from unittest import mock

from . import mjpc_fixed_baseline as baseline
from .aligned_anchor import load_anchor


class FixedBaselineContractTests(unittest.TestCase):
    def test_design_matches_frozen_protocol_and_budget(self):
        self.assertEqual(baseline.design(), json.loads(baseline.PROTOCOL.read_text()))
        d = baseline.design()
        self.assertEqual(d["private_upper_bound_per_repeat"], d["replans"] * d["private_reservation_per_replan"])
        self.assertEqual(d["private_upper_bound_total"], d["repeats"] * d["private_upper_bound_per_repeat"])
        self.assertEqual(d["workers"], 4)
        self.assertEqual(d["binary_sha256"], baseline.BINARY_SHA)

    def test_original_anchor_task_commands_and_horizon(self):
        anchor = load_anchor()
        task = baseline.replace(anchor["task"], task_id="mjpc-fixed-baseline-3s-v1",
                                horizon_ticks=1500, measurement_start_tick=150)
        self.assertEqual(task.horizon_ticks, 1500)
        self.assertEqual(task.command_at(0).tolist(), [0.0, 0.0, 0.0])
        self.assertEqual(task.command_at(150).tolist(), [1.0, 0.0, 0.0])
        self.assertEqual(anchor["controllers"]["mjpc"]["timing"].feedback_period_s, 0.002)

    def test_no_launch_path_never_calls_episode_or_controller(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            root = Path(temp)
            runs = root / "_runs"
            runs.mkdir()
            out = runs / "preflight"
            report = {"head": "head", "output": str(out), "canonical_physics_steps": 0}
            with mock.patch.object(baseline, "RUNS", runs), \
                 mock.patch.object(baseline, "validate", return_value=({}, Path("/fixed"), report)), \
                 mock.patch.object(baseline, "run_aligned_episode", side_effect=AssertionError("physics")), \
                 mock.patch.object(baseline, "NativeMJPCController", side_effect=AssertionError("native")):
                result = baseline.no_launch("packet.json", out)
            self.assertEqual(result["status"], "PRECHECK_PASS_NO_LAUNCH")
            self.assertEqual(result["canonical_physics_steps"], 0)

    def test_output_must_be_fresh_top_level_run(self):
        with self.assertRaises(ValueError):
            baseline.fresh(Path("/tmp/not-a-run"))

if __name__ == "__main__":
    unittest.main()

