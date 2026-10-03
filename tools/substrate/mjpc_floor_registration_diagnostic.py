"""Single-arm private floor registration diagnostic."""

import argparse
import json
import math
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from . import fd_duplicate_diagnostic as build, native_runtime
from . import mjpc_fixed_baseline as baseline
from . import qualification
from .aligned_anchor import load_anchor, validate_canonical_model
from .aligned_episode import replay_aligned_rows, run_aligned_episode
from .contracts import MOTOR_JOINTS, PositionTargetControllerAdapter
from .episode import MujocoPlant
from .guards import wall_deadline, zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_manifest,
    verify_bundle,
    write_new,
)
from .native_mjpc import NativeMJPCController
from .readiness import validate_authorization, validate_review
from tools.research.preflight import DEFAULT_PROCESS_NAMES, find_processes

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "research/mjpc-floor-registration-12s-20261003"
PROTOCOL = ROOT / "tools/substrate/protocols/mjpc_floor_registration_repeat_3s_v1.json"
PROTOCOL_12S = ROOT / "tools/substrate/protocols/mjpc_floor_registration_sustained_12s_v1.json"
R4_PREP = ROOT / "_runs/mjpc_fixed_baseline_prepared_r4_20261003"
R4_RAW = ROOT / "_runs/mjpc_fixed_baseline_capture_r4_20261003T002510Z_repeat1"
MODE = "floor0"
LIMIT = 614400
RESERVE = 4096


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def validate_qualification_claim(record, expected_head, binary_sha256, runtime_sha256):
    qualification_record = record.get("qualification", {})
    inputs = record.get("qualification_inputs", {})
    controller = inputs.get("fd_fixed_controller") or {}
    smoke = record.get("physics_accounting", {})
    retained = record.get("smoke_provenance") is not None
    if (
        record.get("qualification_profile")
        != "mjpc_floor_registration_sustained_12s_v1"
        or qualification_record.get("head") != expected_head
        or qualification_record.get("clean_head") is not True
        or qualification_record.get("development") is not False
        or record.get("canonical_physics_steps") != 0
        or record.get("scientific_attempts") != 0
        or type(record.get("private_engineering_optimizer_calls")) is not int
        or record.get("private_engineering_optimizer_calls") != (0 if retained else 1)
        or record.get("reused_private_engineering_optimizer_calls", 0) != (1 if retained else 0)
        or controller.get("binary_sha256") != binary_sha256
        or smoke.get("binary_sha256") != binary_sha256
        or smoke.get("runtime_identity_sha256") != runtime_sha256
        or smoke.get("canonical_steps") != 0
        or smoke.get("scientific_attempts") != 0
        or smoke.get("optimizer_calls") != 1
        or type(smoke.get("private_step_upper_bound_max")) is not int
        or smoke.get("private_step_upper_bound_max") != 4096
        or (
            "private_step_upper_bound_max" in record
            and (
                type(record["private_step_upper_bound_max"]) is not int
                or record["private_step_upper_bound_max"]
                != smoke.get("private_step_upper_bound_max")
            )
        )
    ):
        raise ValueError("qualification receipt does not bind the exact floor0 consumer")
    if retained:
        from .mjpc_smoke_reuse import validate_reuse_record

        validate_reuse_record(record)
    return True


def identity():
    branch, head = git("branch", "--show-current"), git("rev-parse", "HEAD")
    if branch != BRANCH or git("status", "--porcelain"):
        raise ValueError("requires exact clean named diagnostic branch")
    return {"branch": branch, "head": head}


def protocol():
    expected = {
        "schema": 1,
        "id": "mjpc-floor-registration-repeatability-3s-v1",
        "parent_r4_head": "6e829bed5dcd4a8b4dc6b575f70b1a5be422cb78",
        "parent_floor0_result_sha256": "47cf21600c3f56ab60b709242fcfa14454ffb67beaad6c6c1bed72aedb3f2c26",
        "parent_floor0_packet_sha256": "7662c2d96ca664162888e8f5870b9013f2919c26eca295994d53bb73c04de402",
        "repeats": 2,
        "attempts_per_repeat": 1,
        "max_attempts": 2,
        "horizon_s": 3.0,
        "canonical_steps_max": 1500,
        "max_replan_calls": 150,
        "capture_native_controller_processes_per_repeat_max": 1,
        "capture_native_controller_processes_campaign_max": 2,
        "construction_handshake_native_processes_max": 1,
        "private_step_upper_bound_per_repeat": LIMIT,
        "private_step_upper_bound_total_max": 1228800,
        "seed_rule": "xfrc_std=0; no seed",
        "campaign_identity": "prepared packet SHA-256; repeat index 1 or 2",
        "one_shot_reservation": "exclusive two-attempt campaign record keyed by prepared packet SHA-256; each repeat slot is claimed once",
        "private_reservation_per_replan": RESERVE,
        "private_step_upper_bound_max": LIMIT,
        "wall_timeout_s": 300,
        "zero_command_ticks": 50,
        "ramp_ticks": 100,
        "command_body_mps": [1.0, 0.0, 0.0],
        "intervention": {
            "field": "private_task_flat.floor.pos.z",
            "from_m": -0.01,
            "to_m": 0.0,
        },
        "preserve": [
            "canonical_model",
            "home_reset",
            "mass",
            "damping",
            "contact_smoothing",
            "PD60_5",
            "torque_limits",
            "cost",
            "gait_Trot_Manual",
            "0.35s_horizon",
            "10ms_planner_dt",
            "20ms_replan",
            "2ms_feedback",
            "one_sided_fd1e-6",
            "derivative_skip0",
            "four_workers",
            "FD_duplicate_fix",
        ],
        "failure_policy": "stop before repeat 2 unless repeat 1 has a verified HORIZON_REACHED result; stop on first safety, execution, evidence, identity, warning or budget failure; no retry",
        "prediction_contact_semantics": "selected-state forward reconstruction on smoothed private model; not future rollout",
        "capability_claim": "none; two-repeat 3-second reproducibility diagnostic",
        "repeatability_checks": {
            "both_reach_horizon": True,
            "both_canonical_replays_pass": True,
            "tick20_selected_state_contact_sets_match": True,
            "progress_abs_difference_m_max": 0.05,
            "body_height_envelope_abs_difference_m_max": 0.02,
            "max_abs_roll_difference_rad_max": 0.03,
            "max_abs_pitch_difference_rad_max": 0.03,
            "first_torque_saturation_tick_difference_max": 200,
            "interpretation": "predeclared engineering repeatability check only; not robustness or baseline qualification",
        },
        "start_gate": "fresh exact-head independent science and execution reviews plus one protocol/manifest-bound user authorization for exactly two one-shot repeat slots",
    }
    value = strict_json(PROTOCOL.read_text())
    if value != expected:
        raise ValueError("floor-only protocol drift")
    return value



