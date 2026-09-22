"""One offline engineering qualification command; never starts a live controller."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from .admit import admit, source_manifest
from .integrity import EvidenceRun, experiment_lock, run_logged
from .environment import verify_environment

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--development",
        action="store_true",
        help="record dirty engineering work explicitly; final qualification requires clean HEAD",
    )
    args = p.parse_args()
    try:
        with experiment_lock(), EvidenceRun(args.output, {"argv": sys.argv}) as run:
            verify_environment()
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip()
            before = subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            )
            if before and not args.development:
                raise ValueError("final qualification requires a clean worktree")
            source_before = source_manifest()
            diff_before = subprocess.check_output(
                ["git", "diff", "--binary", "HEAD"], cwd=ROOT
            )
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
                    [
                        sys.executable,
                        "-m",
                        "unittest",
                        "tools.substrate.test_substrate",
                        "tools.substrate.test_native_boundary",
                        "tools.substrate.test_reliability",
                        "tools.substrate.test_policy_runtime",
                        "tools.substrate.test_clock",
                        "-v",
                    ],
                    120,
                ),
                (
                    "preflight_tests",
                    [
                        sys.executable,
                        "-m",
                        "unittest",
                        "tools.research.test_preflight",
                        "tools.research.test_preflight_integration",
                        "-v",
                    ],
                    120,
                ),
                (
                    "dispatcher_tests",
                    [
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tools/tests",
                        "-p",
                        "test_atlas_*.py",
                    ],
                    120,
                ),
                ("hygiene", [sys.executable, "tools/check_repo_hygiene.py"], 120),
                ("diff_check", ["git", "diff", "--check"], 30),
            ]
            run.result["qualification_checks"] = {}
            for name, argv, timeout in commands:
                run.result["qualification_checks"][name] = run_logged(
                    argv, run.path, name, timeout, ROOT
                )
            admit(
                run,
                ROOT / ".substrate/rl/policy.pt",
                ROOT / ".substrate/headless-reliable/go2_mjpc_admit",
            )
            after = subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            )
            final_head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip()
            diff_after = subprocess.check_output(
                ["git", "diff", "--binary", "HEAD"], cwd=ROOT
            )
            if (
                before != after
                or head != final_head
                or source_before != source_manifest()
                or diff_before != diff_after
            ):
                raise ValueError("checkout changed during qualification")
            run.result["qualification"] = {
                "clean_head": not before,
                "development": args.development,
                "head": head,
            }
    except (Exception, KeyboardInterrupt) as exc:
        print(
            json.dumps(
                {"status": "FAILED", "reason": type(exc).__name__ + ": " + str(exc)}
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "ENGINEERING_ADMITTED",
                "clean_head": not before,
                "capability_status": "NOT_RUN",
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
