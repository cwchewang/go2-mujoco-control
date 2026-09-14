#!/usr/bin/env python3
"""Analyze the three Phase1 varying lockstep baseline runs."""
from __future__ import annotations
import argparse
import csv
import hashlib
import itertools
import math
import subprocess

from pathlib import Path
EXPECTED_DT_MS = 2
METRIC_KEYS = (
    "velocity_command_measured_mps",
    "velocity_command_applied_mps",
    "velocity_command_tracking_error_mps",
    "imu_roll_rad",
    "imu_pitch_rad",
    "contact_count",
    "velocity_command_gait_period_s",
    "velocity_command_gait_duty",
)

def meta(path):
    result = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                result[key] = value
    return result

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()

def number(row, key):
    try:
        return float(row.get(key, "nan"))
    except (TypeError, ValueError):
        return math.nan

def percentile(values, q):
    values = sorted(x for x in values if math.isfinite(x))
    if not values:
        return math.nan
    position = (len(values) - 1) * q
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (position - low)

def rows_from(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))

def trace_from(path):
    rows = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        header = None
        for line in stream:
            if not line.strip() or line.startswith("#"):
                continue
            if header is None:
                header = line.strip().split(",")
                continue
            rows.append(dict(zip(header, line.strip().split(","))))
    return rows

def gate(run, name, passed, detail):
    return {"run_id": run, "gate": name, "status": "PASS" if passed else "FAIL",
            "detail": detail}

def protocol(run_dir, run):
    trace_path = run_dir / "lockstep_trace.csv"
    log_path = run_dir / "simulator.log"
    if not trace_path.is_file():
        return [gate(run, "trace_present", False, "missing lockstep_trace.csv")], {
            "protocol_status": "FAIL", "trace_rows": "0", "intervals": "0",
            "dt_ms": "", "violations": "", "fail_closed": "unknown"}
    rows = trace_from(trace_path)
    gates = [gate(run, "trace_present", bool(rows), "rows=%d" % len(rows))]
    intervals = [row for row in rows if row.get("phase") == "lockstep"]
    ticks = [int(row["sim_tick_ms"]) for row in rows]
    diffs = [b - a for a, b in zip(ticks, ticks[1:])]
    dt_ok = bool(diffs) and set(diffs) == {EXPECTED_DT_MS}
    gates.append(gate(run, "constant_sim_tick", dt_ok,
                      "diffs=%s" % sorted(set(diffs))))
    violations = sorted({int(row.get("violations", "0")) for row in rows})
    gates.append(gate(run, "no_protocol_violations", violations == [0],
                      "violations=%s" % violations))
    state_ok = all(int(row["ack_state_seq"]) == int(row["sim_tick_ms"])
                   for row in intervals)
    gates.append(gate(run, "ack_state_matches_published_tick",
                      bool(intervals) and state_ok,
                      "intervals=%d" % len(intervals)))
    window_deltas = [
        int(row["cmd_seq_at_ready"]) - int(row["cmd_seq_at_publish"])
        for row in intervals]
    delta_counts = ",".join("%d:%d" % (x, window_deltas.count(x))
                            for x in sorted(set(window_deltas)))
    command_ok = all(
        int(row["cmd_seq_at_ready"]) - int(row["cmd_seq_at_publish"]) == 1
        and int(row["ack_cmd_seq"]) == int(row["cmd_seq_at_ready"])
        for row in intervals)
    gates.append(gate(run, "one_command_update_per_state_tick",
                      bool(intervals) and command_ok,
                      "intervals=%d delta_counts=%s" %
                      (len(intervals), delta_counts)))
    trigger_ok = bool(intervals) and all(
        int(row["exchange_trigger"]) == 3 for row in intervals)
    gates.append(gate(run, "ack_matched_exchange_trigger", trigger_ok,
                      "triggers=%s" % sorted({row.get("exchange_trigger")
                                                for row in intervals})))
    failed_closed = "SIM_LOCKSTEP_FAIL_CLOSED" in (
        log_path.read_text(encoding="utf-8", errors="replace")
        if log_path.exists() else "")
    gates.append(gate(run, "no_fail_closed_marker", not failed_closed,
                      "marker=%s" % failed_closed))
    summary = {
        "protocol_status": "PASS" if all(x["status"] == "PASS" for x in gates)
        else "FAIL",
        "trace_rows": str(len(rows)), "intervals": str(len(intervals)),
        "dt_ms": str(EXPECTED_DT_MS if dt_ok else ""),
        "violations": ",".join(str(x) for x in violations),
        "fail_closed": str(failed_closed).lower()}
    return gates, summary

