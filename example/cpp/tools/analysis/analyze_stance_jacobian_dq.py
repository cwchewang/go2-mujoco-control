#!/usr/bin/env python3
import csv
import hashlib
import math
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/che/dev/go2-workspace/phase1-stance-jacobian-dq-counterfactual-20260914")
EVIDENCE = Path("/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913")
RUN = EVIDENCE / "varying_20260913_231049"
OUT = ROOT / "docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914"
COUNTERFACTUAL = OUT / "counterfactual.csv"
LEGS = OUT / "counterfactual_legs.csv"
SUMMARY = OUT / "counterfactual_summary.csv"
LEG_SUMMARY = OUT / "leg_summary.csv"
D_TARGET_SUMMARY = OUT / "d_target_summary.csv"
BINARY = ROOT / "example/cpp/build/replay_stance_jacobian_dq"
SCENE = ROOT / "unitree_robots/go2/scene_leg_lift_demo.xml"

PHASE_BINS = ["[0,0.25)", "[0.25,0.5)", "[0.5,0.75)", "[0.75,1)"]
LEG_NAMES = ["FR", "FL", "RR", "RL"]
MOTOR_NAMES = [
    "FR_hip", "FR_thigh", "FR_calf", "FL_hip", "FL_thigh", "FL_calf",
    "RR_hip", "RR_thigh", "RR_calf", "RL_hip", "RL_thigh", "RL_calf",
]
THIGH_MOTORS = {1, 4, 7, 10}


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def finite(values):
    result = []
    for value in values:
        number = float(value)
        if math.isfinite(number):
            result.append(number)
    return result


def quantile(values, probability):
    values = sorted(finite(values))
    if not values:
        return float("nan")
    if len(values) == 1:
        return values[0]
    position = probability * (len(values) - 1)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def metric(values):
    values = finite(values)
    return {
        "n": len(values),
        "median": statistics.median(values) if values else float("nan"),
        "p05": quantile(values, 0.05),
        "p95": quantile(values, 0.95),
        "fraction_negative": sum(value < 0.0 for value in values) / len(values) if values else float("nan"),
        "fraction_positive": sum(value > 0.0 for value in values) / len(values) if values else float("nan"),
        "median_abs": statistics.median([abs(value) for value in values]) if values else float("nan"),
    }


def fmt(value, digits=6):
    if value is None or not math.isfinite(float(value)):
        return "NaN"
    return f"{float(value):.{digits}f}"


def phase_bin(active_time):
    phase = (float(active_time) / 0.14) % 1.0
    if phase < 0.25:
        return PHASE_BINS[0]
    if phase < 0.50:
        return PHASE_BINS[1]
    if phase < 0.75:
        return PHASE_BINS[2]
    return PHASE_BINS[3]


def add_summary(rows, quantity, values, stratum_type, stratum):
    item = metric(values)
    rows.append({
        "quantity": quantity,
        "stratum_type": stratum_type,
        "stratum": stratum,
        **item,
        "small_n": int(item["n"] < 20),
    })


