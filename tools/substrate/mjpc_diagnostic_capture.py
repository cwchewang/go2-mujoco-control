"""Two independent single-attempt diagnostics; exact-head reviews precede capture."""

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import mjpc_diagnostic as spec
from .aligned_episode import run_aligned_episode
from .build_identity import verify_controller
from .contracts import PositionTargetControllerAdapter
from .episode import MujocoPlant
from .guards import wall_deadline, zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_bundle,
    write_new,
)
from .launch import preflight
from .native_mjpc import NativeMJPCController
from .qualification import validate, validate_reference
from .readiness import validate_authorization, validate_review

ROOT = spec.ROOT
BINARY = ROOT / ".substrate/headless-reliable/go2_mjpc_controller"


def identity():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

    if git("branch", "--show-current") != spec.BRANCH or git("status", "--porcelain"):
        raise ValueError("diagnostic needs exact clean named branch")
    return git("rev-parse", "HEAD")


def prepare(output, protocol, qualification):
    with experiment_lock(), zero_step_guard():
        head = identity()
        plan = spec.load_plan(protocol)
        q = validate(qualification)
        build = verify_controller(BINARY)
        audit = spec.model_audit()
        with EvidenceRun(Path(output), {"operation": "mjpc_diagnostic_prepare"}) as run:
            shutil.copyfile(protocol, run.path / "protocol.json")
            write_new(run.path / "model-audit.json", audit)
            write_new(run.path / "controller-identity.json", build)
            plant = MujocoPlant(ROOT / plan["scenario"].scene)
            write_new(run.path / "initial-state.json", plant.snapshot(0))
            if plant.steps or plant.data.time or identity() != head:
                raise ValueError("prepare advanced physics/identity")
            run.result.update(
                status="ENGINEERING_ADMITTED",
                head=head,
                scope="mjpc_single_arm_diagnostic",
                task_id=plan["raw"]["id"],
                protocol_sha256=digest(protocol),
                max_attempts=1,
                canonical_steps_max=1500,
                private_step_upper_bound_max=spec.LIMIT,
                model_audit=audit,
                controller_identity=build,
                qualification=q,
                canonical_physics_steps=0,
                private_optimizer_calls=0,
                readiness="AWAITING_EXACT_HEAD_REVIEWS_AND_BOUND_START",
            )
    return str(output)


def check_original_gate(capture_path, verification_path):
    import numpy as np

    if not capture_path or not verification_path:
        raise ValueError(
            "corrected diagnostic requires new original verified reproduction"
        )
    original = Path(capture_path).resolve()
    a = verify_bundle(original)
    v = verify_bundle(verification_path)
    summary = strict_json(
        (Path(verification_path) / "verified-summary.json").read_text()
    )
    if (
        a["task_id"] != "mjpc-adaptation-original-3s-v1"
        or v.get("verification") != "VERIFIED"
        or summary["capture"] != str(original)
        or summary["capture_manifest_sha256"] != digest(original / "manifest.json")
    ):
        raise ValueError("original admission not source-bound")
    old = (
        ROOT
        / "example/cpp/experiments/_runs/shared_baseline_probes_v1/run_20261002T085338452324Z/mjpc_baseline_1.jsonl"
    )
    if (
        digest(old)
        != "e5f760c54a57d12e8da6150972cb084414c3f9d84f1827ac9582b292532a3841"
    ):
        raise ValueError("old reference changed")
    first = [
        strict_json(line) for line in (original / "raw.jsonl").read_text().splitlines()
    ]
    second = [strict_json(line) for line in old.read_text().splitlines()]
    if len(first) != 1288 or first[-1]["terminal_reason"] != "nonfoot_contact":
        raise ValueError(
            "original does not reproduce known stop; inspect instrumentation before B"
        )
    for x, y in zip(first, second):
        for name in ("qpos", "qvel"):
            if not np.allclose(x[name], y[name], rtol=0, atol=1e-9):
                raise ValueError(
                    "original state prefix differs; do not launch corrected"
                )
        if x["action"] is not None and not np.allclose(
            x["action"]["ctrl"], y["action"]["ctrl"], rtol=0, atol=1e-9
        ):
            raise ValueError("original applied control differs")
        if (
            x["supports"] != y["supports"]
            or x["forbidden_contacts"] != y["forbidden_contacts"]
        ):
            raise ValueError("original contact semantics differ")
    return True


