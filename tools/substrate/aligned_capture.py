"""Aligned capture preparation and externally authorized one-shot execution."""

from pathlib import Path
import json
import os
import subprocess
import time

from .aligned_anchor import load_anchor, validate_canonical_model
from .aligned_episode import replay_aligned_rows, run_aligned_episode
from .build_identity import verify_controller
from .contracts import PositionTargetControllerAdapter, ProprioceptivePolicyAdapter
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
from .model import dependency_manifest, physical_fingerprint
from .native_mjpc import NativeMJPCController
from .readiness import validate_authorization, validate_review
from .rl import FrozenPolicy
from .qualification import validate as validate_qualification, validate_reference

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = Path(__file__).with_name("protocols") / "aligned_flat_capture_v1.json"
LOCK = Path(__file__).with_name("sources.lock.json")
CHECKPOINT = ROOT / ".substrate/rl/policy.pt"
MJPC_BINARY = ROOT / ".substrate/headless-reliable/go2_mjpc_controller"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def validate_capture_plan(raw, plan_path=DEFAULT_PLAN):
    if raw.get("schema") != 1 or raw.get("id") not in (
        "aligned-flat-capture-v1",
        "aligned-flat-capture-v2",
    ):
        raise ValueError("unsupported aligned capture plan")
    expected = {
        "mode": "capture_preparation",
        "capture_order": ["rl", "mjpc"],
        "planned_attempts_per_controller": 1,
        "max_attempts": 2,
        "wall_timeout_s": 300,
        "self_authorizes_physics": False,
        "self_authorized_scientific_attempts": 0,
        "requires_external_start_authorization": True,
        "requires_exact_head_independent_review": True,
        "raw_evidence": "jsonl",
        "replay": "CanonicalEvaluator",
        "output_root": "example/cpp/experiments/_runs/" + raw["id"].replace("-", "_"),
    }
    for key, value in expected.items():
        if raw.get(key) != value:
            raise ValueError("aligned capture plan drifted: " + key)
    anchor_path = ROOT / raw["anchor"]
    if not anchor_path.is_file() or raw.get("anchor_sha256") != digest(anchor_path):
        raise ValueError("aligned capture anchor identity drifted")
    anchor = load_anchor(anchor_path)
    if (
        anchor["raw"]["physics_step_authorized"] is not False
        or anchor["raw"]["scientific_attempts_authorized"] != 0
    ):
        raise ValueError("capture preparation requires non-authorizing anchor")
    return {"raw": raw, "anchor": anchor, "plan_path": Path(plan_path)}


def load_capture_plan(path=DEFAULT_PLAN):
    return validate_capture_plan(strict_json(Path(path).read_text()), path)


def current_head():
    head = git("rev-parse", "HEAD")
    if git("status", "--porcelain"):
        raise ValueError("aligned capture preparation requires clean worktree")
    return head


def prepare(directory, plan_path=DEFAULT_PLAN, *, qualification_path=None):
    directory = Path(directory)
    if qualification_path is None:
        raise ValueError("clean qualification receipt required")
    with experiment_lock(), zero_step_guard():
        qualification = validate_qualification(qualification_path)
        plan = load_capture_plan(plan_path)
        anchor = plan["anchor"]
        head = current_head()
        lock = strict_json(LOCK.read_text())
        with EvidenceRun(
            directory, {"operation": "aligned_capture_prepare_zero_step"}
        ) as run:
            closure = dependency_manifest(ROOT / anchor["scenario"].scene, ROOT)
            for name, expected in closure["files"].items():
                target = run.path / "inputs" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
                if digest(target) != expected:
                    raise ValueError("canonical scene changed while snapshotting")
            plant = MujocoPlant(run.path / "inputs" / anchor["scenario"].scene)
            validate_canonical_model(anchor, plant.model)
            if plant.steps != 0 or plant.data.time != 0:
                raise ValueError("capture preparation advanced canonical physics")
            if digest(CHECKPOINT) != lock["rl"]["sha256"]:
                raise ValueError("RL checkpoint identity drifted")
            native = verify_controller(MJPC_BINARY)
            if native["inputs"]["mjpc"]["head"] != lock["mjpc"]["commit"]:
                raise ValueError("MJPC source identity drifted")
            write_new(run.path / "capture-plan.json", plan["raw"])
            write_new(run.path / "anchor.json", anchor["raw"])
            run.result.update(
                {
                    "status": "ENGINEERING_ADMITTED",
                    "readiness": "AWAITING_EXACT_HEAD_REVIEWS_AND_USER_START",
                    "head": head,
                    "qualification": qualification,
                    "protocol_sha256": digest(Path(plan_path)),
                    "anchor_sha256": digest(ROOT / plan["raw"]["anchor"]),
                    "max_attempts": plan["raw"]["max_attempts"],
                    "planned_arms": plan["raw"]["capture_order"],
                    "model": closure,
                    "physical_sha256": physical_fingerprint(plant.model),
                    "rl_checkpoint_sha256": lock["rl"]["sha256"],
                    "mjpc_source_commit": lock["mjpc"]["commit"],
                    "mjpc_binary_sha256": native["binary_sha256"],
                    "physics_steps": 0,
                    "scientific_attempts": 0,
                }
            )
    verify_bundle(directory)
    return {
        "readiness": "AWAITING_EXACT_HEAD_REVIEWS_AND_USER_START",
        "head": head,
        "physics_steps": 0,
        "scientific_attempts": 0,
        "output": str(directory),
    }


