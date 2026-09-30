"""Source-conditioned headless admission for the pinned upstream MJPC Agent."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = Path(__file__).with_name("sources.lock.json")
EXPECTED_SOURCE_COMMIT = "e00c47a5adb9856af2e0f24231bb3a60d5be23c4"
EXPECTED_MUJOCO_VERSION = "3.3.6"
STRICT_ALIASING_FLAG = "-fno-strict-aliasing"
TASK_XML_RELATIVE = Path("mjpc/mjpc/tasks/quadruped/task_flat.xml")
MODEL_XML_RELATIVE = Path("mjpc/mjpc/tasks/quadruped/go2.xml")
BIAS_NONE = 0
BIAS_AFFINE = 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_source_lock(lock: dict) -> None:
    try:
        source_commit = lock["mjpc"]["commit"]
        mujoco_version = lock["mujoco"]
    except (KeyError, TypeError) as exc:
        raise ValueError("source lock is missing MJPC or MuJoCo identity") from exc
    if source_commit != EXPECTED_SOURCE_COMMIT:
        raise ValueError(f"MJPC source pin drift: {source_commit}")
    if mujoco_version != EXPECTED_MUJOCO_VERSION:
        raise ValueError(f"MuJoCo pin drift: {mujoco_version}")


def validate_source_commit(actual_commit: str, expected_commit: str) -> None:
    if expected_commit != EXPECTED_SOURCE_COMMIT:
        raise ValueError(f"task source pin drift: {expected_commit}")
    if actual_commit != expected_commit:
        raise ValueError(f"MJPC checkout commit mismatch: {actual_commit}")


def validate_actuator_semantics(
    gainprm: list[list[float]],
    biasprm: list[list[float]],
    biastype: list[int],
    expected_count: int = 12,
) -> None:
    if not (len(gainprm) == len(biasprm) == len(biastype) == expected_count):
        raise ValueError("nominal Go2 actuator count drifted")
    for index, (gain, bias, bias_type) in enumerate(
        zip(gainprm, biasprm, biastype, strict=True)
    ):
        if len(gain) < 1 or not math.isclose(gain[0], 60.0, abs_tol=1e-12):
            raise ValueError(f"actuator {index} gainprm[0] drifted from 60")
        if len(bias) < 3 or any(
            not math.isclose(actual, expected, abs_tol=1e-12)
            for actual, expected in zip(bias[:3], (0.0, -60.0, -5.0), strict=True)
        ):
            raise ValueError(f"actuator {index} biasprm drifted from 0 -60 -5")
        if int(bias_type) != BIAS_NONE:
            raise ValueError(f"actuator {index} nominal biastype is no longer non-affine")


def validate_compatibility_metadata(metadata: dict) -> None:
    """Reject evidence that omits any frozen identity or compatibility fact."""
    if metadata.get("source_commit") != EXPECTED_SOURCE_COMMIT:
        raise ValueError("metadata is missing the pinned MJPC source commit")
    if metadata.get("mujoco_version") != EXPECTED_MUJOCO_VERSION:
        raise ValueError("metadata is missing the pinned MuJoCo version")
    flags = metadata.get("compiler_flags", [])
    if STRICT_ALIASING_FLAG not in flags:
        raise ValueError("metadata does not expose -fno-strict-aliasing")
    if metadata.get("task") != "QuadrupedFlat":
        raise ValueError("metadata does not identify upstream QuadrupedFlat")

    compatibility = metadata.get("compatibility", {})
    if compatibility.get("source_validated") is not True:
        raise ValueError("metadata does not record nominal actuator validation")
    if compatibility.get("source_gainprm") != 60:
        raise ValueError("metadata omits the nominal actuator gain")
    if compatibility.get("source_biasprm") != [0, -60, -5]:
        raise ValueError("metadata omits the nominal actuator bias")
    if compatibility.get("source_biastype") != "mjBIAS_NONE":
        raise ValueError("metadata omits the nominal non-affine biastype")
    if compatibility.get("correction") != "actuator biastype=mjBIAS_AFFINE":
        raise ValueError("metadata omits the affine compatibility correction")
    if compatibility.get("correction_scope") != "ephemeral comparator model copy only":
        raise ValueError("metadata does not bound the actuator correction")
    if compatibility.get("canonical_evaluation_plant_modified") is not False:
        raise ValueError("metadata does not preserve the canonical evaluation plant")

    command = metadata.get("command", {})
    for key, expected in (
        ("mode", "Walk"),
        ("gait_switch", "Manual"),
        ("gait", "Trot"),
        ("walk_speed_mps", 1),
        ("walk_turn_radps", 0),
    ):
        if command.get(key) != expected:
            raise ValueError(f"metadata command field {key} drifted")
    argv = command.get("argv")
    if not isinstance(argv, list) or len(argv) < 2:
        raise ValueError("metadata does not record the executed command")

    timing = metadata.get("timing", {})
    for key in (
        "home_hold_simulated_seconds",
        "agent_probe_simulated_seconds",
        "agent_probe_wall_seconds",
        "planning_wall_seconds",
    ):
        value = timing.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"metadata timing field {key} is invalid")

    hold = metadata.get("home_hold", {})
    probe = metadata.get("agent_probe", {})
    for section, key in ((hold, "height_min_m"), (hold, "xy_displacement_m"),
                         (probe, "height_final_m"), (probe, "displacement_xy_m")):
        value = section.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"metadata engineering metric {key} is invalid")
    if metadata.get("nonfinite_status") != "all_checked_values_finite":
        raise ValueError("metadata reports nonfinite or unclassified state values")

    task_model = metadata.get("task_model", {})
    if task_model.get("task_xml_sha256") is None or not re.fullmatch(
        r"[0-9a-f]{64}", task_model["task_xml_sha256"]
    ):
        raise ValueError("metadata task XML identity hash is missing")
    if task_model.get("go2_xml_sha256") is None or not re.fullmatch(
        r"[0-9a-f]{64}", task_model["go2_xml_sha256"]
    ):
        raise ValueError("metadata Go2 model identity hash is missing")


def _git(source_root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source_root), *args], text=True
    ).strip()


def inspect_source(source_root: Path, mujoco_root: Path) -> dict:
    lock = json.loads(LOCK_PATH.read_text())
    validate_source_lock(lock)
    source_root = source_root.resolve(strict=True)
    source_checkout = source_root / "mjpc"
    task_xml = source_root / TASK_XML_RELATIVE
    model_xml = source_root / MODEL_XML_RELATIVE
    if not task_xml.is_file() or not model_xml.is_file():
        raise ValueError("pinned task_flat.xml or go2.xml is missing")
    actual_commit = _git(source_checkout, "rev-parse", "HEAD")
    validate_source_commit(actual_commit, lock["mjpc"]["commit"])
    if _git(source_checkout, "status", "--porcelain"):
        raise ValueError("pinned upstream source checkout is dirty")

    header = mujoco_root / "include/mujoco/mujoco.h"
    library = mujoco_root / "lib/libmujoco.so"
    if not header.is_file() or not library.is_file():
        raise ValueError("MuJoCo SDK header or native library is missing")
    import mujoco

    if mujoco.__version__ != EXPECTED_MUJOCO_VERSION:
        raise ValueError(f"MuJoCo Python version mismatch: {mujoco.__version__}")
    if importlib.metadata.version("numpy") != "2.2.6":
        raise ValueError("NumPy Python distribution version mismatch")
    model = mujoco.MjModel.from_xml_path(str(task_xml))
    if model.nu != 12 or model.nq != 19 or model.nv != 18:
        raise ValueError("pinned QuadrupedFlat model dimensions drifted")
    validate_actuator_semantics(
        model.actuator_gainprm.tolist(),
        model.actuator_biasprm.tolist(),
        model.actuator_biastype.tolist(),
    )

    return {
        "source_commit": actual_commit,
        "task_xml": task_xml,
        "model_xml": model_xml,
        "model": model,
        "mujoco_python_version": mujoco.__version__,
        "numpy_version": importlib.metadata.version("numpy"),
        "mujoco_header": header,
        "mujoco_library": library,
    }


def _cmake_cache(build_dir: Path) -> dict[str, str]:
    cache = build_dir / "CMakeCache.txt"
    if not cache.is_file():
        raise ValueError("CMake cache is missing from the build directory")
    result = {}
    for line in cache.read_text().splitlines():
        if line.startswith("//") or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split("=", 1)
        name = key.split(":", 1)[0]
        result[name] = value
    return result


def inspect_build(build_dir: Path) -> dict:
    build_dir = build_dir.resolve(strict=True)
    compile_db = json.loads((build_dir / "compile_commands.json").read_text())
    records = {}
    for source_name in ("agent.cc", "quadruped.cc", "comparator_probe.cc"):
        matches = [
            row
            for row in compile_db
            if Path(row["file"]).name == source_name
            and ("go2_mjpc_agent" in row["command"]
                 or "go2_mjpc_comparator_probe" in row["command"])
        ]
        if len(matches) != 1:
            raise ValueError(f"compile database does not uniquely bind {source_name}")
        command = matches[0].get("command") or " ".join(matches[0]["arguments"])
        if STRICT_ALIASING_FLAG not in command:
            raise ValueError(f"{source_name} was compiled without {STRICT_ALIASING_FLAG}")
        records[source_name] = command
    cache = _cmake_cache(build_dir)
    compiler_files = list((build_dir / "CMakeFiles").glob("*/CMakeCXXCompiler.cmake"))
    if len(compiler_files) != 1:
        raise ValueError("CMake compiler identity record is missing or ambiguous")
    compiler_text = compiler_files[0].read_text()
    compiler_id = re.search(r'set\(CMAKE_CXX_COMPILER_ID "([^"]+)"\)', compiler_text)
    compiler_version = re.search(
        r'set\(CMAKE_CXX_COMPILER_VERSION "([^"]+)"\)', compiler_text
    )
    if not compiler_id or not compiler_version:
        raise ValueError("CMake compiler identity record is incomplete")
    return {
        "compiler_id": compiler_id.group(1),
        "compiler_version": compiler_version.group(1),
        "compiler_path": cache.get("CMAKE_CXX_COMPILER", "unknown"),
        "build_type": cache.get("CMAKE_BUILD_TYPE", "unknown"),
        "flags": [STRICT_ALIASING_FLAG],
        "strict_aliasing_flag_verified": True,
        "relevant_compile_commands": records,
        "compile_commands_sha256": sha256(build_dir / "compile_commands.json"),
    }


def _write_new(path: Path, data: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def run_admission(
    source_root: Path, mujoco_root: Path, build_dir: Path, binary: Path, output: Path
) -> dict:
    source = inspect_source(source_root, mujoco_root)
    build = inspect_build(build_dir)
    binary = binary.resolve(strict=True)
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"admission output already exists: {output}")
    output.mkdir(parents=True)
    command = [str(binary), str(source["task_xml"])]
    started = {
        "task_branch": subprocess.check_output(
            ["git", "-C", str(ROOT), "branch", "--show-current"], text=True
        ).strip(),
        "task_head": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_commit": source["source_commit"],
        "command": command,
        "start_time_unix": time.time(),
    }
    _write_new(output / "started.json", json.dumps(started, indent=2) + "\n")
    began = time.monotonic()
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=600, check=False
        )
        _write_new(output / "stdout.log", completed.stdout)
        _write_new(output / "stderr.log", completed.stderr)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        _write_new(output / "stdout.log", stdout)
        _write_new(output / "stderr.log", stderr)
        _write_new(
            output / "terminal.json",
            json.dumps({"status": "TIMEOUT", "timeout_seconds": 600}, indent=2)
            + "\n",
        )
        raise ValueError("headless comparator admission exceeded 600 seconds") from exc

    elapsed = time.monotonic() - began
    terminal = {
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "return_code": completed.returncode,
        "wall_seconds": elapsed,
    }
    _write_new(output / "terminal.json", json.dumps(terminal, indent=2) + "\n")
    if completed.returncode != 0:
        raise ValueError(
            f"comparator probe returned {completed.returncode}; inspect preserved raw output"
        )

    probe = json.loads(completed.stdout)
    metadata = dict(probe)
    metadata["schema_version"] = 1
    metadata["source"] = {
        "repository": "https://github.com/johnzhang3/mujoco_mpc.git",
        "commit": source["source_commit"],
    }
    metadata["mujoco_version"] = probe.get("mujoco_version")
    metadata["task_model"] = {
        "task": "QuadrupedFlat",
        "task_xml": TASK_XML_RELATIVE.as_posix(),
        "task_xml_sha256": sha256(source["task_xml"]),
        "go2_xml": MODEL_XML_RELATIVE.as_posix(),
        "go2_xml_sha256": sha256(source["model_xml"]),
        "nq": source["model"].nq,
        "nv": source["model"].nv,
        "nu": source["model"].nu,
        "plant_timestep_s": source["model"].opt.timestep,
    }
    metadata["python_resources"] = {
        "mujoco": source["mujoco_python_version"],
        "numpy": source["numpy_version"],
    }
    metadata["sdk"] = {
        "header": str(source["mujoco_header"]),
        "header_sha256": sha256(source["mujoco_header"]),
        "library": str(source["mujoco_library"]),
        "library_sha256": sha256(source["mujoco_library"]),
    }
    metadata["build"] = {
        "compiler": f"{build['compiler_id']} {build['compiler_version']}",
        "compiler_path": build["compiler_path"],
        "build_type": build["build_type"],
        "flags": build["flags"],
        "strict_aliasing_flag_verified": build["strict_aliasing_flag_verified"],
        "relevant_compile_commands": build["relevant_compile_commands"],
        "compile_commands_sha256": build["compile_commands_sha256"],
    }
    metadata["command"]["argv"] = command
    metadata["command"]["working_directory"] = str(ROOT)
    metadata["engineering_status"] = "PASS"
    metadata["admission_wall_seconds"] = elapsed
    validate_compatibility_metadata(metadata)
    _write_new(output / "metadata.json", json.dumps(metadata, indent=2) + "\n")
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--mujoco-root", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        metadata = run_admission(
            args.source_root,
            args.mujoco_root,
            args.build_dir,
            args.binary,
            args.output,
        )
    except Exception as exc:  # Preserve concise machine-readable caller behavior.
        print(f"MJPC comparator admission failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": metadata["engineering_status"], "task_model": metadata["task_model"],
                      "output": str(args.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
