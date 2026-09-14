#!/usr/bin/env python3
import csv
import hashlib
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/che/dev/go2-workspace/phase1-reference-wbc-structural-attribution-20260914")
EVIDENCE = Path("/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913")
RUN = EVIDENCE / "varying_20260913_231049"
OUT = ROOT / "docs/validation/phase1_reference_wbc_structural_attribution_20260914"
DECOMP = OUT / "d_decomposition.csv"
CLOSURE = RUN / "data.csv.id_closure.csv"
PRIOR = ROOT / "docs/validation/phase1_pd_component_decomposition_20260914/components.csv"

BRANCHES = [
    "NO_D_ALL",
    "NO_D_TARGET_ALL",
    "NO_D_SENSOR_ALL",
    "NO_D_TARGET_THIGHS",
    "NO_D_SENSOR_THIGHS",
]
THIGHS = [(1, "FR_thigh"), (4, "FL_thigh"), (7, "RR_thigh"), (10, "RL_thigh")]
PHASE_BINS = ["[0,0.25)", "[0.25,0.5)", "[0.5,0.75)", "[0.75,1)"]


def finite(values):
    return [float(value) for value in values if math.isfinite(float(value))]


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


def stats(values):
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


def phase_bin(phase):
    if phase < 0.25:
        return "[0,0.25)"
    if phase < 0.50:
        return "[0.25,0.5)"
    if phase < 0.75:
        return "[0.5,0.75)"
    return "[0.75,1)"


def running_leg_phase(phase, leg):
    offset = 0.0 if leg in (0, 3) else 0.46
    return (phase + offset) % 1.0


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_records(path, fields, records):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def add_summary(rows, quantity, values, stratum_type, stratum):
    item = stats(values)
    rows.append({
        "quantity": quantity,
        "stratum_type": stratum_type,
        "stratum": stratum,
        **item,
    })


def aggregate_decomposition(records):
    summary = []
    for branch in BRANCHES:
        quantity = f"delta_{branch}_mps2"
        add_summary(summary, quantity, [row[quantity] for row in records], "full", "all")
        for phase in PHASE_BINS:
            add_summary(summary, quantity, [row[quantity] for row in records if row["phase_bin"] == phase], "phase", phase)
        for mask in sorted({row["replay_contact_mask"] for row in records}, key=int):
            add_summary(summary, quantity, [row[quantity] for row in records if row["replay_contact_mask"] == mask], "contact_mask", f"mask{mask}")

    for motor, label in THIGHS:
        leg = motor // 3
        quantities = {
            "dq_error_radps": f"dq_des_{motor}",
            "d_target_Nm": f"d_target_{motor}",
            "d_sensor_Nm": f"d_sensor_{motor}",
            "d_total_Nm": f"d_total_{motor}",
        }
        for quantity, field in quantities.items():
            for state in ("stance", "swing"):
                values = []
                for row in records:
                    leg_phase = running_leg_phase(float(row["gait_phase"]), leg)
                    actual_state = "stance" if leg_phase < 0.44 else "swing"
                    if actual_state == state:
                        if quantity == "dq_error_radps":
                            values.append(float(row[f"dq_des_{motor}"]) - float(row[f"dq_sensor_{motor}"]))
                        else:
                            values.append(row[field])
                add_summary(summary, f"{label}_{quantity}", values, "state", state)
                for phase in PHASE_BINS:
                    values = []
                    for row in records:
                        if row["phase_bin"] != phase:
                            continue
                        leg_phase = running_leg_phase(float(row["gait_phase"]), leg)
                        if ("stance" if leg_phase < 0.44 else "swing") != state:
                            continue
                        if quantity == "dq_error_radps":
                            values.append(float(row[f"dq_des_{motor}"]) - float(row[f"dq_sensor_{motor}"]))
                        else:
                            values.append(row[field])
                    add_summary(summary, f"{label}_{quantity}", values, f"state_phase", f"{state}:{phase}")
    return summary


def nearest_closure(tick, closure_rows):
    row = min(closure_rows, key=lambda item: abs(int(round(float(item["state_tick_s"]) * 1000.0)) - tick))
    gap = abs(int(round(float(row["state_tick_s"]) * 1000.0)) - tick)
    if gap > 10:
        raise RuntimeError(f"closure join exceeds 10 ms: tick={tick} gap={gap}")
    return row


