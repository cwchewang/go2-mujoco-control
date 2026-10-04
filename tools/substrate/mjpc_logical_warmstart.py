"""Four fresh closed-loop attempts with new logical warmstart ownership."""

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from . import native_runtime
from .aligned_anchor import load_anchor, validate_canonical_model
from .aligned_episode import replay_aligned_rows, run_aligned_episode
from .build_identity import inputs as native_inputs
from .contracts import PositionTargetControllerAdapter
from .episode import MujocoPlant
from .guards import wall_deadline, zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    run_logged,
    strict_json,
    verify_manifest,
    write_new,
)
from .mjpc_dedup_observation import inputs
from .mjpc_floor_registration_diagnostic import (
    StrictWarningController,
    assert_only_floor_z_changed,
)
from .native_mjpc import NativeMJPCController
from .readiness import validate_authorization, validate_review
from .mjpc_short_sequence_launcher import live_controller_processes

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "research/mjpc-logical-warmstart-closed-loop-20261004"
PROTOCOL = (
    ROOT / "tools/substrate/protocols/mjpc_logical_warmstart_closed_loop_3s_v1.json"
)
BUILD = ROOT / "_runs/mjpc_logical_warmstart_native_build_20261004_v3"
RAW = ROOT / "_runs/mjpc_logical_warmstart_closed_loop_20261004"


def identity():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

    if git("branch", "--show-current") != BRANCH or git("status", "--porcelain"):
        raise ValueError("exact clean logical warmstart branch required")
    return {"head": git("rev-parse", "HEAD"), "branch": BRANCH}


def protocol():
    value = strict_json(PROTOCOL.read_text())
    if (
        value["id"] != "mjpc-logical-warmstart-closed-loop-3s-v1"
        or value["branch"] != BRANCH
        or value["order"] != ["logical1", "logical2", "worker1", "worker2"]
        or value["max_attempts"] != 4
        or value["horizon_ticks"] != 1500
        or value["max_canonical_steps"] != 6000
        or value["max_optimizer_calls"] != 600
        or value["max_private_upper"] != 4 * 150 * (35 * 49 + 37 + 700)
        or value["max_private_reserved"] != 4 * 150 * 4096
        or value["tolerance"] != 1e-9
        or value["retry"] != "none"
    ):
        raise ValueError("new protocol/budget identity drift")
    return value


def map_identity(process, runtime, rt):
    paths = sorted(
        {
            x.split()[-1]
            for x in Path(f"/proc/{process.pid}/maps").read_text().splitlines()
            if len(x.split()) >= 6
            and x.split()[-1].startswith("/")
            and ".so" in x.split()[-1]
        }
    )
    wanted = {
        str((runtime / name).resolve()): digest(runtime / name)
        for name in rt["libraries"].values()
    }
    actual = {x: digest(Path(x)) for x in paths}
    if actual != wanted:
        raise ValueError("loaded native library closure drift")
    return actual


def construct(binary, side, mode, directory):
    rt = native_runtime.verify(binary, side)
    launches = []

    def popen(argv, **kw):
        env = dict(kw.get("env", os.environ))
        env["GO2_MJPC_WARMSTART_OWNER"] = mode
        kw["env"] = env
        process = subprocess.Popen(argv, **kw)
        launches.append({"pid": process.pid, "argv": argv, "warmstart_owner": mode})
        return process

    timing = load_anchor()["controllers"]["mjpc"]["timing"]
    native = NativeMJPCController(
        binary,
        timing,
        popen=popen,
        stderr_log_path=directory / "native.stderr.log",
        diagnostic=(
            "floor0",
            side.parent / rt["canonical_xml"],
            directory / "predictions.jsonl",
        ),
        runtime_identity=side,
        fd_trace_path=directory / "fd-trace.jsonl",
    )
    try:
        if (
            len(launches) != 1
            or native.ready.get("warmstart_owner") != mode
            or native.ready.get("worker_count") != 4
            or native.ready.get("horizon_steps") != 36
            or native.ready.get("planner_dt") != 0.01
        ):
            raise ValueError("native owner/readiness drift")
        maps = map_identity(native.process, side.parent, rt)
        return native, launches, maps
    except BaseException:
        native.close()
        raise