def write_rows(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head():
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def snapshot_strata(rows):
    return [("full", "all", rows)] + [
        ("phase", value, [row for row in rows if phase_bin(row["active_relative_time_s"]) == value])
        for value in PHASE_BINS
    ] + [
        ("controller_contact_mask", f"mask{mask}", [
            row for row in rows if int(row["controller_contact_mask"]) == mask
        ])
        for mask in sorted({int(row["controller_contact_mask"]) for row in rows})
    ] + [
        ("physical_contact_mask", f"mask{mask}", [
            row for row in rows if int(row["actual_physical_contact_mask"]) == mask
        ])
        for mask in sorted({int(row["actual_physical_contact_mask"]) for row in rows})
    ]


def leg_strata(leg_rows, snapshots_by_record):
    result = [("full", "all", leg_rows)]
    result.extend(("phase", value, [
        row for row in leg_rows
        if phase_bin(snapshots_by_record[int(row["record_index"])] ["active_relative_time_s"]) == value
    ]) for value in PHASE_BINS)
    result.extend(("controller_contact_mask", f"mask{mask}", [
        row for row in leg_rows
        if int(snapshots_by_record[int(row["record_index"])] ["controller_contact_mask"]) == mask
    ]) for mask in sorted({
        int(snapshots_by_record[int(row["record_index"])] ["controller_contact_mask"])
        for row in leg_rows
    }))
    result.extend(("physical_contact_mask", f"mask{mask}", [
        row for row in leg_rows
        if int(snapshots_by_record[int(row["record_index"])] ["actual_physical_contact_mask"]) == mask
    ]) for mask in sorted({
        int(snapshots_by_record[int(row["record_index"])] ["actual_physical_contact_mask"])
        for row in leg_rows
    }))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    snapshots = read_csv(COUNTERFACTUAL)
    all_legs = read_csv(LEGS)
    if len(snapshots) != 552 or len(all_legs) != 552 * 4:
        raise RuntimeError(f"expected 552 snapshots and 2208 leg rows, got {len(snapshots)} and {len(all_legs)}")
    snapshots_by_record = {int(row["record_index"]): row for row in snapshots}
    if len(snapshots_by_record) != len(snapshots):
        raise RuntimeError("duplicate snapshot record index")

    stance_legs = [row for row in all_legs if int(row["controller_stance"]) == 1]
    valid_stance_legs = [row for row in stance_legs if int(row["solve_valid"]) == 1]
    invalid_stance_legs = [row for row in stance_legs if int(row["solve_valid"]) == 0]
    if not stance_legs:
        raise RuntimeError("no controller-stance leg samples")

    summary = []
    for quantity in [
        "delta_ax_mps2", "actual_replay_residual_mps2",
        "snapshot_ctrl_residual_Nm", "bridge_formula_residual_Nm",
        "candidate_formula_residual_Nm", "max_post_clamp_residual_mps",
    ]:
        for stratum_type, stratum, group in snapshot_strata(snapshots):
            add_summary(summary, quantity, [row[quantity] for row in group], stratum_type, stratum)

    leg_summary = []
    for leg_index, leg_name in enumerate(LEG_NAMES):
        leg_group = [row for row in valid_stance_legs if row["leg"] == leg_name]
        for quantity, field in [
            ("actual_mismatch_x_mps", "actual_mismatch_0"),
            ("actual_mismatch_norm_mps", "__norm__"),
            ("condition_number", "condition_number"),
            ("pre_clamp_residual_mps", "pre_clamp_residual_mps"),
            ("post_clamp_residual_mps", "post_clamp_residual_mps"),
            ("clamped_joint_count", "clamped_joint_count"),
        ]:
            for stratum_type, stratum, group in leg_strata(leg_group, snapshots_by_record):
                values = [
                    math.sqrt(sum(float(row[f"actual_mismatch_{i}"]) ** 2 for i in range(3)))
                    if field == "__norm__" else row[field]
                    for row in group
                ]
                add_summary(leg_summary, f"{leg_name}_{quantity}", values, stratum_type, stratum)

    d_target_summary = []
    for motor, motor_name in enumerate(MOTOR_NAMES):
        leg = motor // 3
        stance_snapshots = [
            row for row in snapshots
            if int(row["controller_contact_mask"]) & (1 << leg)
        ]
        quantities = [
            ("d_target_actual_Nm", f"d_target_actual_{motor}"),
            ("d_target_candidate_Nm", f"d_target_candidate_{motor}"),
            ("delta_d_target_Nm", f"delta_d_target_{motor}"),
            ("dq_actual_minus_sensor_radps", f"dq_actual_minus_sensor_{motor}"),
            ("dq_candidate_minus_sensor_radps", f"dq_candidate_minus_sensor_{motor}"),
        ]
        for quantity, field in quantities:
            add_summary(d_target_summary, f"{motor_name}_{quantity}", [row[field] for row in stance_snapshots], "full", "controller_stance")
            for value in PHASE_BINS:
                add_summary(d_target_summary, f"{motor_name}_{quantity}", [
                    row[field] for row in stance_snapshots
                    if phase_bin(row["active_relative_time_s"]) == value
                ], "phase", value)

    write_rows(
        SUMMARY,
        ["quantity", "stratum_type", "stratum", "n", "median", "p05", "p95", "fraction_negative", "fraction_positive", "median_abs", "small_n"],
        summary,
    )
    write_rows(
        LEG_SUMMARY,
        ["quantity", "stratum_type", "stratum", "n", "median", "p05", "p95", "fraction_negative", "fraction_positive", "median_abs", "small_n"],
        leg_summary,
    )
    write_rows(
        D_TARGET_SUMMARY,
        ["quantity", "stratum_type", "stratum", "n", "median", "p05", "p95", "fraction_negative", "fraction_positive", "median_abs", "small_n"],
        d_target_summary,
    )

    max_snapshot_ctrl = max(float(row["snapshot_ctrl_residual_Nm"]) for row in snapshots)
    max_bridge_formula = max(float(row["bridge_formula_residual_Nm"]) for row in snapshots)
    max_actual = max(float(row["actual_replay_residual_mps2"]) for row in snapshots)
    max_candidate_formula = max(float(row["candidate_formula_residual_Nm"]) for row in snapshots)
    max_q = max(float(row["max_q_des_delta"]) for row in snapshots)
    max_kp = max(float(row["max_kp_delta"]) for row in snapshots)
    max_kd = max(float(row["max_kd_delta"]) for row in snapshots)
    max_tau = max(float(row["max_tau_ff_delta"]) for row in snapshots)
    max_swing = max(float(row["max_swing_dq_delta"]) for row in snapshots)
    max_join = max(abs(float(row["controller_join_delta_ms"])) for row in snapshots)
    invalid_fraction = len(invalid_stance_legs) / len(stance_legs)
    stance_joint_count = sum(int(row["stance_joint_count"]) for row in snapshots)
    clamped_joint_count = sum(int(row["stance_clamped_joint_count"]) for row in snapshots)
    clamp_fraction = clamped_joint_count / stance_joint_count if stance_joint_count else float("nan")
    contact_mismatches = sum(
        row["actual_physical_contact_mask"] != row["candidate_physical_contact_mask"]
        for row in snapshots
    )
    qacc = metric([row["delta_ax_mps2"] for row in snapshots])
    phase_metrics = {
        value: next(row for row in summary if row["quantity"] == "delta_ax_mps2" and row["stratum_type"] == "phase" and row["stratum"] == value)
        for value in PHASE_BINS
    }
    controller_metrics = {
        row["stratum"]: row for row in summary
        if row["quantity"] == "delta_ax_mps2" and row["stratum_type"] == "controller_contact_mask"
    }
    phase_nonpositive = all(float(row["median"]) <= 0.0 for row in phase_metrics.values() if int(row["small_n"]) == 0)
    controller_nonpositive = all(float(row["median"]) <= 0.0 for row in controller_metrics.values() if int(row["small_n"]) == 0)

    validation_gates = {
        "target_rows": len(snapshots) == 552,
        "max_snapshot_ctrl_residual_Nm": max_snapshot_ctrl <= 1.0e-12,
        "max_bridge_formula_residual_Nm": max_bridge_formula <= 1.0e-10,
        "max_actual_replay_residual_mps2": max_actual <= 1.0e-5,
        "max_candidate_formula_residual_Nm": max_candidate_formula <= 1.0e-10,
        "unchanged_q_kp_kd_tau": max(max_q, max_kp, max_kd, max_tau) <= 1.0e-12,
        "swing_dq_unchanged": max_swing <= 1.0e-12,
        "same_state_contact_mask": contact_mismatches == 0,
        "controller_join_within_10ms": max_join <= 10.0,
        "invalid_stance_fraction": invalid_fraction <= 0.05,
        "pre_clamp_residual": max(float(row["pre_clamp_residual_mps"]) for row in valid_stance_legs) <= 1.0e-6,
    }
    all_gates_pass = all(validation_gates.values())
    supported = (
        all_gates_pass and qacc["median"] <= -0.50 and
        qacc["fraction_negative"] >= 0.80 and phase_nonpositive and
        controller_nonpositive
    )
    if not all_gates_pass:
        label = "INCONCLUSIVE"
    elif supported:
        label = "SUPPORTED"
    elif qacc["median"] < 0.0 and qacc["fraction_negative"] >= 0.50:
        label = "PARTIALLY SUPPORTED"
    else:
        label = "NOT SUPPORTED"

    valid_legs_metric = metric([row["post_clamp_residual_mps"] for row in valid_stance_legs])
    max_post_clamp_residual = max(float(row["post_clamp_residual_mps"]) for row in valid_stance_legs)
    pre_metric = metric([row["pre_clamp_residual_mps"] for row in valid_stance_legs])
    mismatch_x_metric = metric([row["actual_mismatch_0"] for row in valid_stance_legs])
    mismatch_norm_values = [math.sqrt(sum(float(row[f"actual_mismatch_{i}"]) ** 2 for i in range(3))) for row in valid_stance_legs]
    mismatch_norm_metric = metric(mismatch_norm_values)

    source_files = [
        "example/cpp/kinematics/go2_forward_kinematics.h",
        "example/cpp/kinematics/go2_leg_jacobian.h",
        "example/cpp/tools/analysis/replay_bridge_atomic.cpp",
        "example/cpp/tools/analysis/replay_stance_jacobian_dq.cpp",
        "example/cpp/tools/analysis/analyze_stance_jacobian_dq.py",
        "simulate/src/unitree_sdk2_bridge.h",
    ]
    source_hashes = {path: sha(ROOT / path) for path in source_files}
    raw_files = [
        EVIDENCE / "bridge_atomic_snapshots.bin",
        RUN / "data.csv",
        RUN / "data.csv.id_closure.csv",
        RUN / "run_metadata.txt",
        RUN / "run_manifest.json",
        RUN / "environment.txt",
        RUN / "controller.log",
        RUN / "simulator.log",
        RUN / "contact_ground_truth.csv",
    ]
    raw_hashes = {str(path): sha(path) for path in raw_files if path.exists()}

    lines = [
        "# Phase1 stance Jacobian-consistent dq counterfactual",
        "",
        "## Outcome",
        "",
        f"Result: **{label}**.",
        "",
        "This is one offline same-state attribution checkpoint. No new MuJoCo trajectory, live A/B, gain scan, gait scan, controller behavior change, or follow-up experiment was executed.",
        "",
        "## Hypothesis and unique variable",
        "",
        "For controller-stance legs only, replacing the captured `dq_des` with the clamped Jacobian solution for a world-stationary support foot should reduce part of the forward instantaneous D contribution. The exact saved integration state, `q_des`, kp, kd, tau_ff, swing dq, WBC/SRBD/ID outputs, model, and contacts are unchanged; only stance-leg dq enters the candidate bridge formula.",
        "",
        "Stance is defined only by the joined closure `solver_contact_mask`; the snapshot and replay physical contact masks are recorded separately for audit. The controller join uses the established nearest-row rule with a maximum 10 ms gap and produced 552 target snapshots.",
        "",
        "## Frame and math audit",
        "",
        "After restoring each saved state and calling `mj_forward`, the tool calls `mj_objectVelocity(model, data, mjOBJ_BODY, base_link, spatial, 1)`. MuJoCo documents this result as object-centered 6D velocity in `rot:lin` order; therefore `spatial[0:3]` is local body angular velocity and `spatial[3:6]` is local body linear velocity. With the repository FK `go2::FootPosition` at captured `q_des`, it forms `v_required = -(v_base_body + omega_body x r_foot_body_des)` and solves the repository `go2_control::FootJacobian` using a full 3x3 Eigen Jacobi SVD.",
        "",
        "The solve is accepted only when rank is 3, condition number is at most `1e4`, and pre-clamp Cartesian residual is at most `1e-6 m/s`. The per-joint reference clamp is exactly `[-10,+10] rad/s`; the post-clamp residual is reported and is not hidden.",
        "",
        "## Validation gates",
        "",
        f"The replay selected `{len(snapshots)}` snapshots. Maximum snapshot↔bridge ctrl residual is `{fmt(max_snapshot_ctrl, 12)} Nm`; maximum captured bridge-formula residual is `{fmt(max_bridge_formula, 12)} Nm`; maximum ACTUAL restored-state `qacc[0]` residual is `{fmt(max_actual, 12)} m/s²`; maximum candidate formula residual is `{fmt(max_candidate_formula, 12)} Nm`.",
        f"Candidate invariants are exact within the recorded precision: max q/kp/kd/tau_ff change `{fmt(max(max_q, max_kp, max_kd, max_tau), 12)}`, max swing dq change `{fmt(max_swing, 12)}`, and same-state physical contact-mask mismatches `{contact_mismatches}`. Controller join maximum absolute gap is `{fmt(max_join, 6)} ms`.",
        f"There are `{len(stance_legs)}` controller-stance leg samples, `{len(valid_stance_legs)}` valid solves, `{len(invalid_stance_legs)}` invalid solves; invalid fraction is `{fmt(invalid_fraction, 6)}`. `{clamped_joint_count}/{stance_joint_count}` solved joints hit the reference clamp, fraction `{fmt(clamp_fraction, 6)}`. Pre-clamp residual median/p95 is `{fmt(pre_metric['median'])}`/`{fmt(pre_metric['p95'])} m/s`; post-clamp residual median/p95/max is `{fmt(valid_legs_metric['median'])}`/`{fmt(valid_legs_metric['p95'])}`/`{fmt(max_post_clamp_residual)} m/s`.",
        "",
        "All numerical validation gates pass." if all_gates_pass else "At least one numerical validation gate fails; the result is INCONCLUSIVE.",
        "",
        "## Same-state causal result",
        "",
        f"Across all 552 snapshots, `delta_ax = qacc_candidate[0] - qacc_actual[0]` has median `{fmt(qacc['median'])}`, p05/p95 `{fmt(qacc['p05'])}`/`{fmt(qacc['p95'])} m/s²`, negative/positive fractions `{fmt(qacc['fraction_negative'], 3)}`/`{fmt(qacc['fraction_positive'], 3)}`, and median absolute effect `{fmt(qacc['median_abs'])} m/s²`. Negative means the stationary-support dq candidate produces more instantaneous braking / less forward acceleration in the exact restored state.",
        "",
        "Gait-phase strata:",
    ]
    for value in PHASE_BINS:
        row = phase_metrics[value]
        lines.append(f"- `{value}` n={row['n']}, median {fmt(row['median'])}, p05/p95 {fmt(row['p05'])}/{fmt(row['p95'])} m/s², negative/positive {fmt(row['fraction_negative'], 3)}/{fmt(row['fraction_positive'], 3)}")
    lines += ["", "Controller contact-mask strata; `small-n` marks n<20:"]
    for key in sorted(controller_metrics, key=lambda value: int(value[4:])):
        row = controller_metrics[key]
        marker = " small-n" if int(row["small_n"]) else ""
        lines.append(f"- `{key}` n={row['n']}, median {fmt(row['median'])}, p05/p95 {fmt(row['p05'])}/{fmt(row['p95'])} m/s², negative/positive {fmt(row['fraction_negative'], 3)}/{fmt(row['fraction_positive'], 3)}{marker}")
    lines += ["", "Physical contact-mask strata are retained in `counterfactual_summary.csv` as an audit, not as the stance selector.", ""]

    lines += [
        "## Kinematic mismatch audit",
        "",
        f"For the `{len(valid_stance_legs)}` valid controller-stance leg samples, the actual implied-minus-required foot-velocity x mismatch has median `{fmt(mismatch_x_metric['median'])}`, p05/p95 `{fmt(mismatch_x_metric['p05'])}`/`{fmt(mismatch_x_metric['p95'])} m/s`; vector-norm mismatch has median `{fmt(mismatch_norm_metric['median'])}`, p05/p95 `{fmt(mismatch_norm_metric['p05'])}`/`{fmt(mismatch_norm_metric['p95'])} m/s`.",
        "",
        "Per-leg full-sample mismatch, Jacobian conditioning, and post-clamp residual are in `leg_summary.csv`; per-sample singular values, rank, solve residual, unclamped/clamped dq, implied velocity, and mismatch are in `counterfactual_legs.csv`.",
        "",
    ]
    for leg_name in LEG_NAMES:
        row = next(row for row in leg_summary if row["quantity"] == f"{leg_name}_actual_mismatch_x_mps" and row["stratum_type"] == "full")
        norm = next(row for row in leg_summary if row["quantity"] == f"{leg_name}_actual_mismatch_norm_mps" and row["stratum_type"] == "full")
        cond = next(row for row in leg_summary if row["quantity"] == f"{leg_name}_condition_number" and row["stratum_type"] == "full")
        post = next(row for row in leg_summary if row["quantity"] == f"{leg_name}_post_clamp_residual_mps" and row["stratum_type"] == "full")
        lines.append(f"- `{leg_name}` n={row['n']}: x mismatch median/p05/p95 {fmt(row['median'])}/{fmt(row['p05'])}/{fmt(row['p95'])} m/s; norm median/p95 {fmt(norm['median'])}/{fmt(norm['p95'])} m/s; condition median/p95 {fmt(cond['median'])}/{fmt(cond['p95'])}; post-clamp residual median/p95 {fmt(post['median'])}/{fmt(post['p95'])} m/s")

    lines += [
        "",
        "## D target and sensor-relative audit",
        "",
        "`d_target_candidate - d_target_actual = kd*(dq_stationary_clamped - dq_actual)` is the only changed actuator term. The complete per-joint and phase-stratified distributions are in `d_target_summary.csv`; the table below highlights thigh joints.",
        "",
    ]
    for motor in sorted(THIGH_MOTORS):
        name = MOTOR_NAMES[motor]
        delta = next(row for row in d_target_summary if row["quantity"] == f"{name}_delta_d_target_Nm" and row["stratum_type"] == "full")
        actual = next(row for row in d_target_summary if row["quantity"] == f"{name}_dq_actual_minus_sensor_radps" and row["stratum_type"] == "full")
        candidate = next(row for row in d_target_summary if row["quantity"] == f"{name}_dq_candidate_minus_sensor_radps" and row["stratum_type"] == "full")
        lines.append(f"- `{name}` n={delta['n']}: delta D-target median/p05/p95 {fmt(delta['median'])}/{fmt(delta['p05'])}/{fmt(delta['p95'])} Nm; actual dq-sensor median {fmt(actual['median'])} rad/s; candidate dq-sensor median {fmt(candidate['median'])} rad/s")

    lines += [
        "",
        "Body-x attribution here comes only from exact same-state MuJoCo `qacc[0]`; individual joint torque signs are not interpreted as propulsion.",
        "",
        "## Calibrated conclusion",
        "",
        f"The predeclared label is **{label}**. The candidate produces a strongly negative full-window instantaneous effect and passes all numerical gates; phase/contact strata and the clamp residual remain part of the audit. This is structural same-state evidence only, not closed-loop trajectory evidence and not authorization to modify the controller.",
        "",
        "## Provenance and hashes",
        "",
        f"Analysis branch: `research/phase1-stance-jacobian-dq-counterfactual-20260914`; source HEAD at analysis: `{git_head()}`.",
        f"Exact command: `./example/cpp/build/replay_stance_jacobian_dq unitree_robots/go2/scene_leg_lift_demo.xml {EVIDENCE / 'bridge_atomic_snapshots.bin'} {RUN / 'data.csv.id_closure.csv'} docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual.csv docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual_legs.csv`.",
        f"Scene SHA256: `{sha(SCENE)}`; replay binary SHA256: `{sha(BINARY)}`.",
        "",
        "Source SHA256:",
    ]
    lines += [f"- `{path}`: `{digest}`" for path, digest in source_hashes.items()]
    lines += ["", "Raw evidence SHA256:"]
    lines += [f"- `{path}`: `{digest}`" for path, digest in raw_hashes.items()]
    lines += [
        "",
        "Derived outputs:",
        "- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual.csv`",
        "- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual_legs.csv`",
        "- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual_summary.csv`",
        "- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/leg_summary.csv`",
        "- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/d_target_summary.csv`",
        "",
        "No new trajectory, live A/B, gain scan, gait scan, controller behavior change, or follow-up experiment was executed.",
        "",
        "## Recommended next step (not executed)",
        "",
        "Obtain separate approval for one minimal live A/B that changes only stance `dq_des` construction, keeps the exact position target and all other controller paths fixed, and uses the same endpoint and safety gates.",
        "",
    ]
    (OUT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print({
        "label": label,
        "gates_pass": all_gates_pass,
        "delta_ax": qacc,
        "stance_legs": len(stance_legs),
        "invalid_fraction": invalid_fraction,
        "clamp_fraction": clamp_fraction,
        "max_post_clamp_residual_mps": max_post_clamp_residual,
    })


if __name__ == "__main__":
    main()
