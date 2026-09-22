"""Portable schedule/stop tests and optional zero-integration native checks."""

import importlib.util
from pathlib import Path
import unittest
import numpy as np

from .baseline_episode import Plant, SourcePolicy, analyze, command_at, episode, safety
from .contracts import POLICY_JOINTS, Proprioception
from .guards import zero_step_guard
from .integrity import strict_json
from .rl import FrozenPolicy, observation45
from .baseline_verify import audit_preflight, trace_consumed, independent_body_vx

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = strict_json(
    (ROOT / "tools/substrate/protocols/rl_source_v1.json").read_text()
)


def sample(tick=0):
    return dict(
        tick=tick,
        time=tick * 0.002,
        qpos=[tick * 0.002, 0, 0.3, 1, 0, 0, 0] + [0] * 12,
        qvel=[1, 0, 0] + [0] * 15,
        clearance=0.3,
        warnings=0,
        base_contacts=[],
        feet=[[tick * 0.002, 0, 0]] * 4,
    )


class FakePlant:
    def __init__(self, fail_tick=None):
        self.steps = 0
        self.fail_tick = fail_tick

    def snapshot(self, tick):
        row = sample(tick)
        row["warnings"] = int(tick == self.fail_tick)
        return row

    def observe(self):
        return Proprioception(
            POLICY_JOINTS, np.zeros(12), np.zeros(12), [1, 0, 0, 0], np.zeros(3)
        )

    def control(self, target):
        return np.zeros(12), np.zeros(12)

    def step(self, applied):
        self.steps += 1


class FakePolicy:
    def act(self, obs, command):
        return np.zeros(45), np.zeros(12, dtype=np.float32)


class BaselineContractTests(unittest.TestCase):
    def test_nonunit_terminal_orientation_preserves_metric_polynomial(self):
        self.assertEqual(independent_body_vx([2, 0, 0, 0], [1, 0, 0]), 1)

    def test_failed_preflight_cannot_verify(self):
        with self.assertRaisesRegex(ValueError, "preflight not passing"):
            audit_preflight({"pass": False, "hard_failure_count": 1}, {}, {})

    def test_initial_safety_stop_does_not_consume(self):
        rows, claims = [], []
        episode(
            FakePlant(0),
            FakePolicy(),
            PROTOCOL["cases"][0],
            PROTOCOL,
            rows.append,
            lambda: claims.append(1),
        )
        self.assertEqual(claims, [])
        self.assertFalse(trace_consumed(rows))
        self.assertEqual(len(rows), 1)

    def test_schedule_transition_exact(self):
        case = PROTOCOL["cases"][5]
        self.assertEqual(command_at(case, 2499)[0], 1)
        self.assertEqual(command_at(case, 2500)[0], 0.5)
        self.assertEqual(command_at(case, 7500)[0], 0)

    def test_claim_before_step_and_source_cadence(self):
        case = {**PROTOCOL["cases"][0], "horizon_ticks": 21}
        plant, rows, claims = FakePlant(), [], []
        episode(
            plant,
            FakePolicy(),
            case,
            PROTOCOL,
            rows.append,
            lambda: claims.append(plant.steps),
        )
        self.assertEqual(claims, [0])
        self.assertEqual(
            [r["tick"] for r in rows if r["observation"] is not None], [10, 20]
        )
        self.assertEqual(plant.steps, 21)
        self.assertIsNone(rows[-1]["applied"])

    def test_no_unused_terminal_inference(self):
        case = {**PROTOCOL["cases"][0], "horizon_ticks": 20}
        rows = []
        episode(FakePlant(), FakePolicy(), case, PROTOCOL, rows.append, lambda: None)
        self.assertEqual(
            [r["tick"] for r in rows if r["observation"] is not None], [10]
        )

    def test_safety_stops_without_extra_step(self):
        plant, rows = FakePlant(12), []
        episode(
            plant,
            FakePolicy(),
            PROTOCOL["cases"][0],
            PROTOCOL,
            rows.append,
            lambda: None,
        )
        self.assertEqual(plant.steps, 12)
        self.assertEqual(rows[-1]["failure"], "physics_warning")
        self.assertIsNone(rows[-1]["applied"])

    def test_emit_failure_prevents_step(self):
        plant = FakePlant()
        with self.assertRaises(OSError):
            episode(
                plant,
                FakePolicy(),
                PROTOCOL["cases"][0],
                PROTOCOL,
                lambda row: (_ for _ in ()).throw(OSError("disk")),
                lambda: None,
            )
        self.assertEqual(plant.steps, 0)

    def test_stairs_allow_high_world_height(self):
        row = sample()
        row["qpos"][2] = 2.2
        self.assertIsNone(safety(row, PROTOCOL))
        row["clearance"] = 0.01
        self.assertEqual(safety(row, PROTOCOL), "posture")

    def test_base_collision_stops(self):
        row = sample()
        row["base_contacts"] = [[0, 2]]
        self.assertEqual(safety(row, PROTOCOL), "base_contact")

    def test_metrics_body_frame_and_half_open_window(self):
        case = {
            **PROTOCOL["cases"][0],
            "horizon_ticks": 3,
            "measurement_delay_ticks": 1,
        }
        rows = []
        for tick in range(4):
            row = sample(tick)
            row.update(
                target=[0] * 12, applied=[0] * 12, policy_wall_s=None, failure=None
            )
            row["qvel"][0] = 100 if tick in (0, 3) else 1
            rows.append(row)
        result = analyze(rows, case, PROTOCOL)
        self.assertEqual(result["windows"][0]["samples"], 2)
        self.assertEqual(result["windows"][0]["mae"], 0)


