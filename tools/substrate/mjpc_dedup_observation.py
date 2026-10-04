"""Four-call unique-index-only intervention with sealed runtime and no canonical stepping."""

from __future__ import annotations

import argparse
import json
import importlib.metadata
from pathlib import Path
import subprocess
import sys

from . import mjpc_short_sequence as sequence
from . import native_runtime
from .guards import wall_deadline, zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_manifest,
    write_new,
)
from .native_transport import NativeTransport
from .qualification import tracked_inputs

ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT.parent / "current"
SOURCE = (
    PARENT
    / "_runs/mjpc_adaptation_diagnostic_execution_20261002/original_capture_20261002T164948Z"
)
OLD_PACKET = PARENT / "_runs/mjpc_short_sequence_evidence_launcherfix_20261003"
BRANCH = "research/mjpc-faithful-dedup-observation-20261004"
BINARY_SHA = "3644c6160dae354319c94840bdd07ca12166500a2b133f97b78421f8db587b08"
DESIGN = {
    "variant": "fixed",
    "repeats": 2,
    "ticks": list(range(11)),
    "replan_ticks": [0, 10],
    "workers": 4,
    "optimizer_calls_max": 4,
    "private_reserved_max": 16384,
    "private_derived_upper": 9808,
    "canonical_integration_steps": 0,
    "tolerance": 1e-9,
    "initialization": "constructor_then_live_adapter_reset",
    "encoder": "production_named_joint_state",
    "failure_policy": "stop_first_execution_evidence_warning_budget_failure_no_retry",
    "mismatch_policy": "retain_both_predeclared_repeats_as_observations",
}


BASELINE = (
    PARENT.parent
    / "faithful-original-observation/_runs/mjpc_faithful_original_observation_20261003"
)
BASELINE_MANIFEST = "8b3e6fc4c36a7a188715b8221d7bf4d9347683f1637355c24e4a9fcefe8e79d9"


def single_factor_audit():
    """Prove the archived pair differs only in derivative index selection."""
    import hashlib
    from .native import patch_mjpc_model_derivatives_diagnostic as patch

    verify_manifest(BASELINE)
    if digest(BASELINE / "manifest.json") != BASELINE_MANIFEST:
        raise ValueError("sealed control observation changed")
    verify_manifest(OLD_PACKET)
    old = strict_json((OLD_PACKET / "packet.json").read_text())
    shared = (
        "build_ninja_sha256",
        "cache_sha256",
        "compile_commands_sha256",
        "diagnostic_patch_script_sha256",
        "index_helper_header_sha256",
        "index_patch_applier_sha256",
        "index_patch_sha256",
        "mjpc_commit",
        "mjpc_source_sha256",
        "workers",
    )
    builds = old["builds"]
    if any(builds["original"][k] != builds["fixed"][k] for k in shared):
        raise ValueError("matched binary provenance differs outside intervention")
    data = (ROOT / ".substrate/mjpc/mjpc/planners/model_derivatives.cc").read_bytes()
    texts = {v: patch.render(data, v == "fixed") for v in ("original", "fixed")}
    if (
        texts["original"].replace(patch.OLD_INSTRUMENTED, patch.FIXED_INSTRUMENTED, 1)
        != texts["fixed"]
    ):
        raise ValueError("native delta is not solely derivative indices")
    for variant in ("original", "fixed"):
        if (
            hashlib.sha256(texts[variant].encode()).hexdigest()
            != builds[variant]["generated_source_sha256"]
        ):
            raise ValueError("archived native derivative source mismatch")
        if (
            digest(OLD_PACKET / ("go2_mjpc_controller_fd_" + variant))
            != builds[variant]["binary_sha256"]
        ):
            raise ValueError("archived native pair mismatch")
    if (
        digest(ROOT / "tools/substrate/native/model_derivative_indices.h")
        != builds["fixed"]["index_helper_header_sha256"]
    ):
        raise ValueError("unique-index helper changed")
    baseline = strict_json((BASELINE / "RESULT.json").read_text())
    if baseline["optimizer_calls"] != 4 or any(
        r["variant"] != "original" for r in baseline["results"]
    ):
        raise ValueError("control is not closed faithful original observation")
    return {
        "baseline_manifest_sha256": BASELINE_MANIFEST,
        "baseline_root": str(BASELINE),
        "matched_builds": builds,
        "intervention": "remove duplicate t34 index only; worker qacc_warmstart untouched",
        "native_shared_provenance_fields": list(shared),
        "current_generator_sha256": digest(
            ROOT / "tools/substrate/native/patch_mjpc_model_derivatives_diagnostic.py"
        ),
        "generator_reuse": "current formatting differs; rendered bytes equal both archived translation units",
        "expected_indices": list(range(36)),
        "original_indices": [0] + list(range(1, 35)) + [34, 35],
        "private_call_upper": 35 * (1 + 36 + 12) + (1 + 36) + 10 * 70,
    }


