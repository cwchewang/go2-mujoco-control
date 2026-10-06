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
TRANSPORT = "inprocess"


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


def check_original_identity(
    record, prepared_binding, expected_head, expected_fingerprint
):
    if record["head"] != expected_head or prepared_binding["head"] != expected_head:
        raise ValueError("original/corrected HEAD mismatch")
    if prepared_binding["qualification"]["fingerprint"] != expected_fingerprint:
        raise ValueError("original/corrected qualification fingerprint mismatch")


def check_original_gate(
    capture_path, verification_path, expected_head, expected_fingerprint
):
    import numpy as np

    if not capture_path or not verification_path:
        raise ValueError(
            "corrected diagnostic requires new original verified reproduction"
        )
    original = Path(capture_path).resolve()
    a = verify_bundle(original)
    binding = strict_json((original / "prepared-reference.json").read_text())
    check_original_identity(a, binding, expected_head, expected_fingerprint)
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
    with zero_step_guard():
        actual_summary = audit_capture(original)
    if summary != actual_summary:
        raise ValueError("original verification does not prove complete current checks")
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


def verify_entry(prepared, review_path, output):
    with experiment_lock() as lock, zero_step_guard():
        head = identity()
        p = verify_bundle(prepared)
        plan = spec.load_plan(Path(prepared) / "protocol.json")
        review = strict_json(Path(review_path).read_text())
        validate_review(review, head)
        if p["head"] != head or p["task_id"] != plan["raw"]["id"]:
            raise ValueError("entry prepared identity")
        validate_reference(p["qualification"])
        if (
            spec.model_audit() != p["model_audit"]
            or verify_controller(BINARY) != p["controller_identity"]
        ):
            raise ValueError("entry model/build drift")
        with EvidenceRun(
            Path(output), {"operation": "mjpc_diagnostic_verify_entry"}
        ) as run:
            preflight(
                lock,
                head,
                review,
                run.path / "preflight.json",
                run.path / "future_capture",
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
            write_new(run.path / "review.json", review)
            write_new(
                run.path / "prepared-reference.json",
                {
                    "path": str(Path(prepared).resolve()),
                    "manifest_sha256": digest(Path(prepared) / "manifest.json"),
                },
            )
            run.result.update(
                status="ENGINEERING_ADMITTED",
                head=head,
                canonical_physics_steps=0,
                private_optimizer_calls=0,
                scientific_attempts=0,
                formal_ledger_touched=False,
                production_entry="PREFLIGHT_VERIFIED",
            )
    return str(output)


def seal_preflight_failure(output, prepared, binding, review, auth, report, error):
    """The already-reserved task stays closed; no controller has been created."""
    with EvidenceRun(
        Path(output), {"operation": "mjpc_diagnostic_preflight_failure"}
    ) as run:
        run.result.update(
            head=prepared["head"],
            task_id=prepared["task_id"],
            scope="mjpc_single_arm_diagnostic",
            diagnostic_status="PREFLIGHT_FAILURE",
            terminal_stage="preflight",
            scientific_attempts=0,
            canonical_physics_steps=0,
            private_optimizer_calls=0,
            process_returncode=getattr(error, "returncode", None),
        )
        run.result["errors"].append(type(error).__name__ + ": " + str(error))
        write_new(run.path / "prepared-reference.json", binding)
        write_new(run.path / "review.json", review)
        write_new(run.path / "authorization.json", auth)
        write_new(
            run.path / "preflight-failure.json",
            {
                "exception_type": type(error).__name__,
                "message": str(error),
                "process_returncode": getattr(error, "returncode", None),
                "report": str(report),
                "attempt_consumed": False,
                "canonical_physics_steps": 0,
                "private_optimizer_calls": 0,
            },
        )
        for source, name in (
            (report, "preflight.json"),
            (report.parent / "preflight.stdout", "preflight.stdout"),
            (report.parent / "preflight.stderr", "preflight.stderr"),
        ):
            if source.is_file():
                shutil.copyfile(source, run.path / name)


def classify_terminal(oracle, outcome):
    reason = oracle["terminal_reason"]
    failure = oracle["first_failure"]
    if reason != outcome["terminal_reason"]:
        raise ValueError("canonical terminal reason mismatch")
    if failure is not None:
        if (
            failure["tick"] != outcome["steps"]
            or failure["reason"] != reason
            or reason in ("horizon", "incomplete_evidence")
        ):
            raise ValueError("canonical first safety failure mismatch")
        return "SAFETY_STOP"
    if reason == "horizon":
        return "HORIZON_REACHED"
    raise ValueError("incomplete evidence without a physical safety failure")


def capture(prepared, review_path, authorization_path, output):
    with experiment_lock() as lock:
        p = verify_bundle(prepared)
        # These identifiers are permanently closed across every checkout. The
        # sealed A consumed its sole attempt and failed B's reproduction gate.
        # A worktree-local empty ledger cannot reopen either historical scope.
        if p.get("task_id") in {
            "mjpc-adaptation-original-3s-v1",
            "mjpc-adaptation-corrected-3s-v1",
        }:
            raise ValueError(
                "mjpc adaptation v1 permanently closed: A CLOSED_NO_RETRY; "
                "B NOT_RUN_REPRODUCTION_GATE_FAILED; use a new prospective task"
            )
        plan = spec.load_plan(Path(prepared) / "protocol.json")
        head = identity()
        review = strict_json(Path(review_path).read_text())
        auth = strict_json(Path(authorization_path).read_text())
        validate_review(review, head)
        binding = dict(
            p,
            prepared_path=str(Path(prepared).resolve()),
            prepared_manifest_sha256=digest(Path(prepared) / "manifest.json"),
        )
        validate_authorization(auth, binding)
        if (
            p["head"] != head
            or p["task_id"] != plan["raw"]["id"]
            or auth.get("task_id") != p["task_id"]
            or type(auth.get("canonical_steps_max")) is not int
            or auth.get("canonical_steps_max") != 1500
            or type(auth.get("private_step_upper_bound_max")) is not int
            or auth.get("private_step_upper_bound_max") != spec.LIMIT
        ):
            raise ValueError("START task/private/canonical budget mismatch")
        if plan["raw"]["mode"] == "corrected":
            check_original_gate(
                auth.get("original_capture"),
                auth.get("original_verification"),
                p["head"],
                p["qualification"]["fingerprint"],
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
        try:
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
        except BaseException as exc:
            seal_preflight_failure(output, p, binding, review, auth, report, exc)
            raise
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

            last_row = None
            try:
                with (run.path / "raw.jsonl").open("x") as stream:

                    def emit(row):
                        nonlocal last_row
                        last_row = row
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
                diagnostic_status=classify_terminal(
                    {
                        "terminal_reason": last_row["terminal_reason"],
                        "first_failure": None
                        if last_row["failure"] is None
                        else {"tick": last_row["tick"], "reason": last_row["failure"]},
                    },
                    outcome,
                ),
                capability_status="NOT_CLAIMED",
            )
        return str(output)


def validate_capture_metadata(record, p, plan, binding, review, auth):
    if (
        p["head"] != record["head"]
        or p["task_id"] != record["task_id"]
        or record["task_id"] != plan["raw"]["id"]
        or p["protocol_sha256"] != plan["protocol_sha256"]
        or p["max_attempts"] != 1
        or p["canonical_steps_max"] != 1500
        or p["private_step_upper_bound_max"] != spec.LIMIT
    ):
        raise ValueError("prepared task/head/protocol/budget binding")
    validate_review(review, record["head"])
    validate_authorization(auth, binding)
    if (
        auth.get("task_id") != p["task_id"]
        or type(auth.get("canonical_steps_max")) is not int
        or auth["canonical_steps_max"] != 1500
        or type(auth.get("private_step_upper_bound_max")) is not int
        or auth["private_step_upper_bound_max"] != spec.LIMIT
    ):
        raise ValueError("START diagnostic task/budget binding")


def verify_capture_binding(directory, record, plan):
    binding = strict_json((directory / "prepared-reference.json").read_text())
    prepared = Path(binding["prepared_path"]).resolve()
    p = verify_bundle(prepared)
    expected = dict(
        p,
        prepared_path=str(prepared),
        prepared_manifest_sha256=digest(prepared / "manifest.json"),
    )
    if binding != expected:
        raise ValueError("prepared reference binding")
    if digest(prepared / "protocol.json") != p["protocol_sha256"]:
        raise ValueError("prepared protocol digest binding")
    validate_capture_metadata(
        record,
        p,
        plan,
        binding,
        strict_json((directory / "review.json").read_text()),
        strict_json((directory / "authorization.json").read_text()),
    )
    auth = strict_json((directory / "authorization.json").read_text())
    report = strict_json((directory / "preflight.json").read_text())
    if (
        report.get("pass") is not True
        or report["identity"]["actual_head"] != record["head"]
        or report["experiment_id"] != p["task_id"]
        or report["qualification"] != p["qualification"]
        or report["sol_review"]["approved_head"] != record["head"]
    ):
        raise ValueError("preflight exact-head/qualification binding")
    validate_reference(p["qualification"])
    if (
        strict_json((directory / "model-audit.json").read_text()) != p["model_audit"]
        or p["model_audit"] != spec.model_audit()
        or strict_json((directory / "controller-identity.json").read_text())
        != p["controller_identity"]
        or verify_controller(BINARY) != p["controller_identity"]
    ):
        raise ValueError("capture model/build mapping binding")
    if plan["raw"]["mode"] == "corrected":
        check_original_gate(
            auth.get("original_capture"),
            auth.get("original_verification"),
            p["head"],
            p["qualification"]["fingerprint"],
        )


def validate_prediction(pred, row, mode, model):
    import mujoco as mj
    import numpy as np
    from .contracts import vector

    account = row["controller_diagnostics"]["controller"]["last_step"]["diagnostic"]
    policy = account["policy_id"]
    if (
        type(pred["anchor_time_s"]) not in (int, float)
        or not np.isfinite(pred["anchor_time_s"])
        or type(pred.get("policy_id")) is not int
        or pred["policy_id"] != policy
        or pred["anchor_time_s"] != row["sim_time_s"]
        or pred["mode"] != mode
        or pred["optimization_model_id"] != mode + "-go2-soft-v1"
        or type(pred["candidate_id"]) is not int
        or not 0 <= pred["candidate_id"] < 10
        or len(pred["states"]) != 36
        or pred["contact_semantics"]
        != "selected_states_forward_reconstruction_smoothed_private_model"
    ):
        raise ValueError("prediction identity/time/model/candidate mismatch")
    budget = pred["private_accounting"]
    if set(budget) != {
        "rollout_mj_step_count",
        "fd_step_upper_bound_count",
        "fd_call_count",
        "reserved_step_upper_bound",
    } or any(type(v) is not int or v < 0 for v in budget.values()):
        raise ValueError("prediction accounting types")
    if (
        any(
            budget[k] != account[k]
            for k in (
                "rollout_mj_step_count",
                "fd_step_upper_bound_count",
                "fd_call_count",
            )
        )
        or budget["reserved_step_upper_bound"]
        != account["private_step_upper_bound_reserved"]
    ):
        raise ValueError("prediction/actual response accounting mismatch")
    q = vector(row["qpos"], 19, "actual qpos")
    v = vector(row["qvel"], 18, "actual qvel")
    order = [10, 11, 12, 7, 8, 9, 16, 17, 18, 13, 14, 15]
    velocity = [9, 10, 11, 6, 7, 8, 15, 16, 17, 12, 13, 14]
    if not np.allclose(
        pred["states"][0]["qpos"], np.r_[q[:7], q[order]], atol=1e-9, rtol=0
    ) or not np.allclose(
        pred["states"][0]["qvel"], np.r_[v[:6], v[velocity]], atol=1e-9, rtol=0
    ):
        raise ValueError("selected prediction not anchored to delivered state")
    d = mj.MjData(model)
    for k, state in enumerate(pred["states"]):
        if type(state["time_s"]) not in (int, float) or not np.isfinite(
            state["time_s"]
        ):
            raise ValueError("prediction knot time type")
        if abs(state["time_s"] - (pred["anchor_time_s"] + 0.01 * k)) > 1e-8:
            raise ValueError("prediction knot clock")
        d.qpos[:] = vector(state["qpos"], 19, "prediction qpos")
        d.qvel[:] = vector(state["qvel"], 18, "prediction qvel")
        d.ctrl[:] = vector(state["nominal_position_action"], 12, "prediction action")
        d.time = state["time_s"]
        mj.mj_forward(model, d)
        active = [c for c in d.contact if c.efc_address >= 0]
        contacts = state["active_contacts"]
        if not isinstance(contacts, list) or len(contacts) != len(active):
            raise ValueError("active contact reconstruction count")
        for saved, actual in zip(contacts, active):
            ids = saved["geom_ids"]
            if (
                not isinstance(ids, list)
                or len(ids) != 2
                or any(type(g) is not int or not 0 <= g < model.ngeom for g in ids)
                or ids != [int(actual.geom1), int(actual.geom2)]
                or saved["geom_names"]
                != [mj.mj_id2name(model, mj.mjtObj.mjOBJ_GEOM, g) or "" for g in ids]
                or type(saved["distance_m"]) not in (int, float)
                or not np.isfinite(saved["distance_m"])
                or abs(saved["distance_m"] - actual.dist) > 1e-9
            ):
                raise ValueError("active contact geometry/name/distance mapping")


def audit_capture(capture_dir):
    import numpy as np
    from .evaluator import CanonicalEvaluator
    from .mjpc_diagnostic import validate_budget_record

    directory = Path(capture_dir).resolve()
    record = verify_bundle(directory)
    plan = spec.load_plan(directory / "protocol.json")
    verify_capture_binding(directory, record, plan)
    ledger = ROOT / "_runs/substrate_attempts" / plan["raw"]["id"]
    if set(p.name for p in ledger.iterdir()) != {"campaign.json", "claim.json"}:
        raise ValueError("real external ledger membership")
    campaign = strict_json((ledger / "campaign.json").read_text())
    claim = strict_json((ledger / "claim.json").read_text())
    if (
        campaign["task_id"] != plan["raw"]["id"]
        or campaign["max_attempts"] != 1
        or campaign["private_step_upper_bound_max"] != spec.LIMIT
        or claim["boundary"] != "first_post_handoff_state_control_sample"
        or campaign["output"] != str(directory)
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
    expected_status = classify_terminal(oracle, outcome)
    if (
        record["diagnostic_status"] != expected_status
        or record["capability_status"] != "NOT_CLAIMED"
    ):
        raise ValueError("diagnostic outcome/classification binding")
    last = None
    by_id = {}
    for tick, row in enumerate(rows[:-1]):
        if row["tick"] != tick or abs(row["sim_time_s"] - tick * 0.002) > 1e-9:
            raise ValueError("actual raw clock/order")
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
        if not (
            np.array_equal(target["kp"], np.full(12, 60.0))
            and np.array_equal(target["kd"], np.full(12, 5.0))
            and np.array_equal(target["feedforward"], np.zeros(12))
            and np.array_equal(target["velocity_target"], np.zeros(12))
        ):
            raise ValueError("source position PD semantics drift")
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
    model = spec.optimization_model(plan["raw"]["mode"])
    for i, pred in enumerate(predictions, 1):
        validate_prediction(pred, by_id[i], plan["raw"]["mode"], model)
    final = strict_json((directory / "last-controller-diagnostics.json").read_text())
    if final["last_step"]["diagnostic"] != last:
        raise ValueError("last actual response accounting mismatch")
    if rows[-1]["tick"] != len(rows) - 1:
        raise ValueError("terminal raw tick")
    return {
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
        "prepared_review_start_checked": True,
        "active_contacts_reconstructed": True,
        "prediction_actual_accounting_checked": True,
    }


def verify_capture(capture_dir, output):
    with zero_step_guard():
        summary = audit_capture(capture_dir)
    with EvidenceRun(Path(output), {"operation": "mjpc_diagnostic_raw_verify"}) as run:
        write_new(run.path / "verified-summary.json", summary)
        run.result.update(status="ENGINEERING_ADMITTED", verification="VERIFIED")
    return str(output)


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="op", required=True)
    a = s.add_parser("prepare")
    a.add_argument("--output", type=Path, required=True)
    a.add_argument("--protocol", type=Path, required=True)
    a.add_argument("--qualification", type=Path, required=True)
    a = s.add_parser("verify-entry")
    for name in ["prepared", "review", "output"]:
        a.add_argument("--" + name, type=Path, required=True)
    a = s.add_parser("capture")
    for name in ["prepared", "review", "authorization", "output"]:
        a.add_argument("--" + name, type=Path, required=True)
    a = s.add_parser("verify")
    a.add_argument("--capture", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.op == "verify-entry":
        result = verify_entry(a.prepared, a.review, a.output)
    elif a.op == "prepare":
        result = prepare(a.output, a.protocol, a.qualification)
    elif a.op == "capture":
        result = capture(a.prepared, a.review, a.authorization, a.output)
    else:
        result = verify_capture(a.capture, a.output)
    print(json.dumps({"output": result}))


if __name__ == "__main__":
    main()
