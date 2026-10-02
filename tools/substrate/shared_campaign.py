"""Bounded shared baseline/probe campaign; CLI exposes preparation and verification only."""

import argparse
import json
import os
from pathlib import Path
import time
from datetime import datetime, timezone

from . import aligned_capture as base
from .aligned_anchor import validate_canonical_model
from .aligned_episode import run_aligned_episode
from .bounded_conditions import BoundedCondition, IDS, condition_specs
from .contracts import (
    PositionTargetControllerAdapter,
    ProprioceptivePolicyAdapter,
    POLICY_JOINTS,
)
from .episode import MujocoPlant
from .guards import wall_deadline, zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_bundle,
    verify_manifest,
    write_new,
)
from .model import dependency_manifest, joint_layout, physical_fingerprint
from .native_mjpc import NativeMJPCController
from .qualification import validate as validate_qualification, validate_reference
from .readiness import validate_review, validate_authorization
from .rl import FrozenPolicy
from .shared_baseline import DEFAULT_PLAN, load_plan, replay_baseline, repeat_difference
from .condition_evidence import verify_condition

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = ROOT / ".substrate/rl/policy.pt"
BINARY = ROOT / ".substrate/headless-reliable/go2_mjpc_controller"


def current_head(plan):
    head = base.current_head()
    if base.git("branch", "--show-current") != plan["raw"]["expected_branch"]:
        raise ValueError("shared campaign requires the frozen named branch")
    return head


def arms(plan):
    result = []
    for name in ("rl", "mjpc"):
        for repeat in (1, 2):
            result.append(
                {
                    "id": f"{name}_baseline_{repeat}",
                    "controller": name,
                    "stage": "baseline",
                    "repeat": repeat,
                    "condition": None,
                    "reference_baseline": None,
                }
            )
    for name in ("rl", "mjpc"):
        for condition in IDS:
            for repeat in (1, 2):
                result.append(
                    {
                        "id": f"{name}_{condition}_{repeat}",
                        "controller": name,
                        "stage": "challenge",
                        "repeat": repeat,
                        "condition": condition,
                        "reference_baseline": f"{name}_baseline_{repeat}",
                    }
                )
    if len(result) != plan["raw"]["max_attempts"]:
        raise ValueError("arm count differs from frozen budget")
    return result


def _identity(prepared):
    validate_reference(prepared["qualification"])
    if digest(CHECKPOINT) != prepared["rl_checkpoint_sha256"]:
        raise ValueError("checkpoint changed since preparation")
    identity = base.verify_controller(BINARY)
    if (
        identity["binary_sha256"] != prepared["mjpc_binary_sha256"]
        or identity["inputs"]["mjpc"]["head"] != prepared["mjpc_source_commit"]
    ):
        raise ValueError("native identity changed since preparation")


