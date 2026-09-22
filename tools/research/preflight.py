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
import signal
import subprocess
import sys
from typing import Any

DEFAULT_PROCESS_NAMES = ("unitree_mujoco", "real_trot_go2", "run_trot.sh")
LINUX_SAFE_DOMAIN_RANGES = ((0, 101), (215, 232))
SURFACES = {"runtime", "runner", "schema", "scene", "analyzer"}
AUTO_REVIEW_SURFACES = {"runtime", "schema", "scene"}
AUTO_TEST_SURFACES = {"runtime", "schema", "scene", "analyzer"}


def command(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        out, err = process.communicate(timeout=120)
        return process.returncode, out.strip(), err.strip()
    finally:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()
        process.stderr.close()


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


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    detail: Any,
    severity: str = "hard",
) -> None:
    checks.append(
        {
            "name": name,
            "status": "PASS" if passed else ("WARN" if severity == "warn" else "FAIL"),
            "severity": severity,
            "detail": detail,
        }
    )


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
    ambiguous = False
    for raw in text.splitlines():
        code = raw.split("#", 1)[0]
        m = re.fullmatch(r"\s*domain_id\s*=\s*['\"]?([0-9]+)['\"]?\s*", code)
        if re.match(r"\s*(?:export\s+)?domain_id\s*=", code) and not m:
            ambiguous = True
        if m:
            assigned.append(int(m.group(1)))
            if len(assigned) > 1:
                ambiguous = True
        values.extend(int(v) for v in re.findall(r"--domain-id(?:\s+|=)([0-9]+)", code))
        if re.search(r"--domain-id(?:\s+|=)['\"]?\$domain_id['\"]?", code):
            if len(set(assigned)) != 1:
                ambiguous = True
            else:
                values.extend(assigned)
    return [] if ambiguous else values


def parent_pid(pid: int) -> int | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return int(fields[1]) if len(fields) > 1 else None
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
    if (
        candidates & {"bash", "sh", "dash", "zsh", "ksh"}
        and len(argv) > 1
        and not argv[1].startswith("-")
    ):
        candidates.add(Path(argv[1]).name)
    return [name for name in names if name in candidates]


def find_processes(names: tuple[str, ...]) -> list[dict[str, Any]]:
    root = Path("/proc")
    if not root.is_dir():
        raise RuntimeError("process inspection unavailable")
    excluded = {os.getpid()} | ancestor_pids(os.getpid())
    found: list[dict[str, Any]] = []
    for entry in root.iterdir():
        if not entry.name.isdigit() or int(entry.name) in excluded:
            continue
        try:
            argv = [
                x.decode("utf-8", errors="replace")
                for x in (entry / "cmdline").read_bytes().split(b"\0")
                if x
            ]
        except FileNotFoundError:
            continue  # process exited during the snapshot
        except OSError as exc:
            raise RuntimeError("incomplete process inspection: " + str(entry)) from exc
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
    if not left or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise ValueError("hash requirement needs a path and 64 hexadecimal characters")
    p = Path(left)
    return ((p if p.is_absolute() else repo / p).resolve(), expected.lower())


def infer_changed_surfaces(paths: list[str]) -> set[str]:
    out: set[str] = set()
    for path in paths:
        p = path.replace("\\", "/")
        name = Path(p).name
        if p.startswith("unitree_robots/") or (
            p.startswith("simulate/") and p.endswith(".xml")
        ):
            out.add("scene")
        if p.startswith("tools/substrate/") and not name.startswith("test_"):
            if "/tasks/" in p:
                out.add("runner")
            elif "/protocols/" in p or name in (
                "contracts.py",
                "evidence.py",
                "capture.template.json",
            ):
                out.add("schema")
            elif name in ("analyze_capture.py", "verify_capture.py"):
                out.add("analyzer")
            elif name == "launch.py":
                out.update(("runner", "runtime"))
            elif Path(p).suffix.lower() not in (".md", ".rst"):
                out.add("runtime")
        if (
            p.startswith("tools/research/")
            and not name.startswith("test_")
            and p.endswith(".py")
        ):
            out.add("runtime")
        if p.startswith("example/cpp/scripts/"):
            out.add("runner")
        if (
            name == "trot_experiment_diagnostics.cpp"
            or "schema" in name.lower()
            or "telemetry" in name.lower()
        ):
            out.add("schema")
        if p.startswith("example/cpp/tools/analysis/") or (
            p.startswith("example/cpp/tools/") and name.startswith("analyze_")
        ):
            out.add("analyzer")
        if (
            p.startswith("example/cpp/trot/")
            or p.startswith("example/cpp/gait/")
            or p.startswith("example/cpp/control/")
            or p.startswith("simulate/src/")
        ) and name != "trot_experiment_diagnostics.cpp":
            out.add("runtime")
    return out


