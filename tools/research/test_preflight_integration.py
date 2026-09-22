"""Preflight end-to-end fixtures. The runner is never executed."""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.research import preflight as p


class ReadinessFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        def git(*args):
            return subprocess.check_output(
                ["git", *args], cwd=self.root, stderr=subprocess.DEVNULL, text=True
            ).strip()

        self.git = git
        git("init", "-b", "fixture")
        git("config", "user.email", "fixture@example.invalid")
        git("config", "user.name", "Fixture")
        (self.root / "runner.sh").write_text(
            "#!/bin/sh\n# Reviewed fixture; preflight only syntax-checks it.\necho unused --domain-id 230\n"
        )
        (self.root / ".gitignore").write_text("out/\n")
        git("add", ".")
        git("commit", "-m", "fixture")
        self.head = git("rev-parse", "HEAD")

    def call(self, *extra):
        argv = [
            "preflight",
            "--repo-root",
            str(self.root),
            "--experiment-id",
            "fixture",
            "--expected-branch",
            "fixture",
            "--expected-head",
            self.head,
            "--runner",
            "runner.sh",
            "--run-dir",
            "out/capture",
            "--domain",
            "230",
            *extra,
        ]
        stream = io.StringIO()
        with (
            patch.object(sys, "argv", argv),
            patch.object(p, "find_processes", return_value=[]),
            patch.object(p, "occupied_udp_ports", return_value=set()),
            patch.object(p, "read_ephemeral_range", return_value=(32768, 60999)),
            contextlib.redirect_stdout(stream),
        ):
            code = p._main()
        return code, json.loads(stream.getvalue())

    def test_positive_fixture_does_not_launch_runner(self):
        code, result = self.call()
        self.assertEqual(code, 0)
        self.assertTrue(result["pass"])
        self.assertFalse((self.root / "out/capture").exists())

    def test_wrong_head_or_dirty_checkout_fails(self):
        code, result = self.call("--expected-head", "a" * 40)
        self.assertEqual(code, 2)
        (self.root / "dirty").write_text("x")
        code, result = self.call()
        self.assertEqual(code, 2)

    def test_empty_expected_head_cannot_disable_identity_check(self):
        code, result = self.call("--expected-head", "")
        self.assertEqual(code, 2)
        self.assertTrue(
            any(
                c["name"] == "expected_head" and c["status"] == "FAIL"
                for c in result["checks"]
            )
        )

    def test_hard_failure_prevents_test_execution(self):
        code, result = self.call(
            "--expected-head", "a" * 40, "--test", "touch SHOULD_NOT_EXIST"
        )
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())
        self.assertEqual(result["tests"][0]["return_code"], 125)

    def test_output_collision_preserves_original(self):
        target = self.root / "out/report.json"
        target.parent.mkdir()
        target.write_text("original")
        code, result = self.call("--output", str(target))
        self.assertEqual(code, 2)
        self.assertEqual(target.read_text(), "original")

    def test_output_cannot_create_capture_directory(self):
        code, result = self.call("--output", "out/capture/preflight.json")
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "out/capture").exists())

    def test_output_is_written_once_and_worktree_remains_clean(self):
        code, result = self.call("--output", "out/report.json")
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "out/report.json").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_review_required_for_substrate_runtime_change(self):
        base = self.head
        code = self.root / "tools/substrate"
        code.mkdir(parents=True)
        (code / "rl.py").write_text("fixture=1\n")
        self.git("add", ".")
        self.git("commit", "-m", "runtime fixture")
        self.head = self.git("rev-parse", "HEAD")
        status, result = self.call("--diff-base", base, "--test", "true")
        self.assertEqual(status, 2)
        self.assertTrue(result["sol_review"]["required"])
        status, result = self.call(
            "--diff-base", base, "--test", "true", "--approved-head", self.head
        )
        self.assertEqual(status, 0)

    def test_test_mutation_of_runner_is_detected(self):
        status, result = self.call("--test", "printf '# changed\n' >> runner.sh")
        self.assertEqual(status, 2)
        self.assertTrue(
            any(
                x["name"] == "runner_unchanged_after_tests" and x["status"] == "FAIL"
                for x in result["checks"]
            )
        )

    def test_dynamic_domain_assignment_is_rejected(self):
        self.assertEqual(
            p.runner_domains(
                "domain_id=230\ndomain_id=$OTHER\nrun --domain-id $domain_id\n"
            ),
            [],
        )
        self.assertEqual(
            p.runner_domains(
                "domain_id=230\nexport domain_id=231\nrun --domain-id $domain_id\n"
            ),
            [],
        )

    def test_hash_requirement_requires_full_digest(self):
        for value in ("x=bad", "=" + "a" * 64, "x=" + "g" * 64):
            with self.assertRaises(ValueError):
                p.parse_hash_requirement(value, self.root)

    def test_proc_unavailable_fails_closed(self):
        with (
            patch.object(Path, "is_dir", return_value=False),
            self.assertRaises(RuntimeError),
        ):
            p.find_processes(("fixture",))


if __name__ == "__main__":
    unittest.main()