def run_metrics(run_dir, run):
    rows = rows_from(run_dir / "data.csv")
    active = [row for row in rows if number(row, "velocity_command_active") > 0.5]
    result = {"run_id": run, "rows": str(len(rows)),
              "active_rows": str(len(active))}
    times = [number(row, "cmd_time_s") for row in rows]
    result["duration_s"] = ("%.6g" % (max(times) - min(times))) if times else ""
    for key in METRIC_KEYS:
        values = [number(row, key) for row in active]
        clean = [x for x in values if math.isfinite(x)]
        short = key.replace("velocity_command_", "").replace("imu_", "")
        result[short + "_p95_abs"] = ("%.9g" % percentile(
            [abs(x) for x in clean], 0.95)) if clean else ""
        result[short + "_max_abs"] = "%.9g" % max(
            (abs(x) for x in clean), default=math.nan)
    metadata = meta(run_dir / "run_metadata.txt")
    for key in ("controller_status", "safety_status", "quality_status",
                "analysis_status", "ground_truth_status", "dynamics_status",
                "completion_status", "manifest_status", "lockstep", "git_head",
                "git_dirty", "simulator_sha256", "controller_sha256",
                "scene_sha256", "profile_sha256"):
        result[key] = metadata.get(key, "")
    result["data_csv_sha256"] = sha256(run_dir / "data.csv")
    result["trace_sha256"] = sha256(run_dir / "lockstep_trace.csv")
    return result

def pairwise(run_dirs):
    result = []
    for left, right in itertools.combinations(sorted(run_dirs), 2):
        def keyed(rows):
            return {round(number(row, "cmd_time_s"), 6): row for row in rows
                    if math.isfinite(number(row, "cmd_time_s"))}
        lmap = keyed(rows_from(run_dirs[left] / "data.csv"))
        rmap = keyed(rows_from(run_dirs[right] / "data.csv"))
        common = sorted(set(lmap) & set(rmap))
        item = {"pair": left + "-" + right, "common_rows": str(len(common))}
        for key in METRIC_KEYS:
            values = [abs(number(lmap[t], key) - number(rmap[t], key))
                      for t in common
                      if math.isfinite(number(lmap[t], key))
                      and math.isfinite(number(rmap[t], key))]
            short = key.replace("velocity_command_", "").replace("imu_", "")
            item[short + "_p95_abs_diff"] = ("%.9g" % percentile(values, 0.95)
                                             if values else "")
            item[short + "_max_abs_diff"] = "%.9g" % max(values, default=math.nan)
        result.append(item)
    return result

def write_csv(path, rows):
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

