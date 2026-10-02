"""Fake episodes and static MuJoCo checks; all native integration is forbidden."""

from dataclasses import replace
from pathlib import Path
import copy
import tempfile
import unittest

import numpy as np

from . import test_aligned_episode as fixtures
from .aligned_episode import run_aligned_episode
from .bounded_conditions import BoundedCondition, condition_specs
from .contracts import WholeBodyState
from .episode import MujocoPlant
from .guards import zero_step_guard
from .native_mjpc import cadence_tick, step_packet
from .shared_baseline import load_plan, replay_baseline, repeat_difference

ROOT = Path(__file__).resolve().parents[2]


class RecordingController(fixtures.FakeController):
    def __init__(self):
        super().__init__()
        self.observations = []

    def step(self, observation, command):
        self.observations.append(observation)
        return super().step(observation, command)


class BoundedConditionsTest(unittest.TestCase):
    def setUp(self):
        guard = zero_step_guard()
        guard.__enter__()
        self.addCleanup(guard.__exit__, None, None, None)
        self.plan = load_plan()

    def fake_episode(self, name, controller_name="mjpc", horizon=40, emit=None):
        config = self.plan["controllers"][controller_name]
        info, timing = condition_specs(name, config["information"], config["timing"])
        task = replace(
            self.plan["task"], horizon_ticks=horizon, measurement_start_tick=0
        )
        plant, controller, rows, claims = (
            fixtures.FakePlant(),
            RecordingController(),
            [],
            [],
        )
        result = run_aligned_episode(
            plant,
            controller,
            task,
            info,
            timing,
            emit or rows.append,
            lambda: claims.append(plant.steps),
            condition=BoundedCondition(name),
        )
        return plant, controller, rows, claims, result

    def test_delayed_content_and_native_current_clock(self):
        _, controller, rows, claims, result = self.fake_episode("observation_delay")
        self.assertEqual(claims, [0])
        old, now = controller.observations[20], rows[20]
        self.assertIsInstance(old, WholeBodyState)
        self.assertAlmostEqual(old.base_position_world[0], rows[10]["qpos"][0])
        self.assertAlmostEqual(old.time_s, 0.04)
        self.assertAlmostEqual(now["information"]["sample_time_s"], 0.02)
        self.assertAlmostEqual(now["information"]["available_time_s"], 0.04)
        self.assertAlmostEqual(now["information"]["age_s"], 0.02)
        self.assertTrue(rows[0]["condition_observation"]["initial_state_seed"])
        self.assertFalse(rows[10]["condition_observation"]["initial_state_seed"])
        previous = None
        timing = self.plan["controllers"]["mjpc"]["timing"]
        for state in controller.observations:
            tick, replan = cadence_tick(state.time_s, timing, previous)
            packet = step_packet(
                state,
                [1, 0, 0],
                controller.observations[0].proprioception.joint_names,
                replan=replan,
            )
            self.assertAlmostEqual(float(packet.split()[2]), state.time_s)
            previous = tick
        self.assertGreater(result["condition_summary"]["delayed_updates"], 0)

    def test_proprioceptive_delay_keeps_named_content(self):
        _, controller, rows, _, _ = self.fake_episode("observation_delay", "rl")
        self.assertEqual(len(controller.observations), 4)
        self.assertAlmostEqual(rows[20]["information"]["age_s"], 0.02)
        self.assertEqual(controller.step_types, ["Proprioception"] * 4)

    def test_decision_period_preserves_native_feedback(self):
        _, controller, rows, _, _ = self.fake_episode("decision_period")
        self.assertEqual(len(controller.observations), 40)
        config = self.plan["controllers"]["mjpc"]
        _, timing = condition_specs(
            "decision_period", config["information"], config["timing"]
        )
        replans = []
        previous = None
        for state in controller.observations:
            tick, replan = cadence_tick(state.time_s, timing, previous)
            if replan:
                replans.append(tick)
            previous = tick
        self.assertEqual(replans, [0, 20])
        self.assertEqual(sum(r["controller_update"] for r in rows), 40)

    def test_decision_period_rl_holds_until_next_decision(self):
        _, controller, rows, _, _ = self.fake_episode("decision_period", "rl")
        self.assertEqual(len(controller.observations), 2)
        self.assertEqual([r["tick"] for r in rows if r["controller_update"]], [0, 20])

    def test_latency_requires_explicit_matching_hook(self):
        config = self.plan["controllers"]["rl"]
        plant = fixtures.FakePlant()
        hook = BoundedCondition("observation_delay")
        with self.assertRaisesRegex(ValueError, "latency"):
            hook.reset(plant, config["information"], config["timing"])
        with self.assertRaisesRegex(ValueError, "unknown"):
            BoundedCondition("search_strength")

    def native_hook(self, name):
        plant = MujocoPlant(ROOT / "unitree_robots/go2/phase2_flat.xml")
        config = self.plan["controllers"]["mjpc"]
        info, timing = condition_specs(name, config["information"], config["timing"])
        hook = BoundedCondition(name)
        hook.reset(plant, info, timing)
        return plant, hook

    def test_static_actual_friction_changes_only_sliding(self):
        plant, hook = self.native_hook("sliding_friction")
        original = plant.model.geom_friction.copy()
        pre = hook.before_step(plant, 2999)
        self.assertEqual(len(pre["actual_contacts"]), 4)
        post = hook.before_step(plant, 3000)
        self.assertEqual(len(post["actual_contacts"]), 4)
        for c in post["actual_contacts"]:
            np.testing.assert_allclose(c["friction"], [0.3, 0.3, 0.02, 0.01, 0.01])
        expected = original.copy()
        expected[list(plant.feet), 0] = 0.3
        np.testing.assert_array_equal(plant.model.geom_friction, expected)
        summary = hook.complete()
        self.assertNotEqual(
            summary["physical_sha256_before"], summary["physical_sha256_after"]
        )
        self.assertEqual((plant.steps, plant.data.time), (0, 0.0))

    def test_ineffective_contact_is_rejected(self):
        plant, hook = self.native_hook("sliding_friction")
        plant.model.geom_priority[plant.floor] = 3
        with self.assertRaisesRegex(ValueError, "actual contact"):
            hook.before_step(plant, 3000)

    def test_force_boundaries_input_impulse_and_cleanup(self):
        plant, hook = self.native_hook("lateral_force")
        self.assertEqual(hook.before_step(plant, 2999)["applied_world_wrench"], [0] * 6)
        for tick in range(3000, 3100):
            self.assertEqual(
                hook.before_step(plant, tick)["applied_world_wrench"],
                [0, 50, 0, 0, 0, 0],
            )
        self.assertEqual(hook.before_step(plant, 3100)["applied_world_wrench"], [0] * 6)
        self.assertEqual(hook.complete()["nominal_applied_impulse_Ns"], 10.0)
        hook.before_step(plant, 3000)
        hook.finish(plant)
        self.assertFalse(np.any(plant.data.xfrc_applied))
        self.assertEqual((plant.steps, plant.data.time), (0, 0.0))

    def test_foreign_force_is_rejected(self):
        plant, hook = self.native_hook("lateral_force")
        plant.data.xfrc_applied[hook.body, 2] = 1
        with self.assertRaisesRegex(ValueError, "outside hook"):
            hook.before_step(plant, 3000)

    def test_force_cleanup_on_emit_exception(self):
        plant, hook = self.native_hook("lateral_force")
        plant.step = lambda ctrl: self.fail("real plant step must not run")
        original = hook.before_step

        def inject(p, tick):
            record = original(p, tick)
            p.data.xfrc_applied[hook.body, 1] = 50
            return record

        hook.before_step = inject
        config = self.plan["controllers"]["mjpc"]

        def fail_emit(row):
            raise RuntimeError("emit failed")

        with self.assertRaisesRegex(RuntimeError, "emit failed"):
            run_aligned_episode(
                plant,
                fixtures.FakeController(),
                self.plan["task"],
                config["information"],
                config["timing"],
                fail_emit,
                lambda: None,
                condition=hook,
            )
        self.assertFalse(np.any(plant.data.xfrc_applied))
        self.assertEqual(plant.steps, 0)

    def rows(self):
        config = self.plan["controllers"]["rl"]
        rows = []
        run_aligned_episode(
            fixtures.FakePlant(),
            fixtures.FakeController(),
            self.plan["task"],
            config["information"],
            config["timing"],
            rows.append,
            lambda: None,
        )
        return rows

    def test_half_open_metrics_and_terminal_endpoint(self):
        rows = self.rows()
        rows[-1]["qvel"][0] = 100
        result = replay_baseline(rows, self.plan)
        self.assertEqual(result["classification"], "PASS")
        self.assertEqual(result["performance"]["measurement_samples"], 5000)
        self.assertEqual(result["performance"]["body_vx_mean_mps"], 1.0)

    def test_performance_and_safety_are_separate(self):
        rows = self.rows()
        for row in rows:
            row["qvel"][0] = 0.5
        self.assertEqual(
            replay_baseline(rows, self.plan)["classification"], "PERFORMANCE_FAIL"
        )
        rows = self.rows()
        rows[-1]["warning_count"] = 1
        self.assertEqual(
            replay_baseline(rows, self.plan)["classification"], "SAFETY_STOP"
        )

    def test_yaw_gate_and_independent_body_velocity(self):
        rows = self.rows()
        # 90-degree body heading, moving at 1 m/s in world-y.
        for row in rows[1:]:
            row["qpos"][3:7] = [2**-0.5, 0, 0, 2**-0.5]
            row["qvel"][:3] = [0, 1, 0]
        result = replay_baseline(rows, self.plan)
        self.assertAlmostEqual(result["performance"]["body_vx_mean_mps"], 1.0)
        self.assertEqual(result["classification"], "PERFORMANCE_FAIL")

    def test_broken_raw_and_command_rejected(self):
        rows = self.rows()
        rows[10]["command"][0] = 0.123
        with self.assertRaisesRegex(ValueError, "command"):
            replay_baseline(rows, self.plan)
        rows = self.rows()
        rows.pop(10)
        with self.assertRaisesRegex(ValueError, "missing"):
            replay_baseline(rows, self.plan)

    def test_repeat_checks_use_states_and_applied_controls(self):
        rows = self.rows()
        other = copy.deepcopy(rows)
        other[20]["controller_diagnostics"] = {"wall_time": 99}
        self.assertTrue(repeat_difference(rows, other)["repeatable"])
        other[20]["action"]["ctrl"][0] = 1e-6
        self.assertFalse(repeat_difference(rows, other)["repeatable"])
        other[20]["qpos"][0] = None
        with self.assertRaisesRegex(ValueError, "invalid"):
            repeat_difference(rows, other)

    def test_candidate_budget_and_cards_fail_closed(self):
        raw = copy.deepcopy(self.plan["raw"])
        raw["max_attempts"] = 21
        from .integrity import write_new

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "plan.json"
            write_new(path, raw)
            with self.assertRaisesRegex(ValueError, "max_attempts"):
                load_plan(path)
