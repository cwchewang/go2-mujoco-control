#!/usr/bin/env python3
import csv
import hashlib
import math
import statistics
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path("/home/che/dev/go2-workspace/phase1-bounded-stance-dq-screen-20260914")
OUT = ROOT / "docs/validation/phase1_bounded_stance_dq_screen_20260914"
SCREEN = OUT / "screen.csv"
LEGS = OUT / "screen_legs.csv"
SUMMARY = OUT / "screen_summary.csv"
JOINT_SUMMARY = OUT / "joint_summary.csv"
LEG_SUMMARY = OUT / "leg_summary.csv"
RESULTS = OUT / "RESULTS.md"
BINARY = ROOT / "example/cpp/build/replay_bounded_stance_dq"
SCENE = ROOT / "unitree_robots/go2/scene_leg_lift_demo.xml"
EVIDENCE = Path("/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913")
RUN = EVIDENCE / "varying_20260913_231049"
PROFILE = ROOT / "example/cpp/configs/phase1_velocity_varying.csv"
PHASE_BINS = ["[0,0.25)", "[0.25,0.5)", "[0.5,0.75)", "[0.75,1)"]
CANDIDATES = ["BOUND_D2", "BOUND_D4", "BOUND_D6"]
CAPS = {"BOUND_D2": 2.0, "BOUND_D4": 4.0, "BOUND_D6": 6.0}
LEGS_NAMES = ["FR", "FL", "RR", "RL"]
JOINT_NAMES = ["hip", "thigh", "calf"]


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def values(rows, field):
    result = []
    for row in rows:
        value = float(row[field])
        if math.isfinite(value):
            result.append(value)
    return result


def quantile(items, probability):
    items = sorted(items)
    if not items:
        return float("nan")
    if len(items) == 1:
        return items[0]
    position = probability * (len(items) - 1)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(items) - 1)
    return items[lower] + (items[upper] - items[lower]) * (position - lower)


