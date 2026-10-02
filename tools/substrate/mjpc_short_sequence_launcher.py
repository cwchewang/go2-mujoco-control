"""Reviewed short-sequence launcher: fixed repo entry, locked preflight, sealed output."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from . import fd_duplicate_diagnostic as d
from . import mjpc_short_sequence as sequence
from .guards import wall_deadline
from .integrity import EvidenceRun, digest, experiment_lock, strict_json, verify_manifest, write_new

ROOT = d.ROOT
RUNS = ROOT / "_runs"
WRAPPER = ROOT / "tools/substrate/run_mjpc_short_sequence"
RUNTIME_FILES = (
    "tools/substrate/run_mjpc_short_sequence",
    "tools/substrate/mjpc_short_sequence_launcher.py",
    "tools/substrate/mjpc_short_sequence.py",
    "tools/substrate/native_transport.py",
    "tools/substrate/fd_duplicate_diagnostic.py",
    "tools/substrate/integrity.py",
    "tools/substrate/guards.py",
)


def runtime_identity():
    files = {name: digest(ROOT / name) for name in RUNTIME_FILES}
    for path in sorted((ROOT / "tools/substrate/native").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            files[path.relative_to(ROOT).as_posix()] = digest(path)
    return files


def top_level_output(path):
    path = sequence.require_fresh_output(path)
    if path.parent != RUNS.resolve(strict=True):
        raise ValueError("output must be an independent top-level _runs directory")
    return path


def design():
    return {
        "trials": sequence.sequence_trials(),
        "ticks": list(sequence.TICKS),
        "optimizer_call_ticks": list(sequence.REPLAN_TICKS),
        "optimizer_calls": 8,
        "workers": 4,
        "private_upper_bound": d.TOTAL_UPPER,
        "private_reservation": d.TOTAL_RESERVED,
        "reservation_per_call": d.RESERVATION,
        "canonical_integration_steps": 0,
        "wall_timeout_s": 300,
        "native_timeout_s": 30,
        "failure_policy": "stop at first failure; no retry or replacement",
    }


def prepare(output, original_binary, fixed_binary):
    """No native launch; create one independent immutable prepared bundle."""
    with experiment_lock():
        output = top_level_output(output)
        identity = d.root_identity()
        builds = {v: d.build_identity(p, v) for v, p in
                  (("original", original_binary), ("fixed", fixed_binary))}
        shared = ("cache_sha256", "build_ninja_sha256", "compile_commands_sha256",
                  "mjpc_commit", "mjpc_source_sha256", "diagnostic_patch_script_sha256",
                  "index_patch_sha256", "index_patch_applier_sha256", "index_helper_header_sha256")
        if (any(builds[v]["mjpc_commit"] != d.UPSTREAM for v in builds)
                or any(builds["original"][key] != builds["fixed"][key] for key in shared)
                or builds["original"]["binary_sha256"] == builds["fixed"]["binary_sha256"]):
            raise ValueError("paired build identity mismatch")
        inputs = sequence.load_sequence()
        packet = {
            "schema": 1, "kind": "mjpc-short-sequence",
            **identity, "design": design(), "runtime": runtime_identity(),
            "inputs": inputs, "models": d.model_identity(), "builds": builds,
            "binaries": {
                v: {"path": str(output / ("go2_mjpc_controller_fd_" + v)),
                    "sha256": builds[v]["binary_sha256"]} for v in builds
            },
        }
        with EvidenceRun(output, {"operation": "short_sequence_prepare", **identity}) as run:
            for variant, build in builds.items():
                shutil.copy2(build["path"], packet["binaries"][variant]["path"])
                if digest(packet["binaries"][variant]["path"]) != build["binary_sha256"]:
                    raise ValueError("copied binary identity mismatch")
            write_new(output / "packet.json", packet)
            run.result.update(
                status="ENGINEERING_ADMITTED", scope="short_sequence_prepare",
                capability_status="NOT_RUN", optimizer_calls_executed=0,
                canonical_integration_steps=0, **identity,
            )
        verify_manifest(output)
        return {"status": "PREPARED_NOT_RUN", "packet": str(output / "packet.json"),
                "packet_sha256": digest(output / "packet.json"),
                "manifest_sha256": digest(output / "manifest.json"), **identity}


def live_controller_processes():
    result = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            executable = (path / "exe").resolve(strict=True)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if executable.name.startswith("go2_mjpc_controller"):
            result.append({"pid": int(path.name), "exe": str(executable)})
    return result


def preflight(packet_path, output):
    """Runs under the caller's experiment lock, without invoking a native program."""
    output = top_level_output(output)
    packet_path = Path(packet_path).resolve(strict=True)
    if packet_path.name != "packet.json" or packet_path.parent.parent != RUNS.resolve():
        raise ValueError("packet must belong to an independent top-level _runs bundle")
    admission = verify_manifest(packet_path.parent)
    packet = strict_json(packet_path.read_text())
    if admission.get("scope") != "short_sequence_prepare" or admission.get("status") != "ENGINEERING_ADMITTED":
        raise ValueError("packet preparation is not admitted")
    identity = d.root_identity()
    if {key: packet.get(key) for key in identity} != identity:
        raise ValueError("packet branch/HEAD identity mismatch")
    if packet.get("schema") != 1 or packet.get("kind") != "mjpc-short-sequence" or packet.get("design") != design():
        raise ValueError("sequence design mismatch")
    if packet.get("runtime") != runtime_identity():
        raise ValueError("launcher/runtime source identity mismatch")
    if packet.get("models") != d.model_identity():
        raise ValueError("model identity mismatch")
    inputs = sequence.load_sequence()
    if packet.get("inputs") != inputs:
        raise ValueError("sealed input identity mismatch")
    sequence.validate_sequence_bundle(inputs)
    binaries = {}
    for variant in ("original", "fixed"):
        build = packet["builds"][variant]
        if d.build_identity(build["path"], variant) != build:
            raise ValueError("stale native build identity: " + variant)
        binary = Path(packet["binaries"][variant]["path"]).resolve(strict=True)
        if binary.parent != packet_path.parent or binary.name != "go2_mjpc_controller_fd_" + variant:
            raise ValueError("binary path outside prepared bundle")
        if not os.access(binary, os.X_OK) or digest(binary) != build["binary_sha256"] or digest(binary) != packet["binaries"][variant]["sha256"]:
            raise ValueError("binary identity mismatch: " + variant)
        binaries[variant] = binary
    current = strict_json((ROOT / "docs/research/current.json").read_text())
    if current["branch"] != identity["branch"]:
        raise ValueError("current research pointer branch mismatch")
    subprocess.run([sys.executable, "-B", "-m", "tools.research.workspace", "--check"],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True, capture_output=True, text=True)
    live = live_controller_processes()
    if live:
        raise ValueError("active native controller processes: " + json.dumps(live))
    report = {
        "status": "PRECHECK_PASS", **identity, "working_directory": str(ROOT),
        "packet": str(packet_path), "packet_sha256": digest(packet_path),
        "prepared_manifest_sha256": digest(packet_path.parent / "manifest.json"),
        "output": str(output), "output_fresh": True, "experiment_lock": "held",
        "binary_sha256": {v: digest(p) for v, p in binaries.items()},
        "source_manifest_sha256": inputs["source_manifest_sha256"],
        "source_raw_sha256": inputs["source_raw_sha256"],
        "runtime": packet["runtime"], "design": design(),
        "native_processes_started": 0, "optimizer_calls_executed": 0,
        "canonical_integration_steps": 0,
    }
    return packet, binaries, report


