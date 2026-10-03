"""Fresh bounded diagnostic qualification; zero canonical integrations."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import fd_duplicate_diagnostic as fd_build
from . import native_runtime
from . import qualification as q
from .aligned_anchor import load_anchor
from .build_identity import inputs, seal, seal_controller
from .contracts import MOTOR_JOINTS, Proprioception, WholeBodyState
from .guards import zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    run_logged,
    write_new,
)
from .mjpc_diagnostic import ROOT, model_audit
from .mjpc_floor_registration_diagnostic import (
    R4_PREP,
    assert_only_floor_z_changed,
)
from .native_mjpc import NativeMJPCController
from .qualify_rl_friction import SUBSTRATE_TESTS, guarded_tests


def smoke_state_from_anchor(row):
    qpos, qvel = row["qpos"], row["qvel"]
    qpos_order = [10, 11, 12, 7, 8, 9, 16, 17, 18, 13, 14, 15]
    qvel_order = [9, 10, 11, 6, 7, 8, 15, 16, 17, 12, 13, 14]
    observation = Proprioception(
        MOTOR_JOINTS,
        [qpos[i] for i in qpos_order],
        [qvel[i] for i in qvel_order],
        qpos[3:7],
        qvel[3:6],
    )
    return WholeBodyState(
        observation, qpos[:3], qvel[:3], float(row["sim_time_s"])
    )


def smoke(directory, binary):
    """One bounded cold-start call on the exact fixed floor0 consumer runtime."""
    raw = (
        ROOT
        / "example/cpp/experiments/_runs/shared_baseline_probes_v1/run_20261002T085338452324Z/mjpc_baseline_1.jsonl"
    )
    if (
        digest(raw)
        != "e5f760c54a57d12e8da6150972cb084414c3f9d84f1827ac9582b292532a3841"
    ):
        raise ValueError("sealed initial-action reference changed")
    binary = Path(binary).resolve(strict=True)
    identity = fd_build.build_identity(binary, "fixed")
    runtime = Path(directory) / "consumer-runtime"
    native_runtime.package(binary, runtime, ROOT, identity)
    task_xml = runtime / "source/mjpc/tasks/quadruped/task_flat.xml"
    base_task = R4_PREP / "runtime/source/mjpc/tasks/quadruped/task_flat.xml"
    source = task_xml.read_text()
    source, count = re.subn(
        r'(<geom\b[^>]*\bname="floor"[^>]*\bpos="[^"]*?)-0\.01([^"]*")',
        r"\g<1>0\g<2>",
        source,
        count=1,
    )
    if count != 1:
        raise ValueError("unique private floor z edit not found")
    task_xml.write_text(source)
    floor_delta = assert_only_floor_z_changed(base_task, task_xml)
    sidecar = runtime / native_runtime.SIDECAR
    side = json.loads(sidecar.read_text())
    side["files"] = {
        item.relative_to(runtime).as_posix(): digest(item)
        for item in sorted(runtime.rglob("*"))
        if item.is_file() and item != sidecar
    }
    sidecar.write_text(json.dumps(side, indent=2, sort_keys=True) + "\n")
    runtime_identity = native_runtime.verify(runtime / binary.name, sidecar)
    canonical = runtime / runtime_identity["canonical_xml"]
    row = json.loads(raw.read_text().splitlines()[0])
    state = smoke_state_from_anchor(row)
    predictions = Path(directory) / "native-smoke-predictions.jsonl"
    fd_trace = Path(directory) / "native-smoke-fd-trace.jsonl"
    stderr = Path(directory) / "native-smoke.stderr"
    anchor = load_anchor()
    controller = NativeMJPCController(
        runtime / binary.name,
        anchor["controllers"]["mjpc"]["timing"],
        stderr_log_path=stderr,
        diagnostic=("floor0", canonical, predictions),
        runtime_identity=sidecar,
        fd_trace_path=fd_trace,
    )
    try:
        action = controller.step(state, row["command"])
        controller.close()
        diagnostics = controller.diagnostics()
    finally:
        controller.close()
    accounting = diagnostics["last_step"]["diagnostic"]
    total = (
        accounting["rollout_mj_step_count"]
        + accounting["fd_step_upper_bound_count"]
    )
    action_delta = float(
        np.max(
            np.abs(
                np.asarray(action)
                - np.asarray(row["target"]["position_target"])
            )
        )
    )
    if (
        accounting["policy_id"] != 1
        or accounting["private_step_upper_bound_reserved"] != 4096
        or accounting["private_step_limit"] != 614400
        or total > 4096
        or accounting["fd_call_count"] <= 0
        or diagnostics["transport"]["stderr_bytes"] != 0
        or diagnostics["transport"]["stderr_read_error"] is not None
        or not np.isfinite(np.asarray(action)).all()
        or not predictions.is_file()
        or not fd_trace.is_file()
        or fd_trace.stat().st_size == 0
    ):
        raise ValueError("exact-consumer one-call accounting/readiness failed")
    return {
        "canonical_steps": 0,
        "scientific_attempts": 0,
        "optimizer_calls": 1,
        "private_step_upper_bound_max": 4096,
        "accounting": accounting,
        "max_initial_action_difference": action_delta,
        "binary_sha256": digest(runtime / binary.name),
        "binary_build_identity": identity,
        "runtime_identity_sha256": digest(sidecar),
        "runtime_identity": runtime_identity,
        "private_model_delta": floor_delta,
        "consumer_scope": "one cold-start floor0 fixed-controller replan at sealed tick-0 state",
        "action_difference_interpretation": "descriptive only; floor registration changes the private model",
        "whole_episode_neutrality": "not established",
    }

def qualify(output):
    with experiment_lock() as lock, zero_step_guard():
        if subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ):
            raise ValueError("qualification requires clean HEAD")
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        with EvidenceRun(
            Path(output), {"operation": "mjpc_diagnostic_qualification"}
        ) as run:
            native = ROOT / ".substrate/headless-reliable"
            run.result["native_checks"] = {}
            run.result["native_checks"]["configure"] = run_logged(
                [
                    "cmake",
                    "-S",
                    ROOT / "tools/substrate/native",
                    "-B",
                    native,
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DFETCHCONTENT_SOURCE_DIR_ABSEIL="
                    + str(native / "_deps/abseil-src"),
                    "-DFETCHCONTENT_FULLY_DISCONNECTED=ON",
                    "-DGO2_MJPC_BUILD_FD_DIAGNOSTIC=ON",
                ],
                run.path,
                "native_configure",
                120,
                ROOT,
            )
            before = inputs(native)
            run.result["native_checks"]["build"] = run_logged(
                ["cmake", "--build", native, "-j", "4"],
                run.path,
                "native_build",
                180,
                ROOT,
            )
            seal(native, before)
            seal_controller(native, before)
            run.result["native_checks"]["tests"] = run_logged(
                ["ctest", "--test-dir", native, "--output-on-failure"],
                run.path,
                "native_tests",
                120,
                ROOT,
            )
            baseline = q.current_inputs(include_controller=False)
            build = ROOT / ".substrate/controller-reliable"
            commands = [
                (
                    "controller_configure",
                    [
                        "cmake",
                        "-S",
                        ROOT / "example/cpp",
                        "-B",
                        build,
                        "-DCMAKE_BUILD_TYPE=Release",
                    ],
                    120,
                ),
                ("controller_build", ["cmake", "--build", build, "-j", "4"], 600),
                (
                    "controller_tests",
                    ["ctest", "--test-dir", build, "--output-on-failure"],
                    120,
                ),
                (
                    "substrate_tests",
                    guarded_tests(
                        SUBSTRATE_TESTS
                        + (
                            "tools.substrate.test_mjpc_diagnostic",
                            "tools.substrate.test_native_mjpc",
                            "tools.substrate.test_aligned_episode",
                            "tools.substrate.test_native_transport",
                            "tools.substrate.test_mjpc_floor_registration_diagnostic",
                        )
                    ),
                    180,
                ),
                (
                    "preflight_tests",
                    guarded_tests(
                        (
                            "tools.research.test_preflight",
                            "tools.research.test_preflight_integration",
                        )
                    ),
                    120,
                ),
                (
                    "tooling_tests",
                    [
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tools/tests",
                        "-p",
                        "test_*.py",
                    ],
                    120,
                ),
                ("quality", [sys.executable, "-m", "tools.check_quality"], 120),
                ("diff_check", ["git", "diff", "--check"], 30),
            ]
            run.result["qualification_checks"] = {}
            initial = None
            for name, argv, timeout in commands:
                run.result["qualification_checks"][name] = run_logged(
                    argv,
                    run.path,
                    name,
                    timeout,
                    ROOT,
                    pass_fds=(lock.fileno(),) if name == "substrate_tests" else (),
                )
                if name == "controller_build":
                    initial = q.current_inputs()
                    if any(
                        baseline[k] != initial[k]
                        for k in baseline
                        if k != "controller_build"
                    ):
                        raise ValueError("qualification inputs changed during build")
            evidence = model_audit()
            write_new(run.path / "model-audit.json", evidence)
            physics = smoke(
                run.path,
                ROOT / ".substrate/headless-reliable/go2_mjpc_controller_fd_fixed",
            )
            write_new(run.path / "native-smoke-accounting.json", physics)
            if (
                q.current_inputs() != initial
                or subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip()
                != head
                or subprocess.check_output(
                    ["git", "status", "--porcelain"], cwd=ROOT, text=True
                )
            ):
                raise ValueError("qualification identity changed")
            run.result.update(
                status="ENGINEERING_ADMITTED",
                qualification_profile="mjpc_floor_registration_sustained_12s_v1",
                qualification={"clean_head": True, "development": False, "head": head},
                qualification_inputs=initial,
                qualification_fingerprint=q.fingerprint(initial),
                canonical_physics_steps=0,
                scientific_attempts=0,
                private_engineering_optimizer_calls=physics["optimizer_calls"],
                physics_accounting=physics,
            )
            q.validate_record(run.result, initial)
    return q.validate(output)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(qualify(a.output)))


if __name__ == "__main__":
    main()
