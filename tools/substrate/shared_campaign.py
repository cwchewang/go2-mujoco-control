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

TRANSPORT = "inprocess"
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


def _plan_identity(directory, plan, record):
    directory = Path(directory)
    identity = {
        "protocol_sha256": digest(directory / "frozen-protocol.json"),
        "capture_plan_sha256": digest(directory / "capture-plan.json"),
    }
    if any(record.get(key) != value for key, value in identity.items()):
        raise ValueError("frozen protocol/archive plan identity differs")
    if any(
        strict_json((directory / name).read_text()) != plan["raw"]
        for name in ("frozen-protocol.json", "capture-plan.json")
    ):
        raise ValueError("frozen protocol/archive plan semantics differ")
    return identity


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
            with (run.path / "frozen-protocol.json").open("xb") as stream:
                stream.write(Path(plan_path).read_bytes())
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
                capture_plan_sha256=digest(run.path / "capture-plan.json"),
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
            _plan_identity(run.path, plan, run.result)
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
    _plan_identity(prepared_dir, plan, prepared)
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
    if item["stage"] == "challenge":
        if _challenge_binding(item, run) != {
            key: item.get(key)
            for key in ("baseline_eligibility_sha256", "reference_baseline_sha256")
        }:
            raise ValueError("challenge baseline binding drifted before launch")
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
        if item["stage"] == "challenge":
            _challenge_binding(item, run)
        claim = {
            "baseline_eligibility_sha256": item.get("baseline_eligibility_sha256"),
            "reference_baseline_sha256": item.get("reference_baseline_sha256"),
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


def _check_analysis(item, directory, plan, consumed):
    directory = Path(directory)
    analysis_path = directory / (item["id"] + "_analysis.json")
    if "analysis" not in item or not analysis_path.is_file():
        raise ValueError("started arm missing analysis")
    analysis = item["analysis"]
    if strict_json(analysis_path.read_text()) != analysis:
        raise ValueError("analysis copy differs")
    raw = directory / (item["id"] + ".jsonl")
    if not raw.is_file() or digest(raw) != analysis["raw_sha256"]:
        raise ValueError("raw SHA differs from analysis")
    rows = _read_rows(raw)
    if (
        type(item.get("physics_steps")) is not int
        or not 0 <= item["physics_steps"] <= plan["task"].horizon_ticks
        or analysis["episode"]["attempt_consumed"] is not consumed
        or len(rows) != item["physics_steps"] + 1
        or analysis["frames"] != len(rows)
        or analysis["physics_steps"] != item["physics_steps"]
        or analysis["episode"]["steps"] != item["physics_steps"]
        or (
            not consumed
            and not (item["status"] == "SAFETY_STOP" and item["physics_steps"] == 0)
        )
    ):
        raise ValueError("raw analysis/claim accounting differs")
    replay = replay_baseline(rows, plan)
    if replay["classification"] == "INCOMPLETE" or replay != analysis["replay"]:
        raise ValueError("raw performance replay differs")
    if analysis["episode"]["terminal_reason"] != replay["canonical"]["terminal_reason"]:
        raise ValueError("episode terminal differs from raw")
    status = replay["classification"]
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
        if actual != analysis["condition_evidence"]:
            raise ValueError("condition replay differs")
        if status != "SAFETY_STOP" and not actual["effective_complete_horizon"]:
            status = "EXPOSURE_EVIDENCE_STOP"
    elif analysis["condition_evidence"] is not None:
        raise ValueError("baseline carries condition evidence")
    if item["status"] != status or analysis["classification"] != status:
        raise ValueError("captured classification differs from replay")
    return replay


def _eligibility(name, directory, attempts, plan):
    pair = [
        item
        for item in attempts
        if item["stage"] == "baseline" and item["controller"] == name
    ]
    if len(pair) != 2:
        raise ValueError("own baseline pair incomplete")
    baselines = []
    for item in pair:
        replay = _check_analysis(item, directory, plan, True)
        baselines.append(
            {
                "id": item["id"],
                "raw_sha256": digest(Path(directory) / (item["id"] + ".jsonl")),
                "classification": replay["classification"],
            }
        )
    result = {
        "eligible": False,
        "reason": "own_baseline_not_passing",
        "baseline_statuses": [b["classification"] for b in baselines],
        "baselines": baselines,
    }
    if any(b["classification"] != "PASS" for b in baselines):
        return result
    difference = repeat_difference(
        *[_read_rows(Path(directory) / (item["id"] + ".jsonl")) for item in pair]
    )
    result.update(
        eligible=difference["repeatable"],
        reason="repeatable_own_baseline"
        if difference["repeatable"]
        else "own_baseline_nonrepeatable",
        repeat_comparison=difference,
    )
    return result


def _freeze_baselines(run, attempts, plan):
    eligibility = {
        name: _eligibility(name, run.path, attempts, plan) for name in ("rl", "mjpc")
    }
    path = run.path / "baseline-eligibility.json"
    write_new(path, {"head": run.result["head"], "eligibility": eligibility})
    run.result["baseline_eligibility"] = eligibility
    run.result["baseline_eligibility_sha256"] = digest(path)


def _frozen_eligibility(run):
    path = run.path / "baseline-eligibility.json"
    eligibility = run.result["baseline_eligibility"]
    if digest(path) != run.result["baseline_eligibility_sha256"] or strict_json(
        path.read_text()
    ) != {"head": run.result["head"], "eligibility": eligibility}:
        raise ValueError("frozen baseline eligibility changed")
    for own in eligibility.values():
        for baseline in own["baselines"]:
            if digest(run.path / (baseline["id"] + ".jsonl")) != baseline["raw_sha256"]:
                raise ValueError("frozen baseline raw SHA changed")
    return eligibility


def _challenge_binding(item, run):
    own = _frozen_eligibility(run)[item["controller"]]
    if not own["eligible"]:
        raise ValueError("ineligible baseline cannot enter challenge")
    reference = next(
        b for b in own["baselines"] if b["id"] == item["reference_baseline"]
    )
    binding = {
        "baseline_eligibility_sha256": run.result["baseline_eligibility_sha256"],
        "reference_baseline_sha256": reference["raw_sha256"],
    }
    if any(key in item and item[key] != value for key, value in binding.items()):
        raise ValueError("challenge baseline binding drifted")
    return binding


def _run_campaign(run, ledger, prepared_dir, prepared, plan, head):
    attempts = run.result["attempts"]
    setup_done = False
    for item in attempts:
        try:
            if item["stage"] == "challenge":
                if not run.result["baseline_eligibility"]:
                    _freeze_baselines(run, attempts, plan)
                own = _frozen_eligibility(run)[item["controller"]]
                if not own["eligible"]:
                    item["not_run_reason"] = own["reason"]
                    continue
                item.update(_challenge_binding(item, run))
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
                protocol_sha256=prepared["protocol_sha256"],
                capture_plan_sha256=prepared["capture_plan_sha256"],
            )
            try:
                write_new(run.path / "review.json", review)
                write_new(run.path / "authorization.json", authorization)
                for name in ("frozen-protocol.json", "capture-plan.json"):
                    with (run.path / name).open("xb") as stream:
                        stream.write((Path(prepared_dir) / name).read_bytes())
                _plan_identity(run.path, plan, prepared)
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
                    "capture_plan_sha256": prepared["capture_plan_sha256"],
                    "prepared_manifest_sha256": digest(
                        Path(prepared_dir) / "manifest.json"
                    ),
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
        identity = _plan_identity(directory, plan, record)
        reference = strict_json((directory / "preparation-reference.json").read_text())
        prepared_dir = Path(reference["path"])
        prepared = verify_bundle(prepared_dir)
        prepared_manifest = digest(prepared_dir / "manifest.json")
        if (
            reference["manifest_sha256"] != prepared_manifest
            or prepared.get("head") != record["head"]
            or prepared.get("scope") != "shared_campaign_preparation"
            or prepared.get("planned_arms") != arms(plan)
            or prepared.get("max_attempts") != 20
            or prepared.get("physics_steps_max") != 120000
            or _plan_identity(prepared_dir, plan, prepared) != identity
        ):
            raise ValueError("capture/preparation reference binding differs")
        qualification = prepared["qualification"]
        qdir = Path(qualification["path"])
        qrecord = verify_bundle(qdir)
        if (
            digest(qdir / "manifest.json") != qualification["manifest_sha256"]
            or qrecord["qualification_fingerprint"] != qualification["fingerprint"]
            or qrecord["qualification"]["head"] != qualification["producer_head"]
        ):
            raise ValueError("preparation/qualification reference binding differs")
        validate_review(
            strict_json((directory / "review.json").read_text()), record["head"]
        )
        authorization = strict_json((directory / "authorization.json").read_text())
        validate_authorization(
            authorization, dict(prepared, prepared_manifest_sha256=prepared_manifest)
        )
        if authorization.get("task_id") != plan["raw"]["id"]:
            raise ValueError("captured authorization belongs to another campaign")
        ledger = Path(ledger or ROOT / "_runs/substrate_attempts" / plan["raw"]["id"])
        known = arms(plan)
        attempts = record["attempts"]
        if len(attempts) != len(known):
            raise ValueError("captured arm catalog length differs")
        for index, (item, frozen) in enumerate(zip(attempts, known), 1):
            if item["index"] != index or any(item[k] != v for k, v in frozen.items()):
                raise ValueError("captured arm catalog differs")
        consumed_ids = {
            item["id"]
            for item in attempts
            if (directory / (item["id"] + "_claim.json")).exists()
        }
        if (
            type(record["scientific_attempts"]) is not int
            or record["scientific_attempts"] != len(consumed_ids)
            or record["live_runs"] != len(consumed_ids)
            or len(consumed_ids) > 20
            or any(
                type(a.get("physics_steps", 0)) is not int
                or a.get("physics_steps", 0) < 0
                for a in attempts
            )
            or record["canonical_physics_steps"]
            != sum(a.get("physics_steps", 0) for a in attempts)
            or record["canonical_physics_steps"] > 120000
        ):
            raise ValueError("captured attempt/step accounting differs")
        if set(p.name for p in ledger.iterdir()) != {
            "campaign.json",
            *[name + ".json" for name in consumed_ids],
        }:
            raise ValueError("external ledger membership differs")
        campaign = strict_json((ledger / "campaign.json").read_text())
        if campaign != strict_json((directory / "campaign-claim.json").read_text()):
            raise ValueError("campaign external claim differs")
        if campaign != {
            "head": record["head"],
            "output": str(directory),
            **identity,
            "prepared_manifest_sha256": prepared_manifest,
            "max_attempts": 20,
            "physics_steps_max": 120000,
            "planned_arms": known,
        }:
            raise ValueError("campaign claim binding differs")
        eligibility, eligibility_hash, stopped = None, None, None
        for item in attempts:
            status, name = item["status"], item["controller"]
            consumed = item["id"] in consumed_ids
            if item["stage"] == "challenge" and eligibility is None and stopped is None:
                eligibility = {
                    own: _eligibility(own, directory, attempts, plan)
                    for own in ("rl", "mjpc")
                }
                path = directory / "baseline-eligibility.json"
                if (
                    not path.is_file()
                    or strict_json(path.read_text())
                    != {"head": record["head"], "eligibility": eligibility}
                    or record["baseline_eligibility"] != eligibility
                    or record.get("baseline_eligibility_sha256") != digest(path)
                ):
                    raise ValueError(
                        "frozen baseline eligibility differs from raw replay"
                    )
                eligibility_hash = digest(path)
            if stopped is not None and status != "NOT_RUN":
                raise ValueError("arm executed after campaign stop")
            if status == "NOT_RUN":
                if (
                    consumed
                    or item.get("physics_steps", 0)
                    or "analysis" in item
                    or any(
                        (directory / (item["id"] + suffix)).exists()
                        for suffix in (
                            ".jsonl",
                            "_analysis.json",
                            "_failure.json",
                            ".native.stderr.log",
                        )
                    )
                ):
                    raise ValueError("skipped arm has execution evidence")
                if stopped is not None:
                    stop_case, stop_status = stopped
                    reason = (
                        "execution_or_evidence_failure"
                        if stop_status == "EXECUTION_EVIDENCE_STOP"
                        else stop_status
                    )
                    expected_reason = f"campaign_stopped:{stop_case}:{reason}"
                elif item["stage"] != "challenge" or eligibility[name]["eligible"]:
                    raise ValueError("eligible or baseline arm skipped")
                else:
                    expected_reason = eligibility[name]["reason"]
                if item["not_run_reason"] != expected_reason:
                    raise ValueError(
                        "skipped arm reason differs from replayed gate/stop"
                    )
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
                raise ValueError("invalid executed arm status")
            binding = {
                "baseline_eligibility_sha256": None,
                "reference_baseline_sha256": None,
            }
            if item["stage"] == "challenge":
                if not eligibility[name]["eligible"]:
                    raise ValueError("ineligible baseline entered challenge")
                reference = next(
                    b
                    for b in eligibility[name]["baselines"]
                    if b["id"] == item["reference_baseline"]
                )
                binding = {
                    "baseline_eligibility_sha256": eligibility_hash,
                    "reference_baseline_sha256": reference["raw_sha256"],
                }
                if any(item.get(key) != value for key, value in binding.items()):
                    raise ValueError("challenge reference binding differs")
            if consumed:
                claim = strict_json((ledger / (item["id"] + ".json")).read_text())
                if claim != strict_json(
                    (directory / (item["id"] + "_claim.json")).read_text()
                ):
                    raise ValueError("arm external claim differs")
                expected_claim = {
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
                    "raw": str(directory / (item["id"] + ".jsonl")),
                    "boundary": "first_post_handoff_state_control_sample",
                    "scope": "scientific",
                }
                if claim != expected_claim:
                    raise ValueError("arm external claim/reference binding differs")
            _check_analysis(item, directory, plan, consumed)
            if status in (
                "SAFETY_STOP",
                "EXPOSURE_EVIDENCE_STOP",
                "EXECUTION_EVIDENCE_STOP",
            ):
                stopped = (item["id"], status)
        if eligibility is None and (
            record["baseline_eligibility"]
            or record.get("baseline_eligibility_sha256") is not None
            or (directory / "baseline-eligibility.json").exists()
        ):
            raise ValueError("baseline eligibility exists before challenge stage")
        if stopped is None:
            if (
                record["status"] != "CAPTURE_COMPLETE"
                or record["campaign_complete"] is not True
                or record.get("stopped_case") is not None
            ):
                raise ValueError("campaign completion differs from arm sequence")
        elif (
            record["status"] != stopped[1]
            or record["campaign_complete"] is not False
            or record.get("stopped_case") != stopped[0]
        ):
            raise ValueError("campaign stop differs from arm sequence")
        return {
            "status": "VERIFIED",
            "head": record["head"],
            "capture_status": record["status"],
            "external_claims_checked": True,
            "baseline_eligibility_recomputed": eligibility is not None,
            "skip_stop_sequence_checked": True,
            "raw_sha_checked": True,
            "canonical_physics_steps": 0,
            "private_planning_calls": 0,
            "scientific_attempts_checked": len(consumed_ids),
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