def validate_external_start(prepared, review, authorization, head, manifest_sha256):
    if prepared.get("readiness") != "AWAITING_EXACT_HEAD_REVIEWS_AND_USER_START":
        raise ValueError("aligned capture preparation is not start-ready")
    if prepared.get("head") != head:
        raise ValueError("aligned capture preparation head is stale")
    value = dict(prepared)
    value["prepared_manifest_sha256"] = manifest_sha256
    validate_review(review, head)
    validate_authorization(authorization, value)
    return True


def validate_start_files(
    prepared_dir, review_path, authorization_path, plan_path=DEFAULT_PLAN
):
    prepared_dir = Path(prepared_dir)
    prepared = verify_bundle(prepared_dir)
    head = current_head()
    validate_reference(prepared.get("qualification"))
    plan = load_capture_plan(plan_path)
    if prepared.get("protocol_sha256") != digest(Path(plan_path)):
        raise ValueError("capture plan changed since preparation")
    if prepared.get("anchor_sha256") != digest(ROOT / plan["raw"]["anchor"]):
        raise ValueError("anchor changed since preparation")
    lock = strict_json(LOCK.read_text())
    if digest(CHECKPOINT) != prepared.get("rl_checkpoint_sha256"):
        raise ValueError("RL checkpoint changed since preparation")
    native = verify_controller(MJPC_BINARY)
    if (
        native["binary_sha256"] != prepared.get("mjpc_binary_sha256")
        or native["inputs"]["mjpc"]["head"] != prepared.get("mjpc_source_commit")
        or native["inputs"]["mjpc"]["head"] != lock["mjpc"]["commit"]
    ):
        raise ValueError("MJPC identity changed since preparation")
    review = strict_json(Path(review_path).read_text())
    authorization = strict_json(Path(authorization_path).read_text())
    validate_external_start(
        prepared,
        review,
        authorization,
        head,
        digest(prepared_dir / "manifest.json"),
    )
    return {
        "head": head,
        "prepared": prepared,
        "review": review,
        "authorization": authorization,
    }


def _setup_runtime():
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(0)


def _make_controller(name, anchor, prepared, *, stderr_log_path=None):
    if name == "rl":
        _setup_runtime()
        policy = FrozenPolicy(CHECKPOINT, prepared["rl_checkpoint_sha256"])
        return ProprioceptivePolicyAdapter(policy), lambda: None
    if name == "mjpc":
        native = NativeMJPCController(
            MJPC_BINARY,
            anchor["controllers"]["mjpc"]["timing"],
            stderr_log_path=stderr_log_path,
        )
        adapter = PositionTargetControllerAdapter(
            native, native.actuator_spec, native.joint_names
        )
        return adapter, native.close
    raise ValueError("unknown aligned capture controller")


def _validate_output(plan, output):
    output = Path(output).absolute()
    root = (ROOT / plan["raw"]["output_root"]).absolute()
    if output.parent != root or not output.name.startswith("run_"):
        raise ValueError(
            "capture output must be a fresh run_* child of frozen output_root"
        )
    return output


