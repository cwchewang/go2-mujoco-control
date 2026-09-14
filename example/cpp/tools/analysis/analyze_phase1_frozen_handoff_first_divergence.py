#!/usr/bin/env python3
"""Compare GO2PDSNP v2 captures and locate the first exact divergence.

This tool is intentionally offline-only. It does not modify raw captures and uses
byte equality as the primary identity test. It understands the snapshot format
written by CounterfactualSnapshotLogger in simulate/src/main.cc at the
phase1 frozen-ready handoff checkpoint.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import math
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, List, Sequence, Tuple

MAGIC = b"GO2PDSNP"
VERSION = 2
MOTOR_COUNT = 12
DOUBLE = struct.Struct("<d")
U32 = struct.Struct("<I")
I32 = struct.Struct("<i")
U64 = struct.Struct("<Q")
I64 = struct.Struct("<q")


class FormatError(RuntimeError):
    pass


def read_exact(f: BinaryIO, n: int) -> bytes:
    data = f.read(n)
    if len(data) != n:
        raise EOFError
    return data


def unpack_one(fmt: struct.Struct, f: BinaryIO):
    return fmt.unpack(read_exact(f, fmt.size))[0]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class Header:
    version: int
    mujoco_version: int
    mjtnum_size: int
    state_sig: int
    state_size: int
    nq: int
    nv: int
    na: int
    nu: int
    start_time_s: float
    end_time_s: float
    timestep_s: float


@dataclass
class Record:
    record_index: int
    time_ms: int
    time_s: float
    qvel0: float
    qacc0_after: float
    ncon: int
    nefc: int
    contact_mask: int
    state_raw: bytes
    bridge_ctrl_seq: int
    motor_count: int
    bridge_sim_time_s: float
    q_raw: bytes
    dq_raw: bytes
    kp_raw: bytes
    kd_raw: bytes
    tau_ff_raw: bytes
    sensor_q_raw: bytes
    sensor_dq_raw: bytes
    bridge_ctrl_raw: bytes
    actual_ctrl_raw: bytes
    bridge_seq_step_index: int

    @property
    def lowcmd_raw(self) -> bytes:
        return self.q_raw + self.dq_raw + self.kp_raw + self.kd_raw + self.tau_ff_raw

    @property
    def bridge_sensor_raw(self) -> bytes:
        return self.sensor_q_raw + self.sensor_dq_raw


@dataclass
class Capture:
    path: Path
    file_sha256: str
    header: Header
    records: List[Record]


def read_header(f: BinaryIO) -> Header:
    if read_exact(f, 8) != MAGIC:
        raise FormatError("bad magic; expected GO2PDSNP")
    version = unpack_one(U32, f)
    if version != VERSION:
        raise FormatError(f"unsupported snapshot version {version}; expected {VERSION}")
    mujoco_version = unpack_one(U32, f)
    mjtnum_size = unpack_one(U32, f)
    state_sig = unpack_one(U32, f)
    state_size = unpack_one(U32, f)
    nq = unpack_one(U32, f)
    nv = unpack_one(U32, f)
    na = unpack_one(U32, f)
    nu = unpack_one(U32, f)
    start_time_s = unpack_one(DOUBLE, f)
    end_time_s = unpack_one(DOUBLE, f)
    timestep_s = unpack_one(DOUBLE, f)
    if mjtnum_size not in (4, 8):
        raise FormatError(f"unexpected mjtNum size: {mjtnum_size}")
    if state_size <= 0:
        raise FormatError(f"invalid state size: {state_size}")
    return Header(
        version, mujoco_version, mjtnum_size, state_sig, state_size,
        nq, nv, na, nu, start_time_s, end_time_s, timestep_s,
    )


def read_array_raw(f: BinaryIO, count: int) -> bytes:
    return read_exact(f, count * DOUBLE.size)


def read_record(f: BinaryIO, h: Header) -> Record:
    record_index = unpack_one(U64, f)
    time_ms = unpack_one(I64, f)
    time_s = unpack_one(DOUBLE, f)
    qvel0 = unpack_one(DOUBLE, f)
    qacc0_after = unpack_one(DOUBLE, f)
    ncon = unpack_one(I32, f)
    nefc = unpack_one(I32, f)
    contact_mask = unpack_one(I32, f)
    record_state_size = unpack_one(U32, f)
    if record_state_size != h.state_size:
        raise FormatError(
            f"record {record_index}: state_size={record_state_size}, header={h.state_size}"
        )
    state_raw = read_exact(f, h.state_size * h.mjtnum_size)
    bridge_ctrl_seq = unpack_one(U64, f)
    motor_count = unpack_one(U32, f)
    bridge_sim_time_s = unpack_one(DOUBLE, f)
    q_raw = read_array_raw(f, MOTOR_COUNT)
    dq_raw = read_array_raw(f, MOTOR_COUNT)
    kp_raw = read_array_raw(f, MOTOR_COUNT)
    kd_raw = read_array_raw(f, MOTOR_COUNT)
    tau_ff_raw = read_array_raw(f, MOTOR_COUNT)
    sensor_q_raw = read_array_raw(f, MOTOR_COUNT)
    sensor_dq_raw = read_array_raw(f, MOTOR_COUNT)
    bridge_ctrl_raw = read_array_raw(f, MOTOR_COUNT)
    actual_ctrl_raw = read_array_raw(f, MOTOR_COUNT)
    bridge_seq_step_index = unpack_one(U32, f)
    return Record(
        record_index, time_ms, time_s, qvel0, qacc0_after,
        ncon, nefc, contact_mask, state_raw, bridge_ctrl_seq,
        motor_count, bridge_sim_time_s, q_raw, dq_raw, kp_raw, kd_raw,
        tau_ff_raw, sensor_q_raw, sensor_dq_raw, bridge_ctrl_raw,
        actual_ctrl_raw, bridge_seq_step_index,
    )


def load_capture(path: Path) -> Capture:
    records: List[Record] = []
    with path.open("rb") as f:
        header = read_header(f)
        while True:
            pos = f.tell()
            marker = f.read(1)
            if marker == b"":
                break
            f.seek(pos)
            try:
                records.append(read_record(f, header))
            except EOFError as exc:
                raise FormatError(f"truncated record at byte offset {pos}") from exc
    if not records:
        raise FormatError("capture contains no records")
    for expected, rec in enumerate(records):
        if rec.record_index != expected:
            raise FormatError(
                f"non-contiguous record index at list index {expected}: {rec.record_index}"
            )
    return Capture(path, sha256_file(path), header, records)


def first_diff_byte(a: bytes, b: bytes) -> int:
    limit = min(len(a), len(b))
    for i in range(limit):
        if a[i] != b[i]:
            return i
    return limit if len(a) != len(b) else -1


def unpack_doubles(raw: bytes) -> Tuple[float, ...]:
    if len(raw) % 8:
        raise ValueError("double array byte length is not divisible by 8")
    return struct.unpack("<" + "d" * (len(raw) // 8), raw)


def describe_double_array_diff(name: str, a: bytes, b: bytes) -> Tuple[str, str, str]:
    av = unpack_doubles(a)
    bv = unpack_doubles(b)
    for i, (x, y) in enumerate(zip(av, bv)):
        if a[i * 8:(i + 1) * 8] != b[i * 8:(i + 1) * 8]:
            delta = y - x if math.isfinite(x) and math.isfinite(y) else float("nan")
            return f"{name}[{i}]", repr(x), repr(delta)
    idx = first_diff_byte(a, b)
    return f"{name}.byte[{idx}]", "", ""


def describe_state_diff(a: Record, b: Record, mjtnum_size: int) -> Tuple[str, str, str]:
    byte_idx = first_diff_byte(a.state_raw, b.state_raw)
    if byte_idx < 0:
        return "", "", ""
    scalar_idx = byte_idx // mjtnum_size
    start = scalar_idx * mjtnum_size
    aa = a.state_raw[start:start + mjtnum_size]
    bb = b.state_raw[start:start + mjtnum_size]
    if mjtnum_size == 8:
        x = struct.unpack("<d", aa)[0]
        y = struct.unpack("<d", bb)[0]
    else:
        x = struct.unpack("<f", aa)[0]
        y = struct.unpack("<f", bb)[0]
    delta = y - x if math.isfinite(x) and math.isfinite(y) else float("nan")
    return f"state[{scalar_idx}]@byte{byte_idx}", repr(x), repr(delta)


def headers_equal(a: Header, b: Header) -> bool:
    return a == b


def classify_observed(category: str) -> str:
    if category == "pre_state":
        return "PREEXISTING_STATE_DIVERGENCE"
    if category in ("bridge_seq", "bridge_seq_step_index", "record_alignment"):
        return "UNRESOLVED_BOUNDARY"
    if category == "lowcmd":
        # The snapshot does not contain the exact controller-observed LowState,
        # so controller-vs-input/transport cannot yet be separated.
        return "UNRESOLVED_BOUNDARY"
    if category == "bridge_sensor":
        return "UNRESOLVED_BOUNDARY"
    if category in ("bridge_ctrl", "actual_ctrl"):
        return "BRIDGE_DIVERGENCE"
    if category in ("contact", "next_state", "post_qacc0"):
        return "SIMULATOR_DIVERGENCE"
    return "UNRESOLVED_BOUNDARY"


def compare_pair(a: Capture, b: Capture) -> dict:
    row = {
        "run_a": a.path.name,
        "run_b": b.path.name,
        "sha256_a": a.file_sha256,
        "sha256_b": b.file_sha256,
        "status": "",
        "classification": "",
        "record_index": "",
        "time_ms": "",
        "category": "",
        "field": "",
        "value_a": "",
        "delta_b_minus_a": "",
        "state_sha256_a": "",
        "state_sha256_b": "",
        "note": "",
    }
    if not headers_equal(a.header, b.header):
        row.update(status="PROTOCOL_FAILURE", classification="PROTOCOL_FAILURE", note="snapshot headers differ")
        return row

    n = min(len(a.records), len(b.records))
    for i in range(n):
        ra, rb = a.records[i], b.records[i]
        row["record_index"] = i
        row["time_ms"] = ra.time_ms
        row["state_sha256_a"] = sha256_bytes(ra.state_raw)
        row["state_sha256_b"] = sha256_bytes(rb.state_raw)

        if ra.record_index != rb.record_index or ra.time_ms != rb.time_ms or struct.pack("<d", ra.time_s) != struct.pack("<d", rb.time_s):
            row.update(
                status="DIVERGED", classification="UNRESOLVED_BOUNDARY",
                category="record_alignment", field="record_index/time",
                value_a=f"{ra.record_index}/{ra.time_ms}/{ra.time_s!r}",
                delta_b_minus_a=f"{rb.record_index}/{rb.time_ms}/{rb.time_s!r}",
                note="records no longer align by simulation time",
            )
            return row

        if ra.state_raw != rb.state_raw:
            field, value_a, delta = describe_state_diff(ra, rb, a.header.mjtnum_size)
            row.update(status="DIVERGED", category="pre_state", field=field, value_a=value_a, delta_b_minus_a=delta)
            row["classification"] = classify_observed("pre_state")
            row["note"] = "state already differs at start of this captured step; inspect prior record"
            return row

        if ra.bridge_ctrl_seq != rb.bridge_ctrl_seq:
            row.update(status="DIVERGED", category="bridge_seq", field="bridge_ctrl_seq", value_a=ra.bridge_ctrl_seq, delta_b_minus_a=rb.bridge_ctrl_seq - ra.bridge_ctrl_seq)
            row["classification"] = classify_observed("bridge_seq")
            return row

        if ra.motor_count != rb.motor_count:
            row.update(status="PROTOCOL_FAILURE", classification="PROTOCOL_FAILURE", category="motor_count", field="motor_count", value_a=ra.motor_count, delta_b_minus_a=rb.motor_count - ra.motor_count)
            return row

        if ra.lowcmd_raw != rb.lowcmd_raw:
            arrays = [
                ("q", ra.q_raw, rb.q_raw), ("dq", ra.dq_raw, rb.dq_raw),
                ("kp", ra.kp_raw, rb.kp_raw), ("kd", ra.kd_raw, rb.kd_raw),
                ("tau_ff", ra.tau_ff_raw, rb.tau_ff_raw),
            ]
            for name, xa, xb in arrays:
                if xa != xb:
                    field, value_a, delta = describe_double_array_diff(name, xa, xb)
                    break
            row.update(status="DIVERGED", category="lowcmd", field=field, value_a=value_a, delta_b_minus_a=delta)
            row["classification"] = classify_observed("lowcmd")
            row["note"] = "first observed divergence is LowCmd; exact controller input is not present in GO2PDSNP v2, so controller vs input/transport remains unresolved"
            return row

        if ra.bridge_sensor_raw != rb.bridge_sensor_raw:
            if ra.sensor_q_raw != rb.sensor_q_raw:
                field, value_a, delta = describe_double_array_diff("sensor_q", ra.sensor_q_raw, rb.sensor_q_raw)
            else:
                field, value_a, delta = describe_double_array_diff("sensor_dq", ra.sensor_dq_raw, rb.sensor_dq_raw)
            row.update(status="DIVERGED", category="bridge_sensor", field=field, value_a=value_a, delta_b_minus_a=delta)
            row["classification"] = classify_observed("bridge_sensor")
            return row

        if ra.bridge_ctrl_raw != rb.bridge_ctrl_raw:
            field, value_a, delta = describe_double_array_diff("bridge_ctrl", ra.bridge_ctrl_raw, rb.bridge_ctrl_raw)
            row.update(status="DIVERGED", category="bridge_ctrl", field=field, value_a=value_a, delta_b_minus_a=delta)
            row["classification"] = classify_observed("bridge_ctrl")
            return row

        if ra.actual_ctrl_raw != rb.actual_ctrl_raw:
            field, value_a, delta = describe_double_array_diff("actual_ctrl", ra.actual_ctrl_raw, rb.actual_ctrl_raw)
            row.update(status="DIVERGED", category="actual_ctrl", field=field, value_a=value_a, delta_b_minus_a=delta)
            row["classification"] = classify_observed("actual_ctrl")
            return row

        if (ra.ncon, ra.nefc, ra.contact_mask) != (rb.ncon, rb.nefc, rb.contact_mask):
            row.update(
                status="DIVERGED", category="contact", field="ncon/nefc/contact_mask",
                value_a=f"{ra.ncon}/{ra.nefc}/{ra.contact_mask}",
                delta_b_minus_a=f"{rb.ncon}/{rb.nefc}/{rb.contact_mask}",
            )
            row["classification"] = classify_observed("contact")
            row["note"] = "integration state and applied ctrl match, but pre-step derived contact/constraint metadata differ"
            return row

        if ra.bridge_seq_step_index != rb.bridge_seq_step_index:
            row.update(status="DIVERGED", category="bridge_seq_step_index", field="bridge_seq_step_index", value_a=ra.bridge_seq_step_index, delta_b_minus_a=rb.bridge_seq_step_index - ra.bridge_seq_step_index)
            row["classification"] = classify_observed("bridge_seq_step_index")
            return row

        if struct.pack("<d", ra.qacc0_after) != struct.pack("<d", rb.qacc0_after):
            delta = rb.qacc0_after - ra.qacc0_after if math.isfinite(ra.qacc0_after) and math.isfinite(rb.qacc0_after) else float("nan")
            row.update(status="DIVERGED", category="post_qacc0", field="qacc0_after", value_a=repr(ra.qacc0_after), delta_b_minus_a=repr(delta))
            row["classification"] = classify_observed("post_qacc0")
            return row

        if i + 1 < n and a.records[i + 1].state_raw != b.records[i + 1].state_raw:
            nxt_a, nxt_b = a.records[i + 1], b.records[i + 1]
            field, value_a, delta = describe_state_diff(nxt_a, nxt_b, a.header.mjtnum_size)
            row.update(
                status="DIVERGED", classification="SIMULATOR_DIVERGENCE",
                category="next_state", field=field, value_a=value_a,
                delta_b_minus_a=delta,
                note="same pre-step integration state and applied ctrl; next captured integration state differs",
            )
            return row

    if len(a.records) != len(b.records):
        row.update(
            status="DIVERGED", classification="UNRESOLVED_BOUNDARY",
            record_index=n, category="record_count", field="record_count",
            value_a=len(a.records), delta_b_minus_a=len(b.records) - len(a.records),
            note="one capture ended before the other",
        )
        return row

    row.update(
        status="NO_DIVERGENCE_IN_WINDOW",
        classification="NO_DIVERGENCE_IN_WINDOW",
        record_index=n - 1,
        time_ms=a.records[-1].time_ms,
        category="none",
        note=f"all {n} aligned records are exact-equal at inspected boundaries",
    )
    return row


def write_csv(path: Path, rows: Sequence[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "run_a", "run_b", "sha256_a", "sha256_b", "status", "classification",
        "record_index", "time_ms", "category", "field", "value_a",
        "delta_b_minus_a", "state_sha256_a", "state_sha256_b", "note",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("captures", nargs="+", type=Path, help="two or more GO2PDSNP v2 files")
    p.add_argument("--output", type=Path, default=Path("first_divergence.csv"))
    args = p.parse_args(argv)

    if len(args.captures) < 2:
        p.error("provide at least two captures")

    loaded: List[Capture] = []
    try:
        for path in args.captures:
            loaded.append(load_capture(path))
    except (OSError, FormatError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rows = [compare_pair(a, b) for a, b in itertools.combinations(loaded, 2)]
    write_csv(args.output, rows)

    for row in rows:
        print(
            f"{row['run_a']} vs {row['run_b']}: "
            f"{row['classification']} record={row['record_index']} "
            f"category={row['category']} field={row['field']}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
