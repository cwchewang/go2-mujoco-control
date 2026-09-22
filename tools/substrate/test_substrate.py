import tempfile
import unittest
from pathlib import Path
import numpy as np
from .contracts import (
    POLICY_JOINTS as P,
    MOTOR_JOINTS as M,
    Proprioception,
    TorqueCommand,
    reorder,
)
from .rl import DEFAULT, observation45
from .model import dependency_manifest
from .evidence import summarize_frames, validate_capture_contract


class Boundaries(unittest.TestCase):
    def obs(self):
        return Proprioception(
            P, DEFAULT.copy(), np.zeros(12), np.array([1.0, 0.0, 0.0, 0.0]), np.zeros(3)
        )

    def test_named_permutation_roundtrip(self):
        a = np.arange(12.0)
        np.testing.assert_array_equal(reorder(reorder(a, P, M), M, P), a)
        self.assertEqual(reorder(a, P, M)[0], 3)

    def test_duplicate_missing_nonfinite_rejected(self):
        for source, values in (
            (P[:-1] + (P[0],), np.zeros(12)),
            (P[:-1], np.zeros(11)),
            (P, np.full(12, np.nan)),
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                reorder(values, source, M)

    def test_torque_pd_sum_before_model_limit(self):
        o = self.obs()
        cmd = TorqueCommand(
            P,
            np.full(12, 30),
            DEFAULT.astype(np.float64) + 1,
            np.zeros(12),
            np.full(12, 20),
            np.full(12, 0.5),
        )
        r = cmd.resolve(o, np.full(12, -40), np.full(12, 40), M)
        np.testing.assert_array_equal(r["total_unclipped"], np.full(12, 50))
        np.testing.assert_array_equal(r["ctrl"], np.full(12, 40))
        self.assertTrue(r["saturated"].all())

    def test_invalid_gain_and_range(self):
        cmd = TorqueCommand(
            P, np.zeros(12), DEFAULT, np.zeros(12), np.full(12, -1), np.zeros(12)
        )
        with self.assertRaises(ValueError):
            cmd.resolve(self.obs(), np.full(12, -40), np.full(12, 40), M)
        cmd = TorqueCommand(
            P, np.zeros(12), DEFAULT, np.zeros(12), np.zeros(12), np.zeros(12)
        )
        with self.assertRaises(ValueError):
            cmd.resolve(self.obs(), np.ones(12), np.zeros(12), M)

    def test_policy_observation_golden(self):
        o = self.obs()
        o = Proprioception(
            M,
            reorder(o.position, P, M) + np.arange(12) / 10,
            reorder(np.arange(12), P, M),
            np.array([np.cos(0.2), np.sin(0.2), 0.0, 0.0]),
            np.array([1.0, 2.0, 3.0]),
        )
        actual = observation45(o, [0.2, -0.1, 0.3], np.arange(12) / 20)
        expected = np.concatenate(
            (
                [0.25, 0.5, 0.75],
                [0, -np.sin(0.4), -np.cos(0.4)],
                [0.4, -0.2, 0.075],
                reorder(o.position, M, P) - DEFAULT,
                np.arange(12) * 0.05,
                np.arange(12) / 20,
            )
        ).astype(np.float32)
        np.testing.assert_allclose(actual, expected, atol=1e-7)
        self.assertEqual(actual.shape, (45,))
        self.assertEqual(actual.dtype, np.float32)

    def test_policy_rejects_bad_quaternion_command(self):
        o = self.obs()
        with self.assertRaises(ValueError):
            observation45(o, [3, 0, 0], np.zeros(12))
        o = Proprioception(P, DEFAULT, np.zeros(12), np.zeros(4), np.zeros(3))
        with self.assertRaises(ValueError):
            observation45(o, [0, 0, 0], np.zeros(12))

    def test_asset_closure_detects_included_mesh_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            (p / "assets").mkdir()
            (p / "assets/a.obj").write_text("mesh one")
            (p / "robot.xml").write_text(
                '<mujoco><compiler meshdir="assets"/><asset><mesh file="a.obj"/></asset></mujoco>'
            )
            (p / "scene.xml").write_text('<mujoco><include file="robot.xml"/></mujoco>')
            a = dependency_manifest(p / "scene.xml", p)
            self.assertEqual(len(a["files"]), 3)
            (p / "assets/a.obj").write_text("mesh two")
            self.assertNotEqual(
                a["sha256"], dependency_manifest(p / "scene.xml", p)["sha256"]
            )

    def test_include_cycle_and_missing_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            f = p / "a.xml"
            for target in ("a.xml", "missing.xml", "../outside.xml"):
                f.write_text(f'<mujoco><include file="{target}"/></mujoco>')
                with self.assertRaises(ValueError):
                    dependency_manifest(f, p)

    def test_earliest_failure_preserved(self):
        rows = [
            dict(sequence=0, sim_time_s=0, failure="solver_nonfinite"),
            dict(sequence=1, sim_time_s=0.02, terminal_reason="task_incomplete"),
        ]
        r = summarize_frames(rows, 0.02)
        self.assertEqual(r["first_failure"]["reason"], "solver_nonfinite")
        self.assertEqual(r["terminal_reason"], "task_incomplete")
        self.assertFalse(r["task_complete"])

    def test_jump_traverse_vs_mandatory_support(self):
        rows = [dict(sequence=0, sim_time_s=0, task_complete=True, supports=[])]
        self.assertTrue(
            summarize_frames(rows, 0.02, "traverse", ["top"])["task_complete"]
        )
        self.assertFalse(
            summarize_frames(rows, 0.02, "mandatory_support", ["top"])["task_complete"]
        )

    def test_duplicate_or_gap_rejected(self):
        for seq, t in ((0, 0.02), (2, 0.02), (1, 0), (1, 0.04), (1, float("nan"))):
            rows = [dict(sequence=0, sim_time_s=0), dict(sequence=seq, sim_time_s=t)]
            with self.subTest(seq=seq, t=t), self.assertRaises(ValueError):
                summarize_frames(rows, 0.02)

    def test_unreviewed_capture_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unfrozen capture"):
            validate_capture_contract({})


if __name__ == "__main__":
    unittest.main()
