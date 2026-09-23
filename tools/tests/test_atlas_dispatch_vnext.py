from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import atlas_dispatch_v2 as dispatch  # noqa: E402
import atlas_issue_state as issue_state  # noqa: E402
import atlas_research_task_v2 as worker_v2  # noqa: E402
import atlas_research_task_v6 as worker_v6  # noqa: E402


def _task(
    number: int,
    *,
    resumable: bool = False,
    created: str | None = None,
) -> dispatch.QueueTask:
    return dispatch.QueueTask(
        number=number,
        created_at=created or f"2026-09-17T00:00:{number:02d}Z",
        command={"task": "workspace-status", "parameters": {}},
        issue={"number": number},
        resumable=resumable,
    )


class QueueEngineTest(unittest.TestCase):
    def test_two_offline_tasks_overlap(self) -> None:
        barrier = threading.Barrier(2)
        intervals: dict[int, tuple[float, float]] = {}
        lock = threading.Lock()

        def execute(task: dispatch.QueueTask) -> None:
            barrier.wait(timeout=2)
            start = time.monotonic()
            time.sleep(0.05)
            end = time.monotonic()
            with lock:
                intervals[task.number] = (start, end)

        engine = dispatch.QueueEngine(
            queue_source=lambda: [_task(1), _task(2)],
            execute=execute,
            max_workers=2,
            poll_seconds=0.01,
            idle_grace_seconds=0.02,
        )
        engine.run()
        self.assertEqual(set(intervals), {1, 2})
        a, b = intervals[1], intervals[2]
        self.assertLess(max(a[0], b[0]), min(a[1], b[1]))

    def test_new_issue_discovered_while_dispatcher_active(self) -> None:
        calls = 0
        executed: list[int] = []
        gate = threading.Event()

        def source() -> list[dispatch.QueueTask]:
            nonlocal calls
            calls += 1
            return [_task(1)] if calls < 2 else [_task(1), _task(2)]

        def execute(task: dispatch.QueueTask) -> None:
            executed.append(task.number)
            if task.number == 1:
                gate.wait(timeout=0.05)

        engine = dispatch.QueueEngine(
            queue_source=source,
            execute=execute,
            max_workers=2,
            poll_seconds=0.01,
            idle_grace_seconds=0.02,
        )
        engine.run()
        self.assertEqual(set(executed), {1, 2})

    def test_duplicate_queue_entries_execute_once(self) -> None:
        count = 0

        def execute(_: dispatch.QueueTask) -> None:
            nonlocal count
            count += 1

        engine = dispatch.QueueEngine(
            queue_source=lambda: [_task(1), _task(1)],
            execute=execute,
            max_workers=2,
            poll_seconds=0.01,
            idle_grace_seconds=0.02,
        )
        engine.run()
        self.assertEqual(count, 1)

    def test_resumable_task_precedes_new_fifo_work(self) -> None:
        order: list[int] = []
        engine = dispatch.QueueEngine(
            queue_source=lambda: [
                _task(1, created="2026-09-17T00:00:01Z"),
                _task(2, resumable=True, created="2026-09-17T00:00:02Z"),
            ],
            execute=lambda task: order.append(task.number),
            max_workers=1,
            poll_seconds=0.01,
            idle_grace_seconds=0.02,
        )
        engine.run()
        self.assertEqual(order[:2], [2, 1])


class HostLockTest(unittest.TestCase):
    def test_host_live_intervals_never_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "host.lock"
            intervals: list[tuple[float, float]] = []
            lock = threading.Lock()
            ready = threading.Barrier(2)

            def run() -> None:
                ready.wait(timeout=2)
                with worker_v6._exclusive_lock(path, blocking=True):
                    start = time.monotonic()
                    time.sleep(0.04)
                    end = time.monotonic()
                with lock:
                    intervals.append((start, end))

            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2)
            self.assertEqual(len(intervals), 2)
            intervals.sort()
            self.assertLessEqual(intervals[0][1], intervals[1][0])


