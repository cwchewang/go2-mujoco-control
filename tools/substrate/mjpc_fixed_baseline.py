"""Fixed-only 3 s MJPC baseline. Prepare/preflight never launch MJPC or integrate."""

from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from . import fd_duplicate_diagnostic as build
from .aligned_anchor import load_anchor, validate_canonical_model
from .aligned_episode import replay_aligned_rows, run_aligned_episode
from .contracts import PositionTargetControllerAdapter
from .episode import MujocoPlant
from .guards import zero_step_guard, wall_deadline
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_manifest,
    write_new,
)
from .native_mjpc import NativeMJPCController
from .readiness import validate_authorization, validate_review
from tools.research.preflight import DEFAULT_PROCESS_NAMES, find_processes

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "_runs"
FIXED = Path("/tmp/go2-mjpc-fd-diagnostic/go2_mjpc_controller_fd_fixed")
BINARY_SHA = "3644c6160dae354319c94840bdd07ca12166500a2b133f97b78421f8db587b08"
PROTOCOL = ROOT / "tools/substrate/protocols/mjpc_fixed_baseline_3s_v1.json"
RUNTIME = (
    "tools/substrate/mjpc_fixed_baseline.py",
    "tools/substrate/aligned_episode.py",
    "tools/substrate/aligned_anchor.py",
    "tools/substrate/native_mjpc.py",
    "tools/substrate/native_transport.py",
    "tools/substrate/contracts.py",
    "tools/substrate/episode.py",
    "tools/substrate/evaluator.py",
    "tools/substrate/clock.py",
    "tools/substrate/guards.py",
    "tools/substrate/integrity.py",
    "tools/substrate/build_identity.py",
    "tools/substrate/mjpc_diagnostic.py",
    "tools/substrate/specs.py",
    "tools/substrate/readiness.py",
    "tools/research/preflight.py",
    "tools/substrate/protocols/aligned_flat_anchor_v1.json",
    "tools/substrate/protocols/mjpc_fixed_baseline_3s_v1.json",
)


def git(*a):
    return subprocess.check_output(["git", *a], cwd=ROOT, text=True).strip()


def identity():
    branch = git("branch", "--show-current")
    if branch != "research/mjpc-fd-duplicate-fix-20261003" or git(
        "status", "--porcelain"
    ):
        raise ValueError("requires clean named research branch")
    return {"branch": branch, "head": git("rev-parse", "HEAD")}


def design():
    return {
        "repeats": 2,
        "workers": 4,
        "horizon_s": 3.0,
        "canonical_steps": 1500,
        "replans": 150,
        "private_reservation_per_replan": 4096,
        "private_upper_bound_per_repeat": 614400,
        "private_upper_bound_total": 1228800,
        "binary_sha256": BINARY_SHA,
        "anchor": "aligned-flat-forward-integration-v1",
        "zero_command_ticks": 50,
        "ramp_ticks": 100,
        "failure_policy": "stop pair on first safety/execution/evidence/budget failure; no retry",
        "pass": "both fresh-process episodes reach 1500 ticks with canonical classification HORIZON_REACHED",
        "capability_claim": "none",
    }


def runtime_identity():
    return {p: digest(ROOT / p) for p in RUNTIME}


def fresh(path):
    p = Path(path).expanduser().resolve()
    if p.parent != RUNS.resolve(strict=True) or p.exists():
        raise ValueError("output must be a fresh direct child of _runs")
    return p


