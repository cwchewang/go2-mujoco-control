#!/usr/bin/env python3
"""Offline gait-quality audit for the deterministic Phase1 D4 A/B captures."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ARMS = ("A", "B")
MOTORS = (
    "FR_hip", "FR_thigh", "FR_calf", "FL_hip", "FL_thigh", "FL_calf",
    "RR_hip", "RR_thigh", "RR_calf", "RL_hip", "RL_thigh", "RL_calf",
)
ACTIVE = "diag_bounded_stance_dq_active_relative_time_s"
START, END = 32.10, 39.90
LEGS = ("FR", "FL", "RR", "RL")
PRE_START, PRE_END = 31.90, 32.10
NBINS = 50
TAU_LIMIT_NM = 45.0
PARENT_PROVENANCE = Path(
    "docs/validation/phase1_d4_deterministic_ab_20260914/provenance.csv"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    if not fields:
        fields = ["status"]
        rows = [{"status": "no_rows"}]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def num(row: dict, key: str, default: float = math.nan) -> float:
    try:
        value = float(row.get(key, ""))
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def finite(values):
    return [x for x in values if math.isfinite(x)]


def quantile(values, p: float) -> float:
    values = sorted(finite(values))
    if not values:
        return math.nan
    z = (len(values) - 1) * p
    lo = int(math.floor(z))
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (z - lo)


def summary(values) -> dict[str, float | int]:
    values = finite(values)
    if not values:
        return {k: math.nan for k in ("mean", "median", "std", "p05", "p95", "min", "max", "ptp")} | {"n": 0}
    mean = statistics.fmean(values)
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    return {
        "n": len(values), "mean": mean, "median": statistics.median(values),
        "std": std, "p05": quantile(values, .05), "p95": quantile(values, .95),
        "min": min(values), "max": max(values), "ptp": max(values) - min(values),
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metadata(path: Path) -> dict[str, str]:
    result = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            result[k] = v
    return result


def in_window(rows, start=START, end=END):
    return [r for r in rows if start <= num(r, ACTIVE) < end]


def add_phase(rows: list[dict]) -> list[dict]:
    selected = sorted(in_window(rows), key=lambda r: num(r, ACTIVE))
    if not selected:
        return []
    out = []
    cycles = 0.0
    last_t = num(selected[0], ACTIVE)
    for i, row in enumerate(selected):
        t = num(row, ACTIVE)
        period = num(row, "velocity_command_gait_period_s", 0.14)
        if not (period > 1e-6):
            period = 0.14
        if i:
            dt = max(0.0, t - last_t)
            cycles += dt / period
        last_t = t
        copy = dict(row)
        copy["_cycle_float"] = cycles
        copy["_cycle"] = int(math.floor(cycles))
        copy["_gait_phase"] = cycles - math.floor(cycles)
        copy["_phase_bin"] = min(NBINS - 1, int(copy["_gait_phase"] * NBINS))
        out.append(copy)
    return out


def corr(a, b) -> float:
    pairs = [(x, y) for x, y in zip(a, b) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 5:
        return math.nan
    xs, ys = zip(*pairs)
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    if den <= 1e-15:
        return math.nan
    return sum(x*y for x, y in zip(dx, dy)) / den


def linear_slope(xs, ys) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 2:
        return math.nan
    x, y = zip(*pairs)
    mx, my = statistics.fmean(x), statistics.fmean(y)
    den = sum((v - mx) ** 2 for v in x)
    return math.nan if den <= 1e-15 else sum((a-mx)*(b-my) for a, b in pairs) / den


def phase_fold(arm: str, rows: list[dict], field: str, scale=1.0, label=None):
    bins: dict[int, list[float]] = defaultdict(list)
    all_values = []
    for r in rows:
        value = num(r, field)
        if math.isfinite(value):
            value *= scale
            bins[int(r["_phase_bin"])].append(value)
            all_values.append(value)
    means = []
    output = []
    for b in range(NBINS):
        s = summary(bins.get(b, []))
        means.append(s["mean"])
        output.append({"arm": arm, "signal": label or field, "phase_bin": b,
                       "phase_center": (b + .5) / NBINS, **s})
    total_mean = statistics.fmean(all_values) if all_values else math.nan
    total_sse = sum((v-total_mean)**2 for v in all_values) if all_values else math.nan
    within_sse = 0.0
    if all_values:
        for b, vals in bins.items():
            m = statistics.fmean(vals)
            within_sse += sum((v-m)**2 for v in vals)
    explained = 1.0 - within_sse/total_sse if total_sse and total_sse > 0 else math.nan
    template = means
    return output, template, explained


def effective_torque_proxy(row: dict) -> float:
    values = []
    for motor in MOTORS:
        ff = num(row, motor + "_tau_ff")
        qd, q = num(row, motor + "_q_target"), num(row, motor + "_q_state")
        dqd, dq = num(row, motor + "_dq_target"), num(row, motor + "_dq_state")
        kp, kd = num(row, motor + "_kp"), num(row, motor + "_kd")
        if all(math.isfinite(v) for v in (ff, qd, q, dqd, dq, kp, kd)):
            values.append(abs(ff + kp * (qd - q) + kd * (dqd - dq)))
    return max(values, default=math.nan)

def cycle_id_for_time(t: float, origin: float, period: float = 0.14) -> int:
    return int(math.floor((t - origin) / period))


def complete_cycles(rows: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        grouped[int(r["_cycle"])].append(r)
    if len(grouped) <= 2:
        return {}
    ids = sorted(grouped)
    # First/last cycles can be partial because the window boundary is arbitrary.
    return {cid: grouped[cid] for cid in ids[1:-1]}


def binned_cycle(cycle: list[dict], field: str, scale=1.0) -> list[float]:
    bins: dict[int, list[float]] = defaultdict(list)
    for r in cycle:
        v = num(r, field)
        if math.isfinite(v):
            bins[int(r["_phase_bin"])].append(v*scale)
    return [statistics.fmean(bins[b]) if bins.get(b) else math.nan for b in range(NBINS)]


def cycle_attitude_rows(arm: str, phased: list[dict], roll_template, pitch_template,
                        closure: list[dict] | None = None):
    rows = []
    cycles = complete_cycles(phased)
    closure_by_cycle: dict[int, list[dict]] = defaultdict(list)
    origin = min((num(r, ACTIVE) for r in phased if math.isfinite(num(r, ACTIVE))), default=START)
    for closure_row in closure or []:
        t = num(closure_row, "active_relative_time_s")
        if math.isfinite(t):
            closure_by_cycle[cycle_id_for_time(t, origin)].append(closure_row)
    for cid, cr in sorted(cycles.items()):
        t = [num(r, ACTIVE) for r in cr]
        roll = [math.degrees(num(r, "imu_roll_rad")) for r in cr]
        pitch = [math.degrees(num(r, "imu_pitch_rad")) for r in cr]
        z = [num(r, "world_base_z_m") for r in cr]
        excess = [num(r, "velocity_command_measured_mps")-num(r, "velocity_command_applied_mps") for r in cr]
        counts = [num(r, "contact_count") for r in cr]
        support_valid = [num(r, "support_foot_kinematics_valid") > 0.5 for r in cr]
        support = [num(r, "support_foot_speed_mps") for r, valid in zip(cr, support_valid) if valid]
        proxy = [effective_torque_proxy(r) for r in cr]
        saturation = [num(r, "torque_saturation_max") for r in closure_by_cycle.get(cid, [])]
        rb = binned_cycle(cr, "imu_roll_rad", 180.0/math.pi)
        pb = binned_cycle(cr, "imu_pitch_rad", 180.0/math.pi)
        def rmse(a, b):
            vals = [(x-y)**2 for x, y in zip(a, b) if math.isfinite(x) and math.isfinite(y)]
            return math.sqrt(statistics.fmean(vals)) if vals else math.nan
        masks = Counter(r.get("wbc_shadow_contact_mask", "") for r in cr)
        rows.append({
            "arm": arm, "cycle": cid,
            "t_start": min(finite(t), default=math.nan), "t_end": max(finite(t), default=math.nan),
            "roll_mean_deg": summary(roll)["mean"], "roll_ptp_deg": summary(roll)["ptp"],
            "pitch_mean_deg": summary(pitch)["mean"], "pitch_ptp_deg": summary(pitch)["ptp"],
            "body_z_mean_m": summary(z)["mean"], "body_z_ptp_m": summary(z)["ptp"],
            "velocity_excess_mean_mps": summary(excess)["mean"],
            "contact_count_min": min(finite(counts), default=math.nan),
            "support_foot_speed_median_mps": summary(support)["median"],
            "support_foot_speed_p95_mps": summary(support)["p95"],
            "support_foot_speed_available_fraction": statistics.fmean(support_valid) if support_valid else math.nan,
            "effective_torque_proxy_mean_nm": summary(proxy)["mean"],
            "effective_torque_proxy_rms_nm": math.sqrt(statistics.fmean([v*v for v in finite(proxy)])) if finite(proxy) else math.nan,
            "torque_saturation_max_nm": max(finite(saturation), default=math.nan),
            "torque_saturation_mean_nm": summary(saturation)["mean"],
            "mask6_fraction": masks.get("6", 0)/len(cr), "mask9_fraction": masks.get("9", 0)/len(cr),
            "roll_template_corr": corr(rb, roll_template), "pitch_template_corr": corr(pb, pitch_template),
            "roll_template_rmse_deg": rmse(rb, roll_template), "pitch_template_rmse_deg": rmse(pb, pitch_template),
        })
    return rows


def contact_quality(arm: str, rows: list[dict]) -> list[dict]:
    total = len(rows)
    out = []
    counts = Counter(int(round(num(r, "contact_count", -1))) for r in rows)
    for c in range(5):
        out.append({"arm": arm, "metric": "physical_contact_count_fraction", "category": c,
                    "value": counts.get(c, 0)/total if total else math.nan})
    masks = Counter(r.get("wbc_shadow_contact_mask", "") for r in rows)
    for m, n in sorted(masks.items(), key=lambda x: str(x[0])):
        out.append({"arm": arm, "metric": "wbc_contact_mask_fraction", "category": m,
                    "value": n/total if total else math.nan})
    for leg in LEGS:
        values = [num(r, "contact_" + leg) for r in rows]
        out.append({"arm": arm, "metric": "physical_" + leg + "_contact_fraction",
                    "category": "contact_" + leg, "value": statistics.fmean(finite(values)) if finite(values) else math.nan})
    out.append({"arm": arm, "metric": "expected_diagonal_mask_fraction", "category": "6_or_9",
                "value": (masks.get("6",0)+masks.get("9",0))/total if total else math.nan})
    out.append({"arm": arm, "metric": "contact_le1_fraction", "category": "<=1",
                "value": sum(n for c,n in counts.items() if c <= 1)/total if total else math.nan})
    touchdown_times = []
    touchdown_count = 0
    touchdown_rows = 0
    for r in rows:
        event_count = num(r, "touchdown_event_count", 0.0)
        if math.isfinite(event_count) and event_count > 0:
            touchdown_count += event_count
            touchdown_rows += 1
            t = num(r, ACTIVE)
            if math.isfinite(t):
                touchdown_times.append(t)
    touchdown_intervals = [b-a for a, b in zip(touchdown_times, touchdown_times[1:])]
    interval_mean = statistics.fmean(touchdown_intervals) if touchdown_intervals else math.nan
    interval_cv = (statistics.pstdev(touchdown_intervals)/interval_mean
                   if touchdown_intervals and interval_mean > 0 else math.nan)
    out += [
        {"arm": arm, "metric": "touchdown_event_count", "category": "all", "value": touchdown_count},
        {"arm": arm, "metric": "touchdown_event_row_count", "category": "all", "value": touchdown_rows},
        {"arm": arm, "metric": "touchdown_interval_median_s", "category": "all", "value": summary(touchdown_intervals)["median"]},
        {"arm": arm, "metric": "touchdown_interval_p05_s", "category": "all", "value": summary(touchdown_intervals)["p05"]},
        {"arm": arm, "metric": "touchdown_interval_p95_s", "category": "all", "value": summary(touchdown_intervals)["p95"]},
        {"arm": arm, "metric": "touchdown_interval_min_s", "category": "all", "value": summary(touchdown_intervals)["min"]},
        {"arm": arm, "metric": "touchdown_interval_max_s", "category": "all", "value": summary(touchdown_intervals)["max"]},
        {"arm": arm, "metric": "touchdown_interval_cv", "category": "all", "value": interval_cv},
    ]
    support_valid = [num(r, "support_foot_kinematics_valid") > 0.5 for r in rows]
    support = [num(r, "support_foot_speed_mps") for r, valid in zip(rows, support_valid) if valid]
    lowfr = [num(r, "support_low_friction_evidence") for r in rows]
    for name, value in (("support_foot_kinematics_valid_fraction", statistics.fmean(support_valid) if support_valid else math.nan),
                        ("support_foot_speed_median", summary(support)["median"]),
                        ("support_foot_speed_p95", summary(support)["p95"]),
                        ("support_foot_speed_max", summary(support)["max"]),
                        ("low_friction_evidence_fraction", statistics.fmean(finite(lowfr)) if finite(lowfr) else math.nan)):
        out.append({"arm": arm, "metric": name, "category": "all", "value": value})
    return out


def actuation_quality(arm: str, rows: list[dict], closure: list[dict]) -> list[dict]:
    out = []
    for field in ("wbc_shadow_solver_ok", "wbc_full_srbd_ok", "wbc_full_id_ok"):
        vals = finite([num(r, field) for r in rows])
        out.append({"arm": arm, "metric": field+"_fraction", "value": statistics.fmean(vals) if vals else math.nan})
    for field in ("wbc_shadow_residual_norm", "wbc_full_eq_residual"):
        vals = [num(r, field) for r in rows]
        s = summary(vals)
        out += [{"arm": arm, "metric": field+"_median", "value": s["median"]},
                {"arm": arm, "metric": field+"_p95", "value": s["p95"]}]
    tau_ff = []
    effective = []
    for r in rows:
        for m in MOTORS:
            ff = num(r, m+"_tau_ff")
            if math.isfinite(ff): tau_ff.append(abs(ff))
            qd, q = num(r,m+"_q_target"), num(r,m+"_q_state")
            dqd, dq = num(r,m+"_dq_target"), num(r,m+"_dq_state")
            kp, kd = num(r,m+"_kp"), num(r,m+"_kd")
            if all(math.isfinite(v) for v in (ff,qd,q,dqd,dq,kp,kd)):
                effective.append(abs(ff + kp*(qd-q) + kd*(dqd-dq)))
    for label, vals in (("abs_tau_ff",tau_ff),("abs_effective_torque_proxy",effective)):
        s=summary(vals)
        rms=math.sqrt(statistics.fmean([v*v for v in vals])) if vals else math.nan
        out += [{"arm":arm,"metric":label+"_median","value":s["median"]},
                {"arm":arm,"metric":label+"_p95","value":s["p95"]},
                {"arm":arm,"metric":label+"_max","value":s["max"]},
                {"arm":arm,"metric":label+"_rms","value":rms}]
    cwin = [r for r in closure if START <= num(r,"active_relative_time_s") < END]
    sat = finite([num(r,"torque_saturation_max") for r in cwin])
    if sat:
        out += [{"arm":arm,"metric":"torque_saturation_max_nm","value":max(sat)},
                {"arm":arm,"metric":"torque_saturation_p95_nm","value":quantile(sat,.95)},
                {"arm":arm,"metric":"torque_at_limit_fraction","value":sum(v>=TAU_LIMIT_NM for v in sat)/len(sat)}]
    d4_s = []
    d4_dq = []
    d4_dt = []
    for r in rows:
        for k,v in r.items():
            if k.startswith("diag_bounded_stance_dq_") and k.endswith("_scalar_s"):
                x=num(r,k)
                if math.isfinite(x) and x>0:d4_s.append(x)
            if k.startswith("diag_bounded_stance_dq_") and k.endswith("_max_abs_delta_dq"):
                x=num(r,k)
                if math.isfinite(x):d4_dq.append(x)
            if k.startswith("diag_bounded_stance_dq_") and k.endswith("_max_abs_delta_d_target"):
                x=num(r,k)
                if math.isfinite(x):d4_dt.append(x)
    gate = finite([num(r,"diag_bounded_stance_dq_gate_active") for r in rows])
    out += [
        {"arm":arm,"metric":"d4_gate_active_fraction","value":statistics.fmean(gate) if gate else math.nan},
        {"arm":arm,"metric":"d4_scalar_s_median_nonzero","value":summary(d4_s)["median"]},
        {"arm":arm,"metric":"d4_scalar_s_p05_nonzero","value":summary(d4_s)["p05"]},
        {"arm":arm,"metric":"d4_scalar_s_p95_nonzero","value":summary(d4_s)["p95"]},
        {"arm":arm,"metric":"d4_max_abs_delta_dq","value":max(d4_dq,default=math.nan)},
        {"arm":arm,"metric":"d4_max_abs_delta_d_target","value":max(d4_dt,default=math.nan)},
    ]
    return out


def lookup(rows: list[dict], arm: str, metric: str) -> float:
    for r in rows:
        if r.get("arm") == arm and r.get("metric") == metric:
            try:return float(r["value"])
            except:return math.nan
    return math.nan


def verify_provenance(root: Path, runs_root: Path):
    errors=[]; rows=[]
    parent=read_csv(root/PARENT_PROVENANCE)
    expected={(r.get("arm"),r.get("artifact")):r for r in parent}
    for arm in ARMS:
        for artifact in ("data.csv","data.csv.id_closure.csv","lockstep_trace.csv","run_metadata.txt","controller.log","simulator.log"):
            path=runs_root/arm/artifact
            key=(arm,artifact)
            exp=expected.get(key)
            if not path.is_file():
                errors.append(f"missing {arm}/{artifact}")
                rows.append({"arm":arm,"artifact":artifact,"verification":"MISSING"});continue
            h=sha256(path); size=path.stat().st_size
            ok=exp is not None and exp.get("sha256")==h and str(exp.get("bytes"))==str(size)
            if not ok:errors.append(f"provenance mismatch {arm}/{artifact}")
            rows.append({"arm":arm,"artifact":artifact,"bytes":size,"sha256":h,
                         "expected_sha256":"" if exp is None else exp.get("sha256",""),
                         "verification":"MATCH" if ok else "MISMATCH"})
    return rows,errors


def make_plots(output: Path, phase_rows: list[dict]):
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return ["matplotlib unavailable; PNG plots not generated"]
    notes=[]
    for signal, label in (("roll_deg","roll (deg)"),("pitch_deg","pitch (deg)"),("world_base_z_m","body z (m)"),("contact_count","contact count")):
        subset=[r for r in phase_rows if r["signal"]==signal]
        if not subset:continue
        fig=plt.figure(figsize=(8,4.5));ax=fig.add_subplot(111)
        for arm in ARMS:
            s=sorted([r for r in subset if r["arm"]==arm],key=lambda r:int(r["phase_bin"]))
            if not s:continue
            x=[float(r["phase_center"]) for r in s]; y=[float(r["mean"]) for r in s]
            ax.plot(x,y,label=arm)
            lo=[float(r["mean"])-float(r["std"]) for r in s];hi=[float(r["mean"])+float(r["std"]) for r in s]
            ax.fill_between(x,lo,hi,alpha=.15)
        ax.set_xlabel("normalized gait phase");ax.set_ylabel(label);ax.legend();ax.grid(True,alpha=.2)
        fig.tight_layout();fig.savefig(output/(signal+"_phase.png"),dpi=160);plt.close(fig)
    return notes


def main() -> int:
    ap=argparse.ArgumentParser();ap.add_argument("--runs-root",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);args=ap.parse_args()
    root=Path(__file__).resolve().parents[4];runs_root=args.runs_root.resolve();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    prov,errors=verify_provenance(root,runs_root);write_csv(out/"provenance.csv",prov)
    arm_data={}; phase_rows=[]; cycle_rows=[]; attitude_rows=[]; contact_rows=[]; act_rows=[]; phase_metrics={}
    for arm in ARMS:
        raw=read_csv(runs_root/arm/"data.csv");closure=read_csv(runs_root/arm/"data.csv.id_closure.csv")
        if not raw:errors.append(f"{arm}: missing/empty data.csv");continue
        phased=add_phase(raw);arm_data[arm]=phased
        for field,label,scale in (("imu_roll_rad","roll_deg",180/math.pi),("imu_pitch_rad","pitch_deg",180/math.pi),("world_base_z_m","world_base_z_m",1.0),("velocity_command_measured_mps","velocity_command_measured_mps",1.0),("velocity_command_applied_mps","velocity_command_applied_mps",1.0),("contact_count","contact_count",1.0),("support_foot_speed_mps","support_foot_speed_mps",1.0)):
            rows,template,expl=phase_fold(arm,phased,field,scale,label);phase_rows.extend(rows);phase_metrics[(arm,field)]=(template,expl)
        rt,re=phase_metrics[(arm,"imu_roll_rad")];pt,pe=phase_metrics[(arm,"imu_pitch_rad")]
        cr=cycle_attitude_rows(arm,phased,rt,pt,closure);cycle_rows.extend(cr)
        roll=[math.degrees(num(r,"imu_roll_rad")) for r in phased];pitch=[math.degrees(num(r,"imu_pitch_rad")) for r in phased]
        for signal,vals,expl in (("roll_deg",roll,re),("pitch_deg",pitch,pe)):
            s=summary(vals); cfield=signal.split("_")[0]+"_template_corr"; rfield=signal.split("_")[0]+"_template_rmse_deg"; cs=[float(r[cfield]) for r in cr if math.isfinite(float(r[cfield]))];rs=[float(r[rfield]) for r in cr if math.isfinite(float(r[rfield]))]
            ptpfield=signal.split("_")[0]+"_ptp_deg"; meansfield=signal.split("_")[0]+"_mean_deg"; pts=[float(r[ptpfield]) for r in cr];mts=[float(r[meansfield]) for r in cr];cts=[.5*(float(r["t_start"])+float(r["t_end"])) for r in cr]
            attitude_rows.append({"arm":arm,"signal":signal,**s,"phase_explained_variance":expl,"cycle_corr_median":summary(cs)["median"],"cycle_corr_p05":summary(cs)["p05"],"cycle_rmse_p90":quantile(rs,.90),"cycle_ptp_median":summary(pts)["median"],"cycle_ptp_p95":summary(pts)["p95"],"cycle_ptp_slope_per_s":linear_slope(cts,pts),"cycle_mean_slope_per_s":linear_slope(cts,mts)})
        contact_rows.extend(contact_quality(arm,phased));act_rows.extend(actuation_quality(arm,phased,closure))
    write_csv(out/"attitude_summary.csv",attitude_rows);write_csv(out/"phase_folded.csv",phase_rows);write_csv(out/"cycle_summary.csv",cycle_rows);write_csv(out/"contact_quality.csv",contact_rows);write_csv(out/"actuation_quality.csv",act_rows)
    plot_notes=make_plots(out,phase_rows)
    def att(arm,signal):return next((r for r in attitude_rows if r["arm"]==arm and r["signal"]==signal),{})
    bro,bpi=att("B","roll_deg"),att("B","pitch_deg")
    structured=all(r and float(r.get("phase_explained_variance",math.nan))>=.40 and float(r.get("cycle_corr_median",math.nan))>=.70 and float(r.get("cycle_rmse_p90",math.inf))<=.35*max(float(r.get("cycle_ptp_median",0)),1e-9) for r in (bro,bpi))
    drift=False
    for r in (bro,bpi):
        if not r:continue
        slope=float(r.get("cycle_ptp_slope_per_s",0));med=float(r.get("cycle_ptp_median",0));
        if math.isfinite(slope) and med>0 and slope*(END-START)>max(.5*med,2.0):drift=True
    a_diag=lookup(contact_rows,"A","expected_diagonal_mask_fraction");b_diag=lookup(contact_rows,"B","expected_diagonal_mask_fraction");a_le1=lookup(contact_rows,"A","contact_le1_fraction");b_le1=lookup(contact_rows,"B","contact_le1_fraction");a_slip=lookup(contact_rows,"A","support_foot_speed_p95");b_slip=lookup(contact_rows,"B","support_foot_speed_p95");a_tau=lookup(act_rows,"A","abs_effective_torque_proxy_rms");b_tau=lookup(act_rows,"B","abs_effective_torque_proxy_rms");a_sat=lookup(act_rows,"A","torque_at_limit_fraction");b_sat=lookup(act_rows,"B","torque_at_limit_fraction")
    costs=[]
    if math.isfinite(a_diag) and math.isfinite(b_diag) and a_diag-b_diag>.20:costs.append(f"diagonal-mask occupancy down {a_diag-b_diag:.3f}")
    if math.isfinite(a_le1) and math.isfinite(b_le1) and b_le1-a_le1>.10:costs.append(f"<=1-contact fraction up {b_le1-a_le1:.3f}")
    if math.isfinite(a_slip) and math.isfinite(b_slip) and b_slip>max(a_slip*1.5,a_slip+.05):costs.append(f"support-foot p95 {a_slip:.4g}->{b_slip:.4g}")
    if math.isfinite(a_tau) and math.isfinite(b_tau) and b_tau>a_tau*1.25:costs.append(f"effective torque RMS {a_tau:.4g}->{b_tau:.4g}")
    if math.isfinite(a_sat) and math.isfinite(b_sat) and b_sat-a_sat>.02:costs.append(f"saturation fraction +{b_sat-a_sat:.3f}")
    if errors:classification="PROTOCOL_FAILURE"
    elif not bro or not bpi:classification="INSUFFICIENT_EVIDENCE"
    elif not structured or drift:classification="UNSTRUCTURED_INSTABILITY"
    elif costs:classification="DYNAMIC_GAIT_WITH_COST"
    else:classification="DYNAMIC_GAIT_STRUCTURED"
    analysis={"classification":classification,"structured_rule_pass":structured,"progressive_drift":drift,"material_costs":costs,"protocol_errors":errors,"plot_notes":plot_notes,"thresholds":{"phase_explained_variance_min":.40,"cycle_corr_median_min":.70,"cycle_rmse_p90_max_fraction_of_median_ptp":.35,"progressive_ptp_growth":"predicted window growth > max(0.5*median_ptp, 2 deg)","contact_costs":"diag occupancy -0.20, <=1-contact +0.10, support p95 > max(1.5x,+0.05m/s), torque RMS >1.25x, saturation +0.02"}}
    (out/"analysis.json").write_text(json.dumps(analysis,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    pitch_max=bpi.get("max",math.nan) if bpi else math.nan
    pitch_expl=bpi.get("phase_explained_variance",math.nan) if bpi else math.nan
    pitch_corr=bpi.get("cycle_corr_median",math.nan) if bpi else math.nan
    lines=["# Phase1 D4 gait-quality audit","",f"Top-level classification: `{classification}`","",f"B maximum signed pitch observed: `{pitch_max}` deg.",f"B pitch phase-explained variance: `{pitch_expl}`; median cycle-template correlation: `{pitch_corr}`.",f"Structured periodic-motion rule: `{'PASS' if structured else 'FAIL'}`; progressive drift: `{drift}`.",f"Material cost flags: `{'; '.join(costs) if costs else 'none'}`.","","Interpretation must be completed from the generated attitude/phase/cycle/contact/actuation tables. Maximum angle alone is not an instability criterion."]
    if errors:lines += ["","Protocol/provenance errors:"]+[f"- {e}" for e in errors]
    if plot_notes:lines += ["","Plot notes:"]+[f"- {e}" for e in plot_notes]
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"classification={classification} structured={structured} drift={drift} costs={len(costs)}")
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
