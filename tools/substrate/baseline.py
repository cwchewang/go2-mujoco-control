"""Source-policy baseline: reviewed preparation, bounded capture, offline verification."""

import argparse
import json
import os
from pathlib import Path
import time

from .admit import ROOT
from .baseline_episode import (
    Plant,
    UnsupportedSceneError,
    analyze,
    command_at,
    expected_reference_digest,
    enforce_reference_digest,
    episode,
    make_policy,
    reference_inputs,
    repeat_reference,
    stop_after,
)
from .environment import verify_environment
from .guards import wall_deadline, zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_bundle,
    write_new,
)
from .launch import CHECKPOINT, current_identity, preflight, setup_runtime
from .model import dependency_manifest, physical_fingerprint
from .qualification import validate, validate_reference
from .readiness import validate_authorization, validate_review
from .task import load_task

TASK = ROOT / "tools/substrate/tasks/rl_source_v1.json"
TRANSPORT = "inprocess"


class IntegrityStopError(RuntimeError):
    """Source or prepared evidence changed after a campaign was qualified."""


class PreflightFailureError(RuntimeError):
    """A required review, qualification, identity, or fresh preflight did not pass."""


def validate_source_identity(protocol, reference_lock, source_lock):
    identity = protocol.get("source_identity")
    if identity is None:
        return
    locked_source = source_lock["rl"]
    expected = {
        "commit": reference_lock["commit"],
        "checkpoint": locked_source["checkpoint"],
        "checkpoint_sha256": locked_source["sha256"],
    }
    if identity != expected:
        raise ValueError("protocol source identity differs from source locks")


def validate_capability_protocol(protocol):
    if protocol.get("id") != "rl-capability-map-v1" or protocol.get("schema") != 2:
        raise ValueError("unsupported capability-map protocol")
    cases = protocol.get("cases", [])
    if len(cases) != protocol.get("max_attempts"):
        raise ValueError("capability-map attempt budget must equal case count")
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)) or not ids or ids[0] != "flat_reference":
        raise ValueError("capability-map cases must have unique IDs and lead with reference")
    expected_reference_digest(protocol)
    ranges = protocol["engineering_probe_envelope"]
    bounds = {
        "vx": ranges["vx_mps"],
        "vy": ranges["vy_mps"],
        "wz": ranges["wz_rps"],
    }
    valid_axes = set(bounds)
    for index, case in enumerate(cases):
        if case.get("adapter") is not True or case.get("reset") != "shared_home":
            raise ValueError("all capability-map cases must preserve shared deployment")
        if not case.get("scene_geoms") or len(case["scene_geoms"]) != len(
            set(case["scene_geoms"])
        ):
            raise ValueError("each capability-map scene needs unique collision geom names")
        axes = case.get("track_axes")
        if not axes or len(axes) != len(set(axes)) or not set(axes) <= valid_axes:
            raise ValueError("invalid capability-map tracking axes")
        commands = case.get("commands", [])
        if not commands or any(len(row) != 4 for row in commands):
            raise ValueError("capability-map commands must be [tick, vx, vy, wz]")
        ticks = [row[0] for row in commands]
        if (
            ticks[0] != 0
            or ticks != sorted(set(ticks))
            or ticks[-1] >= case["horizon_ticks"]
        ):
            raise ValueError("capability-map command schedule is not bounded and ordered")
        if case.get("flat_probe") and index > 0:
            for row in commands:
                for axis, value in zip(("vx", "vy", "wz"), row[1:]):
                    if not bounds[axis][0] <= value <= bounds[axis][1]:
                        raise ValueError("flat probe exceeds source-configured probe envelope")
        if index > 0 and case.get("requires") != ["flat_reference"]:
            raise ValueError("all post-sentinel cases must depend on the flat reference")
        goal = case.get("terrain_goal")
        if goal is not None and not (
            0 <= goal["terrain_x_min"] < goal["terrain_x_max"]
            and goal["base_clearance_m"] > 0
            and goal["foot_clearance_m"] > 0
            and goal["route_lateral_max_m"] > 0
            and goal["hold_ticks"] > 0
        ):
            raise ValueError("invalid terrain crossing goal")
    if protocol.get("retry") != "none":
        raise ValueError("capability-map protocol must forbid retries")
    if protocol.get("progression") != "performance_continue_safety_integrity_stop":
        raise ValueError("capability-map progression must retain performance outcomes")


def campaign_characterized(attempts, protocol):
    statuses = [item["status"] for item in attempts]
    if all(status in ("PASS", "PERFORMANCE_FAIL") for status in statuses):
        return True
    if protocol["progression"] == "first_nonpass_stop":
        for index, status in enumerate(statuses):
            if status == "PERFORMANCE_FAIL":
                return all(later == "NOT_RUN" for later in statuses[index + 1 :])
            if status != "PASS":
                return False
    return False


