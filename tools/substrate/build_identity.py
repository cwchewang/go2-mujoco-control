"""Bind an executable to the exact local build inputs, not merely a git label."""

import json
import shlex
from pathlib import Path
import subprocess
from .integrity import digest, strict_json

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "tools/substrate/sources.lock.json"


def git_identity(directory, expected):
    directory = Path(directory).resolve()
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=directory, text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=directory
    )
    if head != expected or dirty:
        raise ValueError("dirty or incorrect dependency: " + str(directory))
    names = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=directory)
        .decode()
        .split("\0")
    )
    files = {
        name: digest(directory / name)
        for name in names
        if name and (directory / name).is_file()
    }
    return {"head": head, "files": files}


def cache_values(build):
    values = {}
    for line in (Path(build) / "CMakeCache.txt").read_text().splitlines():
        if line and not line.startswith(("#", "//")) and ":" in line and "=" in line:
            key, rest = line.split(":", 1)
            values[key] = rest.split("=", 1)[1]
    return values


def compilation_files(build):
    """Bind generated translation units and actual Ninja-discovered dependencies."""
    build = Path(build).resolve()
    commands = strict_json((build / "compile_commands.json").read_text())
    sources = {}
    planned = {}
    for entry in commands:
        path = Path(entry["file"])
        if not path.is_absolute():
            path = Path(entry["directory"]) / path
        path = path.resolve(strict=True)
        sources[str(path)] = digest(path)
        if path.is_relative_to(ROOT / "tools/substrate/native") or path.is_relative_to(
            build / "generated"
        ):
            argv = entry.get("arguments") or shlex.split(entry["command"])
            cleaned = []
            skip = False
            for arg in argv:
                if skip:
                    skip = False
                    continue
                if arg in ("-o", "-MF", "-MT", "-MQ"):
                    skip = True
                elif arg not in ("-c", "-MD", "-MMD", "-MP"):
                    cleaned.append(arg)
            dependency_text = subprocess.check_output(
                cleaned + ["-M", "-MT", "identity", "-MF", "-"],
                cwd=entry["directory"],
                text=True,
                timeout=30,
            )
            names = shlex.split(
                dependency_text.split(":", 1)[1].replace(chr(92) + chr(10), " ")
            )
            for name in names:
                dependency = Path(name)
                if not dependency.is_absolute():
                    dependency = Path(entry["directory"]) / dependency
                dependency = dependency.resolve(strict=True)
                planned[str(dependency)] = digest(dependency)
    dependencies = {}
    output = subprocess.check_output(
        ["ninja", "-C", str(build), "-t", "deps"], text=True
    )
    for line in output.splitlines():
        if not line.startswith("    "):
            continue
        path = Path(line.strip())
        if not path.is_absolute():
            path = build / path
        path = path.resolve(strict=True)
        dependencies[str(path)] = digest(path)
    return {
        "translation_units": sources,
        "planned_native_dependencies": planned,
        "actual_dependencies": dependencies,
    }


def inputs(build):
    build = Path(build).resolve()
    cache = cache_values(build)
    lock = strict_json(LOCK.read_text())
    source = Path(cache["MJPC_SOURCE_DIR"])
    abseil = cache.get("FETCHCONTENT_SOURCE_DIR_ABSEIL") or str(
        build / "_deps/abseil-src"
    )
    source_files = {
        str(p.relative_to(ROOT)): digest(p)
        for p in sorted((ROOT / "tools/substrate/native").rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }
    # Include MuJoCo headers, not only its runtime library.
    headers = {
        str(p.relative_to(Path(cache["MUJOCO_INCLUDE_DIR"]))): digest(p)
        for p in sorted(Path(cache["MUJOCO_INCLUDE_DIR"]).rglob("*.h"))
    }
    compiler = Path(cache["CMAKE_CXX_COMPILER"]).resolve()
    return {
        "sources": source_files,
        "compilation_files": compilation_files(build),
        "mjpc": git_identity(source, lock["mjpc"]["commit"]),
        "abseil": git_identity(abseil, lock["abseil_commit"]),
        "mujoco_headers": headers,
        "mujoco_library": digest(Path(cache["MUJOCO_LIBRARY"]).resolve()),
        "compiler": {"path": str(compiler), "sha256": digest(compiler)},
        "cache_sha256": digest(build / "CMakeCache.txt"),
        "ninja_sha256": digest(build / "build.ninja"),
        "compile_commands_sha256": digest(build / "compile_commands.json"),
        "lock_sha256": digest(LOCK),
    }


def _seal_binary(build, before, binary_name, identity_name):
    build = Path(build).resolve()
    after = inputs(build)

    def planned(value):
        result = dict(value)
        compilation = dict(result.get("compilation_files", {}))
        compilation.pop("actual_dependencies", None)
        result["compilation_files"] = compilation
        return result

    previous_dependencies = before.get("compilation_files", {}).get(
        "actual_dependencies", {}
    )
    if planned(before) != planned(after) or any(
        digest(Path(path)) != expected
        for path, expected in previous_dependencies.items()
    ):
        raise ValueError("build inputs changed during compilation")
    binary = build / binary_name
    result = {
        "schema": 1,
        "binary": binary_name,
        "inputs": after,
        "binary_sha256": digest(binary),
    }
    path = build / identity_name
    # Build cache is mutable; raw evidence copies of identities are immutable.
    tmp = path.with_suffix(".new")
    tmp.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    tmp.replace(path)
    return result


def seal(build, before):
    return _seal_binary(build, before, "go2_mjpc_admit", "build-identity.json")


def seal_controller(build, before):
    return _seal_binary(
        build,
        before,
        "go2_mjpc_controller",
        "controller-build-identity.json",
    )


def _verify_binary(binary, identity_name, expected_name):
    binary = Path(binary).resolve()
    identity = strict_json((binary.parent / identity_name).read_text())
    if (
        identity.get("schema") != 1
        or identity.get("binary") not in (None, expected_name)
        or identity["binary_sha256"] != digest(binary)
    ):
        raise ValueError("binary does not match build identity")
    if identity["inputs"] != inputs(binary.parent):
        raise ValueError("stale build: inputs changed")
    return identity


def verify(binary):
    return _verify_binary(binary, "build-identity.json", "go2_mjpc_admit")


def verify_controller(binary):
    return _verify_binary(
        binary,
        "controller-build-identity.json",
        "go2_mjpc_controller",
    )
