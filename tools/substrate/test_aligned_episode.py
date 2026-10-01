import types
import unittest
import numpy as np
from .aligned_episode import replay_aligned_rows, run_aligned_episode
from .clock import TimingSpec
from .contracts import (
    POLICY_JOINTS,
    InformationSpec,
    Proprioception,
    TorqueCommand,
    WholeBodyState,
)
from .specs import TaskSpec, TaskThresholds


class FakePlant:
    def __init__(self):
        self.model = types.SimpleNamespace(opt=types.SimpleNamespace(timestep=0.002))
        self.names = POLICY_JOINTS
        self.lower = np.full(12, -100.0)
        self.upper = np.full(12, 100.0)
        self.data = types.SimpleNamespace(time=0.0)
        self.reset()

    def reset(self):
        self.steps = 0
        self.data.time = 0.0
        self.initial_y = 0.0
        self.qpos = np.array([0.0, 0.0, 0.27, 1.0, 0.0, 0.0, 0.0] + [0.0] * 12)
        self.qvel = np.zeros(18)

    def observe(self):
        return Proprioception(
            POLICY_JOINTS, self.qpos[7:], self.qvel[6:], self.qpos[3:7], self.qvel[3:6]
        )

    def whole_body_state(self):
        return WholeBodyState(
            self.observe(), self.qpos[:3], self.qvel[:3], self.data.time
        )

    def snapshot(self, tick):
        return {
            "tick": tick,
            "sim_time_s": self.data.time,
            "qpos": self.qpos.tolist(),
            "qvel": self.qvel.tolist(),
            "initial_y": self.initial_y,
            "supports": [],
            "forbidden_contacts": [],
            "warning_count": 0,
        }

    def step(self, ctrl):
        if not np.isfinite(ctrl).all():
            raise ValueError("nonfinite")
        self.steps += 1
        self.data.time = self.steps * 0.002
        self.qpos[0] += 0.002
        self.qvel[0] = 1.0


class FakeController:
    def __init__(self):
        self.reset_types = []
        self.step_types = []
        self.updates = 0

    def reset(self, observation):
        self.reset_types.append(type(observation).__name__)

    def step(self, observation, command):
        self.step_types.append(type(observation).__name__)
        self.updates += 1
        return TorqueCommand(
            POLICY_JOINTS,
            np.zeros(12),
            np.zeros(12),
            np.zeros(12),
            np.zeros(12),
            np.zeros(12),
        )

    def diagnostics(self):
        return {"updates": self.updates}


class AlignedEpisodeTest(unittest.TestCase):
    def task(self):
        return TaskSpec(
            task_id="fake",
            command_target=np.array([1.0, 0.0, 0.0]),
            command_frame="body",
            zero_command_ticks=0,
            ramp_ticks=1,
            horizon_ticks=4,
            measurement_start_tick=1,
            support_semantics="traverse",
            required_supports=(),
            stop_on=(
                "nonfinite",
                "orientation",
                "physics_warning",
                "nonfoot_contact",
                "posture",
                "lateral",
            ),
            thresholds=TaskThresholds(0.005, 0.1, 0.4, 0.8, 0.12, 0.55),
            longitudinal_metric="body_vx",
        )

    def run_case(self, info, timing):
        plant = FakePlant()
        controller = FakeController()
        rows = []
        consumed = []
        result = run_aligned_episode(
            plant,
            controller,
            self.task(),
            info,
            timing,
            rows.append,
            lambda: consumed.append(plant.steps),
        )
        return plant, controller, rows, consumed, result

    def test_proprioceptive_updates_and_replay(self):
        plant, c, rows, consumed, result = self.run_case(
            InformationSpec("proprioceptive", "none"),
            TimingSpec(0.002, 0.004, feedback_period_s=0.004),
        )
        self.assertEqual(plant.steps, 4)
        self.assertEqual(consumed, [0])
        self.assertEqual(
            [r["controller_update"] for r in rows], [True, False, True, False, False]
        )
        self.assertEqual(c.reset_types, ["Proprioception"])
        self.assertEqual(c.step_types, ["Proprioception"] * 2)
        self.assertEqual(result["terminal_reason"], "horizon")
        self.assertEqual(
            replay_aligned_rows(rows, self.task(), 0.002)["verdict"], "PASS"
        )

    def test_whole_body_updates_every_tick(self):
        plant, c, rows, consumed, _ = self.run_case(
            InformationSpec("whole_body_state", "controller_model"),
            TimingSpec(0.002, 0.004, feedback_period_s=0.002),
        )
        self.assertEqual(plant.steps, 4)
        self.assertEqual(consumed, [0])
        self.assertEqual(
            [r["controller_update"] for r in rows], [True, True, True, True, False]
        )
        self.assertEqual(c.reset_types, ["WholeBodyState"])
        self.assertEqual(c.step_types, ["WholeBodyState"] * 4)

    def test_latency_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "delayed-observation"):
            self.run_case(
                InformationSpec("proprioceptive", "none", latency_s=0.002),
                TimingSpec(0.002, 0.004, feedback_period_s=0.004),
            )


if __name__ == "__main__":
    unittest.main()
