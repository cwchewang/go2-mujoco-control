"""Same-process short-sequence MJPC observation replay; never steps canonical plant."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

from . import fd_duplicate_diagnostic as d
from .native_transport import NativeTransport

TICKS = tuple(range(11))
REPLAN_TICKS = (0, 10)
WARMSTART_KEYS = (
    "warmstart_before_fnv1a64",
    "warmstart_before_norm",
    "warmstart_before_max_abs",
    "warmstart_after_fnv1a64",
    "warmstart_after_norm",
    "warmstart_after_max_abs",
)


def _input_digest(row):
    payload = {
        "tick": row["tick"],
        "time_s": float(row.get("sim_time_s", row.get("time_s"))),
        "command": [float(x) for x in row["command"]],
        "qpos": [float(x) for x in row["qpos"]],
        "qvel": [float(x) for x in row["qvel"]],
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def load_sequence(source_capture=d.CAPTURE):
    """Verify old-A evidence and return only the sealed external 0..10 inputs."""
    source_capture = Path(source_capture).resolve(strict=True)
    admission = d.verify_manifest(source_capture)
    raw = source_capture / "raw.jsonl"
    rows = [d.strict_json(line) for line in raw.read_text().splitlines()]
    if len(rows) < len(TICKS) or [row.get("tick") for row in rows[:11]] != list(TICKS):
        raise ValueError("sealed A stream lacks consecutive ticks 0..10")
    sequence = []
    previous_time = None
    for tick, row in enumerate(rows[:11]):
        time_s = row.get("sim_time_s")
        command, qpos, qvel = row.get("command"), row.get("qpos"), row.get("qvel")
        if (
            row.get("controller_update") is not True
            or row.get("failure") is not None
            or row.get("warning_count") != 0
            or row.get("terminal_reason") is not None
            or not isinstance(time_s, (int, float))
            or isinstance(time_s, bool)
            or not math.isfinite(time_s)
            or not isinstance(command, list)
            or len(command) != 3
            or not d.vector(command, 3)
            or not isinstance(qpos, list)
            or not d.vector(qpos, 19)
            or not isinstance(qvel, list)
            or not d.vector(qvel, 18)
        ):
            raise ValueError(f"invalid sealed external input at tick {tick}")
        expected_time = tick * 0.002
        if not math.isclose(time_s, expected_time, rel_tol=0, abs_tol=1e-12):
            raise ValueError(f"sealed input time discontinuity at tick {tick}")
        if previous_time is not None and time_s <= previous_time:
            raise ValueError(f"sealed input time did not increase at tick {tick}")
        previous_time = time_s
        controller = row.get("controller_diagnostics", {}).get("controller", {})
        last_step = controller.get("last_step", {})
        replan = tick in REPLAN_TICKS
        if last_step.get("replanned") is not replan:
            raise ValueError(f"sealed A replan schedule mismatch at tick {tick}")
        if not math.isclose(
            last_step.get("time_s", float("nan")), time_s, rel_tol=0, abs_tol=1e-12
        ):
            raise ValueError(f"sealed A controller time mismatch at tick {tick}")
        sequence.append(
            {
                "tick": tick,
                "time_s": float(time_s),
                "command": [float(x) for x in command],
                "qpos": [float(x) for x in qpos],
                "qvel": [float(x) for x in qvel],
                "replan": replan,
                "input_sha256": _input_digest(row),
            }
        )
    return {
        "source_capture": str(source_capture),
        "source_manifest_sha256": d.digest(source_capture / "manifest.json"),
        "source_raw_sha256": d.digest(raw),
        "source_status": admission["status"],
        "inputs": sequence,
    }


def validate_sequence_bundle(source):
    if not isinstance(source, dict) or not isinstance(source.get("inputs"), list):
        raise ValueError("sequence input bundle malformed")
    rows = source["inputs"]
    if len(rows) != 11:
        raise ValueError("sequence input bundle must contain ticks 0..10")
    for tick, row in enumerate(rows):
        if (
            not isinstance(row, dict)
            or row.get("tick") != tick
            or row.get("replan") is not (tick in REPLAN_TICKS)
            or not math.isclose(
                row.get("time_s", float("nan")), tick * 0.002, rel_tol=0, abs_tol=1e-12
            )
            or not d.vector(row.get("command"), 3)
            or not d.vector(row.get("qpos"), 19)
            or not d.vector(row.get("qvel"), 18)
            or row.get("input_sha256") != _input_digest(row)
        ):
            raise ValueError(f"sequence input integrity mismatch at tick {tick}")
    capture = Path(source.get("source_capture", "")).resolve(strict=True)
    if capture == Path("/") or capture.is_relative_to(Path("/tmp")):
        raise ValueError("sealed input capture path is not trusted")
    d.verify_manifest(capture)
    if d.digest(capture / "manifest.json") != source.get("source_manifest_sha256"):
        raise ValueError("sealed source manifest identity mismatch")
    return rows


def sequence_trials():
    """Four fresh controller processes; each preserves state over its own 11 ticks."""
    return [
        {"variant": variant, "repeat": repeat}
        for variant in ("original", "fixed")
        for repeat in (1, 2)
    ]


def validate_warmstart_trace(trace, variant, call_index):
    """Validate one native FD-trace line without invoking native code."""
    if not isinstance(trace, dict) or trace.get("call_index") != call_index:
        raise ValueError("FD trace call index mismatch")
    fd_calls = d.OLD_FD[0] if variant == "original" else d.FIXED_FD[0]
    expected_knots = [*range(35), 34, 35] if variant == "original" else list(range(36))
    events = trace.get("events")
    if (
        trace.get("index_count") != fd_calls
        or not isinstance(events, list)
        or len(events) != fd_calls
        or [event.get("t") for event in events] != expected_knots
        or not isinstance(trace.get("jacobian_t34_fnv1a64"), str)
        or len(trace["jacobian_t34_fnv1a64"]) != 16
        or any(c not in "0123456789abcdef" for c in trace["jacobian_t34_fnv1a64"])
    ):
        raise ValueError("FD trace knot schedule mismatch")
    for event in events:
        if (
            event.get("call_index") != call_index
            or type(event.get("worker")) is not int
            or event["worker"] not in range(4)
            or type(event.get("start_ns")) is not int
            or type(event.get("end_ns")) is not int
            or event["start_ns"] >= event["end_ns"]
        ):
            raise ValueError("FD worker event identity or interval mismatch")
        for key in (WARMSTART_KEYS[0], WARMSTART_KEYS[3]):
            value = event.get(key)
            if (
                not isinstance(value, str)
                or len(value) != 16
                or any(c not in "0123456789abcdef" for c in value)
            ):
                raise ValueError("FD warmstart hash missing or malformed")
        for key in WARMSTART_KEYS[1:3] + WARMSTART_KEYS[4:]:
            value = event.get(key)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError("FD warmstart norm summary invalid")


def validate_planner_history(candidate, call_index):
    history = candidate.get("planner_history")
    required = {
        "call_index",
        "pre_policy",
        "pre_previous_policy",
        "post_policy",
        "selected_trajectory",
        "worker_warmstart",
    }
    if (
        not isinstance(history, dict)
        or set(history) != required
        or history["call_index"] != call_index
    ):
        raise ValueError("planner history summary missing or inconsistent")
    for name in (
        "pre_policy",
        "pre_previous_policy",
        "post_policy",
        "selected_trajectory",
    ):
        summary = history[name]
        if (
            not isinstance(summary, dict)
            or type(summary.get("horizon")) is not int
            or type(summary.get("dim_state")) is not int
            or type(summary.get("dim_action")) is not int
            or summary.get("finite") is not True
            or summary.get("return_finite") is not True
            or not d.finite(summary.get("total_return"))
            or not isinstance(summary.get("fnv1a64"), str)
            or len(summary["fnv1a64"]) != 16
            or any(c not in "0123456789abcdef" for c in summary["fnv1a64"])
        ):
            raise ValueError(f"invalid planner trajectory summary: {name}")
    workers = history["worker_warmstart"]
    if not isinstance(workers, dict) or set(workers) != {"pre", "post"}:
        raise ValueError("worker warmstart boundary summary missing")
    expected_pre = 1 if call_index == 1 else 4
    for side, expected_count in (("pre", expected_pre), ("post", 4)):
        values = workers[side]
        if not isinstance(values, list) or len(values) != expected_count:
            raise ValueError(f"worker warmstart count mismatch: {side}")
        for index, value in enumerate(values):
            if (
                not isinstance(value, dict)
                or value.get("worker") != index
                or value.get("finite") is not True
                or not d.finite(value.get("norm"))
                or value["norm"] < 0
                or not d.finite(value.get("max_abs"))
                or value["max_abs"] < 0
                or not isinstance(value.get("fnv1a64"), str)
                or len(value["fnv1a64"]) != 16
                or any(c not in "0123456789abcdef" for c in value["fnv1a64"])
            ):
                raise ValueError(f"invalid worker warmstart summary: {side}")


def _append_json(path, value, first=False):
    mode = "x" if first else "a"
    with Path(path).open(mode, encoding="utf-8") as stream:
        stream.write(
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())


def _validate_replan_output(directory, variant, call_index, anchor):
    traces = [
        d.strict_json(line)
        for line in (directory / "fd-trace.jsonl").read_text().splitlines()
    ]
    candidates = [
        d.strict_json(line)
        for line in (directory / "predictions.jsonl").read_text().splitlines()
    ]
    if len(traces) != call_index or len(candidates) != call_index:
        raise ValueError("replan trace/candidate record count mismatch")
    trace, candidate = traces[-1], candidates[-1]
    validate_warmstart_trace(trace, variant, call_index)
    validate_planner_history(candidate, call_index)
    if (
        candidate.get("policy_id") != call_index
        or candidate.get("mode") != variant
        or candidate.get("optimization_model_id") != variant + "-go2-soft-v1"
        or not math.isclose(
            candidate.get("anchor_time_s", float("nan")),
            anchor["time_s"],
            rel_tol=0,
            abs_tol=1e-12,
        )
    ):
        raise ValueError("replan candidate identity mismatch")
    return {
        "policy_id": candidate["policy_id"],
        "candidate_id": candidate["candidate_id"],
        "cost": None,
        "trajectory_hash": candidate["planner_history"]["selected_trajectory"][
            "fnv1a64"
        ],
        "policy_hash": candidate["planner_history"]["post_policy"]["fnv1a64"],
        "worker_warmstart": candidate["planner_history"]["worker_warmstart"],
        "jacobian_t34_fnv1a64": trace["jacobian_t34_fnv1a64"],
        "t34_workers": [
            event["worker"] for event in trace["events"] if event["t"] == 34
        ],
    }


def require_fresh_output(path):
    """Reject existing paths, symlink aliases, and every sealed ancestor before writes."""
    lexical = Path(os.path.abspath(path))
    resolved = lexical.resolve(strict=False)
    if lexical != resolved:
        raise ValueError("output path traverses a symlink or alias")
    for ancestor in (resolved, *resolved.parents):
        if (ancestor / "manifest.json").exists() and (
            ancestor / "admission.json"
        ).exists():
            raise ValueError("output must be outside sealed evidence")
    if os.path.lexists(lexical):
        raise ValueError("output must be fresh; existing directory or file is rejected")
    return resolved


def run_sequence_trial(
    trial,
    source,
    binaries,
    identities,
    output_dir,
    *,
    popen=subprocess.Popen,
    native_transport=NativeTransport,
):
    """Run one approved variant/repeat after admission; keeps one process for all ticks."""
    variant = trial.get("variant")
    if variant not in ("original", "fixed") or trial.get("repeat") not in (1, 2):
        raise ValueError("invalid sequence trial identity")
    rows = validate_sequence_bundle(source)
    output_dir = require_fresh_output(output_dir)
    capture = Path(source["source_capture"]).resolve(strict=True)
    if output_dir == capture or output_dir.is_relative_to(capture):
        raise ValueError("sequence output must be outside the sealed source capture")
    output_dir.mkdir(parents=True, exist_ok=False)
    trace = output_dir / "fd-trace.jsonl"
    native_log = output_dir / "native.jsonl"
    stderr_log = output_dir / "native.stderr.log"
    predictions = output_dir / "predictions.jsonl"
    argv = [
        str(binaries[variant]),
        str(d.TASK),
        variant,
        str(d.CANON),
        str(predictions),
    ]

    def launch(args, **kwargs):
        env = os.environ.copy()
        env["GO2_MJPC_FD_TRACE_PATH"] = str(trace)
        return popen(args, env=env, **kwargs)

    transport = native_transport(argv, popen=launch, stderr_log_path=stderr_log)
    result = {"variant": variant, "repeat": trial["repeat"], "inputs": []}
    call_index = 0
    try:
        ready = transport.read_json(10)
        d.candidate_contract(ready)
        if ready.get("worker_count") != 4:
            raise ValueError("sequence replay requires four workers")
        _append_json(native_log, {"ready": ready}, first=True)
        for row in rows:
            anchor = {
                "time_s": row["time_s"],
                "command": row["command"],
                "qpos": row["qpos"],
                "qvel": row["qvel"],
            }
            request = d._packet(anchor, replan=row["replan"])
            if row["replan"]:
                call_index += 1
                if call_index > 2:
                    raise ValueError("sequence optimizer call count exceeded")
                _append_json(
                    output_dir / "optimizer-attempts.jsonl",
                    {
                        "call_index": call_index,
                        "tick": row["tick"],
                        "reserved_upper_bound": d.RESERVATION,
                    },
                    first=call_index == 1,
                )
            response = transport.request(request, 30)
            _append_json(
                native_log,
                {
                    "tick": row["tick"],
                    "time_s": row["time_s"],
                    "input_sha256": row["input_sha256"],
                    "request": request,
                    "response": response,
                },
            )
            if (
                response.get("ok") is not True
                or response.get("replanned") is not row["replan"]
                or response.get("current_rollout_valid") is not True
                or not math.isclose(
                    response.get("time_s", float("nan")),
                    row["time_s"],
                    rel_tol=0,
                    abs_tol=1e-12,
                )
                or not math.isclose(
                    response.get("vx", float("nan")),
                    row["command"][0],
                    rel_tol=0,
                    abs_tol=1e-12,
                )
                or not math.isclose(
                    response.get("wz", float("nan")),
                    row["command"][2],
                    rel_tol=0,
                    abs_tol=1e-12,
                )
                or response.get("diagnostic", {}).get("policy_id") != call_index
                or not d.finite(response.get("cost"))
                or not d.vector(response.get("q_des"), 12)
            ):
                raise ValueError(
                    f"native sequence response rejected at tick {row['tick']}"
                )
            diag = response["diagnostic"]
            fd_calls, fd_upper = d.OLD_FD if variant == "original" else d.FIXED_FD
            expected_fd_calls = call_index * fd_calls
            expected_fd_upper = call_index * fd_upper
            expected_rollouts = call_index * d.ROLLOUT_STEPS
            expected_reserved = call_index * d.RESERVATION
            if call_index and (
                diag.get("fd_call_count") != expected_fd_calls
                or diag.get("fd_step_upper_bound_count") != expected_fd_upper
                or diag.get("rollout_mj_step_count") != expected_rollouts
                or diag.get("private_step_upper_bound_reserved") != expected_reserved
                or diag.get("private_step_limit") != d.LIMIT
            ):
                raise ValueError(
                    f"private budget/accounting mismatch at tick {row['tick']}"
                )
            stderr_state = transport.diagnostics()
            if stderr_state["stderr_read_error"] or stderr_state["stderr_bytes"]:
                raise ValueError(f"native warning/stderr stop at tick {row['tick']}")
            replan_summary = None
            if row["replan"]:
                replan_summary = _validate_replan_output(
                    output_dir, variant, call_index, anchor
                )
                replan_summary["cost"] = response["cost"]
            result["inputs"].append(
                {
                    "tick": row["tick"],
                    "time_s": row["time_s"],
                    "input_sha256": row["input_sha256"],
                    "replanned": row["replan"],
                    "policy_id": call_index,
                    "cost": response["cost"],
                    "q_des": response["q_des"],
                    "replan_summary": replan_summary,
                }
            )
        if call_index != 2:
            raise ValueError("sequence must contain exactly two optimizer calls")
    finally:
        transport.close()
    stderr_state = transport.diagnostics()
    if stderr_state["stderr_read_error"] or stderr_state["stderr_bytes"]:
        raise ValueError("native warning/stderr drain failure")
    result.update(
        {
            "binary_identity": identities[variant],
            "source_capture_manifest_sha256": source["source_manifest_sha256"],
            "source_raw_sha256": source["source_raw_sha256"],
            "optimizer_calls": call_index,
            "private_configured_reservation": call_index * d.RESERVATION,
            "canonical_integration_steps": 0,
            "logs": {
                "native": "native.jsonl",
                "stderr": "native.stderr.log",
                "fd_trace": "fd-trace.jsonl",
                "predictions": "predictions.jsonl",
                "optimizer_attempts": "optimizer-attempts.jsonl",
            },
        }
    )
    return result


def compare_sequence_trials(results, tolerance=1e-9):
    """Summarize paired observations; differences are outcomes, not auto-failures."""
    if len(results) != 4 or {
        (result.get("variant"), result.get("repeat")) for result in results
    } != {(variant, repeat) for variant in ("original", "fixed") for repeat in (1, 2)}:
        raise ValueError("comparison requires exactly two repeats per variant")
    source_hashes = {result.get("source_raw_sha256") for result in results}
    if len(source_hashes) != 1 or None in source_hashes:
        raise ValueError("sequence source identities differ")
    by_key = {(r["variant"], r["repeat"]): r for r in results}
    input_digests = []
    for tick in TICKS:
        rows = [result["inputs"][tick] for result in results]
        hashes = {row.get("input_sha256") for row in rows}
        if len(hashes) != 1 or None in hashes:
            raise ValueError(f"external input mismatch at tick {tick}")
        input_digests.append(hashes.pop())
    summaries = []
    for tick in REPLAN_TICKS:
        observations = {
            key: by_key[key]["inputs"][tick]["replan_summary"] for key in by_key
        }
        if any(value is None for value in observations.values()):
            raise ValueError(f"missing optimizer summary at tick {tick}")
        pair_metrics = {}
        for label, pairs in (
            (
                "within_variant_repeat",
                [
                    (("original", 1), ("original", 2)),
                    (("fixed", 1), ("fixed", 2)),
                ],
            ),
            (
                "cross_variant",
                [
                    (("original", 1), ("fixed", 1)),
                    (("original", 1), ("fixed", 2)),
                    (("original", 2), ("fixed", 1)),
                    (("original", 2), ("fixed", 2)),
                ],
            ),
        ):
            max_cost = 0.0
            max_q_des = 0.0
            candidates_equal = True
            for left, right in pairs:
                a = by_key[left]["inputs"][tick]
                b = by_key[right]["inputs"][tick]
                candidates_equal = candidates_equal and (
                    a["replan_summary"]["candidate_id"]
                    == b["replan_summary"]["candidate_id"]
                )
                max_cost = max(max_cost, abs(a["cost"] - b["cost"]))
                max_q_des = max(
                    max_q_des,
                    max(abs(x - y) for x, y in zip(a["q_des"], b["q_des"])),
                )
            pair_metrics[label] = {
                "candidate_ids_equal": candidates_equal,
                "max_abs_cost_difference": max_cost,
                "max_abs_q_des_difference": max_q_des,
                "within_1e_9": max(max_cost, max_q_des) <= tolerance,
            }
        summaries.append(
            {
                "tick": tick,
                "pairs": pair_metrics,
                "per_run": {
                    f"{variant}_repeat{repeat}": {
                        "candidate_id": value["candidate_id"],
                        "cost": value["cost"],
                        "q_des": by_key[(variant, repeat)]["inputs"][tick]["q_des"],
                        "jacobian_t34_fnv1a64": value["jacobian_t34_fnv1a64"],
                        "t34_workers": value["t34_workers"],
                        "policy_hash": value["policy_hash"],
                        "trajectory_hash": value["trajectory_hash"],
                        "worker_warmstart": value["worker_warmstart"],
                    }
                    for (variant, repeat), value in observations.items()
                },
            }
        )
    return {
        "status": "OBSERVATION_COMPLETE",
        "source_raw_sha256": next(iter(source_hashes)),
        "input_digests_match": True,
        "optimizer_calls": 8,
        "private_configured_reservation": 8 * d.RESERVATION,
        "canonical_integration_steps": 0,
        "comparisons": summaries,
    }


def run_sequence_batch(
    source_capture,
    binaries,
    identities,
    output_root,
    *,
    popen=subprocess.Popen,
    native_transport=NativeTransport,
):
    """Run one four-trial sequence set after the existing admission decision."""
    source = load_sequence(source_capture)
    output_root = require_fresh_output(output_root)
    output_root.mkdir(parents=True, exist_ok=False)
    before = d.digest(Path(source["source_capture"]) / "manifest.json")
    if before != source["source_manifest_sha256"]:
        raise ValueError("sealed source manifest changed before sequence run")
    results = []
    for trial in sequence_trials():
        directory = output_root / f"{trial['variant']}_repeat{trial['repeat']}"
        results.append(
            run_sequence_trial(
                trial,
                source,
                binaries,
                identities,
                directory,
                popen=popen,
                native_transport=native_transport,
            )
        )
    d.verify_manifest(Path(source["source_capture"]))
    if d.digest(Path(source["source_capture"]) / "manifest.json") != before:
        raise ValueError("sealed source changed during sequence run")
    return compare_sequence_trials(results)