def identity():
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    )
    if branch != BRANCH or dirty:
        raise ValueError("exact clean faithful-observation branch required")
    return {"head": head, "branch": branch}


def inputs():
    return {
        "tracked_runtime_tests_assets": tracked_inputs(ROOT),
        "interpreter": {
            "path": str(Path(sys.executable).resolve()),
            "sha256": digest(Path(sys.executable).resolve()),
        },
        "checkpoint_unused": digest(ROOT / ".substrate/rl/policy.pt"),
        "source_lock": digest(ROOT / "tools/substrate/sources.lock.json"),
        "python_distributions": {
            name: {
                "version": importlib.metadata.version(name),
                "record_sha256": digest(
                    importlib.metadata.distribution(name).locate_file(
                        str(importlib.metadata.distribution(name)._path.name)
                        + "/RECORD"
                    )
                ),
            }
            for name in ("numpy", "mujoco")
        },
        "cpu": [
            s
            for s in Path("/proc/cpuinfo").read_text().splitlines()
            if s.startswith(("vendor_id", "model name", "microcode", "flags"))
        ][:4],
    }


def jwrite(path, value):
    write_new(path, value)


def prepare(output):
    with experiment_lock(), zero_step_guard(), EvidenceRun(output) as run:
        before = identity()
        source = sequence.load_sequence(SOURCE)
        sequence.validate_sequence_bundle(source)
        old = verify_manifest(OLD_PACKET)
        if old["status"] != "ENGINEERING_ADMITTED":
            raise ValueError("historical original runtime was not admitted")
        packet = strict_json((OLD_PACKET / "packet.json").read_text())
        audit = single_factor_audit()
        jwrite(run.path / "single-factor-audit.json", audit)
        build = packet["builds"]["fixed"]
        binary = OLD_PACKET / "go2_mjpc_controller_fd_fixed"
        if digest(binary) != BINARY_SHA or build["binary_sha256"] != BINARY_SHA:
            raise ValueError("original binary changed")
        snapshot = inputs()
        runtime = native_runtime.package(binary, run.path / "runtime", ROOT, build)
        if (
            digest(run.path / "runtime/lib/libmujoco.so.3.3.6")
            != "b9173509d0c282a9b24b7f5825a40177a9967df0cd6395a9dc39522196e44495"
        ):
            raise ValueError("MuJoCo loader dependency changed")
        commands = [
            (
                "observer_contracts",
                [
                    sys.executable,
                    "-B",
                    "-c",
                    "import unittest; from tools.substrate.guards import zero_step_guard; "
                    "from tools.substrate import fd_duplicate_diagnostic as d; "
                    "from tools.substrate.mjpc_dedup_observation import SOURCE,PARENT; "
                    "d.CAPTURE=SOURCE; d.ROOT=PARENT; "
                    "suite=unittest.defaultTestLoader.loadTestsFromNames("
                    "['tools.substrate.test_mjpc_retired_capture','tools.substrate.test_mjpc_diagnostic.DiagnosticTests',"
                    "'tools.substrate.test_mjpc_sequence_reset','tools.substrate.test_mjpc_sequence_mapping',"
                    "'tools.substrate.test_mjpc_short_sequence','tools.substrate.test_native_transport',"
                    "'tools.substrate.test_native_mjpc','tools.substrate.test_mjpc_faithful_observation','tools.substrate.test_mjpc_dedup_observation']); "
                    "guard=zero_step_guard(); guard.__enter__(); "
                    "result=unittest.TextTestRunner(verbosity=2).run(suite); "
                    "guard.__exit__(None,None,None); raise SystemExit(not result.wasSuccessful())",
                ],
            ),
            (
                "native_zero_integration",
                [
                    "ctest",
                    "--test-dir",
                    str(ROOT / ".substrate/headless-reliable"),
                    "--output-on-failure",
                    "-R",
                    "ground_miss_zero_integration|fresh_plan_zero_integration|diagnostic_mapping_zero_integration",
                ],
            ),
            (
                "quality",
                [
                    str(ROOT / ".substrate/dev-venv/bin/python"),
                    "-B",
                    "-m",
                    "tools.check_quality",
                    "--style",
                ],
            ),
            ("diff_check", ["git", "diff", "--check"]),
        ]
        checks = []
        for name, argv in commands:
            result = subprocess.run(
                argv, cwd=ROOT, capture_output=True, text=True, timeout=90
            )
            (run.path / (name + ".stdout")).write_text(result.stdout)
            (run.path / (name + ".stderr")).write_text(result.stderr)
            checks.append({"name": name, "argv": argv, "returncode": result.returncode})
            if result.returncode:
                raise ValueError("qualification failed: " + name)
        if snapshot != inputs() or before != identity():
            raise ValueError("inputs changed during qualification")
        qualification = {
            "schema": 1,
            "profile": "fixed_external_unique_index_observer_no_optimizer_smoke",
            **before,
            "inputs": snapshot,
            "design": DESIGN,
            "checks": checks,
            "runtime": runtime,
            "source": source,
            "native_build_provenance": build,
            "native_provenance_manifest_sha256": digest(OLD_PACKET / "manifest.json"),
            "native_reuse_boundary": "sealed matched fixed binary; only unique FD indices differ from sealed original control",
            "single_factor_audit": audit,
            "new_optimizer_calls": 0,
            "canonical_integration_steps": 0,
        }
        jwrite(run.path / "packet.json", qualification)
        run.result.update(
            status="ENGINEERING_ADMITTED",
            scope="faithful_dedup_qualification",
            optimizer_calls_executed=0,
            canonical_integration_steps=0,
        )
    return {
        "packet": str(Path(output) / "packet.json"),
        "manifest_sha256": digest(Path(output) / "manifest.json"),
    }


