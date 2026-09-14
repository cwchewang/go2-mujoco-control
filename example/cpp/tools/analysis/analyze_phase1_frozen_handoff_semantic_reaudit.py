#!/usr/bin/env python3
"""Offline component-aware semantic re-audit of frozen handoff captures."""
from __future__ import annotations
import argparse
import csv
import importlib.util
import itertools
import math
import struct
import sys
from pathlib import Path

CTRL_START = 56
CTRL_END = 68
MOTOR_COUNT = 12
OLD = "analyze_phase1_frozen_handoff_first_divergence.py"

def decoder():
    p = Path(__file__).with_name(OLD)
    spec = importlib.util.spec_from_file_location("phase1_old_decoder", p)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v2 decoder")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m

D = decoder()

def fvals(raw):
    return struct.unpack("<" + "d" * (len(raw) // 8), raw)

def diff_array(name, a, b):
    for i, (x, y) in enumerate(zip(fvals(a), fvals(b))):
        if a[i * 8:(i + 1) * 8] != b[i * 8:(i + 1) * 8]:
            d = y - x if math.isfinite(x) and math.isfinite(y) else float("nan")
            return f"{name}[{i}]", repr(x), repr(y), repr(d)
    return f"{name}.byte[{D.first_diff_byte(a, b)}]", "", "", ""

def diff_state(a, b, size):
    byte = D.first_diff_byte(a.state_raw, b.state_raw)
    if byte < 0:
        return "", "", "", ""
    i = byte // size
    aa = a.state_raw[i * size:(i + 1) * size]
    bb = b.state_raw[i * size:(i + 1) * size]
    x = struct.unpack("<d" if size == 8 else "<f", aa)[0]
    y = struct.unpack("<d" if size == 8 else "<f", bb)[0]
    d = y - x if math.isfinite(x) and math.isfinite(y) else float("nan")
    return f"state[{i}]", repr(x), repr(y), repr(d)

def nonctrl(raw, size):
    return raw[:CTRL_START * size] + raw[CTRL_END * size:]

def ctrl(raw, size):
    return raw[CTRL_START * size:CTRL_END * size]

def base(a, b):
    return {
        "pair": f"{a.run_id}-{b.run_id}", "run_a": a.run_id, "run_b": b.run_id,
        "sha256_a": a.file_sha256, "sha256_b": b.file_sha256, "status": "",
        "classification": "", "earliest_record_index": "", "earliest_tick_ms": "",
        "previous_record_index": "", "previous_tick_ms": "", "state_component": "",
        "field": "", "value_a": "", "value_b": "", "delta_b_minus_a": "",
        "upstream_equal": "", "state_sha256_a": "", "state_sha256_b": "",
        "category": "", "evidence_note": "",
    }

def done(row, a, b, i, prev, classification, category, field="", va="", vb="",
         delta="", component="", equal="", note=""):
    row.update(
        status="DIVERGED", classification=classification,
        earliest_record_index=i, earliest_tick_ms=a.time_ms,
        previous_record_index=i - 1 if i else "", previous_tick_ms=prev,
        state_component=component, field=field, value_a=va, value_b=vb,
        delta_b_minus_a=delta, upstream_equal=equal,
        state_sha256_a=__import__("hashlib").sha256(a.state_raw).hexdigest(),
        state_sha256_b=__import__("hashlib").sha256(b.state_raw).hexdigest(),
        category=category, evidence_note=note,
    )
    return row

def compare(a, b):
    row = base(a, b)
    if a.header != b.header or len(a.records) != len(b.records):
        row.update(status="PROTOCOL_FAILURE", classification="PROTOCOL_FAILURE",
                   category="header_or_record_count",
                   evidence_note="capture headers or record counts differ")
        return row
    size = a.header.mjtnum_size
    pending_next = None
    for i, (ra, rb) in enumerate(zip(a.records, b.records)):
        prev = "" if i == 0 else a.records[i - 1].time_ms
        aligned = (ra.record_index == rb.record_index and ra.time_ms == rb.time_ms
                   and struct.pack("<d", ra.time_s) == struct.pack("<d", rb.time_s))
        if not aligned:
            return done(row, ra, rb, i, prev, "PROTOCOL_FAILURE", "record/time",
                        "record_index/time", repr((ra.record_index, ra.time_ms, ra.time_s)),
                        repr((rb.record_index, rb.time_ms, rb.time_s)),
                        equal="", note="records must align by record index and time")
        if nonctrl(ra.state_raw, size) != nonctrl(rb.state_raw, size):
            f, va, vb, d = diff_state(ra, rb, size)
            return done(row, ra, rb, i, prev,
                        "ORIGINAL_CLASSIFICATION_OVERTURNED_PREEXISTING_STATE",
                        "noncontrol_state", f, va, vb, d,
                        "non-control integration state", "record/time equal",
                        "a genuine non-control plant/solver state differs before the candidate step")
        if ra.bridge_sensor_raw != rb.bridge_sensor_raw:
            if ra.sensor_q_raw != rb.sensor_q_raw:
                f, va, vb, d = diff_array("bridge_sensor_q", ra.sensor_q_raw, rb.sensor_q_raw)
            else:
                f, va, vb, d = diff_array("bridge_sensor_dq", ra.sensor_dq_raw, rb.sensor_dq_raw)
            return done(row, ra, rb, i, prev,
                        "ORIGINAL_CLASSIFICATION_OVERTURNED_BRIDGE", "bridge_sensor",
                        f, va, vb, d, equal="record/time and non-control state equal",
                        note="bridge sensor q/dq is first to differ")
        if ra.lowcmd_raw != rb.lowcmd_raw:
            for name, xa, xb in (
                ("LowCmd.q", ra.q_raw, rb.q_raw), ("LowCmd.dq", ra.dq_raw, rb.dq_raw),
                ("LowCmd.kp", ra.kp_raw, rb.kp_raw), ("LowCmd.kd", ra.kd_raw, rb.kd_raw),
                ("LowCmd.tau_ff", ra.tau_ff_raw, rb.tau_ff_raw)):
                if xa != xb:
                    f, va, vb, d = diff_array(name, xa, xb)
                    break
            return done(row, ra, rb, i, prev,
                        "ORIGINAL_CLASSIFICATION_OVERTURNED_CONTROLLER_OR_TRANSPORT",
                        "lowcmd", f, va, vb, d, "ctrl[56:68]",
                        "record/time, non-control state, and bridge sensor q/dq equal",
                        "LowCmd differs before bridge application; v2 cannot distinguish controller from input/transport. state[56:68] is the applied-ctrl duplicate, not simulator-step evidence")
        if ra.bridge_ctrl_raw != rb.bridge_ctrl_raw:
            f, va, vb, d = diff_array("bridge_ctrl", ra.bridge_ctrl_raw, rb.bridge_ctrl_raw)
            return done(row, ra, rb, i, prev,
                        "ORIGINAL_CLASSIFICATION_OVERTURNED_BRIDGE", "bridge_ctrl",
                        f, va, vb, d, equal="all prior semantic fields equal",
                        note="bridge-computed control is first to differ")
        if ra.actual_ctrl_raw != rb.actual_ctrl_raw:
            f, va, vb, d = diff_array("actual_ctrl", ra.actual_ctrl_raw, rb.actual_ctrl_raw)
            return done(row, ra, rb, i, prev,
                        "ORIGINAL_CLASSIFICATION_OVERTURNED_BRIDGE", "actual_ctrl",
                        f, va, vb, d, equal="all prior semantic fields equal",
                        note="actual mjData.ctrl is first to differ")
        if ctrl(ra.state_raw, size) != ctrl(rb.state_raw, size):
            f, va, vb, d = diff_state(ra, rb, size)
            return done(row, ra, rb, i, prev, "UNRESOLVED_STATE_COMPONENT", "state_ctrl",
                        f, va, vb, d, "ctrl[56:68]", equal="all prior explicit fields equal",
                        note="embedded ctrl differs without actual_ctrl; conflicts with Method A identity")
        ma = (ra.ncon, ra.nefc, ra.contact_mask, ra.bridge_ctrl_seq,
              ra.bridge_seq_step_index, ra.motor_count)
        mb = (rb.ncon, rb.nefc, rb.contact_mask, rb.bridge_ctrl_seq,
              rb.bridge_seq_step_index, rb.motor_count)
        if ma != mb:
            return done(row, ra, rb, i, prev, "UNRESOLVED_REQUIRES_POSTSTEP_CAPTURE",
                        "contact_bridge_metadata", "contact/bridge metadata",
                        repr(ma), repr(mb), equal="all state/control fields equal",
                        note="v2 cannot distinguish an intervening writer from simulator evolution")
        if struct.pack("<d", ra.qacc0_after) != struct.pack("<d", rb.qacc0_after):
            d = rb.qacc0_after - ra.qacc0_after
            return done(row, ra, rb, i, prev,
                        "ORIGINAL_SIMULATOR_CLASSIFICATION_CONFIRMED", "qacc0_after",
                        "qacc0_after", repr(ra.qacc0_after), repr(rb.qacc0_after),
                        repr(d), equal="all preceding semantic fields equal",
                        note="immediate post-step qacc0_after differs with identical pre-step state and applied inputs")
        if i + 1 < len(a.records) and a.records[i + 1].state_raw != b.records[i + 1].state_raw:
            pending_next = i + 1
    if pending_next is not None:
        i = pending_next
        ra, rb = a.records[i], b.records[i]
        return done(row, ra, rb, i, a.records[i - 1].time_ms,
                    "UNRESOLVED_REQUIRES_POSTSTEP_CAPTURE", "next_state_component",
                    "component-aware next-record state", "", "", "",
                    equal="current record explicit fields equal",
                    note="next captured state differs but v2 lacks an immediate post-mj_step full-state capture")
    row.update(status="NO_DIVERGENCE_IN_WINDOW",
               classification="ORIGINAL_SIMULATOR_CLASSIFICATION_CONFIRMED",
               category="none", evidence_note="all aligned records match")
    return row

def provenance(caps, path):
    with path.open(newline="", encoding="utf-8") as f:
        rows = {r["run_id"]: r for r in csv.DictReader(f)}
    if set(rows) != {"L1", "L2", "L3"}:
        raise RuntimeError("parent provenance must contain exactly L1, L2, L3")
    found = {}
    for cap in caps:
        hit = [r for r in rows.values() if r["raw_sha256"] == cap.file_sha256]
        if len(hit) != 1:
            raise RuntimeError(f"raw hash not uniquely present in parent provenance: {cap.path}")
        r = hit[0]
        if int(r["raw_bytes"]) != cap.path.stat().st_size or int(r["record_count"]) != len(cap.records):
            raise RuntimeError(f"raw size or record count mismatch for {r['run_id']}")
        cap.run_id = r["run_id"]
        found[cap.run_id] = r
    if set(found) != {"L1", "L2", "L3"}:
        raise RuntimeError("exactly parent L1-L3 captures are required")
    return found

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=fields, lineterminator="\n").writeheader()
        csv.DictWriter(f, fieldnames=fields, lineterminator="\n").writerows(rows)

def component_map(caps):
    h = caps[0].header
    common = {"state_sig": h.state_sig, "state_size": h.state_size,
              "mjtNum_size": h.mjtnum_size, "nq": h.nq, "nv": h.nv,
              "na": h.na, "nu": h.nu}
    specs = [
        ("time", 0, 1, "Method B exact-model layout"),
        ("qpos", 1, 20, "Method B exact-model layout"),
        ("qvel", 20, 38, "Method B exact-model layout"),
        ("act", 38, 38, "Method B exact-model layout; na=0"),
        ("warmstart", 38, 56, "Method B exact-model layout"),
        ("ctrl", 56, 68, "Method B; Method A state[56:68] equals actual_ctrl_raw for 2500/2500 records in each L1-L3 capture"),
        ("qfrc_applied", 68, 86, "Method B exact-model layout"),
        ("xfrc_applied", 86, 194, "Method B exact-model layout"),
    ]
    out = []
    for name, start, end, evidence in specs:
        r = dict(common)
        r.update(component=name, start_index=start, end_index_exclusive=end,
                 scalar_count=end - start,
                 state_56_meaning="ctrl[0]" if name == "ctrl" else "",
                 method_evidence=evidence)
        out.append(r)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("captures", nargs=3, type=Path)
    ap.add_argument("--provenance", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--component-map-output", required=True, type=Path)
    args = ap.parse_args()
    try:
        caps = [D.load_capture(p) for p in args.captures]
        prov = provenance(caps, args.provenance)
        for cap in caps:
            if cap.header.state_size < CTRL_END or cap.header.nu != MOTOR_COUNT:
                raise RuntimeError("capture header cannot support ctrl[56:68]")
            size = cap.header.mjtnum_size
            count = sum(ctrl(r.state_raw, size) == r.actual_ctrl_raw for r in cap.records)
            if count != len(cap.records):
                raise RuntimeError(f"Method A identity failed for {cap.run_id}: {count}/{len(cap.records)}")
        caps.sort(key=lambda c: c.run_id)
        rows = [compare(a, b) for a, b in itertools.combinations(caps, 2)]
        fields = ["pair", "run_a", "run_b", "sha256_a", "sha256_b", "status",
                  "classification", "earliest_record_index", "earliest_tick_ms",
                  "previous_record_index", "previous_tick_ms", "state_component",
                  "field", "value_a", "value_b", "delta_b_minus_a",
                  "upstream_equal", "state_sha256_a", "state_sha256_b",
                  "category", "evidence_note"]
        write_csv(args.output, rows, fields)
        map_fields = ["component", "start_index", "end_index_exclusive",
                      "scalar_count", "state_56_meaning", "state_sig",
                      "state_size", "mjtNum_size", "nq", "nv", "na", "nu",
                      "method_evidence"]
        write_csv(args.component_map_output, component_map(caps), map_fields)
        for r in rows:
            print(f"{r['pair']}: {r['classification']} record={r['earliest_record_index']} field={r['field']}")
        print("parent provenance matched: " + ", ".join(
            k + "=" + v["raw_sha256"] for k, v in sorted(prov.items())))
    except (OSError, D.FormatError, RuntimeError, ValueError) as e:
        print("error: " + str(e), file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
