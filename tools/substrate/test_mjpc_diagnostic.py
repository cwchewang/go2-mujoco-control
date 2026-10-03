import contextlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .mjpc_diagnostic import optimization_model
from .mjpc_diagnostic_capture import (
    check_original_identity,
    validate_capture_metadata,
    validate_prediction,
)
from .integrity import LOCK_PATH, digest, experiment_lock, verify_bundle

import copy
import unittest
from .mjpc_diagnostic import ROOT, load_plan, model_audit, validate_budget_record


class DiagnosticTests(unittest.TestCase):
    def value(self, calls=1):
        return dict(
            policy_id=calls,
            private_step_upper_bound_reserved=calls * 4096,
            private_step_limit=614400,
            rollout_mj_step_count=700 * calls,
            fd_step_upper_bound_count=1801 * calls,
            fd_call_count=37 * calls,
        )

    def test_budget_covers_fd_and_rollouts(self):
        validate_budget_record(self.value(), 0)
        v = self.value(150)
        validate_budget_record(v, 1499)
        v["fd_step_upper_bound_count"] = 614401
        with self.assertRaises(ValueError):
            validate_budget_record(v, 1499)

    def test_feedback_cannot_integrate_or_change_policy(self):
        previous = self.value()
        validate_budget_record(previous, 1, previous)
        for key in (
            "rollout_mj_step_count",
            "fd_step_upper_bound_count",
            "fd_call_count",
        ):
            v = copy.deepcopy(previous)
            v[key] += 1
            with self.assertRaises(ValueError):
                validate_budget_record(v, 1, previous)

    def test_missing_bool_regressed_accounting_rejected(self):
        for key in self.value():
            v = self.value()
            v[key] = True
            with self.assertRaises(ValueError):
                validate_budget_record(v, 0)
        v = self.value()
        v.pop("fd_call_count")
        with self.assertRaises(ValueError):
            validate_budget_record(v, 0)

    def test_two_protocols_have_separate_single_attempt_ownership(self):
        values = [
            load_plan(
                ROOT
                / "tools/substrate/protocols"
                / ("mjpc-adaptation-" + m + "-3s-v1.json")
            )
            for m in ("original", "corrected")
        ]
        self.assertNotEqual(values[0]["raw"]["id"], values[1]["raw"]["id"])
        for p in values:
            self.assertEqual(p["task"].horizon_ticks, 1500)
            self.assertEqual(p["raw"]["scientific_attempts_max"], 1)

    def test_original_corrected_head_and_qualification_identity(self):
        head = "a" * 40
        fingerprint = "b" * 64
        record = {"head": head}
        binding = {"head": head, "qualification": {"fingerprint": fingerprint}}
        check_original_identity(record, binding, head, fingerprint)
        # Identical runtime fingerprint never permits another source HEAD.
        with self.assertRaisesRegex(ValueError, "HEAD mismatch"):
            check_original_identity(record, binding, "c" * 40, fingerprint)
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            check_original_identity(record, binding, head, "d" * 64)
        altered = copy.deepcopy(binding)
        altered["head"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "HEAD mismatch"):
            check_original_identity(record, altered, head, fingerprint)

    def test_named_joint_and_unnamed_collision_mapping(self):
        v = model_audit()
        self.assertEqual(len(v["joint_map"]), 12)
        self.assertEqual(len(v["collision_map"]), 23)
        self.assertEqual(len({r["canonical_geom"] for r in v["collision_map"]}), 23)
        self.assertNotEqual(*v["optimization_models"].values())
        self.assertEqual(v["canonical_integration_steps"], 0)


SMOKE = (
    ROOT
    / "_runs/mjpc_adaptation_diagnostic_prep_20261002/qualification_20261002T145537Z"
)


class ProductionEvidenceRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        verify_bundle(SMOKE)
        cls.prediction = json.loads(
            (SMOKE / "native-smoke-predictions.jsonl").read_text()
        )
        cls.responses = [
            json.loads(s)
            for s in (SMOKE / "native-smoke.stdout").read_text().splitlines()
        ]
        old = (
            ROOT
            / "example/cpp/experiments/_runs/shared_baseline_probes_v1/run_20261002T085338452324Z/mjpc_baseline_1.jsonl"
        )
        if (
            digest(old)
            != "e5f760c54a57d12e8da6150972cb084414c3f9d84f1827ac9582b292532a3841"
        ):
            raise ValueError("sealed raw regression reference drift")
        with old.open() as f:
            cls.row = json.loads(f.readline())
        cls.row["controller_diagnostics"]["controller"]["last_step"]["diagnostic"] = (
            cls.responses[-1]["diagnostic"]
        )
        cls.model = optimization_model("original")

    def test_real_native_response_types_and_position_pd_boundary(self):
        import numpy as np
        from .native_mjpc import validate_ready, parse_step_response

        names, actuator = validate_ready(self.responses[0])
        value, metadata = parse_step_response(self.responses[-1], 0.0, True)
        command, adapter = actuator.command(value)
        self.assertIsInstance(value, np.ndarray)
        self.assertEqual(value.shape, (12,))
        self.assertEqual(tuple(command.joint_names), names)
        self.assertEqual(metadata["replanned"], True)
        np.testing.assert_array_equal(
            adapter["position_target"], self.row["target"]["position_target"]
        )
        np.testing.assert_array_equal(command.kp, np.full(12, 60.0))
        np.testing.assert_array_equal(command.kd, np.full(12, 5.0))

    def test_real_selected_prediction_reconstructs_contacts_zero_step(self):
        validate_prediction(self.prediction, self.row, "original", self.model)

    def test_selected_prediction_mapping_and_count_negatives(self):
        mutations = (
            lambda x: x.update(candidate_id=10),
            lambda x: x.update(candidate_id=True),
            lambda x: x.update(policy_id=True),
            lambda x: x["private_accounting"].update(fd_call_count=38),
            lambda x: x["private_accounting"].update(rollout_mj_step_count=True),
            lambda x: x["states"][0].update(active_contacts=[]),
            lambda x: x["states"][0]["active_contacts"][0].update(geom_ids=[True, 0]),
            lambda x: x["states"][0]["active_contacts"][0].update(
                geom_names=["floor", "WRONG"]
            ),
            lambda x: x["states"][0]["active_contacts"][0].update(distance_m=0.123),
            lambda x: x["states"][0]["qpos"].__setitem__(10, 0.123),
        )
        for mutate in mutations:
            value = copy.deepcopy(self.prediction)
            mutate(value)
            with self.subTest(mutation=str(mutate)), self.assertRaises(ValueError):
                validate_prediction(value, self.row, "original", self.model)

    def test_real_truncated_prefix_is_not_a_safety_stop(self):
        from .evaluator import CanonicalEvaluator
        from .mjpc_diagnostic_capture import classify_terminal

        old = (
            ROOT
            / "example/cpp/experiments/_runs/shared_baseline_probes_v1/run_20261002T085338452324Z/mjpc_baseline_1.jsonl"
        )
        with old.open() as stream:
            rows = [json.loads(next(stream)) for _ in range(101)]
        plan = load_plan(
            ROOT / "tools/substrate/protocols/mjpc-adaptation-original-3s-v1.json"
        )
        oracle = CanonicalEvaluator(plan["task"], 0.002).evaluate(rows).as_dict()
        self.assertEqual(oracle["terminal_reason"], "incomplete_evidence")
        self.assertIsNone(oracle["first_failure"])
        with self.assertRaisesRegex(ValueError, "incomplete evidence"):
            classify_terminal(
                oracle, {"terminal_reason": "incomplete_evidence", "steps": 100}
            )
        with old.open() as stream:
            complete = [json.loads(line) for line in stream]
        safety = CanonicalEvaluator(plan["task"], 0.002).evaluate(complete).as_dict()
        self.assertEqual(
            classify_terminal(
                safety, {"terminal_reason": "nonfoot_contact", "steps": 1287}
            ),
            "SAFETY_STOP",
        )

    def test_prepared_review_start_binding_negatives(self):
        # Explicit unit fixture only; never passed to capture/preflight.
        p = dict(
            head="a" * 40,
            task_id="mjpc-adaptation-original-3s-v1",
            protocol_sha256="b" * 64,
            max_attempts=1,
            canonical_steps_max=1500,
            private_step_upper_bound_max=614400,
        )
        binding = dict(p, prepared_manifest_sha256="c" * 64)
        plan = dict(raw={"id": p["task_id"]}, protocol_sha256=p["protocol_sha256"])
        record = dict(head=p["head"], task_id=p["task_id"])
        review = dict(
            head=p["head"],
            **{
                role: dict(
                    verdict="APPROVED",
                    reviewer="UNIT_FIXTURE_ONLY_" + role,
                    evidence="UNIT_FIXTURE_NOT_ACTUAL_REVIEW",
                )
                for role in ("science", "execution")
            },
        )
        auth = dict(
            action="START_FORMAL_CAPTURE",
            head=p["head"],
            protocol_sha256=p["protocol_sha256"],
            prepared_manifest_sha256=binding["prepared_manifest_sha256"],
            max_attempts=1,
            authorized_by="user",
            user_instruction="UNIT_FIXTURE_NOT_ACTUAL_AUTHORIZATION",
            task_id=p["task_id"],
            canonical_steps_max=1500,
            private_step_upper_bound_max=614400,
        )
        values = [record, p, plan, binding, review, auth]
        validate_capture_metadata(*values)
        for index, key, bad in (
            (0, "head", "d" * 40),
            (1, "task_id", "other"),
            (2, "protocol_sha256", "e" * 64),
            (4, "head", "d" * 40),
            (5, "prepared_manifest_sha256", "f" * 64),
            (5, "canonical_steps_max", True),
            (5, "private_step_upper_bound_max", 1),
            (5, "task_id", "other"),
        ):
            changed = copy.deepcopy(values)
            changed[index][key] = bad
            with self.subTest(index=index, field=key), self.assertRaises(ValueError):
                validate_capture_metadata(*changed)


