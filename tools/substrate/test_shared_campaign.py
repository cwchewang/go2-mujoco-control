"""Claim/stop fixtures are FakePlant only; compiled models use forward and synthetic clocks."""

import copy
import json
from collections import deque
from contextlib import ExitStack, contextmanager
from dataclasses import replace
import fcntl
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from . import shared_campaign as module
from . import test_aligned_episode as fixtures
from . import test_campaign_stop as stops
from .aligned_episode import run_aligned_episode
from .bounded_conditions import BoundedCondition, condition_specs
from .condition_evidence import verify_condition
from .contracts import WholeBodyState
from .episode import MujocoPlant
from .guards import zero_step_guard
from .integrity import (
    EvidenceRun,
    experiment_lock,
    strict_json,
    verify_manifest,
    write_new,
)
from .shared_baseline import load_plan


class FixtureCondition(BoundedCondition):
    """Lifecycle fixture only; real condition effects are tested independently."""

    def reset(self, plant, information, timing):
        self.information = information
        self.history = deque(maxlen=11)
        self.last_tick = -1
        self.initial = self.payload(plant)
        self.delayed_updates = 0
        return self.initial

    def before_step(self, plant, tick):
        return {"id": self.name, "tick": tick, "fake_condition_fixture": True}

    def complete(self):
        return {"fake_condition_fixture": True}

    def finish(self, plant):
        pass


class ClockController(fixtures.FakeController):
    def __init__(self, task, control_ticks=10):
        super().__init__()
        self.task = task
        self.control_ticks = control_ticks
        self.tick = 0
        self.sampled = None
        self.requested = None

    def step(self, observation, command):
        if isinstance(observation, WholeBodyState):
            self.tick = round(observation.time_s / 0.002)
        self.requested = [float(value) for value in command]
        if self.tick % self.control_ticks == 0:
            self.sampled = [float(value) for value in command]
        return super().step(observation, command)

    def diagnostics(self):
        replan = self.tick % self.control_ticks == 0
        return {
            "controller": {
                "control_period_s": self.control_ticks * 0.002,
                "feedback_period_s": 0.002,
                "last_step": {
                    "replanned": replan,
                    "planning_compute_s": 0.0001 if replan else 0,
                    "requested_command": self.requested,
                    "sampled_command": self.sampled,
                },
            }
        }