def prepare(output):
    with experiment_lock(), zero_step_guard(), EvidenceRun(output) as run:
        ident = identity()
        p = protocol()
        verify_manifest(BUILD)
        bi = strict_json((BUILD / "build-identity.json").read_text())
        if bi["inputs"] != native_inputs(BUILD / "build"):
            raise ValueError("new sealed native build changed")
        binary = BUILD / "build/go2_mjpc_controller_fd_fixed"
        if digest(binary) != bi["binary_sha256"]:
            raise ValueError("new binary mismatch")
        rt = native_runtime.package(
            binary, run.path / "runtime", ROOT, {**bi, "workers": 4}
        )
        source = run.path / "runtime" / rt["task_xml"]
        tree = ET.parse(source)
        floors = [g for g in tree.getroot().iter("geom") if g.get("name") == "floor"]
        if len(floors) != 1 or floors[0].get("pos") != "0 0 -0.01":
            raise ValueError("source floor identity drift")
        floors[0].set("pos", "0 0 0")
        tree.write(source, encoding="unicode")
        assert_only_floor_z_changed(
            ROOT / ".substrate/mjpc/mjpc/tasks/quadruped/task_flat.xml", source
        )
        rt["files"][rt["task_xml"]] = digest(source)
        side = run.path / "runtime" / native_runtime.SIDECAR
        side.write_text(json.dumps(rt, indent=2) + "\n")
        native_runtime.verify(run.path / "runtime" / binary.name, side)
        from .environment import verify_environment

        env = verify_environment()
        write_new(run.path / "environment.json", env)
        checks = {}
        checks["contracts"] = run_logged(
            [
                sys.executable,
                "-B",
                "-c",
                "import unittest; from tools.substrate.guards import zero_step_guard; "
                "s=unittest.defaultTestLoader.loadTestsFromNames(['tools.substrate.test_native_transport',"
                "'tools.substrate.test_native_mjpc','tools.substrate.test_mjpc_sequence_reset',"
                "'tools.substrate.test_mjpc_sequence_mapping','tools.substrate.test_mjpc_logical_warmstart']);"
                "g=zero_step_guard();g.__enter__();r=unittest.TextTestRunner(verbosity=2).run(s);"
                "g.__exit__(None,None,None);raise SystemExit(not r.wasSuccessful())",
            ],
            run.path,
            "contracts",
        )
        checks["quality"] = run_logged(
            [
                str(ROOT / ".substrate/dev-venv/bin/python"),
                "-B",
                "-m",
                "tools.check_quality",
            ],
            run.path,
            "quality",
        )
        handshake = {}
        anchor = load_anchor()
        canon = side.parent / rt["canonical_xml"]
        for mode in ("logical", "worker"):
            d = run.path / ("handshake_" + mode)
            d.mkdir()
            native, launches, maps = construct(side.parent / binary.name, side, mode, d)
            plant = MujocoPlant(canon)
            validate_canonical_model(anchor, plant.model)
            try:
                native.reset(plant.whole_body_state())
                if (
                    plant.steps
                    or plant.data.time
                    or native.diagnostics().get("last_step") is not None
                ):
                    raise ValueError("qualification unexpectedly advanced")
                handshake[mode] = {
                    "ready": native.ready,
                    "maps": maps,
                    "launches": launches,
                    "after_reset": native.diagnostics(),
                    "canonical_steps": 0,
                    "optimizer_calls": 0,
                }
            finally:
                native.close()
            if (d / "native.stderr.log").stat().st_size or (
                d / "fd-trace.jsonl"
            ).exists():
                raise ValueError("qualification warning or unexpected FD")
        write_new(run.path / "handshakes.json", handshake)
        snapshot = inputs()
        if identity() != ident:
            raise ValueError("source changed during qualification")
        packet = {
            **ident,
            "protocol": p,
            "protocol_sha256": digest(PROTOCOL),
            "inputs": snapshot,
            "runtime_sidecar_sha256": digest(side),
            "binary_sha256": bi["binary_sha256"],
            "native_build_manifest": digest(BUILD / "manifest.json"),
            "output": str(RAW),
            "qualification": {
                "clean": True,
                "optimizer_calls": 0,
                "canonical_steps": 0,
                "checks": checks,
            },
        }
        write_new(run.path / "packet.json", packet)
        run.result.update(
            status="ENGINEERING_ADMITTED",
            head=ident["head"],
            optimizer_calls=0,
            canonical_steps=0,
            checks=checks,
        )
    return packet