def prepare(output, *, qualification_path, plan_path=DEFAULT_PLAN):
    with experiment_lock(), zero_step_guard():
        plan = load_plan(plan_path)
        head = current_head(plan)
        qualification = validate_qualification(qualification_path)
        native = base.verify_controller(BINARY)
        sources = strict_json(base.LOCK.read_text())
        if digest(CHECKPOINT) != sources["rl"]["sha256"]:
            raise ValueError("checkpoint identity drifted")
        if native["inputs"]["mjpc"]["head"] != sources["mjpc"]["commit"]:
            raise ValueError("native source drifted")
        with EvidenceRun(Path(output), {"operation": "shared_campaign_prepare"}) as run:
            closure = dependency_manifest(ROOT / plan["scenario"].scene, ROOT)
            for name, expected in closure["files"].items():
                target = run.path / "inputs" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write((ROOT / name).read_bytes())
                if digest(target) != expected:
                    raise ValueError("asset changed during preparation")
            plant = MujocoPlant(run.path / "inputs" / plan["scenario"].scene)
            validate_canonical_model(plan, plant.model)
            names, qadr, vadr = joint_layout(plant.model)
            if any(
                qadr[names.index(name)] != 7 + i or vadr[names.index(name)] != 6 + i
                for i, name in enumerate(POLICY_JOINTS)
            ):
                raise ValueError("raw-state canonical joint order drifted")
            if plant.steps != 0 or plant.data.time != 0:
                raise ValueError("preparation advanced the canonical plant")
            write_new(run.path / "capture-plan.json", plan["raw"])
            write_new(run.path / "planned-arms.json", arms(plan))
            run.result.update(
                status="ENGINEERING_ADMITTED",
                scope="shared_campaign_preparation",
                readiness="AWAITING_EXACT_HEAD_REVIEWS_AND_BOUND_DELEGATION",
                head=head,
                branch=plan["raw"]["expected_branch"],
                qualification=qualification,
                protocol_sha256=digest(Path(plan_path)),
                anchor_sha256=plan["raw"]["anchor_sha256"],
                max_attempts=plan["raw"]["max_attempts"],
                physics_steps_max=plan["raw"]["physics_steps_max"],
                rl_checkpoint_sha256=digest(CHECKPOINT),
                mjpc_binary_sha256=native["binary_sha256"],
                mjpc_source_commit=sources["mjpc"]["commit"],
                physical_sha256=physical_fingerprint(plant.model),
                state_joint_order=list(POLICY_JOINTS),
                planned_arms=arms(plan),
                canonical_physics_steps=0,
                private_planning_calls=0,
                scientific_attempts=0,
            )
    verify_bundle(output)
    return {
        "head": head,
        "output": str(output),
        "canonical_physics_steps": 0,
        "private_planning_calls": 0,
        "readiness": run.result["readiness"],
    }


def validate_start_files(prepared_dir, review_path, authorization_path, plan_path):
    plan = load_plan(plan_path)
    prepared = verify_bundle(prepared_dir)
    head = current_head(plan)
    if (
        prepared.get("scope") != "shared_campaign_preparation"
        or prepared.get("head") != head
        or prepared.get("readiness")
        != "AWAITING_EXACT_HEAD_REVIEWS_AND_BOUND_DELEGATION"
        or prepared.get("protocol_sha256") != digest(Path(plan_path))
        or prepared.get("anchor_sha256") != plan["raw"]["anchor_sha256"]
        or prepared.get("max_attempts") != 20
        or prepared.get("physics_steps_max") != 120000
        or prepared.get("planned_arms") != arms(plan)
    ):
        raise ValueError("prepared campaign binding drifted")
    _identity(prepared)
    review = strict_json(Path(review_path).read_text())
    authorization = strict_json(Path(authorization_path).read_text())
    validate_review(review, head)
    binding = dict(
        prepared, prepared_manifest_sha256=digest(Path(prepared_dir) / "manifest.json")
    )
    validate_authorization(authorization, binding)
    if authorization.get("task_id") != plan["raw"]["id"]:
        raise ValueError("authorization must bind this new campaign, never v2 START")
    return plan, prepared, head, review, authorization


