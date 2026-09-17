#!/usr/bin/env python3
"""Queue-aware trusted Atlas dispatcher.

GitHub Issues are the authoritative queue. Workflow invocations only wake this
dispatcher. Multiple Luna workers may prepare/analyze concurrently; each task's
worker owns its own state/worktree and the v6 worker serializes host-live phases.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import atlas_dispatch as legacy
import atlas_issue_state as issue_state
import atlas_research_task as research_base

PROGRESS_PREFIX = "ATLAS_PROGRESS "
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class RepoConfig:
    task_root: str = "docs/research/"
    branch_prefix: str = "research/"
    protected_prefixes: tuple[str, ...] = (".github/", "tools/atlas_")
    evidence_roots: tuple[str, ...] = ("example/cpp/experiments/_runs/",)
    host_policy: str = "serialized"
    max_workers: int = 2
    poll_seconds: float = 5.0
    idle_grace_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "RepoConfig":
        protected = tuple(
            item.strip()
            for item in os.environ.get(
                "ATLAS_PROTECTED_PREFIXES", ".github/,tools/atlas_"
            ).split(",")
            if item.strip()
        )
        evidence = tuple(
            item.strip()
            for item in os.environ.get(
                "ATLAS_EVIDENCE_ROOTS", "example/cpp/experiments/_runs/"
            ).split(",")
            if item.strip()
        )
        host_policy = os.environ.get("ATLAS_HOST_POLICY", "serialized").strip()
        if host_policy != "serialized":
            raise legacy.TaskError("ATLAS_HOST_POLICY must be serialized")
        return cls(
            task_root=os.environ.get("ATLAS_TASK_ROOT", "docs/research/"),
            branch_prefix=os.environ.get("ATLAS_BRANCH_PREFIX", "research/"),
            protected_prefixes=protected,
            evidence_roots=evidence,
            host_policy=host_policy,
            max_workers=max(1, int(os.environ.get("ATLAS_MAX_WORKERS", "2"))),
            poll_seconds=max(0.2, float(os.environ.get("ATLAS_POLL_SECONDS", "5"))),
            idle_grace_seconds=max(
                0.0, float(os.environ.get("ATLAS_IDLE_GRACE_SECONDS", "30"))
            ),
        )


@dataclass(frozen=True)
class QueueTask:
    number: int
    created_at: str
    command: dict[str, Any]
    issue: dict[str, Any]
    resumable: bool = False


class QueueEngine:
    """Small injectable worker-pool scheduler used by production and contract tests."""

    def __init__(
        self,
        *,
        queue_source: Callable[[], list[QueueTask]],
        execute: Callable[[QueueTask], None],
        max_workers: int,
        poll_seconds: float,
        idle_grace_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.queue_source = queue_source
        self.execute = execute
        self.max_workers = max_workers
        self.poll_seconds = poll_seconds
        self.idle_grace_seconds = idle_grace_seconds
        self.sleep = sleep
        self.monotonic = monotonic

    def run(self) -> None:
        active: dict[int, Future[None]] = {}
        finished: set[int] = set()
        idle_since: float | None = None
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while True:
                for number, future in list(active.items()):
                    if not future.done():
                        continue
                    try:
                        future.result()
                    except Exception as exc:
                        print(
                            f"[atlas-dispatch] issue #{number} worker failed: {exc}",
                            flush=True,
                        )
                    finished.add(number)
                    del active[number]

                queue = [
                    task
                    for task in self.queue_source()
                    if task.number not in active and task.number not in finished
                ]
                queue.sort(
                    key=lambda task: (
                        0 if task.resumable else 1,
                        task.created_at,
                        task.number,
                    )
                )
                scheduled = False
                while queue and len(active) < self.max_workers:
                    task = queue.pop(0)
                    active[task.number] = pool.submit(self.execute, task)
                    scheduled = True

                if active or scheduled:
                    idle_since = None
                else:
                    now = self.monotonic()
                    if idle_since is None:
                        idle_since = now
                    elif now - idle_since >= self.idle_grace_seconds:
                        return
                self.sleep(self.poll_seconds)


class ProductionDispatcher:
    def __init__(
        self,
        *,
        full_name: str,
        token: str,
        repo_root: Path,
        output_root: Path,
        config: RepoConfig,
    ) -> None:
        self.full_name = full_name
        self.token = token
        self.repo_root = repo_root
        self.output_root = output_root
        self.config = config
        self.started_at: dict[int, float] = {}
        self.fetch_lock = threading.Lock()
        self.push_lock = threading.Lock()

    def _elapsed(self, number: int) -> float:
        started = self.started_at.setdefault(number, time.monotonic())
        return round(time.monotonic() - started, 1)

    def _progress_path(self, number: int) -> Path:
        path = self.output_root / f"issue-{number}" / "progress.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def publish(self, number: int, progress: dict[str, Any]) -> None:
        progress = dict(progress)
        progress["issue_number"] = number
        progress["elapsed_s"] = self._elapsed(number)
        safe = issue_state.sanitize_progress(progress)
        self._progress_path(number).write_text(
            json.dumps(safe, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        status = safe.get("status", "unknown")
        print(
            f"[atlas-progress] issue=#{number} status={status} "
            f"event={safe.get('last_event', '')}",
            flush=True,
        )
        issue_state.publish_progress(
            full_name=self.full_name,
            number=number,
            token=self.token,
            progress=safe,
            best_effort=True,
        )

    def _is_resumable(self, command: dict[str, Any]) -> bool:
        if command.get("task") != "research-task":
            return False
        parameters = command.get("parameters", {})
        task_commit = parameters.get("task_commit")
        if not isinstance(task_commit, str):
            return False
        try:
            _, _, state_root, _ = research_base._paths()
            state = research_base._load_state(
                research_base._state_path(state_root, task_commit)
            )
        except Exception:
            return False
        return state.get("status") in {
            "starting",
            "running",
            "preparing",
            "candidate_committed",
            "waiting_for_host",
            "host_running",
            "host_completed",
            "analyzing",
            "complete_local",
        } or isinstance(state.get("thread_id"), str)

    def queue_source(self) -> list[QueueTask]:
        tasks: list[QueueTask] = []
        for issue in issue_state.list_open_atlas_tasks(self.full_name, self.token):
            number = issue.get("number")
            if not isinstance(number, int):
                continue
            try:
                command, parsed_number = legacy._extract_command({"issue": issue})
                if parsed_number != number:
                    raise legacy.TaskError("issue number changed during queue parse")
                if command["task"] == "research-task":
                    parameters = command["parameters"]
                    if not parameters["branch"].startswith(self.config.branch_prefix):
                        raise legacy.TaskError("research branch is outside configured prefix")
                    if not parameters["task_path"].startswith(self.config.task_root):
                        raise legacy.TaskError("task path is outside configured task root")
            except legacy.TaskError as exc:
                self.publish(
                    number,
                    {
                        "status": "failed",
                        "last_event": f"invalid queued task: {exc}",
                    },
                )
                continue
            tasks.append(
                QueueTask(
                    number=number,
                    created_at=str(issue.get("created_at") or ""),
                    command=command,
                    issue=issue,
                    resumable=self._is_resumable(command),
                )
            )
        return tasks

    def _prefetch_anchor(self) -> None:
        with self.fetch_lock:
            repo, _, _, _ = research_base._paths()
            legacy._run(["git", "fetch", "origin", "--prune"], repo, timeout=180)

    def _write_result(
        self,
        number: int,
        *,
        status: str,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        issue_dir = self.output_root / f"issue-{number}"
        issue_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 3,
            "issue_number": number,
            "status": status,
            "details": details or {},
            "error": error,
        }
        (issue_dir / "result.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _push_result(self, request: Path) -> str:
        with self.push_lock:
            completed = subprocess.run(
                [
                    "python3",
                    "tools/atlas_push_research_result.py",
                    "--request",
                    str(request),
                ],
                cwd=self.repo_root,
                check=False,
                capture_output=True,
                text=True,
                env=os.environ.copy(),
            )
        output = (completed.stdout + completed.stderr).strip()
        if completed.returncode:
            raise legacy.TaskError(
                f"trusted push failed with exit code {completed.returncode}: "
                f"{output[-4000:] or 'no output'}"
            )
        result = (
            completed.stdout.strip().splitlines()[-1]
            if completed.stdout.strip()
            else ""
        )
        if not SHA_RE.fullmatch(result):
            raise legacy.TaskError("trusted push did not return a commit SHA")
        return result

    def _run_research(self, task: QueueTask) -> dict[str, Any]:
        parameters = task.command["parameters"]
        issue_dir = self.output_root / f"issue-{task.number}"
        issue_dir.mkdir(parents=True, exist_ok=True)
        self._prefetch_anchor()

        env = os.environ.copy()
        env["ATLAS_DISPATCH_PREFETCHED"] = "1"
        env["ATLAS_PROTECTED_PREFIXES"] = ",".join(self.config.protected_prefixes)
        env["ATLAS_EVIDENCE_ROOTS"] = ",".join(self.config.evidence_roots)
        env["ATLAS_HOST_POLICY"] = self.config.host_policy
        command = [
            "python3",
            "tools/atlas_research_task_v6.py",
            "--branch",
            parameters["branch"],
            "--task-path",
            parameters["task_path"],
            "--task-commit",
            parameters["task_commit"],
            "--output-dir",
            str(issue_dir),
        ]
        stdout_path = issue_dir / "worker.stdout.log"
        stderr_path = issue_dir / "worker.stderr.log"
        last_sha = ""
        with stdout_path.open("a", encoding="utf-8") as stdout_log, stderr_path.open(
            "a", encoding="utf-8"
        ) as stderr_log:
            process = subprocess.Popen(
                command,
                cwd=self.repo_root,
                stdout=subprocess.PIPE,
                stderr=stderr_log,
                text=True,
                bufsize=1,
                env=env,
            )
            assert process.stdout is not None
            for line in process.stdout:
                stdout_log.write(line)
                stdout_log.flush()
                stripped = line.strip()
                if stripped.startswith(PROGRESS_PREFIX):
                    try:
                        progress = json.loads(stripped[len(PROGRESS_PREFIX) :])
                    except json.JSONDecodeError:
                        continue
                    if isinstance(progress, dict):
                        self.publish(task.number, progress)
                    continue
                if SHA_RE.fullmatch(stripped):
                    last_sha = stripped
            return_code = process.wait()
        if return_code:
            raise legacy.TaskError(
                f"research worker exited {return_code}; see issue-{task.number} logs"
            )
        request = issue_dir / "research-push.json"
        if not request.is_file():
            raise legacy.TaskError("research worker completed without push request")
        pushed = self._push_result(request)
        if last_sha and pushed != last_sha:
            raise legacy.TaskError("trusted push result differs from worker closeout")
        return {
            "branch": parameters["branch"],
            "task_path": parameters["task_path"],
            "task_commit": parameters["task_commit"],
            "result_commit": pushed,
            "worker_version": 6,
        }

    def execute(self, task: QueueTask) -> None:
        self.started_at[task.number] = time.monotonic()
        parameters = task.command.get("parameters", {})
        self.publish(
            task.number,
            {
                "status": "claimed",
                "branch": parameters.get("branch"),
                "task_commit": parameters.get("task_commit"),
                "last_event": "dispatcher claimed task",
            },
        )
        try:
            if task.command["task"] == "research-task":
                details = self._run_research(task)
            else:
                issue_dir = self.output_root / f"issue-{task.number}"
                details = legacy._run_task(
                    task.command["task"],
                    task.command["parameters"],
                    self.repo_root,
                    issue_dir,
                )
            self._write_result(task.number, status="success", details=details)
            self.publish(
                task.number,
                {
                    "status": "complete",
                    "branch": details.get("branch"),
                    "task_commit": details.get("task_commit"),
                    "result_commit": details.get("result_commit"),
                    "last_event": "trusted result pushed and verified",
                },
            )
        except Exception as exc:
            self._write_result(task.number, status="failure", error=str(exc))
            self.publish(
                task.number,
                {
                    "status": "failed",
                    "branch": parameters.get("branch"),
                    "task_commit": parameters.get("task_commit"),
                    "last_event": str(exc)[:400],
                },
            )
            raise


def _repository_from_event(path: Path) -> str:
    full_name = os.environ.get("GITHUB_REPOSITORY")
    if full_name and "/" in full_name:
        return full_name
    event = legacy._load_event(path)
    repository = event.get("repository", {})
    name = repository.get("full_name") if isinstance(repository, dict) else None
    if not isinstance(name, str) or "/" not in name:
        raise legacy.TaskError("GitHub repository identity is missing")
    return name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required by the trusted queue dispatcher")
    config = RepoConfig.from_env()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    full_name = _repository_from_event(args.event)
    dispatcher = ProductionDispatcher(
        full_name=full_name,
        token=token,
        repo_root=Path(__file__).resolve().parents[1],
        output_root=args.output_dir,
        config=config,
    )
    print(
        f"[atlas-dispatch] queue active repo={full_name} workers={config.max_workers}",
        flush=True,
    )
    QueueEngine(
        queue_source=dispatcher.queue_source,
        execute=dispatcher.execute,
        max_workers=config.max_workers,
        poll_seconds=config.poll_seconds,
        idle_grace_seconds=config.idle_grace_seconds,
    ).run()
    print("[atlas-dispatch] queue empty; idle grace elapsed", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        legacy.TaskError,
        issue_state.GitHubError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"atlas dispatcher failed: {exc}", flush=True)
        raise SystemExit(2)