def inputs(protocol):
    reference, lock = reference_inputs(ROOT)
    source_lock = strict_json((ROOT / "tools/substrate/sources.lock.json").read_text())
    validate_source_identity(protocol, lock, source_lock)
    result = {
        (reference / n).relative_to(ROOT).as_posix(): sha
        for n, sha in lock["files"].items()
    }
    for case in protocol["cases"]:
        result.update(dependency_manifest(ROOT / case["scene"], ROOT)["files"])
    for name in (
        ".substrate/rl/policy.pt",
        "tools/substrate/rl_reference.lock.json",
        "tools/substrate/sources.lock.json",
    ):
        result[name] = digest(ROOT / name)
    locked_source = source_lock["rl"]
    expected = locked_source["sha256"]
    if digest(CHECKPOINT) != expected:
        raise ValueError("checkpoint not source locked")
    if len(protocol["cases"]) != protocol["max_attempts"] or len(
        {c["id"] for c in protocol["cases"]}
    ) != len(protocol["cases"]):
        raise ValueError("case budget/identity mismatch")
    seen = set()
    for case in protocol["cases"]:
        reference_case = repeat_reference(case)
        if reference_case is not None and reference_case not in seen:
            raise ValueError("repeat reference must name a preceding case")
        seen.add(case["id"])
    if protocol.get("schema") == 2:
        validate_capability_protocol(protocol)
    if protocol["progression"] not in (
        "first_nonpass_stop",
        "performance_continue_safety_integrity_stop",
    ):
        raise ValueError("unknown campaign progression")
    return result


def fresh_preflight(lock, head, review, report, fresh, task, qualification, protocol):
    try:
        preflight(
            lock,
            head,
            review,
            report,
            fresh,
            task,
            qualification,
            runner=Path(__file__),
            experiment_id=protocol["id"],
        )
    except UnsupportedSceneError:
        raise
    except Exception as exc:
        raise PreflightFailureError("fresh execution preflight did not pass") from exc


def validate_snapshot(path, expected_manifest):
    try:
        verify_bundle(path)
    except Exception as exc:
        raise IntegrityStopError("prepared snapshot bundle verification failed") from exc
    if digest(path / "manifest.json") != expected_manifest:
        raise IntegrityStopError("prepared snapshot changed")


def prepare_probe(plant, policy, case, command):
    initial = plant.snapshot(0)
    action = policy.act(plant.observe(), command)
    target = action.position_target if case["adapter"] else action[1]
    plant.control(target)
    if plant.steps or plant.data.time != 0 or plant.snapshot(0) != initial:
        raise ValueError("prepare modified plant")
    return initial


def failure_result(exc, operation):
    reason = type(exc).__name__ + ": " + str(exc)
    if isinstance(exc, UnsupportedSceneError):
        return {
            "status": "UNSUPPORTED_SCENE_PREFLIGHT_FAILURE",
            "classification": "UNSUPPORTED_SCENE_PREFLIGHT_FAILURE",
            "reason": reason,
        }
    if isinstance(exc, IntegrityStopError):
        return {
            "status": "INTEGRITY_STOP",
            "classification": "INTEGRITY_STOP",
            "reason": reason,
        }
    if isinstance(exc, PreflightFailureError) or operation == "prepare":
        return {
            "status": "PREFLIGHT_FAILURE",
            "classification": "PREFLIGHT_FAILURE",
            "reason": reason,
        }
    return {
        "status": "FAILED",
        "classification": "EXECUTION_OR_EVIDENCE_FAILURE",
        "reason": reason,
    }