def protocol_12s():
    expected = dict(protocol())
    expected.update(
        id="mjpc-floor-registration-sustained-12s-v1",
        repeats=1,
        max_attempts=1,
        horizon_s=12.0,
        canonical_steps_max=6000,
        max_replan_calls=600,
        capture_native_controller_processes_campaign_max=1,
        private_step_upper_bound_per_repeat=2457600,
        private_step_upper_bound_total_max=2457600,
        private_step_upper_bound_max=2457600,
        failure_policy="stop on first safety, execution, evidence, identity, warning, wall-time or private-budget failure; no retry",
        one_shot_reservation="exclusive one-attempt record keyed by prepared packet SHA-256; slot 1 can be claimed once",
        capability_claim="none; one-arm 12-second sustained-control diagnostic",
        start_gate="fresh exact-head science and execution reviews plus one protocol/manifest-bound user authorization for one attempt",
        campaign_identity="prepared packet SHA-256; single allowed slot 1",
        parent_repeat_campaign_result_sha256="c92d3ae1d21f97f8d6c689eaf421fbb15187f3731bee7b0dcabdad5cb8fe855a",
        parent_saturation_posthoc_sha256="0e56e77b75ec517773c461092f1a38913c40acf5ac5aca0d2741fce3e326fd39",
        saturation_reporting={
            "actuator_joint_order": "source actuator order with named mapping",
            "per_joint": [
                "peak_abs_requested_torque_Nm",
                "max_excess_beyond_ctrlrange_Nm",
                "saturated_action_ticks",
                "saturated_action_share_pct",
                "longest_consecutive_saturated_ticks",
                "episode_start_end_and_duration_s",
            ],
            "whole_run": [
                "total_saturated_action_ticks",
                "total_saturated_joint_ticks",
                "warnings_and_safety_stop_reason",
            ],
            "decision_threshold": "report only; no saturation pass/fail threshold",
        },
        inference_boundary="single-arm frozen-condition result; no causal attribution, repeatability, robustness, or baseline qualification",
        task_spec={
            "command_body_mps": [1.0, 0.0, 0.0],
            "command_frame": "body",
            "zero_command_ticks": 50,
            "ramp_ticks": 100,
            "measurement_start_tick": 150,
            "physics_step_s": 0.002,
            "stop_on": ["nonfinite", "orientation", "physics_warning", "nonfoot_contact", "posture", "lateral"],
            "safety_thresholds": {
                "height_min_m": 0.12,
                "height_max_m": 0.55,
                "tilt_max_rad": 0.8,
                "lateral_max_m": 0.4,
                "quaternion_norm_sq_abs_error_max": 0.000002,
            },
            "canonical_replay_thresholds": {
                "progress_min_m": 0.05,
                "body_vx_mae_max_mps": 2.0,
            },
        },
    )
    expected.pop("repeatability_checks")
    value = strict_json(PROTOCOL_12S.read_text())
    parent = ROOT / "_runs/mjpc_floor_registration_repeat_gate_20261003_r4"
    if (
        digest(parent / "CAMPAIGN_RESULT.json") != value["parent_repeat_campaign_result_sha256"]
        or digest(parent / "SATURATION_POSTHOC.json") != value["parent_saturation_posthoc_sha256"]
    ):
        raise ValueError("12-second parent repeat evidence drift")
    if value != expected:
        raise ValueError("12-second floor-only protocol drift")
    return value


def protocol_for_id(task_id):
    if task_id == protocol()["id"]:
        return protocol()
    if task_id == protocol_12s()["id"]:
        return protocol_12s()
    raise ValueError("unknown floor-registration protocol")


def _floor(root):
    xs = [e for e in root.iter("geom") if e.get("name") == "floor"]
    if len(xs) != 1:
        raise ValueError("expected unique private floor")
    p = xs[0].get("pos", "").split()
    if len(p) != 3:
        raise ValueError("bad floor position")
    return xs[0], p


