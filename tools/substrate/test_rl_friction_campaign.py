"""Real independent entry with FakePlant only; no policy/native/physics startup."""

import copy
from contextlib import ExitStack, contextmanager
from dataclasses import replace
import fcntl
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from . import rl_friction_campaign as runtime
from . import rl_friction_reference as spec
from . import qualify_rl_friction as qualifier
from . import shared_campaign as engine
from . import test_shared_campaign as sharedtests
from . import test_aligned_episode as fixtures
from . import test_campaign_stop as stops
from .aligned_episode import run_aligned_episode
from .guards import zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    write_new,
    verify_manifest,
)
from .qualification import fingerprint, REQUIRED_CHECKS


class IndependentEntryTests(unittest.TestCase):
    @contextmanager
    def fixture(
        self,
        *,
        reason=None,
        performance=False,
        exposed=True,
        boot_failure=False,
        preflight_failure=False,
    ):
        plan = copy.deepcopy(spec.load_plan())
        plan["task"] = replace(
            plan["task"],
            horizon_ticks=32,
            measurement_start_tick=1,
            zero_command_ticks=0,
            ramp_ticks=1,
        )
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            stack.enter_context(zero_step_guard())
            root = Path(temp)
            lockpath = root / "fixture.lock"
            out = root / plan["frozen"]["output_root"] / "run_fake"
            pdir, qdir = root / "prepared", root / "qualification"
            with EvidenceRun(qdir) as qrun:
                qrun.result.update(
                    status="ENGINEERING_ADMITTED",
                    qualification={"head": "h"},
                    qualification_fingerprint="FAKE QUALIFICATION FIXTURE ONLY",
                )
            qref = {
                "path": str(qdir),
                "manifest_sha256": digest(qdir / "manifest.json"),
                "producer_head": "h",
                "fingerprint": "FAKE QUALIFICATION FIXTURE ONLY",
            }
            config = plan["controllers"]["rl"]
            baseline = []
            run_aligned_episode(
                stops.FaultPlant(None, 1),
                fixtures.FakeController(),
                plan["task"],
                config["information"],
                config["timing"],
                baseline.append,
                lambda: None,
            )
            raw = "".join(json.dumps(row) + "\n" for row in baseline)
            with EvidenceRun(pdir) as prun:
                for name in ("rl_baseline_1", "rl_baseline_2"):
                    (prun.path / (name + ".jsonl")).write_text(raw)
                own = {
                    "eligible": True,
                    "reason": "repeatable_own_baseline",
                    "baseline_statuses": ["PASS", "PASS"],
                    "baselines": [
                        {
                            "id": name,
                            "raw_sha256": digest(prun.path / (name + ".jsonl")),
                            "classification": "PASS",
                        }
                        for name in ("rl_baseline_1", "rl_baseline_2")
                    ],
                    "repeat_comparison": {
                        "maximum_absolute_state_control_difference": 0.0,
                        "repeatable": True,
                    },
                }
                reference = {
                    "capture": "FAKE SEALED RL REFERENCE FIXTURE ONLY",
                    "capture_head": "h",
                    "eligibility": {"rl": own},
                    "old_NOT_RUN_count": 17,
                }
                (prun.path / "frozen-protocol.json").write_bytes(
                    spec.DEFAULT_PROTOCOL.read_bytes()
                )
                write_new(prun.path / "capture-plan.json", plan["frozen"])
                write_new(prun.path / "sealed-reference.json", reference)
                prun.result.update(
                    status="ENGINEERING_ADMITTED",
                    head="h",
                    scope="independent_rl_friction_preparation",
                    readiness="AWAITING_EXACT_HEAD_REVIEWS_AND_BOUND_DELEGATION",
                    qualification=qref,
                    protocol_sha256=spec.PROTOCOL_SHA256,
                    capture_plan_sha256=digest(prun.path / "capture-plan.json"),
                    max_attempts=2,
                    physics_steps_max=12000,
                    planned_arms=spec.arms(plan),
                    sealed_reference=reference,
                    rl_checkpoint_sha256="FAKE CHECKPOINT FIXTURE ONLY",
                )
            prepared = verify_manifest(pdir)
            review = {
                "head": "h",
                **{
                    role: {
                        "verdict": "APPROVED",
                        "reviewer": "TEST ONLY " + role,
                        "evidence": "SYNTHETIC REVIEW FIXTURE; no real START approval",
                    }
                    for role in ("science", "execution")
                },
            }
            auth = {
                "action": "START_FORMAL_CAPTURE",
                "head": "h",
                "task_id": plan["frozen"]["id"],
                "protocol_sha256": prepared["protocol_sha256"],
                "prepared_manifest_sha256": digest(pdir / "manifest.json"),
                "max_attempts": 2,
                "physics_steps_max": 12000,
                "authorized_by": "user",
                "user_instruction": "SYNTHETIC AUTH FIXTURE; no real capture authorized",
            }
            review_path, auth_path = root / "review.json", root / "authorization.json"
            write_new(review_path, review)
            write_new(auth_path, auth)
            active, plants, requested = {}, [], []
            original = engine._execute_arm

            def assert_lock():
                with lockpath.open("a") as competitor:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(competitor.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            def preflight(lock, head, *args):
                assert_lock()
                self.assertTrue(
                    (root / plan["frozen"]["ledger_root"] / "campaign.json").exists()
                )
                self.assertEqual(plants, [])
                if preflight_failure:
                    raise RuntimeError("fake preflight failure")
                pref = root / "preflight"
                with EvidenceRun(pref) as run:
                    write_new(
                        run.path / "report.json",
                        {
                            "pass": True,
                            "git": {"head": "h"},
                            "experiment_id": plan["frozen"]["id"],
                        },
                    )
                    run.result.update(status="ENGINEERING_ADMITTED", head="h")
                return {
                    "path": str(pref),
                    "manifest_sha256": digest(pref / "manifest.json"),
                }

            def execute(item, *args):
                active["id"] = item["id"]
                requested.append(item["id"])
                if boot_failure:
                    raise RuntimeError("fake execution boot failure")
                return original(item, *args)

            def plant_factory(*args):
                assert_lock()
                p = stops.FaultPlant(reason if not plants else None, 1)
                snapshot = p.snapshot

                def altered(tick):
                    row = snapshot(tick)
                    if performance and active["id"] == "rl_friction_1" and tick:
                        row["qvel"][0] = 0.5
                    return row

                p.snapshot = altered
                plants.append(p)
                return p

            def controller(name, *args):
                self.assertEqual(name, "rl")
                return fixtures.FakeController(), lambda: None

            patches = {
                "ROOT": root,
                "experiment_lock": lambda: experiment_lock(lockpath),
                "references": mock.Mock(return_value=reference),
                "_identity": mock.Mock(),
                "_fresh_preflight": mock.Mock(side_effect=preflight),
            }
            for name, value in patches.items():
                stack.enter_context(mock.patch.object(runtime, name, value))
            stack.enter_context(mock.patch.object(spec, "load_plan", return_value=plan))
            for name, value in {
                "ROOT": root,
                "current_head": mock.Mock(return_value="h"),
                "MujocoPlant": mock.Mock(side_effect=plant_factory),
                "validate_canonical_model": mock.Mock(),
                "_make_controller": mock.Mock(side_effect=controller),
                "_execute_arm": mock.Mock(side_effect=execute),
                "BoundedCondition": sharedtests.FixtureCondition,
                "verify_condition": mock.Mock(
                    return_value={
                        "effective_complete_horizon": exposed,
                        "exposure_status": "FAKE CONDITION FIXTURE ONLY",
                    }
                ),
                "wall_deadline": mock.MagicMock(),
                "NativeMJPCController": mock.Mock(
                    side_effect=AssertionError("no native startup")
                ),
            }.items():
                stack.enter_context(mock.patch.object(engine, name, value))
            setup = stack.enter_context(
                mock.patch.object(engine.base, "_setup_runtime")
            )
            yield (
                root,
                out,
                pdir,
                plan,
                review_path,
                auth_path,
                requested,
                plants,
                setup,
            )

    def launch(self, f):
        return runtime.capture(f[2], f[4], f[5], f[1])

    def verify(self, f):
        return runtime.verify_capture(f[1])

    def test_real_entry_two_RL_arms_claims_pairing_and_one_setup(self):
        with self.fixture() as f:
            result = self.launch(f)
            self.assertEqual(result["status"], "CAPTURE_COMPLETE")
            self.assertEqual(result["scientific_attempts"], 2)
            self.assertEqual(f[6], ["rl_friction_1", "rl_friction_2"])
            self.assertEqual(len(f[7]), 2)
            f[8].assert_called_once()
            self.assertEqual(self.verify(f)["scientific_attempts_checked"], 2)
            ledger = f[0] / f[3]["frozen"]["ledger_root"]
            self.assertEqual(
                strict_json((ledger / "campaign.json").read_text())[
                    "physics_steps_max"
                ],
                12000,
            )
            for j in (1, 2):
                self.assertEqual(
                    strict_json((ledger / f"rl_friction_{j}.json").read_text())[
                        "reference_baseline"
                    ],
                    f"rl_baseline_{j}",
                )

    def test_six_safety_failures_stop_new_campaign(self):
        for reason in (
            "nonfinite",
            "orientation",
            "physics_warning",
            "nonfoot_contact",
            "posture",
            "lateral",
        ):
            with self.subTest(reason=reason), self.fixture(reason=reason) as f:
                self.assertEqual(self.launch(f)["status"], "SAFETY_STOP")
                self.assertEqual(f[6], ["rl_friction_1"])
                self.assertEqual(self.verify(f)["capture_status"], "SAFETY_STOP")

    def test_performance_failure_retained_and_second_repeat_runs(self):
        with self.fixture(performance=True) as f:
            self.launch(f)
            a = verify_manifest(f[1])["attempts"]
            self.assertEqual([i["status"] for i in a], ["PERFORMANCE_FAIL", "PASS"])
            self.assertEqual(self.verify(f)["capture_status"], "CAPTURE_COMPLETE")

    def test_unexposed_horizon_stops_without_second_repeat(self):
        with self.fixture(exposed=False) as f:
            self.assertEqual(self.launch(f)["status"], "EXPOSURE_EVIDENCE_STOP")
            self.assertEqual(f[6], ["rl_friction_1"])
            self.verify(f)

    def test_boot_failure_stops_and_verifies_zero_claims(self):
        with self.fixture(boot_failure=True) as f:
            self.assertEqual(self.launch(f)["status"], "EXECUTION_EVIDENCE_STOP")
            self.assertEqual(self.verify(f)["scientific_attempts_checked"], 0)

    def test_preflight_failure_reserves_no_retry_with_zero_arms(self):
        with self.fixture(preflight_failure=True) as f:
            self.assertEqual(self.launch(f)["status"], "EXECUTION_EVIDENCE_STOP")
            self.assertEqual(f[6], [])
            self.assertEqual(self.verify(f)["scientific_attempts_checked"], 0)
            with self.assertRaisesRegex(ValueError, "no retry"):
                self.launch(f)

    def test_old_or_wrong_budget_START_creates_no_ledger_or_plant(self):
        for key, value in (
            ("task_id", "shared-baseline-probes-v1"),
            ("physics_steps_max", 12001),
            ("max_attempts", 3),
            ("head", "old"),
        ):
            with self.subTest(key=key), self.fixture() as f:
                a = strict_json(f[5].read_text())
                a[key] = value
                f[5].write_text(json.dumps(a))
                with self.assertRaises(ValueError):
                    self.launch(f)
                self.assertFalse((f[0] / f[3]["frozen"]["ledger_root"]).exists())
                self.assertEqual(f[7], [])

    def test_existing_campaign_never_consumes_third_arm_or_new_output(self):
        with self.fixture() as f:
            self.launch(f)
            with self.assertRaisesRegex(ValueError, "no retry"):
                runtime.capture(f[2], f[4], f[5], f[1].parent / "run_replacement")
            self.assertEqual(f[6], ["rl_friction_1", "rl_friction_2"])

    def test_real_external_ledger_tamper_rejected(self):
        with self.fixture() as f:
            self.launch(f)
            path = f[0] / f[3]["frozen"]["ledger_root"] / "rl_friction_1.json"
            a = strict_json(path.read_text())
            a["reference_baseline_sha256"] = "forged"
            path.write_text(json.dumps(a))
            with self.assertRaisesRegex(ValueError, "external claim"):
                self.verify(f)


class IndependentFreshPreflightTests(sharedtests.FreshPreflightTests):
    """The actual new preflight entry calls the actual child with held lock."""

    def setUp(self):
        super().setUp()
        self.runner = self.root / "tools/substrate/rl_friction_campaign.py"
        self.runner.write_text(
            'raise AssertionError("runner must never be executed by preflight")\n'
            + Path(runtime.__file__).read_text()
        )
        self.commit()

    def call(self, *, review_head=None):
        review = {
            "head": review_head or self.head,
            **{
                role: {
                    "verdict": "APPROVED",
                    "reviewer": "TEST ONLY " + role,
                    "evidence": "SYNTHETIC FIXTURE ONLY; no real review approval",
                }
                for role in ("science", "execution")
            },
        }
        plan = {
            "raw": {"expected_branch": "fixture", "accepted_parent_head": self.base},
            "frozen": {"id": "rl-sliding-friction-reference-v1"},
        }
        with (
            experiment_lock(self.lock_path) as lock,
            mock.patch.object(runtime, "ROOT", self.root),
            mock.patch.object(runtime, "__file__", str(self.runner)),
            mock.patch.object(self.launch, "ROOT", self.root),
        ):
            try:
                return runtime._fresh_preflight(
                    lock,
                    self.head,
                    review,
                    plan,
                    {"qualification": self.reference},
                    self.output,
                )
            finally:
                with self.lock_path.open("a") as competitor:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(competitor.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertFalse(self.output.exists())
                self.assertFalse((self.root / "_runs/substrate_attempts").exists())

    def report(self):
        paths = list((self.root / "_runs/rl_friction_preflight").glob("*/report.json"))
        self.assertEqual(len(paths), 1)
        return strict_json(paths[0].read_text())


class NativeBasisTests(unittest.TestCase):
    def data(self):
        source_inputs = {
            "tracked_files": {
                "native.cc": "pinned",
                "tools/substrate/shared_campaign.py": "before",
            },
            "native_build": {"binary": "same"},
            "runtime": "same",
        }
        source = {
            "qualification": {
                "clean_head": True,
                "development": False,
                "head": "FIXTURE ONLY",
            },
            "qualification_inputs": source_inputs,
            "qualification_fingerprint": fingerprint(source_inputs),
            "qualification_checks": {
                name: {"returncode": 0} for name in REQUIRED_CHECKS
            },
        }
        actual = copy.deepcopy(source_inputs)
        actual["tracked_files"].update(
            {name: "reviewed increment" for name in qualifier.OVERLAY_FILES}
        )
        return source, actual

    def test_only_explicit_increment_may_differ(self):
        source, actual = self.data()
        self.assertTrue(
            qualifier.cached_basis(source, actual)[
                "native_build_binary_link_compiler_model_environment_unchanged"
            ]
        )
        actual["tracked_files"]["unexpected_runtime.py"] = "new"
        with self.assertRaisesRegex(ValueError, "inputs differ"):
            qualifier.cached_basis(source, actual)

    def test_native_or_environment_drift_cannot_reuse_checks(self):
        for key in ("native_build", "runtime"):
            with self.subTest(key=key):
                source, actual = self.data()
                actual[key] = "changed"
                with self.assertRaisesRegex(ValueError, "inputs differ"):
                    qualifier.cached_basis(source, actual)

    def test_missing_increment_or_failed_source_checks_rejected(self):
        source, actual = self.data()
        actual["tracked_files"].pop("tools/substrate/rl_friction_campaign.py")
        with self.assertRaisesRegex(ValueError, "files are missing"):
            qualifier.cached_basis(source, actual)
        source, actual = self.data()
        source["qualification_checks"]["controller_tests"]["returncode"] = 1
        with self.assertRaisesRegex(ValueError, "not passing"):
            qualifier.cached_basis(source, actual)


if __name__ == "__main__":
    unittest.main()
