"""Freeze an independent RL friction protocol and precheck sealed references.

This preparation module has no capture/START entry and does not call controllers.
The existing shared episode, condition hook, primary replay and STOP engine remain
unchanged. Live binding/qualification is a separate execution admission step.
"""

import argparse
import hashlib
from dataclasses import replace
import math
import subprocess
from pathlib import Path

import numpy as np

from . import shared_campaign as shared
from .aligned_anchor import validate_canonical_model
from .bounded_conditions import BoundedCondition, condition_specs
from .episode import MujocoPlant
from .guards import zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_manifest,
    write_new,
)
from .model import dependency_manifest, physical_fingerprint
from .shared_baseline import load_plan as load_inherited_plan

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = (
    Path(__file__).with_name("protocols") / "rl_sliding_friction_reference_v1.json"
)
PROTOCOL_SHA256 = "d10719424809db2037a01f755786b4f93c20ad6cfe2db1455e847ef0f57da89d"


def load_plan(path=DEFAULT_PROTOCOL):
    path = Path(path)
    if digest(path) != PROTOCOL_SHA256:
        raise ValueError("independent frozen protocol drifted")
    frozen = strict_json(path.read_text())
    inherited_path = ROOT / frozen["inherit_protocol"]
    if digest(inherited_path) != frozen["inherit_protocol_sha256"]:
        raise ValueError("inherited contracts drifted")
    inherited = load_inherited_plan(inherited_path)
    card = {k: v for k, v in frozen["condition"].items() if k != "id"}
    if (
        card != inherited["raw"]["conditions"]["sliding_friction"]
        or frozen["performance"] != inherited["raw"]["performance"]
        or frozen["physics_steps_max"]
        != frozen["max_attempts"] * frozen["horizon_ticks"]
    ):
        raise ValueError("frozen intervention or budget differs from inherited runner")
    raw = {
        **inherited["raw"],
        **frozen,
        "conditions": {"sliding_friction": card},
        "measurement_start_tick": frozen["primary_measurement"]["start_tick"],
        "measurement_end_tick_exclusive": frozen["primary_measurement"][
            "end_tick_exclusive"
        ],
    }
    return {
        **inherited,
        "raw": raw,
        "frozen": frozen,
        "task": replace(inherited["task"], task_id=frozen["id"]),
        "controllers": {"rl": inherited["controllers"]["rl"]},
    }


def arms(plan):
    return [
        {
            "id": f"rl_friction_{j}",
            "controller": "rl",
            "stage": "challenge",
            "repeat": j,
            "condition": "sliding_friction",
            "reference_baseline": f"rl_baseline_{j}",
        }
        for j in (1, 2)
    ]


def auxiliary_window(rows):
    """Prospective [6,12) scalar body-vx metrics; partial horizons stay unscored."""
    velocities = []
    for expected_tick, row in enumerate(rows):
        if type(row["tick"]) is not int or row["tick"] != expected_tick:
            raise ValueError("auxiliary raw tick sequence drifted")
        if not math.isclose(
            row["sim_time_s"], expected_tick * 0.002, rel_tol=0, abs_tol=1e-9
        ):
            raise ValueError("auxiliary raw clock drifted")
        q, v = (
            np.asarray(row["qpos"], dtype=float),
            np.asarray(row["qvel"], dtype=float),
        )
        if (
            q.shape != (19,)
            or v.shape != (18,)
            or not np.isfinite(q).all()
            or not np.isfinite(v).all()
        ):
            raise ValueError("auxiliary raw state invalid")
        if 3000 <= expected_tick < 6000:
            w, x, y, z = q[3:7]
            velocities.append(
                (w * w + x * x - y * y - z * z) * v[0]
                + 2 * (x * y + w * z) * v[1]
                + 2 * (x * z - w * y) * v[2]
            )
    complete = len(rows) == 6001 and rows[-1]["terminal_reason"] == "horizon"
    result = {
        "status": "COMPLETE" if complete else "NOT_MEASURABLE",
        "measurement_window": "[6,12)",
        "measurement_samples": len(velocities),
        "endpoint_in_performance_mean": False,
        "body_vx_mean_mps": None,
        "body_vx_mae_mps": None,
        "affects_primary_classification": False,
    }
    if complete:
        if len(velocities) != 3000:
            raise ValueError("auxiliary half-open sample count drifted")
        result.update(
            body_vx_mean_mps=float(np.mean(velocities)),
            body_vx_mae_mps=float(np.mean(np.abs(np.asarray(velocities) - 1.0))),
        )
    return result


