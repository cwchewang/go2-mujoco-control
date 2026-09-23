"""No-integration audit: external claims, source policy replay and PD algebra."""

import math
import numpy as np

from .admit import ROOT
from .baseline_episode import (
    Plant,
    SourcePolicy,
    analyze,
    repeat_reference,
    safety,
    stop_after,
)
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
from .launch import setup_runtime
from .readiness import validate_authorization, validate_review


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_preflight(value, prepared, protocol):
    require(
        value.get("pass") is True and value.get("hard_failure_count") == 0,
        "preflight not passing",
    )
    require(
        value["git"]
        == dict(
            head=prepared["head"], branch=prepared["task"]["configuration"]["branch"]
        ),
        "preflight identity mismatch",
    )
    require(
        value["experiment_id"] == protocol["id"]
        and value["qualification"] == prepared["qualification_reference"],
        "preflight scope mismatch",
    )
    checks = {c["name"]: c for c in value["checks"]}
    require(
        all(c["status"] != "FAIL" for c in value["checks"]), "failed preflight check"
    )
    require(
        checks["runner_python_syntax"]["detail"]
        == str(ROOT / "tools/substrate/baseline.py"),
        "preflight runner mismatch",
    )
    require(
        checks["runner_unchanged_after_tests"]["detail"]
        == prepared["source_files"]["tools/substrate/baseline.py"],
        "preflight runner hash mismatch",
    )
    require(
        value["sol_review"]["approved_head"] == prepared["head"],
        "preflight review mismatch",
    )


def trace_consumed(rows):
    return any(r["applied"] is not None for r in rows)


def independent_body_vx(quaternion, velocity):
    # Same declared rotation polynomial without assuming a unit failure frame.
    w, *xyz = quaternion
    xyz, velocity = np.asarray(xyz), np.asarray(velocity)
    return float(
        (
            velocity
            - 2 * w * np.cross(xyz, velocity)
            + 2 * np.cross(xyz, np.cross(xyz, velocity))
        )[0]
    )


def audit_rows(rows, plant, policy, case, protocol):
    require(bool(rows), "empty trace")
    expected_target = policy.default.copy()
    updates = 0
    maximum_target_error = 0.0
    for tick, row in enumerate(rows):
        require(
            row["tick"] == tick and abs(row["time"] - tick * 0.002) < 1e-8,
            "trace clock",
        )
        command = [speed for start, speed in case["commands"] if start <= tick][-1]
        require(row["command"] == [command, 0.0, 0.0], "command schedule")
        require(
            np.isfinite(row["qpos"] + row["qvel"] + row["target"]).all(),
            "nonfinite trace",
        )
        if tick == 0:
            require(
                row["qpos"] == plant.data.qpos.tolist()
                and row["qvel"] == plant.data.qvel.tolist(),
                "reset mismatch",
            )
        plant.data.qpos[:] = row["qpos"]
        plant.data.qvel[:] = row["qvel"]
        plant.data.time = row["time"]
        rebuilt = plant.snapshot(tick)
        for key in (
            "feet",
            "terrain_height",
            "clearance",
            "ground_contacts",
            "base_contacts",
        ):
            require(rebuilt[key] == row[key], "telemetry mismatch: " + key)
        require(
            row["failure"] == safety(row, protocol), "safety classification mismatch"
        )
        active = tick < case["horizon_ticks"] and row["failure"] is None
        update = (
            active
            and tick >= case["first_inference_tick"]
            and tick % protocol["decimation"] == 0
        )
        require(
            (row["observation"] is not None) == update
            and (row["policy_wall_s"] is not None) == update,
            "policy cadence",
        )
        if update:
            assembled, expected_target = policy.act(plant.observe(), row["command"])
            require(
                np.array_equal(assembled, row["observation"]),
                "source observation mismatch",
            )
            updates += 1
        error = float(np.max(np.abs(expected_target - row["target"])))
        maximum_target_error = max(error, maximum_target_error)
        require(error == 0, "source target mismatch")
        if active:
            q, v = np.array(row["qpos"]), np.array(row["qvel"])
            independent = 20.0 * (expected_target - q[plant.qadr]) - 0.5 * v[plant.vadr]
            require(
                np.allclose(independent, row["requested"], rtol=0, atol=1e-12),
                "PD mismatch",
            )
            bounds = plant.model.actuator_ctrlrange[plant.aids]
            applied = [
                min(max(value, lo), hi) if limited else value
                for value, (lo, hi), limited in zip(
                    independent, bounds, plant.model.actuator_ctrllimited[plant.aids]
                )
            ]
            require(
                np.allclose(applied, row["applied"], rtol=0, atol=1e-12),
                "actuation mismatch",
            )
            plant.data.ctrl[plant.aids] = row["applied"]
        else:
            require(
                row["applied"] is None and row["requested"] is None, "terminal control"
            )
            require(tick == len(rows) - 1, "trace continued after stop")
    require(
        rows[-1]["failure"] is not None or rows[-1]["tick"] == case["horizon_ticks"],
        "truncated trace",
    )
    result = analyze(rows, case, protocol)
    # Independent scalar body-axis projection and MAE, not the analyzer helper.
    for window in result["windows"]:
        values = []
        for r in rows:
            if (
                window["start_tick"] + case["measurement_delay_ticks"]
                <= r["tick"]
                < window["end_tick"]
            ):
                values.append(independent_body_vx(r["qpos"][3:7], r["qvel"][:3]))
        if values:
            require(
                abs(
                    math.fsum(abs(v - window["command"]) for v in values) / len(values)
                    - window["mae"]
                )
                < 1e-10,
                "independent MAE mismatch",
            )
    return result, {
        "policy_updates_replayed": updates,
        "max_target_error": maximum_target_error,
        "contact_frames_rebuilt": len(rows),
        "physics_steps": 0,
    }