def prepare(output, review_path, qualification_path, task_path=TASK):
    with (
        experiment_lock() as lock,
        zero_step_guard(),
        EvidenceRun(output, {"operation": "baseline_prepare_zero_step"}) as run,
    ):
        task = load_task(task_path)
        head, sources = current_identity(task)
        protocol_path = ROOT / task["configuration"]["protocol"]
        protocol = strict_json(protocol_path.read_text())
        review = strict_json(review_path.read_text())
        validate_review(review, head)
        qualification = validate(qualification_path)
        fresh_preflight(
            lock,
            head,
            review,
            run.path / "preflight.json",
            run.path / "future_capture",
            task,
            qualification,
            protocol,
        )
        runtime = verify_environment()
        setup_runtime()
        source_inputs = inputs(protocol)
        for name, expected in source_inputs.items():
            dest = run.path / "inputs" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / name).read_bytes())
            if digest(dest) != expected:
                raise ValueError("input changed during snapshot")
        models = {}
        for case in protocol["cases"]:
            plant = Plant(
                run.path / "inputs" / case["scene"], case, protocol["physics_period_s"]
            )
            policy = make_policy(
                run.path / "inputs", case, source_inputs[".substrate/rl/policy.pt"]
            )
            # Validate policy shape/finite output on an isolated object, not live history.
            probe_command = (
                command_at(case, 0) if protocol.get("schema") == 2 else [1.0, 0.0, 0.0]
            )
            row = prepare_probe(plant, policy, case, probe_command)
            models[case["id"]] = dict(
                physical_sha256=physical_fingerprint(plant.model),
                qadr=plant.qadr,
                vadr=plant.vadr,
                aids=plant.aids,
                initial=row,
            )
        if (
            inputs(protocol) != source_inputs
            or (head, sources) != current_identity(task)
            or task != load_task(task_path)
        ):
            raise ValueError("inputs changed during prepare")
        validate_reference(qualification)
        ledger = ROOT / "_runs/substrate_attempts" / protocol["id"]
        if ledger.exists():
            raise ValueError("campaign already claimed")
        write_new(run.path / "protocol.json", protocol)
        run.result.update(
            status="ENGINEERING_ADMITTED",
            readiness="READY_AWAITING_START",
            head=head,
            source_files=sources,
            task=task,
            review=review,
            runtime=runtime,
            qualification_reference=qualification,
            protocol_sha256=digest(protocol_path),
            max_attempts=protocol["max_attempts"],
            source_inputs=source_inputs,
            models=models,
            physics_steps=0,
        )
    verify_bundle(output)
    return {"status": "READY_AWAITING_START", "head": head, "physics_steps": 0}


def capture_readiness(prepared_path, authorization_path, task_path):
    try:
        prepared = verify_bundle(prepared_path)
        task = load_task(task_path)
        head, sources = current_identity(task)
        protocol_path = ROOT / task["configuration"]["protocol"]
        protocol = strict_json(protocol_path.read_text())
        if (
            prepared["readiness"] != "READY_AWAITING_START"
            or prepared["task"] != task
            or prepared["head"] != head
            or prepared["source_files"] != sources
            or prepared["protocol_sha256"] != digest(protocol_path)
            or prepared["source_inputs"] != inputs(protocol)
        ):
            raise PreflightFailureError("stale preparation")
        prepared["prepared_manifest_sha256"] = digest(
            prepared_path / "manifest.json"
        )
        auth = strict_json(authorization_path.read_text())
        validate_authorization(auth, prepared)
        validate_review(prepared["review"], head)
        qualification = validate_reference(prepared["qualification_reference"])
        verify_environment()
        setup_runtime()
        return prepared, task, head, sources, protocol_path, protocol, auth, qualification
    except (PreflightFailureError, UnsupportedSceneError, IntegrityStopError):
        raise
    except Exception as exc:
        raise PreflightFailureError("capture readiness checks did not pass") from exc