def capture(
    prepared_dir, review_path, authorization_path, output, *, plan_path=DEFAULT_PLAN
):
    """Run exactly one RL arm and one MJPC arm after external authorization."""

    prepared_dir = Path(prepared_dir)
    with experiment_lock():
        # This gate must complete before output/plant/controller creation.
        start = validate_start_files(
            prepared_dir, review_path, authorization_path, plan_path
        )
        prepared = start["prepared"]
        head = start["head"]
        plan = load_capture_plan(plan_path)
        anchor = plan["anchor"]
        raw_plan = plan["raw"]
        output = _validate_output(plan, output)

        ledger = ROOT / "_runs/substrate_attempts" / raw_plan["id"]
        if ledger.exists():
            raise ValueError(
                "aligned capture campaign already claimed; no retry or replacement"
            )

        with EvidenceRun(output, {"operation": "formal_aligned_capture"}) as run:
            attempts = [
                {"index": index + 1, "controller": name, "status": "NOT_RUN"}
                for index, name in enumerate(raw_plan["capture_order"])
            ]
            run.result.update(
                {
                    "scope": "formal_aligned_engineering_capture",
                    "status": "FAILED",
                    "integration_status": "INCOMPLETE",
                    "head": head,
                    "attempts": attempts,
                    "live_runs": 0,
                    "scientific_attempts": 0,
                }
            )
            write_new(run.path / "review.json", start["review"])
            write_new(run.path / "authorization.json", start["authorization"])
            write_new(run.path / "capture-plan.json", raw_plan)
            write_new(run.path / "anchor.json", anchor["raw"])
            write_new(
                run.path / "preparation-reference.json",
                {
                    "path": str(prepared_dir.resolve()),
                    "manifest_sha256": digest(prepared_dir / "manifest.json"),
                },
            )

            ledger.mkdir(parents=True, exist_ok=False)
            campaign = {
                "head": head,
                "output": str(run.path.resolve()),
                "protocol_sha256": prepared["protocol_sha256"],
                "anchor_sha256": prepared["anchor_sha256"],
                "capture_order": raw_plan["capture_order"],
            }
            write_new(ledger / "campaign.json", campaign)
            write_new(run.path / "campaign-claim.json", campaign)

            results = {}
            for item in attempts:
                name = item["controller"]
                if current_head() != head:
                    raise ValueError("capture HEAD changed during campaign")
                verify_bundle(prepared_dir)
                validate_reference(prepared.get("qualification"))
                if digest(CHECKPOINT) != prepared["rl_checkpoint_sha256"]:
                    raise ValueError("RL checkpoint changed during capture")
                native_identity = verify_controller(MJPC_BINARY)
                if (
                    native_identity["binary_sha256"] != prepared["mjpc_binary_sha256"]
                    or native_identity["inputs"]["mjpc"]["head"]
                    != prepared["mjpc_source_commit"]
                ):
                    raise ValueError("MJPC identity changed during capture")

                plant = MujocoPlant(prepared_dir / "inputs" / anchor["scenario"].scene)
                validate_canonical_model(anchor, plant.model)
                controller, close = _make_controller(
                    name,
                    anchor,
                    prepared,
                    stderr_log_path=run.path / (name + ".native.stderr.log"),
                )
                raw = run.path / (name + ".jsonl")
                item["status"] = "BOOTING"
                consumed = False

                def consume():
                    nonlocal consumed
                    if consumed:
                        raise ValueError("attempt consumed more than once")
                    claim = {
                        "index": item["index"],
                        "controller": name,
                        "head": head,
                        "raw": str(raw.resolve()),
                        "boundary": "first_post_handoff_state_control_sample",
                    }
                    write_new(ledger / (name + ".json"), claim)
                    write_new(run.path / (name + "_claim.json"), claim)
                    item["status"] = "CAPTURING"
                    run.result["live_runs"] += 1
                    consumed = True

                started = time.monotonic()
                try:
                    with raw.open("x", encoding="utf-8") as stream:

                        def emit(row):
                            stream.write(
                                json.dumps(
                                    row,
                                    allow_nan=False,
                                    separators=(",", ":"),
                                    sort_keys=True,
                                )
                                + "\n"
                            )
                            stream.flush()

                        with wall_deadline(raw_plan["wall_timeout_s"]):
                            episode_result = run_aligned_episode(
                                plant,
                                controller,
                                anchor["task"],
                                anchor["controllers"][name]["information"],
                                anchor["controllers"][name]["timing"],
                                emit,
                                consume,
                            )
                        stream.flush()
                        os.fsync(stream.fileno())
                finally:
                    close()

                rows = [
                    strict_json(line) for line in raw.read_text().splitlines() if line
                ]
                replay = replay_aligned_rows(
                    rows, anchor["task"], anchor["physics_period_s"]
                )
                analysis = {
                    "controller": name,
                    "elapsed_s": time.monotonic() - started,
                    "episode": episode_result,
                    "replay": replay,
                    "frames": len(rows),
                    "physics_steps": plant.steps,
                    "controller_updates": sum(
                        1 for row in rows if row.get("controller_update")
                    ),
                }
                write_new(run.path / (name + "_analysis.json"), analysis)
                item.update(status=replay["verdict"], analysis=analysis)
                results[name] = analysis

            if run.result["live_runs"] != len(raw_plan["capture_order"]):
                raise ValueError("capture attempt accounting mismatch")
            run.result.update(
                {
                    "status": "CAPTURE_COMPLETE",
                    "integration_status": "CHARACTERIZED",
                    "controller_results": results,
                }
            )

    return {
        "status": run.result["status"],
        "integration_status": run.result["integration_status"],
        "head": head,
        "live_runs": run.result["live_runs"],
        "scientific_attempts": 0,
        "output": str(output),
        "results": results,
    }
