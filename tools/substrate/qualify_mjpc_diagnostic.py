"""Fresh bounded diagnostic qualification; zero canonical integrations."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import qualification as q
from .build_identity import inputs, seal, seal_controller
from .guards import zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    run_logged,
    write_new,
    verify_bundle,
)
from .mjpc_diagnostic import ROOT, model_audit
from .qualify_rl_friction import SUBSTRATE_TESTS, guarded_tests


def smoke(directory):
    raw = (
        ROOT
        / "example/cpp/experiments/_runs/shared_baseline_probes_v1/run_20261002T085338452324Z/mjpc_baseline_1.jsonl"
    )
    if (
        digest(raw)
        != "e5f760c54a57d12e8da6150972cb084414c3f9d84f1827ac9582b292532a3841"
    ):
        raise ValueError("sealed initial-action reference changed")
    row = json.loads(raw.open().readline())
    pos = row["qpos"]
    vel = row["qvel"]
    values = (
        [0, 0, 0, 0]
        + pos[:7]
        + [pos[i] for i in [10, 11, 12, 7, 8, 9, 16, 17, 18, 13, 14, 15]]
        + vel[:6]
        + [vel[i] for i in [9, 10, 11, 6, 7, 8, 15, 16, 17, 12, 13, 14]]
    )
    packet = "step 1 " + " ".join(format(x, ".17g") for x in values) + "\nquit\n"
    binary = ROOT / ".substrate/headless-reliable/go2_mjpc_controller"
    args = [
        str(binary),
        str(ROOT / ".substrate/mjpc/mjpc/tasks/quadruped/task_flat.xml"),
        "original",
        str(ROOT / "unitree_robots/go2/phase2_flat.xml"),
        str(directory / "native-smoke-predictions.jsonl"),
    ]
    result = subprocess.run(
        args, input=packet, text=True, capture_output=True, timeout=30
    )
    (directory / "native-smoke.stdout").write_text(result.stdout)
    (directory / "native-smoke.stderr").write_text(result.stderr)
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    if result.returncode or not responses[-1].get("ok"):
        raise ValueError("bounded native engineering smoke failed")
    account = responses[-1]["diagnostic"]
    delta = float(
        np.max(
            np.abs(
                np.asarray(responses[-1]["q_des"]) - row["target"]["position_target"]
            )
        )
    )
    if (
        delta != 0
        or account["policy_id"] != 1
        or account["rollout_mj_step_count"] <= 0
        or account["fd_call_count"] <= 0
        or account["rollout_mj_step_count"] + account["fd_step_upper_bound_count"]
        > 4096
    ):
        raise ValueError("initial-action neutrality/counter proof failed")
    return {
        "canonical_steps": 0,
        "scientific_attempts": 0,
        "optimizer_calls": 1,
        "private_step_upper_bound_max": 4096,
        "accounting": account,
        "max_initial_action_difference": delta,
        "binary_sha256": digest(binary),
        "whole_episode_neutrality": "not established",
    }


def retained_smoke(directory):
    """Reuse only sealed native smoke evidence; all qualification checks rerun."""
    source = (
        ROOT
        / "_runs/mjpc_adaptation_diagnostic_prep_20261002/qualification_20261002T145537Z"
    )
    development = (
        ROOT
        / "_runs/mjpc_adaptation_diagnostic_prep_20261002/engineering_smoke_20261002T143620582863Z"
    )
    refs = [
        (
            development,
            "752d8ab69d7abf5abde7a1c36c81d22ea3d28c74b17d42fd52c2aee8f78f1d59",
        ),
        (source, "c826241af14d63e65c7a412652376a2064a5d66751ddc8d3f5602bffaee42228"),
    ]
    records = []
    for path, expected in refs:
        if digest(path / "manifest.json") != expected:
            raise ValueError("sealed engineering smoke source changed")
        record = verify_bundle(path)
        value = record.get("private_accounting")
        if value is None:
            value = record["physics_accounting"]["accounting"]
        if (
            value["policy_id"] != 1
            or value["rollout_mj_step_count"] != 700
            or value["fd_step_upper_bound_count"] != 1801
            or value["fd_call_count"] != 37
            or value["private_step_upper_bound_reserved"] != 4096
            or record["canonical_physics_steps"] != 0
            or record["scientific_attempts"] != 0
        ):
            raise ValueError("engineering smoke total accounting source mismatch")
        records.append(
            {
                "path": str(path),
                "manifest_sha256": expected,
                "optimizer_calls": 1,
                "rollout_steps": 700,
                "fd_step_upper_bound": 1801,
                "combined_step_upper_bound": 2501,
                "reserved_step_upper_bound": 4096,
                "canonical_steps": 0,
                "scientific_attempts": 0,
            }
        )
    original = verify_bundle(source)
    value = json.loads((source / "native-smoke-accounting.json").read_text())
    binary = ROOT / ".substrate/headless-reliable/go2_mjpc_controller"
    if value["binary_sha256"] != digest(binary):
        raise ValueError("retained smoke binary changed; cannot reuse")
    now = q.current_inputs()
    old = original["qualification_inputs"]
    if any(
        now[k] != old[k]
        for k in (
            "runtime",
            "native_build",
            "native_binary_sha256",
            "linked_libraries",
            "interpreter_sha256",
            "cpu_identity",
        )
    ):
        raise ValueError("retained smoke native/runtime inputs changed")
    ledger = {
        "runs": records,
        "optimizer_calls_total": sum(r["optimizer_calls"] for r in records),
        "rollout_steps_total": sum(r["rollout_steps"] for r in records),
        "fd_step_upper_bound_total": sum(r["fd_step_upper_bound"] for r in records),
        "combined_step_upper_bound_total": sum(
            r["combined_step_upper_bound"] for r in records
        ),
        "reserved_step_upper_bound_total": sum(
            r["reserved_step_upper_bound"] for r in records
        ),
        "canonical_steps_total": 0,
        "scientific_attempts_total": 0,
        "new_optimizer_calls_in_this_qualification": 0,
        "authorization_basis": {
            "source_thread_id": "01a0f08f-d223-7240-813b-ee93267b700d",
            "standing_third_stage_instruction_summary": "Continue minimum adaptation diagnostic preparation and bounded qualification; no user reauthorization for third stage.",
            "scope": "engineering preparation only; genuine exact-head reviews still required before formal capture",
            "task": "docs/research/TASK_MJPC_ADAPTATION_DIAGNOSTIC_V1_20261002.md",
            "direction_turn": "01a0fcef-18b2-753f-b7ef-ee6ca2ba89b6",
            "direction_is_exact_head_approval": False,
        },
    }
    write_new(directory / "engineering-total-ledger.json", ledger)
    for name in (
        "native-smoke.stdout",
        "native-smoke.stderr",
        "native-smoke-predictions.jsonl",
    ):
        (directory / name).write_bytes((source / name).read_bytes())
    return dict(
        value,
        execution="reused_sealed_native_smoke_no_new_optimizer",
        source_reference=records[1],
        cumulative_engineering_accounting=ledger,
    )


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
            physics = retained_smoke(run.path)
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
                qualification_profile="mjpc_adaptation_diagnostic_v1",
                qualification={"clean_head": True, "development": False, "head": head},
                qualification_inputs=initial,
                qualification_fingerprint=q.fingerprint(initial),
                canonical_physics_steps=0,
                scientific_attempts=0,
                private_engineering_optimizer_calls=0,
                cumulative_engineering_accounting=physics[
                    "cumulative_engineering_accounting"
                ],
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
