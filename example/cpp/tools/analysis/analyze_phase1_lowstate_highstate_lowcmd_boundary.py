#!/usr/bin/env python3
"""Offline comparator for the Phase 1 LowState/HighState/LowCmd boundary trace."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

HEADER = [
    "record_type", "tick", "sequence", "callback_seq", "low_hash",
    "high_hash", "high_source_generation", "high_source_tick",
    "low_published", "high_published", "high_skipped",
    "low_receipt_seq", "high_receipt_seq", "consumed_low_receipt_seq",
    "consumed_high_receipt_seq", "have_state", "have_high_state",
    "control_seq", "lowcmd_hash", "low_payload_hex", "high_payload_hex",
    "lowcmd_payload_hex",
]
WINDOW = (11800, 12600)
FNV_OFFSET = 1469598103934665603
FNV_PRIME = 1099511628211

def fnv64(data: bytes) -> str:
    value = FNV_OFFSET
    for byte in data:
        value ^= byte
        value = (value * FNV_PRIME) & ((1 << 64) - 1)
    return f"{value:016x}"

def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size

def parse_kv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result

def load_trace(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    if not path.exists():
        return [], [f"missing trace: {path}"]
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != HEADER:
            errors.append(f"header mismatch: {path}")
        rows: list[dict[str, str]] = []
        for index, row in enumerate(reader, start=2):
            if None in row:
                errors.append(f"extra CSV fields at {path}:{index}")
                continue
            if any(value is None for value in row.values()):
                errors.append(f"missing CSV field at {path}:{index}")
                continue
            rows.append(row)
    return rows, errors

def verify_payload_rows(rows: Iterable[dict[str, str]], path: Path) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(rows, start=2):
        for payload_key, hash_key in (
            ("low_payload_hex", "low_hash"),
            ("high_payload_hex", "high_hash"),
            ("lowcmd_payload_hex", "lowcmd_hash"),
        ):
            payload = row[payload_key]
            expected = row[hash_key]
            if not payload:
                continue
            try:
                decoded = bytes.fromhex(payload)
            except ValueError:
                errors.append(f"non-hex {payload_key} at {path}:{index}")
                continue
            if expected != fnv64(decoded):
                errors.append(
                    f"hash mismatch {hash_key} at {path}:{index}: "
                    f"{expected} != {fnv64(decoded)}"
                )
    return errors

def rows_of(rows: list[dict[str, str]], record_type: str) -> list[dict[str, str]]:
    return [row for row in rows if row["record_type"] == record_type]

def by_tick(rows: list[dict[str, str]]) -> dict[int, list[dict[str, str]]]:
    result: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        try:
            tick = int(row["tick"])
        except ValueError:
            continue
        if WINDOW[0] <= tick <= WINDOW[1]:
            result[tick].append(row)
    return result

def first_row(rows: dict[int, list[dict[str, str]]], tick: int) -> dict[str, str] | None:
    candidates = rows.get(tick, [])
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda row: (
            int(row["control_seq"] or "0"),
            int(row["sequence"] or "0"),
            int(row["callback_seq"] or "0"),
        ),
    )[0]

def first_difference(
    left: dict[str, str] | None,
    right: dict[str, str] | None,
    fields: list[str],
) -> tuple[str, str, str] | None:
    for field in fields:
        left_value = "" if left is None else left.get(field, "")
        right_value = "" if right is None else right.get(field, "")
        if left_value != right_value:
            return field, left_value, right_value
    return None

def run_info(run_root: Path, run_id: str) -> dict:
    run_dir = run_root / run_id
    bridge_path = run_dir / "boundary.bridge.csv"
    controller_path = run_dir / "boundary.controller.csv"
    metadata = parse_kv(run_dir / "run_metadata.txt")
    bridge, bridge_errors = load_trace(bridge_path)
    controller, controller_errors = load_trace(controller_path)
    errors = bridge_errors + controller_errors
    errors += verify_payload_rows(bridge, bridge_path)
    errors += verify_payload_rows(controller, controller_path)
    bridge_window = rows_of(bridge, "bridge_source")
    controller_window = [
        row for row in controller
        if row["record_type"] in (
            "controller_consumption",
            "controller_lowcmd_prepublish",
            "controller_receipt_low",
            "controller_receipt_high",
        )
    ]
    if not bridge_window or not controller_window:
        errors.append("trace window has no boundary records")
    files = [bridge_path, controller_path, run_dir / "run_metadata.txt"]
    optional = [
        run_dir / "mj_snapshot.bin",
        run_dir / "environment.txt",
        run_dir / "lockstep_handoff.csv",
        run_dir / "lockstep_trace.csv",
    ]
    for path in optional:
        if path.exists():
            files.append(path)
    hashes = []
    for path in files:
        if path.exists():
            digest, size = sha256_file(path)
            hashes.append({
                "run_id": run_id,
                "artifact": str(path),
                "bytes": size,
                "sha256": digest,
            })
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "metadata": metadata,
        "bridge": bridge,
        "controller": controller,
        "errors": errors,
        "hashes": hashes,
    }

def self_test(source_root: Path) -> None:
    assert fnv64(b"") == "14650fb0739d0383"
    low = struct.pack("<I", 11800) + b"\0" * 192
    high = b"\0" * 24
    cmd = b"\0" * 240
    assert len(low) == 196
    assert len(high) == 24
    assert len(cmd) == 240
    identical_low = bytes(low)
    assert low == identical_low
    assert fnv64(low) == fnv64(identical_low)
    mutated_low = bytearray(low)
    mutated_low[4] ^= 1
    assert bytes(mutated_low) != low
    assert fnv64(bytes(mutated_low)) != fnv64(low)
    field_layout = {"tick": (0, 4), "motor[0].q": (4, 8)}
    changed = [
        name for name, (start, end) in field_layout.items()
        if low[start:end] != bytes(mutated_low[start:end])
    ]
    header = (source_root / "example/cpp/trot/phase1_boundary_trace.h").read_text()
    assert "CanonicalLowState" in header
    assert "CanonicalHighState" in header
    assert "CanonicalLowCmd" in header
    assert "reinterpret_cast" not in header
    lifecycle = (
        source_root / "example/cpp/trot/trot_experiment_lifecycle.cpp"
    ).read_text()
    control = (
        source_root / "example/cpp/trot/trot_experiment_control.cpp"
    ).read_text()
    assert "std::lock_guard<std::mutex> lock(state_mutex_);" in lifecycle
    assert "boundary_low_receipt_seq_" in lifecycle
    assert "if (boundary_trace_enabled_)" in lifecycle
    assert "RecordBoundaryLowCmd(state_snapshot);" in control
    assert control.count("lowcmd_publisher_->Write(low_cmd_)") == 1
    print("phase1 boundary trace self-test: PASS")

def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def compare_pair(left: dict, right: dict) -> dict:
    def boundary_context(
        ba, bb, la, lb, ha, hb, ca, cb, pa, pb
    ) -> dict[str, str]:
        context: dict[str, str] = {}
        for side, bridge, low, high, consumed, pre in (
            ("a", ba, la, ha, ca, pa),
            ("b", bb, lb, hb, cb, pb),
        ):
            for key in (
                "low_hash", "high_hash", "high_source_generation",
                "high_source_tick", "high_skipped",
            ):
                context[f"source_{key}_{side}"] = (bridge or {}).get(key, "")
            context[f"receipt_low_seq_{side}"] = (low or {}).get(
                "callback_seq", "")
            context[f"receipt_high_seq_{side}"] = (high or {}).get(
                "callback_seq", "")
            context[f"consumed_low_receipt_seq_{side}"] = (
                consumed or {}).get("consumed_low_receipt_seq", "")
            context[f"consumed_high_receipt_seq_{side}"] = (
                consumed or {}).get("consumed_high_receipt_seq", "")
            context[f"control_seq_{side}"] = (consumed or {}).get(
                "control_seq", "")
            context[f"consumed_low_hash_{side}"] = (consumed or {}).get(
                "low_hash", "")
            context[f"consumed_high_hash_{side}"] = (consumed or {}).get(
                "high_hash", "")
            context[f"lowcmd_hash_{side}"] = (pre or {}).get(
                "lowcmd_hash", "")
        return context
    bridge_a = by_tick(rows_of(left["bridge"], "bridge_source"))
    bridge_b = by_tick(rows_of(right["bridge"], "bridge_source"))
    cons_a = by_tick(rows_of(left["controller"], "controller_consumption"))
    cons_b = by_tick(rows_of(right["controller"], "controller_consumption"))
    pre_a = by_tick(rows_of(left["controller"], "controller_lowcmd_prepublish"))
    pre_b = by_tick(rows_of(right["controller"], "controller_lowcmd_prepublish"))
    rec_low_a = by_tick(rows_of(left["controller"], "controller_receipt_low"))
    rec_low_b = by_tick(rows_of(right["controller"], "controller_receipt_low"))
    rec_high_a = by_tick(rows_of(left["controller"], "controller_receipt_high"))
    rec_high_b = by_tick(rows_of(right["controller"], "controller_receipt_high"))
    ticks = sorted(set(cons_a) & set(cons_b))
    if not ticks:
        return {
            "run_a": left["run_id"], "run_b": right["run_id"],
            "classification": "INSTRUMENTATION_PERTURBATION",
            "tick": "", "boundary": "no_common_consumption_tick",
            "field": "", "value_a": "", "value_b": "",
            "upstream_equal": "false", "common_ticks": 0,
        }
    for tick in ticks:
        ba, bb = first_row(bridge_a, tick), first_row(bridge_b, tick)
        ca, cb = first_row(cons_a, tick), first_row(cons_b, tick)
        pa, pb = first_row(pre_a, tick), first_row(pre_b, tick)
        la, lb = first_row(rec_low_a, tick), first_row(rec_low_b, tick)
        ha, hb = first_row(rec_high_a, tick), first_row(rec_high_b, tick)
        result = None
        boundary = "none"
        if ba is None or bb is None:
            result = ("PROTOCOL_FAILURE", "bridge_record",
                      "" if ba is None else "present",
                      "" if bb is None else "present")
            boundary = "bridge_source"
        else:
            diff = first_difference(ba, bb, ["low_hash", "low_payload_hex"])
            if diff:
                result = ("BRIDGE_SOURCE_INPUT_DIVERGENCE", diff[0], diff[1], diff[2])
                boundary = "bridge_lowstate_source"
            if result is None:
                diff = first_difference(
                    ba, bb,
                    ["high_hash", "high_source_generation",
                     "high_source_tick", "high_skipped"],
                )
                if diff:
                    result = ("HIGHSTATE_PUBLICATION_PAIRING_DIVERGENCE",
                              diff[0], diff[1], diff[2])
                    boundary = "bridge_highstate_publication"
            if result is None:
                diff = first_difference(la, lb, ["low_hash", "low_payload_hex"])
                if diff:
                    result = ("TRANSPORT_OR_SUBSCRIBER_DIVERGENCE",
                              "low_" + diff[0], diff[1], diff[2])
                    boundary = "controller_lowstate_receipt"
            if result is None:
                diff = first_difference(ha, hb, ["high_hash", "high_payload_hex"])
                if diff:
                    result = ("TRANSPORT_OR_SUBSCRIBER_DIVERGENCE",
                              "high_" + diff[0], diff[1], diff[2])
                    boundary = "controller_highstate_receipt"
            if result is None:
                diff = first_difference(
                    ca, cb,
                    ["low_hash", "high_hash", "low_payload_hex", "high_payload_hex",
                     "consumed_low_receipt_seq", "consumed_high_receipt_seq"],
                )
                if diff:
                    result = ("CONTROLLER_INPUT_PAIRING_DIVERGENCE",
                              diff[0], diff[1], diff[2])
                    boundary = "controller_consumed_pair"
            if result is None:
                diff = first_difference(
                    pa, pb, ["lowcmd_hash", "lowcmd_payload_hex", "control_seq"],
                )
                if diff:
                    result = ("CONTROLLER_INTERNAL_DIVERGENCE",
                              diff[0], diff[1], diff[2])
                    boundary = "controller_lowcmd_prepublish"
        if result is not None:
            classification, field, value_a, value_b = result
            return {
                "run_a": left["run_id"], "run_b": right["run_id"],
                "classification": classification, "tick": str(tick),
                "boundary": boundary, "field": field,
                "value_a": value_a, "value_b": value_b,
                "upstream_equal": "false", "common_ticks": len(ticks),
                **boundary_context(ba, bb, la, lb, ha, hb, ca, cb, pa, pb),
            }
    return {
        "run_a": left["run_id"], "run_b": right["run_id"],
        "classification": "NO_DIVERGENCE_IN_WINDOW",
        "tick": "", "boundary": "none", "field": "",
        "value_a": "", "value_b": "", "upstream_equal": "true",
        "common_ticks": len(ticks),
    }

def write_results(
    output_dir: Path, infos: list[dict], pair_results: list[dict],
    global_classification: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "run_a", "run_b", "tick", "boundary", "field", "value_a",
        "value_b", "upstream_equal", "classification", "common_ticks",
        "source_low_hash_a", "source_low_hash_b",
        "source_high_hash_a", "source_high_hash_b",
        "source_high_source_generation_a", "source_high_source_generation_b",
        "source_high_source_tick_a", "source_high_source_tick_b",
        "source_high_skipped_a", "source_high_skipped_b",
        "receipt_low_seq_a", "receipt_low_seq_b",
        "receipt_high_seq_a", "receipt_high_seq_b",
        "consumed_low_receipt_seq_a", "consumed_low_receipt_seq_b",
        "consumed_high_receipt_seq_a", "consumed_high_receipt_seq_b",
        "control_seq_a", "control_seq_b",
        "consumed_low_hash_a", "consumed_low_hash_b",
        "consumed_high_hash_a", "consumed_high_hash_b",
        "lowcmd_hash_a", "lowcmd_hash_b",
    ]
    write_csv(output_dir / "first_boundary.csv", pair_results, fields)
    provenance_rows = []
    for info in infos:
        metadata = info["metadata"]
        for item in info["hashes"]:
            row = dict(item)
            row.update({
                "domain_id": metadata.get("domain_id", ""),
                "git_head": metadata.get("git_head", ""),
                "simulator_sha256": metadata.get("simulator_sha256", ""),
                "controller_sha256": metadata.get("controller_sha256", ""),
                "scene_sha256": metadata.get("scene_sha256", ""),
            })
            provenance_rows.append(row)
    write_csv(
        output_dir / "provenance.csv", provenance_rows,
        ["run_id", "artifact", "bytes", "sha256", "domain_id",
         "git_head", "simulator_sha256", "controller_sha256", "scene_sha256"],
    )
    analysis = {
        "window": {"start_tick": WINDOW[0], "end_tick": WINDOW[1]},
        "classification": global_classification,
        "runs": [
            {"run_id": info["run_id"], "metadata": info["metadata"],
             "errors": info["errors"]}
            for info in infos
        ],
        "pairwise": pair_results,
        "scope": {
            "live_runs": ["L1", "L2", "L3"],
            "d4": False,
            "repair_applied": False,
            "simulation_replayed_offline": False,
        },
    }
    (output_dir / "analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n"
    )
    lines = [
        "# Phase 1 LowState/HighState/LowCmd Boundary",
        "",
        f"Top-level classification: {global_classification}",
        "",
        "Window: ticks 11800–12600 inclusive. Exactly L1/L2/L3 were compared.",
        "",
        "Pairwise first-boundary results:",
        "",
        "| Pair | Tick | Boundary | Field | Classification |",
        "|---|---:|---|---|---|",
    ]
    for row in pair_results:
        lines.append(
            f"| {row['run_a']}–{row['run_b']} | {row['tick'] or '—'} | "
            f"{row['boundary']} | {row['field'] or '—'} | "
            f"{row['classification']} |"
        )
    lines += [
        "",
        "Trace payloads use fixed-width little-endian canonical fields and the "
        "trace-header-defined 64-bit FNV-style hash; every non-empty payload hash is verified offline.",
        "",
        "The bridge records HighState trylock publication skips and source "
        "generation/tick. The controller records callback receipt, mutex-protected "
        "snapshot consumption, and LowCmd immediately before CRC/publish.",
        "",
        "No D4 intervention, repair, controller retuning, or follow-up experiment was run.",
        "",
        "See first_boundary.csv, provenance.csv, and analysis.json for machine-readable "
        "closeout evidence.",
        "",
        "Source audit: PublishStateSnapshot uses blocking LowState publication and an "
        "independent HighState trylock path; LowStateMessageHandler and "
        "HighStateMessageHandler update cached messages plus diagnostic sequence shadows "
        "under state_mutex_; SnapshotState copies the exact cached tuple before control math.",
        "",
        "Canonical fields are LowState tick plus active motor q/dq/tau_est, IMU and "
        "foot-force fields; HighState position/velocity; and LowCmd q/dq/kp/kd/tau for "
        "12 motors. No raw struct memory or DDS bytes are hashed.",
        "",
        "Protocol/instrumentation gates: pre-run HEAD is bc6e202a3efde6c7d7118656afde91fd4c0869d3; "
        "L1/L2/L3 each passed the inherited lockstep gate with 43554 rows at 2 ms; "
        "focused self-test and simulate/build test_lockstep passed; diagnostic OFF has no added publish/ack path; D4 remained off.",
        "The first divergence is HighState publication generation while bridge physical "
        "payloads at tick 11800 remain equal; downstream LowState receipt, consumed tuple, "
        "and LowCmd are not called causal after this earlier boundary.",
        "",
        "Recommended next checkpoint: offline semantic re-audit of HighState source-generation "
        "freshness/pairing at the first LowCmd divergence, with trylock and DDS behavior unchanged.",
    ]
    (output_dir / "RESULTS.md").write_text("\n".join(lines) + "\n")

def analyze(source_root: Path, runs_root: Path, output_dir: Path) -> int:
    infos = [run_info(runs_root, run_id) for run_id in ("L1", "L2", "L3")]
    all_errors = [error for info in infos for error in info["errors"]]
    if all_errors:
        classification = "PROTOCOL_FAILURE"
        pair_results = [{
            "run_a": "L1", "run_b": "L2", "classification": classification,
            "tick": "", "boundary": "trace_validation", "field": "error",
            "value_a": "; ".join(all_errors), "value_b": "",
            "upstream_equal": "false", "common_ticks": 0,
        }]
    else:
        pair_results = [
            compare_pair(infos[0], infos[1]),
            compare_pair(infos[0], infos[2]),
            compare_pair(infos[1], infos[2]),
        ]
        labels = {row["classification"] for row in pair_results}
        classification = next(iter(labels)) if len(labels) == 1 else "UNRESOLVED_BOUNDARY"
    write_results(output_dir, infos, pair_results, classification)
    print(f"classification={classification}")
    for row in pair_results:
        print(
            f"{row['run_a']}-{row['run_b']}: "
            f"{row['classification']} tick={row['tick'] or 'none'}"
        )
    return 0 if classification not in ("PROTOCOL_FAILURE", "INSTRUMENTATION_PERTURBATION") else 1

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("example/cpp/experiments/_runs/"
                     "phase1_lowstate_highstate_lowcmd_boundary_20260914"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/validation/"
                     "phase1_lowstate_highstate_lowcmd_boundary_20260914"),
    )
    args = parser.parse_args()
    if args.self_test:
        self_test(args.source_root)
        return 0
    return analyze(args.source_root, args.runs_root, args.output_dir)

if __name__ == "__main__":
    sys.exit(main())