def capture(prepared_path, authorization_path, output, task_path=TASK):
    with experiment_lock() as lock:
        (
            prepared,
            task,
            head,
            sources,
            protocol_path,
            protocol,
            auth,
            qualification,
        ) = capture_readiness(prepared_path, authorization_path, task_path)
        ledger = ROOT / "_runs/substrate_attempts" / protocol["id"]
        if ledger.exists():
            raise IntegrityStopError("campaign already claimed; no retry")
        with EvidenceRun(output, {"operation": "baseline_capture"}) as run:
            attempts = [
                dict(index=i + 1, case=c["id"], status="NOT_RUN")
                for i, c in enumerate(protocol["cases"])
            ]
            run.result.update(
                status="FAILED",
                capability_status="INCOMPLETE",
                head=head,
                attempts=attempts,
                live_runs=0,
            )
            fresh_preflight(
                lock,
                head,
                prepared["review"],
                run.path / "preflight.json",
                ledger,
                task,
                qualification,
                protocol,
            )
            write_new(run.path / "authorization.json", auth)
            write_new(run.path / "protocol.json", protocol)
            write_new(
                run.path / "preparation-reference.json",
                dict(
                    path=str(prepared_path.resolve()),
                    manifest_sha256=prepared["prepared_manifest_sha256"],
                ),
            )
            ledger.mkdir(parents=True, exist_ok=False)
            claim = dict(
                head=head,
                output=str(run.path.resolve()),
                protocol_sha256=prepared["protocol_sha256"],
            )
            write_new(ledger / "campaign.json", claim)
            write_new(run.path / "campaign-claim.json", claim)
            completed = {}
            for item, case in zip(attempts, protocol["cases"]):
                if any(
                    completed.get(name, {}).get("verdict") != "PASS"
                    for name in case["requires"]
                ):
                    item["reason"] = "reference_dependency_failed"
                    continue
                if (head, sources) != current_identity(task):
                    raise IntegrityStopError("source changed during capture")
                validate_snapshot(prepared_path, prepared["prepared_manifest_sha256"])
                plant = Plant(
                    prepared_path / "inputs" / case["scene"],
                    case,
                    protocol["physics_period_s"],
                )
                if (
                    physical_fingerprint(plant.model)
                    != prepared["models"][case["id"]]["physical_sha256"]
                ):
                    raise IntegrityStopError("plant changed after preparation")
                policy = make_policy(
                    prepared_path / "inputs",
                    case,
                    prepared["source_inputs"][".substrate/rl/policy.pt"],
                )
                raw = run.path / (case["id"] + ".jsonl")
                item["status"] = "BOOTING"

                def consume():
                    claim = dict(
                        index=item["index"],
                        case=case["id"],
                        head=head,
                        raw=str(raw.resolve()),
                        boundary="first_post_handoff_state_control_sample",
                    )
                    write_new(ledger / (case["id"] + ".json"), claim)
                    write_new(run.path / (case["id"] + "_claim.json"), claim)
                    run.result["live_runs"] += 1
                    item["status"] = "CAPTURING"

                started = time.monotonic()
                try:
                    with raw.open("x") as stream:

                        def emit(row):
                            stream.write(
                                json.dumps(row, separators=(",", ":"), allow_nan=False)
                                + "\n"
                            )
                            stream.flush()

                        try:
                            with wall_deadline(protocol["wall_timeout_s"]):
                                episode(plant, policy, case, protocol, emit, consume)
                        finally:
                            stream.flush()
                            os.fsync(stream.fileno())
                    rows = [strict_json(line) for line in raw.read_text().splitlines()]
                    result = analyze(rows, case, protocol)
                    result["elapsed_s"] = time.monotonic() - started
                    result = enforce_reference_digest(result, case)
                    reference_case = repeat_reference(case)
                    if (
                        reference_case is not None
                        and result["trace_sha256"]
                        != (completed[reference_case]["trace_sha256"])
                    ):
                        result["verdict"] = "INTEGRITY_STOP"
                        result["failure"] = "trajectory_mismatch"
                        if "failure_classes" in result:
                            result["failure_classes"] = ["INTEGRITY_STOP"]
                    write_new(run.path / (case["id"] + "_analysis.json"), result)
                    item.update(status=result["verdict"], analysis=result)
                    completed[case["id"]] = result
                    validate_snapshot(
                        prepared_path, prepared["prepared_manifest_sha256"]
                    )
                    print(json.dumps({"case": case["id"], **result}), flush=True)
                    if stop_after(protocol, result["verdict"]):
                        break
                except BaseException as exc:
                    item.update(
                        status="ERROR", reason=type(exc).__name__ + ": " + str(exc)
                    )
                    raise
            validate_snapshot(prepared_path, prepared["prepared_manifest_sha256"])
            try:
                capture_inputs = inputs(protocol)
            except Exception as exc:
                raise IntegrityStopError("source inputs failed capture revalidation") from exc
            if (head, sources) != current_identity(task) or capture_inputs != prepared[
                "source_inputs"
            ]:
                raise IntegrityStopError("source changed during capture")
            run.result.update(
                status="CAPTURE_COMPLETE",
                capability_status="CHARACTERIZED"
                if campaign_characterized(attempts, protocol)
                else "PARTIAL",
            )
    return {
        "status": run.result["status"],
        "capability_status": run.result["capability_status"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--task", type=Path, default=TASK)
    prep.add_argument("--output", required=True, type=Path)
    prep.add_argument("--review", required=True, type=Path)
    prep.add_argument("--qualification", required=True, type=Path)
    cap = sub.add_parser("capture")
    cap.add_argument("--task", type=Path, default=TASK)
    cap.add_argument("--prepared", required=True, type=Path)
    cap.add_argument("--authorization", required=True, type=Path)
    cap.add_argument("--output", required=True, type=Path)
    ver = sub.add_parser("verify")
    ver.add_argument("--capture", required=True, type=Path)
    ver.add_argument("--prepared", required=True, type=Path)
    ver.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.operation == "prepare":
            result = prepare(args.output, args.review, args.qualification, args.task)
        elif args.operation == "capture":
            result = capture(args.prepared, args.authorization, args.output, args.task)
        else:
            from .baseline_verify import verify

            result = verify(args.capture, args.prepared, args.output)
        print(json.dumps(result))
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps(failure_result(exc, args.operation)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