def verify(capture, prepared_path, output):
    with (
        experiment_lock(),
        zero_step_guard(),
        EvidenceRun(output, {"operation": "baseline_offline_verify"}) as run,
    ):
        setup_runtime()
        prepared = verify_bundle(prepared_path)
        admission = verify_manifest(capture)
        require(admission["status"] == "CAPTURE_COMPLETE", "capture incomplete")
        protocol = strict_json((capture / "protocol.json").read_text())
        require(
            protocol == strict_json((prepared_path / "protocol.json").read_text()),
            "protocol mismatch",
        )
        reference = strict_json((capture / "preparation-reference.json").read_text())
        require(
            reference["manifest_sha256"] == digest(prepared_path / "manifest.json"),
            "preparation mismatch",
        )
        prepared["prepared_manifest_sha256"] = reference["manifest_sha256"]
        validate_authorization(
            strict_json((capture / "authorization.json").read_text()), prepared
        )
        validate_review(prepared["review"], prepared["head"])
        audit_preflight(
            strict_json((capture / "preflight.json").read_text()), prepared, protocol
        )
        require(admission["head"] == prepared["head"], "capture head mismatch")
        ledger = ROOT / "_runs/substrate_attempts" / protocol["id"]
        claim = strict_json((capture / "campaign-claim.json").read_text())
        require(
            claim == strict_json((ledger / "campaign.json").read_text()),
            "external campaign mismatch",
        )
        require(
            claim
            == dict(
                head=prepared["head"],
                output=str(capture.resolve()),
                protocol_sha256=prepared["protocol_sha256"],
            ),
            "campaign identity mismatch",
        )
        require(
            len(admission["attempts"]) == protocol["max_attempts"],
            "attempt budget mismatch",
        )
        completed = {}
        audits = {}
        consumed = set()
        stopped = False
        for index, (case, item) in enumerate(
            zip(protocol["cases"], admission["attempts"])
        ):
            require(
                item["case"] == case["id"] and item["index"] == index + 1,
                "case identity mismatch",
            )
            raw = capture / (case["id"] + ".jsonl")
            dependency_failed = any(
                completed.get(n, {}).get("verdict") != "PASS" for n in case["requires"]
            )
            if stopped or dependency_failed:
                require(
                    item["status"] == "NOT_RUN" and not raw.exists(),
                    "run after stop/failed dependency",
                )
                continue
            require(
                item["status"] != "NOT_RUN" and raw.exists(), "missing prescribed case"
            )
            rows = [strict_json(line) for line in raw.read_text().splitlines()]
            if trace_consumed(rows):
                require(
                    strict_json((capture / (case["id"] + "_claim.json")).read_text())
                    == strict_json((ledger / (case["id"] + ".json")).read_text())
                    == dict(
                        index=index + 1,
                        case=case["id"],
                        head=prepared["head"],
                        raw=str(raw.resolve()),
                        boundary="first_post_handoff_state_control_sample",
                    ),
                    "external attempt mismatch",
                )
                consumed.add(case["id"] + ".json")
            else:
                require(
                    len(rows) == 1 and rows[0]["failure"] is not None,
                    "unconsumed trace is not initial safety stop",
                )
                require(
                    not (capture / (case["id"] + "_claim.json")).exists()
                    and not (ledger / (case["id"] + ".json")).exists(),
                    "claim without control sample",
                )
            plant = Plant(
                prepared_path / "inputs" / case["scene"],
                case,
                protocol["physics_period_s"],
            )
            policy = SourcePolicy(
                prepared_path / "inputs/.substrate/upstream-go2-30e74dc5",
                prepared_path / "inputs/.substrate/rl/policy.pt",
                prepared["source_inputs"][".substrate/rl/policy.pt"],
            )
            result, audit = audit_rows(rows, plant, policy, case, protocol)
            reference_case = repeat_reference(case)
            if reference_case is not None and result["trace_sha256"] != (
                completed[reference_case]["trace_sha256"]
            ):
                result.update(verdict="INTEGRITY_STOP", failure="trajectory_mismatch")
            stored = strict_json(
                (capture / (case["id"] + "_analysis.json")).read_text()
            )
            require(
                all(stored[k] == v for k, v in result.items())
                and stored == item["analysis"]
                and stored["verdict"] == item["status"],
                "analysis mismatch",
            )
            completed[case["id"]] = result
            audits[case["id"]] = audit
            stopped = stop_after(protocol, result["verdict"])
        require(
            {p.name for p in ledger.iterdir()} == consumed | {"campaign.json"},
            "external claim set mismatch",
        )
        require(admission["live_runs"] == len(consumed), "consumed count mismatch")
        write_new(run.path / "analysis.json", completed)
        write_new(run.path / "audits.json", audits)
        run.result.update(
            status="ENGINEERING_ADMITTED",
            verification="VERIFIED",
            external_ledger_checked=True,
            consumed=len(consumed),
            physics_steps=0,
            capture_manifest_sha256=digest(capture / "manifest.json"),
            prepared_manifest_sha256=digest(prepared_path / "manifest.json"),
        )
    return {"status": "VERIFIED", "consumed": len(consumed), "physics_steps": 0}