def capture(prepared, review_path, authorization_path, output):
    with experiment_lock() as lock:
        p = verify_bundle(prepared)
        plan = spec.load_plan(Path(prepared) / "protocol.json")
        head = identity()
        review = strict_json(Path(review_path).read_text())
        auth = strict_json(Path(authorization_path).read_text())
        validate_review(review, head)
        binding = dict(
            p, prepared_manifest_sha256=digest(Path(prepared) / "manifest.json")
        )
        validate_authorization(auth, binding)
        if (
            p["head"] != head
            or p["task_id"] != plan["raw"]["id"]
            or auth.get("task_id") != p["task_id"]
            or auth.get("canonical_steps_max") != 1500
            or auth.get("private_step_upper_bound_max") != spec.LIMIT
        ):
            raise ValueError("START task/private/canonical budget mismatch")
        if plan["raw"]["mode"] == "corrected":
            check_original_gate(
                auth.get("original_capture"), auth.get("original_verification")
            )
        validate_reference(p["qualification"])
        if (
            spec.model_audit() != p["model_audit"]
            or verify_controller(BINARY) != p["controller_identity"]
        ):
            raise ValueError("diagnostic model/build identity drift")
        ledger = ROOT / "_runs/substrate_attempts" / p["task_id"]
        if ledger.exists() or Path(output).exists():
            raise ValueError("closed/existing diagnostic cannot retry")
        # Reserve unique task before fresh preflight: failure permanently closes it.
        ledger.mkdir(parents=True, exist_ok=False)
        write_new(
            ledger / "campaign.json",
            {
                "task_id": p["task_id"],
                "head": head,
                "output": str(Path(output).resolve()),
                "max_attempts": 1,
                "private_step_upper_bound_max": spec.LIMIT,
            },
        )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        report = ROOT / "_runs/mjpc_diagnostic_preflight" / stamp / "report.json"
        report.parent.mkdir(parents=True, exist_ok=False)
        from tools.research.preflight import DEFAULT_PROCESS_NAMES, find_processes

        if find_processes(DEFAULT_PROCESS_NAMES + ("go2_mjpc_controller",)):
            raise ValueError("stale native/runtime process")
        preflight(
            lock,
            head,
            review,
            report,
            output,
            {
                "configuration": {
                    "branch": spec.BRANCH,
                    "diff_base": plan["raw"]["parent"],
                }
            },
            p["qualification"],
            runner=Path(__file__),
            experiment_id=p["task_id"],
        )
        with EvidenceRun(
            Path(output), {"operation": "mjpc_single_arm_diagnostic"}
        ) as run:
            for n in ("protocol.json", "model-audit.json", "controller-identity.json"):
                shutil.copyfile(Path(prepared) / n, run.path / n)
            write_new(run.path / "review.json", review)
            write_new(run.path / "authorization.json", auth)
            write_new(run.path / "prepared-reference.json", binding)
            shutil.copyfile(report, run.path / "preflight.json")
            run.result.update(
                head=head,
                task_id=p["task_id"],
                scientific_attempts=0,
                canonical_physics_steps=0,
                scope="mjpc_single_arm_diagnostic",
            )
            plant = MujocoPlant(ROOT / plan["scenario"].scene)
            native = NativeMJPCController(
                BINARY,
                plan["controllers"]["mjpc"]["timing"],
                stderr_log_path=run.path / "native.stderr.log",
                diagnostic=(
                    plan["raw"]["mode"],
                    ROOT / plan["scenario"].scene,
                    run.path / "predictions.jsonl",
                ),
            )
            controller = PositionTargetControllerAdapter(
                native, native.actuator_spec, native.joint_names
            )

            def consume():
                write_new(
                    ledger / "claim.json",
                    {
                        "task_id": p["task_id"],
                        "head": head,
                        "raw": str((run.path / "raw.jsonl").resolve()),
                        "boundary": "first_post_handoff_state_control_sample",
                    },
                )
                run.result["scientific_attempts"] = 1

            try:
                with (run.path / "raw.jsonl").open("x") as stream:

                    def emit(row):
                        stream.write(
                            json.dumps(row, allow_nan=False, sort_keys=True) + "\n"
                        )
                        stream.flush()

                    with wall_deadline(300):
                        outcome = run_aligned_episode(
                            plant,
                            controller,
                            plan["task"],
                            plan["controllers"]["mjpc"]["information"],
                            plan["controllers"]["mjpc"]["timing"],
                            emit,
                            consume,
                        )
                    os.fsync(stream.fileno())
            finally:
                native.close()
                run.result["canonical_physics_steps"] = plant.steps
                write_new(
                    run.path / "last-controller-diagnostics.json", native.diagnostics()
                )
            write_new(run.path / "outcome.json", outcome)
            run.result.update(
                status="ENGINEERING_ADMITTED",
                diagnostic_status="SAFETY_STOP"
                if outcome["terminal_reason"] != "horizon"
                else "HORIZON_REACHED",
                capability_status="NOT_CLAIMED",
            )
        return str(output)


