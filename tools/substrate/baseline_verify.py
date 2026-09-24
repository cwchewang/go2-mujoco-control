"""No-integration audit: external claims, source policy replay and PD algebra."""

import math
import numpy as np

from .admit import ROOT
from .baseline_episode import (
    Plant,
    SourcePolicy,
    analyze,
    command_at,
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
from .rl import DEFAULT, FrozenPolicy, observation45


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


def independent_body_twist(quaternion, velocity):
    """Independent inverse-quaternion projection for all commanded axes."""
    w, *xyz = quaternion
    xyz = np.asarray(xyz, dtype=np.float64)
    linear, angular = np.asarray(velocity[:3]), np.asarray(velocity[3:6])

    def rotate(vector):
        return (
            vector * (2 * w * w - 1)
            - 2 * w * np.cross(xyz, vector)
            + 2 * xyz * np.dot(xyz, vector)
        )

    body_linear, body_angular = rotate(linear), rotate(angular)
    return dict(vx=float(body_linear[0]), vy=float(body_linear[1]), wz=float(body_angular[2]))


def replay_policy_action(plant, policy, case, command):
    observation = plant.observe()
    if case["adapter"]:
        assembled = observation45(observation, command, policy.previous_action)
        action = policy.act(observation, command)
        return assembled, action.position_target
    return policy.act(observation, command)


def audit_rows(rows, plant, policy, case, protocol):
    require(bool(rows), "empty trace")
    expected_target = DEFAULT.copy() if case["adapter"] else policy.default.copy()
    updates = 0
    maximum_target_error = 0.0
    for tick, row in enumerate(rows):
        require(
            row["tick"] == tick
            and abs(row["time"] - tick * protocol["physics_period_s"]) < 1e-8,
            "trace clock",
        )
        command = command_at(case, tick)
        require(row["command"] == command, "command schedule")
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
            assembled, expected_target = replay_policy_action(
                plant, policy, case, row["command"]
            )
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
    if protocol.get("schema") == 2:
        _audit_capability_metrics(rows, case, protocol, result)
    else:
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
                        math.fsum(
                            abs(v - window["command"]) for v in values
                        )
                        / len(values)
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


def _audit_capability_metrics(rows, case, protocol, result):
    actual = [
        independent_body_twist(row["qpos"][3:7], row["qvel"]) for row in rows
    ]
    for window in result["windows"]:
        commands = [
            row
            for row in case["commands"]
            if row[0] == window["start_tick"]
        ]
        require(len(commands) == 1, "unknown capability command window")
        command = commands[0][1:]
        selected = [
            i
            for i, row in enumerate(rows)
            if window["start_tick"] + case["measurement_delay_ticks"]
            <= row["tick"]
            < window["end_tick"]
        ]
        for name, value in zip(("vx", "vy", "wz"), command):
            if name not in case["track_axes"]:
                continue
            metrics = window["axes"][name]
            values = [actual[i][name] for i in selected]
            errors = [v - value for v in values]
            require(metrics["samples"] == len(values), "axis sample count mismatch")
            if not values:
                require(metrics["mae"] is None, "empty axis window has metrics")
                continue
            mean = math.fsum(values) / len(values)
            mae = math.fsum(abs(error) for error in errors) / len(errors)
            rmse = math.sqrt(math.fsum(error * error for error in errors) / len(errors))
            require(
                abs(mean - metrics["mean"]) < 1e-10
                and abs(mae - metrics["mae"]) < 1e-10
                and abs(rmse - metrics["rmse"]) < 1e-10,
                "independent body-axis metrics mismatch",
            )

    complete = rows[-1]["tick"] == case["horizon_ticks"]
    tracking_pass = complete and all(
        metrics["mae"] is not None
        and metrics["mae"]
        <= max(
            protocol["tracking_absolute_tolerance"],
            protocol["tracking_relative_tolerance"] * abs(metrics["command"]),
        )
        for window in result["windows"]
        for metrics in window["axes"].values()
    )
    require(result["tracking_pass"] == tracking_pass, "tracking gate mismatch")

    initial = rows[0]["qpos"]
    yaw = [
        math.atan2(
            2 * (row["qpos"][3] * row["qpos"][6] + row["qpos"][4] * row["qpos"][5]),
            1 - 2 * (row["qpos"][5] ** 2 + row["qpos"][6] ** 2),
        )
        for row in rows
    ]
    yaw = np.unwrap(yaw) - yaw[0]
    flat_cross_axis_pass = True
    if case.get("flat_probe", False):
        dx = max(abs(row["qpos"][0] - initial[0]) for row in rows)
        dy = max(abs(row["qpos"][1] - initial[1]) for row in rows)
        if "wz" in case["track_axes"]:
            flat_cross_axis_pass = max(dx, dy) <= protocol["flat_cross_axis_max"]
        elif "vy" in case["track_axes"]:
            flat_cross_axis_pass = dx <= protocol["flat_cross_axis_max"]
        else:
            flat_cross_axis_pass = dy <= protocol["flat_cross_axis_max"]
        if "wz" not in case["track_axes"]:
            flat_cross_axis_pass = flat_cross_axis_pass and max(map(abs, yaw)) <= protocol[
                "flat_cross_axis_max"
            ]
    require(
        result["flat_cross_axis_pass"] == flat_cross_axis_pass,
        "flat cross-axis gate mismatch",
    )

    if case.get("reference_gate", False):
        mean_vx = result["windows"][0]["axes"]["vx"]["mean"]
        require(
            result["reference_mean_vx"] == mean_vx
            and result["reference_pass"]
            == (mean_vx is not None and mean_vx >= protocol["reference_mean_min"]),
            "flat reference gate mismatch",
        )
    else:
        require(result["reference_pass"] is True, "unexpected reference gate failure")

    if "terrain_goal" in case:
        goal = case["terrain_goal"]
        edge = goal["terrain_x_max"]
        initial_y = initial[1]
        holds, maximum = 0, 0
        for row in rows:
            reached = (
                row["qpos"][0] >= edge + goal["base_clearance_m"]
                and min(foot[0] for foot in row["feet"])
                >= edge + goal["foot_clearance_m"]
                and abs(row["qpos"][1] - initial_y)
                <= goal["route_lateral_max_m"]
            )
            holds = holds + 1 if reached else 0
            maximum = max(maximum, holds)
        route = [
            row
            for row in rows
            if goal["terrain_x_min"]
            <= row["qpos"][0]
            <= goal["terrain_x_max"]
        ]
        route_pass = bool(route) and all(
            abs(row["qpos"][1] - initial_y) <= goal["route_lateral_max_m"]
            for row in route
        )
        task_goal_pass = complete and route_pass and maximum >= goal["hold_ticks"]
        require(
            result["task_goal_pass"] == task_goal_pass
            and result["route_pass"] == route_pass
            and result["task_goal_maximum_hold_ticks"] == maximum,
            "terrain goal mismatch",
        )
    else:
        task_goal_pass = None

    failure_classes = []
    if rows[-1]["failure"]:
        failure_classes.append("SAFETY_STOP")
    else:
        if not tracking_pass or not flat_cross_axis_pass or not result["reference_pass"]:
            failure_classes.append("TRACKING_FAILURE")
        if task_goal_pass is False:
            failure_classes.append("TASK_GOAL_FAILURE")
    verdict = (
        "SAFETY_STOP"
        if "SAFETY_STOP" in failure_classes
        else ("PERFORMANCE_FAIL" if failure_classes else "PASS")
    )
    require(
        result["failure_classes"] == failure_classes and result["verdict"] == verdict,
        "capability classification mismatch",
    )


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
            if case["adapter"]:
                policy = FrozenPolicy(
                    prepared_path / "inputs/.substrate/rl/policy.pt",
                    prepared["source_inputs"][".substrate/rl/policy.pt"],
                )
            else:
                policy = SourcePolicy(
                    prepared_path / "inputs/.substrate/upstream-go2-30e74dc5",
                    prepared_path / "inputs/.substrate/rl/policy.pt",
                    prepared["source_inputs"][".substrate/rl/policy.pt"],
                )
            result, audit = audit_rows(rows, plant, policy, case, protocol)
            reference_case = repeat_reference(case)
            if (
                reference_case is not None
                and result["trace_sha256"]
                != (completed[reference_case]["trace_sha256"])
            ):
                result.update(verdict="INTEGRITY_STOP", failure="trajectory_mismatch")
                if "failure_classes" in result:
                    result["failure_classes"] = ["INTEGRITY_STOP"]
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