def assert_only_floor_z_changed(a_path, b_path):
    a, b = ET.parse(a_path).getroot(), ET.parse(b_path).getroot()
    ga, pa = _floor(a)
    gb, pb = _floor(b)
    if pa[2] != "-0.01" or pb[2] != "0":
        raise ValueError("floor z must be -0.01 -> 0")
    if pa[:2] != pb[:2]:
        raise ValueError("floor x/y changed")
    normalized = " ".join(pa[:2] + ["0"])
    ga.set("pos", normalized)
    gb.set("pos", normalized)
    if ET.tostring(a) != ET.tostring(b):
        raise ValueError("private XML changed beyond floor.pos.z")
    return {
        "field": "private_task_flat.floor.pos.z",
        "from_m": -0.01,
        "to_m": 0.0,
        "other_xml_values_equal": True,
    }


def sealed_r4():
    verify_manifest(R4_PREP)
    verify_manifest(R4_RAW)
    old = strict_json((R4_PREP / "packet.json").read_text())
    out = strict_json((R4_RAW / "outcome.json").read_text())
    rawsha, predsha = digest(R4_RAW / "raw.jsonl"), digest(R4_RAW / "predictions.jsonl")
    man = strict_json((R4_RAW / "manifest.json").read_text())
    if (
        old.get("head") != protocol()["parent_r4_head"]
        or man.get("raw.jsonl") != rawsha
        or out.get("classification") != "SAFETY_STOP"
        or out.get("canonical_physics_steps") != 260
    ):
        raise ValueError("sealed R4 identity/outcome changed")
    rows = [strict_json(x) for x in (R4_RAW / "raw.jsonl").read_text().splitlines()]
    by = {x["tick"]: x for x in rows}
    sat = min(
        x["tick"]
        for x in rows
        if x.get("action") and any(x["action"].get("saturated") or [])
    )
    preds = [
        strict_json(x) for x in (R4_RAW / "predictions.jsonl").read_text().splitlines()
    ]
    pred = next(
        x
        for x in preds
        if x["policy_id"] == 3
        and math.isclose(x["anchor_time_s"], 0.04, rel_tol=0, abs_tol=1e-12)
    )["states"][0]
    labels = sorted(
        {
            n
            for c in pred["active_contacts"]
            for n in c["geom_names"]
            if n in ("FR", "FL", "RR", "RL")
        }
    )
    diff = max(abs(a - b) for a, b in zip(pred["qpos"], by[20]["qpos"]))
    if (
        sat != 105
        or labels
        or set(by[20]["supports"]) != {"FR", "FL", "RR", "RL"}
        or diff >= 0.001
    ):
        raise ValueError("R4 contact/saturation facts differ")
    return {
        "path": str(R4_RAW),
        "manifest_sha256": digest(R4_RAW / "manifest.json"),
        "raw_sha256": rawsha,
        "predictions_sha256": predsha,
        "outcome_sha256": digest(R4_RAW / "outcome.json"),
        "stop_tick": 260,
        "stop_reason": "nonfoot_contact",
        "canonical_steps": 260,
        "optimizer_calls": out["optimizer_calls"],
        "first_pd_saturation_tick": sat,
        "tick20": {
            "actual_supports": by[20]["supports"],
            "selected_state_reconstructed_feet": labels,
            "qpos_max_abs_diff": diff,
            "semantics": "selected-state forward reconstruction on smoothed private model; not future rollout",
        },
        "reuse": "comparison only; never rerun",
    }



def sealed_floor0_single():
    capture = ROOT / "_runs/mjpc_floor_registration_capture_20261003_r2"
    prepared = ROOT / "_runs/mjpc_floor_registration_prepared_20261003_r2"
    verify_manifest(capture)
    verify_manifest(prepared)
    result = strict_json((capture / "RESULT.json").read_text())
    attempt = strict_json((capture / "attempt.json").read_text())
    packet = strict_json((prepared / "packet.json").read_text())
    if (
        digest(capture / "RESULT.json") != protocol()["parent_floor0_result_sha256"]
        or digest(prepared / "packet.json") != protocol()["parent_floor0_packet_sha256"]
        or attempt.get("head") != packet.get("head")
        or attempt.get("packet_sha256") != digest(prepared / "packet.json")
        or result.get("classification") != "HORIZON_REACHED"
        or result.get("canonical_physics_steps") != 1500
        or result.get("retry") != "none"
        or packet.get("private_model_delta", {}).get("field")
        != "private_task_flat.floor.pos.z"
    ):
        raise ValueError("sealed floor0 parent result/identity changed")
    return {
        "path": str(capture),
        "head": packet["head"],
        "packet_sha256": digest(prepared / "packet.json"),
        "manifest_sha256": digest(capture / "manifest.json"),
        "result_sha256": digest(capture / "RESULT.json"),
        "classification": result["classification"],
        "canonical_physics_steps": result["canonical_physics_steps"],
        "retry": "none",
        "reuse": "comparison only; never rerun",
    }