def paired_auxiliary(rows, baseline_rows):
    actual, reference = auxiliary_window(rows), auxiliary_window(baseline_rows)
    complete = actual["status"] == reference["status"] == "COMPLETE"
    return {
        "actual": actual,
        "reference": reference,
        "paired_mean_delta_mps": actual["body_vx_mean_mps"]
        - reference["body_vx_mean_mps"]
        if complete
        else None,
        "paired_mae_delta_mps": actual["body_vx_mae_mps"] - reference["body_vx_mae_mps"]
        if complete
        else None,
    }


def static_inputs(plan):
    plant = MujocoPlant(ROOT / plan["scenario"].scene)
    validate_canonical_model(plan, plant.model)
    config = plan["controllers"]["rl"]
    information, timing = condition_specs(
        "sliding_friction", config["information"], config["timing"]
    )
    condition = BoundedCondition("sliding_friction")
    condition.reset(plant, information, timing)
    if (
        plant.steps != 0
        or plant.data.time != 0
        or information != config["information"]
        or timing != config["timing"]
    ):
        raise ValueError(
            "static friction preparation changed timing or advanced physics"
        )
    if digest(shared.CHECKPOINT) != config["raw"]["checkpoint_sha256"]:
        raise ValueError("inherited checkpoint differs")
    closure = dependency_manifest(ROOT / plan["scenario"].scene, ROOT)
    return plant, closure