def verify_capture(capture_dir, output):
    import numpy as np
    from .evaluator import CanonicalEvaluator
    from .mjpc_diagnostic import validate_budget_record

    directory = Path(capture_dir).resolve()
    record = verify_bundle(directory)
    plan = spec.load_plan(directory / "protocol.json")
    ledger = ROOT / "_runs/substrate_attempts" / plan["raw"]["id"]
    if set(p.name for p in ledger.iterdir()) != {"campaign.json", "claim.json"}:
        raise ValueError("real external ledger membership")
    campaign = strict_json((ledger / "campaign.json").read_text())
    claim = strict_json((ledger / "claim.json").read_text())
    if (
        campaign["output"] != str(directory)
        or campaign["head"] != record["head"]
        or claim["task_id"] != plan["raw"]["id"]
        or claim["head"] != record["head"]
        or claim["raw"] != str(directory / "raw.jsonl")
        or record["scientific_attempts"] != 1
    ):
        raise ValueError("external claim binding")
    rows = [
        strict_json(line) for line in (directory / "raw.jsonl").read_text().splitlines()
    ]
    predictions = [
        strict_json(line)
        for line in (directory / "predictions.jsonl").read_text().splitlines()
    ]
    if len(rows) != record["canonical_physics_steps"] + 1 or not 1 < len(rows) <= 1501:
        raise ValueError("frame/budget accounting")
    oracle = CanonicalEvaluator(plan["task"], 0.002).evaluate(rows).as_dict()
    outcome = strict_json((directory / "outcome.json").read_text())
    if (
        oracle["terminal_reason"] != outcome["terminal_reason"]
        or outcome["steps"] != len(rows) - 1
    ):
        raise ValueError("canonical safety replay mismatch")
    last = None
    by_id = {}
    for row in rows[:-1]:
        if row["tick"] != len(by_id) * 10 and row["tick"] % 10 == 0:
            raise ValueError("planning clock shifted")
        target = row["target"]
        names = [
            leg + "_" + joint + "_joint"
            for leg in ("FR", "FL", "RR", "RL")
            for joint in ("hip", "thigh", "calf")
        ]
        if target["joint_names"] != names:
            raise ValueError("applied target joint identity")
        q = np.asarray(row["qpos"])[[10, 11, 12, 7, 8, 9, 16, 17, 18, 13, 14, 15]]
        dq = np.asarray(row["qvel"])[[9, 10, 11, 6, 7, 8, 15, 16, 17, 12, 13, 14]]
        pd = np.asarray(target["kp"]) * (
            np.asarray(target["position_target"]) - q
        ) + np.asarray(target["kd"]) * (np.asarray(target["velocity_target"]) - dq)
        total = pd + np.asarray(target["feedforward"])
        limits = np.array([40, 40, 45.43] * 4)
        if not (
            np.allclose(pd, row["action"]["pd"], rtol=0, atol=1e-9)
            and np.allclose(
                np.clip(total, -limits, limits),
                row["action"]["ctrl"],
                rtol=0,
                atol=1e-9,
            )
        ):
            raise ValueError("independent PD/resolved torque replay")
        value = row["controller_diagnostics"]["controller"]["last_step"]["diagnostic"]
        last = validate_budget_record(value, row["tick"], last)
        if row["tick"] % 10 == 0:
            by_id[value["policy_id"]] = row
    if len(predictions) != len(by_id):
        raise ValueError("missing/extra selected prediction")
    for i, pred in enumerate(predictions, 1):
        row = by_id[i]
        if (
            pred["policy_id"] != i
            or pred["anchor_time_s"] != row["sim_time_s"]
            or pred["mode"] != plan["raw"]["mode"]
            or pred["optimization_model_id"] != plan["raw"]["mode"] + "-go2-soft-v1"
            or pred["candidate_id"] < 0
            or len(pred["states"]) != 36
            or pred["contact_semantics"]
            != "selected_states_forward_reconstruction_smoothed_private_model"
        ):
            raise ValueError("prediction identity/time/model mismatch")
        q = np.asarray(row["qpos"])
        v = np.asarray(row["qvel"])
        order = [10, 11, 12, 7, 8, 9, 16, 17, 18, 13, 14, 15]
        velocity = [9, 10, 11, 6, 7, 8, 15, 16, 17, 12, 13, 14]
        if not np.allclose(
            pred["states"][0]["qpos"], np.r_[q[:7], q[order]], atol=1e-9, rtol=0
        ) or not np.allclose(
            pred["states"][0]["qvel"], np.r_[v[:6], v[velocity]], atol=1e-9, rtol=0
        ):
            raise ValueError("selected prediction not anchored to delivered state")
        for k, state in enumerate(pred["states"]):
            if abs(state["time_s"] - (pred["anchor_time_s"] + 0.01 * k)) > 1e-8:
                raise ValueError("prediction knot clock")
            for name, size in [
                ("qpos", 19),
                ("qvel", 18),
                ("nominal_position_action", 12),
            ]:
                values = np.asarray(state[name])
                if values.shape != (size,) or not np.isfinite(values).all():
                    raise ValueError("invalid prediction state/action")
        a = pred["private_accounting"]
        if (
            a["rollout_mj_step_count"] + a["fd_step_upper_bound_count"]
            > a["reserved_step_upper_bound"]
            or a["reserved_step_upper_bound"] != i * 4096
        ):
            raise ValueError("prediction budget record")
    with EvidenceRun(Path(output), {"operation": "mjpc_diagnostic_raw_verify"}) as run:
        write_new(
            run.path / "verified-summary.json",
            {
                "capture": str(directory),
                "capture_manifest_sha256": digest(directory / "manifest.json"),
                "status": "VERIFIED",
                "external_ledger_checked": True,
                "classification": record["diagnostic_status"],
                "scientific_attempts": 1,
                "canonical_steps": len(rows) - 1,
                "selected_predictions": len(predictions),
                "private_accounting": last,
                "verification_integration_steps": 0,
            },
        )
        run.result.update(status="ENGINEERING_ADMITTED", verification="VERIFIED")
    return str(output)


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="op", required=True)
    a = s.add_parser("prepare")
    a.add_argument("--output", type=Path, required=True)
    a.add_argument("--protocol", type=Path, required=True)
    a.add_argument("--qualification", type=Path, required=True)
    a = s.add_parser("capture")
    for name in ["prepared", "review", "authorization", "output"]:
        a.add_argument("--" + name, type=Path, required=True)
    a = s.add_parser("verify")
    a.add_argument("--capture", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.op == "prepare":
        result = prepare(a.output, a.protocol, a.qualification)
    elif a.op == "capture":
        result = capture(a.prepared, a.review, a.authorization, a.output)
    else:
        result = verify_capture(a.capture, a.output)
    print(json.dumps({"output": result}))


if __name__ == "__main__":
    main()
