from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import atlas_host_experiment as host  # noqa: E402
import atlas_research_task_v4 as worker  # noqa: E402


SHA = "0123456789abcdef0123456789abcdef01234567"


def _manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "command": [
            "bash",
            "example/cpp/scripts/run_trot.sh",
            "--domain-id",
            "220",
        ],
        "domain_id": 220,
        "run_dir": "example/cpp/experiments/_runs/example/C",
        "timeout_s": 120,
        "environment": {"LD_LIBRARY_PATH": "/opt/mujoco/lib"},
    }


class HostManifestTest(unittest.TestCase):
    def test_extracts_frozen_manifest(self) -> None:
        text = (
            "# task\n\n<!-- ATLAS_HOST_EXPERIMENT\n"
            + json.dumps(_manifest())
            + "\nATLAS_HOST_EXPERIMENT -->\n"
        )
        manifest = host.extract_manifest(text)
        self.assertIsNotNone(manifest)
        assert manifest is not None
        self.assertEqual(manifest["domain_id"], 220)
        self.assertEqual(manifest["command"][-1], "220")

    def test_rejects_shell_c(self) -> None:
        manifest = _manifest()
        manifest["command"] = ["bash", "-c", "echo nope", "--domain-id", "220"]
        with self.assertRaises(host.HostExperimentError):
            host.validate_manifest(manifest)

    def test_rejects_domain_mismatch(self) -> None:
        manifest = _manifest()
        manifest["domain_id"] = 221
        with self.assertRaises(host.HostExperimentError):
            host.validate_manifest(manifest)

    def test_rejects_secret_environment(self) -> None:
        manifest = _manifest()
        manifest["environment"] = {"GITHUB_TOKEN": "nope"}
        with self.assertRaises(host.HostExperimentError):
            host.validate_manifest(manifest)

    def test_rejects_run_dir_escape(self) -> None:
        manifest = _manifest()
        manifest["run_dir"] = "example/cpp/experiments/_runs/../escape"
        with self.assertRaises(host.HostExperimentError):
            host.validate_manifest(manifest)

    def test_rejects_runner_path_mismatch(self) -> None:
        manifest = _manifest()
        manifest["run_dir"] = "example/cpp/experiments/_runs/expected"
        manifest["command"] = [
            "bash",
            "example/cpp/scripts/run_trot.sh",
            "45",
            "different",
            "--domain-id",
            "220",
        ]
        with self.assertRaises(host.HostExperimentError):
            host.validate_manifest(manifest)

    def test_canonical_and_legacy_run_paths_resolve_identically(self) -> None:
        helper = TOOLS.parent / "example/cpp/scripts/experiment_path.sh"
        repo = "/repo"
        cpp = "/repo/example/cpp"

        def resolve(value: str) -> str:
            completed = subprocess.run(
                [
                    "bash",
                    "-c",
                    'source "$1"; resolve_go2_experiment_dir "$2" "$3" "$4"',
                    "bash",
                    str(helper),
                    repo,
                    cpp,
                    value,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return completed.stdout.strip()

        expected = "/repo/example/cpp/experiments/_runs/demo"
        self.assertEqual(
            resolve("example/cpp/experiments/_runs/demo"),
            expected,
        )
        self.assertEqual(resolve("_runs/demo"), expected)
        self.assertEqual(resolve("demo"), expected)


class EvidenceIntegrityTest(unittest.TestCase):
    def test_snapshot_detects_raw_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            expected = host.snapshot_tree(root)
            self.assertTrue(host.verify_snapshot(root, expected))
            (root / "data.csv").write_text("a,b\n1,3\n", encoding="utf-8")
            self.assertFalse(host.verify_snapshot(root, expected))

    def test_closeout_normalizer_is_mechanical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            path = worktree / "docs/validation/example/RESULTS.md"
            path.parent.mkdir(parents=True)
            path.write_text("# Result  \n\nvalue  \n\n\n", encoding="utf-8")

            original = worker.v2._working_tree_paths
            worker.v2._working_tree_paths = lambda _: [
                "docs/validation/example/RESULTS.md"
            ]
            try:
                worker._normalize_closeout_text(worktree)
            finally:
                worker.v2._working_tree_paths = original
            self.assertEqual(path.read_text(encoding="utf-8"), "# Result\n\nvalue\n")


if __name__ == "__main__":
    unittest.main()