def _fresh_preflight(lock, head, review, plan, prepared, output):
    from .launch import preflight
    from tools.research.preflight import find_processes, DEFAULT_PROCESS_NAMES

    stale = find_processes(DEFAULT_PROCESS_NAMES + ("go2_mjpc_controller",))
    if stale:
        raise ValueError("stale Go2 runtime present")
    directory = (
        ROOT
        / "_runs/shared_campaign_preflight"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    task = {
        "configuration": {
            "branch": plan["raw"]["expected_branch"],
            "diff_base": plan["raw"]["accepted_parent_head"],
        }
    }
    with EvidenceRun(
        directory, {"operation": "shared_campaign_fresh_preflight"}
    ) as run:
        preflight(
            lock,
            head,
            review,
            run.path / "report.json",
            output,
            task,
            prepared["qualification"],
            runner=Path(__file__),
            experiment_id=plan["raw"]["id"],
        )
        run.result.update(
            status="ENGINEERING_ADMITTED",
            head=head,
            canonical_physics_steps=0,
            scientific_attempts=0,
        )
    return {
        "path": str(directory),
        "manifest_sha256": digest(directory / "manifest.json"),
    }


def _make_controller(name, timing, prepared, stderr):
    if name == "rl":
        return ProprioceptivePolicyAdapter(
            FrozenPolicy(CHECKPOINT, prepared["rl_checkpoint_sha256"])
        ), lambda: None
    native = NativeMJPCController(BINARY, timing, stderr_log_path=stderr)
    return PositionTargetControllerAdapter(
        native, native.actuator_spec, native.joint_names
    ), native.close


def _read_rows(path):
    return [strict_json(line) for line in Path(path).read_text().splitlines() if line]


def _execute_arm(item, run, ledger, prepared_dir, prepared, plan, head):
    config = plan["controllers"][item["controller"]]
    information, timing = config["information"], config["timing"]
    condition = None
    if item["condition"] is not None:
        information, timing = condition_specs(item["condition"], information, timing)
        condition = BoundedCondition(item["condition"])
    plant = MujocoPlant(Path(prepared_dir) / "inputs" / plan["scenario"].scene)
    item["physics_steps"] = 0
    validate_canonical_model(plan, plant.model)
    controller, close = _make_controller(
        item["controller"],
        timing,
        prepared,
        run.path / (item["id"] + ".native.stderr.log"),
    )
    raw = run.path / (item["id"] + ".jsonl")
    consumed = False

    def consume():
        nonlocal consumed
        if consumed or run.result["scientific_attempts"] >= plan["raw"]["max_attempts"]:
            raise ValueError("attempt duplicate or budget exhausted")
        claim = {
            **{
                k: item[k]
                for k in (
                    "id",
                    "controller",
                    "stage",
                    "repeat",
                    "condition",
                    "reference_baseline",
                )
            },
            "index": item["index"],
            "head": head,
            "raw": str(raw.resolve()),
            "boundary": "first_post_handoff_state_control_sample",
            "scope": "scientific",
        }
        write_new(ledger / (item["id"] + ".json"), claim)
        consumed = True
        run.result["scientific_attempts"] += 1
        run.result["live_runs"] += 1
        item["status"] = "CAPTURING"
        item["not_run_reason"] = None
        write_new(run.path / (item["id"] + "_claim.json"), claim)

    started = time.monotonic()
    try:
        with raw.open("x", encoding="utf-8") as stream:

            def emit(row):
                stream.write(
                    json.dumps(
                        row, allow_nan=False, separators=(",", ":"), sort_keys=True
                    )
                    + "\n"
                )
                stream.flush()

            try:
                with wall_deadline(plan["raw"]["wall_timeout_s"]):
                    outcome = run_aligned_episode(
                        plant,
                        controller,
                        plan["task"],
                        information,
                        timing,
                        emit,
                        consume,
                        condition=condition,
                    )
            finally:
                stream.flush()
                os.fsync(stream.fileno())
    finally:
        item["physics_steps"] = plant.steps
        close()
    rows = _read_rows(raw)
    replay = replay_baseline(rows, plan)
    if (
        outcome["terminal_reason"] != replay["canonical"]["terminal_reason"]
        or outcome["steps"] != plant.steps
        or len(rows) != plant.steps + 1
        or outcome["attempt_consumed"] is not consumed
        or (
            not consumed
            and not (replay["classification"] == "SAFETY_STOP" and plant.steps == 0)
        )
    ):
        raise ValueError("episode/replay/claim terminal evidence mismatch")
    if replay["classification"] == "INCOMPLETE":
        raise ValueError("incomplete raw evidence")
    evidence = None
    if item["condition"] is not None:
        reference = run.path / (item["reference_baseline"] + ".jsonl")
        evidence = verify_condition(
            rows,
            _read_rows(reference),
            item["condition"],
            item["controller"],
            plan,
            digest(reference),
        )
    analysis = {
        "case": item["id"],
        "episode": outcome,
        "replay": replay,
        "classification": replay["classification"],
        "condition_evidence": evidence,
        "elapsed_s": time.monotonic() - started,
        "frames": len(rows),
        "physics_steps": plant.steps,
        "raw_sha256": digest(raw),
    }
    if (
        evidence is not None
        and replay["classification"] != "SAFETY_STOP"
        and not evidence["effective_complete_horizon"]
    ):
        analysis["classification"] = "EXPOSURE_EVIDENCE_STOP"
    write_new(run.path / (item["id"] + "_analysis.json"), analysis)
    return analysis


def _not_run_after(attempts, case, reason):
    for item in attempts:
        if item["status"] == "NOT_RUN" and item["not_run_reason"] == "not_reached":
            item["not_run_reason"] = f"campaign_stopped:{case}:{reason}"


def _eligibility(name, run, attempts):
    pair = [
        item
        for item in attempts
        if item["stage"] == "baseline" and item["controller"] == name
    ]
    if any(item["status"] != "PASS" for item in pair):
        return {
            "eligible": False,
            "reason": "own_baseline_not_passing",
            "baseline_statuses": [item["status"] for item in pair],
        }
    difference = repeat_difference(
        *[_read_rows(run.path / (item["id"] + ".jsonl")) for item in pair]
    )
    return {
        "eligible": difference["repeatable"],
        "reason": "repeatable_own_baseline"
        if difference["repeatable"]
        else "own_baseline_nonrepeatable",
        "repeat_comparison": difference,
    }


def _run_campaign(run, ledger, prepared_dir, prepared, plan, head):
    attempts = run.result["attempts"]
    eligibility = run.result["baseline_eligibility"]
    setup_done = False
    for item in attempts:
        try:
            if item["stage"] == "challenge":
                name = item["controller"]
                if name not in eligibility:
                    eligibility[name] = _eligibility(name, run, attempts)
                if not eligibility[name]["eligible"]:
                    item["not_run_reason"] = eligibility[name]["reason"]
                    continue
            if current_head(plan) != head:
                raise ValueError("HEAD changed during campaign")
            verify_bundle(prepared_dir)
            _identity(prepared)
            if not setup_done:
                base._setup_runtime()
                setup_done = True
            item["status"] = "BOOTING"
            item["not_run_reason"] = None
            analysis = _execute_arm(
                item, run, ledger, prepared_dir, prepared, plan, head
            )
            item.update(status=analysis["classification"], analysis=analysis)
            if item["status"] in ("SAFETY_STOP", "EXPOSURE_EVIDENCE_STOP"):
                run.result.update(
                    status=item["status"],
                    campaign_complete=False,
                    stopped_case=item["id"],
                )
                _not_run_after(attempts, item["id"], item["status"])
                break
        except (Exception, KeyboardInterrupt) as error:
            item["status"] = "EXECUTION_EVIDENCE_STOP"
            item["not_run_reason"] = None
            failure = {
                "case": item["id"],
                "error_type": type(error).__name__,
                "error": str(error),
                "physics_steps": item.get("physics_steps", 0),
                "attempt_consumed": (ledger / (item["id"] + ".json")).exists(),
            }
            write_new(run.path / (item["id"] + "_failure.json"), failure)
            run.result.update(
                status="EXECUTION_EVIDENCE_STOP",
                campaign_complete=False,
                stopped_case=item["id"],
                errors=[failure],
            )
            _not_run_after(attempts, item["id"], "execution_or_evidence_failure")
            break
    else:
        run.result.update(status="CAPTURE_COMPLETE", campaign_complete=True)
    run.result["canonical_physics_steps"] = sum(
        item.get("physics_steps", 0) for item in attempts
    )
    if run.result["canonical_physics_steps"] > plan["raw"]["physics_steps_max"]:
        raise ValueError("canonical step budget exceeded")
    claims = [p for p in ledger.glob("*.json") if p.name != "campaign.json"]
    if (
        len(claims) != run.result["scientific_attempts"]
        or len(claims) > plan["raw"]["max_attempts"]
    ):
        raise ValueError("external claim accounting mismatch")
    if any(
        item["status"] == "NOT_RUN" and item["not_run_reason"] == "not_reached"
        for item in attempts
    ):
        raise ValueError("unclosed NOT_RUN reason")


def capture(
    prepared_dir, review_path, authorization_path, output, *, plan_path=DEFAULT_PLAN
):
    """No CLI start: caller must supply genuine exact-head dual review and user binding."""
    with experiment_lock() as lock:
        plan, prepared, head, review, authorization = validate_start_files(
            prepared_dir, review_path, authorization_path, plan_path
        )
        output = Path(output).absolute()
        if output.parent != (
            ROOT / plan["raw"]["output_root"]
        ).absolute() or not output.name.startswith("run_"):
            raise ValueError("output must be a fresh run_* under frozen output root")
        ledger = ROOT / "_runs/substrate_attempts" / plan["raw"]["id"]
        if ledger.exists() or output.exists():
            raise ValueError("campaign/output already exists; no retry or replacement")
        preflight = _fresh_preflight(lock, head, review, plan, prepared, output)
        with EvidenceRun(output, {"operation": "formal_shared_baseline_probes"}) as run:
            attempts = [
                {
                    **item,
                    "index": i + 1,
                    "status": "NOT_RUN",
                    "not_run_reason": "not_reached",
                }
                for i, item in enumerate(arms(plan))
            ]
            run.result.update(
                scope="formal_shared_baseline_probes",
                status="FAILED",
                head=head,
                branch=plan["raw"]["expected_branch"],
                attempts=attempts,
                baseline_eligibility={},
                live_runs=0,
                scientific_attempts=0,
                canonical_physics_steps=0,
                campaign_complete=False,
            )
            try:
                write_new(run.path / "review.json", review)
                write_new(run.path / "authorization.json", authorization)
                write_new(run.path / "capture-plan.json", plan["raw"])
                write_new(
                    run.path / "preparation-reference.json",
                    {
                        "path": str(Path(prepared_dir).resolve()),
                        "manifest_sha256": digest(Path(prepared_dir) / "manifest.json"),
                    },
                )
                write_new(run.path / "preflight-reference.json", preflight)
                ledger.mkdir(parents=True, exist_ok=False)
                campaign = {
                    "head": head,
                    "output": str(output),
                    "protocol_sha256": prepared["protocol_sha256"],
                    "max_attempts": 20,
                    "physics_steps_max": 120000,
                    "planned_arms": arms(plan),
                }
                write_new(ledger / "campaign.json", campaign)
                write_new(run.path / "campaign-claim.json", campaign)
                _run_campaign(run, ledger, prepared_dir, prepared, plan, head)
            finally:
                _not_run_after(
                    attempts,
                    run.result.get("stopped_case", "capture_unfinished"),
                    "execution_or_evidence_failure",
                )
                run.result["canonical_physics_steps"] = sum(
                    a.get("physics_steps", 0) for a in attempts
                )
    return {
        "head": head,
        "status": run.result["status"],
        "output": str(output),
        "scientific_attempts": run.result["scientific_attempts"],
        "canonical_physics_steps": run.result["canonical_physics_steps"],
    }


def verify_capture(directory, *, ledger=None):
    """Read-only raw replay and real external claims; no controller calls or dynamics."""
    with experiment_lock(), zero_step_guard():
        directory = Path(directory).resolve()
        record = verify_manifest(directory)
        plan = load_plan(directory / "capture-plan.json")
        ledger = Path(ledger or ROOT / "_runs/substrate_attempts" / plan["raw"]["id"])
        known = arms(plan)
        if len(record["attempts"]) != len(known):
            raise ValueError("captured arm catalog length differs")
        for index, (item, frozen) in enumerate(zip(record["attempts"], known), 1):
            if item["index"] != index or any(item[k] != v for k, v in frozen.items()):
                raise ValueError("captured arm catalog differs")
            if item["status"] == "NOT_RUN":
                if (
                    not item["not_run_reason"]
                    or item["not_run_reason"] == "not_reached"
                ):
                    raise ValueError("unclosed skipped arm")
                if (directory / (item["id"] + ".jsonl")).exists():
                    raise ValueError("skipped arm has raw samples")
        expected = [
            a
            for a in record["attempts"]
            if (directory / (a["id"] + "_claim.json")).exists()
        ]
        if (
            record["scientific_attempts"] != len(expected)
            or len(expected) > 20
            or record["canonical_physics_steps"]
            != sum(a.get("physics_steps", 0) for a in record["attempts"])
            or record["canonical_physics_steps"] > 120000
        ):
            raise ValueError("captured attempt/step accounting differs")
        if set(p.name for p in ledger.iterdir()) != {
            "campaign.json",
            *[a["id"] + ".json" for a in expected],
        }:
            raise ValueError("external ledger membership differs")
        if strict_json((ledger / "campaign.json").read_text()) != strict_json(
            (directory / "campaign-claim.json").read_text()
        ):
            raise ValueError("campaign external claim differs")
        for item in record["attempts"]:
            consumed = item in expected
            if consumed:
                claim = strict_json((ledger / (item["id"] + ".json")).read_text())
                if (
                    claim
                    != strict_json(
                        (directory / (item["id"] + "_claim.json")).read_text()
                    )
                    or claim["head"] != record["head"]
                    or Path(claim["raw"]) != directory / (item["id"] + ".jsonl")
                ):
                    raise ValueError("arm external claim differs")
            if "analysis" not in item:
                continue
            rows = _read_rows(directory / (item["id"] + ".jsonl"))
            analysis = item["analysis"]
            if (
                analysis["episode"]["attempt_consumed"] is not consumed
                or len(rows) != item["physics_steps"] + 1
                or analysis["physics_steps"] != item["physics_steps"]
                or (
                    not consumed
                    and not (
                        item["status"] == "SAFETY_STOP" and item["physics_steps"] == 0
                    )
                )
            ):
                raise ValueError("raw analysis/claim accounting differs")
            if replay_baseline(rows, plan) != item["analysis"]["replay"]:
                raise ValueError("raw performance replay differs")
            if item["condition"] is not None:
                reference = directory / (item["reference_baseline"] + ".jsonl")
                actual = verify_condition(
                    rows,
                    _read_rows(reference),
                    item["condition"],
                    item["controller"],
                    plan,
                    digest(reference),
                )
                if actual != item["analysis"]["condition_evidence"]:
                    raise ValueError("condition replay differs")
            expected_status = item["analysis"]["replay"]["classification"]
            if (
                item["condition"] is not None
                and expected_status != "SAFETY_STOP"
                and not actual["effective_complete_horizon"]
            ):
                expected_status = "EXPOSURE_EVIDENCE_STOP"
            if (
                item["status"] != expected_status
                or item["analysis"]["classification"] != expected_status
            ):
                raise ValueError("captured classification differs from replay")
        return {
            "status": "VERIFIED",
            "head": record["head"],
            "capture_status": record["status"],
            "external_claims_checked": True,
            "canonical_physics_steps": 0,
            "private_planning_calls": 0,
            "scientific_attempts_checked": len(expected),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--qualification", type=Path, required=True)
    p.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    v = commands.add_parser("verify")
    v.add_argument("--capture", type=Path, required=True)
    v.add_argument("--ledger", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(
            args.output, qualification_path=args.qualification, plan_path=args.plan
        )
    else:
        result = verify_capture(args.capture, ledger=args.ledger)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
