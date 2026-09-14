#!/usr/bin/env python3
import csv
import hashlib
import itertools
import math
import re
import statistics
from bisect import bisect_left
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUN_ROOT = ROOT / "example/cpp/experiments/_runs/phase1_lockstep_frozen_ready_handoff_20260914"
OUT = ROOT / "docs/validation/phase1_lockstep_frozen_ready_handoff_20260914"
RUNS = ("L1", "L2", "L3")
GRID = 0.010
TOL = 0.010
OUT.mkdir(parents=True, exist_ok=True)

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def metadata(path):
    return dict(x.split("=", 1) for x in path.read_text(
        errors="replace").splitlines() if "=" in x)

def csv_rows(path):
    with path.open(newline="", errors="replace") as f:
        return list(csv.DictReader(f))

def iv(row, key, default=-1):
    try:
        return int(row[key])
    except (KeyError, TypeError, ValueError):
        return default

def fv(row, key, default=float("nan")):
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return default

def fmt(x):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return ""
    return "%.9f" % x if isinstance(x, float) else str(x)

def med(xs):
    return statistics.median(xs) if xs else float("nan")

def percentile(xs, q):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    x = (len(xs) - 1) * q
    lo, hi = int(x), min(int(x) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (x - lo)

def counts(xs):
    d = {}
    for x in xs:
        d[x] = d.get(x, 0) + 1
    return ",".join("%s:%d" % (k, d[k]) for k in sorted(d))

def emit(path, data, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\\n")
        w.writeheader()
        w.writerows(data)

def gate(run, name, ok, detail):
    return {"run_id": run, "gate": name,
            "status": "PASS" if ok else "FAIL", "detail": detail}

def log_tick(path, pattern):
    m = re.search(pattern, path.read_text(errors="replace"))
    return int(m.group(1)) if m else None

def contact_mask(row):
    return (iv(row, "contact_FR", 0) | iv(row, "contact_FL", 0) << 1 |
            iv(row, "contact_RR", 0) << 2 | iv(row, "contact_RL", 0) << 3)

def nearest(xs, ts, target):
    if not xs:
        return None
    i = bisect_left(ts, target)
    choices = ([i] if i < len(xs) else []) + ([i - 1] if i else [])
    j = min(choices, key=lambda k: abs(ts[k] - target))
    return xs[j] if abs(ts[j] - target) <= TOL + 1e-12 else None

def delta(a, b, key):
    if key == "measured":
        return abs(fv(a, "velocity_command_measured_mps") -
                   fv(b, "velocity_command_measured_mps"))
    if key == "applied":
        return abs(fv(a, "velocity_command_applied_mps") -
                   fv(b, "velocity_command_applied_mps"))
    if key == "excess":
        ae = fv(a, "velocity_command_measured_mps") - fv(
            a, "velocity_command_applied_mps")
        be = fv(b, "velocity_command_measured_mps") - fv(
            b, "velocity_command_applied_mps")
        return abs(ae - be)
    if key in ("roll", "pitch"):
        return abs(math.degrees(fv(a, "imu_%s_rad" % key)) -
                   math.degrees(fv(b, "imu_%s_rad" % key)))
    if key == "contact_count":
        return abs(fv(a, "contact_count") - fv(b, "contact_count"))
    if key == "contact_mask":
        return abs(contact_mask(a) - contact_mask(b))
    if key == "gait_phase":
        return abs(fv(a, "phase") - fv(b, "phase"))
    raise KeyError(key)

info = {}
data_by_run = {}
protocol = []
handoff = []

for run in RUNS:
    d = RUN_ROOT / run
    m = metadata(d / "run_metadata.txt")
    h = csv_rows(d / "lockstep_handoff.csv")[0]
    nq, nv = iv(h, "nq", 0), iv(h, "nv", 0)
    qpos = [fv(h, "qpos_%d" % i) for i in range(nq)]
    qvel = [fv(h, "qvel_%d" % i) for i in range(nv)]
    handoff.append({"run_id": run, "pre_motion_steps": iv(h, "pre_motion_steps"),
                    "sim_tick_ms": iv(h, "sim_tick_ms"),
                    "sim_time_s": h.get("sim_time_s", ""), "nq": nq, "nv": nv,
                    "nu": iv(h, "nu"), "binary_sha256": sha(
                        d / "lockstep_handoff.csv.bin"), "qpos": qpos,
                    "qvel": qvel})
    trace = csv_rows(d / "lockstep_trace.csv")
    lock = [r for r in trace if r.get("phase") == "lockstep"]
    barrier = next((r for r in trace if r.get("phase") == "barrier"), {})
    summary_line = next((x for x in reversed((d / "lockstep_trace.csv").read_text(
        errors="replace").splitlines()) if x.startswith("#summary")), "")
    summary = dict(x.split("=", 1) for x in summary_line[8:].split() if "=" in x)
    diag = csv_rows(d / "data.csv.lockstep_publish.csv")
    gated = [r for r in diag if r.get("gate_engaged") == "1" and
             r.get("writer_branch") == "gated"]
    first = gated[0] if gated else {}
    gated_ticks = [iv(r, "state_tick") for r in gated]
    trace_dt = [iv(b, "sim_tick_ms") - iv(a, "sim_tick_ms")
                for a, b in zip(lock, lock[1:])]
    cmd_delta = [iv(r, "cmd_seq_at_ready") - iv(r, "cmd_seq_at_publish")
                 for r in lock]
    simlog = d / "simulator.log"
    ctrllog = d / "controller.log"
    freeze = log_tick(simlog, r"pre-motion handoff ready: steps=4000 tick=(\d+)")
    capture = log_tick(ctrllog, r"frozen capture tick=(\d+)")
    ready = log_tick(ctrllog, r"READY published: tick=(\d+)")
    first_post = iv(lock[0], "sim_tick_ms", 0) if lock else 0
    data = csv_rows(d / "data.csv")
    data_by_run[run] = data
    active = [r for r in data if iv(r, "velocity_command_active") == 1]
    active_end = max((fv(r, "diag_active_relative_time_s") for r in active),
                     default=float("nan"))
    window = [r for r in active if 32 <= fv(
        r, "diag_active_relative_time_s") < 33]
    excess = [fv(r, "velocity_command_measured_mps") - fv(
        r, "velocity_command_applied_mps") for r in window]
    measured = [fv(r, "velocity_command_measured_mps") for r in window]
    applied = [fv(r, "velocity_command_applied_mps") for r in window]
    desired = [fv(r, "wbc_full_requested_acc_x_mps2") for r in window]
    srbd = [fv(r, "wbc_full_srbd_acc_x_mps2") for r in window]
    ident = [fv(r, "wbc_full_id_qdd_x_mps2") for r in window]
    regimes = sorted(set(r.get("velocity_command_gait_regime", "")
                         for r in window))
    physical = (
        active_end >= 40 and all(m.get(k) == "0" for k in (
            "safety_status", "quality_status", "analysis_status",
            "ground_truth_status", "dynamics_status", "completion_status")) and
        bool(window) and regimes == ["continuous-trot"] and
        0.15 <= med(excess) <= 0.35 and med(desired) < 0 and
        med(srbd) < 0 and med(ident) < 0)
    ps = [
        gate(run, "handoff_tick_8000", iv(h, "pre_motion_steps") == 4000 and
             iv(h, "sim_tick_ms") == 8000 and freeze == 8000,
             "handoff=%s freeze_log=%s" % (h.get("sim_tick_ms", ""), freeze)),
        gate(run, "capture_and_ready_tick_8000",
             capture == 8000 and ready == 8000,
             "capture=%s ready=%s" % (capture, ready)),
        gate(run, "first_gated_lowcmd_8000_seq_1",
             iv(first, "state_tick") == 8000 and
             iv(first, "lockstep_cmd_seq") == 1,
             "tick=%s seq=%s" % (first.get("state_tick", ""),
                                  first.get("lockstep_cmd_seq", ""))),
        gate(run, "first_ack_pair_8000_1",
             iv(barrier, "ack_state_seq") == 8000 and
             iv(barrier, "ack_cmd_seq") == 1,
             "ack=%s,%s" % (barrier.get("ack_state_seq", ""),
                            barrier.get("ack_cmd_seq", ""))),
        gate(run, "first_post_command_tick_8002", first_post == 8002,
             "first_post=%s" % first_post),
        gate(run, "zero_steps_before_first_exact",
             iv(summary, "post_freeze_steps_before_first_exact") == 0,
             "steps=%s" % summary.get("post_freeze_steps_before_first_exact", "")),
        gate(run, "zero_lowcmd_before_ready",
             iv(summary, "commands_before_ready") == 0,
             "commands=%s" % summary.get("commands_before_ready", "")),
        gate(run, "post_handoff_dt2_delta1_no_duplicates",
             bool(lock) and set(trace_dt) == {2} and set(cmd_delta) == {1} and
             len(gated_ticks) == len(set(gated_ticks)),
             "dt=%s delta=%s duplicate_extra=%s" %
             (sorted(set(trace_dt)), sorted(set(cmd_delta)),
              len(gated_ticks) - len(set(gated_ticks)))),
        gate(run, "no_protocol_violation_or_fail_closed",
             iv(summary, "violations") == 0 and iv(summary, "fail_closed") == 0
             and "SIM_LOCKSTEP_FAIL_CLOSED" not in simlog.read_text(
                 errors="replace") and "LOCKSTEP_WRITER_FAIL_CLOSED" not in
             ctrllog.read_text(errors="replace"),
             "violations=%s fail_closed=%s" %
             (summary.get("violations", ""), summary.get("fail_closed", ""))),
    ]
    protocol.extend(ps)
    info[run] = {
        "run_id": run, "source_git_head": m.get("git_head", ""),
        "git_branch": m.get("git_branch", ""), "git_dirty": m.get("git_dirty", ""),
        "simulator_sha256": m.get("simulator_sha256", ""),
        "controller_sha256": m.get("controller_sha256", ""),
        "scene_sha256": m.get("scene_sha256", ""),
        "profile_sha256": m.get("profile_sha256", ""),
        "sim_cpu_affinity": m.get("sim_cpu_affinity", ""),
        "controller_cpu_affinity": m.get("controller_cpu_affinity", ""),
        "domain_id": m.get("domain_id", ""), "freeze_tick": freeze,
        "capture_tick": capture, "ready_tick": ready,
        "first_gated_tick": iv(first, "state_tick", 0),
        "first_lowcmd_cmd_seq": iv(first, "lockstep_cmd_seq", 0),
        "first_ack_state_tick": iv(barrier, "ack_state_seq", 0),
        "first_ack_cmd_seq": iv(barrier, "ack_cmd_seq", 0),
        "first_post_command_sim_tick": first_post,
        "mj_steps_before_first_exact": iv(
            summary, "post_freeze_steps_before_first_exact"),
        "lowcmd_before_ready": iv(summary, "commands_before_ready"),
        "frozen_publish_count": iv(summary, "frozen_publishes"),
        "active_relative_duration_s": fmt(active_end), "active_rows": len(active),
        "window_rows_32_33": len(window), "measured_median_mps": fmt(med(measured)),
        "applied_median_mps": fmt(med(applied)), "excess_median_mps": fmt(med(excess)),
        "wbc_desired_ax_median_mps2": fmt(med(desired)),
        "srbd_ax_median_mps2": fmt(med(srbd)), "id_qdd_x_median_mps2": fmt(med(ident)),
        "gait_regimes_32_33": "|".join(regimes),
        "controller_status": m.get("controller_status", ""),
        "safety_status": m.get("safety_status", ""),
        "quality_status": m.get("quality_status", ""),
        "analysis_status": m.get("analysis_status", ""),
        "ground_truth_status": m.get("ground_truth_status", ""),
        "dynamics_status": m.get("dynamics_status", ""),
        "completion_status": m.get("completion_status", ""),
        "trace_rows": len(trace), "post_trace_dt_values": counts(trace_dt),
        "post_command_delta_values": counts(cmd_delta),
        "gated_tick_counts": counts(gated_ticks),
        "protocol_status": "PASS" if all(x["status"] == "PASS" for x in ps) else "FAIL",
        "physical_status": "PASS" if physical else "FAIL",
    }
base = handoff[0]
base_qpos = list(base["qpos"])
base_qvel = list(base["qvel"])
base_binary_sha = base["binary_sha256"]
for row in handoff:
    diffs = [abs(a - b) for a, b in zip(row["qpos"], base_qpos)]
    diffs += [abs(a - b) for a, b in zip(row["qvel"], base_qvel)]
    if len(row["qpos"]) != len(base_qpos) or len(row["qvel"]) != len(base_qvel):
        diffs.append(float("inf"))
    mx = max(diffs, default=float("nan"))
    row["numeric_max_abs_diff_vs_L1"] = fmt(mx)
    row["numeric_equal_vs_L1"] = mx <= 1e-12
    row["binary_equal_vs_L1"] = row["binary_sha256"] == base_binary_sha
    row["qpos"] = ";".join("%.17g" % x for x in row["qpos"])
    row["qvel"] = ";".join("%.17g" % x for x in row["qvel"])
handoff_fields = ["run_id", "pre_motion_steps", "sim_tick_ms", "sim_time_s",
                  "nq", "nv", "nu", "binary_sha256", "qpos", "qvel",
                  "numeric_max_abs_diff_vs_L1", "numeric_equal_vs_L1",
                  "binary_equal_vs_L1"]
emit(OUT / "handoff_states.csv", handoff, handoff_fields)
emit(OUT / "protocol_gates.csv", protocol,
     ["run_id", "gate", "status", "detail"])

run_start = []
for run in RUNS:
    dg = csv_rows(RUN_ROOT / run / "data.csv.lockstep_publish.csv")
    g = [r for r in dg if r.get("gate_engaged") == "1" and
         r.get("writer_branch") == "gated"]
    run_start.append(fv(g[0], "running_time_s") if g else 0.0)
common_start = max(run_start)
common_end = min(float(info[r]["active_relative_duration_s"]) for r in RUNS)
start = math.ceil(common_start / GRID - 1e-9) * GRID
end = math.floor(common_end / GRID + 1e-9) * GRID
points = max(0, int(round((end - start) / GRID)) + 1)
metrics = ("measured", "applied", "excess", "roll", "pitch",
           "contact_count", "contact_mask", "gait_phase")
aligned = {}
for run, begin in zip(RUNS, run_start):
    active = [r for r in data_by_run[run]
              if iv(r, "velocity_command_active") == 1 and
              fv(r, "diag_active_relative_time_s") >= begin]
    active.sort(key=lambda r: fv(r, "diag_active_relative_time_s"))
    times = [fv(r, "diag_active_relative_time_s") for r in active]
    aligned[run] = [nearest(active, times, start + i * GRID)
                    for i in range(points)]

pair_fields = ["pair", "grid_dt_s", "join_tolerance_s",
               "common_start_s", "common_end_s", "grid_points"]
pair_fields += ["%s_%s_abs_diff" % (m, s)
                for m in metrics for s in ("p50", "p95", "max")]
pair_fields += ["first_sustained_divergence_s",
                "first_sustained_divergence_before_40s"]
pairs = []
for left, right in itertools.combinations(RUNS, 2):
    item = {"pair": left + "__" + right, "grid_dt_s": fmt(GRID),
            "join_tolerance_s": fmt(TOL), "common_start_s": fmt(start),
            "common_end_s": fmt(end), "grid_points": points}
    bad = []
    for metric in metrics:
        values = [delta(a, b, metric) for a, b in zip(
            aligned[left], aligned[right]) if a is not None and b is not None]
        item["%s_p50_abs_diff" % metric] = fmt(percentile(values, .5))
        item["%s_p95_abs_diff" % metric] = fmt(percentile(values, .95))
        item["%s_max_abs_diff" % metric] = fmt(max(values)
                                               if values else float("nan"))
    for a, b in zip(aligned[left], aligned[right]):
        bad.append(a is None or b is None or
                   delta(a, b, "measured") > .05 or
                   delta(a, b, "roll") > 2 or delta(a, b, "pitch") > 2)
    streak = first = before = 0
    for i, is_bad in enumerate(bad):
        streak = streak + 1 if is_bad else 0
        if streak >= 10:
            onset = start + (i - 9) * GRID
            if not first:
                first = onset
            if onset < 40 and not before:
                before = onset
    item["first_sustained_divergence_s"] = fmt(first or None)
    item["first_sustained_divergence_before_40s"] = fmt(before or None)
    pairs.append(item)
emit(OUT / "pairwise.csv", pairs, pair_fields)

excess = [float(info[r]["excess_median_mps"]) for r in RUNS]
excess_range = max(excess) - min(excess)
all_protocol = all(info[r]["protocol_status"] == "PASS" for r in RUNS)
all_physical = all(info[r]["physical_status"] == "PASS" for r in RUNS)
no_early = all(not x["first_sustained_divergence_before_40s"] for x in pairs)
if not all_protocol:
    decision = "FROZEN_HANDOFF_PROTOCOL_FAIL"
elif not all_physical:
    decision = "FROZEN_HANDOFF_PHYSICAL_FAIL"
elif excess_range > .010 or not no_early:
    decision = "FROZEN_HANDOFF_STILL_NONDETERMINISTIC"
else:
    decision = "READY_FOR_CAUSAL_AB"
summary_fields = [
    "run_id", "source_git_head", "git_branch", "git_dirty",
    "simulator_sha256", "controller_sha256", "scene_sha256", "profile_sha256",
    "sim_cpu_affinity", "controller_cpu_affinity", "domain_id", "freeze_tick",
    "capture_tick", "ready_tick", "first_gated_tick", "first_lowcmd_cmd_seq",
    "first_ack_state_tick", "first_ack_cmd_seq", "first_post_command_sim_tick",
    "mj_steps_before_first_exact", "lowcmd_before_ready", "frozen_publish_count",
    "active_relative_duration_s", "active_rows", "window_rows_32_33",
    "measured_median_mps", "applied_median_mps", "excess_median_mps",
    "wbc_desired_ax_median_mps2", "srbd_ax_median_mps2", "id_qdd_x_median_mps2",
    "gait_regimes_32_33", "controller_status", "safety_status", "quality_status",
    "analysis_status", "ground_truth_status", "dynamics_status",
    "completion_status", "trace_rows", "post_trace_dt_values",
    "post_command_delta_values", "gated_tick_counts", "protocol_status",
    "physical_status",
]
emit(OUT / "run_summary.csv", [info[r] for r in RUNS], summary_fields)

source_paths = [
    "simulate/src/lockstep.h", "simulate/src/main.cc",
    "simulate/src/unitree_sdk2_bridge.h", "simulate/src/tests/test_lockstep.cpp",
    "example/cpp/trot/trot_experiment.h",
    "example/cpp/trot/trot_experiment_lifecycle.cpp",
    "example/cpp/trot/trot_experiment_control.cpp",
    "example/cpp/tests/test_lockstep_motion_clock_integration.cpp",
    "example/cpp/trot/lockstep_writer_gate.h",
    "example/cpp/trot/lockstep_motion_clock.h",
    "example/cpp/scripts/run_trot.sh",
    "example/cpp/configs/phase1_velocity_varying.csv",
    "unitree_robots/go2/scene_leg_lift_demo.xml",
]

lines = [
    "Phase1 frozen-state READY handoff, 2026-09-14",
    "",
    "Base checkpoint: e7c7c88edd4e461c7b819397d5038b7d8786e9b6.",
    "Decision: %s." % decision,
    "",
    "Stage 0 audit preceded behavior edits. The inherited deterministic 4000-step zero-control routine serializes the handoff state at tick 8000. The old BarrierComplete-only condition left a wall-clock mj_step path active, advancing the state to observed ticks 9090-9496 before the first gated publish. The old bridge had no immutable 8000 repetition or READY. The controller settled, captured joints/world reference, prepared the gate and clock, then started its writer without READY.",
    "",
    "Stage 1 adds verification metadata only: the simulator freezes at 8000 and republishes it, accepts exact READY 8000, then requires the exact first LowCmd/ack pair before one step to 8002. READY alone cannot step and pre-READY LowCmd arrivals fail closed. The controller sends READY after capture and before the gated writer. Flag-off behavior is unchanged.",
    "",
    "Frozen handoff evidence is in handoff_states.csv, protocol_gates.csv, and run_summary.csv. Handoff numeric equality uses the required <=1e-12 gate and binary equality is reported by SHA256.",
    "",
    "|run|freeze|capture|READY|first gated|ack|first post|steps before exact|LowCmd before READY|frozen publishes|protocol|physical|",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
]
for run in RUNS:
    x = info[run]
    lines.append("|%s|%s|%s|%s|%s|%s,%s|%s|%s|%s|%s|%s|%s|" % (
        run, x["freeze_tick"], x["capture_tick"], x["ready_tick"],
        x["first_gated_tick"], x["first_ack_state_tick"],
        x["first_ack_cmd_seq"], x["first_post_command_sim_tick"],
        x["mj_steps_before_first_exact"], x["lowcmd_before_ready"],
        x["frozen_publish_count"], x["protocol_status"],
        x["physical_status"]))
lines += [
    "",
    "The physical gate is the inherited active-duration/status/continuous-trot/excess and negative WBC-SRBD-ID acceleration gate. Pairwise.csv uses the preregistered 10 ms active-relative grid, 10 ms join tolerance, and 10-consecutive-point divergence definition.",
    "All protocol PASS=%s; all physical PASS=%s; excess-median range=%s m/s (<=0.010=%s); no sustained divergence before 40 s=%s." % (
        str(all_protocol).lower(), str(all_physical).lower(), fmt(excess_range),
        str(excess_range <= .010).lower(), str(no_early).lower()),
    "",
    "Exactly L1, L2, and L3 ran sequentially with the varying-profile WBC-full running-trot baseline, D4 and other A/B flags OFF, fixed affinity, and DDS domains 231/232/230. No fourth run was launched.",
    "The exact source HEAD, binary hashes, scene/profile hashes, protocol deltas, and raw artifact locations are recorded in run_metadata.txt and run_summary.csv. Source SHA256 values:",
]
for path in source_paths:
    lines.append("%s %s" % (path, sha(ROOT / path)))
lines += [
    "",
    "Checkpoint complete: Stage 0 audit, Stage 1 handshake, Stage 2 tests, and exactly three authorized Stage 3 launches are complete.",
]
if decision == "READY_FOR_CAUSAL_AB":
    lines.append("Recommended next step: run the separately authorized causal D4 A/B; not executed here.")
elif decision == "FROZEN_HANDOFF_STILL_NONDETERMINISTIC":
    lines.append("Recommended next step: resolve reproducibility in a separately authorized checkpoint; not executed here.")
elif decision == "FROZEN_HANDOFF_PHYSICAL_FAIL":
    lines.append("Recommended next step: resolve physical baseline failure in a separately authorized checkpoint; not executed here.")
else:
    lines.append("Recommended next step: inspect the failing freeze/READY protocol gate in a separately authorized checkpoint; not executed here.")
(OUT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("decision=%s protocol=%s physical=%s excess_range=%s no_early=%s" %
      (decision, all_protocol, all_physical, fmt(excess_range), no_early))
for run in RUNS:
    x = info[run]
    print(run, x["protocol_status"], x["physical_status"],
          x["freeze_tick"], x["capture_tick"], x["ready_tick"],
          x["first_gated_tick"], x["first_post_command_sim_tick"])
