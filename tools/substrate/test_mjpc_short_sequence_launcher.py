"""No-native end-to-end tests of the exact repo launcher command."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid
from unittest.mock import Mock

from . import fd_duplicate_diagnostic as d
from . import mjpc_short_sequence as sequence
from . import mjpc_short_sequence_launcher as launcher


def snapshot(directory):
    return {
        p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob("*")
        if p.is_file()
    }


class LauncherEndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = d.ROOT
        cls.wrapper = launcher.WRAPPER
        cls.old_prepared = (
            cls.root / "_runs/mjpc_fd_duplicate_diagnostic_prepare_contractfix_20261002"
        )
        cls.failed = (
            cls.root / "_runs/mjpc_fd_duplicate_sequence_execution_84e85199f6b3"
        )
        originals = Path("/tmp/go2-mjpc-fd-diagnostic")
        if (
            not d.CAPTURE.exists()
            or not (originals / "go2_mjpc_controller_fd_original").exists()
        ):
            raise unittest.SkipTest("Atlas sealed inputs and diagnostic build required")
        if d.git("status", "--porcelain"):
            raise AssertionError(
                "full launcher tests require the committed clean checkout"
            )
        cls.preserved = {
            path: snapshot(path) for path in (cls.old_prepared, cls.failed)
        }
        cls.tag = uuid.uuid4().hex
        cls.bundle = cls.root / ("_runs/mjpc_short_sequence_launcher_e2e_" + cls.tag)
        argv = [
            str(cls.wrapper),
            "--prepare",
            "--original-binary",
            str(originals / "go2_mjpc_controller_fd_original"),
            "--fixed-binary",
            str(originals / "go2_mjpc_controller_fd_fixed"),
            "--output",
            str(cls.bundle),
        ]
        result = subprocess.run(argv, cwd="/tmp", text=True, capture_output=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.prepare_report = json.loads(result.stdout)
        cls.packet = cls.bundle / "packet.json"
        cls.bundle_before = snapshot(cls.bundle)

    @classmethod
    def tearDownClass(cls):
        # Keep all fixtures and existing evidence; never remove ignored run records.
        for path, before in cls.preserved.items():
            if snapshot(path) != before:
                raise AssertionError("old evidence changed: " + str(path))
        if snapshot(cls.bundle) != cls.bundle_before:
            raise AssertionError("sealed test packet changed")

    def command(self, output):
        return [
            str(self.wrapper),
            "--execute",
            "--packet",
            str(self.packet),
            "--output",
            str(output),
            "--no-launch",
        ]

    def check_from(self, cwd, suffix):
        output = self.root / (
            "_runs/mjpc_short_sequence_no_launch_" + self.tag + "_" + suffix
        )
        command = self.command(output)
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "PRECHECK_PASS_NO_LAUNCH")
        self.assertEqual(report["working_directory"], str(self.root))
        self.assertEqual(report["optimizer_calls_executed"], 0)
        self.assertEqual(report["native_processes_started"], 0)
        self.assertFalse(output.exists())
        self.assertEqual(snapshot(self.bundle), self.bundle_before)

    def test_complete_command_from_tmp(self):
        self.check_from("/tmp", "tmp")

    def test_complete_command_from_repo(self):
        self.check_from(self.root, "repo")

    def test_existing_empty_and_nonempty_outputs_are_rejected_without_writes(self):
        for label, content in (("empty", None), ("nonempty", "keep exact bytes\n")):
            with self.subTest(label=label):
                output = self.root / (
                    "_runs/mjpc_short_sequence_existing_" + self.tag + "_" + label
                )
                output.mkdir()
                if content is not None:
                    (output / "sentinel.txt").write_text(content)
                before = snapshot(output)
                result = subprocess.run(
                    self.command(output), cwd="/tmp", text=True, capture_output=True
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("output must be fresh", result.stderr)
                self.assertEqual(snapshot(output), before)

    def test_complete_prepare_and_execute_reject_sealed_parent_without_new_members(
        self,
    ):
        for parent in (self.old_prepared, self.bundle):
            before = snapshot(parent)
            output = parent / "must-not-be-created"
            execute_result = subprocess.run(
                self.command(output), cwd="/tmp", text=True, capture_output=True
            )
            self.assertNotEqual(execute_result.returncode, 0)
            self.assertIn("outside sealed evidence", execute_result.stderr)
            prepare_result = subprocess.run(
                [
                    str(self.wrapper),
                    "--prepare",
                    "--original-binary",
                    "/tmp/go2-mjpc-fd-diagnostic/go2_mjpc_controller_fd_original",
                    "--fixed-binary",
                    "/tmp/go2-mjpc-fd-diagnostic/go2_mjpc_controller_fd_fixed",
                    "--output",
                    str(output),
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(prepare_result.returncode, 0)
            self.assertIn("outside sealed evidence", prepare_result.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(snapshot(parent), before)

    def test_actual_batch_rejects_sealed_parent_before_transport(self):
        forbidden = Mock(side_effect=AssertionError("native transport must not start"))
        with self.assertRaisesRegex(ValueError, "outside sealed evidence"):
            sequence.run_sequence_batch(
                d.CAPTURE,
                {},
                {},
                self.bundle / "core-must-not-create",
                popen=forbidden,
                native_transport=forbidden,
            )
        forbidden.assert_not_called()
        self.assertEqual(snapshot(self.bundle), self.bundle_before)

    def test_no_launch_mode_cannot_reach_injected_runner(self):
        forbidden = Mock(side_effect=AssertionError("runner must not start"))
        output = self.root / ("_runs/mjpc_short_sequence_no_runner_" + self.tag)
        result = launcher.execute(self.packet, output, no_launch=True, runner=forbidden)
        self.assertEqual(result["optimizer_calls_executed"], 0)
        forbidden.assert_not_called()
        self.assertFalse(output.exists())

    def test_failed_manifest_and_members_are_preserved(self):
        self.assertEqual(
            d.digest(self.failed / "manifest.json"),
            "eb1d857fb777ec381867a0c822ffa471436b5165fcb5201093f99274ad4655db",
        )
        admission = d.verify_manifest(self.failed)
        self.assertEqual(admission["optimizer_calls_executed"], 0)
        self.assertEqual(admission["status"], "FAILED")


class PathProtectionTest(unittest.TestCase):
    def test_symlink_alias_cannot_bypass_sealed_ancestor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sealed = root / "sealed"
            sealed.mkdir()
            (sealed / "manifest.json").write_text("{}")
            (sealed / "admission.json").write_text("{}")
            alias = root / "alias"
            alias.symlink_to(sealed, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink or alias"):
                sequence.require_fresh_output(alias / "must-not-create")
            self.assertFalse((sealed / "must-not-create").exists())

    def test_core_existing_directory_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "output must be fresh"):
                sequence.require_fresh_output(temporary)


if __name__ == "__main__":
    unittest.main()