def live_controller_processes(proc=Path("/proc")):
    """Find direct and ELF-loader-launched controller children without launching."""
    found = []
    for process in proc.iterdir():
        if not process.name.isdecimal():
            continue
        try:
            executable = (process / "exe").resolve().name
            args = (process / "cmdline").read_bytes().split(b"\0")
            names = [Path(arg.decode(errors="replace")).name for arg in args if arg]
        except (OSError, ValueError):
            continue
        direct = executable.startswith("go2_mjpc_controller")
        loader = executable.startswith("ld-linux") and any(
            name.startswith("go2_mjpc_controller") for name in names
        )
        if direct or loader:
            found.append(
                {"pid": int(process.name), "executable": executable, "argv": names}
            )
    return found


def precheck(packet_path, output):
    packet_path = Path(packet_path).resolve(strict=True)
    admission = verify_manifest(packet_path.parent)
    packet = strict_json(packet_path.read_text())
    if (
        admission.get("scope") != "faithful_dedup_qualification"
        or admission.get("status") != "ENGINEERING_ADMITTED"
    ):
        raise ValueError("applicable qualification not admitted")
    if (
        {k: packet[k] for k in ("head", "branch")} != identity()
        or packet["inputs"] != inputs()
        or packet["design"] != DESIGN
    ):
        raise ValueError("qualification is stale")
    if packet["single_factor_audit"] != single_factor_audit():
        raise ValueError("single-factor intervention binding changed")
    if packet["source"] != sequence.load_sequence(SOURCE):
        raise ValueError("fixed external input identity changed")
    sidecar = packet_path.parent / "runtime" / native_runtime.SIDECAR
    binary = sidecar.parent / "go2_mjpc_controller_fd_fixed"
    if (
        native_runtime.verify(binary, sidecar) != packet["runtime"]
        or digest(binary) != BINARY_SHA
    ):
        raise ValueError("sealed runtime changed")
    output = sequence.require_fresh_output(output)
    if output.parent != ROOT / "_runs":
        raise ValueError("output must be a new top-level observer run")
    if live_controller_processes():
        raise ValueError("native controller already running")
    return (
        packet,
        binary,
        sidecar,
        {
            "status": "PRECHECK_PASS",
            **identity(),
            "packet_sha256": digest(packet_path),
            "qualification_manifest_sha256": digest(
                packet_path.parent / "manifest.json"
            ),
            "output": str(output),
            "design": DESIGN,
            "runtime_closure_verified": True,
            "source_identity_verified": True,
            "optimizer_calls_executed": 0,
            "canonical_integration_steps": 0,
        },
    )