def runtime_delta(rt):
    old = R4_PREP / "runtime"
    files_old = {
        x.relative_to(old).as_posix(): digest(x) for x in old.rglob("*") if x.is_file()
    }
    files_new = {
        x.relative_to(rt).as_posix(): digest(x) for x in rt.rglob("*") if x.is_file()
    }
    if set(files_old) != set(files_new):
        raise ValueError("runtime closure file set changed")
    diffs = [
        {"path": k, "r4_sha256": files_old[k], "floor0_sha256": files_new[k]}
        for k in sorted(files_old)
        if files_old[k] != files_new[k]
    ]
    allowed = {
        "go2_mjpc_controller_fd_fixed",
        "build-provenance.json",
        "source/mjpc/tasks/quadruped/task_flat.xml",
        native_runtime.SIDECAR,
    }
    if not diffs or {x["path"] for x in diffs} - allowed:
        raise ValueError(
            "runtime changed outside binary/provenance/private floor/sidecar"
        )
    return diffs


def prepare(binary, output, qualification_path, protocol_id=None):
    p = protocol() if protocol_id in (None, protocol()["id"]) else protocol_for_id(protocol_id)
    protocol_path = PROTOCOL if p["id"] == protocol()["id"] else PROTOCOL_12S
    ident = identity()
    qualification_reference = qualification.validate(qualification_path)
    if qualification_reference["producer_head"] != ident["head"]:
        raise ValueError("qualification receipt producer HEAD differs")
    r4 = sealed_r4()
    old = strict_json((R4_PREP / "packet.json").read_text())
    if verify_manifest(R4_PREP).get("status") != "PREPARED_NOT_RUN":
        raise ValueError("R4 preparation not sealed")
    bi = build.build_identity(binary, "fixed")
    if bi["binary_sha256"] == old["binary"]["sha256"]:
        raise ValueError("binary lacks floor0 label")
    for key in (
        "variant",
        "workers",
        "mjpc_commit",
        "mjpc_source_sha256",
        "generated_source_sha256",
        "diagnostic_patch_script_sha256",
        "index_patch_sha256",
        "index_patch_applier_sha256",
        "index_helper_header_sha256",
    ):
        if bi.get(key) != old["build"].get(key):
            raise ValueError("fixed controller source/build input drift: " + key)
    out = Path(output).resolve()
    if out.parent != (ROOT / "_runs").resolve() or out.exists():
        raise ValueError("output must be fresh child of _runs")
    with (
        experiment_lock(),
        zero_step_guard(),
        EvidenceRun(out, {"operation": "floor0_prepare", **ident}) as run,
    ):
        rt = out / "runtime"
        native_runtime.package(binary, rt, ROOT, bi)
        task = rt / "source/mjpc/tasks/quadruped/task_flat.xml"
        base = R4_PREP / "runtime/source/mjpc/tasks/quadruped/task_flat.xml"
        s = task.read_text()
        pat = r'(<geom\b[^>]*\bname="floor"[^>]*\bpos="[^"]*?)-0\.01([^"]*")'
        s, n = re.subn(pat, r"\g<1>0\g<2>", s, count=1)
        if n != 1:
            raise ValueError("unique private floor z edit not found")
        task.write_text(s)
        delta = assert_only_floor_z_changed(base, task)
        side = rt / native_runtime.SIDECAR
        m = strict_json(side.read_text())
        m["files"] = {
            x.relative_to(rt).as_posix(): digest(x)
            for x in sorted(rt.rglob("*"))
            if x.is_file() and x != side
        }
        side.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
        native_runtime.verify(rt / binary.name, side)
        qualification_record = verify_bundle(qualification_path)
        validate_qualification_claim(
            qualification_record,
            ident["head"],
            digest(rt / binary.name),
            digest(side),
        )
        anchor = load_anchor()
        canon = rt / m["canonical_xml"]
        plant = MujocoPlant(canon)
        validate_canonical_model(anchor, plant.model)
        if plant.steps or plant.data.time:
            raise ValueError("canonical physics advanced")
        files = tuple(
            sorted(
                set(baseline.RUNTIME)
                | {
                    "tools/substrate/mjpc_floor_registration_diagnostic.py",
                    "tools/substrate/native/diagnostic.h",
                    protocol_path.relative_to(ROOT).as_posix(),
                    "docs/research/TASK_MJPC_FLOOR_REGISTRATION_SUSTAINED_12S_20261003.md",
                }
            )
        )
        rd = runtime_delta(rt)
        packet = {
            "schema": 1,
            "kind": p["id"],
            **ident,
            "protocol_sha256": digest(protocol_path),
            "design": p,
            "qualification_reference": qualification_reference,
            "parent_r4": r4,
            "parent_floor0_single": sealed_floor0_single(),
            "r4_packet_sha256": digest(R4_PREP / "packet.json"),
            "binary": {
                "name": "runtime/" + binary.name,
                "sha256": digest(rt / binary.name),
                "build_identity": bi,
            },
            "runtime_identity": {
                "name": "runtime/" + native_runtime.SIDECAR,
                "sha256": digest(side),
            },
            "runtime_code": {x: digest(ROOT / x) for x in files},
            "runtime_file_differences": rd,
            "canonical_physical_sha256": anchor["raw"]["canonical"]["physical_sha256"],
            "canonical_xml_sha256": digest(canon),
            "private_model_delta": delta,
            "private_task_xml_sha256": digest(task),
            "task_document_sha256": digest(
                ROOT / "docs/research/TASK_MJPC_FLOOR_REGISTRATION_SUSTAINED_12S_20261003.md"
            ),
            "repeats": p["repeats"],
            "attempts_per_repeat": p["attempts_per_repeat"],
            "capture_native_controller_processes_per_repeat_max": 1,
            "capture_native_controller_processes_campaign_max": p["repeats"],
            "max_attempts": p["max_attempts"],
            "canonical_steps_max": p["canonical_steps_max"],
            "private_total_upper_bound_max": p["private_step_upper_bound_per_repeat"],
            "private_total_upper_bound_campaign_max": p["private_step_upper_bound_total_max"],
            "canonical_physics_step_authorized": False,
            "scientific_attempts_authorized": 0,
            "readiness": "AWAITING_INDEPENDENT_REVIEWS_AND_FRESH_USER_START",
        }
        write_new(out / "protocol.json", p)
        write_new(out / "packet.json", packet)
        write_new(
            out / "comparison.json",
            {
                "r4": r4,
                "interpretation": "tick20 selected-state contact labels are reconstructed, not future rollout; first PD saturation is later at tick105.",
            },
        )
        run.result.update(
            status="ENGINEERING_ADMITTED",
            task_id=p["id"],
            qualification_reference=qualification_reference,
            head=ident["head"],
            readiness=packet["readiness"],
            repeats=p["repeats"],
            max_attempts=p["max_attempts"],
            canonical_steps_max=p["canonical_steps_max"],
            private_total_upper_bound_max=p["private_step_upper_bound_per_repeat"],
            canonical_physics_steps=0,
            optimizer_calls=0,
            native_processes_started=0,
            scientific_attempts=0,
        )
    return str(out)