def attempted_calls(directory):
    return sum(len(path.read_text().splitlines())
               for path in Path(directory).rglob("optimizer-attempts.jsonl"))


def accounting(directory):
    """Native counters accumulate within a process; budget each call by its delta."""
    calls = []
    for trial in sequence.sequence_trials():
        sub = Path(directory) / (trial["variant"] + "_repeat" + str(trial["repeat"]))
        previous_upper = previous_reserved = 0
        for line in (sub / "native.jsonl").read_text().splitlines():
            row = strict_json(line)
            if row.get("tick") not in sequence.REPLAN_TICKS:
                continue
            diag = row["response"]["diagnostic"]
            upper = diag["fd_step_upper_bound_count"] + diag["rollout_mj_step_count"]
            reserved = diag["private_step_upper_bound_reserved"]
            delta, reservation = upper - previous_upper, reserved - previous_reserved
            if reservation != d.RESERVATION or not 0 <= delta <= reservation:
                raise ValueError("private per-call delta/reservation mismatch")
            calls.append({**trial, "tick": row["tick"], "upper_bound": delta, "reservation": reservation})
            previous_upper, previous_reserved = upper, reserved
    if len(calls) != 8 or attempted_calls(directory) != 8:
        raise ValueError("optimizer attempt count mismatch")
    total = sum(call["upper_bound"] for call in calls)
    if total > d.TOTAL_UPPER or sum(call["reservation"] for call in calls) != d.TOTAL_RESERVED:
        raise ValueError("aggregate private budget mismatch")
    return {"calls": calls, "private_upper_bound_total": total,
            "private_reserved_total": d.TOTAL_RESERVED, "optimizer_calls": 8,
            "canonical_integration_steps": 0}