def review(path, role, preflight):
    value = strict_json(Path(path).read_text())
    if (
        value.get("role") != role
        or value.get("verdict") != "PASS"
        or value.get("head") != preflight["head"]
        or value.get("packet_sha256") != preflight["packet_sha256"]
        or not value.get("reviewer")
        or not value.get("rationale")
    ):
        raise ValueError("independent current review binding failed: " + role)
    return value


def compare(results):
    if [r["repeat"] for r in results] != [1, 2] or any(
        r["variant"] != "fixed" for r in results
    ):
        raise ValueError("exact fixed repeat pair required")
    comparisons = []
    for tick in sequence.TICKS:
        a, b = [r["inputs"][tick] for r in results]
        if a["input_sha256"] != b["input_sha256"]:
            raise ValueError("repeat external inputs differ")
        comparisons.append(
            {
                "tick": tick,
                "max_abs_q_des_difference": max(
                    abs(x - y) for x, y in zip(a["q_des"], b["q_des"])
                ),
                "abs_cost_difference": abs(a["cost"] - b["cost"]),
                "summaries": [a["replan_summary"], b["replan_summary"]],
            }
        )
    return comparisons


def partial_accounting(directory):
    """Account only validated returned counters; preserve unknown reservations."""
    attempted = completed = upper = reserved = 0
    errors = []
    for trial in Path(directory).glob("fixed_repeat[12]"):

        def read_rows(path):
            if not path.exists():
                return []
            values = []
            for index, line in enumerate(path.read_text().splitlines()):
                try:
                    value = strict_json(line)
                    if not isinstance(value, dict):
                        raise ValueError("row is not an object")
                    values.append(value)
                except (ValueError, TypeError) as error:
                    errors.append(f"{trial.name}/{path.name}:{index + 1}: {error}")
            return values

        attempts = read_rows(trial / "optimizer-attempts.jsonl")
        attempted += len(attempts)
        for row in attempts:
            if (
                type(row.get("reserved_upper_bound")) is int
                and row["reserved_upper_bound"] == 4096
            ):
                reserved += row["reserved_upper_bound"]
            else:
                errors.append(trial.name + ": invalid reservation")
        calls = 0
        known_upper = 0
        for row in read_rows(trial / "native.jsonl"):
            if row.get("tick") not in (0, 10):
                continue
            response = row.get("response")
            diag = response.get("diagnostic") if isinstance(response, dict) else None
            expected = {
                "policy_id": calls + 1,
                "fd_call_count": (calls + 1) * 36,
                "fd_step_upper_bound_count": (calls + 1) * 1752,
                "rollout_mj_step_count": (calls + 1) * 700,
                "private_step_upper_bound_reserved": (calls + 1) * 4096,
                "private_step_limit": 614400,
            }
            if (
                not isinstance(response, dict)
                or response.get("ok") is not True
                or response.get("replanned") is not True
                or not isinstance(diag, dict)
                or row["tick"] != (0 if calls == 0 else 10)
                or any(
                    type(diag.get(key)) is not int or diag[key] != value
                    for key, value in expected.items()
                )
            ):
                errors.append(trial.name + ": unverified replan response/counters")
                continue
            calls += 1
            known_upper = (
                diag["fd_step_upper_bound_count"] + diag["rollout_mj_step_count"]
            )
        completed += calls
        upper += known_upper
    return {
        "reserved_optimizer_calls": attempted,
        "completed_optimizer_calls": completed,
        "private_reserved": reserved,
        "private_accounted_upper": upper,
        "unverified_reserved_upper": max(0, reserved - completed * 4096),
        "accounting_complete": attempted == completed and not errors,
        "accounting_errors": errors,
        "canonical_integration_steps": 0,
    }