def validate_packet(prepared):
    d = Path(prepared).resolve(strict=True)
    ad = verify_manifest(d)
    pkt = strict_json((d / "packet.json").read_text())
    ident = identity()
    p = protocol_for_id(pkt.get("kind"))
    protocol_path = PROTOCOL if p["id"] == protocol()["id"] else PROTOCOL_12S
    if (
        ad.get("status") != "ENGINEERING_ADMITTED"
        or any(pkt.get(k) != ident[k] for k in ("branch", "head"))
        or pkt.get("parent_floor0_single") != sealed_floor0_single()
        or pkt.get("repeats") != p["repeats"]
        or pkt.get("max_attempts") != p["max_attempts"]
        or pkt.get("canonical_steps_max") != p["canonical_steps_max"]
        or pkt.get("private_total_upper_bound_max") != p["private_step_upper_bound_per_repeat"]
        or pkt.get("private_total_upper_bound_campaign_max") != p["private_step_upper_bound_total_max"]
        or pkt.get("task_document_sha256")
        != digest(ROOT / "docs/research/TASK_MJPC_FLOOR_REGISTRATION_SUSTAINED_12S_20261003.md")
    ):
        raise ValueError("prepared packet/head invalid")
    if pkt["protocol_sha256"] != digest(protocol_path) or pkt["runtime_code"] != {
        x: digest(ROOT / x) for x in pkt["runtime_code"]
    }:
        raise ValueError("protocol/source drift")
    side = d / pkt["runtime_identity"]["name"]
    binary = d / pkt["binary"]["name"]
    if (
        digest(side) != pkt["runtime_identity"]["sha256"]
        or digest(binary) != pkt["binary"]["sha256"]
    ):
        raise ValueError("runtime identity mismatch")
    native_runtime.verify(binary, side)
    qualification.validate_reference(pkt.get("qualification_reference"))
    qualification_record = verify_bundle(
        pkt["qualification_reference"]["path"]
    )
    validate_qualification_claim(
        qualification_record,
        ident["head"],
        pkt["binary"]["sha256"],
        pkt["runtime_identity"]["sha256"],
    )
    if runtime_delta(d / "runtime") != pkt.get("runtime_file_differences"):
        raise ValueError("runtime changed outside predeclared paths")
    if (
        assert_only_floor_z_changed(
            R4_PREP / "runtime/source/mjpc/tasks/quadruped/task_flat.xml",
            d / "runtime/source/mjpc/tasks/quadruped/task_flat.xml",
        )
        != pkt["private_model_delta"]
    ):
        raise ValueError("model delta mismatch")
    return pkt, binary, side


def handshake(prepared, output):
    pkt, binary, side = validate_packet(prepared)
    out = Path(output).resolve()
    if out.parent != (ROOT / "_runs").resolve() or out.exists():
        raise ValueError("handshake output must be fresh _runs child")
    anchor = load_anchor()
    with (
        experiment_lock(),
        zero_step_guard(),
        EvidenceRun(
            out, {"operation": "floor0_construction_handshake", "head": pkt["head"]}
        ) as run,
    ):
        rt = native_runtime.verify(binary, side)
        plant = MujocoPlant(side.parent / rt["canonical_xml"])
        validate_canonical_model(anchor, plant.model)
        launches = []

        def popen(argv, **kw):
            x = subprocess.Popen(argv, **kw)
            launches.append({"pid": x.pid, "argv": argv})
            return x

        pred, fd = out / "predictions.jsonl", out / "fd-trace.jsonl"
        native = NativeMJPCController(
            binary,
            anchor["controllers"]["mjpc"]["timing"],
            popen=popen,
            stderr_log_path=out / "native.stderr.log",
            diagnostic=(MODE, side.parent / rt["canonical_xml"], pred),
            runtime_identity=side,
            fd_trace_path=fd,
        )
        try:
            PositionTargetControllerAdapter(
                native, native.actuator_spec, native.joint_names
            )
            if (
                native.ready.get("worker_count") != 4
                or native.ready.get("horizon_steps") != 36
                or native.ready.get("planner_dt") != 0.01
            ):
                raise ValueError("controller readiness identity drift")
            libs = native_runtime.loaded_libraries(native.process.pid, side)
            if (
                len(launches) != 1
                or native.ready.get("worker_count") != 4
                or native.ready.get("horizon_steps") != 36
                or native.ready.get("planner_dt") != 0.01
            ):
                raise ValueError("native process count/controller readiness drift")
            if (
                plant.steps
                or plant.data.time
                or native.diagnostics().get("last_step") is not None
            ):
                raise ValueError("handshake advanced physics/optimizer")
            write_new(out / "controller-ready.json", native.ready)
            write_new(out / "loaded-libraries.json", libs)
        finally:
            native.close()
        tr = native.diagnostics()["transport"]
        if (
            tr["stderr_bytes"]
            or tr["stderr_read_error"]
            or (pred.exists() and pred.stat().st_size)
            or (fd.exists() and fd.stat().st_size)
        ):
            raise ValueError("startup warning/optimizer evidence")
        write_new(
            out / "construction.json",
            {
                "launches": launches,
                "canonical_physics_steps": plant.steps,
                "optimizer_calls": 0,
                "scientific_attempts": 0,
                "binary_sha256": digest(binary),
                "runtime_identity_sha256": digest(side),
                "stderr_bytes": tr["stderr_bytes"],
            },
        )
        run.result.update(
            status="CONSTRUCTION_PRECHECK_PASS",
            canonical_physics_steps=0,
            optimizer_calls=0,
            scientific_attempts=0,
            native_processes_started=len(launches),
        )
    return str(out)