class CampaignFixture(unittest.TestCase):
    def setUp(self):
        guard = zero_step_guard()
        guard.__enter__()
        self.addCleanup(guard.__exit__, None, None, None)

    @contextmanager
    def fixture(
        self,
        *,
        reason=None,
        fault_tick=1,
        performance=False,
        mismatch=False,
        real_prepare=False,
    ):
        plan = copy.deepcopy(load_plan())
        plan["task"] = replace(
            plan["task"],
            horizon_ticks=32,
            measurement_start_tick=1,
            zero_command_ticks=0,
            ramp_ticks=1,
        )
        original_execute = module._execute_arm
        plants, controllers, closed, requested = [], [], [], []
        active = {}
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            prepared_dir = root / "prepared"
            lock_path = root / "fixture.lock"
            out = root / plan["raw"]["output_root"] / "run_fake"
            qdir = root / "qualification"
            with EvidenceRun(qdir) as qrun:
                qrun.result.update(
                    status="ENGINEERING_ADMITTED",
                    qualification={"head": "h"},
                    qualification_fingerprint="fake-qualification-fingerprint",
                )
            qualification = {
                "path": str(qdir.resolve()),
                "manifest_sha256": module.digest(qdir / "manifest.json"),
                "producer_head": "h",
                "fingerprint": "fake-qualification-fingerprint",
            }
            if real_prepare:
                sources = strict_json(module.base.LOCK.read_text())
                native = {
                    "binary_sha256": "b",
                    "inputs": {"mjpc": {"head": sources["mjpc"]["commit"]}},
                }
                with (
                    mock.patch.object(module, "current_head", return_value="h"),
                    mock.patch.object(
                        module, "validate_qualification", return_value=qualification
                    ),
                    mock.patch.object(
                        module.base, "verify_controller", return_value=native
                    ),
                    mock.patch.object(
                        module,
                        "experiment_lock",
                        side_effect=lambda: experiment_lock(lock_path),
                    ),
                    mock.patch.object(
                        module,
                        "NativeMJPCController",
                        side_effect=AssertionError(
                            "no private controller in preparation"
                        ),
                    ),
                    mock.patch.object(
                        module,
                        "FrozenPolicy",
                        side_effect=AssertionError(
                            "no policy inference in preparation"
                        ),
                    ),
                ):
                    module.prepare(
                        prepared_dir,
                        qualification_path=qdir,
                        plan_path=module.DEFAULT_PLAN,
                    )
                prepared = verify_manifest(prepared_dir)
            else:
                with EvidenceRun(prepared_dir) as prun:
                    with (prepared_dir / "frozen-protocol.json").open("xb") as stream:
                        stream.write(module.DEFAULT_PLAN.read_bytes())
                    write_new(prepared_dir / "capture-plan.json", plan["raw"])
                    prun.result.update(
                        status="ENGINEERING_ADMITTED",
                        scope="shared_campaign_preparation",
                        head="h",
                        readiness="AWAITING_EXACT_HEAD_REVIEWS_AND_BOUND_DELEGATION",
                        qualification=qualification,
                        rl_checkpoint_sha256="r",
                        mjpc_binary_sha256="b",
                        mjpc_source_commit="s",
                        protocol_sha256=module.digest(module.DEFAULT_PLAN),
                        capture_plan_sha256=module.digest(
                            prepared_dir / "capture-plan.json"
                        ),
                        anchor_sha256=plan["raw"]["anchor_sha256"],
                        max_attempts=20,
                        physics_steps_max=120000,
                        planned_arms=module.arms(plan),
                    )
                prepared = verify_manifest(prepared_dir)
            review = {
                "head": "h",
                "science": {
                    "verdict": "APPROVED",
                    "reviewer": "fake-science",
                    "evidence": "FakePlant",
                },
                "execution": {
                    "verdict": "APPROVED",
                    "reviewer": "fake-execution",
                    "evidence": "FakePlant",
                },
            }
            authorization = {
                "action": "START_FORMAL_CAPTURE",
                "head": "h",
                "protocol_sha256": prepared["protocol_sha256"],
                "prepared_manifest_sha256": module.digest(
                    prepared_dir / "manifest.json"
                ),
                "max_attempts": 20,
                "authorized_by": "user",
                "user_instruction": "FAKE FIXTURE ONLY; no real live authorization",
                "task_id": plan["raw"]["id"],
            }

            def assert_lock():
                with lock_path.open("a") as other:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            def preflight(lock, *args):
                self.assertGreaterEqual(lock.fileno(), 0)
                assert_lock()
                return {"fake_preflight": True}

            def execute(item, *args):
                active["id"] = item["id"]
                requested.append(item["id"])
                return original_execute(item, *args)

            def plant_factory(*args):
                assert_lock()
                p = stops.FaultPlant(reason if not plants else None, fault_tick)
                original = p.snapshot
                case = active["id"]

                def snapshot(tick):
                    row = original(tick)
                    if performance and case == "rl_baseline_1" and tick:
                        row["qvel"][0] = 0.5
                    if mismatch and case == "rl_baseline_2" and tick:
                        row["qpos"][0] += 1e-5
                    return row

                p.snapshot = snapshot
                plants.append(p)
                return p

            def controller_factory(name, timing, prepared, stderr):
                assert_lock()
                case = active["id"]
                c = fixtures.FakeController()
                controllers.append(case)
                return c, lambda: closed.append(case)

            patches = {
                "ROOT": root,
                "experiment_lock": lambda: experiment_lock(lock_path),
                "load_plan": mock.Mock(return_value=plan),
                "current_head": mock.Mock(return_value="h"),
                "validate_start_files": mock.Mock(
                    return_value=(plan, prepared, "h", review, authorization)
                ),
                "_fresh_preflight": mock.Mock(side_effect=preflight),
                "_identity": mock.Mock(),
                "MujocoPlant": mock.Mock(side_effect=plant_factory),
                "validate_canonical_model": mock.Mock(),
                "_make_controller": mock.Mock(side_effect=controller_factory),
                "_execute_arm": mock.Mock(side_effect=execute),
                "BoundedCondition": FixtureCondition,
                "verify_condition": mock.Mock(
                    return_value={
                        "effective_complete_horizon": True,
                        "exposure_status": "FAKE_CONDITION_FIXTURE",
                    }
                ),
                "wall_deadline": mock.MagicMock(),
            }
            for key, value in patches.items():
                stack.enter_context(mock.patch.object(module, key, value))
            setup = stack.enter_context(
                mock.patch.object(module.base, "_setup_runtime")
            )
            yield (
                root,
                out,
                prepared_dir,
                plan,
                plants,
                controllers,
                closed,
                requested,
                patches,
                setup,
            )

    def launch(self, out, prepared):
        return module.capture(prepared, "fake-review", "fake-authorization", out)

    def test_all20_claims_fresh_instances_pairing_and_single_runtime_setup(self):
        with self.fixture() as (
            _,
            out,
            prepared,
            plan,
            plants,
            controllers,
            closed,
            requested,
            _,
            setup,
        ):
            result = self.launch(out, prepared)
            record = verify_manifest(out)
            self.assertEqual(result["status"], "CAPTURE_COMPLETE")
            self.assertEqual(result["scientific_attempts"], 20)
            self.assertEqual(len(plants), 20)
            self.assertEqual(len(set(id(p) for p in plants)), 20)
            self.assertEqual(closed, controllers)
            self.assertEqual(requested, [a["id"] for a in module.arms(plan)])
            setup.assert_called_once()
            for arm in record["attempts"][4:]:
                self.assertEqual(
                    arm["reference_baseline"],
                    f"{arm['controller']}_baseline_{arm['repeat']}",
                )
            verified = module.verify_capture(out)
            self.assertEqual(verified["scientific_attempts_checked"], 20)

    def test_six_safety_conditions_stop_whole_campaign(self):
        for reason in (
            "nonfinite",
            "orientation",
            "physics_warning",
            "nonfoot_contact",
            "posture",
            "lateral",
        ):
            with (
                self.subTest(reason=reason),
                self.fixture(reason=reason) as (
                    _,
                    out,
                    prepared,
                    _,
                    plants,
                    _,
                    closed,
                    requested,
                    _,
                    _,
                ),
            ):
                result = self.launch(out, prepared)
                record = verify_manifest(out)
                self.assertEqual(result["status"], "SAFETY_STOP")
                self.assertEqual(result["scientific_attempts"], 1)
                self.assertEqual(len(plants), 1)
                self.assertEqual(len(closed), 1)
                self.assertEqual(requested, ["rl_baseline_1"])
                self.assertEqual(
                    module.verify_capture(out)["scientific_attempts_checked"], 1
                )
                for arm in record["attempts"][1:]:
                    self.assertEqual(arm["status"], "NOT_RUN")
                    self.assertIn(
                        "campaign_stopped:rl_baseline_1", arm["not_run_reason"]
                    )

    def test_initial_safety_stops_with_zero_claims_and_zero_steps(self):
        with self.fixture(reason="physics_warning", fault_tick=0) as (
            _,
            out,
            prepared,
            _,
            plants,
            _,
            closed,
            requested,
            _,
            _,
        ):
            result = self.launch(out, prepared)
            record = verify_manifest(out)
            self.assertEqual(result["status"], "SAFETY_STOP")
            self.assertEqual(result["scientific_attempts"], 0)
            self.assertEqual(result["canonical_physics_steps"], 0)
            self.assertEqual(len(plants), 1)
            self.assertEqual(len(closed), 1)
            self.assertEqual(requested, ["rl_baseline_1"])
            first = record["attempts"][0]
            self.assertFalse(first["analysis"]["episode"]["attempt_consumed"])
            self.assertEqual(first["analysis"]["frames"], 1)
            self.assertFalse((out / "rl_baseline_1_claim.json").exists())
            self.assertTrue(
                all(
                    a["status"] == "NOT_RUN"
                    and "campaign_stopped:" in a["not_run_reason"]
                    for a in record["attempts"][1:]
                )
            )
            self.assertEqual(
                module.verify_capture(out)["scientific_attempts_checked"], 0
            )

    def test_performance_failure_retained_blocks_only_own_challenges(self):
        with self.fixture(performance=True) as (
            _,
            out,
            prepared,
            _,
            plants,
            _,
            _,
            requested,
            _,
            _,
        ):
            result = self.launch(out, prepared)
            record = verify_manifest(out)
            self.assertEqual(result["status"], "CAPTURE_COMPLETE")
            self.assertEqual(result["scientific_attempts"], 12)
            self.assertEqual(len(plants), 12)
            self.assertEqual(record["attempts"][0]["status"], "PERFORMANCE_FAIL")
            self.assertIn("rl_baseline_2", requested)
            for arm in record["attempts"][4:12]:
                self.assertEqual(arm["status"], "NOT_RUN")
                self.assertEqual(arm["not_run_reason"], "own_baseline_not_passing")
                self.assertFalse((out / (arm["id"] + ".jsonl")).exists())

    def test_nonrepeatable_baseline_blocks_own_challenges(self):
        with self.fixture(mismatch=True) as (_, out, prepared, _, _, _, _, _, _, _):
            result = self.launch(out, prepared)
            record = verify_manifest(out)
            self.assertEqual(result["scientific_attempts"], 12)
            self.assertEqual(
                record["baseline_eligibility"]["rl"]["reason"],
                "own_baseline_nonrepeatable",
            )
            self.assertEqual(
                module.verify_capture(out)["scientific_attempts_checked"], 12
            )

    def test_execution_boot_failure_claims_zero_and_closes_all_remaining(self):
        with self.fixture() as (_, out, prepared, _, _, _, _, _, patches, _):
            patches["_make_controller"].side_effect = RuntimeError("boot fixture")
            result = self.launch(out, prepared)
            record = verify_manifest(out)
            self.assertEqual(result["status"], "EXECUTION_EVIDENCE_STOP")
            self.assertEqual(result["scientific_attempts"], 0)
            self.assertTrue(all(a["not_run_reason"] for a in record["attempts"][1:]))

    def test_claim_copy_failure_retains_authoritative_single_claim(self):
        with self.fixture() as (root, out, prepared, plan, _, _, _, _, _, _):
            original = module.write_new

            def fail_copy(path, value):
                if Path(path).name == "rl_baseline_1_claim.json":
                    raise OSError("claim copy fixture")
                return original(path, value)

            with mock.patch.object(module, "write_new", side_effect=fail_copy):
                result = self.launch(out, prepared)
            ledger = root / "_runs/substrate_attempts" / plan["raw"]["id"]
            self.assertTrue((ledger / "rl_baseline_1.json").exists())
            self.assertEqual(result["scientific_attempts"], 1)
            self.assertEqual(result["status"], "EXECUTION_EVIDENCE_STOP")

    def test_duplicate_consume_stops_without_second_claim(self):
        with self.fixture() as (_, out, prepared, _, _, _, _, _, _, _):

            def double(*args, **kwargs):
                consume = args[6]
                consume()
                consume()

            with mock.patch.object(module, "run_aligned_episode", side_effect=double):
                result = self.launch(out, prepared)
            self.assertEqual(result["scientific_attempts"], 1)
            self.assertEqual(result["status"], "EXECUTION_EVIDENCE_STOP")

    def test_unexposed_horizon_stops_and_remaining_not_run(self):
        with self.fixture() as (_, out, prepared, _, _, _, _, _, patches, _):
            patches["verify_condition"].return_value = {
                "effective_complete_horizon": False,
                "exposure_status": "NOT_EXPOSED_HORIZON",
            }
            result = self.launch(out, prepared)
            record = verify_manifest(out)
            self.assertEqual(result["status"], "EXPOSURE_EVIDENCE_STOP")
            self.assertEqual(result["scientific_attempts"], 5)
            self.assertEqual(
                record["attempts"][4]["analysis"]["condition_evidence"][
                    "exposure_status"
                ],
                "NOT_EXPOSED_HORIZON",
            )
            self.assertTrue(
                all(
                    a["status"] == "NOT_RUN" and a["not_run_reason"]
                    for a in record["attempts"][5:]
                )
            )

    def test_gate_failure_creates_no_output_no_plant_no_claim(self):
        with self.fixture() as (root, out, prepared, plan, plants, _, _, _, patches, _):
            patches["validate_start_files"].side_effect = ValueError(
                "missing exact review"
            )
            with self.assertRaisesRegex(ValueError, "exact review"):
                self.launch(out, prepared)
            self.assertFalse(out.exists())
            self.assertFalse(
                (root / "_runs/substrate_attempts" / plan["raw"]["id"]).exists()
            )
            self.assertEqual(plants, [])
            patches["_fresh_preflight"].assert_not_called()

    def test_existing_campaign_never_retried(self):
        with self.fixture(reason="physics_warning") as (
            _,
            out,
            prepared,
            _,
            plants,
            _,
            _,
            _,
            patches,
            _,
        ):
            self.launch(out, prepared)
            self.assertEqual(len(plants), 1)
            with self.assertRaisesRegex(ValueError, "already exists"):
                self.launch(out.with_name("run_replacement"), prepared)
            self.assertEqual(len(plants), 1)
            self.assertEqual(patches["_fresh_preflight"].call_count, 1)

    def test_external_ledger_tamper_is_rejected_by_offline_verifier(self):
        with self.fixture(reason="physics_warning") as (
            root,
            out,
            prepared,
            plan,
            _,
            _,
            _,
            _,
            _,
            _,
        ):
            self.launch(out, prepared)
            path = (
                root
                / "_runs/substrate_attempts"
                / plan["raw"]["id"]
                / "rl_baseline_1.json"
            )
            claim = strict_json(path.read_text())
            claim["head"] = "wrong"
            path.write_text(__import__("json").dumps(claim))
            with self.assertRaisesRegex(ValueError, "external claim"):
                module.verify_capture(out)

    def rewrite_fake_json(self, path, value):
        # Mutation tests affect only TemporaryDirectory fixtures, never raw runs.
        self.assertIn("run_fake", str(path))
        Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

    def reseal_fake(self, out, record):
        self.assertEqual(record["head"], "h")
        self.rewrite_fake_json(out / "admission.json", record)
        self.rewrite_fake_json(
            out / "manifest.json",
            {
                p.relative_to(out).as_posix(): module.digest(p)
                for p in out.rglob("*")
                if p.is_file() and p.name != "manifest.json"
            },
        )

    def replace_fake_raw(self, out, item, rows, plan):
        path = out / (item["id"] + ".jsonl")
        self.assertIn("run_fake", str(path))
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
        replay = module.replay_baseline(rows, plan)
        item["physics_steps"] = rows[-1]["tick"]
        item["status"] = replay["classification"]
        analysis = item["analysis"]
        analysis.update(
            replay=replay,
            classification=replay["classification"],
            raw_sha256=module.digest(path),
            frames=len(rows),
            physics_steps=item["physics_steps"],
        )
        analysis["episode"].update(
            steps=item["physics_steps"], terminal_reason=rows[-1]["terminal_reason"]
        )
        self.rewrite_fake_json(out / (item["id"] + "_analysis.json"), analysis)

    def bind_fake_snapshot(self, root, out, record, plan):
        eligibility = {
            name: module._eligibility(name, out, record["attempts"], plan)
            for name in ("rl", "mjpc")
        }
        self.rewrite_fake_json(
            out / "baseline-eligibility.json", {"head": "h", "eligibility": eligibility}
        )
        snapshot_sha = module.digest(out / "baseline-eligibility.json")
        record["baseline_eligibility"] = eligibility
        record["baseline_eligibility_sha256"] = snapshot_sha
        ledger = root / "_runs/substrate_attempts" / plan["raw"]["id"]
        for item in record["attempts"][4:]:
            if item["status"] == "NOT_RUN":
                continue
            own = eligibility[item["controller"]]
            reference = next(
                b for b in own["baselines"] if b["id"] == item["reference_baseline"]
            )
            item.update(
                baseline_eligibility_sha256=snapshot_sha,
                reference_baseline_sha256=reference["raw_sha256"],
            )
            claim_path = out / (item["id"] + "_claim.json")
            claim = strict_json(claim_path.read_text())
            claim.update(
                baseline_eligibility_sha256=snapshot_sha,
                reference_baseline_sha256=reference["raw_sha256"],
            )
            self.rewrite_fake_json(claim_path, claim)
            # External ledger here belongs to this same temporary FakePlant fixture.
            (ledger / (item["id"] + ".json")).write_text(
                json.dumps(claim, indent=2, sort_keys=True) + "\n"
            )

    def test_challenge_claims_bind_frozen_qualification_and_reference(self):
        with self.fixture() as (root, out, prepared, plan, _, _, _, _, _, _):
            self.launch(out, prepared)
            record = verify_manifest(out)
            snapshot = strict_json((out / "baseline-eligibility.json").read_text())
            self.assertEqual(snapshot["eligibility"], record["baseline_eligibility"])
            sha = module.digest(out / "baseline-eligibility.json")
            for arm in record["attempts"][4:]:
                claim = strict_json((out / (arm["id"] + "_claim.json")).read_text())
                self.assertEqual(claim["baseline_eligibility_sha256"], sha)
                self.assertEqual(
                    claim["reference_baseline_sha256"],
                    module.digest(out / (arm["reference_baseline"] + ".jsonl")),
                )
            verified = module.verify_capture(out)
            self.assertTrue(verified["baseline_eligibility_recomputed"])
            self.assertTrue(verified["skip_stop_sequence_checked"])

    def test_frozen_baseline_change_stops_before_challenge_plant_claim(self):
        with self.fixture() as (_, out, prepared, _, plants, _, _, _, patches, _):
            execute = patches["_execute_arm"].side_effect

            def change(item, *args):
                if item["stage"] == "challenge":
                    path = out / "rl_baseline_1.jsonl"
                    path.write_text(path.read_text() + "\n")
                return execute(item, *args)

            patches["_execute_arm"].side_effect = change
            result = self.launch(out, prepared)
            self.assertEqual(result["status"], "EXECUTION_EVIDENCE_STOP")
            self.assertEqual(result["scientific_attempts"], 4)
            self.assertEqual(len(plants), 4)
            self.assertFalse((out / "rl_sliding_friction_1_claim.json").exists())

    def test_failed_or_nonrepeatable_baseline_entering_challenge_rejected(self):
        for mode in ("performance", "repeat"):
            with (
                self.subTest(mode=mode),
                self.fixture() as (root, out, prepared, plan, _, _, _, _, _, _),
            ):
                self.launch(out, prepared)
                record = verify_manifest(out)
                item = record["attempts"][0 if mode == "performance" else 1]
                rows = module._read_rows(out / (item["id"] + ".jsonl"))
                for row in rows[1:]:
                    if mode == "performance":
                        row["qvel"][0] = 0.5
                    else:
                        row["qpos"][0] += 1e-5
                self.replace_fake_raw(out, item, rows, plan)
                self.bind_fake_snapshot(root, out, record, plan)
                self.reseal_fake(out, record)
                with self.assertRaisesRegex(
                    ValueError, "ineligible baseline entered challenge"
                ):
                    module.verify_capture(out)

    def test_stop_followed_by_execution_rejected(self):
        with self.fixture() as (_, out, prepared, plan, _, _, _, _, _, _):
            self.launch(out, prepared)
            record = verify_manifest(out)
            item = record["attempts"][0]
            rows = module._read_rows(out / "rl_baseline_1.jsonl")[:2]
            rows[-1].update(
                warning_count=1,
                failure="physics_warning",
                terminal_reason="physics_warning",
                controller_update=False,
                information=None,
                controller_diagnostics=None,
                target=None,
                action=None,
            )
            self.replace_fake_raw(out, item, rows, plan)
            record.update(
                status="SAFETY_STOP",
                campaign_complete=False,
                stopped_case=item["id"],
                canonical_physics_steps=sum(
                    a.get("physics_steps", 0) for a in record["attempts"]
                ),
            )
            self.reseal_fake(out, record)
            with self.assertRaisesRegex(ValueError, "executed after campaign stop"):
                module.verify_capture(out)

    def test_raw_sha_drift_rejected_even_resealed(self):
        with self.fixture() as (_, out, prepared, _, _, _, _, _, _, _):
            self.launch(out, prepared)
            record = verify_manifest(out)
            raw = out / "rl_baseline_1.jsonl"
            raw.write_text(raw.read_text() + "\n")
            self.reseal_fake(out, record)
            with self.assertRaisesRegex(ValueError, "raw SHA"):
                module.verify_capture(out)

    def test_missing_analysis_never_verified(self):
        for delete_copy in (False, True):
            with (
                self.subTest(delete_copy=delete_copy),
                self.fixture() as (_, out, prepared, _, _, _, _, _, _, _),
            ):
                self.launch(out, prepared)
                record = verify_manifest(out)
                if delete_copy:
                    (out / "rl_baseline_1_analysis.json").unlink()
                else:
                    del record["attempts"][0]["analysis"]
                self.reseal_fake(out, record)
                with self.assertRaisesRegex(ValueError, "missing analysis"):
                    module.verify_capture(out)

    def test_reference_hash_tamper_rejected_even_copies_agree(self):
        for change_item in (False, True):
            with (
                self.subTest(change_item=change_item),
                self.fixture() as (root, out, prepared, plan, _, _, _, _, _, _),
            ):
                self.launch(out, prepared)
                record = verify_manifest(out)
                item = record["attempts"][4]
                copy = out / (item["id"] + "_claim.json")
                claim = strict_json(copy.read_text())
                claim["reference_baseline_sha256"] = "0" * 64
                self.rewrite_fake_json(copy, claim)
                ledger = root / "_runs/substrate_attempts" / plan["raw"]["id"]
                (ledger / (item["id"] + ".json")).write_text(
                    json.dumps(claim, indent=2, sort_keys=True) + "\n"
                )
                if change_item:
                    item["reference_baseline_sha256"] = "0" * 64
                self.reseal_fake(out, record)
                with self.assertRaisesRegex(ValueError, "reference binding"):
                    module.verify_capture(out)

    def test_forged_snapshot_rejected_from_independent_replay(self):
        with self.fixture() as (_, out, prepared, _, _, _, _, _, _, _):
            self.launch(out, prepared)
            record = verify_manifest(out)
            record["baseline_eligibility"]["rl"]["eligible"] = False
            self.rewrite_fake_json(
                out / "baseline-eligibility.json",
                {"head": "h", "eligibility": record["baseline_eligibility"]},
            )
            record["baseline_eligibility_sha256"] = module.digest(
                out / "baseline-eligibility.json"
            )
            self.reseal_fake(out, record)
            with self.assertRaisesRegex(
                ValueError, "eligibility differs from raw replay"
            ):
                module.verify_capture(out)

    def test_wrong_eligibility_skip_reason_rejected(self):
        with self.fixture(performance=True) as (_, out, prepared, _, _, _, _, _, _, _):
            self.launch(out, prepared)
            self.assertEqual(
                module.verify_capture(out)["scientific_attempts_checked"], 12
            )
            record = verify_manifest(out)
            record["attempts"][4]["not_run_reason"] = "arbitrary_closed_reason"
            self.reseal_fake(out, record)
            with self.assertRaisesRegex(ValueError, "skipped arm reason"):
                module.verify_capture(out)

    def test_campaign_completion_lie_rejected(self):
        with self.fixture() as (_, out, prepared, _, _, _, _, _, _, _):
            self.launch(out, prepared)
            record = verify_manifest(out)
            record.update(
                status="SAFETY_STOP",
                campaign_complete=False,
                stopped_case="rl_baseline_1",
            )
            self.reseal_fake(out, record)
            with self.assertRaisesRegex(ValueError, "completion differs"):
                module.verify_capture(out)

    def test_real_protocol_normal_prepare_capture_verify_uses_two_identities(self):
        with self.fixture(real_prepare=True) as (_, out, prepared, _, _, _, _, _, _, _):
            p = verify_manifest(prepared)
            original = module.DEFAULT_PLAN.read_bytes()
            self.assertEqual((prepared / "frozen-protocol.json").read_bytes(), original)
            self.assertEqual(p["protocol_sha256"], module.digest(module.DEFAULT_PLAN))
            self.assertEqual(
                p["protocol_sha256"],
                "76c94c60b98d4dc452ea3c18e2746f6b39990b061e894013462173715e467265",
            )
            self.assertEqual(
                p["capture_plan_sha256"],
                "42f509301c8d24e94121bddf4e100476c5849d465326ea93959e8e527d2e494d",
            )
            self.assertNotEqual(p["protocol_sha256"], p["capture_plan_sha256"])
            self.assertEqual(p["canonical_physics_steps"], 0)
            self.assertEqual(p["private_planning_calls"], 0)
            self.launch(out, prepared)
            record = verify_manifest(out)
            claim = strict_json((out / "campaign-claim.json").read_text())
            for key in ("protocol_sha256", "capture_plan_sha256"):
                self.assertEqual(claim[key], p[key])
                self.assertEqual(record[key], p[key])
            self.assertEqual((out / "frozen-protocol.json").read_bytes(), original)
            self.assertEqual(
                (out / "capture-plan.json").read_bytes(),
                (prepared / "capture-plan.json").read_bytes(),
            )
            self.assertEqual(
                claim["prepared_manifest_sha256"],
                module.digest(prepared / "manifest.json"),
            )
            self.assertEqual(
                module.verify_capture(out)["scientific_attempts_checked"], 20
            )

    def test_swapped_original_archive_campaign_identities_rejected(self):
        for key in ("protocol_sha256", "capture_plan_sha256"):
            with (
                self.subTest(key=key),
                self.fixture() as (root, out, prepared, plan, _, _, _, _, _, _),
            ):
                self.launch(out, prepared)
                record = verify_manifest(out)
                claim = strict_json((out / "campaign-claim.json").read_text())
                other = (
                    "capture_plan_sha256"
                    if key == "protocol_sha256"
                    else "protocol_sha256"
                )
                claim[key] = claim[other]
                self.rewrite_fake_json(out / "campaign-claim.json", claim)
                ledger = root / "_runs/substrate_attempts" / plan["raw"]["id"]
                (ledger / "campaign.json").write_text(
                    json.dumps(claim, indent=2, sort_keys=True) + "\n"
                )
                self.reseal_fake(out, record)
                with self.assertRaisesRegex(
                    ValueError, "campaign claim binding differs"
                ):
                    module.verify_capture(out)

    def test_capture_original_or_archive_byte_drift_rejected(self):
        for name in ("frozen-protocol.json", "capture-plan.json"):
            with (
                self.subTest(name=name),
                self.fixture() as (_, out, prepared, _, _, _, _, _, _, _),
            ):
                self.launch(out, prepared)
                record = verify_manifest(out)
                path = out / name
                path.write_bytes(path.read_bytes() + b"\n")
                self.reseal_fake(out, record)
                with self.assertRaisesRegex(
                    ValueError, "protocol/archive plan identity"
                ):
                    module.verify_capture(out)

    def test_preparation_manifest_reference_tamper_rejected(self):
        with self.fixture() as (_, out, prepared, _, _, _, _, _, _, _):
            self.launch(out, prepared)
            record = verify_manifest(out)
            reference = strict_json((out / "preparation-reference.json").read_text())
            reference["manifest_sha256"] = "0" * 64
            self.rewrite_fake_json(out / "preparation-reference.json", reference)
            self.reseal_fake(out, record)
            with self.assertRaisesRegex(ValueError, "capture/preparation reference"):
                module.verify_capture(out)

    def test_authorization_protocol_must_bind_original_identity(self):
        with self.fixture() as (_, out, prepared, _, _, _, _, _, _, _):
            self.launch(out, prepared)
            record = verify_manifest(out)
            auth = strict_json((out / "authorization.json").read_text())
            auth["protocol_sha256"] = record["capture_plan_sha256"]
            self.rewrite_fake_json(out / "authorization.json", auth)
            self.reseal_fake(out, record)
            with self.assertRaisesRegex(ValueError, "start authorization"):
                module.verify_capture(out)

    def test_qualification_reference_tamper_rejected_after_outer_rebinding(self):
        with self.fixture() as (root, out, prepared, plan, _, _, _, _, _, _):
            self.launch(out, prepared)
            record = verify_manifest(out)
            p = verify_manifest(prepared)
            p["qualification"]["manifest_sha256"] = "0" * 64
            # Both preparation and qualification are temporary fixtures here.
            self.assertTrue(prepared.is_relative_to(root))
            (prepared / "admission.json").write_text(
                json.dumps(p, indent=2, sort_keys=True) + "\n"
            )
            (prepared / "manifest.json").write_text(
                json.dumps(
                    {
                        item.relative_to(prepared).as_posix(): module.digest(item)
                        for item in prepared.rglob("*")
                        if item.is_file() and item.name != "manifest.json"
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            sha = module.digest(prepared / "manifest.json")
            ref = strict_json((out / "preparation-reference.json").read_text())
            ref["manifest_sha256"] = sha
            self.rewrite_fake_json(out / "preparation-reference.json", ref)
            auth = strict_json((out / "authorization.json").read_text())
            auth["prepared_manifest_sha256"] = sha
            self.rewrite_fake_json(out / "authorization.json", auth)
            campaign = strict_json((out / "campaign-claim.json").read_text())
            campaign["prepared_manifest_sha256"] = sha
            self.rewrite_fake_json(out / "campaign-claim.json", campaign)
            ledger = root / "_runs/substrate_attempts" / plan["raw"]["id"]
            (ledger / "campaign.json").write_text(
                json.dumps(campaign, indent=2, sort_keys=True) + "\n"
            )
            self.reseal_fake(out, record)
            with self.assertRaisesRegex(
                ValueError, "preparation/qualification reference"
            ):
                module.verify_capture(out)

    def test_v2_start_cannot_authorize_this_campaign(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            plan = load_plan()
            prepared_dir = root / "prepared"
            prepared_dir.mkdir()
            write_new(prepared_dir / "manifest.json", {})
            (prepared_dir / "frozen-protocol.json").write_bytes(
                module.DEFAULT_PLAN.read_bytes()
            )
            write_new(prepared_dir / "capture-plan.json", plan["raw"])
            prepared = {
                "capture_plan_sha256": module.digest(
                    prepared_dir / "capture-plan.json"
                ),
                "scope": "shared_campaign_preparation",
                "head": "h",
                "readiness": "AWAITING_EXACT_HEAD_REVIEWS_AND_BOUND_DELEGATION",
                "protocol_sha256": module.digest(module.DEFAULT_PLAN),
                "anchor_sha256": plan["raw"]["anchor_sha256"],
                "max_attempts": 20,
                "physics_steps_max": 120000,
                "planned_arms": module.arms(plan),
            }
            review = {
                "head": "h",
                "science": {
                    "verdict": "APPROVED",
                    "reviewer": "fake-science",
                    "evidence": "fixture",
                },
                "execution": {
                    "verdict": "APPROVED",
                    "reviewer": "fake-execution",
                    "evidence": "fixture",
                },
            }
            authorization = {
                "action": "START_FORMAL_CAPTURE",
                "head": "h",
                "protocol_sha256": prepared["protocol_sha256"],
                "prepared_manifest_sha256": module.digest(
                    prepared_dir / "manifest.json"
                ),
                "max_attempts": 20,
                "authorized_by": "user",
                "user_instruction": "FAKE FIXTURE ONLY",
                "task_id": "aligned-flat-capture-v2",
            }
            write_new(root / "review.json", review)
            write_new(root / "authorization.json", authorization)
            stack.enter_context(
                mock.patch.object(module, "current_head", return_value="h")
            )
            stack.enter_context(
                mock.patch.object(module, "verify_bundle", return_value=prepared)
            )
            stack.enter_context(mock.patch.object(module, "_identity"))
            with self.assertRaisesRegex(ValueError, "never v2 START"):
                module.validate_start_files(
                    prepared_dir,
                    root / "review.json",
                    root / "authorization.json",
                    module.DEFAULT_PLAN,
                )

    def test_missing_qualification_prevents_preparation(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "never_created"
            with (
                mock.patch.object(module, "current_head", return_value="h"),
                mock.patch.object(
                    module,
                    "validate_qualification",
                    side_effect=ValueError("qualification required"),
                ),
                mock.patch.object(
                    module,
                    "experiment_lock",
                    side_effect=lambda: experiment_lock(
                        Path(temp) / "prepare_fixture.lock"
                    ),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "qualification"):
                    module.prepare(output, qualification_path="missing")
            self.assertFalse(output.exists())


class ConditionEvidenceTests(unittest.TestCase):
    def setUp(self):
        guard = zero_step_guard()
        guard.__enter__()
        self.addCleanup(guard.__exit__, None, None, None)
        self.plan = load_plan()

    def delay_rows(self, name="observation_delay"):
        plan = copy.deepcopy(self.plan)
        plan["task"] = replace(plan["task"], horizon_ticks=40, measurement_start_tick=0)
        config = plan["controllers"]["mjpc"]
        base_rows = []
        run_aligned_episode(
            fixtures.FakePlant(),
            ClockController(plan["task"]),
            plan["task"],
            config["information"],
            config["timing"],
            base_rows.append,
            lambda: None,
        )
        info, timing = condition_specs(name, config["information"], config["timing"])
        rows = []
        run_aligned_episode(
            fixtures.FakePlant(),
            ClockController(plan["task"], timing.decimation),
            plan["task"],
            info,
            timing,
            rows.append,
            lambda: None,
            condition=BoundedCondition(name),
        )
        return rows, base_rows, plan

    def test_hashes_independently_match_old_measurement_and_native_current_time(self):
        rows, baseline, plan = self.delay_rows()
        actual = verify_condition(
            rows, baseline, "observation_delay", "mjpc", plan, "baseline-sha"
        )
        self.assertTrue(actual["effective_complete_horizon"])
        self.assertEqual(actual["exposure_status"], "EXPOSED_COMPLETE")
        self.assertNotEqual(
            rows[20]["condition_observation"]["source_payload_sha256"],
            rows[20]["condition_observation"]["controller_payload_sha256"],
        )
        self.assertEqual(rows[20]["condition_observation"]["source_tick"], 10)

    def test_measurement_and_retimed_hash_corruption_each_rejected(self):
        for key in ("source_payload_sha256", "controller_payload_sha256"):
            with self.subTest(key=key):
                rows, baseline, plan = self.delay_rows()
                rows[20]["condition_observation"][key] = "0" * 64
                with self.assertRaisesRegex(ValueError, "hash"):
                    verify_condition(
                        rows,
                        baseline,
                        "observation_delay",
                        "mjpc",
                        plan,
                        "baseline-sha",
                    )

    def test_wrong_source_tick_rejected_even_with_valid_timestamps(self):
        rows, baseline, plan = self.delay_rows()
        rows[20]["condition_observation"]["source_tick"] = 20
        with self.assertRaisesRegex(ValueError, "source"):
            verify_condition(
                rows, baseline, "observation_delay", "mjpc", plan, "baseline-sha"
            )

    def test_actual_decision_and_command_sampling_verified(self):
        rows, baseline, plan = self.delay_rows("decision_period")
        actual = verify_condition(
            rows, baseline, "decision_period", "mjpc", plan, "baseline-sha"
        )
        self.assertTrue(actual["effective_complete_horizon"])
        rows[10]["controller_diagnostics"]["controller"]["last_step"]["replanned"] = (
            True
        )
        with self.assertRaisesRegex(ValueError, "cadence"):
            verify_condition(
                rows, baseline, "decision_period", "mjpc", plan, "baseline-sha"
            )

    def test_native_command_shape_and_nonfinite_values_rejected(self):
        for key in ("sampled_command", "requested_command"):
            for value in ([], [0], [0, 0, 0, 0], [float("nan"), 0, 0]):
                with self.subTest(key=key, value=value):
                    rows, baseline, plan = self.delay_rows()
                    rows[20]["controller_diagnostics"]["controller"]["last_step"][
                        key
                    ] = value
                    with self.assertRaisesRegex(ValueError, "command"):
                        verify_condition(
                            rows,
                            baseline,
                            "observation_delay",
                            "mjpc",
                            plan,
                            "baseline-sha",
                        )

    def test_pre_exposure_prefix_mismatch_is_not_a_challenge_pass(self):
        rows, baseline, plan = self.delay_rows()
        rows[0]["action"]["ctrl"][0] = 0.1
        with self.assertRaisesRegex(ValueError, "pre-exposure prefix"):
            verify_condition(
                rows, baseline, "observation_delay", "mjpc", plan, "baseline-sha"
            )

    def physical_clock_fixture(self, name, fail_tick=3000, horizon=6000):
        plan = copy.deepcopy(self.plan)
        plan["task"] = replace(
            plan["task"],
            horizon_ticks=horizon,
            measurement_start_tick=min(1000, horizon),
        )
        root = Path(__file__).resolve().parents[2]
        plant = MujocoPlant(root / plan["scenario"].scene)
        original_snapshot = plant.snapshot

        def snapshot(tick):
            row = original_snapshot(tick)
            if tick == fail_tick:
                row["warning_count"] = 1
            return row

        plant.snapshot = snapshot

        def synthetic_clock(ctrl):
            # Deliberately no mj_step/mj_step1/mj_step2 or numerical dynamics.
            plant.steps += 1
            plant.data.time = plant.steps * 0.002

        plant.step = synthetic_clock
        config = plan["controllers"]["mjpc"]
        info, timing = condition_specs(name, config["information"], config["timing"])
        rows = []
        outcome = run_aligned_episode(
            plant,
            ClockController(plan["task"]),
            plan["task"],
            info,
            timing,
            rows.append,
            lambda: None,
            condition=BoundedCondition(name),
        )
        baseline = copy.deepcopy(rows)
        return plant, rows, baseline, plan, outcome

    def test_onset_safety_runs_before_friction_or_force_setting(self):
        for name in ("sliding_friction", "lateral_force"):
            with self.subTest(name=name):
                plant, rows, baseline, plan, outcome = self.physical_clock_fixture(name)
                self.assertEqual(outcome["terminal_reason"], "physics_warning")
                self.assertNotIn("condition", rows[3000])
                actual = verify_condition(
                    rows, baseline, name, "mjpc", plan, "baseline-sha"
                )
                self.assertEqual(actual["exposure_status"], "PRE_EXPOSURE_STOP")
                self.assertFalse(actual["actual_exposure_observed"])
                self.assertFalse(actual["effective_complete_horizon"])
                np.testing.assert_array_equal(
                    plant.model.geom_friction[list(plant.feet), 0], [0.8] * 4
                )
                self.assertFalse(np.any(plant.data.xfrc_applied))

    def test_unexposed_complete_horizon_is_explicit_not_robustness_pass(self):
        _, rows, baseline, plan, outcome = self.physical_clock_fixture(
            "sliding_friction", fail_tick=-1, horizon=32
        )
        self.assertEqual(outcome["terminal_reason"], "horizon")
        actual = verify_condition(
            rows, baseline, "sliding_friction", "mjpc", plan, "baseline-sha"
        )
        self.assertEqual(actual["exposure_status"], "NOT_EXPOSED_HORIZON")
        self.assertFalse(actual["effective_complete_horizon"])