def prepare(output, binary=FIXED):
    with experiment_lock(), zero_step_guard():
        ident = identity()
        if strict_json(PROTOCOL.read_text()) != design():
            raise ValueError("protocol drift")
        bi = build.build_identity(binary, "fixed")
        if bi["binary_sha256"] != BINARY_SHA or bi["workers"] != 4:
            raise ValueError("fixed binary identity/workers mismatch")
        out = fresh(output)
        packet = {
            "schema": 1,
            "kind": "mjpc-fixed-baseline-3s-v1",
            **ident,
            "design": design(),
            "runtime": runtime_identity(),
            "protocol_sha256": digest(PROTOCOL),
            "anchor_sha256": digest(
                ROOT / "tools/substrate/protocols/aligned_flat_anchor_v1.json"
            ),
            "build": bi,
            "binary": {"name": "go2_mjpc_controller_fd_fixed", "sha256": BINARY_SHA},
        }
        with EvidenceRun(
            out, {"operation": "mjpc_fixed_baseline_prepare", **ident}
        ) as run:
            target = out / packet["binary"]["name"]
            shutil.copy2(binary, target)
            if digest(target) != BINARY_SHA:
                raise ValueError("copied binary digest mismatch")
            write_new(out / "packet.json", packet)
            run.result.update(
                status="PREPARED_NOT_RUN",
                scope="fixed_baseline_prepare",
                canonical_physics_steps=0,
                native_processes_started=0,
                scientific_attempts=0,
            )
        verify_manifest(out)
        return {
            "status": "PREPARED_NOT_RUN",
            "packet": str(out / "packet.json"),
            "packet_sha256": digest(out / "packet.json"),
            **ident,
        }


def validate(packet_path, output):
    out = fresh(output)
    pp = Path(packet_path).resolve(strict=True)
    if pp.name != "packet.json" or pp.parent.parent != RUNS.resolve(strict=True):
        raise ValueError("packet must be in direct-child _runs bundle")
    manifest = verify_manifest(pp.parent)
    packet = strict_json(pp.read_text())
    ident = identity()
    if manifest.get("status") != "PREPARED_NOT_RUN" or any(
        packet.get(k) != ident[k] for k in ("branch", "head")
    ):
        raise ValueError("stale preparation")
    if (
        packet.get("kind") != "mjpc-fixed-baseline-3s-v1"
        or packet.get("design") != design()
    ):
        raise ValueError("design mismatch")
    if (
        packet.get("runtime") != runtime_identity()
        or packet.get("protocol_sha256") != digest(PROTOCOL)
        or packet.get("anchor_sha256")
        != digest(ROOT / "tools/substrate/protocols/aligned_flat_anchor_v1.json")
    ):
        raise ValueError("runtime/protocol/anchor drift")
    binary = pp.parent / packet["binary"]["name"]
    source_binary = Path(packet["build"]["path"]).resolve(strict=True)
    bi = build.build_identity(source_binary, "fixed")
    if (
        bi != packet.get("build")
        or digest(binary) != BINARY_SHA
        or digest(source_binary) != BINARY_SHA
        or bi["workers"] != 4
    ):
        raise ValueError("binary/workers mismatch")
    anchor = load_anchor()
    task = replace(
        anchor["task"],
        task_id="mjpc-fixed-baseline-3s-v1",
        horizon_ticks=1500,
        measurement_start_tick=150,
    )
    timing = anchor["controllers"]["mjpc"]["timing"]
    plant = MujocoPlant(ROOT / anchor["scenario"].scene)
    validate_canonical_model(anchor, plant.model)
    if (
        plant.steps != 0
        or float(plant.data.time) != 0.0
        or plant.model.opt.timestep != timing.physics_period_s
    ):
        raise ValueError("zero-step plant/timing check")
    if task.command_at(0).tolist() != [0.0, 0.0, 0.0] or task.command_at(
        150
    ).tolist() != [1.0, 0.0, 0.0]:
        raise ValueError("task command mismatch")
    live = find_processes(DEFAULT_PROCESS_NAMES + ("go2_mjpc_controller_fd_fixed",))
    if live:
        raise ValueError("active native/Go2 process blocks preflight")
    return (
        packet,
        source_binary,
        {
            "status": "PRECHECK_PASS",
            "branch": ident["branch"],
            "head": ident["head"],
            "packet_sha256": digest(pp),
            "prepared_manifest_sha256": digest(pp.parent / "manifest.json"),
            "output": str(out),
            "fixed_binary_sha256": digest(binary),
            "workers": 4,
            "canonical_physics_steps": 0,
            "native_processes_started": 0,
            "optimizer_calls": 0,
            "experiment_lock": "held",
        },
    )


