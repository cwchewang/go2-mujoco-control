"""Portable schedule/stop tests and optional zero-integration native checks."""

import importlib.util
from pathlib import Path
import unittest
import numpy as np

from .baseline_episode import Plant, SourcePolicy, analyze, command_at, episode, safety
from .contracts import POLICY_JOINTS, Proprioception
from .baseline import campaign_characterized, validate_source_identity
from .baseline_episode import repeat_reference, stop_after
from .baseline_verify import audit_preflight, trace_consumed, independent_body_vx
from .guards import zero_step_guard
from .integrity import strict_json
from .rl import FrozenPolicy, observation45

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = strict_json(
    (ROOT / "tools/substrate/protocols/rl_source_v1.json").read_text()
)
COMBINED_PROTOCOL = strict_json(
    (
        ROOT / "tools/substrate/protocols/rl_shared_transfer_combination_v1.json"
    ).read_text()
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
    def test_combination_protocol_freezes_the_minimal_full_transfer(self):
        self.assertEqual(COMBINED_PROTOCOL["id"], "rl-shared-transfer-combination-v1")
        self.assertEqual(COMBINED_PROTOCOL["mode"], "confirmatory")
        self.assertEqual(COMBINED_PROTOCOL["max_attempts"], 2)
        self.assertEqual(COMBINED_PROTOCOL["seed"], 0)
        self.assertEqual(
            COMBINED_PROTOCOL["source_identity"],
            {
                "commit": "30e74dc507bec7a642a8c98be26081f2c6f0822d",
                "checkpoint": (
                    "deploy/pre_train/go2/go2_moe_cts_high_slope_thre_164k_0.6715.pt"
                ),
                "checkpoint_sha256": (
                    "9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d"
                ),
            },
        )
        first, repeat = COMBINED_PROTOCOL["cases"]
        for case in (first, repeat):
            self.assertEqual(case["scene"], "unitree_robots/go2/phase2_flat.xml")
            self.assertTrue(case["adapter"])
            self.assertEqual(case["reset"], "shared_home")
            self.assertEqual(case["first_inference_tick"], 10)
            self.assertEqual(case["horizon_ticks"], 6000)
            self.assertEqual(case["commands"], [[0, 1.0]])
            self.assertEqual(case["measurement_delay_ticks"], 1000)
            self.assertTrue(case["reference_gate"])
        self.assertEqual(repeat["repeat_of"], first["id"])
        self.assertEqual(repeat["requires"], [first["id"]])
        self.assertEqual(COMBINED_PROTOCOL["progression"], "first_nonpass_stop")
        self.assertEqual(COMBINED_PROTOCOL["reference_mean_min"], 0.8)
        self.assertEqual(COMBINED_PROTOCOL["tracking_absolute_tolerance"], 0.05)
        self.assertEqual(COMBINED_PROTOCOL["tracking_relative_tolerance"], 0.2)
        self.assertEqual(COMBINED_PROTOCOL["flat_lateral_max"], 0.3)
        self.assertEqual(COMBINED_PROTOCOL["flat_yaw_max"], 0.3)

    def test_protocol_source_identity_is_bound_to_existing_locks(self):
        reference_lock = strict_json(
            (ROOT / "tools/substrate/rl_reference.lock.json").read_text()
        )
        source_lock = strict_json(
            (ROOT / "tools/substrate/sources.lock.json").read_text()
        )
        validate_source_identity(COMBINED_PROTOCOL, reference_lock, source_lock)
        altered_lock = {**source_lock, "rl": {**source_lock["rl"], "sha256": "0" * 64}}
        with self.assertRaisesRegex(ValueError, "source identity"):
            validate_source_identity(COMBINED_PROTOCOL, reference_lock, altered_lock)

    def test_combination_uses_declared_repeat_and_first_nonpass(self):
        self.assertEqual(repeat_reference(COMBINED_PROTOCOL["cases"][1]), "combined_1")
        self.assertEqual(repeat_reference(PROTOCOL["cases"][1]), "source_1")
        self.assertFalse(stop_after(COMBINED_PROTOCOL, "PASS"))
        self.assertTrue(stop_after(COMBINED_PROTOCOL, "PERFORMANCE_FAIL"))
        self.assertTrue(stop_after(COMBINED_PROTOCOL, "SAFETY_STOP"))
        self.assertTrue(stop_after(COMBINED_PROTOCOL, "INTEGRITY_STOP"))
        self.assertFalse(stop_after(PROTOCOL, "PERFORMANCE_FAIL"))
        self.assertTrue(
            campaign_characterized(
                [{"status": "PERFORMANCE_FAIL"}, {"status": "NOT_RUN"}],
                COMBINED_PROTOCOL,
            )
        )
        self.assertFalse(
            campaign_characterized(
                [{"status": "SAFETY_STOP"}, {"status": "NOT_RUN"}],
                COMBINED_PROTOCOL,
            )
        )

    def test_combination_startup_cadence_runs_synthetically(self):
        case = {
            **COMBINED_PROTOCOL["cases"][0],
            "adapter": False,
            "horizon_ticks": 21,
        }
        plant, rows = FakePlant(), []
        episode(plant, FakePolicy(), case, COMBINED_PROTOCOL, rows.append, lambda: None)
        self.assertEqual(
            [r["tick"] for r in rows if r["observation"] is not None], [10, 20]
        )
        self.assertEqual(plant.steps, 21)

    def test_combination_analyzer_applies_reference_mean_gate(self):
        case = {
            **COMBINED_PROTOCOL["cases"][0],
            "horizon_ticks": 2,
            "measurement_delay_ticks": 0,
        }
        rows = []
        for tick in range(3):
            row = sample(tick)
            row.update(
                target=[0] * 12,
                applied=[0] * 12,
                failure=None,
                policy_wall_s=None,
            )
            rows.append(row)
        result = analyze(rows, case, COMBINED_PROTOCOL)
        self.assertEqual(result["verdict"], "PASS")
        stricter = {**COMBINED_PROTOCOL, "reference_mean_min": 1.01}
        result = analyze(rows, case, stricter)
        self.assertEqual(result["windows"][0]["mae"], 0)
        self.assertEqual(result["verdict"], "PERFORMANCE_FAIL")

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