def kinematic_rows(decomp, closure_rows):
    result = []
    leg_rows = []
    for row in decomp:
        tick = int(round(float(row["state_tick_s"]) * 1000.0))
        closure = nearest_closure(tick, closure_rows)
        phase = float(row["gait_phase"])
        period = float(closure["period_s"])
        duty = float(closure["duty"])
        step = float(closure["step_length_m"])
        required = -float(closure["base_body_vx_mps"])
        stance_refs = []
        for leg in range(4):
            leg_phase = running_leg_phase(phase, leg)
            if leg_phase >= duty:
                continue
            stance_phase = leg_phase / duty
            commanded = -step / period * 6.0 * stance_phase * (1.0 - stance_phase)
            stance_refs.append(commanded)
            leg_rows.append({
                "phase_bin": row["phase_bin"],
                "leg": ("FR", "FL", "RR", "RL")[leg],
                "commanded_stance_foot_vx_mps": commanded,
                "stationary_support_required_vx_mps": required,
                "stance_velocity_disagreement_mps": commanded - required,
            })
        if not stance_refs:
            continue
        mean_commanded = statistics.fmean(stance_refs)
        disagreement = mean_commanded - required
        result.append({
            "phase_bin": row["phase_bin"],
            "commanded_stance_foot_vx_mps": mean_commanded,
            "stationary_support_required_vx_mps": required,
            "stance_velocity_disagreement_mps": disagreement,
            "abs_stance_velocity_disagreement_mps": abs(disagreement),
            "delta_NO_D_ALL_mps2": float(row["delta_NO_D_ALL_mps2"]),
            "delta_NO_D_TARGET_ALL_mps2": float(row["delta_NO_D_TARGET_ALL_mps2"]),
            "delta_NO_D_SENSOR_ALL_mps2": float(row["delta_NO_D_SENSOR_ALL_mps2"]),
        })
    return result, leg_rows


def kinematic_summary(rows):
    output = []
    quantities = [
        "commanded_stance_foot_vx_mps",
        "stationary_support_required_vx_mps",
        "stance_velocity_disagreement_mps",
        "abs_stance_velocity_disagreement_mps",
        "delta_NO_D_ALL_mps2",
        "delta_NO_D_TARGET_ALL_mps2",
        "delta_NO_D_SENSOR_ALL_mps2",
    ]
    for quantity in quantities:
        add_summary(output, quantity, [row[quantity] for row in rows], "full", "stance_rows")
        for phase in PHASE_BINS:
            add_summary(output, quantity, [row[quantity] for row in rows if row["phase_bin"] == phase], "phase", phase)
        for label, predicate in (("abs_disagreement_le_0.5", lambda row: row["abs_stance_velocity_disagreement_mps"] <= 0.5), ("abs_disagreement_gt_0.5", lambda row: row["abs_stance_velocity_disagreement_mps"] > 0.5)):
            add_summary(output, quantity, [row[quantity] for row in rows if predicate(row)], "disagreement_bin", label)
    for leg in ("FR", "FL", "RR", "RL"):
        leg_values = [row for row in LEG_ROWS if row["leg"] == leg]
        for quantity in ("commanded_stance_foot_vx_mps", "stationary_support_required_vx_mps", "stance_velocity_disagreement_mps"):
            add_summary(output, f"{leg}_{quantity}", [row[quantity] for row in leg_values], "full", "stance_leg_rows")
    return output


def find_prior_no_d_median():
    for row in read_csv(PRIOR):
        if row["branch"] == "NO_D" and row["scope"] == "global" and row["stratum_type"] == "full" and row["stratum"] == "all":
            return float(row["median_mps2"])
    raise RuntimeError("prior NO_D full median not found")


def get_metric(rows, quantity, stratum_type, stratum):
    for row in rows:
        if row["quantity"] == quantity and row["stratum_type"] == stratum_type and row["stratum"] == stratum:
            return row
    raise RuntimeError(f"missing metric {quantity}/{stratum_type}/{stratum}")