def no_launch(packet_path, output):
    with experiment_lock(), zero_step_guard():
        packet, binary, report = validate(packet_path, output)
        out = Path(report["output"])
        with EvidenceRun(
            out, {"operation": "mjpc_fixed_baseline_preflight", "head": report["head"]}
        ) as run:
            write_new(out / "preflight.json", report)
            run.result.update(
                status="PRECHECK_PASS_NO_LAUNCH",
                canonical_physics_steps=0,
                native_processes_started=0,
                scientific_attempts=0,
            )
        verify_manifest(out)
        return {
            **report,
            "status": "PRECHECK_PASS_NO_LAUNCH",
            "manifest_sha256": digest(out / "manifest.json"),
        }


def _run_one(packet_path, output):
    """Capture primitive used only after a separate reviewed START gate."""
    packet, binary, _ = validate(
        packet_path, Path(output).parent / (Path(output).name + "_preflight")
    )
    anchor = load_anchor()
    task = replace(
        anchor["task"],
        task_id="mjpc-fixed-baseline-3s-v1",
        horizon_ticks=1500,
        measurement_start_tick=150,
    )
    timing = anchor["controllers"]["mjpc"]["timing"]
    info = anchor["controllers"]["mjpc"]["information"]
    plant = MujocoPlant(ROOT / anchor["scenario"].scene)
    native = NativeMJPCController(
        binary,
        timing,
        stderr_log_path=Path(output) / "native.stderr.log",
        diagnostic=(
            "original",
            ROOT / anchor["scenario"].scene,
            Path(output) / "predictions.jsonl",
        ),
    )
    controller = PositionTargetControllerAdapter(
        native, native.actuator_spec, native.joint_names
    )
    consumed = False

    def consume():
        nonlocal consumed
        if consumed:
            raise ValueError("attempt already consumed")
        write_new(
            Path(output) / "attempt.json",
            {
                "attempt": 1,
                "head": packet["head"],
                "packet_sha256": digest(Path(packet_path)),
                "first_sample_boundary": "first post-reset action before canonical step 1",
            },
        )
        consumed = True

    try:
        with (Path(output) / "raw.jsonl").open("x") as stream:

            def emit(row):
                stream.write(json.dumps(row, allow_nan=False, sort_keys=True) + chr(10))
                stream.flush()

            with wall_deadline(300):
                outcome = run_aligned_episode(
                    plant, controller, task, info, timing, emit, consume
                )
            stream.flush()
            os.fsync(stream.fileno())
        diagnostics = native.diagnostics()
        (Path(output) / "native-diagnostics.json").write_text(
            json.dumps(diagnostics, sort_keys=True) + chr(10)
        )
    finally:
        native.close()
    diag = diagnostics.get("last_step", {}).get("diagnostic")
    if (
        not isinstance(diag, dict)
        or diag.get("private_step_upper_bound_reserved", 614401) > 614400
    ):
        raise ValueError("private-step reservation/accounting bound failed")
    upper = diag.get("fd_step_upper_bound_count", 0) + diag.get(
        "rollout_mj_step_count", 0
    )
    if upper > diag.get("private_step_upper_bound_reserved", 0):
        raise ValueError("private-step upper bound exceeded reservation")
    rows = [
        strict_json(line)
        for line in (Path(output) / "raw.jsonl").read_text().splitlines()
    ]
    evaluation = replay_aligned_rows(rows, task, timing.physics_period_s)
    if outcome["terminal_reason"] == "horizon" and diag.get("policy_id") != 150:
        raise ValueError("horizon reached without all 150 replans")
    return {
        "outcome": outcome,
        "canonical_evaluation": evaluation,
        "canonical_physics_steps": plant.steps,
        "attempt_consumed": consumed,
        "private_upper_bound": upper,
        "private_reserved": diag["private_step_upper_bound_reserved"],
        "optimizer_calls": diag.get("policy_id"),
        "classification": "HORIZON_REACHED"
        if outcome["terminal_reason"] == "horizon"
        else "SAFETY_STOP",
    }