def provenance_lines(root, summary_rows):
    lines = [
        "", "## Provenance hashes", "",
        "|run|simulator SHA256|controller SHA256|data.csv SHA256|trace SHA256|",
        "|---|---|---|---|---|",
    ]
    for item in summary_rows:
        lines.append("|{run_id}|{simulator_sha256}|{controller_sha256}|{data_csv_sha256}|{trace_sha256}|".format(**item))
    sources = [
        root / "simulate/src/lockstep.h",
        root / "simulate/src/main.cc",
        root / "simulate/src/unitree_sdk2_bridge.h",
        root / "example/cpp/trot/lockstep_writer_gate.h",
        root / "example/cpp/trot/lockstep_motion_clock.h",
        root / "example/cpp/trot/trot_experiment_lifecycle.cpp",
        root / "example/cpp/trot/trot_experiment_control.cpp",
        root / "example/cpp/scripts/run_trot.sh",
        root / "example/cpp/scripts/run_phase1_lockstep_baseline.sh",
    ]
    lines += ["", "Scoped source SHA256:"]
    lines.extend("- %s: %s" % (path.relative_to(root), sha256(path))
                 for path in sources)
    return lines

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_dirs = {run: args.runs_root / run for run in ("L1", "L2", "L3")}
    protocol_rows, protocol_summaries = [], {}
    for run, run_dir in run_dirs.items():
        gates, summary = protocol(run_dir, run)
        protocol_rows.extend(gates)
        protocol_summaries[run] = summary
    summary_rows = []
    for run, run_dir in run_dirs.items():
        item = run_metrics(run_dir, run)
        item.update(protocol_summaries[run])
        summary_rows.append(item)
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "protocol_gates.csv", protocol_rows)
    write_csv(args.output / "run_summary.csv", summary_rows)
    write_csv(args.output / "pairwise.csv", pairwise(run_dirs))
    root = args.runs_root.parents[4]
    source_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    scene = root / "unitree_robots/go2/scene_leg_lift_demo.xml"
    profile = root / "example/cpp/configs/phase1_velocity_varying.csv"
    overall_pass = all(x["protocol_status"] == "PASS"
                       for x in protocol_summaries.values())
    lines = [
        "# Phase1 lockstep baseline determinism", "",
        "Hypothesis: removing wall-clock scheduling from the simulator/controller exchange preserves the existing varying-command baseline and makes the state/command pairing auditable.", "",
        "Scope: three sequential L1/L2/L3 launches of the existing varying profile; period=0.14 s, duty=0.44, D4=OFF. No D4 or gain/threshold/analyzer change was introduced.", "",
        "Authority source HEAD at launch: %s." % source_head,
        "Scene SHA256: %s." % sha256(scene),
        "Profile SHA256: %s." % sha256(profile), "",
        "Checkpoint gate: %s. The strict one-command-update gate is the limiting result; see protocol_gates.csv." % ("PASS" if overall_pass else "FAIL"), "",
        "Protocol status is reported separately from the legacy physical/safety status. protocol_gates.csv is the checkpoint gate; run_summary.csv records observed run and legacy statuses; pairwise.csv compares common controller timestamps only.", "",
        "The three runs used run_phase1_lockstep_baseline.sh L1, then L2, then L3, with DDS domains 201, 202, and 203. Each run used the frozen Phase1 varying command and lockstep simulator flag.", "",
        "## Per-run result", "",
        "|run|protocol|trace rows|intervals|dt ms|violations|legacy controller|safety|quality|",
        "|---|---|---:|---:|---:|---|---:|---:|---:|",
    ]
    for item in summary_rows:
        lines.append("|{run_id}|{protocol_status}|{trace_rows}|{intervals}|{dt_ms}|{violations}|{controller_status}|{safety_status}|{quality_status}|".format(**item))
    lines += provenance_lines(root, summary_rows)
    lines += [
        "", "## Classification", "",
        "The lockstep protocol is PASS only when every protocol gate is PASS. Physical/safety failures, if present, are reported as observed baseline outcomes and are not converted into protocol failures. Pairwise values are descriptive determinism evidence; no wall-clock comparison or new acceptance threshold is introduced.", "",
        "## Reproduction", "",
        "Build the simulator and controller targets from the task, then invoke the three runner commands sequentially. Raw run directories remain under _runs/phase1_lockstep_baseline_determinism_20260914/.", "",
        "## Checkpoint boundary", "",
        "This is one lockstep baseline determinism checkpoint. No D4, counterfactual, lag, gain, threshold, or additional experiment was run after L1/L2/L3.", ""]
    (args.output / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    return 0 if all(x["protocol_status"] == "PASS" for x in protocol_summaries.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
