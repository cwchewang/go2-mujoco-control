"""Matched retain/zero incoming-FD-warmstart contrast; no canonical integration."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from . import mjpc_dedup_observation as base
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

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "research/mjpc-fd-warmstart-observation-20261004"
DESIGN = {
    **base.DESIGN,
    "modes": ["retain", "zero"],
    "optimizer_calls_max": 8,
    "private_derived_upper": 19616,
    "private_reserved_max": 32768,
    "intervention": "qacc_warmstart zero only at incoming FD call; retain rollout warmstarts",
    "binary": "same archived fixed controller and same sealed shim in both arms",
}
PARENT_QUAL = (
    ROOT.parent
    / "faithful-dedup-observation/_runs/mjpc_faithful_dedup_qualification_20261004_v2"
)
PARENT_PIN = "30bd091bfa733021d205f118fc366c4746dc3da30a7cb8a74146b7f3577e5980"


def configure():
    base.BRANCH = BRANCH
    base.DESIGN = DESIGN


def loader_args(binary, sidecar):
    argv, task = native_runtime.argv(binary, sidecar)
    root = Path(sidecar).parent
    return [
        *argv[:-1],
        "--preload",
        str(root / "lib/libgo2_fd_warmstart.so"),
        argv[-1],
    ], task


def seed_records(path, mode, calls):
    values = [strict_json(s) for s in Path(path).read_text().splitlines()]
    if values[0]["mode"] != mode or len(values) != calls + 1:
        raise ValueError("warmstart intervention trace count/mode mismatch")
    entries = values[1:]
    if {r["index"] for r in entries} != set(range(1, calls + 1)):
        raise ValueError("interposed FD call indexes differ")
    for row in entries:
        if row["end_ns"] < row["start_ns"]:
            raise ValueError("invalid interception interval")
        if mode == "zero" and not row["effective_zero"]:
            raise ValueError("incoming warmstart was not cleared")
        if mode == "retain" and row["before_hash"] != row["effective_hash"]:
            raise ValueError("retain arm altered warmstart")
    return values


def package(binary, target, root, provenance):
    if digest(PARENT_QUAL / "manifest.json") != PARENT_PIN:
        raise ValueError("parent qualification pin changed")
    verify_manifest(PARENT_QUAL)
    value = native_runtime.package(binary, target, root, provenance)
    target = Path(target)
    source = ROOT / "tools/substrate/native/fd_warmstart_shim.c"
    include = (
        ROOT / ".substrate/venv-reliable/lib/python3.10/site-packages/mujoco/include"
    )
    shim = target / "lib/libgo2_fd_warmstart.so"
    command = [
        "/usr/bin/cc",
        "-std=c11",
        "-O2",
        "-shared",
        "-fPIC",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I" + str(include),
        "-MMD",
        "-MF",
        str(target / "shim-deps.d"),
        str(source),
        "-ldl",
        "-o",
        str(shim),
    ]
    built = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if built.returncode:
        raise ValueError("warmstart shim build failed: " + built.stderr)
    needed = subprocess.check_output(["readelf", "-d", str(shim)], text=True)
    if any(
        "NEEDED" in line and "libc.so.6" not in line for line in needed.splitlines()
    ):
        raise ValueError("shim requires unexpected libraries")
    deps = (
        (target / "shim-deps.d")
        .read_text()
        .replace("\\\n", " ")
        .split(":", 1)[1]
        .split()
    )
    write_new(
        target / "warmstart-build.json",
        {
            "command": command,
            "compiler_sha256": digest(Path("/usr/bin/cc").resolve()),
            "source_sha256": digest(source),
            "header_dependencies": {
                str(Path(p).resolve()): digest(Path(p)) for p in deps
            },
            "shim_sha256": digest(shim),
            "parent_qualification_manifest": PARENT_PIN,
            "native_change": "same controller; shared shim intercepts only mjd_transitionFD entry; mode controls only zero loop",
        },
    )
    value["libraries"]["libgo2_fd_warmstart.so"] = "lib/libgo2_fd_warmstart.so"
    value["files"] = {
        p.relative_to(target).as_posix(): digest(p)
        for p in sorted(target.rglob("*"))
        if p.is_file() and p.name != native_runtime.SIDECAR
    }
    value["fd_warmstart_shim"] = {
        "path": "lib/libgo2_fd_warmstart.so",
        "sha256": digest(shim),
    }
    # This is still the new unsealed package, not a historical runtime.
    (target / native_runtime.SIDECAR).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n"
    )
    sidecar = target / native_runtime.SIDECAR
    native_runtime.verify(target / Path(binary).name, sidecar)

    tests = target.parent / "shim-contract"
    tests.mkdir()
    fake = tests / "libfakefd.so"
    executable = tests / "shim_contract"
    for cmd in (
        [
            "/usr/bin/cc",
            "-shared",
            "-fPIC",
            "-I" + str(include),
            str(ROOT / "tools/substrate/native/fd_warmstart_fake.c"),
            "-o",
            str(fake),
        ],
        [
            "/usr/bin/cc",
            "-I" + str(include),
            str(ROOT / "tools/substrate/native/fd_warmstart_contract.c"),
            "-L" + str(tests),
            "-lfakefd",
            "-o",
            str(executable),
        ],
    ):
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
    loader = target / value["loader"]
    evidence = []
    for mode in ("retain", "zero"):
        fake_log = tests / (mode + ".jsonl")
        env = os.environ.copy()
        for k in ("LD_PRELOAD", "LD_AUDIT", "LD_LIBRARY_PATH"):
            env.pop(k, None)
        env.update(GO2_FD_WARMSTART_MODE=mode, GO2_FD_WARMSTART_LOG=str(fake_log))
        cmd = [
            str(loader),
            "--library-path",
            str(tests) + ":" + str(target / "lib"),
            "--preload",
            str(shim),
            str(executable),
        ]
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
        if p.returncode or p.stdout or p.stderr:
            raise ValueError("zero-integration shim contract failed")
        seed_records(fake_log, mode, 1)
        # New actual-controller readiness, constructor/reset only: zero FD/optimizer calls.
        log = tests / (mode + "-ready-seeds.jsonl")
        args, task = loader_args(target / Path(binary).name, sidecar)
        env.update(GO2_FD_WARMSTART_LOG=str(log))

        def popen(argv, **kwargs):
            return subprocess.Popen(argv, env=env, **kwargs)

        transport = NativeTransport(
            [
                *args,
                str(task),
                "fixed",
                str(target / value["canonical_xml"]),
                str(tests / (mode + "-ready.predictions.jsonl")),
            ],
            popen=popen,
            stderr_log_path=tests / (mode + "-ready.stderr"),
        )
        try:
            ready = transport.read_json(10)
            sequence.d.candidate_contract(ready)
            reset = transport.request("reset", 10)
            if reset != {"ok": True, "reset": True}:
                raise ValueError("ready reset failed")
            loaded = native_runtime.loaded_libraries(transport.process.pid, sidecar)
        finally:
            transport.close()
        if transport.diagnostics()["stderr_bytes"]:
            raise ValueError("readiness stderr")
        seeds = seed_records(log, mode, 0)
        if Path(seeds[0]["delegate"]).resolve() != target / "lib/libmujoco.so.3.3.6":
            raise ValueError("FD delegate outside sealed MuJoCo")
        evidence.append(
            {
                "mode": mode,
                "ready": ready,
                "reset": reset,
                "loaded_libraries": loaded,
                "optimizer_calls": 0,
                "canonical_steps": 0,
            }
        )
    write_new(
        tests / "RESULT.json",
        {
            "fake_forwarding_contracts": 2,
            "actual_zero_readiness": evidence,
            "real_optimizer_calls": 0,
            "canonical_steps": 0,
        },
    )
    return value


def prepare(output):
    configure()
    extra = [
        (
            "warmstart_python_contracts",
            [
                sys.executable,
                "-B",
                "-m",
                "unittest",
                "tools.substrate.test_mjpc_warmstart_observation",
                "-v",
            ],
        )
    ]
    return base.prepare(output, runtime_packager=package, extra_checks=extra)


def precheck(packet, output):
    configure()
    result = base.precheck(packet, output)
    runtime = result[0]["runtime"]
    if runtime.get("fd_warmstart_shim", {}).get("sha256") != digest(
        result[2].parent / "lib/libgo2_fd_warmstart.so"
    ):
        raise ValueError("warmstart shim binding changed")
    return result


def execute(packet_path, output, science, execution):
    configure()
    with experiment_lock(), zero_step_guard(), wall_deadline(300):
        packet, binary, sidecar, preflight = precheck(packet_path, output)
        reviews = [
            base.review(science, "science", preflight),
            base.review(execution, "execution", preflight),
        ]
        if reviews[0]["reviewer"] == reviews[1]["reviewer"]:
            raise ValueError("reviewers not independent")
        with EvidenceRun(output, {"head": preflight["head"], "design": DESIGN}) as run:
            write_new(run.path / "preflight.json", preflight)
            write_new(run.path / "reviews.json", reviews)
            write_new(
                run.path / "campaign-reservation.json",
                {
                    "calls_max": 8,
                    "private_reserved_max": 32768,
                    "canonical_steps": 0,
                    "authorization": "direct 2026-10-04 user continuation; new small matched FD-warmstart contrast",
                    "source_thread": "01a0f08f-d223-7240-813b-ee93267b700d",
                },
            )
            run.result.update(
                scope="fd_warmstart_observation", capability_status="STARTED"
            )
            results = []
            try:
                args, task = loader_args(binary, sidecar)
                for mode in ("retain", "zero"):
                    for repeat in (1, 2):
                        sub = run.path / (mode + "_repeat" + str(repeat))

                        def popen(argv, **kwargs):
                            if argv[0] != str(binary) or argv[2] != "fixed":
                                raise ValueError("unbound native launch")
                            env = kwargs["env"]
                            for key in ("LD_PRELOAD", "LD_AUDIT", "LD_LIBRARY_PATH"):
                                env.pop(key, None)
                            env.update(
                                GO2_FD_WARMSTART_MODE=mode,
                                GO2_FD_WARMSTART_LOG=str(sub / "warmstart-seeds.jsonl"),
                            )
                            return subprocess.Popen(
                                [
                                    *args,
                                    str(task),
                                    "fixed",
                                    str(
                                        sidecar.parent
                                        / packet["runtime"]["canonical_xml"]
                                    ),
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
                                    write_new(path, loaded)
                                return response

                        result = sequence.run_sequence_trial(
                            {"variant": "fixed", "repeat": repeat},
                            packet["source"],
                            {"fixed": binary},
                            {"fixed": packet["native_build_provenance"]},
                            sub,
                            popen=popen,
                            native_transport=BoundTransport,
                        )
                        seeds = seed_records(sub / "warmstart-seeds.jsonl", mode, 72)
                        if (
                            Path(seeds[0]["delegate"]).resolve()
                            != sidecar.parent / "lib/libmujoco.so.3.3.6"
                        ):
                            raise ValueError("FD delegate identity differs")
                        result["warmstart_mode"] = mode
                        write_new(sub / "result.json", result)
                        results.append(result)
                counts = accounting(run.path)
                if (
                    not counts["accounting_complete"]
                    or counts["completed_optimizer_calls"] != 8
                    or counts["private_accounted_upper"] != 19616
                    or counts["private_reserved"] != 32768
                ):
                    raise ValueError("matched campaign accounting mismatch")
                write_new(
                    run.path / "RESULT.json",
                    {
                        **preflight,
                        "status": "OBSERVATION_COMPLETE",
                        "design": DESIGN,
                        "results": results,
                        "accounting": counts,
                    },
                )
                verify_manifest(base.SOURCE)
                native_runtime.verify(binary, sidecar)
                if (
                    packet["inputs"] != base.inputs()
                    or base.identity()["head"] != packet["head"]
                ):
                    raise ValueError("source changed after observation")
                run.result.update(
                    status="ENGINEERING_ADMITTED",
                    optimizer_calls_executed=8,
                    canonical_integration_steps=0,
                )
            finally:
                counts = accounting(run.path)
                write_new(run.path / "accounting.json", counts)
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


def accounting(root):
    # Reuse the reviewed fixed-counter failure parser without altering native evidence.
    total = {
        k: 0
        for k in (
            "reserved_optimizer_calls",
            "completed_optimizer_calls",
            "private_reserved",
            "private_accounted_upper",
            "unverified_reserved_upper",
        )
    }
    errors = []
    for mode in ("retain", "zero"):
        counts = base.partial_accounting(root, pattern=mode + "_repeat[12]")
        for k in total:
            total[k] += counts[k]
        errors += counts["accounting_errors"]
    return {
        **total,
        "accounting_complete": total["reserved_optimizer_calls"]
        == total["completed_optimizer_calls"]
        and not errors,
        "accounting_errors": errors,
        "canonical_integration_steps": 0,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("prepare", "precheck", "execute"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--packet", type=Path)
    p.add_argument("--science", type=Path)
    p.add_argument("--execution", type=Path)
    a = p.parse_args()
    if a.action == "prepare":
        v = prepare(a.output)
    elif a.action == "precheck":
        with experiment_lock(), zero_step_guard():
            v = precheck(a.packet, a.output)[3]
    else:
        v = execute(a.packet, a.output, a.science, a.execution)
    print(json.dumps(v, sort_keys=True))


if __name__ == "__main__":
    main()