def precheck(packet_path, output):
    packet_path = Path(packet_path).resolve(strict=True)
    admission = verify_manifest(packet_path.parent)
    pkt = strict_json(packet_path.read_text())
    if (
        admission["status"] != "ENGINEERING_ADMITTED"
        or pkt["head"] != identity()["head"]
        or pkt["protocol"] != protocol()
        or pkt["protocol_sha256"] != digest(PROTOCOL)
        or pkt["inputs"] != inputs()
        or str(Path(output).resolve()) != pkt["output"]
        or Path(output).exists()
        or live_controller_processes()
    ):
        raise ValueError("fresh precheck identity/input/output/process gate")
    if (
        pkt["qualification"]["optimizer_calls"] != 0
        or pkt["qualification"]["canonical_steps"] != 0
        or admission.get("optimizer_calls") != 0
        or admission.get("canonical_steps") != 0
    ):
        raise ValueError("qualification consumed live budget")
    ledger = (
        ROOT / "_runs" / ("logical_warmstart_campaign_" + digest(packet_path) + ".json")
    )
    if ledger.exists():
        raise ValueError("campaign already reserved; cannot retry")
    side = packet_path.parent / "runtime" / native_runtime.SIDECAR
    if digest(side) != pkt["runtime_sidecar_sha256"]:
        raise ValueError("sidecar changed")
    native_runtime.verify(side.parent / "go2_mjpc_controller_fd_fixed", side)
    return pkt


def metrics(rows):
    actions = [x for x in rows if x.get("action")]
    saturated = [x["tick"] for x in actions if any(x["action"]["saturated"])]
    import math

    def rpy(q):
        w, x, y, z = q
        return math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)), math.asin(
            max(-1, min(1, 2 * (w * y - z * x)))
        )

    angles = [rpy(x["qpos"][3:7]) for x in rows]
    return {
        "terminal_tick": rows[-1]["tick"],
        "terminal_reason": rows[-1]["terminal_reason"],
        "progress_m": rows[-1]["qpos"][0] - rows[0]["qpos"][0],
        "height_min_m": min(x["qpos"][2] for x in rows),
        "height_max_m": max(x["qpos"][2] for x in rows),
        "max_abs_roll": max(abs(x[0]) for x in angles),
        "max_abs_pitch": max(abs(x[1]) for x in angles),
        "first_saturation_tick": min(saturated) if saturated else None,
        "saturated_ticks": len(saturated),
    }


def compare(first, second):
    a = [strict_json(x) for x in (first / "raw.jsonl").read_text().splitlines()]
    b = [strict_json(x) for x in (second / "raw.jsonl").read_text().splitlines()]
    ma, mb = metrics(a), metrics(b)
    detail = {}
    for key, field in (
        ("state_qpos", "qpos"),
        ("state_qvel", "qvel"),
        ("control", "action"),
        ("target", "target"),
    ):
        differences = []
        for x, y in zip(a, b):
            if field == "action":
                u, v = (
                    (x[field]["ctrl"] if x.get(field) else []),
                    (y[field]["ctrl"] if y.get(field) else []),
                )
            elif field == "target":
                u, v = (
                    (x[field]["position_target"] if x.get(field) else []),
                    (y[field]["position_target"] if y.get(field) else []),
                )
            else:
                u, v = x[field], y[field]
            if len(u) != len(v):
                continue
            d = max((abs(i - j) for i, j in zip(u, v)), default=0)
            differences.append((x["tick"], d))
        detail[key] = {
            "first_exact_difference": next((t for t, d in differences if d != 0), None),
            "first_over_1e_9": next((t for t, d in differences if d > 1e-9), None),
            "max_abs": max((d for t, d in differences), default=0),
        }
    thresholds = protocol()["repeatability_checks"]
    sa, sb = ma["first_saturation_tick"], mb["first_saturation_tick"]
    sat_gap = (
        abs(sa - sb) if sa is not None and sb is not None else (0 if sa == sb else None)
    )
    checks = {
        "both_reach_horizon": ma["terminal_reason"]
        == mb["terminal_reason"]
        == "horizon",
        "progress": abs(ma["progress_m"] - mb["progress_m"])
        <= thresholds["progress_abs_difference_m_max"],
        "height": max(abs(ma[k] - mb[k]) for k in ("height_min_m", "height_max_m"))
        <= thresholds["body_height_envelope_abs_difference_m_max"],
        "roll": abs(ma["max_abs_roll"] - mb["max_abs_roll"])
        <= thresholds["max_abs_roll_difference_rad_max"],
        "pitch": abs(ma["max_abs_pitch"] - mb["max_abs_pitch"])
        <= thresholds["max_abs_pitch_difference_rad_max"],
        "saturation": sat_gap is not None
        and sat_gap <= thresholds["first_torque_saturation_tick_difference_max"],
    }
    if (first / "RESULT.json").exists() and (second / "RESULT.json").exists():
        ra = strict_json((first / "RESULT.json").read_text())
        rb = strict_json((second / "RESULT.json").read_text())
        checks["both_canonical_replays_pass"] = (
            ra["replay"]["verdict"] == rb["replay"]["verdict"] == "PASS"
        )
    else:
        checks["both_canonical_replays_pass"] = False

    def contacts(directory):
        path = directory / "predictions.jsonl"
        if not path.exists():
            return None
        predictions = [strict_json(x) for x in path.read_text().splitlines()]
        if len(predictions) < 3:
            return None
        if abs(predictions[2]["states"][0]["time_s"] - 0.04) > 1e-12:
            raise ValueError("tick20 prediction time")
        return [
            [sorted(c["geom_ids"]) for c in state["active_contacts"]]
            for state in predictions[2]["states"]
        ]

    ca, cb = contacts(first), contacts(second)
    checks["tick20_selected_state_contact_sets_match"] = ca is not None and ca == cb
    return {
        "first": ma,
        "second": mb,
        "first_saturation_gap": sat_gap,
        "differences": detail,
        "engineering_checks": checks,
    }


