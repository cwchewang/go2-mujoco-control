from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import atlas_dispatch  # noqa: E402
import atlas_push_research_result  # noqa: E402
import atlas_research_task  # noqa: E402


SHA = "0123456789abcdef0123456789abcdef01234567"


def _event(body: dict[str, object]) -> dict[str, object]:
    return {
        "issue": {
            "number": 7,
            "body": json.dumps(body),
        }
    }


class AtlasDispatchContractTest(unittest.TestCase):
    def test_research_task_contract_accepts_pointer_only(self) -> None:
        command, issue = atlas_dispatch._extract_command(
            _event(
                {
                    "task": "research-task",
                    "parameters": {
                        "branch": "research/example-20260917",
                        "task_path": "docs/research/TASK_EXAMPLE_20260917.md",
                        "task_commit": SHA,
                    },
                }
            )
        )
        self.assertEqual(issue, 7)
        self.assertEqual(command["task"], "research-task")
        self.assertEqual(command["parameters"]["task_commit"], SHA)

    def test_research_task_contract_rejects_arbitrary_fields(self) -> None:
        with self.assertRaises(atlas_dispatch.TaskError):
            atlas_dispatch._extract_command(
                _event(
                    {
                        "task": "research-task",
                        "parameters": {
                            "branch": "research/example",
                            "task_path": "docs/research/TASK_EXAMPLE.md",
                            "task_commit": SHA,
                            "command": "rm -rf /",
                        },
                    }
                )
            )

    def test_research_task_contract_rejects_non_research_branch(self) -> None:
        with self.assertRaises(atlas_dispatch.TaskError):
            atlas_dispatch._extract_command(
                _event(
                    {
                        "task": "research-task",
                        "parameters": {
                            "branch": "main",
                            "task_path": "docs/research/TASK_EXAMPLE.md",
                            "task_commit": SHA,
                        },
                    }
                )
            )

    def test_maintenance_tasks_still_require_empty_parameters(self) -> None:
        with self.assertRaises(atlas_dispatch.TaskError):
            atlas_dispatch._extract_command(
                _event(
                    {
                        "task": "repo-smoke",
                        "parameters": {"branch": "research/example"},
                    }
                )
            )


class ResearchWorkerValidationTest(unittest.TestCase):
    def test_worker_request_validation(self) -> None:
        atlas_research_task._validate_request(
            "research/example",
            "docs/research/TASK_EXAMPLE.md",
            SHA,
        )
        with self.assertRaises(atlas_research_task.ResearchTaskError):
            atlas_research_task._validate_request(
                "research/../main",
                "docs/research/TASK_EXAMPLE.md",
                SHA,
            )

    def test_push_payload_validation(self) -> None:
        values = atlas_push_research_result._validate_payload(
            {
                "branch": "research/example",
                "task_commit": SHA,
                "result_commit": "f" * 40,
                "repo": "/tmp/repo",
                "worktree": "/tmp/worktree",
                "state_path": "/tmp/state.json",
            }
        )
        self.assertEqual(values[2], "research/example")
        with self.assertRaises(atlas_push_research_result.PushError):
            atlas_push_research_result._validate_payload(
                {
                    "branch": "main",
                    "task_commit": SHA,
                    "result_commit": "f" * 40,
                    "repo": "/tmp/repo",
                    "worktree": "/tmp/worktree",
                    "state_path": "/tmp/state.json",
                }
            )


if __name__ == "__main__":
    unittest.main()
