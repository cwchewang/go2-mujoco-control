"""Receipt applicability and fail-closed historical evidence fixtures."""

import copy
import tempfile
import subprocess
import unittest
import json
from unittest.mock import patch
from pathlib import Path

from .qualification import (
    REQUIRED_CHECKS,
    controller_inputs,
    fingerprint,
    tracked_inputs,
    validate_record,
)
from . import test_launch
from .verify_capture import verify_capture
from .integrity import digest
from .readiness import validate_authorization
from .task import load_task


class QualificationTests(unittest.TestCase):
    def record(self):
        inputs = {"tracked_files": {"runtime.py": "a"}, "runtime": {"python": "3.10"}}
        record = {
            "qualification": {
                "head": "a" * 40,
                "clean_head": True,
                "development": False,
            },
            "qualification_checks": {
                name: {"returncode": 0} for name in REQUIRED_CHECKS
            },
            "qualification_inputs": inputs,
            "qualification_fingerprint": fingerprint(inputs),
        }
        return inputs, record

    def test_same_inputs_allow_new_git_identity_but_not_dependency_drift(self):
        inputs, record = self.record()
        validate_record(record, inputs)
        changed = copy.deepcopy(inputs)
        changed["runtime"]["python"] = "3.10.other"
        with self.assertRaisesRegex(ValueError, "inputs"):
            validate_record(record, changed)

    def test_dirty_development_incomplete_failed_receipts_rejected(self):
        for mutation in (
            lambda r: r["qualification"].update(clean_head=False),
            lambda r: r["qualification"].update(development=True),
            lambda r: r["qualification_checks"].pop("substrate_tests"),
            lambda r: r["qualification_checks"]["substrate_tests"].update(returncode=1),
        ):
            inputs, record = self.record()
            mutation(record)
            with self.assertRaises(ValueError):
                validate_record(record, inputs)

    def test_documentation_and_task_metadata_are_excluded_but_tests_are_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            for name in (
                "tools/substrate/tasks/task.json",
                "tools/substrate/test_a.py",
                "tools/substrate/run.py",
                "README.md",
                "scripts/launch.sh",
                "simulate_python/go2.py",
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("initial")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            before = tracked_inputs(root)
            self.assertIn("scripts/launch.sh", before)
            self.assertIn("simulate_python/go2.py", before)
            (root / "README.md").write_text("new prose")
            (root / "tools/substrate/tasks/task.json").write_text("new metadata")
            self.assertEqual(before, tracked_inputs(root))
            (root / "tools/substrate/test_a.py").write_text("new check")
            self.assertNotEqual(before, tracked_inputs(root))
            (root / "tools/substrate/new.py").write_text("new code")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            self.assertIn("tools/substrate/new.py", tracked_inputs(root))

    def test_authorization_binds_declared_budget(self):
        prepared = dict(
            head="a", protocol_sha256="b", prepared_manifest_sha256="c", max_attempts=4
        )
        auth = dict(
            prepared,
            action="START_FORMAL_CAPTURE",
            authorized_by="user",
            user_instruction="fixture",
        )
        validate_authorization(auth, prepared)
        auth["max_attempts"] = 3
        with self.assertRaisesRegex(ValueError, "authorization"):
            validate_authorization(auth, prepared)

    def test_task_cannot_select_protocol_outside_qualified_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proto = root / "docs/protocol.json"
            proto.parent.mkdir()
            proto.write_text('{"max_attempts":3}')
            value = dict(
                schema=1,
                branch="fixture",
                protocol="docs/protocol.json",
                protocol_sha256=digest(proto),
                diff_base="a" * 40,
            )
            task = root / "task.json"
            task.write_text(json.dumps(value))
            with patch("tools.substrate.task.subprocess.run"):
                with self.assertRaisesRegex(ValueError, "qualified protocol"):
                    load_task(task, root)

    def test_not_run_claim_rejected_even_when_external_ledger_agrees(self):
        fixture = test_launch.LaunchTests()
        fixture.setUp()
        try:

            def fall(row):
                if row["tick"] == 7:
                    row["qpos"][2] = 0.1

            _, _, _, root = fixture.campaign(fall)
            directory = root / "capture"
            ledger = root / "_runs/substrate_attempts/rl-flat-compatibility-v1"
            forged = '{"index":2}'
            (directory / "attempt_02_claim.json").write_text(forged)
            (ledger / "attempt_02.json").write_text(forged)
            (directory / "manifest.json").write_text(
                json.dumps(
                    {
                        p.relative_to(directory).as_posix(): digest(p)
                        for p in directory.rglob("*")
                        if p.is_file() and p.name != "manifest.json"
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "campaign stop"):
                verify_capture(directory, root / "prepared", ledger)
        finally:
            fixture.doCleanups()

    def test_controller_external_header_change_invalidates_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / "build"
            build.mkdir()
            header = root / "external.hpp"
            header.write_text("original")
            (build / "CMakeCache.txt").write_text("fixture")
            (build / "file.o.d").write_text("file.o: " + str(header))
            before = controller_inputs(build)
            header.write_text("changed external dependency")
            self.assertNotEqual(before, controller_inputs(build))

    def test_unknown_substrate_executables_are_classified(self):
        from tools.research.preflight import infer_changed_surfaces

        for name in ("new.cpp", "new.hpp", "new.sh", "new.cmake", "CMakeLists.txt"):
            self.assertIn(
                "runtime", infer_changed_surfaces(["tools/substrate/" + name])
            )

    def test_ledger_requires_exact_claims_and_file_set(self):
        fixture = test_launch.LaunchTests()
        fixture.setUp()
        try:
            _, _, _, root = fixture.campaign()
            ledger = root / "_runs/substrate_attempts/rl-flat-compatibility-v1"
            self.assertTrue(
                verify_capture(root / "capture", root / "prepared", ledger)[
                    "external_ledger_verified"
                ]
            )
            (ledger / "unexpected.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "file set"):
                verify_capture(root / "capture", root / "prepared", ledger)
        finally:
            fixture.doCleanups()