def precheck(output, protocol_path=DEFAULT_PROTOCOL):
    """Official old-raw verification plus new frozen-config/static-model checks."""
    plan = load_plan(protocol_path)
    frozen = plan["frozen"]
    capture = ROOT / frozen["reference_capture"]
    if digest(capture / "manifest.json") != frozen["reference_capture_manifest_sha256"]:
        raise ValueError("sealed reference capture identity differs")
    # This verifier acquires the existing lock itself and never calls a controller.
    verified = shared.verify_capture(capture, ledger=ROOT / frozen["reference_ledger"])
    with experiment_lock(), zero_step_guard():
        if shared.base.git("branch", "--show-current") != frozen["expected_branch"]:
            raise ValueError("prospective preparation requires its named branch")
        head = shared.base.current_head()
        if (ROOT / frozen["ledger_root"]).exists() or (
            ROOT / frozen["output_root"]
        ).exists():
            raise ValueError(
                "new campaign already has an output/ledger; no replacement"
            )
        source = verify_manifest(capture)
        if (
            source["head"] != frozen["reference_capture_head"]
            or source["status"] != "SAFETY_STOP"
            or source["scientific_attempts"] != 3
            or source["canonical_physics_steps"] != 13287
            or sum(a["status"] == "NOT_RUN" for a in source["attempts"]) != 17
            or digest(capture / "manifest.json")
            != frozen["reference_capture_manifest_sha256"]
        ):
            raise ValueError("old campaign closure differs")
        inherited = load_inherited_plan(ROOT / frozen["inherit_protocol"])
        eligible = shared._eligibility("rl", capture, source["attempts"], inherited)
        if not eligible["eligible"]:
            raise ValueError("sealed own RL pair is ineligible")
        references, auxiliary = [], {}
        for expected, actual in zip(
            frozen["reference_baselines"], eligible["baselines"]
        ):
            if (
                actual["id"] != expected["id"]
                or actual["raw_sha256"] != expected["raw_sha256"]
            ):
                raise ValueError("sealed repeat pairing/hash differs")
            name = expected["id"]
            references.append(
                {
                    **expected,
                    "producer_head": source["head"],
                    "capture_claim_sha256": digest(capture / (name + "_claim.json")),
                    "external_claim_sha256": digest(
                        ROOT / frozen["reference_ledger"] / (name + ".json")
                    ),
                    "classification": actual["classification"],
                    "role": "read_only_reference_not_new_attempt",
                }
            )
            auxiliary[name] = auxiliary_window(
                shared._read_rows(capture / (name + ".jsonl"))
            )
        plant, closure = static_inputs(plan)
        preparation_reference = strict_json(
            (capture / "preparation-reference.json").read_text()
        )
        prepared = verify_manifest(preparation_reference["path"])
        runtime_paths = [
            "shared_campaign.py",
            "shared_baseline.py",
            "bounded_conditions.py",
            "condition_evidence.py",
            "aligned_episode.py",
            "aligned_anchor.py",
            "rl.py",
            "evaluator.py",
            "episode.py",
            "model.py",
            "integrity.py",
            "guards.py",
            "qualification.py",
            "launch.py",
            "readiness.py",
        ]
        source_hashes = {
            "tools/substrate/" + name: digest(ROOT / "tools/substrate" / name)
            for name in runtime_paths
        }
        for relative, expected in source_hashes.items():
            original = subprocess.check_output(
                ["git", "show", source["head"] + ":" + relative], cwd=ROOT
            )
            if hashlib.sha256(original).hexdigest() != expected:
                raise ValueError("inherited runtime source changed: " + relative)
        chain = {
            "capture": str(capture),
            "manifest_sha256": frozen["reference_capture_manifest_sha256"],
            "producer_head": source["head"],
            "prepared": preparation_reference,
            "source_qualification": prepared["qualification"],
            "source_qualification_is_new_head_admission": False,
            "own_rl_baseline_eligibility": eligible,
            "paired_references": references,
            "external_ledger_files": {
                p.name: digest(p)
                for p in sorted((ROOT / frozen["reference_ledger"]).glob("*.json"))
            },
            "old_not_run_count": 17,
            "old_campaign_status": "PERMANENTLY_CLOSED",
        }
        with EvidenceRun(
            Path(output), {"operation": "prospective_rl_friction_freeze_precheck"}
        ) as run:
            (run.path / "frozen-protocol.json").write_bytes(
                Path(protocol_path).read_bytes()
            )
            write_new(run.path / "planned-arms.json", arms(plan))
            write_new(run.path / "reference-chain.json", chain)
            write_new(run.path / "source-verification.json", verified)
            write_new(run.path / "auxiliary-reference.json", auxiliary)
            write_new(run.path / "unchanged-runtime-source-hashes.json", source_hashes)
            write_new(run.path / "model-dependencies.json", closure)
            run.result.update(
                status="PRECHECK_PASS",
                scope="prospective_spec_reference_static_precheck",
                head=head,
                branch=frozen["expected_branch"],
                protocol_sha256=digest(Path(protocol_path)),
                max_attempts=2,
                physics_steps_max=12000,
                physical_sha256=physical_fingerprint(plant.model),
                physics_step_authorized=False,
                canonical_physics_steps=0,
                private_planning_calls=0,
                scientific_attempts=0,
                readiness=frozen["live_readiness"],
                live_execution_admission="NOT_CREATED",
                execution_remaining="Bind independent two-arm catalog and sealed RL references to unchanged engine; new exact-head qualification/preflight and incremental reviews before START",
                checks=[
                    "strict_frozen_protocol_and_inherited_loader",
                    "official_source_capture_real_ledger_verifier",
                    "two_passing_repeatable_own_rl_references",
                    "old_campaign_closed_17_NOT_RUN",
                    "static_canonical_model_and_checkpoint",
                    "friction_reset_does_not_change_RL_information_or_timing",
                    "half_open_auxiliary_reference_samples",
                    "new_campaign_output_and_ledger_absent",
                ],
            )
    record = verify_manifest(output)
    return {
        "head": head,
        "status": record["status"],
        "output": str(output),
        "manifest_sha256": digest(Path(output) / "manifest.json"),
        "canonical_physics_steps": 0,
        "private_planning_calls": 0,
        "scientific_attempts": 0,
        "live_execution_admission": "NOT_CREATED",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(precheck(args.output))


if __name__ == "__main__":
    main()
