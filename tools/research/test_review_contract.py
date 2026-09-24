from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.research.review_contract import (
    contract_hashes,
    inherited_approvals,
    routing,
    validate_receipt,
)
from tools.research.review_precheck import run_precheck


class ReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "Fixture"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "fixture@example.invalid"],
            check=True,
        )

        for path in (
            "tools/substrate/protocols",
            "tools/substrate/tasks",
            "tools/research/review_contracts",
            "docs/research",
        ):
            (self.root / path).mkdir(parents=True, exist_ok=True)

        self.protocol_path = self.root / "tools/substrate/protocols/test.json"
        self.protocol = {
            "schema": 1,
            "id": "fixture",
            "max_attempts": 2,
            "threshold": 0.5,
            "retry": "none",
        }
        self._write_json(self.protocol_path, self.protocol)

        self.runner_path = self.root / "runner.py"
        self.runner_path.write_text("print('runner')\n", encoding="utf-8")
        self.verifier_path = self.root / "verifier.py"
        self.verifier_path.write_text("FORMAT = 1\n", encoding="utf-8")
        self.task_doc = self.root / "docs/research/TASK.md"
        self.task_doc.write_text("# task\n", encoding="utf-8")
        self.alt_task_doc = self.root / "docs/research/TASK_ALT.md"
        self.alt_task_doc.write_text("# alt\n", encoding="utf-8")

        self.contract_path = (
            self.root / "tools/research/review_contracts/fixture.json"
        )
        self.contract = {
            "schema": 1,
            "name": "fixture",
            "domains": {
                "science": {
                    "files": [],
                    "json_files": ["tools/substrate/protocols/test.json"],
                    "values": {"question": "fixture question"},
                },
                "execution": {
                    "files": ["runner.py"],
                    "json_files": ["tools/substrate/tasks/test.json"],
                    "values": {},
                },
                "evidence": {
                    "files": ["verifier.py"],
                    "json_files": [],
                    "values": {},
                },
            },
            "precheck": {"commands": [], "timeout_seconds": 30},
        }
        self._write_json(self.contract_path, self.contract)

        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-qm", "fixture base"],
            check=True,
        )
        self.diff_base = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True
        ).strip()

        self.task_path = self.root / "tools/substrate/tasks/test.json"
        self.task = {
            "schema": 1,
            "branch": "research/fixture",
            "protocol": "tools/substrate/protocols/test.json",
            "protocol_sha256": self._raw_sha(self.protocol_path),
            "diff_base": self.diff_base,
            "praxis": {
                "issue_number": 7,
                "task_path": "docs/research/TASK.md",
            },
            "review_contract": "tools/research/review_contracts/fixture.json",
        }
        self._write_json(self.task_path, self.task)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-qm", "fixture task"],
            check=True,
        )

    def _write_json(self, path: Path, value) -> None:
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _raw_sha(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def hashes(self):
        return contract_hashes(
            "tools/research/review_contracts/fixture.json",
            self.root,
        )["contracts"]

    def test_issue_number_changes_execution_only(self):
        before = self.hashes()
        task = json.loads(self.task_path.read_text())
        task["praxis"]["issue_number"] = 8
        self._write_json(self.task_path, task)
        after = self.hashes()
        self.assertEqual(routing(before, after)["changed_domains"], ["execution"])
        report = run_precheck(
            task_path=self.task_path,
            expected_praxis_issue_number=7,
            root=self.root,
            run_static_commands=False,
        )
        self.assertFalse(report["pass"])
        check = next(
            item for item in report["checks"]
            if item["name"] == "expected_praxis_issue_number"
        )
        self.assertEqual(check["status"], "FAIL")

    def test_task_path_changes_execution_only(self):
        before = self.hashes()
        task = json.loads(self.task_path.read_text())
        task["praxis"]["task_path"] = "docs/research/TASK_ALT.md"
        self._write_json(self.task_path, task)
        after = self.hashes()
        self.assertEqual(routing(before, after)["changed_domains"], ["execution"])

    def test_threshold_changes_science_only(self):
        before = self.hashes()
        protocol = json.loads(self.protocol_path.read_text())
        protocol["threshold"] = 0.7
        self._write_json(self.protocol_path, protocol)
        after = self.hashes()
        self.assertEqual(routing(before, after)["changed_domains"], ["science"])

    def test_verifier_serialization_changes_evidence_only(self):
        before = self.hashes()
        self.verifier_path.write_text("FORMAT = 2\n", encoding="utf-8")
        after = self.hashes()
        self.assertEqual(routing(before, after)["changed_domains"], ["evidence"])

    def test_science_approval_inherits_across_execution_only_fix(self):
        before = self.hashes()
        science_receipt = {
            "schema": 1,
            "verdict": "APPROVED",
            "reviewer": "science-reviewer",
            "reviewed_domains": ["science"],
            "contracts": {"science": before["science"]},
            "target_head": "a" * 40,
            "evidence": ["science-review.json"],
            "summary": "science approved",
        }

        task = json.loads(self.task_path.read_text())
        task["praxis"]["issue_number"] = 8
        self._write_json(self.task_path, task)
        after = self.hashes()

        validate_receipt(
            science_receipt,
            after,
            required_domains=["science"],
        )
        inherited = inherited_approvals(
            [science_receipt],
            after,
            required_domains=["science"],
        )
        self.assertTrue(inherited["pass"])
        self.assertEqual(inherited["missing"], [])
        self.assertEqual(routing(before, after)["reviews_required"], ["execution"])

    def test_precheck_positive_identity_and_negative_controls(self):
        report = run_precheck(
            task_path=self.task_path,
            expected_praxis_issue_number=7,
            expected_praxis_task_path="docs/research/TASK.md",
            root=self.root,
            run_static_commands=False,
        )
        self.assertTrue(report["pass"])
        identity = report["identity"]
        self.assertTrue(identity["exact_binding_pass"])
        self.assertTrue(identity["wrong_issue_rejected"])
        self.assertTrue(identity["wrong_task_path_rejected"])
        self.assertEqual(report["physics_steps"], 0)
        self.assertEqual(report["scientific_attempts"], 0)


if __name__ == "__main__":
    unittest.main()
