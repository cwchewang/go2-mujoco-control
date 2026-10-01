"""Campaign-stop regression fixtures: FakePlant only, no canonical integration."""

import copy
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from pathlib import Path
from unittest import mock

from . import aligned_capture as module
from .guards import zero_step_guard
from .integrity import strict_json, verify_manifest
from . import test_aligned_episode as episode_fixture
from .test_aligned_episode import FakeController, FakePlant


class FaultPlant(FakePlant):
    def __init__(self, reason=None, fault_tick=1):
        self.reason = reason
        self.fault_tick = fault_tick
        super().__init__()

    def snapshot(self, tick):
        row = super().snapshot(tick)
        if tick != self.fault_tick:
            return row
        if self.reason == "nonfinite":
            row["qvel"][0] = float("nan")
        elif self.reason == "orientation":
            row["qpos"][3] = 2.0
        elif self.reason == "physics_warning":
            row["warning_count"] = 1
        elif self.reason == "nonfoot_contact":
            row["forbidden_contacts"] = ["body"]
        elif self.reason == "posture":
            row["qpos"][2] = 0.01
        elif self.reason == "lateral":
            row["qpos"][1] = 0.5
        return row


class CampaignStopTest(unittest.TestCase):
    @contextmanager
    def fixture(
        self, *, reason=None, fault_tick=1, performance=None, continue_policy=True
    ):
        plan = copy.deepcopy(
            module.load_capture_plan(
                Path("tools/substrate/protocols/aligned_flat_capture_v2.json")
            )
        )
        task = episode_fixture.AlignedEpisodeTest().task()
        if performance == "progress":
            task = replace(
                task, thresholds=replace(task.thresholds, progress_min_m=100.0)
            )
        elif performance == "vx_mae":
            task = replace(
                task,
                thresholds=replace(task.thresholds, vx_mae_max_mps=0.0),
                command_target=task.command_target * 2,
            )
        plan["anchor"]["task"] = task
        if not continue_policy:
            plan["raw"].pop("horizon_performance_failure_policy")
        prepared = {
            "protocol_sha256": "p",
            "anchor_sha256": "a",
            "rl_checkpoint_sha256": "r",
            "mjpc_binary_sha256": "b",
            "mjpc_source_commit": "s",
            "qualification": {},
        }
        identity = {"binary_sha256": "b", "inputs": {"mjpc": {"head": "s"}}}
        plants, controllers, closed = [], [], []

        def plant_factory(*args):
            plant = FaultPlant(reason if not plants else None, fault_tick)
            plants.append(plant)
            return plant

        def controller_factory(name, *args, **kwargs):
            controller = FakeController()
            controllers.append((name, controller))
            return controller, lambda: closed.append(name)

        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            out = root / "run_fake"
            stack.enter_context(zero_step_guard())
            patches = {
                "ROOT": root,
                "experiment_lock": mock.MagicMock(),
                "validate_start_files": mock.Mock(
                    return_value={
                        "prepared": prepared,
                        "head": "h",
                        "review": {},
                        "authorization": {},
                    }
                ),
                "load_capture_plan": mock.Mock(return_value=plan),
                "_validate_output": mock.Mock(return_value=out),
                "current_head": mock.Mock(return_value="h"),
                "verify_bundle": mock.Mock(),
                "validate_reference": mock.Mock(),
                "digest": mock.Mock(return_value="r"),
                "verify_controller": mock.Mock(return_value=identity),
                "MujocoPlant": mock.Mock(side_effect=plant_factory),
                "validate_canonical_model": mock.Mock(),
                "_make_controller": mock.Mock(side_effect=controller_factory),
                "wall_deadline": mock.MagicMock(),
            }
            for key, value in patches.items():
                stack.enter_context(mock.patch.object(module, key, value))
            yield root, out, plan, plants, controllers, closed, patches

    def launch(self, out):
        return module.capture(
            "prepared", "review", "authorization", out, plan_path="v2"
        )

    def assert_sealed_stop(
        self, root, out, plants, controllers, closed, status, claims=1
    ):
        admission = verify_manifest(out)
        self.assertEqual(admission["status"], status)
        self.assertEqual(admission["integration_status"], "INCOMPLETE")
        self.assertEqual(admission["attempts"][1]["status"], "NOT_RUN")
        self.assertEqual(len(plants), 1)
        self.assertEqual([name for name, _ in controllers], ["rl"])
        self.assertEqual(closed, ["rl"])
        ledger = root / "_runs/substrate_attempts/aligned-flat-capture-v2"
        self.assertTrue((ledger / "campaign.json").is_file())
        self.assertEqual((ledger / "rl.json").exists(), bool(claims))
        self.assertFalse((ledger / "mjpc.json").exists())
        self.assertFalse((out / "mjpc.jsonl").exists())
        self.assertEqual(admission["live_runs"], claims)
        self.assertEqual(admission["scientific_attempts"], 0)
        with self.assertRaisesRegex(ValueError, "already claimed"):
            self.launch(root / "run_retry")
        self.assertEqual(len(plants), 1)
        return admission

    def test_all_canonical_stop_on_seal_campaign_and_retain_terminal_analysis(self):
        for reason in episode_fixture.AlignedEpisodeTest().task().stop_on:
            with self.subTest(reason=reason), self.fixture(reason=reason) as f:
                root, out, _, plants, controllers, closed, patches = f
                result = self.launch(out)
                self.assertEqual(result["status"], "SAFETY_STOP")
                self.assert_sealed_stop(
                    root, out, plants, controllers, closed, "SAFETY_STOP"
                )
                analysis = strict_json((out / "rl_analysis.json").read_text())
                self.assertEqual(analysis["classification"], "SAFETY_STOP")
                self.assertEqual(
                    analysis["replay"]["first_failure"], {"tick": 1, "reason": reason}
                )
                rows = [
                    strict_json(line)
                    for line in (out / "rl.jsonl").read_text().splitlines()
                ]
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[-1]["terminal_reason"], reason)
                self.assertFalse(rows[-1]["controller_update"])
                self.assertEqual(plants[0].steps, 1)  # FakePlant counter only.
                if reason == "nonfinite":
                    self.assertIsNone(rows[-1]["qvel"][0])
                patches["wall_deadline"].assert_called_once_with(300)

    def test_initial_safety_stop_has_no_consumed_attempt_but_seals_campaign(self):
        with self.fixture(reason="posture", fault_tick=0) as f:
            root, out, _, plants, controllers, closed, _ = f
            self.launch(out)
            self.assert_sealed_stop(
                root, out, plants, controllers, closed, "SAFETY_STOP", claims=0
            )

    def test_predeclared_horizon_metric_failures_continue_and_remain_failures(self):
        for metric in ("progress", "vx_mae"):
            with self.subTest(metric=metric), self.fixture(performance=metric) as f:
                root, out, _, plants, controllers, closed, patches = f
                result = self.launch(out)
                admission = verify_manifest(out)
                self.assertEqual(result["status"], "CAPTURE_COMPLETE")
                self.assertEqual(
                    [x["status"] for x in admission["attempts"]],
                    ["PERFORMANCE_FAIL", "PERFORMANCE_FAIL"],
                )
                self.assertEqual(len(plants), 2)
                self.assertEqual(closed, ["rl", "mjpc"])
                self.assertEqual(admission["live_runs"], 2)
                self.assertEqual(
                    patches["wall_deadline"].call_args_list,
                    [mock.call(300), mock.call(300)],
                )

    def test_unannounced_performance_failure_stops(self):
        with self.fixture(performance="progress", continue_policy=False) as f:
            root, out, _, plants, controllers, closed, _ = f
            self.launch(out)
            self.assert_sealed_stop(
                root, out, plants, controllers, closed, "PERFORMANCE_STOP"
            )

    def test_execution_and_replay_errors_seal_partial_evidence_without_next_arm(self):
        real_episode = module.run_aligned_episode
        for error in (
            RuntimeError("IPC/solver"),
            TimeoutError("wall_timeout"),
            ValueError("identity"),
        ):
            with self.subTest(error=str(error)), self.fixture() as f:
                root, out, _, plants, controllers, closed, _ = f

                def broken_episode(
                    plant, controller, task, info, timing, emit, consume
                ):
                    consume()
                    emit({"partial": "retained"})
                    raise error

                with mock.patch.object(
                    module, "run_aligned_episode", side_effect=broken_episode
                ):
                    with self.assertRaises(type(error)):
                        self.launch(out)
                self.assert_sealed_stop(
                    root, out, plants, controllers, closed, "FAILED"
                )
                self.assertEqual(
                    (out / "rl.jsonl").read_text(), '{"partial":"retained"}\n'
                )
                self.assertTrue((out / "rl_failure.json").is_file())
                self.assertTrue((out / "rl_claim.json").is_file())
        with self.fixture() as f:
            root, out, _, plants, controllers, closed, _ = f
            with mock.patch.object(
                module, "replay_aligned_rows", side_effect=ValueError("bad replay")
            ):
                with self.assertRaisesRegex(ValueError, "bad replay"):
                    self.launch(out)
            self.assert_sealed_stop(root, out, plants, controllers, closed, "FAILED")
            self.assertEqual(len((out / "rl.jsonl").read_text().splitlines()), 5)
        self.assertIs(module.run_aligned_episode, real_episode)

    def test_analysis_write_error_preserves_raw_and_claim_and_stops(self):
        real_write = module.write_new
        with self.fixture() as f:
            root, out, _, plants, controllers, closed, _ = f

            def write(path, value):
                if Path(path).name == "rl_analysis.json":
                    raise OSError("analysis storage failure")
                return real_write(path, value)

            with mock.patch.object(module, "write_new", side_effect=write):
                with self.assertRaisesRegex(OSError, "analysis storage"):
                    self.launch(out)
            self.assert_sealed_stop(root, out, plants, controllers, closed, "FAILED")
            self.assertTrue((out / "rl_claim.json").exists())
            self.assertTrue((out / "rl.jsonl").exists())

    def test_identity_error_before_plant_stops_without_claim(self):
        with self.fixture() as f:
            root, out, _, plants, controllers, closed, patches = f
            patches["verify_controller"].side_effect = ValueError("identity drift")
            with self.assertRaisesRegex(ValueError, "identity drift"):
                self.launch(out)
            admission = verify_manifest(out)
            self.assertEqual(admission["status"], "FAILED")
            self.assertEqual(admission["attempts"][1]["status"], "NOT_RUN")
            self.assertFalse(plants)
            self.assertFalse(controllers)
            self.assertFalse(closed)
            self.assertFalse((out / "rl_claim.json").exists())

    def test_v2_stop_and_deadline_policy_drift_rejected(self):
        plan = module.load_capture_plan(
            Path("tools/substrate/protocols/aligned_flat_capture_v2.json")
        )
        for key in (
            "safety_failure_policy",
            "execution_evidence_failure_policy",
            "horizon_performance_failure_policy",
            "wall_timeout_scope",
        ):
            with self.subTest(key=key):
                raw = copy.deepcopy(plan["raw"])
                raw[key] = "changed"
                with self.assertRaisesRegex(ValueError, "drifted"):
                    module.validate_capture_plan(raw)

    def test_owned_close_exception_seals_raw_claim_without_next_arm(self):
        with self.fixture() as f:
            root, out, _, plants, controllers, closed, patches = f
            original = patches["_make_controller"].side_effect

            def factory(*args, **kwargs):
                controller, close = original(*args, **kwargs)

                def broken_close():
                    close()
                    raise RuntimeError("owned close failure")

                return controller, broken_close

            patches["_make_controller"].side_effect = factory
            with self.assertRaisesRegex(RuntimeError, "owned close"):
                self.launch(out)
            self.assert_sealed_stop(root, out, plants, controllers, closed, "FAILED")
            self.assertEqual(len((out / "rl.jsonl").read_text().splitlines()), 5)

    def test_run_claim_write_failure_retains_durable_consumed_claim(self):
        real_write = module.write_new
        with self.fixture() as f:
            root, out, _, plants, controllers, closed, _ = f

            def write(path, value):
                if Path(path).name == "rl_claim.json":
                    raise OSError("claim evidence storage failure")
                return real_write(path, value)

            with mock.patch.object(module, "write_new", side_effect=write):
                with self.assertRaisesRegex(OSError, "claim evidence"):
                    self.launch(out)
            admission = verify_manifest(out)
            ledger = root / "_runs/substrate_attempts/aligned-flat-capture-v2"
            self.assertTrue((ledger / "rl.json").is_file())
            self.assertFalse((ledger / "mjpc.json").exists())
            self.assertEqual(admission["status"], "FAILED")
            self.assertEqual(admission["attempts"][1]["status"], "NOT_RUN")
            failure = strict_json((out / "rl_failure.json").read_text())
            self.assertTrue(failure["attempt_consumed"])
            self.assertEqual(admission["live_runs"], 1)
            self.assertEqual(closed, ["rl"])
            with self.assertRaisesRegex(ValueError, "already claimed"):
                self.launch(root / "run_retry")

    def test_second_arm_identity_error_retains_first_analysis_without_second_plant(
        self,
    ):
        with self.fixture() as f:
            root, out, _, plants, controllers, closed, patches = f
            identity = patches["verify_controller"].return_value
            patches["verify_controller"].side_effect = [
                identity,
                ValueError("next identity drift"),
            ]
            with self.assertRaisesRegex(ValueError, "next identity"):
                self.launch(out)
            admission = verify_manifest(out)
            self.assertEqual(admission["status"], "FAILED")
            self.assertEqual(admission["attempts"][0]["status"], "PASS")
            self.assertEqual(len(plants), 1)
            self.assertEqual(closed, ["rl"])
            self.assertTrue((out / "rl_analysis.json").is_file())
            self.assertFalse((out / "mjpc_claim.json").exists())


if __name__ == "__main__":
    unittest.main()