def deny_native_launch(*args, **kwargs):
    raise RuntimeError("no-launch mode forbids native execution")


def execute(packet_path, output, no_launch=False, *, runner=None):
    """The full command uses this same lock/preflight for check and capture."""
    runner = deny_native_launch if no_launch else (runner or sequence.run_sequence_batch)
    with experiment_lock():
        packet, binaries, report = preflight(packet_path, output)
        if no_launch:
            return {**report, "status": "PRECHECK_PASS_NO_LAUNCH"}
        output = Path(report["output"])
        with EvidenceRun(output, {"operation": "short_sequence_execute",
                                  "head": report["head"], "packet_sha256": report["packet_sha256"]}) as run:
            run.result.update(scope="short_sequence_observation", optimizer_calls_attempted=0,
                              canonical_integration_steps=0, capability_status="NOT_RUN")
            write_new(output / "fresh-preflight.json", report)
            try:
                with wall_deadline(300):
                    result = runner(packet["inputs"]["source_capture"], binaries,
                                    report["binary_sha256"], output / "trials")
                budget = accounting(output / "trials")
                write_new(output / "RESULT.json", result)
                write_new(output / "private-accounting.json", budget)
                run.result.update(status="ENGINEERING_ADMITTED", capability_status="OBSERVATION_COMPLETE",
                                  private_upper_bound_total=budget["private_upper_bound_total"],
                                  private_reserved_total=d.TOTAL_RESERVED)
            finally:
                run.result["optimizer_calls_attempted"] = attempted_calls(output)
        verify_manifest(output)
        return {"status": "OBSERVATION_COMPLETE", "output": str(output),
                "manifest_sha256": digest(output / "manifest.json")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--original-binary", type=Path)
    parser.add_argument("--fixed-binary", type=Path)
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    if args.prepare:
        if args.no_launch or args.packet or not args.original_binary or not args.fixed_binary:
            parser.error("--prepare requires both binary paths; --no-launch applies to --execute")
        result = prepare(args.output, args.original_binary, args.fixed_binary)
    else:
        if args.packet is None or args.original_binary or args.fixed_binary:
            parser.error("--execute requires --packet; binary identities come from the sealed packet")
        result = execute(args.packet, args.output, args.no_launch)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