class StrictWarningController:
    def __init__(self, inner):
        self.inner = inner

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def step(self, *args, **kwargs):
        action = self.inner.step(*args, **kwargs)
        transport = self.inner.diagnostics().get("transport", {})
        if transport.get("stderr_bytes") or transport.get("stderr_read_error"):
            raise ValueError("native warning/error; stop the single attempt")
        return action


def capture(prepared, review, authorization, output, repeat_index):
    pkt, binary, side = validate_packet(prepared)
    p = protocol_for_id(pkt["kind"])
    repeat_count = p["repeats"]
    run_limit = p["private_step_upper_bound_per_repeat"]
    d = Path(prepared).resolve()
    base = Path(output).resolve()
    if base.parent != (ROOT / "_runs").resolve() or not 1 <= repeat_index <= repeat_count:
        raise ValueError("campaign output/slot invalid")
    out = Path(str(base) + f"_repeat{repeat_index}")
    outputs = [str(Path(str(base) + f"_repeat{i}").resolve()) for i in range(1, repeat_count + 1)]
    if out.exists():
        raise ValueError("repeat output already exists; no retry")
    review = Path(review).resolve(strict=True)
    authorization = Path(authorization).resolve(strict=True)
    validate_review(strict_json(review.read_text()), pkt["head"])
    validate_authorization(
        strict_json(authorization.read_text()),
        {
            "head": pkt["head"],
            "protocol_sha256": pkt["protocol_sha256"],
            "prepared_manifest_sha256": digest(d / "manifest.json"),
            "max_attempts": repeat_count,
        },
    )
    anchor = load_anchor()
    task = baseline.replace(
        anchor["task"],
        task_id=pkt["kind"],
        horizon_ticks=p["canonical_steps_max"],
        measurement_start_tick=150,
    )
    timing = anchor["controllers"]["mjpc"]["timing"]
    info = anchor["controllers"]["mjpc"]["information"]
    rt = native_runtime.verify(binary, side)
    canon = side.parent / rt["canonical_xml"]
    if find_processes(DEFAULT_PROCESS_NAMES + ("go2_mjpc_controller_fd_fixed",)):
        raise ValueError("stale Go2/native process")
    packet_sha = digest(d / "packet.json")
    reservation = (
        ROOT / "_runs" / ("mjpc_floor_registration_campaign_" + packet_sha + ".json")
    )
    claim = reservation.with_name(
        reservation.stem + f"_attempt{repeat_index}.claim"
    )
    reservation_status = (
        "RESERVED_TWO_REPEAT_NO_RETRY" if repeat_count == 2 else "RESERVED_ONE_ATTEMPT_NO_RETRY"
    )
    binding = {
        "head": pkt["head"],
        "packet_sha256": packet_sha,
        "prepared_manifest_sha256": digest(d / "manifest.json"),
        "protocol_sha256": pkt["protocol_sha256"],
        "review_sha256": digest(review),
        "authorization_sha256": digest(authorization),
        "max_attempts": repeat_count,
        "capture_native_controller_processes_per_repeat_max": 1,
        "capture_native_controller_processes_campaign_max": repeat_count,
        "outputs": outputs,
    }
    with experiment_lock():
        if repeat_index == 1:
            if reservation.exists():
                raise ValueError("the campaign is already reserved; no retry")
            write_new(reservation, {**binding, "status": reservation_status})
        else:
            if not reservation.exists():
                raise ValueError("repeat 2 requires the existing campaign reservation")
            record = strict_json(reservation.read_text())
            if record != {**binding, "status": reservation_status}:
                raise ValueError("repeat campaign reservation identity mismatch")
            claim1 = reservation.with_name(reservation.stem + "_attempt1.claim")
            if not claim1.exists():
                raise ValueError("repeat 1 has no consumed one-shot claim")
            first = Path(outputs[0])
            first_admission = verify_manifest(first)
            first_result = strict_json((first / "RESULT.json").read_text())
            if (
                repeat_count != 2
                or first_admission.get("status") != "HORIZON_REACHED"
                or first_result.get("classification") != "HORIZON_REACHED"
                or first_result.get("canonical_physics_steps") != 1500
                or first_result.get("repeat_index") != 1
                or first_result.get("retry") != "none"
                or first_result.get("scientific_attempts") != 1
                or first_result.get("optimizer_calls", 0) > p["max_replan_calls"]
                or first_result.get("private_observed_upper_bound", run_limit + 1) > run_limit
                or first_result.get("private_reserved", run_limit + 1) > run_limit
                or first_result.get("canonical_evaluation", {}).get("verdict") != "PASS"
            ):
                raise ValueError("repeat 2 is blocked unless repeat 1 fully passes")
        write_new(
            claim,
            {
                "campaign_id": packet_sha,
                "repeat_index": repeat_index,
                "output": str(out),
            },
        )
        directory_fd = os.open(reservation.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    with (
        experiment_lock(),
        EvidenceRun(
            out,
            {
                "operation": "floor0_repeat_capture",
                "head": pkt["head"],
                "repeat_index": repeat_index,
                "campaign_id": packet_sha,
            },
        ) as run,
    ):
        plant = MujocoPlant(canon)
        validate_canonical_model(anchor, plant.model)
        launches = []

        def popen(argv, **kw):
            x = subprocess.Popen(argv, **kw)
            launches.append({"pid": x.pid, "argv": argv})
            return x

        native = NativeMJPCController(
            binary,
            timing,
            popen=popen,
            stderr_log_path=out / "native.stderr.log",
            diagnostic=(MODE, canon, out / "predictions.jsonl"),
            runtime_identity=side,
            fd_trace_path=out / "fd-trace.jsonl",
        )
        if (
            len(launches) != 1
            or native.ready.get("worker_count") != 4
            or native.ready.get("horizon_steps") != 36
            or native.ready.get("planner_dt") != 0.01
        ):
            native.close()
            raise ValueError("native process count/controller readiness drift")
        controller = StrictWarningController(
            PositionTargetControllerAdapter(
                native, native.actuator_spec, native.joint_names
            )
        )
        consumed = False

        def consume():
            nonlocal consumed
            if consumed:
                raise ValueError("one fresh process/attempt only")
            write_new(
                out / "attempt.json",
                {
                    "attempt": repeat_index,
                    "repeat_index": repeat_index,
                    "repeat_count": 2,
                    "campaign_id": packet_sha,
                    "head": pkt["head"],
                    "packet_sha256": packet_sha,
                    "first_sample_boundary": "first post-reset action before canonical step 1",
                },
            )
            consumed = True

        try:
            with (out / "raw.jsonl").open("x") as f:

                def emit(row):
                    f.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                    f.flush()

                with wall_deadline(p["wall_timeout_s"]):
                    outcome = run_aligned_episode(
                        plant, controller, task, info, timing, emit, consume
                    )
                f.flush()
                os.fsync(f.fileno())
            diag = native.diagnostics()
            write_new(out / "native-diagnostics.json", diag)
        finally:
            native.close()
        transport = diag.get("transport", {})
        if transport.get("stderr_bytes") or transport.get("stderr_read_error"):
            raise ValueError("native warning/error; stop the campaign")
        acc = diag.get("last_step", {}).get("diagnostic", {})
        upper = acc.get("fd_step_upper_bound_count", 0) + acc.get(
            "rollout_mj_step_count", 0
        )
        reserved = acc.get("private_step_upper_bound_reserved", 0)
        calls = acc.get("policy_id", 0)
        if (
            upper > reserved
            or reserved > run_limit
            or calls > p["max_replan_calls"]
            or (outcome["terminal_reason"] == "horizon" and calls != p["max_replan_calls"])
        ):
            raise ValueError("private/call budget or horizon count mismatch")
        rows = [strict_json(x) for x in (out / "raw.jsonl").read_text().splitlines()]
        result = {
            "classification": "HORIZON_REACHED"
            if outcome["terminal_reason"] == "horizon"
            else "SAFETY_STOP",
            "outcome": outcome,
            "canonical_evaluation": replay_aligned_rows(
                rows, task, timing.physics_period_s
            ),
            "canonical_physics_steps": plant.steps,
            "native_processes_started": len(launches),
            "stderr_bytes": transport["stderr_bytes"],
            "scientific_attempts": int(consumed),
            "optimizer_calls": acc.get("policy_id", 0),
            "private_observed_upper_bound": upper,
            "private_reserved": reserved,
            "r4_parent": pkt["parent_r4"],
            "parent_floor0_single": pkt["parent_floor0_single"],
            "repeat_index": repeat_index,
            "repeat_count": repeat_count,
            "campaign_id": packet_sha,
            "prediction_contact_semantics": p["prediction_contact_semantics"],
            "retry": "none",
            "one_shot_reservation": str(reservation),
            "one_shot_reservation_sha256": digest(reservation),
            "one_shot_claim": str(claim),
            "one_shot_claim_sha256": digest(claim),
        }
        write_new(out / "RESULT.json", result)
        run.result.update(
            status=result["classification"],
            repeat_index=repeat_index,
            campaign_id=packet_sha,
            native_processes_started=len(launches),
            stderr_bytes=transport["stderr_bytes"],
            canonical_physics_steps=plant.steps,
            scientific_attempts=int(consumed),
            optimizer_calls=result["optimizer_calls"],
            private_observed_upper_bound=upper,
            private_reserved=reserved,
            capability_status="DIAGNOSTIC_ONLY",
        )
    return str(out / "RESULT.json")



def analyze(capture_path, output):
    capture_path = Path(capture_path).resolve(strict=True)
    admission = verify_manifest(capture_path)
    if admission.get("status") not in ("HORIZON_REACHED", "SAFETY_STOP"):
        raise ValueError("capture status is not analyzable")
    result = strict_json((capture_path / "RESULT.json").read_text())
    rows = [
        strict_json(line)
        for line in (capture_path / "raw.jsonl").read_text().splitlines()
    ]
    actions = [row for row in rows if isinstance(row.get("action"), dict)]
    if not actions:
        raise ValueError("capture contains no action samples")
    names = tuple(actions[0]["target"]["joint_names"])
    if names != MOTOR_JOINTS:
        raise ValueError("unexpected source actuator joint order")
    per_joint = []
    for index, name in enumerate(names):
        saturated = []
        requested = []
        excess = []
        episodes = []
        active_start = None
        for row in actions:
            action = row["action"]
            if any(
                len(action.get(key, [])) != len(names)
                for key in ("ctrl", "total_unclipped", "saturated")
            ):
                raise ValueError("invalid torque action vector in capture")
            is_saturated = action["saturated"][index]
            if type(is_saturated) is not bool:
                raise ValueError("invalid saturation marker")
            req = float(action["total_unclipped"][index])
            applied = float(action["ctrl"][index])
            requested.append(abs(req))
            if is_saturated:
                saturated.append(row["tick"])
                excess.append(abs(req - applied))
                if active_start is None:
                    active_start = row["tick"]
            elif active_start is not None:
                end = row["tick"] - 1
                ticks = end - active_start + 1
                episodes.append(
                    {
                        "start_tick": active_start,
                        "end_tick": end,
                        "ticks": ticks,
                        "duration_s": ticks * 0.002,
                    }
                )
                active_start = None
        if active_start is not None:
            end = actions[-1]["tick"]
            ticks = end - active_start + 1
            episodes.append(
                {
                    "start_tick": active_start,
                    "end_tick": end,
                    "ticks": ticks,
                    "duration_s": ticks * 0.002,
                }
            )
        per_joint.append(
            {
                "joint": name,
                "peak_abs_requested_torque_Nm": max(requested),
                "max_excess_beyond_ctrlrange_Nm": max(excess, default=0.0),
                "saturated_action_ticks": len(saturated),
                "saturated_action_share_pct": 100.0 * len(saturated) / len(actions),
                "longest_consecutive_saturated_ticks": max(
                    (item["ticks"] for item in episodes), default=0
                ),
                "episodes": episodes,
            }
        )
    report = {
        "capture": str(capture_path),
        "capture_status": admission["status"],
        "result_sha256": digest(capture_path / "RESULT.json"),
        "raw_sha256": digest(capture_path / "raw.jsonl"),
        "physics_step_s": 0.002,
        "action_samples": len(actions),
        "terminal_reason": result.get("outcome", {}).get("terminal_reason"),
        "canonical_physics_steps": result.get("canonical_physics_steps"),
        "canonical_replay": result.get("canonical_evaluation"),
        "stderr_bytes": result.get("stderr_bytes"),
        "per_joint": per_joint,
        "total_saturated_action_ticks": sum(
            any(row["action"]["saturated"]) for row in actions
        ),
        "total_saturated_joint_ticks": sum(
            sum(row["action"]["saturated"]) for row in actions
        ),
        "saturation_threshold": "report only; no pass/fail threshold",
        "physics_steps_during_analysis": 0,
    }
    out = Path(output).resolve()
    if out.parent != (ROOT / "_runs").resolve() or out.exists():
        raise ValueError("analysis output must be a fresh _runs child")
    with EvidenceRun(
        out,
        {
            "operation": "floor_registration_saturation_analysis",
            "source_raw_sha256": report["raw_sha256"],
        },
    ) as run:
        write_new(out / "SATURATION_REPORT.json", report)
        run.result.update(
            status="ANALYZED",
            source_raw_sha256=report["raw_sha256"],
            action_samples=len(actions),
            physics_steps=0,
        )
    return str(out / "SATURATION_REPORT.json")



def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    q = s.add_parser("prepare")
    q.add_argument("--binary", type=Path, required=True)
    q.add_argument("--qualification", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    q.add_argument("--protocol-id", choices=("mjpc-floor-registration-repeatability-3s-v1", "mjpc-floor-registration-sustained-12s-v1"))
    q = s.add_parser("handshake")
    q.add_argument("--prepared", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    q = s.add_parser("capture")
    q.add_argument("--prepared", type=Path, required=True)
    q.add_argument("--review", type=Path, required=True)
    q.add_argument("--authorization", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    q.add_argument("--repeat-index", type=int, choices=(1, 2), required=True)
    q = s.add_parser("analyze")
    q.add_argument("--capture", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(
        prepare(a.binary, a.output, a.qualification, a.protocol_id)
        if a.cmd == "prepare"
        else handshake(a.prepared, a.output)
        if a.cmd == "handshake"
        else capture(a.prepared, a.review, a.authorization, a.output, a.repeat_index)
        if a.cmd == "capture"
        else analyze(a.capture, a.output)
    )


if __name__ == "__main__":
    main()
