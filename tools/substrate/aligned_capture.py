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

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = Path(__file__).with_name("protocols") / "aligned_flat_capture_v1.json"
LOCK = Path(__file__).with_name("sources.lock.json")
CHECKPOINT = ROOT / ".substrate/rl/policy.pt"
MJPC_BINARY = ROOT / ".substrate/headless-reliable/go2_mjpc_controller"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def validate_capture_plan(raw, plan_path=DEFAULT_PLAN):
    if raw.get("schema") != 1 or raw.get("id") != "aligned-flat-capture-v1":
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
        "output_root": "example/cpp/experiments/_runs/aligned_flat_capture_v1",
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


def prepare(directory, plan_path=DEFAULT_PLAN):
    directory = Path(directory)
    with experiment_lock(), zero_step_guard():
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