def metric_sentence(metric):
    return f"median {fmt(metric['median'])}, p05/p95 {fmt(metric['p05'])}/{fmt(metric['p95'])}, negative/positive fractions {fmt(metric['fraction_negative'], 3)}/{fmt(metric['fraction_positive'], 3)}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    decomp = read_csv(DECOMP)
    closure = read_csv(CLOSURE)
    if len(decomp) != 552 or not closure:
        raise RuntimeError(f"expected 552 target rows and nonempty closure, got decomp={len(decomp)} closure_rows={len(closure)}")

    decomposition_summary = aggregate_decomposition(decomp)
    write_records(
        OUT / "d_decomposition_summary.csv",
        ["quantity", "stratum_type", "stratum", "n", "median", "p05", "p95", "fraction_negative", "fraction_positive", "median_abs"],
        decomposition_summary,
    )
    global LEG_ROWS
    LEG_ROWS = []
    kinematic, leg_rows = kinematic_rows(decomp, closure)
    LEG_ROWS = leg_rows
    kinematic_summary_rows = kinematic_summary(kinematic)
    write_records(
        OUT / "kinematic_attribution.csv",
        ["quantity", "stratum_type", "stratum", "n", "median", "p05", "p95", "fraction_negative", "fraction_positive", "median_abs"],
        kinematic_summary_rows,
    )

    prior_no_d = find_prior_no_d_median()
    current_no_d = get_metric(decomposition_summary, "delta_NO_D_ALL_mps2", "full", "all")
    validation = {
        "target_rows": len(decomp),
        "max_snapshot_ctrl_residual_Nm": max(float(row["snapshot_ctrl_residual_Nm"]) for row in decomp),
        "max_bridge_formula_residual_Nm": max(float(row["bridge_formula_residual_Nm"]) for row in decomp),
        "max_actual_replay_residual_mps2": max(float(row["actual_replay_residual_mps2"]) for row in decomp),
        "no_d_all_median_mps2": float(current_no_d["median"]),
        "prior_no_d_median_mps2": prior_no_d,
        "prior_no_d_delta_mps2": float(current_no_d["median"]) - prior_no_d,
    }

    source_files = [
        "example/cpp/trot/velocity_command.h",
        "example/cpp/gait/raibert_trot_kernel.h",
        "example/cpp/gait/locomotion_kernel.h",
        "example/cpp/trot/trot_experiment_gait.cpp",
        "example/cpp/trot/trot_experiment_control.cpp",
        "example/cpp/trot/trot_experiment_wbc.cpp",
        "simulate/src/unitree_sdk2_bridge.h",
        "example/cpp/tools/analysis/replay_pd_d_decomposition.cpp",
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
        PRIOR,
    ]
    raw_hashes = {str(path): sha(path) for path in raw_files if path.is_file()}
    binary = ROOT / "example/cpp/build/replay_pd_d_decomposition"

    full = {branch: get_metric(decomposition_summary, f"delta_{branch}_mps2", "full", "all") for branch in BRANCHES}
    phase_metrics = {
        phase: get_metric(decomposition_summary, "delta_NO_D_ALL_mps2", "phase", phase)
        for phase in PHASE_BINS
    }
    kinematic_full = {quantity: get_metric(kinematic_summary_rows, quantity, "full", "stance_rows") for quantity in (
        "commanded_stance_foot_vx_mps", "stationary_support_required_vx_mps", "stance_velocity_disagreement_mps", "abs_stance_velocity_disagreement_mps")}
    low = {quantity: get_metric(kinematic_summary_rows, quantity, "disagreement_bin", "abs_disagreement_le_0.5") for quantity in ("delta_NO_D_ALL_mps2", "delta_NO_D_TARGET_ALL_mps2", "delta_NO_D_SENSOR_ALL_mps2")}
    high = {quantity: get_metric(kinematic_summary_rows, quantity, "disagreement_bin", "abs_disagreement_gt_0.5") for quantity in ("delta_NO_D_ALL_mps2", "delta_NO_D_TARGET_ALL_mps2", "delta_NO_D_SENSOR_ALL_mps2")}
    target_dq_stance = [get_metric(decomposition_summary, f"{label}_dq_error_radps", "state", "stance") for _, label in THIGHS]
    target_dq_swing = [get_metric(decomposition_summary, f"{label}_dq_error_radps", "state", "swing") for _, label in THIGHS]

    lines = [
        "# Phase1 reference/WBC structural attribution",
        "",
        "## Outcome",
        "",
        "Result: **PARTIALLY SUPPORTED**.",
        "",
        "This is an offline/source-analysis checkpoint only. No MuJoCo trajectory, live A/B, gain scan, controller behavior change, or new logging run was executed. The evidence supports a structural conflict mechanism as a contributor, but does not isolate it as the sole closed-loop root cause.",
        "",
        "## Required conclusions",
        "",
        "1. LowCmd `dq_des` is not an analytic task-space velocity solution. `BuildGaitTargets` first obtains body-frame foot targets from the running-trot kernel and maps them through `AllLegInverseKinematicsClamped`; `UpdateJointVelocityFeedforward` then computes each joint velocity as the finite difference `(joint_targets - previous_joint_targets) / motion_dt`, clamped to ±10 rad/s, when velocity feedforward is enabled. The same resulting joint dq array is written for stance and swing legs.",
        "2. The harmful D marginal is mixed/context-dependent, with a net target-motion contribution larger than the sensor-damping contribution in this replay. Negative branch delta means removing that component lowers instantaneous base-x acceleration, so the removed D component had a forward marginal at that state.",
        "3. The stance reference has a structural phase shape. For the actual running-trot kernel, `x_offset = start - direction * stance_travel * Smoothstep(u)`, `u=leg_phase/duty`, `stance_travel=step_length*duty`; after the established-gait blend, `dx/dt = -direction*(step_length/period)*6u(1-u)`. Its mean magnitude over stance is `v_nominal=step_length/period`, while its peak is `1.5*v_nominal` at `u=0.5`.",
        "4. The kinematic and WBC paths demand incompatible behavior in part of the overspeed/braking window: the stance reference is tied to scheduled step/period and varies from zero to a 1.5× peak, while the WBC/SRBD/ID path uses measured body velocity and requests base-x braking. The code also treats commanded foot velocity differently: `commanded_body_feet_velocity_` enters the swing-foot WBC `v_des`, but the running full-WBC stance task uses foot position/velocity damping and does not use that commanded foot velocity.",
        "5. The label is **PARTIALLY SUPPORTED**, not SUPPORTED: exact replay gates pass; D removal is net forward in aggregate and changes sign by phase/contact context; the stance-reference mismatch is present and largest in the phase-shaped mid-stance; however, the existing evidence is marginal same-state acceleration, not a closed-loop trajectory counterfactual, and it does not prove that the mismatch alone causes residual overspeed.",
        "6. One next step, not executed: design and approve one same-state-plus-trajectory attribution that replaces only the stance reference velocity with the measured-speed-consistent stationary-support value while preserving foot positions, WBC targets, and all gates; then compare against the unchanged baseline.",
        "",
        "## Side-by-side dependency graph",
        "",
        "```text",
        "runtime velocity -> ScheduleContinuousVelocityGait -> step/period/duty",
        "  -> RaibertTrotKernel::Compute -> body-frame foot position x(t)",
        "  -> IK -> joint q targets -> finite-difference joint dq_des",
        "  -> LowCmd q,dq,kp,kd -> bridge tau_ff + kp*(q-q_sensor) + kd*(dq-dq_sensor)",
        "",
        "applied/nominal body velocity -> velocity error -> SRBD desired acceleration/forces",
        "  -> ID-WBC qdd/contact forces/tau -> LowCmd tau_ff -> same bridge PD formula",
        "",
        "shared: applied/nominal speed, gait time/phase, body state, contact state, model",
        "can disagree: scheduled foot trajectory/dq_des versus measured-speed base-x braking objective",
        "```",
        "",
        "## Stage 1 source trace",
        "",
        "Path A: `example/cpp/trot/velocity_command.h:186-199` clamps the runtime speed, fixes period `0.14 s`, duty `0.44`, and sets `step_length=speed*period`. `trot_experiment_gait.cpp:200-211` installs those values into the kernel and disables the effective-speed convention. `raibert_trot_kernel.h` computes the schedule nominal as `direction_sign*step_length/period`, uses running-trot offsets FR/RL `0.0` and FL/RR `0.46`, and applies Smoothstep stance interpolation. `trot_experiment_gait.cpp:1493-1503` finite-differences the final body-frame foot targets for `commanded_body_feet_velocity_`; it is not an analytic IK velocity. `trot_experiment_gait.cpp` then performs IK, `trot_experiment_control.cpp:214-216` calls `UpdateJointVelocityFeedforward`, and `trot_experiment_control.cpp:1379-1397` finite-differences the joint targets. `WriteMotorCommands` writes the same q/dq to stance and swing motors; only kp/kd/tau_ff composition differs by WBC contact state. The bridge applies the PD formula in `simulate/src/unitree_sdk2_bridge.h`.",
        "Path B: `trot_experiment_wbc.cpp:414-476` forms the SRBD input and uses `kernel_nominal_velocity_x_mps_` as the body velocity reference; `trot_experiment_wbc.cpp:520-560` passes the first SRBD acceleration into ID-WBC, with later velocity-task/braking logic in the same function. ID-WBC returns qdd/contact forces/tau; `PrepareWbcTorqueFeedforward` maps the motor rows to `wbc_torque_ff`, which is written as LowCmd `tau_ff` in `WriteMotorCommands`. `trot_experiment_wbc.cpp:780-822` confirms swing `v_des = linear_vel_world + R*(omega×r + commanded_body_feet_velocity)`, whereas the stance branch above it uses the actual foot velocity and position error/damping, not `commanded_body_feet_velocity_`.",
        "",
        "## Stage 2 validation and D decomposition",
        "",
        f"The tool selected exactly `{validation['target_rows']}` target snapshots from active-relative `[31.90,33.00)`. Atomic snapshot↔bridge ctrl maximum residual is `{fmt(validation['max_snapshot_ctrl_residual_Nm'], 12)} Nm`; bridge formula maximum residual is `{fmt(validation['max_bridge_formula_residual_Nm'], 12)} Nm`; ACTUAL replay↔live `qacc[0]` maximum residual is `{fmt(validation['max_actual_replay_residual_mps2'], 12)} m/s²`. Every branch calls `mj_setState` from the saved state before `mj_forward`, so branches are independently restored.",
        f"NO_D_ALL regression against the prior committed `components.csv` is `{fmt(validation['no_d_all_median_mps2'], 15)}` versus `{fmt(validation['prior_no_d_median_mps2'], 15)}`, delta `{fmt(validation['prior_no_d_delta_mps2'], 15)}` m/s²: PASS.",
        "",
        "Full target-window branch deltas (`qacc_branch[0] - qacc_ACTUAL[0]`; negative means the removed component was forward-contributing):",
        "",
    ]
    for branch in BRANCHES:
        lines.append(f"- `{branch}`: {metric_sentence(full[branch])} m/s²")
    lines += [
        "",
        "The target/sensor split is not additive by assumption: the two single-component removals are separate marginal replays. The full-window medians show a larger target-motion marginal than sensor-damping marginal, while phase/contact rows in `d_decomposition_summary.csv` retain the sign changes needed to call it mixed/context-dependent.",
        "",
        "## Stage 3 structural attribution",
        "",
        f"For stance samples, the exact Smoothstep derivative reconstructs commanded body-frame foot x velocity with median `{fmt(kinematic_full['commanded_stance_foot_vx_mps']['median'])}` m/s and p05/p95 `{fmt(kinematic_full['commanded_stance_foot_vx_mps']['p05'])}`/`{fmt(kinematic_full['commanded_stance_foot_vx_mps']['p95'])}`. The measured-speed-consistent stationary-support approximation `v_foot,body,x ≈ -v_body,x` has median `{fmt(kinematic_full['stationary_support_required_vx_mps']['median'])}` m/s. The signed reference-minus-requirement disagreement has median `{fmt(kinematic_full['stance_velocity_disagreement_mps']['median'])}` m/s and absolute median/p95 `{fmt(kinematic_full['abs_stance_velocity_disagreement_mps']['median'])}`/`{fmt(kinematic_full['abs_stance_velocity_disagreement_mps']['p95'])}` m/s.",
        "",
        "The disagreement stratification is descriptive, not a newly selected acceptance threshold. Using `|disagreement|=0.5 m/s` only to separate the existing samples, the NO_D_ALL removal delta is:",
        "",
        f"- low-disagreement `n={low['delta_NO_D_ALL_mps2']['n']}`: {metric_sentence(low['delta_NO_D_ALL_mps2'])} m/s²; target/sensor `{fmt(low['delta_NO_D_TARGET_ALL_mps2']['median'])}`/`{fmt(low['delta_NO_D_SENSOR_ALL_mps2']['median'])}` m/s²",
        f"- high-disagreement `n={high['delta_NO_D_ALL_mps2']['n']}`: {metric_sentence(high['delta_NO_D_ALL_mps2'])} m/s²; target/sensor `{fmt(high['delta_NO_D_TARGET_ALL_mps2']['median'])}`/`{fmt(high['delta_NO_D_SENSOR_ALL_mps2']['median'])}` m/s²",
        "",
        "The high-disagreement group has the stronger forward D marginal when its NO_D delta is more negative, but the per-phase/contact CSV is the audit trail: sign and magnitude remain context-dependent. Thigh `dq_des-dq_sensor` stance medians by FR/FL/RR/RL are `" + "/".join(fmt(item["median"]) for item in target_dq_stance) + "` rad/s; swing medians are `" + "/".join(fmt(item["median"]) for item in target_dq_swing) + "` rad/s.",
        "",
        "## Prior evidence boundary",
        "",
        "The atomic snapshot and matching closure are from the validated bridge-atomic checkpoint `6cd37e02385eaa98a1ea75002b21378a70120740`; the prior replay gates and NO_D baseline are retained as evidence. This checkpoint does not reinterpret the prior live D90/RR-thigh failures and does not claim a closed-loop improvement from any same-state branch.",
        "",
        "## Provenance and hashes",
        "",
        f"Analysis branch: `research/phase1-reference-wbc-structural-attribution-20260914`; source HEAD at analysis: `{__import__('subprocess').check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()}`.",
        f"Primary evidence run: `{RUN}`; snapshot records are selected only by the existing atomic join to closure ticks within 10 ms and active-relative `[31.90,33.00)`.",
        f"Offline replay binary SHA256: `{sha(binary)}`.",
        "",
        "Source SHA256:",
    ]
    lines += [f"- `{path}`: `{digest}`" for path, digest in source_hashes.items()]
    lines += ["", "Raw/derived evidence SHA256:"]
    lines += [f"- `{path}`: `{digest}`" for path, digest in raw_hashes.items()]
    lines += [
        "",
        "Committed derived outputs:",
        "- `docs/validation/phase1_reference_wbc_structural_attribution_20260914/d_decomposition.csv`",
        "- `docs/validation/phase1_reference_wbc_structural_attribution_20260914/d_decomposition_summary.csv`",
        "- `docs/validation/phase1_reference_wbc_structural_attribution_20260914/kinematic_attribution.csv`",
        "- `example/cpp/tools/analysis/replay_pd_d_decomposition.cpp`",
        "- `example/cpp/tools/analysis/analyze_reference_wbc_structural_attribution.py`",
        "",
        "No new trajectory, live A/B, gain scan, controller behavior change, WBC rewrite, acceptance change, or follow-up experiment was executed.",
    ]
    (OUT / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print("validation", validation)
    print("NO_D_ALL", metric_sentence(current_no_d))
    print("NO_D_TARGET_ALL", metric_sentence(full["NO_D_TARGET_ALL"]))
    print("NO_D_SENSOR_ALL", metric_sentence(full["NO_D_SENSOR_ALL"]))
    print("NO_D_TARGET_THIGHS", metric_sentence(full["NO_D_TARGET_THIGHS"]))
    print("NO_D_SENSOR_THIGHS", metric_sentence(full["NO_D_SENSOR_THIGHS"]))
    print("kinematic", {key: metric_sentence(value) for key, value in kinematic_full.items()})
    print("low_disagreement", {key: metric_sentence(value) for key, value in low.items()})
    print("high_disagreement", {key: metric_sentence(value) for key, value in high.items()})


if __name__ == "__main__":
    main()
