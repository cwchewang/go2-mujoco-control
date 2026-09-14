#!/usr/bin/env python3
"""Validate the Phase1 deterministic HighState-pairing repair."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

RUNS = ("L1", "L2", "L3")
DOMAINS = {"L1": "211", "L2": "212", "L3": "213"}
STATUS_KEYS = (
    "controller_status", "safety_status", "quality_status", "analysis_status",
    "ground_truth_status", "dynamics_status", "completion_status",
)
SUMMARY_RE = re.compile(
    r"PAIRED_HIGHSTATE_SUMMARY\s+cycles=(\d+)\s+"
    r"validation_failures=(\d+)\s+async_fallbacks=(\d+)"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paired_summary(run_dir: Path) -> dict[str, str]:
    path = run_dir / "controller.log"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    matches = list(SUMMARY_RE.finditer(text))
    if not matches:
        return {"summary_present": "false", "cycles": "0",
                "validation_failures": "", "async_fallbacks": ""}
    match = matches[-1]
    return {
        "summary_present": "true",
        "cycles": match.group(1),
        "validation_failures": match.group(2),
        "async_fallbacks": match.group(3),
    }


def run_snapshot_comparator(root: Path, run_dirs: dict[str, Path], output: Path) -> tuple[bool, str]:
    tool = root / "example/cpp/tools/analysis/analyze_phase1_frozen_handoff_first_divergence.py"
    snapshots = [str(run_dirs[run] / "mj_snapshot.bin") for run in RUNS]
    if not all(Path(path).is_file() for path in snapshots):
        return False, "missing mj_snapshot.bin"
    command = [sys.executable, str(tool), *snapshots, "--output", str(output)]
    completed = subprocess.run(command, cwd=root, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if completed.returncode != 0 or not output.exists():
        return False, f"snapshot comparator rc={completed.returncode}: {completed.stdout[-1000:]}"
    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        return False, "empty snapshot comparator output"
    classifications = {row.get("classification", "") for row in rows}
    return classifications == {"NO_DIVERGENCE_IN_WINDOW"}, ",".join(sorted(classifications))


def exact_full_run(pair_rows: list[dict], run_rows: list[dict], base) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    row_counts = {row["rows"] for row in run_rows}
    active_counts = {row["active_rows"] for row in run_rows}
    durations = {row["duration_s"] for row in run_rows}
    if len(row_counts) != 1 or len(active_counts) != 1 or len(durations) != 1:
        reasons.append("run row/active/duration counts differ")
    expected_rows = next(iter(row_counts)) if len(row_counts) == 1 else None
    for pair in pair_rows:
        if expected_rows is not None and pair.get("common_rows") != expected_rows:
            reasons.append(f"{pair['pair']}: common_rows {pair.get('common_rows')} != {expected_rows}")
        for key in base.METRIC_KEYS:
            short = key.replace("velocity_command_", "").replace("imu_", "")
            field = short + "_max_abs_diff"
            try:
                value = float(pair.get(field, "nan"))
            except ValueError:
                value = math.nan
            if not math.isfinite(value) or value != 0.0:
                reasons.append(f"{pair['pair']}: {field}={pair.get(field)}")
    for key in STATUS_KEYS:
        values = {row.get(key, "") for row in run_rows}
        if len(values) != 1:
            reasons.append(f"status mismatch {key}: {sorted(values)}")
        elif next(iter(values)) not in ("0", ""):
            reasons.append(f"nonzero status {key}: {next(iter(values))}")
    return not reasons, reasons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[4]
    runs_root = args.runs_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    run_dirs = {run: runs_root / run for run in RUNS}

    sem = load_module(Path(__file__).with_name(
        "analyze_phase1_highstate_semantic_reaudit.py"), "phase1_pairing_sem")
    base = load_module(Path(__file__).with_name(
        "analyze_phase1_lockstep_baseline.py"), "phase1_pairing_base")

    metadata = {run: base.meta(run_dirs[run] / "run_metadata.txt") for run in RUNS}
    heads = {metadata[run].get("git_head", "") for run in RUNS}
    head_ok = len(heads) == 1 and "" not in heads
    runtime_head = next(iter(heads)) if head_ok else ""
    sem.DOMAINS = dict(DOMAINS)
    sem.RUNTIME_HEAD = runtime_head
    sem.WINDOW = (11800, 12600)

    semantic_runs = [sem.load_run(runs_root, run) for run in RUNS]
    semantic_errors = [error for run in semantic_runs for error in run["errors"]]
    audits = [
        sem.pair_audit(semantic_runs[0], semantic_runs[1]),
        sem.pair_audit(semantic_runs[0], semantic_runs[2]),
        sem.pair_audit(semantic_runs[1], semantic_runs[2]),
    ]
    boundary_rows: list[dict] = []
    boundary_clear = True
    for audit in audits:
        pair = f"{audit['left']['run_id']}-{audit['right']['run_id']}"
        consumed = audit["boundaries"]["consumed_high"]
        lowcmd = audit["boundaries"]["lowcmd"]
        row = {
            "pair": pair,
            "consumed_high_first_tick": consumed["first_tick"],
            "consumed_high_status": consumed["status"],
            "consumed_high_field": consumed["field"],
            "lowcmd_first_tick": lowcmd["first_tick"],
            "lowcmd_status": lowcmd["status"],
            "semantic_classification": audit["classification"],
        }
        boundary_rows.append(row)
        if consumed["status"] != "none" or lowcmd["status"] != "none":
            boundary_clear = False
    write_csv(output / "pairwise_boundary.csv", boundary_rows)

    protocol_rows: list[dict] = []
    protocol_ok = True
    protocol_summaries: dict[str, dict] = {}
    run_rows: list[dict] = []
    paired_rows: list[dict] = []
    for run in RUNS:
        gates, summary = base.protocol(run_dirs[run], run)
        protocol_rows.extend(gates)
        protocol_summaries[run] = summary
        protocol_ok = protocol_ok and summary["protocol_status"] == "PASS"
        run_rows.append(base.run_metrics(run_dirs[run], run))
        paired = paired_summary(run_dirs[run])
        paired["run_id"] = run
        paired_rows.append(paired)
    write_csv(output / "protocol_gates.csv", protocol_rows)
    write_csv(output / "paired_highstate_summary.csv", paired_rows)

    paired_ok = all(
        row["summary_present"] == "true"
        and int(row["cycles"]) > 0
        and row["validation_failures"] == "0"
        and row["async_fallbacks"] == "0"
        for row in paired_rows
    )

    pair_rows = base.pairwise(run_dirs)
    write_csv(output / "full_run_pairwise.csv", pair_rows)
    write_csv(output / "run_summary.csv", run_rows)
    full_exact, full_reasons = exact_full_run(pair_rows, run_rows, base)

    snapshot_path = output / "snapshot_first_divergence.csv"
    snapshot_clear, snapshot_detail = run_snapshot_comparator(
        root, run_dirs, snapshot_path
    )

    provenance_rows: list[dict] = []
    for run in RUNS:
        run_dir = run_dirs[run]
        for name in (
            "data.csv", "lockstep_trace.csv", "boundary.bridge.csv",
            "boundary.controller.csv", "mj_snapshot.bin", "run_metadata.txt",
            "controller.log", "simulator.log",
        ):
            path = run_dir / name
            provenance_rows.append({
                "run_id": run, "artifact": name,
                "bytes": path.stat().st_size if path.exists() else "",
                "sha256": sha256(path) if path.exists() else "MISSING",
                "domain_id": metadata[run].get("domain_id", ""),
                "git_head": metadata[run].get("git_head", ""),
                "simulator_sha256": metadata[run].get("simulator_sha256", ""),
                "controller_sha256": metadata[run].get("controller_sha256", ""),
                "scene_sha256": metadata[run].get("scene_sha256", ""),
            })
    write_csv(output / "provenance.csv", provenance_rows)

    domain_ok = all(metadata[run].get("domain_id") == DOMAINS[run] for run in RUNS)
    binary_provenance_ok = head_ok and domain_ok and all(
        len({row.get(key, "") for row in run_rows}) == 1
        for key in ("simulator_sha256", "controller_sha256", "scene_sha256")
    )

    if semantic_errors or not protocol_ok:
        classification = "PROTOCOL_FAILURE"
    elif not paired_ok or not binary_provenance_ok:
        classification = "INSTRUMENTATION_OR_FIX_PERTURBATION"
    elif not boundary_clear:
        classification = "FIX_FAILED_HIGHSTATE_PAIRING_PERSISTS"
    elif not snapshot_clear or not full_exact:
        classification = "FIX_REMOVES_HIGHSTATE_CAUSE_BUT_OTHER_DIVERGENCE_REMAINS"
    else:
        classification = "FIX_VALIDATED_FULL_BASELINE_REPRODUCIBLE"

    analysis = {
        "classification": classification,
        "runtime_head": runtime_head,
        "boundary_clear": boundary_clear,
        "snapshot_clear": snapshot_clear,
        "snapshot_detail": snapshot_detail,
        "full_exact": full_exact,
        "full_exact_reasons": full_reasons,
        "paired_summary_ok": paired_ok,
        "protocol_ok": protocol_ok,
        "binary_provenance_ok": binary_provenance_ok,
        "semantic_errors": semantic_errors,
        "protocol_summaries": protocol_summaries,
    }
    (output / "analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# Phase 1 HighState pairing fix validation", "",
        f"Top-level classification: `{classification}`", "",
        f"Runtime HEAD: `{runtime_head or 'unresolved'}`", "",
        f"- Lockstep protocol: {'PASS' if protocol_ok else 'FAIL'}",
        f"- Paired HighState runtime validation: {'PASS' if paired_ok else 'FAIL'}",
        f"- 11800–12600 consumed-HighState/LowCmd window: {'CLEAR' if boundary_clear else 'DIVERGED'}",
        f"- 7.999–13.0 snapshot window: {'CLEAR' if snapshot_clear else 'DIVERGED'} ({snapshot_detail})",
        f"- Full-run exact selected-metric repeatability: {'PASS' if full_exact else 'FAIL'}",
        f"- Binary/source provenance: {'PASS' if binary_provenance_ok else 'FAIL'}",
        "",
        "Pairwise boundary table is in `pairwise_boundary.csv`; full-run differences are in `full_run_pairwise.csv`; protocol and paired-runtime gates have dedicated CSVs. Raw artifacts are hashed in `provenance.csv`.",
    ]
    if semantic_errors:
        lines += ["", "Semantic/protocol errors:"] + [f"- {x}" for x in semantic_errors[:20]]
    if full_reasons:
        lines += ["", "Full-run exact-repeatability failures:"] + [f"- {x}" for x in full_reasons[:30]]
    (output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"classification={classification}")
    print(f"runtime_head={runtime_head}")
    # A non-success research classification is still a valid completed analysis.
    # Return nonzero only for malformed/incomplete execution paths that prevent
    # the closeout artifacts from being produced. All classifications above are
    # intentional scientific outcomes and must allow the executor to close out.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