@unittest.skipUnless(
    importlib.util.find_spec("mujoco")
    and importlib.util.find_spec("torch")
    and (ROOT / ".substrate/upstream-go2-30e74dc5").exists(),
    "native source assets required",
)
class NativeBaselineTests(unittest.TestCase):
    def test_telemetry_does_not_modify_live_data(self):
        with zero_step_guard():
            case = PROTOCOL["cases"][0]
            p = Plant(ROOT / case["scene"], case, 0.002)
            before = {
                n: getattr(p.data, n).copy()
                for n in ("qpos", "qvel", "qacc_warmstart", "ctrl", "qfrc_actuator")
            }
            p.snapshot(0)
            for name, expected in before.items():
                np.testing.assert_array_equal(getattr(p.data, name), expected)
            self.assertEqual(p.steps, 0)

    def test_all_models_zero_step_and_limit_location(self):
        with zero_step_guard():
            for index in (0, 7, 8, 9):
                c = PROTOCOL["cases"][index]
                p = Plant(ROOT / c["scene"], c, 0.002)
                self.assertIsNone(safety(p.snapshot(0), PROTOCOL))
                self.assertEqual(p.steps, 0)
                if index == 0:
                    self.assertFalse(p.model.actuator_ctrllimited.any())
                    self.assertTrue(p.model.jnt_actfrclimited[1:].all())

    def test_source_adapter_initial_history_equivalence(self):
        expected = strict_json(
            (ROOT / "tools/substrate/sources.lock.json").read_text()
        )["rl"]["sha256"]
        source = SourcePolicy(
            ROOT / ".substrate/upstream-go2-30e74dc5",
            ROOT / ".substrate/rl/policy.pt",
            expected,
        )
        adapter = FrozenPolicy(ROOT / ".substrate/rl/policy.pt", expected)
        with zero_step_guard():
            for i in range(8):
                obs = Proprioception(
                    POLICY_JOINTS,
                    np.arange(12) * 0.01 * i,
                    np.arange(12) * 0.03,
                    [1, 0, 0, 0],
                    [0.1, 0.2, 0.3],
                )
                assembled = observation45(obs, [1, 0, 0], adapter.previous_action)
                upstream, target = source.act(obs, [1, 0, 0])
                own = adapter.act(obs, [1, 0, 0])
                np.testing.assert_array_equal(assembled, upstream)
                np.testing.assert_array_equal(target, own.position_target)


if __name__ == "__main__":
    unittest.main()
