#!/usr/bin/env python3
"""Trusted GitHub issue state/progress helpers for Atlas dispatch."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com"
API_VERSION = "2022-11-28"
MAX_COMMENT_CHARS = 6_000
PROGRESS_MARKER = "<!-- atlas-progress:v1 -->"
TERMINAL_STATES = ("complete", "failed")
CLI_STATES = ("running", "complete", "failed")
PROGRESS_STATES = (
    "queued",
    "claimed",
    "preparing",
    "candidate_committed",
    "waiting_for_host",
    "host_running",
    "host_completed",
    "analyzing",
    "complete",
    "failed",
)
SAFE_PROGRESS_FIELDS = {
    "status",
    "elapsed_s",
    "issue_number",
    "branch",
    "task_commit",
    "candidate_commit",
    "result_commit",
    "tests",
    "build",
    "dds_ready",
    "controller_handoff",
    "scientific_attempt_consumed",
    "gait_cycle",
    "gait_cycle_total",
    "raw_file_count",
    "raw_bytes",
    "host_return_code",
    "last_event",
    "timestamp",
}


class GitHubError(RuntimeError):
    """A GitHub API operation failed."""


def _api(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        API_ROOT + path,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        detail = ""
        if isinstance(exc, HTTPError):
            detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise GitHubError(f"GitHub API {method} {path} failed: {detail or exc}") from exc
    return json.loads(raw) if raw else None


def _event(path: Path) -> tuple[str, int]:
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GitHubError(f"cannot read GitHub event: {exc}") from exc
    repository = event.get("repository", {})
    issue = event.get("issue", {})
    full_name = repository.get("full_name")
    number = issue.get("number")
    if not isinstance(full_name, str) or not full_name:
        raise GitHubError("event repository is missing")
    if not isinstance(number, int) or number <= 0:
        raise GitHubError("event issue number is invalid")
    return full_name, number


def _issue_path(full_name: str, number: int, suffix: str = "") -> str:
    return f"/repos/{full_name}/issues/{number}{suffix}"


def _label_path(full_name: str, number: int, label: str) -> str:
    return _issue_path(full_name, number, f"/labels/{quote(label, safe='')}")


def _notify_mention(full_name: str) -> str:
    login = os.environ.get("ATLAS_NOTIFY_LOGIN")
    if not login:
        login = full_name.split("/", 1)[0]
    login = login.strip().lstrip("@")
    if not login:
        raise GitHubError("Atlas notification login is empty")
    return f"@{login}"


def _label_names(issue: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for label in issue.get("labels", []):
        if isinstance(label, dict) and isinstance(label.get("name"), str):
            names.add(label["name"])
        elif isinstance(label, str):
            names.add(label)
    return names


def list_open_atlas_tasks(full_name: str, token: str) -> list[dict[str, Any]]:
    """Return trusted-candidate open atlas-task issues in creation order."""
    items: list[dict[str, Any]] = []
    page = 1
    while True:
        path = (
            f"/repos/{full_name}/issues"
            f"?state=open&labels=atlas-task&sort=created&direction=asc&per_page=100&page={page}"
        )
        batch = _api("GET", path, token)
        if not isinstance(batch, list):
            raise GitHubError("GitHub issues response is not a list")
        for issue in batch:
            if not isinstance(issue, dict) or "pull_request" in issue:
                continue
            if issue.get("author_association") not in {"OWNER", "MEMBER", "COLLABORATOR"}:
                continue
            labels = _label_names(issue)
            if "atlas-complete" in labels or "atlas-failed" in labels:
                continue
            items.append(issue)
        if len(batch) < 100:
            break
        page += 1
    return items


def sanitize_progress(progress: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in progress.items():
        if key not in SAFE_PROGRESS_FIELDS or value is None:
            continue
        if key == "status":
            if value not in PROGRESS_STATES:
                continue
            safe[key] = value
        elif isinstance(value, bool):
            safe[key] = value
        elif isinstance(value, (int, float)):
            safe[key] = value
        elif isinstance(value, str):
            safe[key] = value[:500]
    # `timestamp` is the publish/update time, not a caller-provided event timestamp.
    # Refresh it on every publication so heartbeat comments show when they changed.
    safe["timestamp"] = int(time.time())
    return safe


def _progress_body(full_name: str, progress: dict[str, Any]) -> str:
    p = sanitize_progress(progress)
    status = p.get("status", "queued")
    lines = [PROGRESS_MARKER, "## Atlas task progress", "", f"- Status: `{status}`"]
    order = (
        ("elapsed_s", "Elapsed"),
        ("branch", "Branch"),
        ("task_commit", "Task commit"),
        ("candidate_commit", "Candidate commit"),
        ("result_commit", "Result commit"),
        ("tests", "Tests"),
        ("build", "Build"),
        ("dds_ready", "DDS ready"),
        ("controller_handoff", "Controller handoff"),
        ("scientific_attempt_consumed", "Scientific attempt consumed"),
        ("gait_cycle", "Gait cycle"),
        ("gait_cycle_total", "Gait cycle total"),
        ("raw_file_count", "Raw files"),
        ("raw_bytes", "Raw bytes"),
        ("host_return_code", "Host return code"),
        ("last_event", "Last safe event"),
        ("timestamp", "Updated"),
    )
    for key, label in order:
        if key in p:
            lines.append(f"- {label}: `{p[key]}`")
    if status in TERMINAL_STATES:
        lines.extend(["", _notify_mention(full_name)])
    return "\n".join(lines)[:MAX_COMMENT_CHARS]


def _find_progress_comment(full_name: str, number: int, token: str) -> int | None:
    comments = _api(
        "GET",
        _issue_path(full_name, number, "/comments?per_page=100"),
        token,
    )
    if not isinstance(comments, list):
        return None
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = comment.get("body")
        comment_id = comment.get("id")
        if (
            isinstance(body, str)
            and PROGRESS_MARKER in body
            and isinstance(comment_id, int)
        ):
            return comment_id
    return None


def _upsert_progress_comment(
    full_name: str,
    number: int,
    token: str,
    progress: dict[str, Any],
) -> None:
    body = _progress_body(full_name, progress)
    comment_id = _find_progress_comment(full_name, number, token)
    if comment_id is None:
        _api(
            "POST",
            _issue_path(full_name, number, "/comments"),
            token,
            {"body": body},
        )
    else:
        _api(
            "PATCH",
            f"/repos/{full_name}/issues/comments/{comment_id}",
            token,
            {"body": body},
        )


def _set_labels(full_name: str, number: int, token: str, state: str) -> None:
    label = "atlas-running" if state not in TERMINAL_STATES else f"atlas-{state}"
    _api(
        "POST",
        _issue_path(full_name, number, "/labels"),
        token,
        {"labels": [label]},
    )
    for old in ("atlas-running", "atlas-complete", "atlas-failed"):
        if old == label:
            continue
        try:
            _api("DELETE", _label_path(full_name, number, old), token)
        except GitHubError as exc:
            if "404" not in str(exc):
                raise


def publish_progress(
    *,
    full_name: str,
    number: int,
    token: str,
    progress: dict[str, Any],
    best_effort: bool = True,
) -> bool:
    """Persist one safe progress comment. Observability failures never need fail work."""
    safe = sanitize_progress(progress)
    try:
        status = safe.get("status")
        if isinstance(status, str):
            _set_labels(full_name, number, token, status)
        _upsert_progress_comment(full_name, number, token, safe)
        if status == "complete":
            _api(
                "PATCH",
                _issue_path(full_name, number),
                token,
                {"state": "closed", "state_reason": "completed"},
            )
        return True
    except GitHubError as exc:
        if not best_effort:
            raise
        print(f"[atlas-progress-warning] {exc}", flush=True)
        return False


def _set_state(
    *,
    full_name: str,
    number: int,
    token: str,
    state: str,
    summary_file: Path | None,
) -> None:
    # Compatibility seam for the old workflow CLI. New dispatch uses publish_progress.
    mapped = {"running": "claimed", "complete": "complete", "failed": "failed"}[state]
    last_event = None
    if summary_file and summary_file.is_file():
        last_event = summary_file.read_text(encoding="utf-8")[:500]
    publish_progress(
        full_name=full_name,
        number=number,
        token=token,
        progress={"status": mapped, "last_event": last_event},
        best_effort=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--state", choices=CLI_STATES, required=True)
    parser.add_argument("--summary-file", type=Path)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    full_name, number = _event(args.event)
    _set_state(
        full_name=full_name,
        number=number,
        token=token,
        state=args.state,
        summary_file=args.summary_file,
    )
    print(f"Atlas issue #{number}: {args.state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
