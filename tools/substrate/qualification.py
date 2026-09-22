"""Content-bound qualification receipts; exact execution identity stays separate."""

from pathlib import Path
import hashlib
import json
import subprocess
import sys
import re

from .integrity import digest, verify_bundle
from .environment import verify_environment
from .build_identity import verify as verify_build

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_CHECKS = {
    "controller_configure",
    "controller_build",
    "controller_tests",
    "substrate_tests",
    "preflight_tests",
    "tooling_tests",
    "quality",
    "diff_check",
}


def tracked_inputs(root=ROOT):
    """Include code, tests, build plans and assets; exclude prose and task metadata."""
    names = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        .decode()
        .split("\0")
    )
    prefixes = ("tools/", "example/cpp/", "simulate/", "unitree_robots/")
    return {
        name: digest(root / name)
        for name in sorted(names)
        if name
        and (name.startswith(prefixes) or name == "pyproject.toml")
        and not name.startswith(("tools/substrate/tasks/", "example/cpp/experiments/"))
        and Path(name).suffix.lower() not in (".md", ".rst")
        and (root / name).is_file()
    }


def current_inputs():
    binary = ROOT / ".substrate/headless-reliable/go2_mjpc_admit"
    libraries = {}
    for executable in (binary, Path(sys.executable).resolve()):
        linkage = subprocess.check_output(["ldd", str(executable)], text=True)
        for name in re.findall(r"(?:=>\s*)?(/[^\s]+)", linkage):
            path = Path(name).resolve()
            if path.is_file():
                libraries[str(path)] = digest(path)
    cpu = {
        line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip()
        for line in Path("/proc/cpuinfo").read_text().splitlines()
        if ":" in line
        and line.split(":", 1)[0].strip()
        in ("vendor_id", "model name", "microcode", "flags")
    }
    return {
        "schema": 1,
        "tracked_files": tracked_inputs(),
        "runtime": verify_environment(),
        "interpreter_sha256": digest(Path(sys.executable).resolve()),
        "checkpoint_sha256": digest(ROOT / ".substrate/rl/policy.pt"),
        "native_build": verify_build(binary),
        "native_binary_sha256": digest(binary),
        "linked_libraries": libraries,
        "cpu_identity": cpu,
    }


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def validate_record(record, actual):
    q = record.get("qualification", {})
    if q.get("clean_head") is not True or q.get("development") is not False:
        raise ValueError("qualification must be clean and non-development")
    checks = record.get("qualification_checks", {})
    if set(checks) != REQUIRED_CHECKS or any(
        type(item.get("returncode")) is not int or item["returncode"] != 0
        for item in checks.values()
    ):
        raise ValueError("qualification required checks missing or not passing")
    if record.get("qualification_inputs") != actual:
        raise ValueError("qualification inputs changed or receipt predates binding")
    if record.get("qualification_fingerprint") != fingerprint(actual):
        raise ValueError("qualification fingerprint mismatch")


def validate(directory):
    directory = Path(directory).resolve()
    record = verify_bundle(directory)
    validate_record(record, current_inputs())
    for name in REQUIRED_CHECKS:
        for suffix in ("stdout", "stderr"):
            if not (directory / f"{name}.{suffix}").is_file():
                raise ValueError("qualification check log missing")
    return {
        "path": str(directory),
        "manifest_sha256": digest(directory / "manifest.json"),
        "producer_head": record["qualification"]["head"],
        "fingerprint": record["qualification_fingerprint"],
    }


def validate_reference(reference):
    if not isinstance(reference, dict) or not reference.get("path"):
        raise ValueError("bound qualification receipt required")
    current = validate(reference["path"])
    if current != reference:
        raise ValueError("qualification reference mismatch")
    return current
