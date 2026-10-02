"""Fixed-only 3 s MJPC baseline. Preparation is offline; preflight launches one ready-only native worker."""

from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
import stat
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
    LOCK_PATH,
    digest,
    experiment_lock,
    strict_json,
    verify_manifest,
    write_new,
)
from .native_mjpc import NativeMJPCController
from . import native_runtime
from .readiness import validate_authorization, validate_review
from tools.research.preflight import DEFAULT_PROCESS_NAMES, find_processes

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "_runs"
BINARY_SHA = "3644c6160dae354319c94840bdd07ca12166500a2b133f97b78421f8db587b08"
PROTOCOL = ROOT / "tools/substrate/protocols/mjpc_fixed_baseline_3s_v1.json"
RUNTIME = (
    "tools/substrate/mjpc_fixed_baseline.py",
    "tools/substrate/run_mjpc_fixed_baseline",
    "tools/substrate/native_runtime.py",
    "tools/substrate/model.py",
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


def prepare(output, binary):
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
            "binary": {
                "name": "runtime/go2_mjpc_controller_fd_fixed",
                "sha256": BINARY_SHA,
            },
        }
        with EvidenceRun(
            out, {"operation": "mjpc_fixed_baseline_prepare", **ident}
        ) as run:
            native_runtime.package(binary, out / "runtime", ROOT, bi)
            packet["runtime_identity"] = {
                "name": "runtime/" + native_runtime.SIDECAR,
                "sha256": digest(out / "runtime" / native_runtime.SIDECAR),
            }
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
    sidecar = pp.parent / packet["runtime_identity"]["name"]
    if digest(sidecar) != packet["runtime_identity"]["sha256"]:
        raise ValueError("runtime sidecar differs from packet")
    runtime = native_runtime.verify(binary, sidecar)
    if runtime["binary_sha256"] != BINARY_SHA or runtime["workers"] != 4:
        raise ValueError("binary/workers mismatch")
    anchor = load_anchor()
    task = replace(
        anchor["task"],
        task_id="mjpc-fixed-baseline-3s-v1",
        horizon_ticks=1500,
        measurement_start_tick=150,
    )
    timing = anchor["controllers"]["mjpc"]["timing"]
    plant = MujocoPlant(sidecar.parent / runtime["canonical_xml"])
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
        binary,
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