def validate_start(packet_path, review_path, authorization_path):
    pp = Path(packet_path).resolve(strict=True)
    packet = strict_json(pp.read_text())
    prepared = {
        "head": packet["head"],
        "protocol_sha256": packet["protocol_sha256"],
        "prepared_manifest_sha256": digest(pp.parent / "manifest.json"),
        "max_attempts": 2,
    }
    validate_review(strict_json(Path(review_path).read_text()), prepared["head"])
    validate_authorization(strict_json(Path(authorization_path).read_text()), prepared)
    return pp


def run_pair(packet_path, output, review_path, authorization_path):
    pp = validate_start(packet_path, review_path, authorization_path)
    base = fresh(output)
    with experiment_lock():
        validate(pp, base)
        results = []
        for repeat in (1, 2):
            target = Path(str(base) + f"_repeat{repeat}")
            if target.exists():
                raise ValueError("repeat output already exists; no retry")
            command = [
                sys.executable,
                "-B",
                "-m",
                "tools.substrate.mjpc_fixed_baseline",
                "--worker",
                "--packet",
                str(pp),
                "--output",
                str(target),
                "--review",
                str(review_path),
                "--authorization",
                str(authorization_path),
            ]
            completed = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, timeout=330
            )
            if completed.returncode:
                results.append(
                    {
                        "repeat": repeat,
                        "status": "EXECUTION_STOP",
                        "stderr": completed.stderr[-4000:],
                    }
                )
                return {"status": "STOPPED_NO_RETRY", "results": results}
            result = strict_json(completed.stdout)
            results.append({"repeat": repeat, **result})
            if (
                result.get("classification") != "HORIZON_REACHED"
                or result.get("canonical_physics_steps") != 1500
            ):
                return {"status": "STOPPED_NO_RETRY", "results": results}
    return {"status": "TWO_REPEAT_HORIZON_REACHED", "results": results}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare", action="store_true")
    g.add_argument("--preflight", action="store_true")
    g.add_argument("--capture", action="store_true")
    g.add_argument("--worker", action="store_true")
    p.add_argument("--packet", type=Path)
    p.add_argument("--binary", type=Path, default=FIXED)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--review", type=Path)
    p.add_argument("--authorization", type=Path)
    a = p.parse_args(argv)
    os.chdir(ROOT)
    if a.prepare:
        if a.packet:
            p.error("--prepare does not accept --packet")
        result = prepare(a.output, a.binary)
    elif a.preflight:
        if not a.packet:
            p.error("--preflight requires --packet")
        result = no_launch(a.packet, a.output)
    elif a.worker:
        if not a.packet or not a.review or not a.authorization:
            p.error("--worker requires --packet, --review, and --authorization")
        validate_start(a.packet, a.review, a.authorization)
        out = fresh(a.output)
        with EvidenceRun(
            out, {"operation": "mjpc_fixed_baseline_repeat_worker"}
        ) as run:
            result = _run_one(a.packet, out)
            write_new(out / "outcome.json", result)
            run.result.update(
                status=result["classification"],
                canonical_physics_steps=result["canonical_physics_steps"],
                private_upper_bound=result["private_upper_bound"],
                private_reserved=result["private_reserved"],
                optimizer_calls=result["optimizer_calls"],
                scientific_attempts=int(result["attempt_consumed"]),
            )
        verify_manifest(out)
        print(json.dumps(result, sort_keys=True))
        return
    else:
        if not a.packet or not a.review or not a.authorization:
            p.error("--capture requires --packet, --review, and --authorization")
        result = run_pair(a.packet, a.output, a.review, a.authorization)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