def diff_paths(repo: Path, base: str, head: str) -> tuple[bool, list[str], str]:
    rc, out, err = command(["git", "diff", "--name-only", f"{base}..{head}"], repo)
    return rc == 0, [x for x in out.splitlines() if x], err


def git_diff_summary(
    repo: Path, base: str, head: str, relative_path: str
) -> tuple[bool, dict[str, Any]]:
    rc, out, err = command(
        ["git", "diff", f"{base}..{head}", "--", relative_path], repo
    )
    if rc != 0:
        return False, {"error": err}
    data = out.encode()
    additions = sum(
        1
        for line in out.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    deletions = sum(
        1
        for line in out.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )
    return True, {
        "changed": bool(out),
        "diff_sha256": sha256_bytes(data),
        "additions": additions,
        "deletions": deletions,
    }


def diff_summary(repo: Path, left: Path, right: Path) -> tuple[bool, dict[str, Any]]:
    rc, out, err = command(
        ["git", "diff", "--no-index", "--", str(left), str(right)], repo
    )
    if rc not in (0, 1):
        return False, {"error": err}
    data = out.encode()
    additions = sum(
        1
        for line in out.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    deletions = sum(
        1
        for line in out.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )
    return True, {
        "changed": rc == 1,
        "diff_sha256": sha256_bytes(data),
        "additions": additions,
        "deletions": deletions,
    }


def occupied_udp_ports():
    ports = set()
    for table in ("/proc/net/udp", "/proc/net/udp6"):
        try:
            lines = Path(table).read_text().splitlines()[1:]
            ports.update(int(line.split()[1].split(":")[1], 16) for line in lines)
        except (OSError, ValueError, IndexError) as exc:
            raise RuntimeError("UDP inspection unavailable: " + table) from exc
    return ports


def _main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, default=Path.cwd())
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--expected-branch", required=True)
    ap.add_argument(
        "--expected-head",
        required=True,
        help="exact HEAD prepared and reviewed for this checkpoint",
    )
    ap.add_argument("--runner", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--domain", type=int)
    ap.add_argument("--transport", choices=("dds", "inprocess"), default="dds")
    ap.add_argument("--held-lock-fd", type=int)
    ap.add_argument(
        "--qualification", type=Path, help="verified content-bound offline test receipt"
    )
    ap.add_argument(
        "--participants",
        type=int,
        default=2,
        help="reserved participant count (controller and simulator default)",
    )
    ap.add_argument(
        "--dds-policy", choices=("linux-safe", "spec-only"), default="linux-safe"
    )
    ap.add_argument("--baseline-runner", type=Path)
    ap.add_argument(
        "--diff-base",
        help="accepted parent/baseline ref used to auto-detect changed execution surfaces",
    )
    ap.add_argument(
        "--changed-surface",
        action="append",
        choices=tuple(sorted(SURFACES)),
        default=[],
        help="manual override/addition",
    )
    ap.add_argument(
        "--requires-sol-review",
        action="store_true",
        help="use when a runner/analyzer/tooling diff changes trajectory or primary evidence meaning",
    )
    ap.add_argument("--approved-head")
    ap.add_argument("--require-file", action="append", default=[])
    ap.add_argument("--hash", dest="hash_requirements", action="append", default=[])
    ap.add_argument(
        "--test",
        action="append",
        default=[],
        help="reviewed no-live/build test command",
    )
    ap.add_argument("--process-name", action="append", default=[])
    ap.add_argument(
        "--output",
        type=Path,
        help="JSON report; stdout or ignored/out-of-repo path recommended",
    )
    args = ap.parse_args()

    repo = args.repo_root.resolve()
    runner = (
        args.runner if args.runner.is_absolute() else repo / args.runner
    ).resolve()
    run_dir = (
        args.run_dir if args.run_dir.is_absolute() else repo / args.run_dir
    ).resolve()
    baseline_runner = (
        (
            args.baseline_runner
            if args.baseline_runner.is_absolute()
            else repo / args.baseline_runner
        ).resolve()
        if args.baseline_runner
        else None
    )
    checks: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "schema_version": 2,
        "experiment_id": args.experiment_id,
        "repo_root": str(repo),
        "checks": checks,
    }

    git_rc, head, git_err = command(["git", "rev-parse", "HEAD"], repo)
    branch_rc, branch, branch_err = command(["git", "branch", "--show-current"], repo)
    status_rc, status, status_err = command(["git", "status", "--porcelain"], repo)
    add_check(
        checks, "git_head_readable", git_rc == 0, head if git_rc == 0 else git_err
    )
    add_check(
        checks,
        "expected_branch",
        branch_rc == 0 and branch == args.expected_branch,
        {"actual": branch, "expected": args.expected_branch, "stderr": branch_err},
    )
    add_check(
        checks,
        "expected_head",
        bool(re.fullmatch(r"[0-9a-f]{40}", args.expected_head))
        and git_rc == 0
        and head == args.expected_head,
        {"actual": head, "expected": args.expected_head},
    )
    add_check(
        checks,
        "worktree_clean_before_tests",
        status_rc == 0 and not status,
        status or status_err,
    )

    auto_paths: list[str] = []
    auto_surfaces: set[str] = set()
    if args.diff_base and git_rc == 0:
        ok, auto_paths, err = diff_paths(repo, args.diff_base, head)
        add_check(
            checks, "diff_base_resolved", ok, {"base": args.diff_base, "error": err}
        )
        if ok:
            auto_surfaces = infer_changed_surfaces(auto_paths)
    changed = auto_surfaces | set(args.changed_surface)
    report["changes"] = {
        "diff_base": args.diff_base,
        "paths": auto_paths,
        "auto_surfaces": sorted(auto_surfaces),
        "manual_surfaces": sorted(set(args.changed_surface)),
        "surfaces": sorted(changed),
    }

    runner_exists = runner.is_file()
    add_check(checks, "runner_exists", runner_exists, str(runner))
    runner_text = (
        runner.read_text(encoding="utf-8", errors="replace") if runner_exists else ""
    )
    if args.transport == "inprocess":
        # Explicit transport semantics, not a fictitious reserved DDS domain.
        add_check(checks, "inprocess_has_no_domain", args.domain is None, args.domain)
        valid = runner_exists and runner.suffix == ".py"
        if valid:
            try:
                compile(runner_text, str(runner), "exec")
            except SyntaxError:
                valid = False
        add_check(checks, "runner_python_syntax", valid, str(runner))
        add_check(
            checks,
            "reviewed_inprocess_runner",
            runner_text.count('TRANSPORT = "inprocess"') == 1,
            "declared and exact-head reviewed; no DDS sockets",
        )
    else:
        if runner_exists:
            rc, _, err = command(["bash", "-n", str(runner)], repo)
            add_check(checks, "runner_bash_syntax", rc == 0, err or "PASS")
            domains = runner_domains(runner_text)
            add_check(
                checks,
                "runner_domain_matches",
                domains == [args.domain],
                {"runner_domains": domains, "expected": args.domain},
            )
        else:
            add_check(checks, "runner_bash_syntax", False, "runner missing")
            add_check(checks, "runner_domain_matches", False, "runner missing")

        if args.domain is None:
            args.domain = -1
        ports = {}
        if 0 <= args.domain <= 232 and 1 <= args.participants <= 120:
            for participant in range(args.participants):
                ports.update(
                    {
                        f"{participant}:{key}": value
                        for key, value in dds_ports(args.domain, participant).items()
                    }
                )
        add_check(
            checks,
            "participant_count_valid",
            1 <= args.participants <= 120,
            args.participants,
        )
        add_check(
            checks,
            "dds_domain_spec_range",
            0 <= args.domain <= 232,
            {"domain": args.domain, "allowed": [0, 232]},
        )
        add_check(
            checks,
            "dds_rtps_ports_legal",
            bool(ports) and all(0 <= x <= 65535 for x in ports.values()),
            ports,
        )
        if args.dds_policy == "linux-safe":
            add_check(
                checks,
                "dds_linux_safe_pool",
                domain_in_linux_safe_pool(args.domain),
                {"domain": args.domain, "allowed_ranges": LINUX_SAFE_DOMAIN_RANGES},
            )
        eph = read_ephemeral_range()
        if eph and ports:
            lo, hi = eph
            overlap = {k: v for k, v in ports.items() if lo <= v <= hi}
            add_check(
                checks,
                "dds_ephemeral_port_overlap",
                not overlap,
                {"ephemeral_range": eph, "overlap": overlap},
                "hard" if args.dds_policy == "linux-safe" else "warn",
            )
        else:
            add_check(
                checks,
                "dds_ephemeral_port_range_readable",
                eph is not None,
                eph or "unavailable",
            )
        try:
            occupied = occupied_udp_ports()
            conflicts = sorted(set(ports.values()) & occupied)
            add_check(checks, "dds_udp_ports_unused", not conflicts, conflicts)
        except RuntimeError as exc:
            add_check(checks, "dds_udp_ports_unused", False, str(exc))
        lock_ok, lock_path = domain_lock_free(args.domain)
        add_check(checks, "dds_domain_lock_free", lock_ok, lock_path)
    add_check(checks, "run_directory_fresh", not run_dir.exists(), str(run_dir))
    names = (
        list(args.process_name) if args.process_name else list(DEFAULT_PROCESS_NAMES)
    )
    if runner_exists and runner.name not in names:
        names.append(runner.name)
    try:
        procs = find_processes(tuple(names))
        add_check(checks, "no_stale_runtime_process", not procs, procs)
    except RuntimeError as exc:
        add_check(checks, "no_stale_runtime_process", False, str(exc))

    for raw in args.require_file:
        p = Path(raw)
        p = p if p.is_absolute() else repo / p
        add_check(checks, f"required_file:{raw}", p.is_file(), str(p.resolve()))
    for raw in args.hash_requirements:
        try:
            p, expected = parse_hash_requirement(raw, repo)
            actual = sha256_file(p) if p.is_file() else "MISSING"
            add_check(
                checks,
                f"hash:{p}",
                actual == expected,
                {"actual": actual, "expected": expected},
            )
        except ValueError as e:
            add_check(checks, f"hash:{raw}", False, str(e))

    runner_summary = None
    if baseline_runner:
        if baseline_runner.is_file() and runner.is_file():
            ok, runner_summary = diff_summary(repo, baseline_runner, runner)
            add_check(checks, "baseline_runner_diff_generated", ok, runner_summary)
        else:
            add_check(
                checks,
                "baseline_runner_diff_generated",
                False,
                {"baseline": str(baseline_runner), "runner": str(runner)},
            )
    elif (
        args.diff_base
        and "runner" in changed
        and runner_exists
        and inside(runner, repo)
    ):
        relative_runner = runner.relative_to(repo).as_posix()
        ok, runner_summary = git_diff_summary(
            repo, args.diff_base, head, relative_runner
        )
        add_check(checks, "baseline_runner_diff_generated", ok, runner_summary)
    report["runner_diff"] = runner_summary

    tests: list[dict[str, Any]] = []
    runner_hash = sha256_file(runner) if runner_exists else None
    initial_failures = any(
        x["status"] == "FAIL" and x["severity"] == "hard" for x in checks
    )
    for i, test in enumerate(args.test, 1):
        if initial_failures:
            rc, out, err = 125, "", "SKIPPED: hard preflight failure before tests"
        else:
            rc, out, err = shell_command(test, repo)
        item = {
            "index": i,
            "command": test,
            "return_code": rc,
            "stdout": out,
            "stderr": err,
        }
        tests.append(item)
        add_check(checks, f"test_{i}", rc == 0, item)
    report["tests"] = tests
    qualified = False
    if args.qualification and not initial_failures:
        try:
            sys.path.insert(0, str(repo))
            from tools.substrate.qualification import validate

            receipt = validate(args.qualification)
            qualified = True
            report["qualification"] = receipt
            add_check(checks, "qualification_receipt_valid", True, receipt)
        except Exception as exc:
            add_check(checks, "qualification_receipt_valid", False, str(exc))
    needs_test = bool(changed & AUTO_TEST_SURFACES)
    if needs_test:
        add_check(
            checks,
            "changed_surface_has_no_live_test",
            bool(args.test) or qualified,
            {
                "surfaces": sorted(changed & AUTO_TEST_SURFACES),
                "test_count": len(args.test),
            },
        )

    # A runner/analyzer diff is reported automatically, but only requires Sol
    # review when Luna/Sol determine that it changes trajectory or primary
    # evidence meaning. Runtime/schema/scene changes always require review.
    review_required = bool(args.requires_sol_review or (changed & AUTO_REVIEW_SURFACES))
    report["sol_review"] = {
        "required": review_required,
        "approved_head": args.approved_head,
        "current_head": head,
        "auto_trigger_surfaces": sorted(changed & AUTO_REVIEW_SURFACES),
    }
    add_check(
        checks,
        "sol_review_exact_head",
        (not review_required)
        or (bool(args.approved_head) and args.approved_head == head),
        "not required"
        if not review_required
        else {"approved_head": args.approved_head, "current_head": head},
    )

    post_head_rc, post_head, _ = command(["git", "rev-parse", "HEAD"], repo)
    post_status_rc, post_status, post_err = command(
        ["git", "status", "--porcelain"], repo
    )
    add_check(
        checks,
        "head_unchanged_after_tests",
        post_head_rc == 0 and post_head == head,
        {"before": head, "after": post_head},
    )
    add_check(
        checks,
        "worktree_clean_after_tests",
        post_status_rc == 0 and not post_status,
        post_status or post_err,
    )

    add_check(
        checks,
        "runner_unchanged_after_tests",
        runner_exists and runner.is_file() and sha256_file(runner) == runner_hash,
        runner_hash,
    )
    for raw in args.hash_requirements:
        try:
            path, expected = parse_hash_requirement(raw, repo)
            add_check(
                checks,
                "hash_after_tests:" + str(path),
                path.is_file() and sha256_file(path) == expected,
                expected,
            )
        except ValueError as exc:
            add_check(checks, "hash_after_tests:" + raw, False, str(exc))
    output: Path | None = None
    output_writable = True
    if args.output:
        output = (
            args.output if args.output.is_absolute() else repo / args.output
        ).resolve()
        if inside(output, repo):
            rel = output.relative_to(repo)
            rc, _, _ = command(["git", "check-ignore", "-q", "--", str(rel)], repo)
            output_writable = rc == 0
            add_check(
                checks,
                "output_preserves_clean_worktree",
                output_writable,
                {"output": str(output), "gitignored": output_writable},
            )
        else:
            add_check(
                checks,
                "output_preserves_clean_worktree",
                True,
                {"output": str(output), "inside_repo": False},
            )

    if output:
        fresh = (
            not output.exists()
            and not output.is_symlink()
            and not inside(output, run_dir)
        )
        add_check(checks, "output_fresh_outside_capture", fresh, str(output))
        output_writable = output_writable and fresh
    failures = [x for x in checks if x["severity"] == "hard" and x["status"] == "FAIL"]
    report.update(
        {
            "git": {"head": head, "branch": branch},
            "pass": not failures,
            "hard_failure_count": len(failures),
            "warning_count": sum(x["status"] == "WARN" for x in checks),
        }
    )
    if output:
        report["output"] = {"path": str(output), "written": output_writable}
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output and output_writable:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
    sys.stdout.write(rendered)
    return 0 if report["pass"] else 2


def main() -> int:
    # Held throughout tests and report generation. This is a readiness snapshot;
    # a future launcher must reacquire and recheck before starting capture.
    def interrupted(signum, frame):
        # selectors retries InterruptedError as EINTR, which would swallow the
        # stop request inside subprocess.communicate and strand its test group.
        raise RuntimeError("preflight interrupted")

    previous_signal = signal.signal(signal.SIGTERM, interrupted)
    try:
        # A launcher may pass its already-held descriptor, preserving one
        # uninterrupted lock across preflight and capture. Verify its inode and
        # acquire on that same open file description; never trust an env flag.
        probe = argparse.ArgumentParser(add_help=False)
        probe.add_argument("--held-lock-fd", type=int)
        inherited, _ = probe.parse_known_args()
        lock_path = "/tmp/go2_mujoco_experiment.lock"
        if inherited.held_lock_fd is not None:
            fd = inherited.held_lock_fd
            actual, expected = os.fstat(fd), os.stat(lock_path)
            if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino):
                raise RuntimeError("inherited lock descriptor mismatch")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return _main()
        with open(lock_path, "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return _main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(
            json.dumps({"pass": False, "reason": type(exc).__name__ + ": " + str(exc)})
        )
        return 2
    finally:
        signal.signal(signal.SIGTERM, previous_signal)


if __name__ == "__main__":
    raise SystemExit(main())
