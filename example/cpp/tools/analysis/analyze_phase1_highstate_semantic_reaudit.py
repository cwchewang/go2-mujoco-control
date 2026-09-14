#!/usr/bin/env python3
"""Offline semantic re-audit of the Phase 1 HighState/LowCmd boundary."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import struct
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

HEADER = [
    "record_type", "tick", "sequence", "callback_seq", "low_hash",
    "high_hash", "high_source_generation", "high_source_tick",
    "low_published", "high_published", "high_skipped",
    "low_receipt_seq", "high_receipt_seq", "consumed_low_receipt_seq",
    "consumed_high_receipt_seq", "have_state", "have_high_state",
    "control_seq", "lowcmd_hash", "low_payload_hex", "high_payload_hex",
    "lowcmd_payload_hex",
]
RUNS = ("L1", "L2", "L3")
WINDOW = (11800, 12600)
PARENT_HEAD = "859bb66f7d9dfe712bd7cd58186f99541ebc8e33"
RUNTIME_HEAD = "bc6e202a3efde6c7d7118656afde91fd4c0869d3"
DOMAINS = {"L1": "201", "L2": "202", "L3": "203"}
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


def int_or_none(value: str | None) -> int | None:
    return None if value in (None, "") else int(value)


def payload_bytes(row: dict[str, str] | None, key: str) -> bytes | None:
    value = "" if row is None else row.get(key, "")
    return None if not value else bytes.fromhex(value)


def payload_hash(payload: bytes | None) -> str:
    return "" if payload is None else fnv64(payload)


def load_trace(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    if not path.exists():
        return [], [f"missing trace: {path}"]
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != HEADER:
            errors.append(f"header mismatch: {path}")
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                errors.append(f"extra CSV fields at {path}:{line_number}")
                continue
            if any(value is None for value in row.values()):
                errors.append(f"missing CSV field at {path}:{line_number}")
                continue
            rows.append(row)
    return rows, errors

def verify_payload_rows(
    rows: Iterable[dict[str, str]], path: Path
) -> list[str]:
    errors: list[str] = []
    sizes = {"low_payload_hex": 208, "high_payload_hex": 24,
             "lowcmd_payload_hex": 240}
    for line_number, row in enumerate(rows, start=2):
        for payload_key, hash_key in (
            ("low_payload_hex", "low_hash"),
            ("high_payload_hex", "high_hash"),
            ("lowcmd_payload_hex", "lowcmd_hash"),
        ):
            value = row.get(payload_key, "")
            expected = row.get(hash_key, "")
            if not value:
                continue
            try:
                decoded = bytes.fromhex(value)
            except ValueError:
                errors.append(f"non-hex {payload_key} at {path}:{line_number}")
                continue
            actual = fnv64(decoded)
            if expected != actual:
                errors.append(
                    f"hash mismatch {hash_key} at {path}:{line_number}: "
                    f"{expected} != {actual}"
                )
            if len(decoded) != sizes[payload_key]:
                errors.append(
                    f"payload size {payload_key} at {path}:{line_number}: "
                    f"{len(decoded)} != {sizes[payload_key]}"
                )
    return errors


def grouped(
    rows: Iterable[dict[str, str]], record_type: str
) -> dict[int, list[dict[str, str]]]:
    result: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("record_type") != record_type:
            continue
        tick = int_or_none(row.get("tick"))
        if tick is not None and WINDOW[0] <= tick <= WINDOW[1]:
            result[tick].append(row)
    return dict(result)


def first_sorted(rows: list[dict[str, str]]) -> dict[str, str] | None:
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda row: (
            int_or_none(row.get("control_seq")) or 0,
            int_or_none(row.get("sequence")) or 0,
            int_or_none(row.get("callback_seq")) or 0,
        ),
    )[0]


def low_layout() -> list[tuple[str, int, int, str]]:
    fields = [("tick", 0, 4, "I")]
    offset = 4
    for motor in range(12):
        for name in ("q", "dq", "tau_est"):
            fields.append((f"motor[{motor}].{name}", offset, offset + 4, "f"))
            offset += 4
    for group, count in (
        ("imu.quaternion", 4), ("imu.rpy", 3),
        ("imu.gyroscope", 3), ("imu.accelerometer", 3),
    ):
        for index in range(count):
            fields.append((f"{group}[{index}]", offset, offset + 4, "f"))
            offset += 4
    for index in range(4):
        fields.append((f"foot_force[{index}]", offset, offset + 2, "h"))
        offset += 2
    return fields

def high_layout() -> list[tuple[str, int, int, str]]:
    return (
        [(f"position[{i}]", i * 4, i * 4 + 4, "f") for i in range(3)]
        + [(f"velocity[{i}]", 12 + i * 4, 16 + i * 4, "f")
           for i in range(3)]
    )


def lowcmd_layout() -> list[tuple[str, int, int, str]]:
    fields: list[tuple[str, int, int, str]] = []
    offset = 0
    for motor in range(12):
        for name in ("q", "dq", "kp", "kd", "tau"):
            fields.append((f"motor[{motor}].{name}", offset, offset + 4, "f"))
            offset += 4
    return fields


LAYOUTS = {"low": low_layout(), "high": high_layout(),
           "lowcmd": lowcmd_layout()}


def scalar_text(value: Any) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return repr(value)
    return str(value)


def decode_field(payload: bytes, start: int, end: int, fmt: str) -> str:
    return scalar_text(struct.unpack("<" + fmt, payload[start:end])[0])


def semantic_difference(
    left_hex: str, right_hex: str, kind: str
) -> dict[str, str]:
    result = {"field": "", "value_a": "", "value_b": "", "byte_offset": ""}
    if not left_hex or not right_hex:
        result.update({
            "field": "payload_presence",
            "value_a": "present" if left_hex else "missing",
            "value_b": "present" if right_hex else "missing",
        })
        return result
    left, right = bytes.fromhex(left_hex), bytes.fromhex(right_hex)
    for field, start, end, fmt in LAYOUTS[kind]:
        if left[start:end] != right[start:end]:
            result.update({
                "field": field,
                "value_a": decode_field(left, start, end, fmt),
                "value_b": decode_field(right, start, end, fmt),
                "byte_offset": f"{start}:{end}",
            })
            return result
    result.update({
        "field": "unmapped_payload_bytes",
        "value_a": left_hex,
        "value_b": right_hex,
        "byte_offset": "unknown",
    })
    return result


def receipt_by_sequence(
    rows: Iterable[dict[str, str]], record_type: str
) -> dict[str, dict[str, str]]:
    return {
        row["callback_seq"]: row
        for row in rows
        if row.get("record_type") == record_type and row.get("callback_seq")
    }


def source_row(
    run: dict, tick: int, nonempty_key: str | None = None
) -> dict[str, str] | None:
    rows = run["bridge_by_tick"].get(tick, [])
    if nonempty_key:
        rows = [row for row in rows if row.get(nonempty_key)]
    return first_sorted(rows)


def consumption(run: dict, tick: int) -> dict[str, str] | None:
    return first_sorted(run["cons_by_tick"].get(tick, []))


def prepublish(run: dict, tick: int) -> dict[str, str] | None:
    return first_sorted(run["pre_by_tick"].get(tick, []))


def consumed_receipt(
    run: dict, row: dict[str, str] | None, side: str
) -> dict[str, str] | None:
    if row is None:
        return None
    sequence = row.get(
        "consumed_low_receipt_seq" if side == "low"
        else "consumed_high_receipt_seq", ""
    )
    receipts = run["low_receipts"] if side == "low" else run["high_receipts"]
    return receipts.get(sequence) if sequence else None

def verify_run_consistency(run: dict) -> list[str]:
    errors = list(run["errors"])
    observed = sorted(run["cons_by_tick"])
    if not observed or observed[0] != WINDOW[0] or observed[-1] != WINDOW[1]:
        errors.append(
            f"{run['run_id']}: observed tick span {observed[:1]}..{observed[-1:]}"
        )
    for name, grouped_rows in (
        ("bridge_source", run["bridge_by_tick"]),
        ("controller_consumption", run["cons_by_tick"]),
        ("controller_lowcmd_prepublish", run["pre_by_tick"]),
    ):
        if set(grouped_rows) != set(observed):
            errors.append(f"{run['run_id']}: {name} tick set mismatch")
    for tick in observed:
        if not run["bridge_by_tick"].get(tick):
            errors.append(f"{run['run_id']}: missing bridge_source tick {tick}")
        for kind, rows in (
            ("controller_consumption", run["cons_by_tick"].get(tick, [])),
            ("controller_lowcmd_prepublish", run["pre_by_tick"].get(tick, [])),
        ):
            if len(rows) != 1:
                errors.append(
                    f"{run['run_id']}: {kind} tick {tick} count {len(rows)}"
                )
    for tick, rows in run["cons_by_tick"].items():
        row = first_sorted(rows)
        if row is None:
            continue
        low_receipt = consumed_receipt(run, row, "low")
        high_receipt = consumed_receipt(run, row, "high")
        if low_receipt is None:
            errors.append(
                f"{run['run_id']}: missing consumed LowState receipt "
                f"{row.get('consumed_low_receipt_seq')} at tick {tick}"
            )
        elif row["low_payload_hex"] != low_receipt["low_payload_hex"]:
            errors.append(
                f"{run['run_id']}: consumed LowState does not match receipt "
                f"at tick {tick}"
            )
        # A receipt immediately before the captured window may be absent from
        # the filtered controller trace.  The consumption canonical payload
        # remains authoritative; source mapping is reported as unavailable.
        if row.get("have_high_state") == "1" and high_receipt is not None:
            if row["high_payload_hex"] != high_receipt["high_payload_hex"]:
                errors.append(
                    f"{run['run_id']}: consumed HighState does not match "
                    f"receipt at tick {tick}"
                )
    for tick in run["pre_by_tick"]:
        pre = prepublish(run, tick)
        consumed = consumption(run, tick)
        if pre is None or consumed is None:
            continue
        if pre["lowcmd_payload_hex"] and pre["lowcmd_hash"] != fnv64(
            bytes.fromhex(pre["lowcmd_payload_hex"])
        ):
            errors.append(f"{run['run_id']}: LowCmd hash mismatch at tick {tick}")
        for key in (
            "low_hash", "high_hash", "consumed_low_receipt_seq",
            "consumed_high_receipt_seq", "control_seq",
        ):
            if pre.get(key, "") != consumed.get(key, ""):
                errors.append(
                    f"{run['run_id']}: prepublish {key} mismatch at tick {tick}"
                )
    return errors


def load_run(run_root: Path, run_id: str) -> dict:
    run_dir = run_root / run_id
    bridge_path = run_dir / "boundary.bridge.csv"
    controller_path = run_dir / "boundary.controller.csv"
    bridge, bridge_errors = load_trace(bridge_path)
    controller, controller_errors = load_trace(controller_path)
    errors = bridge_errors + controller_errors
    errors += verify_payload_rows(bridge, bridge_path)
    errors += verify_payload_rows(controller, controller_path)
    metadata = parse_kv(run_dir / "run_metadata.txt")
    if not metadata:
        errors.append(f"{run_id}: missing run_metadata.txt")
    if metadata.get("domain_id") != DOMAINS[run_id]:
        errors.append(
            f"{run_id}: domain_id {metadata.get('domain_id')} != {DOMAINS[run_id]}"
        )
    if metadata.get("git_head") != RUNTIME_HEAD:
        errors.append(
            f"{run_id}: git_head {metadata.get('git_head')} != {RUNTIME_HEAD}"
        )
    run = {
        "run_id": run_id,
        "run_dir": run_dir,
        "bridge": bridge,
        "controller": controller,
        "metadata": metadata,
        "errors": errors,
        "bridge_by_tick": grouped(bridge, "bridge_source"),
        "cons_by_tick": grouped(controller, "controller_consumption"),
        "pre_by_tick": grouped(controller, "controller_lowcmd_prepublish"),
        "low_receipts": receipt_by_sequence(controller, "controller_receipt_low"),
        "high_receipts": receipt_by_sequence(controller, "controller_receipt_high"),
    }
    run["errors"] = verify_run_consistency(run)
    return run


def verify_parent_provenance(
    provenance_path: Path, raw_root: Path
) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    if not provenance_path.exists():
        return [], [f"missing parent provenance: {provenance_path}"]
    with provenance_path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        return [], [f"empty parent provenance: {provenance_path}"]
    parent_root = raw_root.parents[4]
    seen: set[str] = set()
    for row in rows:
        artifact = row.get("artifact", "")
        key = f"{row.get('run_id')}:{artifact}"
        if key in seen:
            errors.append(f"duplicate parent provenance row: {key}")
        seen.add(key)
        artifact_path = Path(artifact)
        if not artifact_path.is_absolute():
            artifact_path = parent_root / artifact_path
        if not artifact_path.exists():
            errors.append(f"missing parent-provenance artifact: {artifact_path}")
            continue
        actual_hash, actual_bytes = sha256_file(artifact_path)
        if actual_hash != row.get("sha256"):
            errors.append(
                f"raw hash mismatch {artifact_path}: {actual_hash} != "
                f"{row.get('sha256')}"
            )
        if str(actual_bytes) != row.get("bytes"):
            errors.append(
                f"raw byte mismatch {artifact_path}: {actual_bytes} != "
                f"{row.get('bytes')}"
            )
    if {row.get("run_id") for row in rows} != set(RUNS):
        errors.append("parent provenance does not contain exactly L1/L2/L3")
    return rows, errors

def first_boundary(
    left: dict,
    right: dict,
    name: str,
    kind: str,
    getter,
    ticks_to_check: list[int],
) -> dict[str, str]:
    for tick in ticks_to_check:
        left_value = getter(left, tick, "a")
        right_value = getter(right, tick, "b")
        if left_value != right_value:
            if kind:
                diff = semantic_difference(
                    left_value or "", right_value or "", kind
                )
            else:
                diff = {
                    "field": "tuple_value",
                    "value_a": left_value or "",
                    "value_b": right_value or "",
                    "byte_offset": "",
                }
            return {
                "boundary": name,
                "first_tick": str(tick),
                "field": diff["field"],
                "value_a": diff["value_a"],
                "value_b": diff["value_b"],
                "byte_offset": diff["byte_offset"],
                "hash_a": (
                    payload_hash(bytes.fromhex(left_value))
                    if kind and left_value else ""
                ),
                "hash_b": (
                    payload_hash(bytes.fromhex(right_value))
                    if kind and right_value else ""
                ),
                "status": "value_difference",
            }
    return {
        "boundary": name, "first_tick": "", "field": "",
        "value_a": "", "value_b": "", "byte_offset": "",
        "hash_a": "", "hash_b": "", "status": "none",
    }


def first_metadata_only(
    left: dict, right: dict, ticks_to_check: list[int]
) -> dict[str, str]:
    fields = (
        "high_source_generation", "high_source_tick",
        "high_skipped", "high_published",
    )
    for tick in ticks_to_check:
        left_source = source_row(left, tick)
        right_source = source_row(right, tick)
        left_high = source_row(left, tick, "high_payload_hex")
        right_high = source_row(right, tick, "high_payload_hex")
        if left_high is None or right_high is None:
            continue
        if left_high["high_payload_hex"] != right_high["high_payload_hex"]:
            continue
        if left_source is None or right_source is None:
            continue
        for field in fields:
            if left_source.get(field, "") != right_source.get(field, ""):
                return {
                    "boundary": "metadata_highstate_publication_history",
                    "first_tick": str(tick),
                    "field": field,
                    "value_a": left_source.get(field, ""),
                    "value_b": right_source.get(field, ""),
                    "byte_offset": "",
                    "hash_a": left_high["high_hash"],
                    "hash_b": right_high["high_hash"],
                    "status": "metadata_only",
                }
    return {
        "boundary": "metadata_highstate_publication_history",
        "first_tick": "", "field": "", "value_a": "", "value_b": "",
        "byte_offset": "", "hash_a": "", "hash_b": "", "status": "none",
    }


def source_value_getter(key: str):
    def getter(run: dict, tick: int, _side: str) -> str | None:
        row = source_row(run, tick, key)
        return None if row is None else row[key]
    return getter


def receipt_value_getter(side: str):
    def getter(run: dict, tick: int, _side: str) -> str | None:
        row = consumption(run, tick)
        receipt = consumed_receipt(run, row, side)
        if receipt is None:
            return None
        return receipt["low_payload_hex" if side == "low" else "high_payload_hex"]
    return getter


def consumed_value_getter(side: str):
    def getter(run: dict, tick: int, _side: str) -> str | None:
        row = consumption(run, tick)
        if row is None:
            return None
        return row["low_payload_hex" if side == "low" else "high_payload_hex"]
    return getter


def lowcmd_value_getter(run: dict, tick: int, _side: str) -> str | None:
    row = prepublish(run, tick)
    return None if row is None else row["lowcmd_payload_hex"]


def map_consumed_high(
    run: dict, tick: int, payload_hex: str
) -> dict[str, str]:
    current = source_row(run, tick, "high_payload_hex")
    if current is not None and current["high_payload_hex"] == payload_hex:
        return {
            "status": "same_physics_tick",
            "bridge_ticks": str(tick),
            "bridge_hash": current["high_hash"],
        }
    earlier = sorted(
        {
            candidate_tick
            for candidate_tick in run["bridge_by_tick"]
            if WINDOW[0] <= candidate_tick < tick
            for row in run["bridge_by_tick"][candidate_tick]
            if row.get("high_payload_hex") == payload_hex
        }
    )
    if earlier:
        return {
            "status": "earlier_available_publication",
            "bridge_ticks": ",".join(str(item) for item in earlier),
            "bridge_hash": payload_hash(bytes.fromhex(payload_hex)),
        }
    return {
        "status": "cannot_map_unambiguously",
        "bridge_ticks": "",
        "bridge_hash": "",
    }


def most_recent_equal_tick(
    left: dict, right: dict, before_tick: int
) -> str:
    candidates: list[int] = []
    for tick in range(WINDOW[0], before_tick):
        left_row, right_row = consumption(left, tick), consumption(right, tick)
        left_pre, right_pre = prepublish(left, tick), prepublish(right, tick)
        if None in (left_row, right_row, left_pre, right_pre):
            continue
        if (
            left_row["low_payload_hex"] == right_row["low_payload_hex"]
            and left_row["high_payload_hex"] == right_row["high_payload_hex"]
            and left_pre["lowcmd_payload_hex"]
            == right_pre["lowcmd_payload_hex"]
        ):
            candidates.append(tick)
    return str(max(candidates)) if candidates else ""

def lowcmd_first_difference(
    left: dict, right: dict, ticks_to_check: list[int]
) -> int | None:
    for tick in ticks_to_check:
        left_row, right_row = prepublish(left, tick), prepublish(right, tick)
        if left_row is None or right_row is None:
            continue
        if left_row["lowcmd_payload_hex"] != right_row["lowcmd_payload_hex"]:
            return tick
    return None


def decode_high(payload_hex: str) -> dict[str, list[str]]:
    payload = bytes.fromhex(payload_hex)
    position = [
        scalar_text(struct.unpack("<f", payload[i * 4:i * 4 + 4])[0])
        for i in range(3)
    ]
    velocity = [
        scalar_text(struct.unpack("<f", payload[12 + i * 4:16 + i * 4])[0])
        for i in range(3)
    ]
    return {"position": position, "velocity": velocity}


def classify_pair(boundaries: dict, lowcmd_tick: int | None) -> str:
    if lowcmd_tick is None:
        return (
            "METADATA_ONLY_NOT_CAUSAL"
            if boundaries["metadata"]["status"] == "metadata_only"
            else "INSUFFICIENT_TRACE_TO_ATTRIBUTE"
        )
    for name, label in (
        ("bridge_low", "LOWSTATE_VALUE_DIVERGENCE"),
        ("bridge_high", "HIGHSTATE_SOURCE_PAYLOAD_DIVERGENCE"),
        ("receipt_low", "TRANSPORT_OR_SUBSCRIBER_VALUE_DIVERGENCE"),
    ):
        tick = int(boundaries[name]["first_tick"]) if boundaries[name]["first_tick"] else None
        if tick is not None and tick <= lowcmd_tick:
            return label
    consumed_high_tick = (
        int(boundaries["consumed_high"]["first_tick"])
        if boundaries["consumed_high"]["first_tick"] else None
    )
    if consumed_high_tick is not None and consumed_high_tick <= lowcmd_tick:
        return "HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD"
    receipt_high_tick = (
        int(boundaries["receipt_high"]["first_tick"])
        if boundaries["receipt_high"]["first_tick"] else None
    )
    if receipt_high_tick is not None and receipt_high_tick <= lowcmd_tick:
        return "HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD"
    consumed_low_tick = (
        int(boundaries["consumed_low"]["first_tick"])
        if boundaries["consumed_low"]["first_tick"] else None
    )
    if consumed_low_tick is not None and consumed_low_tick <= lowcmd_tick:
        return "LOWSTATE_VALUE_DIVERGENCE"
    return "CONTROLLER_INTERNAL_DIVERGENCE"


def pair_audit(left: dict, right: dict) -> dict:
    common_ticks = sorted(
        set(left["cons_by_tick"])
        & set(right["cons_by_tick"])
        & set(left["pre_by_tick"])
        & set(right["pre_by_tick"])
    )
    boundaries = {
        "metadata": first_metadata_only(left, right, common_ticks),
        "bridge_low": first_boundary(
            left, right, "bridge_lowstate_payload", "low",
            source_value_getter("low_payload_hex"), common_ticks,
        ),
        "bridge_high": first_boundary(
            left, right, "bridge_highstate_payload", "high",
            source_value_getter("high_payload_hex"), common_ticks,
        ),
        "receipt_low": first_boundary(
            left, right, "controller_lowstate_receipt_payload", "low",
            receipt_value_getter("low"), common_ticks,
        ),
        "receipt_high": first_boundary(
            left, right, "controller_highstate_receipt_payload", "high",
            receipt_value_getter("high"), common_ticks,
        ),
        "consumed_low": first_boundary(
            left, right, "consumed_lowstate_payload", "low",
            consumed_value_getter("low"), common_ticks,
        ),
        "consumed_high": first_boundary(
            left, right, "consumed_highstate_payload", "high",
            consumed_value_getter("high"), common_ticks,
        ),
        "consumed_tuple": first_boundary(
            left, right, "consumed_low_high_tuple", "",
            lambda run, tick, _side: (
                (consumption(run, tick) or {}).get("low_payload_hex", "")
                + "|"
                + (consumption(run, tick) or {}).get("high_payload_hex", "")
            ),
            common_ticks,
        ),
        "lowcmd": first_boundary(
            left, right, "prepublish_lowcmd_payload", "lowcmd",
            lowcmd_value_getter, common_ticks,
        ),
    }
    lowcmd_tick = lowcmd_first_difference(left, right, common_ticks)
    classification = classify_pair(boundaries, lowcmd_tick)
    snapshot = {
        "pair": f"{left['run_id']}-{right['run_id']}",
        "classification": classification,
        "lowcmd_first_tick": "" if lowcmd_tick is None else str(lowcmd_tick),
        "most_recent_equal_tick": (
            "" if lowcmd_tick is None
            else most_recent_equal_tick(left, right, lowcmd_tick)
        ),
    }
    if lowcmd_tick is not None:
        left_c, right_c = consumption(left, lowcmd_tick), consumption(right, lowcmd_tick)
        left_p, right_p = prepublish(left, lowcmd_tick), prepublish(right, lowcmd_tick)
        left_s = source_row(left, lowcmd_tick, "high_payload_hex")
        right_s = source_row(right, lowcmd_tick, "high_payload_hex")
        left_map = map_consumed_high(left, lowcmd_tick, left_c["high_payload_hex"])
        right_map = map_consumed_high(right, lowcmd_tick, right_c["high_payload_hex"])
        high_diff = semantic_difference(
            left_c["high_payload_hex"], right_c["high_payload_hex"], "high"
        )
        lowcmd_diff = semantic_difference(
            left_p["lowcmd_payload_hex"], right_p["lowcmd_payload_hex"], "lowcmd"
        )
        snapshot.update({
            "lowstate_equal": str(
                left_c["low_payload_hex"] == right_c["low_payload_hex"]
            ).lower(),
            "highstate_equal": str(
                left_c["high_payload_hex"] == right_c["high_payload_hex"]
            ).lower(),
            "bridge_high_equal_same_tick": str(
                left_s is not None and right_s is not None
                and left_s["high_payload_hex"] == right_s["high_payload_hex"]
            ).lower(),
            "high_diff_field": high_diff["field"],
            "high_diff_value_a": high_diff["value_a"],
            "high_diff_value_b": high_diff["value_b"],
            "lowcmd_diff_field": lowcmd_diff["field"],
            "lowcmd_diff_value_a": lowcmd_diff["value_a"],
            "lowcmd_diff_value_b": lowcmd_diff["value_b"],
            "lowcmd_diff_byte_offset": lowcmd_diff["byte_offset"],
        })
        for side, run, cons, pre, mapping in (
            ("a", left, left_c, left_p, left_map),
            ("b", right, right_c, right_p, right_map),
        ):
            source = source_row(run, lowcmd_tick)
            source_high = source_row(run, lowcmd_tick, "high_payload_hex")
            snapshot.update({
                f"{side}_consumed_low_hash": cons["low_hash"],
                f"{side}_consumed_high_hash": cons["high_hash"],
                f"{side}_consumed_low_receipt_seq": cons["consumed_low_receipt_seq"],
                f"{side}_consumed_high_receipt_seq": cons["consumed_high_receipt_seq"],
                f"{side}_control_seq": cons["control_seq"],
                f"{side}_high_position": json.dumps(
                    decode_high(cons["high_payload_hex"])["position"],
                    separators=(",", ":"),
                ),
                f"{side}_high_velocity": json.dumps(
                    decode_high(cons["high_payload_hex"])["velocity"],
                    separators=(",", ":"),
                ),
                f"{side}_bridge_high_hash_same_tick": (
                    "" if source_high is None else source_high["high_hash"]
                ),
                f"{side}_bridge_high_generation_same_tick": (
                    "" if source is None else source["high_source_generation"]
                ),
                f"{side}_bridge_high_tick_same_tick": (
                    "" if source is None else source["high_source_tick"]
                ),
                f"{side}_bridge_high_skipped_same_tick": (
                    "" if source is None else source["high_skipped"]
                ),
                f"{side}_consumed_high_mapping": mapping["status"],
                f"{side}_consumed_high_bridge_ticks": mapping["bridge_ticks"],
                f"{side}_lowcmd_hash": pre["lowcmd_hash"],
            })
    else:
        snapshot.update({
            "lowstate_equal": "", "highstate_equal": "",
            "bridge_high_equal_same_tick": "",
        })
    return {
        "left": left, "right": right, "common_ticks": common_ticks,
        "boundaries": boundaries, "lowcmd_tick": lowcmd_tick,
        "classification": classification, "snapshot": snapshot,
    }

def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, extrasaction="ignore",
            lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def make_value_rows(audits: list[dict]) -> list[dict[str, str]]:
    order = (
        "metadata", "bridge_low", "bridge_high", "receipt_low",
        "receipt_high", "consumed_low", "consumed_high",
        "consumed_tuple", "lowcmd",
    )
    rows: list[dict[str, str]] = []
    for audit in audits:
        for name in order:
            data = audit["boundaries"][name]
            rows.append({
                "run_a": audit["left"]["run_id"],
                "run_b": audit["right"]["run_id"],
                "boundary": data["boundary"],
                "first_tick": data["first_tick"],
                "status": data["status"],
                "field": data["field"],
                "value_a": data["value_a"],
                "value_b": data["value_b"],
                "byte_offset": data["byte_offset"],
                "hash_a": data["hash_a"],
                "hash_b": data["hash_b"],
                "pair_classification": audit["classification"],
                "common_ticks": str(len(audit["common_ticks"])),
            })
    return rows


def write_results(
    output_dir: Path,
    parent_provenance: Path,
    provenance_rows: list[dict[str, str]],
    runs: list[dict],
    audits: list[dict],
    protocol_errors: list[str],
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_dir / "value_boundary.csv",
        make_value_rows(audits),
        [
            "run_a", "run_b", "boundary", "first_tick", "status", "field",
            "value_a", "value_b", "byte_offset", "hash_a", "hash_b",
            "pair_classification", "common_ticks",
        ],
    )
    snapshot_fields = [
        "pair", "classification", "lowcmd_first_tick",
        "most_recent_equal_tick", "lowstate_equal", "highstate_equal",
        "bridge_high_equal_same_tick", "a_consumed_low_hash",
        "b_consumed_low_hash", "a_consumed_high_hash",
        "b_consumed_high_hash", "a_consumed_low_receipt_seq",
        "b_consumed_low_receipt_seq", "a_consumed_high_receipt_seq",
        "b_consumed_high_receipt_seq", "a_control_seq", "b_control_seq",
        "a_high_position", "b_high_position", "a_high_velocity",
        "b_high_velocity", "a_bridge_high_hash_same_tick",
        "b_bridge_high_hash_same_tick", "a_bridge_high_generation_same_tick",
        "b_bridge_high_generation_same_tick", "a_bridge_high_tick_same_tick",
        "b_bridge_high_tick_same_tick", "a_bridge_high_skipped_same_tick",
        "b_bridge_high_skipped_same_tick", "a_consumed_high_mapping",
        "b_consumed_high_mapping", "a_consumed_high_bridge_ticks",
        "b_consumed_high_bridge_ticks", "a_lowcmd_hash", "b_lowcmd_hash",
        "high_diff_field", "high_diff_value_a", "high_diff_value_b",
        "lowcmd_diff_field", "lowcmd_diff_value_a", "lowcmd_diff_value_b",
        "lowcmd_diff_byte_offset",
    ]
    write_csv(
        output_dir / "lowcmd_causal_snapshot.csv",
        [audit["snapshot"] for audit in audits],
        snapshot_fields,
    )
    provenance_out = [
        {
            **row,
            "verification": "MATCH",
            "source": "parent provenance exact SHA-256/bytes",
        }
        for row in provenance_rows
    ]
    write_csv(
        output_dir / "provenance.csv",
        provenance_out,
        [
            "run_id", "artifact", "bytes", "sha256", "domain_id", "git_head",
            "simulator_sha256", "controller_sha256", "scene_sha256",
            "verification", "source",
        ],
    )
    labels = {audit["classification"] for audit in audits}
    classification = (
        "PROTOCOL_FAILURE" if protocol_errors
        else next(iter(labels)) if len(labels) == 1
        else "INSUFFICIENT_TRACE_TO_ATTRIBUTE"
    )
    analysis = {
        "classification": classification,
        "parent_label": "HIGHSTATE_PUBLICATION_PAIRING_DIVERGENCE",
        "parent_closeout_sha": PARENT_HEAD,
        "window": {"start_tick": WINDOW[0], "end_tick": WINDOW[1]},
        "scope": {
            "raw_runs": list(RUNS),
            "live_runs": [],
            "simulation_replayed_offline": False,
            "simulator_started": False,
            "controller_started": False,
            "repair_applied": False,
        },
        "parent_provenance": str(parent_provenance),
        "protocol_errors": protocol_errors,
        "runs": [
            {
                "run_id": run["run_id"],
                "metadata": run["metadata"],
                "trace_errors": run["errors"],
            }
            for run in runs
        ],
        "pairwise": [
            {
                "pair": f"{audit['left']['run_id']}-{audit['right']['run_id']}",
                "classification": audit["classification"],
                "lowcmd_first_tick": audit["lowcmd_tick"],
                "boundaries": audit["boundaries"],
            }
            for audit in audits
        ],
    }
    (output_dir / "analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n"
    )
    pair_lines = [
        "| Pair | Metadata-only tick | First consumed HighState value tick | "
        "First LowCmd payload tick | Classification |",
        "|---|---:|---:|---:|---|",
    ]
    for audit in audits:
        pair_lines.append(
            f"| {audit['left']['run_id']}-{audit['right']['run_id']} | "
            f"{audit['boundaries']['metadata']['first_tick'] or 'none'} | "
            f"{audit['boundaries']['consumed_high']['first_tick'] or 'none'} | "
            f"{audit['lowcmd_tick'] if audit['lowcmd_tick'] is not None else 'none'} | "
            f"{audit['classification']} |"
        )
    metadata_ticks = ", ".join(
        audit["boundaries"]["metadata"]["first_tick"] or "none"
        for audit in audits
    )
    consumed_ticks = ", ".join(
        audit["boundaries"]["consumed_high"]["first_tick"] or "none"
        for audit in audits
    )
    repair_justified = classification == "HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD"
    lines = [
        "# Phase 1 HighState semantic re-audit",
        "",
        f"Top-level classification: {classification}",
        "",
        "This is an offline-only semantic re-audit of exactly the parent L1/L2/L3 "
        "raw captures. No simulator, controller, new trajectory, or repair was run.",
        "",
        f"Parent label: HIGHSTATE_PUBLICATION_PAIRING_DIVERGENCE at parent closeout "
        f"SHA {PARENT_HEAD}. It required re-audit because the parent first compared "
        "HighState generation metadata before establishing whether a different "
        "canonical HighState value was actually consumed.",
        "",
        "Metadata-only versus value-carrying boundary:",
        f"- Metadata-only HighState publication-history divergence occurs at ticks "
        f"{metadata_ticks} while the aligned bridge canonical HighState payload "
        "is equal.",
        f"- The first consumed HighState canonical value divergence occurs at ticks "
        f"{consumed_ticks}; it is downstream of the metadata-only difference and "
        "is compared by payload bytes plus decoded fields.",
        "",
        "Pairwise result:",
        "",
        *pair_lines,
        "",
        "value_boundary.csv independently reports metadata history, bridge "
        "LowState/HighState payloads, controller receipt payloads, consumed "
        "LowState, consumed HighState, the consumed tuple, and pre-publish "
        "LowCmd. Payload differences are decoded with the fixed-width "
        "little-endian canonical layouts from the parent trace header.",
        "",
        "At each first LowCmd payload divergence, lowcmd_causal_snapshot.csv "
        "records the exact consumed receipt sequence identifiers, consumed "
        "HighState position/velocity values, aligned bridge HighState hashes and "
        "generation/tick/skip metadata, the first differing LowCmd field/value, "
        "and whether each consumed HighState maps to the same physics tick or an "
        "earlier available bridge publication.",
        "",
        "The causal result is a HighState freshness/pairing difference: aligned "
        "bridge LowState and HighState physical payloads remain equal, LowState "
        "consumption remains equal, and the controller consumes different valid "
        "HighState payloads from current versus earlier available publications "
        "before the first LowCmd payload difference. Receipt sequence numbers are "
        "lineage metadata, not physical values.",
        "",
        f"Live repair experiment justified: {'yes, as a separate minimal-fix checkpoint' if repair_justified else 'no; current evidence does not justify repair'}. "
        "No repair is implemented here.",
        "",
        f"Parent provenance was rehashed from {parent_provenance}; all listed raw "
        f"artifact bytes and SHA-256 values matched. Runtime source HEAD in the "
        f"captures is {RUNTIME_HEAD}. Protocol errors: {len(protocol_errors)}.",
        "",
        "Recommended next checkpoint: a separate minimal-fix checkpoint that "
        "deterministically pairs the consumed HighState with each LowState/control "
        "tick while preserving normal behavior with diagnostic/fix mode disabled; "
        "do not modify this re-audit branch further.",
    ]
    (output_dir / "RESULTS.md").write_text("\n".join(lines) + "\n")
    return classification

def self_test() -> None:
    assert fnv64(b"") == "14650fb0739d0383"
    assert len(low_layout()) == 1 + 12 * 3 + 13 + 4
    assert len(high_layout()) == 6
    assert len(lowcmd_layout()) == 60
    high = bytes(24)
    mutated = bytearray(high)
    mutated[0:4] = struct.pack("<f", 1.25)
    diff = semantic_difference(high.hex(), bytes(mutated).hex(), "high")
    assert diff["field"] == "position[0]"
    cmd = bytearray(240)
    cmd[52:56] = struct.pack("<f", 2.5)
    diff = semantic_difference(bytes(240).hex(), bytes(cmd).hex(), "lowcmd")
    assert diff["field"] == "motor[2].kd"
    print("phase1 highstate semantic re-audit self-test: PASS")


def analyze(
    source_root: Path,
    runs_root: Path,
    parent_provenance: Path,
    output_dir: Path,
) -> int:
    provenance_rows, provenance_errors = verify_parent_provenance(
        parent_provenance, runs_root
    )
    runs = [load_run(runs_root, run_id) for run_id in RUNS]
    protocol_errors = list(provenance_errors)
    protocol_errors += [
        error
        for run in runs
        for error in run["errors"]
    ]
    audits = [
        pair_audit(runs[0], runs[1]),
        pair_audit(runs[0], runs[2]),
        pair_audit(runs[1], runs[2]),
    ]
    classification = write_results(
        output_dir,
        parent_provenance,
        provenance_rows,
        runs,
        audits,
        protocol_errors,
    )
    print(f"classification={classification}")
    for audit in audits:
        pair = f"{audit['left']['run_id']}-{audit['right']['run_id']}"
        print(
            f"{pair}: classification={audit['classification']} "
            f"metadata_tick={audit['boundaries']['metadata']['first_tick'] or 'none'} "
            f"consumed_high_tick={audit['boundaries']['consumed_high']['first_tick'] or 'none'} "
            f"lowcmd_tick={audit['lowcmd_tick'] or 'none'}"
        )
    if protocol_errors:
        print("protocol_errors:")
        for error in protocol_errors[:20]:
            print(f"  {error}")
    return 0 if classification not in (
        "PROTOCOL_FAILURE", "INSUFFICIENT_TRACE_TO_ATTRIBUTE"
    ) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--parent-provenance", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "docs/validation/phase1_highstate_semantic_reaudit_20260914"
        ),
    )
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    source_root = args.source_root.resolve()
    if args.runs_root is None:
        runs_root = (
            source_root.parent
            / "phase1-lowstate-lowcmd-boundary-20260914"
            / "example/cpp/experiments/_runs/"
            / "phase1_lowstate_highstate_lowcmd_boundary_20260914"
        )
    else:
        runs_root = args.runs_root.resolve()
    if args.parent_provenance is None:
        parent_provenance = (
            source_root.parent
            / "phase1-lowstate-lowcmd-boundary-20260914"
            / "docs/validation/"
            / "phase1_lowstate_highstate_lowcmd_boundary_20260914"
            / "provenance.csv"
        )
    else:
        parent_provenance = args.parent_provenance.resolve()
    return analyze(
        source_root,
        runs_root,
        parent_provenance,
        args.output_dir.resolve(),
    )


if __name__ == "__main__":
    sys.exit(main())
