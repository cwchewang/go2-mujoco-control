"""Prepare only by default. Capture requires a separate explicit start record."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

from .admit import ROOT, source_manifest
from .analyze_capture import analyze
from .environment import verify_environment
from .episode import MujocoPlant, episode, safety
from .integrity import (
    EvidenceRun,
    LOCK_PATH,
    digest,
    strict_json,
    verify_bundle,
    write_new,
    run_logged,
)
from .model import dependency_manifest, physical_fingerprint
from .rl import FrozenPolicy
from .readiness import (
    validate_review as validate_review,
    validate_authorization as validate_authorization,
)
from .guards import zero_step_guard as zero_step_guard, wall_deadline as wall_deadline
from .task import DEFAULT_TASK, load_task
from .qualification import validate as validate_qualification, validate_reference

TRANSPORT = "inprocess"
PROTOCOL = ROOT / "tools/substrate/protocols/rl_flat_v1.json"
CHECKPOINT = ROOT / ".substrate/rl/policy.pt"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def current_identity(task=None):
    head, branch = git("rev-parse", "HEAD"), git("branch", "--show-current")
    task = task or load_task(DEFAULT_TASK)
    if branch != task["configuration"]["branch"] or git("status", "--porcelain"):
        raise ValueError("launch preparation requires the clean reserved branch")
    return head, source_manifest()


def preflight(lock, head, review, report, fresh_run, task, qualification):
    validate_review(review, head)
    argv = [
        sys.executable,
        str(ROOT / "tools/research/preflight.py"),
        "--repo-root",
        str(ROOT),
        "--experiment-id",
        "rl-flat-compatibility-v1",
        "--expected-branch",
        task["configuration"]["branch"],
        "--expected-head",
        head,
        "--runner",
        str(Path(__file__)),
        "--run-dir",
        str(fresh_run),
        "--transport",
        "inprocess",
        "--held-lock-fd",
        str(lock.fileno()),
        "--diff-base",
        task["configuration"]["diff_base"],
        "--requires-sol-review",
        "--approved-head",
        head,
        "--qualification",
        qualification["path"],
        "--output",
        str(report),
    ]
    # More than the one inner test's 120s limit; TERM is handled by preflight
    # so its independent test process group is reaped before the wrapper exits.
    run_logged(
        argv,
        report.parent,
        "preflight",
        timeout=180,
        cwd=ROOT,
        pass_fds=(lock.fileno(),),
        termination_grace=2,
    )
    report_value = strict_json(report.read_text())
    if report_value.get("pass") is not True:
        raise ValueError("preflight report not passing")


def setup_runtime():
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(0)


def prepare(directory, review_path, qualification_path, task_path=DEFAULT_TASK):
    with LOCK_PATH.open("a") as lock, zero_step_guard():
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with EvidenceRun(
            directory, {"argv": sys.argv, "operation": "prepare_zero_step"}
        ) as run:
            task = load_task(task_path)
            protocol_path = ROOT / task["configuration"]["protocol"]
            head, sources = current_identity(task)
            qualification = validate_qualification(qualification_path)
            review = strict_json(review_path.read_text())
            preflight(
                lock,
                head,
                review,
                run.path / "preflight.json",
                run.path / "future_capture",
                task,
                qualification,
            )
            runtime = verify_environment()
            setup_runtime()
            protocol = strict_json(protocol_path.read_text())
            write_new(run.path / "protocol.json", protocol)
            write_new(run.path / "review.json", review)
            closure = dependency_manifest(ROOT / protocol["scene"], ROOT)
            for name, expected in closure["files"].items():
                target = run.path / "inputs" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
                if digest(target) != expected:
                    raise ValueError("model changed while snapshotting")
            plant = MujocoPlant(run.path / "inputs" / protocol["scene"])
            if plant.model.opt.timestep != protocol["physics_period_s"]:
                raise ValueError("physics timestep differs from protocol")
            expected = strict_json(
                (ROOT / "tools/substrate/sources.lock.json").read_text()
            )["rl"]["sha256"]
            policy = FrozenPolicy(CHECKPOINT, expected)
            initial = plant.snapshot(0)
            if safety(initial, protocol):
                raise ValueError("initial state violates frozen safety conditions")
            action = policy.act(plant.observe(), [0.0, 0.0, 0.0]).resolve(
                plant.observe(), plant.lower, plant.upper, plant.names
            )
            policy.reset()
            second = policy.act(plant.observe(), [0.0, 0.0, 0.0]).resolve(
                plant.observe(), plant.lower, plant.upper, plant.names
            )
            if any(not (action[k] == second[k]).all() for k in action):
                raise ValueError("initial action reset mismatch")
            if plant.data.time != 0 or plant.steps != 0 or plant.snapshot(0) != initial:
                raise ValueError("prepare advanced or changed plant")
            write_new(run.path / "initial-state.json", initial)
            write_new(
                run.path / "initial-action.json",
                {k: v.tolist() for k, v in action.items()},
            )
            if (head, sources) != current_identity(
                task
            ) or closure != dependency_manifest(ROOT / protocol["scene"], ROOT):
                raise ValueError("source changed during prepare")
            validate_reference(qualification)
            if task != load_task(task_path):
                raise ValueError("task changed during prepare")
            readiness = (
                "VERIFIED_ZERO_STEP_CAMPAIGN_CLOSED"
                if (ROOT / "_runs/substrate_attempts" / protocol["id"]).exists()
                else "READY_AWAITING_START"
            )
            run.result.update(
                {
                    "status": "ENGINEERING_ADMITTED",
                    "readiness": readiness,
                    "head": head,
                    "source_files": sources,
                    "runtime": runtime,
                    "protocol_sha256": digest(protocol_path),
                    "task": task,
                    "qualification_reference": qualification,
                    "checkpoint_sha256": expected,
                    "model": closure,
                    "physical_sha256": physical_fingerprint(plant.model),
                    "review": review,
                    "physics_steps": 0,
                    "scientific_attempts": 0,
                    "layout": {
                        "names": plant.names,
                        "qadr": plant.qadr,
                        "vadr": plant.vadr,
                    },
                    "lower": plant.lower.tolist(),
                    "upper": plant.upper.tolist(),
                }
            )
    verify_bundle(directory)
    return {
        "readiness": readiness,
        "head": head,
        "physics_steps": 0,
        "output": str(directory),
    }


def capture(prepared_dir, authorization_path, output):
    """Never invoked by prepare, qualification or tests with a real plant."""
    with LOCK_PATH.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prepared = verify_bundle(prepared_dir)
        if not isinstance(prepared.get("task"), dict):
            raise ValueError("new capture requires task-bound preparation")
        task = load_task(ROOT / prepared["task"]["path"])
        if task != prepared["task"]:
            raise ValueError("task changed since preparation")
        protocol_path = ROOT / task["configuration"]["protocol"]
        head, sources = current_identity(task)
        if (
            prepared.get("readiness") != "READY_AWAITING_START"
            or prepared["head"] != head
            or prepared["source_files"] != sources
            or prepared["protocol_sha256"] != digest(protocol_path)
        ):
            raise ValueError("stale preparation")
        prepared["prepared_manifest_sha256"] = digest(prepared_dir / "manifest.json")
        authorization = strict_json(authorization_path.read_text())
        validate_authorization(authorization, prepared)
        validate_review(prepared["review"], head)
        qualification = validate_reference(prepared.get("qualification_reference"))
        verify_environment()
        setup_runtime()
        protocol = strict_json(protocol_path.read_text())
        if (
            digest(CHECKPOINT) != prepared["checkpoint_sha256"]
            or dependency_manifest(ROOT / protocol["scene"], ROOT) != prepared["model"]
        ):
            raise ValueError("changed runtime inputs")
        # One immutable campaign claim per protocol, across output paths and
        # code revisions. No rerun/replacement campaign can hide a failed arm.
        ledger = ROOT / "_runs/substrate_attempts" / protocol["id"]
        if ledger.exists():
            raise ValueError(
                "campaign already claimed; inspect preserved evidence, no autonomous retry"
            )
        with EvidenceRun(
            output, {"argv": sys.argv, "operation": "formal_capture"}
        ) as run:
            run.result.update(
                {
                    "scope": "formal_exploratory_capture",
                    "capability_status": "INCOMPLETE",
                    "status": "FAILED",
                }
            )
            preflight(
                lock,
                head,
                prepared["review"],
                run.path / "preflight.json",
                ledger,
                task,
                qualification,
            )
            if (head, sources) != current_identity(task):
                raise ValueError("source changed before launch")
            write_new(run.path / "authorization.json", authorization)
            write_new(run.path / "protocol.json", protocol)
            write_new(
                run.path / "preparation-reference.json",
                {
                    "path": str(prepared_dir),
                    "manifest_sha256": prepared["prepared_manifest_sha256"],
                },
            )
            ledger.mkdir(parents=True, exist_ok=False)
            claim = {
                "head": head,
                "output": str(run.path.resolve()),
                "protocol_sha256": prepared["protocol_sha256"],
            }
            write_new(ledger / "campaign.json", claim)
            write_new(run.path / "campaign-claim.json", claim)
            attempts = [
                {"index": i, "status": "NOT_RUN"}
                for i in range(1, protocol["max_attempts"] + 1)
            ]
            run.result.update({"head": head, "attempts": attempts, "live_runs": 0})
            try:
                for item in attempts:
                    number = item["index"]
                    plant = MujocoPlant(prepared_dir / "inputs" / protocol["scene"])
                    if physical_fingerprint(plant.model) != prepared["physical_sha256"]:
                        raise ValueError("snapshot physics differs")
                    policy = FrozenPolicy(CHECKPOINT, prepared["checkpoint_sha256"])
                    raw = run.path / ("attempt_%02d.jsonl" % number)
                    started = time.monotonic()
                    usage = resource.getrusage(resource.RUSAGE_SELF)
                    item["status"] = "BOOTING"

                    def consume():
                        claim = {
                            "index": number,
                            "head": head,
                            "raw": str(raw.resolve()),
                            "boundary": "first_post_handoff_state_control_sample",
                        }
                        write_new(ledger / ("attempt_%02d.json" % number), claim)
                        write_new(
                            run.path / ("attempt_%02d_claim.json" % number), claim
                        )
                        item["status"] = "CAPTURING"
                        run.result["live_runs"] += 1

                    with raw.open("x") as stream:

                        def emit(row):
                            stream.write(
                                json.dumps(row, allow_nan=False, separators=(",", ":"))
                                + "\n"
                            )
                            stream.flush()

                        try:
                            with wall_deadline(protocol["wall_timeout_s"]):
                                episode(plant, policy, protocol, emit, consume)
                        finally:
                            stream.flush()
                            os.fsync(stream.fileno())
                    rows = [strict_json(line) for line in raw.read_text().splitlines()]
                    reference_trace = (
                        attempts[0].get("analysis", {}).get("trace_sha256")
                        if number > 1
                        else None
                    )
                    result = analyze(
                        rows,
                        protocol,
                        plant.lower,
                        plant.upper,
                        prepared["layout"],
                        reference_trace,
                    )
                    after = resource.getrusage(resource.RUSAGE_SELF)
                    result["resources"] = {
                        "elapsed_s": time.monotonic() - started,
                        "cpu_user_s": after.ru_utime - usage.ru_utime,
                        "cpu_system_s": after.ru_stime - usage.ru_stime,
                        "process_peak_rss_kib": after.ru_maxrss,
                    }
                    write_new(
                        run.path / ("attempt_%02d_analysis.json" % number), result
                    )
                    item.update({"status": result["verdict"], "analysis": result})
                    if (head, sources) != current_identity(task):
                        raise ValueError("source_changed")
                    if result["verdict"] != "PASS":
                        break
                run.result["capability_status"] = (
                    "PASS" if all(v["status"] == "PASS" for v in attempts) else "FAIL"
                )
                # Explicit scientific status; never masquerade as engineering admission.
                run.result["status"] = "CAPTURE_COMPLETE"
            except BaseException as exc:
                if "item" in locals() and item["status"] in ("BOOTING", "CAPTURING"):
                    item["status"] = "ERROR"
                    item["reason"] = type(exc).__name__ + ": " + str(exc)
                raise
    return {
        "status": run.result["status"],
        "capability_status": run.result["capability_status"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--review", type=Path, required=True)
    prep.add_argument("--qualification", type=Path, required=True)
    prep.add_argument("--task", type=Path, default=DEFAULT_TASK)
    live = sub.add_parser("capture")
    live.add_argument("--prepared", type=Path, required=True)
    live.add_argument("--authorization", type=Path, required=True)
    live.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (
            prepare(args.output, args.review, args.qualification, args.task)
            if args.operation == "prepare"
            else capture(args.prepared, args.authorization, args.output)
        )
        print(json.dumps(result))
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(
            json.dumps(
                {"status": "FAILED", "reason": type(exc).__name__ + ": " + str(exc)}
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
