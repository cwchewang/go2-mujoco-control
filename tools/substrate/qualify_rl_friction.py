"""Task-specific qualification: fresh Python checks, unchanged sealed native checks."""

import argparse
import copy
from pathlib import Path
import sys

from . import qualification as q
from . import rl_friction_reference as spec
from .guards import zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    run_logged,
    verify_bundle,
    write_new,
)

ROOT = spec.ROOT
CACHED = (
    ROOT
    / "_runs/shared_campaign_runner_prep_20261002/preflight_wiring_qualification_20261002T082220356151Z"
)
CACHED_MANIFEST = "1db729ccb7723becfc4eadaca3948bf13cb438db3c003f99ba048f1bd423d621"
OVERLAY_FILES = frozenset(
    {
        "tools/substrate/rl_friction_reference.py",
        "tools/substrate/test_rl_friction_reference.py",
        "tools/substrate/protocols/rl_sliding_friction_reference_v1.json",
        "tools/substrate/rl_friction_campaign.py",
        "tools/substrate/test_rl_friction_campaign.py",
        "tools/substrate/qualify_rl_friction.py",
        "tools/substrate/shared_campaign.py",
    }
)
CACHED_CHECKS = ("controller_configure", "controller_build", "controller_tests")
SUBSTRATE_TESTS = (
    "tools.substrate.test_substrate",
    "tools.substrate.test_native_boundary",
    "tools.substrate.test_reliability",
    "tools.substrate.test_policy_runtime",
    "tools.substrate.test_clock",
    "tools.substrate.test_launch",
    "tools.substrate.test_qualification",
    "tools.substrate.test_baseline",
    "tools.substrate.test_bounded_conditions",
    "tools.substrate.test_shared_campaign",
    "tools.substrate.test_rl_friction_reference",
    "tools.substrate.test_rl_friction_campaign",
)


def cached_basis(source, actual):
    """Only this reviewed Python/protocol increment may differ from the old base."""
    q.validate_record(source, source["qualification_inputs"])
    before, after = copy.deepcopy(source["qualification_inputs"]), copy.deepcopy(actual)
    for value in (before, after):
        value["tracked_files"] = {
            k: v for k, v in value["tracked_files"].items() if k not in OVERLAY_FILES
        }
    if before != after:
        raise ValueError(
            "unchanged native/environment/base qualification inputs differ"
        )
    if not OVERLAY_FILES.issubset(actual["tracked_files"]):
        raise ValueError("qualification increment files are missing")
    return {
        "source_head": source["qualification"]["head"],
        "source_fingerprint": source["qualification_fingerprint"],
        "allowed_reviewed_increment_files": sorted(OVERLAY_FILES),
        "unchanged_remainder_fingerprint": q.fingerprint(after),
        "native_build_binary_link_compiler_model_environment_unchanged": True,
    }


def guarded_tests(modules):
    code = (
        "import unittest; from tools.substrate.guards import zero_step_guard; "
        "guard=zero_step_guard(); guard.__enter__(); "
        "suite=unittest.defaultTestLoader.loadTestsFromNames("
        + repr(list(modules))
        + "); "
        "result=unittest.TextTestRunner(verbosity=2).run(suite); "
        "guard.__exit__(None,None,None); raise SystemExit(not result.wasSuccessful())"
    )
    return [sys.executable, "-c", code]


def qualify(output):
    with experiment_lock(), zero_step_guard():
        plan = spec.load_plan()
        head = spec.shared.current_head(plan)
        if digest(CACHED / "manifest.json") != CACHED_MANIFEST:
            raise ValueError("pinned sealed native qualification differs")
        source = verify_bundle(CACHED)
        initial = q.current_inputs()
        basis = cached_basis(source, initial)
        with EvidenceRun(
            Path(output), {"operation": "rl_friction_increment_qualification"}
        ) as run:
            run.result["qualification_checks"] = {}
            source_reference = {
                "path": str(CACHED),
                "manifest_sha256": CACHED_MANIFEST,
                "producer_head": source["qualification"]["head"],
                "fingerprint": source["qualification_fingerprint"],
            }
            write_new(run.path / "cached-native-reference.json", source_reference)
            write_new(run.path / "native-basis-proof.json", basis)
            for name in CACHED_CHECKS:
                for suffix in ("stdout", "stderr"):
                    path = CACHED / (name + "." + suffix)
                    with (run.path / path.name).open("xb") as stream:
                        stream.write(path.read_bytes())
                    if digest(path) != digest(run.path / path.name):
                        raise ValueError("sealed native check log changed")
                run.result["qualification_checks"][name] = {
                    **source["qualification_checks"][name],
                    "execution": "reused_unchanged_sealed_native_inputs",
                    "source_reference": source_reference,
                }
            commands = [
                ("substrate_tests", guarded_tests(SUBSTRATE_TESTS), 180),
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
            for name, argv, timeout in commands:
                run.result["qualification_checks"][name] = {
                    **run_logged(argv, run.path, name, timeout=timeout, cwd=ROOT),
                    "execution": "fresh_no_physics",
                }
            spec.static_inputs(plan)
            final = q.current_inputs()
            if final != initial or spec.shared.current_head(plan) != head:
                raise ValueError("qualification checkout/inputs changed")
            run.result.update(
                status="ENGINEERING_ADMITTED",
                qualification_profile="rl_friction_increment_v1",
                qualification={"clean_head": True, "development": False, "head": head},
                qualification_inputs=initial,
                qualification_fingerprint=q.fingerprint(initial),
                cached_native_qualification=source_reference,
                native_basis_proof=basis,
                canonical_physics_steps=0,
                private_planning_calls=0,
                scientific_attempts=0,
                physics_accounting={
                    "canonical_physics_steps": 0,
                    "canonical_python_integrators_guarded": True,
                    "private_rollouts_expected_this_invocation": False,
                    "private_static_optimizer_invocations": 0,
                    "private_static_admission_execution": "not_run; unchanged historical native qualification referenced",
                },
            )
            q.validate_record(run.result, final)
    # Ordinary unmodified receipt validator checks complete current fingerprint/logs.
    reference = q.validate(output)
    return {
        "head": head,
        "status": "ENGINEERING_ADMITTED",
        "qualification": reference,
        "canonical_physics_steps": 0,
        "private_planning_calls": 0,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    print(qualify(args.output))


if __name__ == "__main__":
    main()