def _capture(packet_path, review_path, authorization_path, output):
    output = Path(output)
    with experiment_lock(), wall_deadline(protocol()["wall_timeout_s"]):
        pkt = precheck(packet_path, output)
        review = strict_json(Path(review_path).read_text())
        validate_review(review, pkt["head"])
        authorization = strict_json(Path(authorization_path).read_text())
        validate_authorization(
            authorization,
            {
                **pkt,
                "prepared_manifest_sha256": digest(
                    Path(packet_path).parent / "manifest.json"
                ),
                "max_attempts": 4,
            },
        )
        ledger = (
            ROOT
            / "_runs"
            / ("logical_warmstart_campaign_" + digest(packet_path) + ".json")
        )
        write_new(
            ledger,
            {
                "packet": digest(packet_path),
                "head": pkt["head"],
                "outputs": pkt["protocol"]["order"],
                "max_attempts": 4,
                "status": "RESERVED_NO_RETRY",
                "authorization": authorization,
                "review_sha256": digest(review_path),
            },
        )
        with EvidenceRun(output) as campaign:
            write_new(
                output / "binding.json",
                {
                    "packet": pkt,
                    "ledger": str(ledger),
                    "ledger_sha256": digest(ledger),
                    "qualification_manifest": digest(
                        Path(packet_path).parent / "manifest.json"
                    ),
                    "review": review,
                    "authorization": authorization,
                },
            )
            completed = []
            total = {
                "canonical_steps": 0,
                "attempts": 0,
                "optimizer_calls": 0,
                "private_upper": 0,
                "private_reserved": 0,
            }
            for slot, label in enumerate(pkt["protocol"]["order"], 1):
                mode = "logical" if label.startswith("logical") else "worker"
                claim = ledger.with_name(ledger.stem + f"_slot{slot}.claim")
                write_new(
                    claim,
                    {
                        "slot": slot,
                        "mode": mode,
                        "output": str(output / label),
                        "status": "CLAIMED_NO_RETRY",
                    },
                )
                d = output / label
                with EvidenceRun(d) as run:
                    side = Path(packet_path).parent / "runtime" / native_runtime.SIDECAR
                    rt = native_runtime.verify(
                        side.parent / "go2_mjpc_controller_fd_fixed", side
                    )
                    plant = MujocoPlant(side.parent / rt["canonical_xml"])
                    anchor = load_anchor()
                    validate_canonical_model(anchor, plant.model)
                    native, launches, maps = construct(
                        side.parent / "go2_mjpc_controller_fd_fixed", side, mode, d
                    )
                    write_new(
                        d / "launch.json",
                        {"launches": launches, "maps": maps, "ready": native.ready},
                    )
                    controller = StrictWarningController(
                        PositionTargetControllerAdapter(
                            native, native.actuator_spec, native.joint_names
                        )
                    )
                    consumed = False

                    def consume():
                        nonlocal consumed
                        if consumed:
                            raise ValueError("duplicate first-sample attempt")
                        write_new(
                            d / "attempt.json",
                            {
                                "slot": slot,
                                "head": pkt["head"],
                                "boundary": "first valid post-reset state/control sample",
                                "claim": str(claim),
                                "claim_sha256": digest(claim),
                            },
                        )
                        consumed = True

                    task = replace(
                        anchor["task"],
                        task_id=pkt["protocol"]["id"],
                        horizon_ticks=1500,
                        measurement_start_tick=150,
                    )
                    started = time.monotonic()
                    try:
                        with (d / "raw.jsonl").open("x") as f:

                            def emit(row):
                                f.write(
                                    json.dumps(row, sort_keys=True, allow_nan=False)
                                    + "\n"
                                )
                                f.flush()

                            outcome = run_aligned_episode(
                                plant,
                                controller,
                                task,
                                anchor["controllers"]["mjpc"]["information"],
                                anchor["controllers"]["mjpc"]["timing"],
                                emit,
                                consume,
                            )
                            f.flush()
                            os.fsync(f.fileno())
                        diag = native.diagnostics()
                    finally:
                        native.close()
                        write_new(d / "partial-diagnostics.json", native.diagnostics())
                    diag = native.diagnostics()
                    if diag["transport"]["stderr_bytes"] or diag["transport"].get(
                        "stderr_read_error"
                    ):
                        raise ValueError("native warning/drain stop")
                    acc = diag["last_step"]["diagnostic"]
                    calls = acc["policy_id"]
                    upper = (
                        acc["fd_step_upper_bound_count"] + acc["rollout_mj_step_count"]
                    )
                    if (
                        calls > 150
                        or acc["private_step_upper_bound_reserved"] != 4096 * calls
                        or upper != 2452 * calls
                        or (outcome["terminal_reason"] == "horizon" and calls != 150)
                    ):
                        raise ValueError("fixed private budget/counter drift")
                    rows = [
                        strict_json(x)
                        for x in (d / "raw.jsonl").read_text().splitlines()
                    ]
                    replay = replay_aligned_rows(rows, task, 0.002)
                    write_new(d / "diagnostics.json", diag)
                    result = {
                        "outcome": outcome,
                        "metrics": metrics(rows),
                        "replay": replay,
                        "canonical_steps": plant.steps,
                        "attempts": int(consumed),
                        "optimizer_calls": calls,
                        "private_upper": upper,
                        "private_reserved": 4096 * calls,
                        "elapsed_s": time.monotonic() - started,
                        "classification": "HORIZON_REACHED"
                        if outcome["terminal_reason"] == "horizon"
                        else "SAFETY_STOP",
                    }
                    write_new(d / "RESULT.json", result)
                    run.result.update(
                        status=result["classification"], **{k: result[k] for k in total}
                    )
                completed.append(label)
                for k in total:
                    total[k] += result[k]
                if (
                    replay["verdict"] != "PASS"
                    or result["classification"] != "HORIZON_REACHED"
                ):
                    break
            comparisons = {}
            for mode in ("logical", "worker"):
                if mode + "1" in completed and mode + "2" in completed:
                    comparisons[mode] = compare(
                        output / (mode + "1"), output / (mode + "2")
                    )
            result = {
                "status": "CAMPAIGN_COMPLETE"
                if len(completed) == 4
                else "CAMPAIGN_STOPPED",
                "completed": completed,
                "not_run": [x for x in pkt["protocol"]["order"] if x not in completed],
                "budget": "CLOSED",
                "totals": total,
                "comparisons": comparisons,
                "retry": "none",
                "ledger": str(ledger),
                "ledger_sha256": digest(ledger),
            }
            if (
                total["canonical_steps"] > 6000
                or total["attempts"] > 4
                or total["optimizer_calls"] > 600
                or total["private_upper"] > 1471200
                or total["private_reserved"] > 2457600
            ):
                raise ValueError("aggregate budget exceeded")
            write_new(output / "RESULT.json", result)
            campaign.result.update(
                status=result["status"], budget="CLOSED", totals=total
            )
    return result


def capture(packet_path, review_path, authorization_path, output):
    ledger = (
        ROOT / "_runs" / ("logical_warmstart_campaign_" + digest(packet_path) + ".json")
    )
    closed = ledger.with_suffix(".closed.json")
    try:
        return _capture(packet_path, review_path, authorization_path, output)
    finally:
        if ledger.exists() and not closed.exists():
            write_new(
                closed,
                {
                    "budget": "CLOSED",
                    "retry": "none",
                    "ledger_sha256": digest(ledger),
                    "output": str(output),
                    "claims": [
                        str(x)
                        for x in sorted(
                            ledger.parent.glob(ledger.stem + "_slot*.claim")
                        )
                    ],
                },
            )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("prepare", "precheck", "capture"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--packet", type=Path)
    p.add_argument("--review", type=Path)
    p.add_argument("--authorization", type=Path)
    a = p.parse_args()
    if a.action == "prepare":
        v = prepare(a.output)
    elif a.action == "precheck":
        with experiment_lock():
            v = precheck(a.packet, a.output)
    else:
        v = capture(a.packet, a.review, a.authorization, a.output)
    print(json.dumps(v, sort_keys=True))


if __name__ == "__main__":
    main()
