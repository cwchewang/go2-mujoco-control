"""Receipt applicability and fail-closed historical evidence fixtures."""

import copy
import tempfile
import subprocess
import unittest
from pathlib import Path

from .qualification import REQUIRED_CHECKS, fingerprint, tracked_inputs, validate_record
from . import test_launch
from .verify_capture import verify_capture


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
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("initial")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            before = tracked_inputs(root)
            (root / "README.md").write_text("new prose")
            (root / "tools/substrate/tasks/task.json").write_text("new metadata")
            self.assertEqual(before, tracked_inputs(root))
            (root / "tools/substrate/test_a.py").write_text("new check")
            self.assertNotEqual(before, tracked_inputs(root))
            (root / "tools/substrate/new.py").write_text("new code")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            self.assertIn("tools/substrate/new.py", tracked_inputs(root))

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