def _run_one(packet_path, output, *, construction_only=False):
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
    sidecar = Path(packet_path).resolve().parent / packet["runtime_identity"]["name"]
    runtime = native_runtime.verify(binary, sidecar)
    canonical = sidecar.parent / runtime["canonical_xml"]
    plant = MujocoPlant(canonical)
    validate_canonical_model(anchor, plant.model)
    launches = []

    def counted_launch(argv, **kwargs):
        process = subprocess.Popen(argv, **kwargs)
        launches.append({"pid": process.pid, "argv": list(argv)})
        return process

    native = None
    try:
        native = NativeMJPCController(
            binary,
            timing,
            popen=counted_launch,
            stderr_log_path=Path(output) / "native.stderr.log",
            diagnostic=("original", canonical, Path(output) / "predictions.jsonl"),
            runtime_identity=sidecar,
            fd_trace_path=Path(output) / "fd-trace.jsonl",
        )
        controller = PositionTargetControllerAdapter(
            native, native.actuator_spec, native.joint_names
        )
        mapped = native_runtime.loaded_libraries(native.process.pid, sidecar)
        write_new(Path(output) / "controller-ready.json", native.ready)
        write_new(Path(output) / "loaded-libraries.json", mapped)
        write_new(
            Path(output) / "construction.json",
            {
                "phase": "controller_ready_before_episode",
                "runtime_sidecar_sha256": digest(sidecar),
                "runtime_binary": str(binary),
                "canonical_xml": str(canonical),
                "native_launches": launches,
                "worker_command": Path("/proc/self/cmdline")
                .read_bytes()
                .decode()
                .split(chr(0))[:-1],
                "worker_pid": os.getpid(),
                "canonical_physics_steps": plant.steps,
                "optimizer_calls": 0,
            },
        )
        if construction_only:
            if (
                plant.steps != 0
                or float(plant.data.time) != 0
                or native.diagnostics().get("last_step") is not None
            ):
                raise ValueError("construction-only worker advanced episode")
            if (Path(output) / "predictions.jsonl").stat().st_size or (
                Path(output) / "fd-trace.jsonl"
            ).exists():
                raise ValueError("construction-only worker emitted optimizer evidence")
            native.close()
            transport = native.diagnostics()["transport"]
            if transport["stderr_bytes"]:
                raise ValueError("native startup emitted warning/diagnostic stderr")
            return {
                "classification": "CONSTRUCTION_PRECHECK_PASS",
                "phase": "controller_ready_before_episode",
                "native_processes_started": len(launches),
                "python_workers_started": 1,
                "canonical_physics_steps": 0,
                "optimizer_calls": 0,
                "scientific_attempts": 0,
                "attempt_consumed": False,
                "runtime_sidecar_sha256": digest(sidecar),
                "workers": native.ready["worker_count"],
            }
    except BaseException:
        if native is not None:
            native.close()
        raise
    finally:
        write_new(
            Path(output) / "construction-accounting.json",
            {
                "native_processes_started": len(launches),
                "canonical_physics_steps_before_episode": plant.steps,
                "optimizer_calls_before_episode": 0,
                "construction_only": construction_only,
            },
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


def consume_construction_capability(packet_path, output, lock_fd, token_fd):
    if Path(f"/proc/self/fd/{lock_fd}").resolve() != LOCK_PATH.resolve():
        raise ValueError("construction worker lacks inherited lock")
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not stat.S_ISFIFO(os.fstat(token_fd).st_mode):
        raise ValueError("construction capability must be an inherited pipe")
    with os.fdopen(token_fd, "r") as stream:
        value = strict_json(stream.read())
    expected = {
        "mode": "construction_only",
        "packet_sha256": digest(packet_path),
        "output": str(Path(output).resolve()),
        "parent_pid": os.getppid(),
    }
    if value != expected:
        raise ValueError("construction capability binding mismatch")


def construction_preflight(packet_path, output):
    pp = Path(packet_path).resolve(strict=True)
    with experiment_lock() as lock:
        _, _, report = validate(pp, output)
        out = Path(report["output"])
        read_fd, write_fd = os.pipe()
        command = [
            sys.executable,
            "-B",
            "-m",
            "tools.substrate.mjpc_fixed_baseline",
            "--worker",
            "--construction-only",
            "--packet",
            str(pp),
            "--output",
            str(out),
            "--worker-lock-fd",
            str(lock.fileno()),
            "--worker-token-fd",
            str(read_fd),
        ]
        try:
            child = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                pass_fds=(lock.fileno(), read_fd),
            )
            os.close(read_fd)
            read_fd = -1
            capability = {
                "mode": "construction_only",
                "packet_sha256": digest(pp),
                "output": str(out),
                "parent_pid": os.getpid(),
            }
            os.write(write_fd, json.dumps(capability).encode())
            os.close(write_fd)
            write_fd = -1
            try:
                stdout, stderr = child.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate()
                raise TimeoutError("construction preflight worker timed out")
        finally:
            for fd in (read_fd, write_fd):
                if fd >= 0:
                    os.close(fd)
        if child.returncode:
            raise RuntimeError("construction worker failed: " + stderr[-8000:])
        result = strict_json(stdout)
        if result.get("classification") != "CONSTRUCTION_PRECHECK_PASS":
            raise ValueError("construction preflight did not reach episode boundary")
        verify_manifest(out)
        return {
            **report,
            **result,
            "status": "PRECHECK_PASS_CONSTRUCTION",
            "command": command,
            "manifest_sha256": digest(out / "manifest.json"),
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


def campaign_reservation_path(packet_path):
    return RUNS / f"mjpc_fixed_baseline_campaign_{digest(packet_path)}.json"


def reserve_campaign(packet_path, authorization_path, output_base):
    pp = Path(packet_path).resolve(strict=True)
    packet = strict_json(pp.read_text())
    tokens = [os.urandom(32).hex(), os.urandom(32).hex()]
    base = str(Path(output_base).resolve())
    record = {
        "schema": 1,
        "campaign_id": digest(pp),
        "packet_sha256": digest(pp),
        "prepared_manifest_sha256": digest(pp.parent / "manifest.json"),
        "head": packet["head"],
        "protocol_sha256": packet["protocol_sha256"],
        "authorization_sha256": digest(authorization_path),
        "max_attempts": 2,
        "output_base": base,
        "outputs": [base + "_repeat1", base + "_repeat2"],
        "worker_token_sha256": [
            hashlib.sha256(token.encode()).hexdigest() for token in tokens
        ],
        "status": "RESERVED_ONCE",
    }
    reservation = campaign_reservation_path(pp)
    encoded = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode()
    fd = os.open(reservation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(reservation.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        # Keep an exclusive partial reservation as a permanent fail-closed stop.
        raise
    return reservation, tokens


def consume_worker_capability(
    packet_path,
    output,
    reservation_path,
    attempt,
    lock_fd,
    token_fd,
    review_path,
    authorization_path,
):
    pp = validate_start(packet_path, review_path, authorization_path)
    os.fstat(lock_fd)
    if Path(f"/proc/self/fd/{lock_fd}").resolve() != LOCK_PATH.resolve():
        raise ValueError("worker did not inherit the experiment lock handle")
    # Re-flocking the inherited open-file description succeeds only for the pair's
    # held lock. A separately opened competing descriptor cannot pass this check.
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not stat.S_ISFIFO(os.fstat(token_fd).st_mode):
        raise ValueError("worker capability must arrive over an inherited pipe")
    token = os.read(token_fd, 128).decode()
    os.close(token_fd)
    reservation = Path(reservation_path).resolve(strict=True)
    if reservation != campaign_reservation_path(pp).resolve():
        raise ValueError("reservation is not the packet's unique campaign slot")
    record = strict_json(reservation.read_text())
    auth_sha = digest(authorization_path)
    expected = {
        "campaign_id": digest(pp),
        "packet_sha256": digest(pp),
        "prepared_manifest_sha256": digest(pp.parent / "manifest.json"),
        "head": strict_json(pp.read_text())["head"],
        "protocol_sha256": strict_json(pp.read_text())["protocol_sha256"],
        "authorization_sha256": auth_sha,
        "max_attempts": 2,
    }
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("campaign reservation binding mismatch")
    if attempt not in (1, 2) or Path(output).resolve() != Path(
        record["outputs"][attempt - 1]
    ):
        raise ValueError("worker output/attempt does not match reserved campaign")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if token_hash != record["worker_token_sha256"][attempt - 1]:
        raise ValueError("worker capability token mismatch")
    if attempt == 2:
        first = Path(record["outputs"][0])
        verify_manifest(first)
        prior = strict_json((first / "outcome.json").read_text())
        if (
            prior.get("classification") != "HORIZON_REACHED"
            or prior.get("canonical_physics_steps") != 1500
        ):
            raise ValueError("repeat 2 is blocked unless repeat 1 reached horizon")
    claim = reservation.with_name(reservation.stem + f"_attempt{attempt}.claim")
    claim_data = {
        "campaign_id": record["campaign_id"],
        "attempt": attempt,
        "output": str(Path(output).resolve()),
        "pid": os.getpid(),
    }
    fd = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(claim_data, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return pp


def run_pair(packet_path, output, review_path, authorization_path):
    pp = validate_start(packet_path, review_path, authorization_path)
    base = fresh(output)
    results = []
    with experiment_lock() as lock:
        validate(pp, base)
        reservation, tokens = reserve_campaign(pp, authorization_path, base)
        for attempt, token in enumerate(tokens, start=1):
            target = Path(str(base) + f"_repeat{attempt}")
            if target.exists():
                raise ValueError("reserved repeat output already exists; no retry")
            token_read_fd, token_write_fd = os.pipe()
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
                "--reservation",
                str(reservation),
                "--attempt",
                str(attempt),
                "--worker-lock-fd",
                str(lock.fileno()),
                "--worker-token-fd",
                str(token_read_fd),
            ]
            try:
                child = subprocess.Popen(
                    command,
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    pass_fds=(lock.fileno(), token_read_fd),
                )
                os.close(token_read_fd)
                token_read_fd = -1
                os.write(token_write_fd, token.encode())
                os.close(token_write_fd)
                token_write_fd = -1
                try:
                    stdout, stderr = child.communicate(timeout=330)
                except subprocess.TimeoutExpired:
                    child.kill()
                    stdout, stderr = child.communicate()
                    results.append(
                        {
                            "repeat": attempt,
                            "status": "EXECUTION_STOP",
                            "stderr": stderr[-4000:],
                        }
                    )
                    return {
                        "status": "STOPPED_NO_RETRY",
                        "reservation": str(reservation),
                        "results": results,
                    }
            finally:
                for fd in (token_read_fd, token_write_fd):
                    if fd >= 0:
                        os.close(fd)
            if child.returncode:
                results.append(
                    {
                        "repeat": attempt,
                        "status": "EXECUTION_STOP",
                        "stderr": stderr[-4000:],
                    }
                )
                return {
                    "status": "STOPPED_NO_RETRY",
                    "reservation": str(reservation),
                    "results": results,
                }
            result = strict_json(stdout)
            results.append({"repeat": attempt, **result})
            if (
                result.get("classification") != "HORIZON_REACHED"
                or result.get("canonical_physics_steps") != 1500
            ):
                return {
                    "status": "STOPPED_NO_RETRY",
                    "reservation": str(reservation),
                    "results": results,
                }
    return {
        "status": "TWO_REPEAT_HORIZON_REACHED",
        "reservation": str(reservation),
        "results": results,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare", action="store_true")
    g.add_argument("--preflight", action="store_true")
    g.add_argument("--capture", action="store_true")
    g.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--packet", type=Path)
    p.add_argument("--binary", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--review", type=Path)
    p.add_argument("--authorization", type=Path)
    p.add_argument("--reservation", type=Path)
    p.add_argument("--attempt", type=int)
    p.add_argument("--worker-lock-fd", type=int)
    p.add_argument("--worker-token-fd", type=int)
    p.add_argument("--construction-only", action="store_true", help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    os.chdir(ROOT)
    if a.prepare:
        if a.packet or a.binary is None:
            p.error(
                "--prepare requires an explicit audited build binary and no --packet"
            )
        result = prepare(a.output, a.binary)
    elif a.preflight:
        if not a.packet:
            p.error("--preflight requires --packet")
        result = construction_preflight(a.packet, a.output)
    elif a.worker:
        if not a.packet or a.worker_lock_fd is None or a.worker_token_fd is None:
            p.error(
                "direct worker requires the pair runner's inherited lock and one-use capability"
            )
        if a.construction_only:
            consume_construction_capability(
                a.packet, a.output, a.worker_lock_fd, a.worker_token_fd
            )
        else:
            if not all((a.review, a.authorization, a.reservation)) or a.attempt not in (
                1,
                2,
            ):
                p.error("formal worker requires its reserved campaign")
            consume_worker_capability(
                a.packet,
                a.output,
                a.reservation,
                a.attempt,
                a.worker_lock_fd,
                a.worker_token_fd,
                a.review,
                a.authorization,
            )
        out = fresh(a.output)
        with EvidenceRun(
            out,
            {
                "operation": "mjpc_fixed_baseline_repeat_worker",
                "attempt": a.attempt,
            },
        ) as run:
            if a.construction_only:
                with zero_step_guard():
                    result = _run_one(a.packet, out, construction_only=True)
            else:
                result = _run_one(a.packet, out)
            write_new(out / "outcome.json", result)
            run.result.update(
                status=result["classification"],
                canonical_physics_steps=result["canonical_physics_steps"],
                private_upper_bound=result.get("private_upper_bound", 0),
                private_reserved=result.get("private_reserved", 0),
                optimizer_calls=result["optimizer_calls"],
                native_processes_started=result.get("native_processes_started", 1),
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