class ResourceProvisioningTest(unittest.TestCase):
    def test_verified_resources_are_linked_into_ignored_substrate_namespace(
        self,
    ) -> None:
        old = os.environ.get("GO2_SUBSTRATE_RESOURCE_ROOT")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                worktree = root / "task"
                resources = root / "resources"
                (worktree / "tools/substrate").mkdir(parents=True)
                (resources / "rl").mkdir(parents=True)
                (resources / "upstream-go2-30e74dc5/deploy").mkdir(parents=True)
                (resources / "venv-reliable/bin").mkdir(parents=True)
                (resources / "headless-reliable").mkdir(parents=True)

                policy = resources / "rl/policy.pt"
                policy.write_bytes(b"policy")
                source = resources / "upstream-go2-30e74dc5/deploy/source.py"
                source.write_bytes(b"source")

                (worktree / "tools/substrate/sources.lock.json").write_text(
                    json.dumps(
                        {
                            "rl": {
                                "sha256": hashlib.sha256(b"policy").hexdigest()
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                (worktree / "tools/substrate/rl_reference.lock.json").write_text(
                    json.dumps(
                        {
                            "files": {
                                "deploy/source.py": hashlib.sha256(
                                    b"source"
                                ).hexdigest()
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                python = resources / "venv-reliable/bin/python"
                python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                python.chmod(0o755)
                (resources / "headless-reliable/go2_mjpc_admit").write_bytes(
                    b"elf"
                )

                os.environ["GO2_SUBSTRATE_RESOURCE_ROOT"] = str(resources)
                worker_v6._provision_substrate_resources(worktree)

                self.assertEqual(
                    (worktree / ".substrate/rl/policy.pt").resolve(),
                    policy.resolve(),
                )
                self.assertEqual(
                    (worktree / ".substrate/upstream-go2-30e74dc5").resolve(),
                    (resources / "upstream-go2-30e74dc5").resolve(),
                )
                self.assertEqual(
                    (worktree / ".substrate/venv-reliable").resolve(),
                    (resources / "venv-reliable").resolve(),
                )
                self.assertEqual(
                    (worktree / ".substrate/headless-reliable").resolve(),
                    (resources / "headless-reliable").resolve(),
                )
        finally:
            if old is None:
                os.environ.pop("GO2_SUBSTRATE_RESOURCE_ROOT", None)
            else:
                os.environ["GO2_SUBSTRATE_RESOURCE_ROOT"] = old

    def test_checkpoint_hash_mismatch_fails_closed(self) -> None:
        old = os.environ.get("GO2_SUBSTRATE_RESOURCE_ROOT")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                worktree = root / "task"
                resources = root / "resources"
                (worktree / "tools/substrate").mkdir(parents=True)
                (resources / "rl").mkdir(parents=True)
                (resources / "rl/policy.pt").write_bytes(b"wrong")
                (worktree / "tools/substrate/sources.lock.json").write_text(
                    json.dumps({"rl": {"sha256": "0" * 64}}), encoding="utf-8"
                )
                (worktree / "tools/substrate/rl_reference.lock.json").write_text(
                    json.dumps({"files": {}}), encoding="utf-8"
                )
                os.environ["GO2_SUBSTRATE_RESOURCE_ROOT"] = str(resources)
                with self.assertRaises(Exception):
                    worker_v6._provision_substrate_resources(worktree)
        finally:
            if old is None:
                os.environ.pop("GO2_SUBSTRATE_RESOURCE_ROOT", None)
            else:
                os.environ["GO2_SUBSTRATE_RESOURCE_ROOT"] = old


class CloseoutNormalizationTest(unittest.TestCase):
    def test_validation_markdown_trailing_whitespace_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "docs/validation/example/RESULTS.md"
            path.parent.mkdir(parents=True)
            path.write_text("# Result  \nline\t\n\n", encoding="utf-8")
            worker_v2._normalize_closeout_markdown(
                root, ["docs/validation/example/RESULTS.md"]
            )
            self.assertEqual(path.read_text(encoding="utf-8"), "# Result\nline\n")


class ProgressTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_api = issue_state._api
        self.original_time = issue_state.time.time

    def tearDown(self) -> None:
        issue_state._api = self.original_api
        issue_state.time.time = self.original_time

    def test_single_progress_comment_is_updated_in_place(self) -> None:
        comments: list[dict[str, object]] = []
        posts = 0
        patches = 0

        def fake_api(method: str, path: str, token: str, payload=None):
            nonlocal posts, patches
            del token
            if method == "GET" and path.endswith("/comments?per_page=100"):
                return list(comments)
            if method == "POST" and path.endswith("/comments"):
                posts += 1
                comments.append({"id": 99, "body": payload["body"]})
                return comments[-1]
            if method == "PATCH" and "/issues/comments/99" in path:
                patches += 1
                comments[0]["body"] = payload["body"]
                return comments[0]
            if method in {"POST", "DELETE", "PATCH"}:
                return {}
            raise AssertionError((method, path))

        issue_state._api = fake_api
        self.assertTrue(
            issue_state.publish_progress(
                full_name="owner/repo",
                number=7,
                token="x",
                progress={"status": "preparing", "last_event": "build"},
                best_effort=False,
            )
        )
        self.assertTrue(
            issue_state.publish_progress(
                full_name="owner/repo",
                number=7,
                token="x",
                progress={"status": "analyzing", "last_event": "tests"},
                best_effort=False,
            )
        )
        self.assertEqual(posts, 1)
        self.assertGreaterEqual(patches, 1)
        self.assertEqual(len(comments), 1)
        self.assertIn("analyzing", str(comments[0]["body"]))

    def test_progress_allowlist_drops_hidden_or_arbitrary_fields(self) -> None:
        safe = issue_state.sanitize_progress(
            {
                "status": "preparing",
                "last_event": "unit tests",
                "chain_of_thought": "secret",
                "raw_model_output": "secret",
            }
        )
        self.assertEqual(safe["status"], "preparing")
        self.assertNotIn("chain_of_thought", safe)
        self.assertNotIn("raw_model_output", safe)

    def test_progress_timestamp_refreshes_on_every_publish(self) -> None:
        issue_state.time.time = lambda: 1234.0
        safe = issue_state.sanitize_progress({"status": "preparing", "timestamp": 7})
        self.assertEqual(safe["timestamp"], 1234)

    def test_progress_api_failure_is_best_effort(self) -> None:
        def fail_api(*args, **kwargs):
            raise issue_state.GitHubError("offline")

        issue_state._api = fail_api
        ok = issue_state.publish_progress(
            full_name="owner/repo",
            number=8,
            token="x",
            progress={"status": "preparing"},
            best_effort=True,
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
