"""Independent two-arm RL friction capture using the established shared engine."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import json

from . import shared_campaign as engine
from . import rl_friction_reference as spec
from .guards import zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_bundle,
    verify_manifest,
    write_new,
)
from .qualification import validate as validate_qualification, validate_reference
from .readiness import validate_review, validate_authorization
from .aligned_anchor import validate_canonical_model
from .episode import MujocoPlant
from .model import dependency_manifest

TRANSPORT = "inprocess"
ROOT = spec.ROOT
DEFAULT_PLAN = spec.DEFAULT_PROTOCOL


def current_head(plan):
    return engine.current_head(plan)


def references(plan):
    """Adopt only the pinned sealed own RL pair; keep the old catalog closed."""
    f = plan["frozen"]
    directory = ROOT / f["reference_capture"]
    if digest(directory / "manifest.json") != f["reference_capture_manifest_sha256"]:
        raise ValueError("sealed reference capture identity differs")
    record = verify_manifest(directory)
    if (
        record["head"] != f["reference_capture_head"]
        or record["status"] != "SAFETY_STOP"
        or record["stopped_case"] != "mjpc_baseline_1"
        or record["scientific_attempts"] != 3
        or record["canonical_physics_steps"] != 13287
        or sum(a["status"] == "NOT_RUN" for a in record["attempts"]) != 17
    ):
        raise ValueError("old campaign closure changed")
    ledger = ROOT / f["reference_ledger"]
    expected = {
        "campaign.json",
        "rl_baseline_1.json",
        "rl_baseline_2.json",
        "mjpc_baseline_1.json",
    }
    if {p.name for p in ledger.iterdir()} != expected:
        raise ValueError("old external ledger membership changed")
    for name in expected:
        copied = (
            "campaign-claim.json"
            if name == "campaign.json"
            else name[:-5] + "_claim.json"
        )
        if strict_json((ledger / name).read_text()) != strict_json(
            (directory / copied).read_text()
        ):
            raise ValueError("old external ledger claim changed")
    inherited = engine.load_plan(ROOT / f["inherit_protocol"])
    own = engine._eligibility("rl", directory, record["attempts"], inherited)
    if not own["eligible"] or any(
        actual["id"] != expected["id"] or actual["raw_sha256"] != expected["raw_sha256"]
        for actual, expected in zip(own["baselines"], f["reference_baselines"])
    ):
        raise ValueError("sealed RL reference pair drifted or is ineligible")
    return {
        "capture": str(directory),
        "capture_manifest_sha256": f["reference_capture_manifest_sha256"],
        "capture_head": record["head"],
        "eligibility": {"rl": own},
        "external_ledger_files": {p.name: digest(p) for p in sorted(ledger.iterdir())},
        "old_NOT_RUN_count": 17,
    }


def _copy(path, target):
    with Path(target).open("xb") as stream:
        stream.write(Path(path).read_bytes())
    if digest(path) != digest(target):
        raise ValueError("snapshot source changed while copying")


def _reference_copy(directory, reference):
    for b in reference["eligibility"]["rl"]["baselines"]:
        if digest(Path(directory) / (b["id"] + ".jsonl")) != b["raw_sha256"]:
            raise ValueError("copied reference raw differs")


def _identity(prepared):
    validate_reference(prepared["qualification"])
    if digest(engine.CHECKPOINT) != prepared["rl_checkpoint_sha256"]:
        raise ValueError("RL checkpoint changed")
    # No native identity process or optimizer is needed for this RL-only task.


def _plan_identity(directory, plan, record):
    directory = Path(directory)
    identity = {
        "protocol_sha256": digest(directory / "frozen-protocol.json"),
        "capture_plan_sha256": digest(directory / "capture-plan.json"),
    }
    if identity["protocol_sha256"] != spec.PROTOCOL_SHA256 or any(
        record.get(k) != v for k, v in identity.items()
    ):
        raise ValueError("independent protocol/archive identity changed")
    if any(
        strict_json((directory / name).read_text()) != plan["frozen"]
        for name in ("frozen-protocol.json", "capture-plan.json")
    ):
        raise ValueError("independent protocol/archive semantics changed")
    return identity


def prepare(output, *, qualification_path, plan_path=DEFAULT_PLAN):
    with experiment_lock(), zero_step_guard():
        plan = spec.load_plan(plan_path)
        head = current_head(plan)
        qualification = validate_qualification(qualification_path)
        reference = references(plan)
        spec.static_inputs(plan)
        with EvidenceRun(
            Path(output), {"operation": "independent_rl_friction_prepare"}
        ) as run:
            closure = dependency_manifest(ROOT / plan["scenario"].scene, ROOT)
            for name, expected in closure["files"].items():
                target = run.path / "inputs" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                _copy(ROOT / name, target)
                if digest(target) != expected:
                    raise ValueError("model dependency changed during preparation")
            plant = MujocoPlant(run.path / "inputs" / plan["scenario"].scene)
            validate_canonical_model(plan, plant.model)
            for b in reference["eligibility"]["rl"]["baselines"]:
                _copy(
                    Path(reference["capture"]) / (b["id"] + ".jsonl"),
                    run.path / (b["id"] + ".jsonl"),
                )
            _copy(plan_path, run.path / "frozen-protocol.json")
            write_new(run.path / "capture-plan.json", plan["frozen"])
            write_new(run.path / "sealed-reference.json", reference)
            write_new(run.path / "planned-arms.json", spec.arms(plan))
            run.result.update(
                status="ENGINEERING_ADMITTED",
                scope="independent_rl_friction_preparation",
                readiness="AWAITING_EXACT_HEAD_REVIEWS_AND_BOUND_DELEGATION",
                head=head,
                branch=plan["raw"]["expected_branch"],
                qualification=qualification,
                protocol_sha256=digest(plan_path),
                capture_plan_sha256=digest(run.path / "capture-plan.json"),
                max_attempts=2,
                physics_steps_max=12000,
                planned_arms=spec.arms(plan),
                rl_checkpoint_sha256=digest(engine.CHECKPOINT),
                sealed_reference=reference,
                canonical_physics_steps=0,
                private_planning_calls=0,
                scientific_attempts=0,
            )
            _plan_identity(run.path, plan, run.result)
            _reference_copy(run.path, reference)
            if (
                plant.steps
                or plant.data.time
                or current_head(plan) != head
                or references(plan) != reference
            ):
                raise ValueError(
                    "prepare advanced physics or changed identity/reference"
                )
    verify_bundle(output)
    return {
        "head": head,
        "output": str(output),
        "canonical_physics_steps": 0,
        "scientific_attempts": 0,
    }


def validate_start_files(
    prepared_dir, review_path, authorization_path, plan_path=DEFAULT_PLAN
):
    plan = spec.load_plan(plan_path)
    prepared = verify_bundle(prepared_dir)
    head = current_head(plan)
    if (
        prepared.get("head") != head
        or prepared.get("scope") != "independent_rl_friction_preparation"
        or prepared.get("max_attempts") != 2
        or prepared.get("physics_steps_max") != 12000
        or prepared.get("planned_arms") != spec.arms(plan)
        or prepared.get("sealed_reference") != references(plan)
        or prepared.get("readiness")
        != "AWAITING_EXACT_HEAD_REVIEWS_AND_BOUND_DELEGATION"
    ):
        raise ValueError("independent prepared binding changed")
    _plan_identity(prepared_dir, plan, prepared)
    _reference_copy(prepared_dir, prepared["sealed_reference"])
    _identity(prepared)
    review, authorization = (
        strict_json(Path(review_path).read_text()),
        strict_json(Path(authorization_path).read_text()),
    )
    validate_review(review, head)
    binding = {
        **prepared,
        "prepared_manifest_sha256": digest(Path(prepared_dir) / "manifest.json"),
    }
    validate_authorization(authorization, binding)
    if (
        authorization.get("task_id") != plan["frozen"]["id"]
        or type(authorization.get("physics_steps_max")) is not int
        or authorization["physics_steps_max"] != 12000
    ):
        raise ValueError("START must bind the independent task and 12000-step budget")
    return plan, prepared, head, review, authorization


def _fresh_preflight(lock, head, review, plan, prepared, output):
    from .launch import preflight
    from tools.research.preflight import find_processes, DEFAULT_PROCESS_NAMES

    if find_processes(DEFAULT_PROCESS_NAMES + ("go2_mjpc_controller",)):
        raise ValueError("stale Go2 runtime present")
    directory = (
        ROOT
        / "_runs/rl_friction_preflight"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    task = {
        "configuration": {
            "branch": plan["raw"]["expected_branch"],
            "diff_base": plan["raw"]["accepted_parent_head"],
        }
    }
    try:
        with EvidenceRun(
            directory, {"operation": "independent_rl_friction_fresh_preflight"}
        ) as run:
            run.result.update(
                head=head,
                canonical_physics_steps=0,
                private_planning_calls=0,
                scientific_attempts=0,
            )
            preflight(
                lock,
                head,
                review,
                run.path / "report.json",
                output,
                task,
                prepared["qualification"],
                runner=Path(__file__),
                experiment_id=plan["frozen"]["id"],
            )
            run.result.update(status="ENGINEERING_ADMITTED")
    except (Exception, KeyboardInterrupt) as error:
        error.preflight_reference = {
            "path": str(directory),
            "manifest_sha256": digest(directory / "manifest.json"),
        }
        raise

    return {
        "path": str(directory),
        "manifest_sha256": digest(directory / "manifest.json"),
    }


def _campaign_claim(plan, prepared, prepared_dir, head, output):
    return {
        "head": head,
        "output": str(output),
        "protocol_sha256": prepared["protocol_sha256"],
        "capture_plan_sha256": prepared["capture_plan_sha256"],
        "prepared_manifest_sha256": digest(Path(prepared_dir) / "manifest.json"),
        "sealed_reference_sha256": digest(Path(prepared_dir) / "sealed-reference.json"),
        "max_attempts": 2,
        "physics_steps_max": 12000,
        "planned_arms": spec.arms(plan),
    }


def capture(
    prepared_dir, review_path, authorization_path, output, *, plan_path=DEFAULT_PLAN
):
    with experiment_lock() as lock:
        plan, prepared, head, review, authorization = validate_start_files(
            prepared_dir, review_path, authorization_path, plan_path
        )
        output = Path(output).absolute()
        if output.parent != (
            ROOT / plan["frozen"]["output_root"]
        ).absolute() or not output.name.startswith("run_"):
            raise ValueError(
                "capture requires fresh run_* under independent output root"
            )
        ledger = ROOT / plan["frozen"]["ledger_root"]
        if ledger.exists() or output.exists():
            raise ValueError("independent campaign/output already exists; no retry")
        claim = _campaign_claim(plan, prepared, prepared_dir, head, output)
        # Validated START reserves this campaign before fresh preflight. A failed
        # preflight also permanently closes it, without consuming an arm.
        ledger.mkdir(parents=True, exist_ok=False)
        write_new(ledger / "campaign.json", claim)
        preflight, failure = None, None
        try:
            preflight = _fresh_preflight(lock, head, review, plan, prepared, output)
        except (Exception, KeyboardInterrupt) as error:
            failure = error
            preflight = getattr(error, "preflight_reference", None)
        with EvidenceRun(
            output, {"operation": "formal_independent_rl_friction"}
        ) as run:
            attempts = [
                {
                    **item,
                    "index": i,
                    "status": "NOT_RUN",
                    "not_run_reason": "not_reached",
                }
                for i, item in enumerate(spec.arms(plan), 1)
            ]
            run.result.update(
                status="FAILED",
                scope="formal_independent_rl_friction",
                head=head,
                branch=plan["raw"]["expected_branch"],
                attempts=attempts,
                baseline_eligibility=prepared["sealed_reference"]["eligibility"],
                live_runs=0,
                scientific_attempts=0,
                canonical_physics_steps=0,
                private_planning_calls=0,
                campaign_complete=False,
                protocol_sha256=prepared["protocol_sha256"],
                capture_plan_sha256=prepared["capture_plan_sha256"],
                sealed_reference=prepared["sealed_reference"],
            )
            phase = "preflight" if failure else "setup"
            try:
                write_new(run.path / "review.json", review)
                write_new(run.path / "authorization.json", authorization)
                write_new(run.path / "campaign-claim.json", claim)
                write_new(
                    run.path / "preparation-reference.json",
                    {
                        "path": str(Path(prepared_dir).resolve()),
                        "manifest_sha256": digest(Path(prepared_dir) / "manifest.json"),
                    },
                )
                if preflight:
                    write_new(run.path / "preflight-reference.json", preflight)
                for name in (
                    "frozen-protocol.json",
                    "capture-plan.json",
                    "sealed-reference.json",
                    "rl_baseline_1.jsonl",
                    "rl_baseline_2.jsonl",
                ):
                    _copy(Path(prepared_dir) / name, run.path / name)
                _plan_identity(run.path, plan, prepared)
                path = run.path / "baseline-eligibility.json"
                write_new(
                    path,
                    {"head": head, "eligibility": run.result["baseline_eligibility"]},
                )
                run.result["baseline_eligibility_sha256"] = digest(path)
                if failure:
                    raise failure
                phase = "postcapture"
                engine._run_campaign(
                    run,
                    ledger,
                    prepared_dir,
                    prepared,
                    plan,
                    head,
                    identity_check=_identity,
                )
                for item in attempts:
                    if "analysis" in item:
                        auxiliary = spec.paired_auxiliary(
                            engine._read_rows(run.path / (item["id"] + ".jsonl")),
                            engine._read_rows(
                                run.path / (item["reference_baseline"] + ".jsonl")
                            ),
                        )
                        write_new(
                            run.path / (item["id"] + "_auxiliary.json"), auxiliary
                        )
            except (Exception, KeyboardInterrupt) as error:
                detail = {
                    "case": phase,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "physics_steps": sum(i.get("physics_steps", 0) for i in attempts),
                    "scientific_attempts": run.result["scientific_attempts"],
                }
                write_new(run.path / "global-failure.json", detail)
                run.result.update(
                    status="EXECUTION_EVIDENCE_STOP",
                    campaign_complete=False,
                    stopped_case=phase,
                    errors=[detail],
                )
                engine._not_run_after(attempts, phase, "execution_or_evidence_failure")
            finally:
                engine._not_run_after(
                    attempts,
                    run.result.get("stopped_case", "capture_unfinished"),
                    "execution_or_evidence_failure",
                )
                run.result["canonical_physics_steps"] = sum(
                    i.get("physics_steps", 0) for i in attempts
                )
    return {
        "head": head,
        "status": run.result["status"],
        "output": str(output),
        "scientific_attempts": run.result["scientific_attempts"],
        "canonical_physics_steps": run.result["canonical_physics_steps"],
    }


def verify_capture(directory, *, ledger=None):
    """Independent raw/claims/prefix/exposure/auxiliary replay, zero integration."""
    with experiment_lock(), zero_step_guard():
        directory = Path(directory).resolve()
        record = verify_manifest(directory)
        plan = spec.load_plan(directory / "frozen-protocol.json")
        identity = _plan_identity(directory, plan, record)
        reference = strict_json((directory / "preparation-reference.json").read_text())
        pdir = Path(reference["path"])
        prepared = verify_bundle(pdir)
        psha = digest(pdir / "manifest.json")
        if (
            reference["manifest_sha256"] != psha
            or prepared["head"] != record["head"]
            or prepared["scope"] != "independent_rl_friction_preparation"
            or prepared["max_attempts"] != 2
            or prepared["physics_steps_max"] != 12000
            or prepared["planned_arms"] != spec.arms(plan)
            or _plan_identity(pdir, plan, prepared) != identity
        ):
            raise ValueError("capture/prepared independent binding differs")
        source = references(plan)
        if any(
            value != source
            for value in (
                prepared["sealed_reference"],
                record["sealed_reference"],
                strict_json((directory / "sealed-reference.json").read_text()),
                strict_json((pdir / "sealed-reference.json").read_text()),
            )
        ):
            raise ValueError("sealed reference ownership changed")
        _reference_copy(directory, source)
        _reference_copy(pdir, source)
        qref = prepared["qualification"]
        qdir = Path(qref["path"])
        qr = verify_bundle(qdir)
        if (
            digest(qdir / "manifest.json") != qref["manifest_sha256"]
            or qr["qualification_fingerprint"] != qref["fingerprint"]
            or qr["qualification"]["head"] != qref["producer_head"]
        ):
            raise ValueError("prepared qualification source differs")
        review = strict_json((directory / "review.json").read_text())
        validate_review(review, record["head"])
        authorization = strict_json((directory / "authorization.json").read_text())
        validate_authorization(
            authorization, {**prepared, "prepared_manifest_sha256": psha}
        )
        if (
            authorization.get("task_id") != plan["frozen"]["id"]
            or type(authorization.get("physics_steps_max")) is not int
            or authorization["physics_steps_max"] != 12000
        ):
            raise ValueError("captured START belongs to another task/budget")
        attempts = record["attempts"]
        if len(attempts) != 2 or any(
            a["index"] != i or any(a.get(k) != v for k, v in frozen.items())
            for i, (a, frozen) in enumerate(zip(attempts, spec.arms(plan)), 1)
        ):
            raise ValueError("captured independent two-arm catalog differs")
        ledger = Path(ledger or ROOT / plan["frozen"]["ledger_root"])
        consumed = {
            a["id"] for a in attempts if (ledger / (a["id"] + ".json")).exists()
        }
        copies = {
            a["id"]
            for a in attempts
            if (directory / (a["id"] + "_claim.json")).exists()
        }
        if consumed != copies or {p.name for p in ledger.iterdir()} != {
            "campaign.json",
            *[name + ".json" for name in consumed],
        }:
            raise ValueError("real external claim membership differs")
        if (
            any(
                type(a.get("physics_steps", 0)) is not int
                or not 0 <= a.get("physics_steps", 0) <= 6000
                for a in attempts
            )
            or type(record["scientific_attempts"]) is not int
            or record["scientific_attempts"] != len(consumed)
            or record["live_runs"] != len(consumed)
            or record["canonical_physics_steps"]
            != sum(a.get("physics_steps", 0) for a in attempts)
            or record["canonical_physics_steps"] > 12000
            or len(consumed) > 2
        ):
            raise ValueError("independent attempt/step accounting differs")
        expected_campaign = _campaign_claim(
            plan, prepared, pdir, record["head"], directory
        )
        if any(
            strict_json(path.read_text()) != expected_campaign
            for path in (ledger / "campaign.json", directory / "campaign-claim.json")
        ):
            raise ValueError("campaign external claim/budget differs")
        eligibility_path = directory / "baseline-eligibility.json"
        eligibility = source["eligibility"]
        if (
            record["baseline_eligibility"] != eligibility
            or record["baseline_eligibility_sha256"] != digest(eligibility_path)
            or strict_json(eligibility_path.read_text())
            != {"head": record["head"], "eligibility": eligibility}
        ):
            raise ValueError("independent adopted RL eligibility differs")
        global_failure = directory / "global-failure.json"
        global_case = record.get("stopped_case") in (
            "preflight",
            "setup",
            "postcapture",
        )
        stopped = (
            (record["stopped_case"], "EXECUTION_EVIDENCE_STOP") if global_case else None
        )
        if global_case:
            failure = strict_json(global_failure.read_text())
            if (
                failure["case"] != stopped[0]
                or failure["physics_steps"] != record["canonical_physics_steps"]
                or failure["scientific_attempts"] != len(consumed)
            ):
                raise ValueError("global failure accounting differs")
            if stopped[0] != "postcapture" and consumed:
                raise ValueError("arm consumed after preflight/setup failure")
        elif global_failure.exists():
            raise ValueError("unreported global failure")
        if (directory / "preflight-reference.json").exists():
            pref = strict_json((directory / "preflight-reference.json").read_text())
            pr = verify_manifest(pref["path"])
            if (
                digest(Path(pref["path"]) / "manifest.json") != pref["manifest_sha256"]
                or pr.get("head") != record["head"]
            ):
                raise ValueError("preflight source/head differs")
            if not global_case or stopped[0] != "preflight":
                report = strict_json((Path(pref["path"]) / "report.json").read_text())
                if (
                    pr["status"] != "ENGINEERING_ADMITTED"
                    or report["pass"] is not True
                    or report["git"]["head"] != record["head"]
                    or report["experiment_id"] != plan["frozen"]["id"]
                ):
                    raise ValueError("captured fresh preflight did not pass")
        elif not global_case or stopped[0] != "preflight":
            raise ValueError("started campaign lacks fresh preflight evidence")
        for item in attempts:
            status, name = item["status"], item["id"]
            has_claim = name in consumed
            if (
                stopped
                and not (global_case and stopped[0] == "postcapture")
                and status != "NOT_RUN"
            ):
                raise ValueError("arm executed after campaign stop")
            if status == "NOT_RUN":
                if (
                    has_claim
                    or item.get("physics_steps", 0)
                    or "analysis" in item
                    or any(
                        (directory / (name + suffix)).exists()
                        for suffix in (
                            ".jsonl",
                            "_analysis.json",
                            "_failure.json",
                            "_auxiliary.json",
                            ".native.stderr.log",
                        )
                    )
                ):
                    raise ValueError("NOT_RUN arm has execution evidence")
                if not stopped:
                    raise ValueError("eligible fresh RL arm skipped")
                reason = (
                    "execution_or_evidence_failure"
                    if stopped[1] == "EXECUTION_EVIDENCE_STOP"
                    else stopped[1]
                )
                if item["not_run_reason"] != f"campaign_stopped:{stopped[0]}:{reason}":
                    raise ValueError("NOT_RUN stop reason differs")
                continue
            if (
                status
                not in (
                    "PASS",
                    "PERFORMANCE_FAIL",
                    "SAFETY_STOP",
                    "EXPOSURE_EVIDENCE_STOP",
                    "EXECUTION_EVIDENCE_STOP",
                )
                or item["not_run_reason"] is not None
            ):
                raise ValueError("invalid started arm status")
            baseline = next(
                b
                for b in eligibility["rl"]["baselines"]
                if b["id"] == item["reference_baseline"]
            )
            binding = {
                "baseline_eligibility_sha256": digest(eligibility_path),
                "reference_baseline_sha256": baseline["raw_sha256"],
            }
            if any(item.get(k) != v for k, v in binding.items()):
                raise ValueError("challenge pairing differs from sealed reference")
            if has_claim:
                expected = {
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
                    **binding,
                    "index": item["index"],
                    "head": record["head"],
                    "raw": str(directory / (name + ".jsonl")),
                    "boundary": "first_post_handoff_state_control_sample",
                    "scope": "scientific",
                }
                if any(
                    strict_json(path.read_text()) != expected
                    for path in (
                        ledger / (name + ".json"),
                        directory / (name + "_claim.json"),
                    )
                ):
                    raise ValueError("arm external claim/reference differs")
            if status == "EXECUTION_EVIDENCE_STOP":
                fail = strict_json((directory / (name + "_failure.json")).read_text())
                if (
                    fail["case"] != name
                    or fail["physics_steps"] != item.get("physics_steps", 0)
                    or fail["attempt_consumed"] is not has_claim
                ):
                    raise ValueError("failed arm evidence/claim accounting differs")
            else:
                engine._check_analysis(item, directory, plan, has_claim)
                actual = spec.paired_auxiliary(
                    engine._read_rows(directory / (name + ".jsonl")),
                    engine._read_rows(
                        directory / (item["reference_baseline"] + ".jsonl")
                    ),
                )
                if (
                    strict_json((directory / (name + "_auxiliary.json")).read_text())
                    != actual
                ):
                    raise ValueError("prospective auxiliary replay differs")
            if (
                status
                in ("SAFETY_STOP", "EXPOSURE_EVIDENCE_STOP", "EXECUTION_EVIDENCE_STOP")
                and not global_case
            ):
                stopped = (name, status)
        if stopped:
            if (
                record["status"] != stopped[1]
                or record["stopped_case"] != stopped[0]
                or record["campaign_complete"] is not False
            ):
                raise ValueError("campaign STOP differs from arm sequence")
        elif (
            record["status"] != "CAPTURE_COMPLETE"
            or record["campaign_complete"] is not True
            or record.get("stopped_case") is not None
        ):
            raise ValueError("campaign completion differs")
        return {
            "status": "VERIFIED",
            "head": record["head"],
            "capture_status": record["status"],
            "scientific_attempts_checked": len(consumed),
            "external_claims_checked": True,
            "paired_prefix_exposure_and_auxiliary_checked": True,
            "canonical_physics_steps": 0,
            "private_planning_calls": 0,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--qualification", type=Path, required=True)
    live = sub.add_parser("capture")
    live.add_argument("--prepared", type=Path, required=True)
    live.add_argument("--review", type=Path, required=True)
    live.add_argument("--authorization", type=Path, required=True)
    live.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "prepare":
        result = prepare(args.output, qualification_path=args.qualification)
    elif args.operation == "capture":
        result = capture(args.prepared, args.review, args.authorization, args.output)
    else:
        result = verify_capture(args.capture)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