def metric(items):
    items = [item for item in items if math.isfinite(item)]
    return {
        "n": len(items),
        "median": statistics.median(items) if items else float("nan"),
        "p05": quantile(items, 0.05),
        "p95": quantile(items, 0.95),
        "fraction_negative": sum(item < 0.0 for item in items) / len(items) if items else float("nan"),
        "fraction_positive": sum(item > 0.0 for item in items) / len(items) if items else float("nan"),
        "median_abs": statistics.median([abs(item) for item in items]) if items else float("nan"),
        "zero_fraction": sum(item == 0.0 for item in items) / len(items) if items else float("nan"),
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


def add_summary(rows, candidate, quantity, stratum_type, stratum, items):
    item = metric(items)
    rows.append({
        "candidate": candidate,
        "quantity": quantity,
        "stratum_type": stratum_type,
        "stratum": stratum,
        **item,
        "small_n": int(item["n"] < 20),
    })


def write_csv(path, fields, rows):
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
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def screen_strata(rows):
    result = [("full", "all", rows)]
    result.extend(("phase", value, [row for row in rows if phase_bin(row["active_relative_time_s"]) == value]) for value in PHASE_BINS)
    result.extend(("controller_contact_mask", f"mask{mask}", [row for row in rows if int(row["controller_contact_mask"]) == mask])
                  for mask in sorted({int(row["controller_contact_mask"]) for row in rows}))
    result.extend(("physical_contact_mask", f"mask{mask}", [row for row in rows if int(row["actual_physical_contact_mask"]) == mask])
                  for mask in sorted({int(row["actual_physical_contact_mask"]) for row in rows}))
    return result


def leg_strata(rows, snapshots):
    result = [("full", "all", rows)]
    result.extend(("phase", value, [row for row in rows if phase_bin(snapshots[int(row["record_index"])] ["active_relative_time_s"]) == value]) for value in PHASE_BINS)
    result.extend(("controller_contact_mask", f"mask{mask}", [row for row in rows if int(snapshots[int(row["record_index"])] ["controller_contact_mask"]) == mask])
                  for mask in sorted({int(snapshots[int(row["record_index"])] ["controller_contact_mask"]) for row in rows}))
    result.extend(("physical_contact_mask", f"mask{mask}", [row for row in rows if int(snapshots[int(row["record_index"])] ["actual_physical_contact_mask"]) == mask])
                  for mask in sorted({int(snapshots[int(row["record_index"])] ["actual_physical_contact_mask"]) for row in rows}))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    screen = read_csv(SCREEN)
    legs = read_csv(LEGS)
    if len(screen) != 552 * 3:
        raise RuntimeError(f"expected 1656 screen rows, got {len(screen)}")
    if len(legs) != 552 * 4 * 3:
        raise RuntimeError(f"expected 6624 leg rows, got {len(legs)}")
    snapshots = {}
    for candidate in CANDIDATES:
        candidate_rows = [row for row in screen if row["candidate"] == candidate]
        if len(candidate_rows) != 552:
            raise RuntimeError(f"{candidate} does not have 552 rows")
        indexes = [int(row["record_index"]) for row in candidate_rows]
        if len(set(indexes)) != 552:
            raise RuntimeError(f"{candidate} has duplicate record indexes")
        if not snapshots:
            snapshots = {int(row["record_index"]): row for row in candidate_rows}
        elif set(snapshots) != set(indexes):
            raise RuntimeError("candidate record indexes differ")
    if sorted({row["candidate"] for row in screen}) != CANDIDATES:
        raise RuntimeError("unexpected candidate set")

    # All bridge/model/replay gates are evaluated from the emitted exact-state audit.
    max_snapshot_ctrl = max(float(row["snapshot_ctrl_residual_Nm"]) for row in screen)
    max_bridge_formula = max(float(row["bridge_formula_residual_Nm"]) for row in screen)
    max_actual_replay = max(float(row["actual_replay_residual_mps2"]) for row in screen)
    max_candidate_formula = max(float(row["candidate_formula_residual_Nm"]) for row in screen)
    max_q = max(float(row["max_q_des_delta"]) for row in screen)
    max_kp = max(float(row["max_kp_delta"]) for row in screen)
    max_kd = max(float(row["max_kd_delta"]) for row in screen)
    max_tau = max(float(row["max_tau_ff_delta"]) for row in screen)
    max_swing = max(float(row["max_swing_dq_delta"]) for row in screen)
    max_join = max(abs(float(row["controller_join_delta_ms"])) for row in screen)
    contact_mismatches = sum(
        row["actual_physical_contact_mask"] != row["candidate_physical_contact_mask"]
        for row in screen
    )
    stance_rows = [row for row in legs if int(row["controller_stance"]) == 1]
    valid_stance_rows = [row for row in stance_rows if int(row["solve_valid"]) == 1]
    invalid_stance_rows = [row for row in stance_rows if int(row["solve_valid"]) == 0]
    max_pre_residual = max(float(row["pre_residual_mps"]) for row in valid_stance_rows)
    max_condition = max(float(row["condition_number"]) for row in valid_stance_rows)
    min_rank = min(int(row["rank"]) for row in valid_stance_rows)
    max_dq_change = {candidate: max(max(abs(float(row[f"delta_dq_{joint}"])) for joint in range(3))
                                   for row in valid_stance_rows if row["candidate"] == candidate)
                     for candidate in CANDIDATES}
    max_d_change = {candidate: max(max(abs(float(row[f"delta_d_target_{joint}"])) for joint in range(3))
                                  for row in valid_stance_rows if row["candidate"] == candidate)
                    for candidate in CANDIDATES}
    swing_leg_delta = max(abs(float(row[f"delta_dq_{joint}"])) for row in legs
                          if int(row["controller_stance"]) == 0 for joint in range(3))
    if swing_leg_delta != 0.0:
        max_swing = max(max_swing, swing_leg_delta)

    summary_rows = []
    for candidate in CANDIDATES:
        candidate_rows = [row for row in screen if row["candidate"] == candidate]
        for stratum_type, stratum, group in screen_strata(candidate_rows):
            add_summary(summary_rows, candidate, "delta_ax_mps2", stratum_type, stratum,
                        values(group, "delta_ax_mps2"))
    write_csv(SUMMARY,
              ["candidate", "quantity", "stratum_type", "stratum", "n", "median", "p05", "p95",
               "fraction_negative", "fraction_positive", "median_abs", "zero_fraction", "small_n"],
              summary_rows)

    joint_rows = []
    leg_rows = []
    limiter_rows = []
    for candidate in CANDIDATES:
        candidate_legs = [row for row in valid_stance_rows if row["candidate"] == candidate]
        counts = Counter(row["limiter"] for row in candidate_legs)
        for limiter in ["D_CAP", "DQ_CAP", "BOTH", "NONE", "ZERO"]:
            limiter_rows.append({
                "candidate": candidate,
                "limiter": limiter,
                "n": counts[limiter],
                "fraction": counts[limiter] / len(candidate_legs),
            })
        for leg in LEGS_NAMES:
            group = [row for row in candidate_legs if row["leg"] == leg]
            for quantity, field in [("delta_dq_radps", "delta_dq"),
                                    ("delta_d_target_Nm", "delta_d_target"),
                                    ("dq_base_radps", "dq_base"),
                                    ("dq_ss_radps", "dq_ss")]:
                for joint_index, joint in enumerate(JOINT_NAMES):
                    item = metric([float(row[f"{field}_{joint_index}"]) for row in group])
                    joint_rows.append({"candidate": candidate, "leg": leg, "joint": joint,
                                       "quantity": quantity, **item,
                                       "small_n": int(item["n"] < 20)})
            for stratum_type, stratum, stratum_group in leg_strata(group, snapshots):
                baseline_norm = values(stratum_group, "mismatch_actual_norm_mps")
                candidate_norm = values(stratum_group, "mismatch_candidate_norm_mps")
                baseline_x = values(stratum_group, "mismatch_actual_x_mps")
                candidate_x = values(stratum_group, "mismatch_candidate_x_mps")
                s_values = values(stratum_group, "s_leg")
                leg_rows.extend([
                    {"candidate": candidate, "leg": leg, "quantity": "baseline_mismatch_norm_mps",
                     "stratum_type": stratum_type, "stratum": stratum, **metric(baseline_norm), "small_n": int(len(baseline_norm) < 20)},
                    {"candidate": candidate, "leg": leg, "quantity": "candidate_mismatch_norm_mps",
                     "stratum_type": stratum_type, "stratum": stratum, **metric(candidate_norm), "small_n": int(len(candidate_norm) < 20)},
                    {"candidate": candidate, "leg": leg, "quantity": "baseline_mismatch_x_mps",
                     "stratum_type": stratum_type, "stratum": stratum, **metric(baseline_x), "small_n": int(len(baseline_x) < 20)},
                    {"candidate": candidate, "leg": leg, "quantity": "candidate_mismatch_x_mps",
                     "stratum_type": stratum_type, "stratum": stratum, **metric(candidate_x), "small_n": int(len(candidate_x) < 20)},
                    {"candidate": candidate, "leg": leg, "quantity": "s_leg",
                     "stratum_type": stratum_type, "stratum": stratum, **metric(s_values), "small_n": int(len(s_values) < 20)},
                ])
    write_csv(JOINT_SUMMARY,
              ["candidate", "leg", "joint", "quantity", "n", "median", "p05", "p95",
               "fraction_negative", "fraction_positive", "median_abs", "zero_fraction", "small_n"],
              joint_rows)
    write_csv(LEG_SUMMARY,
              ["candidate", "leg", "quantity", "stratum_type", "stratum", "n", "median", "p05", "p95",
               "fraction_negative", "fraction_positive", "median_abs", "zero_fraction", "small_n"],
              leg_rows)

    candidate_metrics = {}
    for candidate in CANDIDATES:
        rows = [row for row in screen if row["candidate"] == candidate]
        delta = metric(values(rows, "delta_ax_mps2"))
        phase = {stratum: metric(values(group, "delta_ax_mps2"))
                 for kind, stratum, group in screen_strata(rows) if kind == "phase"}
        controller = {stratum: metric(values(group, "delta_ax_mps2"))
                      for kind, stratum, group in screen_strata(rows) if kind == "controller_contact_mask"}
        leg_group = [row for row in valid_stance_rows if row["candidate"] == candidate]
        baseline_norm = metric(values(leg_group, "mismatch_actual_norm_mps"))
        candidate_norm = metric(values(leg_group, "mismatch_candidate_norm_mps"))
        phase_ok = all(item["median"] < 0.0 for item in phase.values())
        controller_ok = all(item["median"] <= 0.0 for item in controller.values() if item["n"] >= 20)
        promotion = {
            "median": delta["median"] <= -0.25,
            "fraction_negative": delta["fraction_negative"] >= 0.75,
            "fraction_positive": delta["fraction_positive"] <= 0.10,
            "controller_medians": controller_ok,
            "phase_medians": phase_ok,
            "mismatch_reduction": baseline_norm["median"] - candidate_norm["median"] >= 0.15,
            "caps": max_dq_change[candidate] <= 2.0 + 1.0e-10 and max_d_change[candidate] <= CAPS[candidate] + 1.0e-10,
        }
        candidate_metrics[candidate] = {
            "delta": delta,
            "phase": phase,
            "controller": controller,
            "baseline_norm": baseline_norm,
            "candidate_norm": candidate_norm,
            "promotion": promotion,
            "promotable": all(promotion.values()),
        }

    validation_gates = {
        "target_rows": len(screen) == 1656,
        "snapshot_ctrl_reconstruction": max_snapshot_ctrl <= 1.0e-12,
        "bridge_formula": max_bridge_formula <= 1.0e-10,
        "actual_qacc_replay": max_actual_replay <= 1.0e-5,
        "candidate_formula": max_candidate_formula <= 1.0e-10,
        "q_kp_kd_tau_unchanged": max(max_q, max_kp, max_kd, max_tau) <= 1.0e-12,
        "swing_dq_unchanged": max_swing <= 1.0e-12,
        "same_state_contact_mask": contact_mismatches == 0,
        "controller_join_within_10ms": max_join <= 10.0,
        "all_stance_solves_valid": len(invalid_stance_rows) == 0 and min_rank == 3 and max_condition <= 1.0e4 and max_pre_residual <= 1.0e-6,
        "invalid_fraction": len(invalid_stance_rows) / len(stance_rows) <= 0.05,
        "dq_caps": all(value <= 2.0 + 1.0e-10 for value in max_dq_change.values()),
        "d_target_caps": all(max_d_change[candidate] <= CAPS[candidate] + 1.0e-10 for candidate in CANDIDATES),
        "candidate_changes_only_stance": swing_leg_delta <= 1.0e-12,
    }
    gates_pass = all(validation_gates.values())
    promotable = [candidate for candidate in CANDIDATES if gates_pass and candidate_metrics[candidate]["promotable"]]
    if not gates_pass:
        outcome = "INCONCLUSIVE"
        recommendation = "修复同一离线测试的最小验证/数学门问题后，再重做该测试；不运行 live A/B。"
    elif promotable:
        outcome = "LIVE-CANDIDATE-ELIGIBLE: " + min(promotable, key=lambda item: CAPS[item])
        recommendation = f"对 {min(promotable, key=lambda item: CAPS[item])} 申请一次单独批准的最小 live A/B，只改变 controller-stance dq_des 构造。"
    else:
        outcome = "NO LIVE CANDIDATE"
        recommendation = "放弃这条 bounded stance-dq 速度参考候选，转查命令/bridge 时序层的结构性归因。"

    source_files = [
        "example/cpp/kinematics/go2_forward_kinematics.h",
        "example/cpp/kinematics/go2_leg_jacobian.h",
        "example/cpp/tools/analysis/replay_bridge_atomic.cpp",
        "example/cpp/tools/analysis/replay_bounded_stance_dq.cpp",
        "example/cpp/tools/analysis/analyze_bounded_stance_dq.py",
        "simulate/src/unitree_sdk2_bridge.h",
    ]
    raw_files = [
        EVIDENCE / "bridge_atomic_snapshots.bin", RUN / "data.csv", RUN / "data.csv.id_closure.csv",
        RUN / "run_metadata.txt", RUN / "run_manifest.json", RUN / "environment.txt",
        RUN / "controller.log", RUN / "simulator.log", RUN / "contact_ground_truth.csv",
        PROFILE,
    ]
    report_lines = [
        "# Phase1 bounded stance-dq offline screen",
        "",
        f"Result: **{outcome}**.",
        "",
        "This is exactly one offline same-state checkpoint. No new MuJoCo trajectory, live A/B, gain scan, gait scan, controller benchmark, parameter search, or follow-up experiment was executed.",
        "",
        "## Hypothesis and unique variable",
        "",
        "A small scalar correction of controller-stance `dq_des` toward the prior Jacobian-consistent stationary-support solution can retain a consistent instantaneous braking direction while respecting a per-joint 2 rad/s change cap and one of the predeclared D-target caps 2/4/6 Nm.",
        "",
        "The prior full-rank solution is reproduced with the same q-target FK, restored-state local body twist, repository foot Jacobian, and SVD gates. In this screen `dq_ss` is the complete unbounded SVD solution; the bounded candidate is `dq_base + s_leg*(dq_ss-dq_base)`. The prior ±10 rad/s clamp is retained only as an audit field and is not applied before the scalar bound. Only controller-stance dq changes; swing dq, q/kp/kd/tau_ff, state, contacts, model, and WBC/SRBD/ID outputs remain ACTUAL.",
        "",
        "## Candidate construction",
        "",
        "For each stance leg, `s_leg = min(1, 2/max(abs(delta_dq_raw)), cap/max(abs(kd*delta_dq_raw)))`, with an inactive constraint treated as infinity. The entire three-joint correction direction is preserved; joints are not independently clipped. `D_CAP`, `DQ_CAP`, `BOTH`, `NONE`, and exact-zero cases are recorded per leg/sample.",
        "",
        "## Validation gates",
        "",
        f"The replay selected 552 snapshots and emitted 1,656 candidate rows plus 6,624 leg/candidate rows. This is 1,100 controller-stance leg samples per candidate, 3,300 across the three candidates. All gate values are computed from the emitted audit CSVs; the binary independently checked the MuJoCo 3.3.6, mjtNum=8, `mjSTATE_INTEGRATION`, nq=19, nv=18, na=0, nu=12 signature.",
        f"Maximum snapshot↔atomic ctrl residual: `{fmt(max_snapshot_ctrl, 12)} Nm`; maximum captured bridge-formula residual: `{fmt(max_bridge_formula, 12)} Nm`; maximum ACTUAL restored-state qacc[0] residual: `{fmt(max_actual_replay, 12)} m/s²`; maximum candidate bridge-formula residual: `{fmt(max_candidate_formula, 12)} Nm`.",
        f"Controller join maximum absolute gap: `{fmt(max_join, 6)} ms`. Stance samples across candidates: `{len(stance_rows)}`; per candidate: `{len(stance_rows)//3}`; valid: `{len(valid_stance_rows)}`; invalid: `{len(invalid_stance_rows)}`; invalid fraction: `{fmt(len(invalid_stance_rows)/len(stance_rows), 6)}`. Minimum SVD rank: `{min_rank}`; maximum condition number: `{fmt(max_condition, 6)}`; maximum pre-clamp residual: `{fmt(max_pre_residual, 12)} m/s`.",
        f"Maximum unchanged q/kp/kd/tau_ff audit: `{fmt(max(max_q, max_kp, max_kd, max_tau), 12)}`; maximum swing dq change: `{fmt(max_swing, 12)} rad/s`; actual/candidate physical contact-mask mismatches: `{contact_mismatches}`.",
        "",
        "| gate | result |",
        "|---|---|",
    ]
    for name, passed in validation_gates.items():
        report_lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")
    report_lines += ["", "All validation gates pass." if gates_pass else "At least one validation gate fails; interpretation is INCONCLUSIVE.", "", "## Promotion screen", ""]
    report_lines += [
        "`delta_ax = qacc_candidate[0] - qacc_actual[0]`; negative is the desired instantaneous braking direction. Promotion additionally requires the full-window and stratum gates in the task, including at least 0.15 m/s median stance mismatch-norm reduction.",
        "",
        "| candidate | n | median | p05 | p95 | frac<0 | frac>0 | median abs | zero frac | baseline norm | candidate norm | norm reduction | eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for candidate in CANDIDATES:
        item = candidate_metrics[candidate]
        delta = item["delta"]
        reduction = item["baseline_norm"]["median"] - item["candidate_norm"]["median"]
        report_lines.append(
            f"| `{candidate}` | {delta['n']} | {fmt(delta['median'])} | {fmt(delta['p05'])} | {fmt(delta['p95'])} | {fmt(delta['fraction_negative'], 3)} | {fmt(delta['fraction_positive'], 3)} | {fmt(delta['median_abs'])} | {fmt(delta['zero_fraction'], 3)} | {fmt(item['baseline_norm']['median'])} | {fmt(item['candidate_norm']['median'])} | {fmt(reduction)} | {'YES' if item['promotable'] else 'NO'} |"
        )
    report_lines += ["", "Promotion gate details:", ""]
    for candidate in CANDIDATES:
        report_lines.append(f"- `{candidate}`: " + ", ".join(f"{key}={'PASS' if value else 'FAIL'}" for key, value in candidate_metrics[candidate]["promotion"].items()))

    report_lines += ["", "## Phase and contact strata", "", "The following are `delta_ax` metrics. Contact-mask strata with n<20 are marked small-n; physical masks are audit-only.", ""]
    for candidate in CANDIDATES:
        report_lines += [f"### {candidate}", "", "| stratum | n | median | p05 | p95 | frac<0 | frac>0 | small-n |", "|---|---:|---:|---:|---:|---:|---:|---|"]
        for kind, stratum, _ in screen_strata([row for row in screen if row["candidate"] == candidate]):
            if kind == "full":
                continue
            item = next(row for row in summary_rows if row["candidate"] == candidate and row["quantity"] == "delta_ax_mps2" and row["stratum_type"] == kind and row["stratum"] == stratum)
            report_lines.append(f"| {kind}:{stratum} | {item['n']} | {fmt(item['median'])} | {fmt(item['p05'])} | {fmt(item['p95'])} | {fmt(item['fraction_negative'], 3)} | {fmt(item['fraction_positive'], 3)} | {'yes' if item['small_n'] else 'no'} |")

    report_lines += ["", "## Bounded correction and foot-velocity audit", "", "Limiter fractions are over valid controller-stance leg samples. Per-leg/per-joint distributions and all per-sample values are in `joint_summary.csv`, `leg_summary.csv`, and `screen_legs.csv`.", ""]
    report_lines += ["| candidate | s median | s p05/p95 | D_CAP | DQ_CAP | BOTH | NONE | ZERO | max abs dq change | max abs D-target change |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for candidate in CANDIDATES:
        group = [row for row in valid_stance_rows if row["candidate"] == candidate]
        sm = metric(values(group, "s_leg"))
        counts = Counter(row["limiter"] for row in group)
        fractions = {name: counts[name] / len(group) for name in ["D_CAP", "DQ_CAP", "BOTH", "NONE", "ZERO"]}
        report_lines.append(f"| `{candidate}` | {fmt(sm['median'])} | {fmt(sm['p05'])}/{fmt(sm['p95'])} | {fmt(fractions['D_CAP'], 3)} | {fmt(fractions['DQ_CAP'], 3)} | {fmt(fractions['BOTH'], 3)} | {fmt(fractions['NONE'], 3)} | {fmt(fractions['ZERO'], 3)} | {fmt(max_dq_change[candidate], 12)} | {fmt(max_d_change[candidate], 12)} |")
    report_lines += ["", "Per-leg/per-joint bounded correction distributions (median/p05/p95):", "", "| candidate | leg.joint | delta dq rad/s | delta D-target Nm |", "|---|---|---|---|"]
    for candidate in CANDIDATES:
        for leg in LEGS_NAMES:
            for joint in JOINT_NAMES:
                dq_item = next(row for row in joint_rows if row["candidate"] == candidate and row["leg"] == leg and row["joint"] == joint and row["quantity"] == "delta_dq_radps")
                d_item = next(row for row in joint_rows if row["candidate"] == candidate and row["leg"] == leg and row["joint"] == joint and row["quantity"] == "delta_d_target_Nm")
                report_lines.append(f"| `{candidate}` | {leg}.{joint} | {fmt(dq_item['median'])}/{fmt(dq_item['p05'])}/{fmt(dq_item['p95'])} | {fmt(d_item['median'])}/{fmt(d_item['p05'])}/{fmt(d_item['p95'])} |")
    report_lines += ["", "Baseline versus candidate stationary-support mismatch norm and x-component, full valid stance samples:", "", "| candidate | baseline norm median/p05/p95 m/s | candidate norm median/p05/p95 m/s | baseline x median/p05/p95 m/s | candidate x median/p05/p95 m/s |", "|---|---|---|---|---|"]
    for candidate in CANDIDATES:
        group = [row for row in valid_stance_rows if row["candidate"] == candidate]
        bn = metric(values(group, "mismatch_actual_norm_mps")); cn = metric(values(group, "mismatch_candidate_norm_mps"))
        bx = metric(values(group, "mismatch_actual_x_mps")); cx = metric(values(group, "mismatch_candidate_x_mps"))
        report_lines.append(f"| `{candidate}` | {fmt(bn['median'])}/{fmt(bn['p05'])}/{fmt(bn['p95'])} | {fmt(cn['median'])}/{fmt(cn['p05'])}/{fmt(cn['p95'])} | {fmt(bx['median'])}/{fmt(bx['p05'])}/{fmt(bx['p95'])} | {fmt(cx['median'])}/{fmt(cx['p05'])}/{fmt(cx['p95'])} |")
    report_lines += ["", "## Provenance and reproduction", "", f"Analysis branch: `research/phase1-bounded-stance-dq-screen-20260914`; source HEAD before this checkpoint commit: `{git_head()}`.", "", "Exact replay command:", "", "```text", "./example/cpp/build/replay_bounded_stance_dq unitree_robots/go2/scene_leg_lift_demo.xml /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv docs/validation/phase1_bounded_stance_dq_screen_20260914/screen.csv docs/validation/phase1_bounded_stance_dq_screen_20260914/screen_legs.csv docs/validation/phase1_bounded_stance_dq_screen_20260914/replay_summary.txt", "```", "", "Exact analysis command:", "", "```text", "python3 example/cpp/tools/analysis/analyze_bounded_stance_dq.py", "```", "", "Scene SHA256: `" + sha(SCENE) + "`; replay binary SHA256: `" + sha(BINARY) + "`.", "", "Source SHA256:"]
    for path in source_files:
        report_lines.append(f"- `{path}`: `{sha(ROOT / path)}`")
    report_lines += ["", "Raw evidence SHA256:"]
    for path in raw_files:
        report_lines.append(f"- `{path}`: `{sha(path)}`")
    report_lines += ["", "Derived outputs:", "", "- `screen.csv` (1,656 candidate/snapshot rows)", "- `screen_legs.csv` (6,624 candidate/leg/snapshot rows)", "- `screen_summary.csv`, `joint_summary.csv`, `leg_summary.csv`", "", "The raw evidence remains in its prior worktree and was not modified, renamed, or deleted.", "", "## Interpretation", "", "This is same-state instantaneous evidence only. A passing candidate is not a controller fix, does not establish closed-loop trajectory behavior, and does not authorize a live run. Body-x attribution comes only from exact MuJoCo qacc[0] replay; individual joint torque signs are not interpreted as propulsion or braking.", "", "## Recommended next step (not executed)", "", recommendation]
    RESULTS.write_text("\n".join(report_lines) + "\n")


if __name__ == "__main__":
    main()