def execute(packet_path, output, science, execution):
    with experiment_lock(), zero_step_guard(), wall_deadline(300):
        packet, binary, sidecar, preflight = precheck(packet_path, output)
        reviews = [
            review(science, "science", preflight),
            review(execution, "execution", preflight),
        ]
        if reviews[0]["reviewer"] == reviews[1]["reviewer"]:
            raise ValueError("independent reviewer roles require distinct identities")
        with EvidenceRun(output, {"head": preflight["head"], "design": DESIGN}) as run:
            jwrite(run.path / "preflight.json", preflight)
            jwrite(run.path / "reviews.json", reviews)
            jwrite(
                run.path / "campaign-reservation.json",
                {
                    "calls_max": 4,
                    "private_reserved_max": 16384,
                    "canonical_steps": 0,
                    "authorization": "direct user continuation 2026-10-04; new independent unique-index-only four-call budget; no retry",
                    "source_thread": "01a0f08f-d223-7240-813b-ee93267b700d",
                },
            )
            run.result.update(
                scope="faithful_dedup_observation", capability_status="STARTED"
            )
            try:
                results = []
                runtime = packet["runtime"]
                loader_argv, task = native_runtime.argv(binary, sidecar)

                def popen(argv, **kwargs):
                    if argv[0] != str(binary) or argv[2] != "fixed":
                        raise ValueError("non-fixed launch prohibited")
                    env = kwargs["env"]
                    for key in ("LD_PRELOAD", "LD_AUDIT", "LD_LIBRARY_PATH"):
                        env.pop(key, None)
                    return subprocess.Popen(
                        [
                            *loader_argv,
                            str(task),
                            "fixed",
                            str(sidecar.parent / runtime["canonical_xml"]),
                            argv[4],
                        ],
                        **kwargs,
                    )

                class BoundTransport(NativeTransport):
                    def read_json(self, timeout):
                        response = super().read_json(timeout)
                        loaded = native_runtime.loaded_libraries(
                            self.process.pid, sidecar
                        )
                        path = self.stderr_path.parent / "loaded-libraries.json"
                        if not path.exists():
                            jwrite(path, loaded)
                        return response

                # No comparisons suppress either repeat; integrity/warning/budget errors stop immediately.
                for repeat in (1, 2):
                    sub = run.path / ("fixed_repeat" + str(repeat))
                    result = sequence.run_sequence_trial(
                        {"variant": "fixed", "repeat": repeat},
                        packet["source"],
                        {"fixed": binary},
                        {"fixed": packet["native_build_provenance"]},
                        sub,
                        popen=popen,
                        native_transport=BoundTransport,
                    )
                    jwrite(sub / "result.json", result)
                    results.append(result)
                calls = sum(
                    len(
                        (
                            run.path
                            / ("fixed_repeat" + str(i))
                            / "optimizer-attempts.jsonl"
                        )
                        .read_text()
                        .splitlines()
                    )
                    for i in (1, 2)
                )
                upper = 0
                reserved = 0
                for i in (1, 2):
                    rows = [
                        strict_json(s)
                        for s in (run.path / ("fixed_repeat" + str(i)) / "native.jsonl")
                        .read_text()
                        .splitlines()
                    ]
                    diag = rows[-1]["response"]["diagnostic"]
                    upper += (
                        diag["fd_step_upper_bound_count"]
                        + diag["rollout_mj_step_count"]
                    )
                    reserved += diag["private_step_upper_bound_reserved"]
                if calls != 4 or upper != 9808 or reserved != 16384:
                    raise ValueError("campaign accounting mismatch")
                report = {
                    "status": "OBSERVATION_COMPLETE",
                    "design": DESIGN,
                    "results": results,
                    "comparisons": compare(results),
                    "optimizer_calls": calls,
                    "private_accounted_upper": upper,
                    "private_reserved": reserved,
                    "canonical_integration_steps": 0,
                    **preflight,
                }
                report["status"] = "OBSERVATION_COMPLETE"
                jwrite(run.path / "RESULT.json", report)
                # Recheck sealed inputs and source after the bounded campaign.
                verify_manifest(SOURCE)
                native_runtime.verify(binary, sidecar)
                if packet["inputs"] != inputs() or identity()["head"] != packet["head"]:
                    raise ValueError("execution inputs changed during observation")
                run.result.update(
                    status="ENGINEERING_ADMITTED",
                    scope="faithful_dedup_observation",
                    optimizer_calls_executed=calls,
                    private_accounted_upper=upper,
                    private_reserved=reserved,
                    canonical_integration_steps=0,
                )
            finally:
                counts = partial_accounting(run.path)
                jwrite(run.path / "accounting.json", counts)
                run.result.update(**counts)
                run.result["capability_status"] = (
                    "COMPLETE"
                    if run.result["status"] == "ENGINEERING_ADMITTED"
                    else "FAILED"
                )
    return {
        "status": "OBSERVATION_COMPLETE",
        "manifest_sha256": digest(Path(output) / "manifest.json"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "precheck", "execute"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--science", type=Path)
    parser.add_argument("--execution", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        result = prepare(args.output)
    elif args.action == "precheck":
        with experiment_lock(), zero_step_guard():
            result = precheck(args.packet, args.output)[3]
    else:
        result = execute(args.packet, args.output, args.science, args.execution)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