@contextlib.contextmanager
def regression_lock():
    # Qualification passes its actual descriptor; the production child checks its inode.
    target = LOCK_PATH.stat() if LOCK_PATH.exists() else None
    for path in Path("/proc/self/fd").iterdir():
        try:
            stat = path.stat()
            if target and (stat.st_dev, stat.st_ino) == (target.st_dev, target.st_ino):
                yield int(path.name)
                return
        except OSError:
            pass
    with experiment_lock() as lock:
        yield lock.fileno()


class RealPreflightSubprocessRegression(unittest.TestCase):
    def test_all_formal_runners_declaration_and_experiment_sentinel(self):
        # Fixed roster: dropping a declaration must not silently drop its regression.
        runners = (
            "launch",
            "baseline",
            "aligned_capture",
            "shared_campaign",
            "rl_friction_campaign",
            "mjpc_diagnostic_capture",
        )
        for name in runners:
            runner_source = (ROOT / ("tools/substrate/" + name + ".py")).read_text()
            for declared in (True, False):
                with (
                    self.subTest(runner=name, declared=declared),
                    tempfile.TemporaryDirectory() as temp,
                ):
                    root = Path(temp)
                    runner = root / "runner.py"
                    sentinel = root / "EXPERIMENT_STARTED"
                    source = (
                        runner_source
                        if declared
                        else runner_source.replace(
                            'TRANSPORT = "inprocess"', "# omitted transport declaration"
                        )
                    )
                    # Real preflight syntax-checks but must never execute this runner.
                    import ast

                    tree = ast.parse(source)
                    future_end = max(
                        (
                            node.end_lineno
                            for node in tree.body
                            if isinstance(node, ast.ImportFrom)
                            and node.module == "__future__"
                        ),
                        default=0,
                    )
                    lines = source.splitlines(keepends=True)
                    lines.insert(
                        future_end,
                        '__import__("pathlib").Path('
                        + repr(str(sentinel))
                        + ').write_text("EXPERIMENT STARTED")\n',
                    )
                    runner.write_text("".join(lines))

                    def git(*args):
                        return subprocess.check_output(
                            ["git", *args],
                            cwd=root,
                            stderr=subprocess.DEVNULL,
                            text=True,
                        ).strip()

                    git("init", "-b", "entry-regression")
                    git("add", "runner.py")
                    git(
                        "-c",
                        "user.name=Regression",
                        "-c",
                        "user.email=regression@example.invalid",
                        "commit",
                        "-m",
                        "production runner declaration regression",
                    )
                    head = git("rev-parse", "HEAD")
                    argv = [
                        sys.executable,
                        str(ROOT / "tools/research/preflight.py"),
                        "--repo-root",
                        str(root),
                        "--experiment-id",
                        "UNIT_PREFLIGHT_ONLY",
                        "--expected-branch",
                        "entry-regression",
                        "--expected-head",
                        head,
                        "--runner",
                        str(runner),
                        "--run-dir",
                        str(root / "NEVER_CREATED"),
                        "--transport",
                        "inprocess",
                    ]
                    with regression_lock() as fd:
                        result = subprocess.run(
                            argv + ["--held-lock-fd", str(fd)],
                            text=True,
                            capture_output=True,
                            timeout=30,
                            pass_fds=(fd,),
                        )
                    report = json.loads(result.stdout)
                    self.assertEqual(
                        result.returncode, 0 if declared else 2, result.stderr
                    )
                    self.assertEqual(report["pass"], declared, report)
                    checks = {c["name"]: c["status"] for c in report["checks"]}
                    self.assertEqual(
                        checks["reviewed_inprocess_runner"],
                        "PASS" if declared else "FAIL",
                    )
                    self.assertFalse((root / "NEVER_CREATED").exists())
                    self.assertFalse(sentinel.exists())

    def test_real_preflight_failure_seals_zero_attempt_and_original_rc(self):
        from .integrity import verify_manifest, write_new
        from .mjpc_diagnostic_capture import seal_preflight_failure

        with tempfile.TemporaryDirectory() as temp:
            top = Path(temp)
            root = top / "repo"
            root.mkdir()
            sentinel = top / "EXPERIMENT_STARTED"
            runner = root / "runner.py"
            runner.write_text(
                'TRANSPORT = "inprocess"\n__import__("pathlib").Path('
                + repr(str(sentinel))
                + ').write_text("started")\n'
            )
            subprocess.run(
                ["git", "init", "-b", "entry-regression"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "add", "runner.py"], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Regression",
                    "-c",
                    "user.email=regression@example.invalid",
                    "commit",
                    "-m",
                    "fixture",
                ],
                cwd=root,
                check=True,
                capture_output=True,
            )
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            report = top / "preflight" / "report.json"
            argv = [
                sys.executable,
                str(ROOT / "tools/research/preflight.py"),
                "--repo-root",
                str(root),
                "--experiment-id",
                "UNIT_PREFLIGHT_FAILURE_ONLY",
                "--expected-branch",
                "entry-regression",
                "--expected-head",
                "f" * 40,
                "--runner",
                str(runner),
                "--run-dir",
                str(root / "NEVER_CREATED"),
                "--transport",
                "inprocess",
                "--output",
                str(report),
            ]
            with regression_lock() as fd:
                result = subprocess.run(
                    argv + ["--held-lock-fd", str(fd)],
                    text=True,
                    capture_output=True,
                    timeout=30,
                    pass_fds=(fd,),
                )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["pass"])
            ledger = top / "unit-ledger"
            ledger.mkdir()
            write_new(ledger / "campaign.json", {"unit_fixture": True})
            output = top / "failed-evidence"
            prepared = {"head": head, "task_id": "UNIT_PREFLIGHT_FAILURE_ONLY"}
            error = subprocess.CalledProcessError(result.returncode, argv)
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                try:
                    raise error
                except BaseException as exc:
                    seal_preflight_failure(
                        output,
                        prepared,
                        prepared,
                        {"unit_fixture": True},
                        {"unit_fixture": True},
                        report,
                        exc,
                    )
                    raise
            self.assertEqual(caught.exception.returncode, 2)
            record = verify_manifest(output)
            self.assertEqual(record["status"], "FAILED")
            self.assertEqual(record["diagnostic_status"], "PREFLIGHT_FAILURE")
            self.assertEqual(record["process_returncode"], 2)
            for key in (
                "scientific_attempts",
                "canonical_physics_steps",
                "private_optimizer_calls",
            ):
                self.assertEqual(record[key], 0)
            self.assertEqual(digest(output / "preflight.json"), digest(report))
            self.assertTrue((ledger / "campaign.json").is_file())
            self.assertFalse((ledger / "claim.json").exists())
            self.assertFalse((output / "raw.jsonl").exists())
            self.assertFalse(sentinel.exists())
            with self.assertRaises(ValueError):
                verify_bundle(output)


if __name__ == "__main__":
    unittest.main()
