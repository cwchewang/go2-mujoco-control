#!/usr/bin/env python3
"""Fail-closed preflight for expensive Go2 research runs.

Checks execution integrity, not scientific merit. Scientific intent remains a
human/agent review responsibility under docs/research/SOP.md.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

DEFAULT_PROCESS_NAMES = ("unitree_mujoco", "real_trot_go2", "run_trot.sh")
LINUX_SAFE_DOMAIN_RANGES = ((0, 101), (215, 232))
SURFACES = {"runtime", "runner", "schema", "scene", "analyzer"}
AUTO_REVIEW_SURFACES = {"runtime", "schema", "scene"}
AUTO_TEST_SURFACES = {"runtime", "schema", "scene"}


def command(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    p = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, check=False)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def shell_command(text: str, cwd: Path) -> tuple[int, str, str]:
    return command(["bash", "-lc", text], cwd)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def add_check(checks: list[dict[str, Any]], name: str, passed: bool,
              detail: Any, severity: str = "hard") -> None:
    checks.append({"name": name,
                   "status": "PASS" if passed else ("WARN" if severity == "warn" else "FAIL"),
                   "severity": severity, "detail": detail})


def dds_ports(domain: int, participant: int = 0) -> dict[str, int]:
    pb, dg, pg = 7400, 250, 2
    return {
        "discovery_multicast": pb + dg * domain,
        "user_multicast": pb + dg * domain + 1,
        "discovery_unicast": pb + dg * domain + 10 + pg * participant,
        "user_unicast": pb + dg * domain + 11 + pg * participant,
    }


def domain_in_linux_safe_pool(domain: int) -> bool:
    return any(lo <= domain <= hi for lo, hi in LINUX_SAFE_DOMAIN_RANGES)


def read_ephemeral_range() -> tuple[int, int] | None:
    try:
        values = Path("/proc/sys/net/ipv4/ip_local_port_range").read_text().split()
        return int(values[0]), int(values[1])
    except (OSError, ValueError, IndexError):
        return None


def runner_domains(text: str) -> list[int]:
    assigned: list[int] = []
    values: list[int] = []
    for raw in text.splitlines():
        code = raw.split("#", 1)[0]
        m = re.fullmatch(r"\s*domain_id\s*=\s*['\"]?([0-9]+)['\"]?\s*", code)
        if m:
            assigned = [int(m.group(1))]
        values.extend(int(v) for v in re.findall(r"--domain-id(?:\s+|=)([0-9]+)", code))
        if re.search(r"--domain-id(?:\s+|=)['\"]?\$domain_id['\"]?", code):
            values.extend(assigned)
    return values


def parent_pid(pid: int) -> int | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split()
        return int(fields[3]) if len(fields) > 3 else None
    except (OSError, ValueError):
        return None


def ancestor_pids(pid: int) -> set[int]:
    out: set[int] = set()
    cur = parent_pid(pid)
    while cur and cur > 1 and cur not in out:
        out.add(cur)
        cur = parent_pid(cur)
    return out


def process_argv_matches(argv: list[str], names: tuple[str, ...]) -> list[str]:
    if not argv:
        return []
    candidates = {Path(argv[0]).name}
    if candidates & {"bash", "sh", "dash", "zsh", "ksh"} and len(argv) > 1 and not argv[1].startswith("-"):
        candidates.add(Path(argv[1]).name)
    return [name for name in names if name in candidates]


def find_processes(names: tuple[str, ...]) -> list[dict[str, Any]]:
    root = Path("/proc")
    if not root.is_dir():
        return []
    excluded = {os.getpid()} | ancestor_pids(os.getpid())
    found: list[dict[str, Any]] = []
    for entry in root.iterdir():
        if not entry.name.isdigit() or int(entry.name) in excluded:
            continue
        try:
            argv = [x.decode("utf-8", errors="replace") for x in
                    (entry / "cmdline").read_bytes().split(b"\0") if x]
        except OSError:
            continue
        matches = process_argv_matches(argv, names)
        if matches:
            found.append({"pid": int(entry.name), "matches": matches, "argv": argv[:8]})
    return found


def domain_lock_free(domain: int) -> tuple[bool, str]:
    path = Path(f"/tmp/unitree_mujoco_run_trot_domain_{domain}.lock")
    f = path.open("a+")
    try:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False, str(path)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True, str(path)
    finally:
        f.close()


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def parse_hash_requirement(raw: str, repo: Path) -> tuple[Path, str]:
    if "=" not in raw:
        raise ValueError("hash requirement must be PATH=SHA256")
    left, expected = raw.rsplit("=", 1)
    p = Path(left)
    return ((p if p.is_absolute() else repo / p).resolve(), expected.lower())


def infer_changed_surfaces(paths: list[str]) -> set[str]:
    out: set[str] = set()
    for path in paths:
        p = path.replace("\\", "/")
        name = Path(p).name
        if p.startswith("unitree_robots/") or (p.startswith("simulate/") and p.endswith(".xml")):
            out.add("scene")
        if p.startswith("example/cpp/scripts/"):
            out.add("runner")
        if name == "trot_experiment_diagnostics.cpp" or "schema" in name.lower() or "telemetry" in name.lower():
            out.add("schema")
        if p.startswith("example/cpp/tools/analysis/") or (p.startswith("example/cpp/tools/") and name.startswith("analyze_")):
            out.add("analyzer")
        if (p.startswith("example/cpp/trot/") or p.startswith("example/cpp/gait/") or
                p.startswith("example/cpp/control/") or p.startswith("simulate/src/")) and name != "trot_experiment_diagnostics.cpp":
            out.add("runtime")
    return out


def diff_paths(repo: Path, base: str, head: str) -> tuple[bool, list[str], str]:
    rc, out, err = command(["git", "diff", "--name-only", f"{base}..{head}"], repo)
    return rc == 0, [x for x in out.splitlines() if x], err


def diff_summary(repo: Path, left: Path, right: Path) -> tuple[bool, dict[str, Any]]:
    rc, out, err = command(["git", "diff", "--no-index", "--", str(left), str(right)], repo)
    if rc not in (0, 1):
        return False, {"error": err}
    data = out.encode()
    additions = sum(1 for line in out.splitlines() if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in out.splitlines() if line.startswith("-") and not line.startswith("---"))
    return True, {"changed": rc == 1, "diff_sha256": sha256_bytes(data),
                  "additions": additions, "deletions": deletions}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, default=Path.cwd())
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--expected-branch", required=True)
    ap.add_argument("--expected-head")
    ap.add_argument("--runner", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--domain", type=int, required=True)
    ap.add_argument("--dds-policy", choices=("linux-safe", "spec-only"), default="linux-safe")
    ap.add_argument("--baseline-runner", type=Path)
    ap.add_argument("--diff-base", help="accepted parent/baseline ref used to auto-detect changed execution surfaces")
    ap.add_argument("--changed-surface", action="append", choices=tuple(sorted(SURFACES)), default=[], help="manual override/addition")
    ap.add_argument("--requires-sol-review", action="store_true", help="use when a runner/analyzer/tooling diff changes trajectory or primary evidence meaning")
    ap.add_argument("--approved-head")
    ap.add_argument("--require-file", action="append", default=[])
    ap.add_argument("--hash", dest="hash_requirements", action="append", default=[])
    ap.add_argument("--test", action="append", default=[], help="reviewed no-live/build test command")
    ap.add_argument("--process-name", action="append", default=[])
    ap.add_argument("--output", type=Path, help="JSON report; stdout or ignored/out-of-repo path recommended")
    args = ap.parse_args()

    repo = args.repo_root.resolve()
    runner = (args.runner if args.runner.is_absolute() else repo / args.runner).resolve()
    run_dir = (args.run_dir if args.run_dir.is_absolute() else repo / args.run_dir).resolve()
    baseline_runner = ((args.baseline_runner if args.baseline_runner.is_absolute() else repo / args.baseline_runner).resolve()
                       if args.baseline_runner else None)
    checks: list[dict[str, Any]] = []
    report: dict[str, Any] = {"schema_version": 2, "experiment_id": args.experiment_id,
                              "repo_root": str(repo), "checks": checks}

    git_rc, head, git_err = command(["git", "rev-parse", "HEAD"], repo)
    branch_rc, branch, branch_err = command(["git", "branch", "--show-current"], repo)
    status_rc, status, status_err = command(["git", "status", "--porcelain"], repo)
    add_check(checks, "git_head_readable", git_rc == 0, head if git_rc == 0 else git_err)
    add_check(checks, "expected_branch", branch_rc == 0 and branch == args.expected_branch,
              {"actual": branch, "expected": args.expected_branch, "stderr": branch_err})
    if args.expected_head:
        add_check(checks, "expected_head", git_rc == 0 and head == args.expected_head,
                  {"actual": head, "expected": args.expected_head})
    add_check(checks, "worktree_clean_before_tests", status_rc == 0 and not status, status or status_err)

    auto_paths: list[str] = []
    auto_surfaces: set[str] = set()
    if args.diff_base and git_rc == 0:
        ok, auto_paths, err = diff_paths(repo, args.diff_base, head)
        add_check(checks, "diff_base_resolved", ok, {"base": args.diff_base, "error": err})
        if ok:
            auto_surfaces = infer_changed_surfaces(auto_paths)
    changed = auto_surfaces | set(args.changed_surface)
    report["changes"] = {"diff_base": args.diff_base, "paths": auto_paths,
                         "auto_surfaces": sorted(auto_surfaces),
                         "manual_surfaces": sorted(set(args.changed_surface)),
                         "surfaces": sorted(changed)}

    runner_exists = runner.is_file()
    add_check(checks, "runner_exists", runner_exists, str(runner))
    runner_text = runner.read_text(encoding="utf-8", errors="replace") if runner_exists else ""
    if runner_exists:
        rc, _, err = command(["bash", "-n", str(runner)], repo)
        add_check(checks, "runner_bash_syntax", rc == 0, err or "PASS")
        domains = runner_domains(runner_text)
        add_check(checks, "runner_domain_matches", domains == [args.domain],
                  {"runner_domains": domains, "expected": args.domain})
    else:
        add_check(checks, "runner_bash_syntax", False, "runner missing")
        add_check(checks, "runner_domain_matches", False, "runner missing")

    ports = dds_ports(args.domain) if args.domain >= 0 else {}
    add_check(checks, "dds_domain_spec_range", 0 <= args.domain <= 232,
              {"domain": args.domain, "allowed": [0, 232]})
    add_check(checks, "dds_rtps_ports_legal", bool(ports) and all(0 <= x <= 65535 for x in ports.values()), ports)
    if args.dds_policy == "linux-safe":
        add_check(checks, "dds_linux_safe_pool", domain_in_linux_safe_pool(args.domain),
                  {"domain": args.domain, "allowed_ranges": LINUX_SAFE_DOMAIN_RANGES})
    eph = read_ephemeral_range()
    if eph and ports:
        lo, hi = eph
        overlap = {k: v for k, v in ports.items() if lo <= v <= hi}
        add_check(checks, "dds_ephemeral_port_overlap", not overlap,
                  {"ephemeral_range": eph, "overlap": overlap},
                  "hard" if args.dds_policy == "linux-safe" else "warn")
    else:
        add_check(checks, "dds_ephemeral_port_range_readable", eph is not None, eph or "unavailable", "warn")
    lock_ok, lock_path = domain_lock_free(args.domain)
    add_check(checks, "dds_domain_lock_free", lock_ok, lock_path)
    add_check(checks, "run_directory_fresh", not run_dir.exists(), str(run_dir))
    names = tuple(args.process_name) if args.process_name else DEFAULT_PROCESS_NAMES
    procs = find_processes(names)
    add_check(checks, "no_stale_runtime_process", not procs, procs)

    for raw in args.require_file:
        p = Path(raw); p = p if p.is_absolute() else repo / p
        add_check(checks, f"required_file:{raw}", p.is_file(), str(p.resolve()))
    for raw in args.hash_requirements:
        try:
            p, expected = parse_hash_requirement(raw, repo)
            actual = sha256_file(p) if p.is_file() else "MISSING"
            add_check(checks, f"hash:{p}", actual == expected,
                      {"actual": actual, "expected": expected})
        except ValueError as e:
            add_check(checks, f"hash:{raw}", False, str(e))

    runner_summary = None
    if baseline_runner:
        if baseline_runner.is_file() and runner.is_file():
            ok, runner_summary = diff_summary(repo, baseline_runner, runner)
            add_check(checks, "baseline_runner_diff_generated", ok, runner_summary)
        else:
            add_check(checks, "baseline_runner_diff_generated", False,
                      {"baseline": str(baseline_runner), "runner": str(runner)})
    report["runner_diff"] = runner_summary

    tests: list[dict[str, Any]] = []
    for i, test in enumerate(args.test, 1):
        rc, out, err = shell_command(test, repo)
        item = {"index": i, "command": test, "return_code": rc,
                "stdout": out, "stderr": err}
        tests.append(item)
        add_check(checks, f"test_{i}", rc == 0, item)
    report["tests"] = tests
    needs_test = bool(changed & AUTO_TEST_SURFACES)
    if needs_test:
        add_check(checks, "changed_surface_has_no_live_test", bool(args.test),
                  {"surfaces": sorted(changed & AUTO_TEST_SURFACES), "test_count": len(args.test)})

    # A runner/analyzer diff is reported automatically, but only requires Sol
    # review when Luna/Sol determine that it changes trajectory or primary
    # evidence meaning. Runtime/schema/scene changes always require review.
    review_required = bool(args.requires_sol_review or (changed & AUTO_REVIEW_SURFACES))
    report["sol_review"] = {"required": review_required, "approved_head": args.approved_head,
                            "current_head": head, "auto_trigger_surfaces": sorted(changed & AUTO_REVIEW_SURFACES)}
    add_check(checks, "sol_review_exact_head",
              (not review_required) or (bool(args.approved_head) and args.approved_head == head),
              "not required" if not review_required else {"approved_head": args.approved_head, "current_head": head})

    post_head_rc, post_head, _ = command(["git", "rev-parse", "HEAD"], repo)
    post_status_rc, post_status, post_err = command(["git", "status", "--porcelain"], repo)
    add_check(checks, "head_unchanged_after_tests", post_head_rc == 0 and post_head == head,
              {"before": head, "after": post_head})
    add_check(checks, "worktree_clean_after_tests", post_status_rc == 0 and not post_status,
              post_status or post_err)

    output: Path | None = None
    output_writable = True
    if args.output:
        output = (args.output if args.output.is_absolute() else repo / args.output).resolve()
        if inside(output, repo):
            rel = output.relative_to(repo)
            rc, _, _ = command(["git", "check-ignore", "-q", "--", str(rel)], repo)
            output_writable = rc == 0
            add_check(checks, "output_preserves_clean_worktree", output_writable,
                      {"output": str(output), "gitignored": output_writable})
        else:
            add_check(checks, "output_preserves_clean_worktree", True,
                      {"output": str(output), "inside_repo": False})

    failures = [x for x in checks if x["severity"] == "hard" and x["status"] == "FAIL"]
    report.update({"git": {"head": head, "branch": branch}, "pass": not failures,
                   "hard_failure_count": len(failures),
                   "warning_count": sum(x["status"] == "WARN" for x in checks)})
    if output:
        report["output"] = {"path": str(output), "written": output_writable}
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output and output_writable:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
