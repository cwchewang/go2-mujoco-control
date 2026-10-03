"""Reuse sealed floor0 smoke evidence without launching a native controller."""

import ast
import copy
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from . import native_runtime, qualification
from .fd_duplicate_diagnostic import build_identity
from .integrity import digest, strict_json, verify_bundle

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "mjpc_floor_registration_sustained_12s_v1"
PRODUCER = "tools/substrate/qualify_mjpc_diagnostic.py"
CONSUMER = "tools/substrate/mjpc_floor_registration_diagnostic.py"
# These files affect qualification/reuse checks, not the executed smoke.
# Fresh qualification still fingerprints their complete current contents.
CHECK_ONLY_FILES = {
    "tools/substrate/mjpc_smoke_reuse.py",
    "tools/substrate/test_mjpc_smoke_reuse.py",
    "tools/substrate/test_mjpc_floor_registration_diagnostic.py",
}
PROJECTED_FUNCTIONS = {
    PRODUCER: {"qualify", "main"},
    CONSUMER: {"validate_qualification_claim"},
}
SMOKE_LOGS = (
    "native-smoke-accounting.json",
    "native-smoke-fd-trace.jsonl",
    "native-smoke-predictions.jsonl",
    "native-smoke.stderr",
)


def source_projection(source, name):
    """Keep smoke and capture code; remove only qualification/receipt readers."""
    tree = ast.parse(source)
    ignored = PROJECTED_FUNCTIONS[name]
    found = {
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if not ignored.issubset(found):
        raise ValueError("smoke projection expected function missing: " + name)
    tree.body = [
        node for node in tree.body
        if not (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in ignored
        )
    ]
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()


def native_smoke_inputs(inputs, source_head=None, root=ROOT):
    """Compare every input except tested receipt/qualification-only changes."""
    result = copy.deepcopy(inputs)
    tracked = result["tracked_files"]
    for name in CHECK_ONLY_FILES:
        tracked.pop(name, None)
    for name in PROJECTED_FUNCTIONS:
        if name not in tracked:
            raise ValueError("smoke source input missing: " + name)
        if source_head is None:
            raw = (root / name).read_bytes()
        else:
            raw = subprocess.check_output(
                ["git", "show", source_head + ":" + name], cwd=root
            )
        if hashlib.sha256(raw).hexdigest() != tracked[name]:
            raise ValueError("smoke source hash differs: " + name)
        tracked[name] = source_projection(raw.decode(), name)
    return result


def _differences(left, right, path=""):
    if isinstance(left, dict) and isinstance(right, dict):
        out = []
        for key in sorted(set(left) | set(right)):
            out.extend(_differences(left.get(key), right.get(key), path + "/" + key))
        return out
    return [] if left == right else [path]


def matching_native_inputs(source_record, current):
    retained = native_smoke_inputs(
        source_record["qualification_inputs"], source_record["qualification"]["head"]
    )
    actual = native_smoke_inputs(current)
    changes = _differences(retained, actual)
    if changes:
        raise ValueError("retained smoke inputs changed: " + ", ".join(changes))
    return qualification.fingerprint(actual)


def validate_source_record(record):
    """An original one-call receipt is required; reuse chains are rejected."""
    qualification.validate_record(record, record.get("qualification_inputs"))
    physics = record.get("physics_accounting", {})
    expected = {
        "policy_id": 1,
        "fd_call_count": 36,
        "fd_step_upper_bound_count": 1752,
        "rollout_mj_step_count": 700,
        "private_step_upper_bound_reserved": 4096,
        "private_step_limit": 614400,
    }
    if (
        record.get("qualification_profile") != PROFILE
        or type(record.get("private_engineering_optimizer_calls")) is not int
        or record["private_engineering_optimizer_calls"] != 1
        or record.get("reused_private_engineering_optimizer_calls", 0) != 0
        or record.get("smoke_provenance") is not None
        or record.get("canonical_physics_steps") != 0
        or record.get("scientific_attempts") != 0
        or physics.get("canonical_steps") != 0
        or physics.get("scientific_attempts") != 0
        or type(physics.get("optimizer_calls")) is not int
        or physics["optimizer_calls"] != 1
        or type(physics.get("private_step_upper_bound_max")) is not int
        or physics["private_step_upper_bound_max"] != 4096
        or any(
            type(physics.get("accounting", {}).get(key)) is not int
            or physics["accounting"][key] != value
            for key, value in expected.items()
        )
        or physics.get("private_model_delta") != {
            "field": "private_task_flat.floor.pos.z",
            "from_m": -0.01,
            "to_m": 0.0,
            "other_xml_values_equal": True,
        }
    ):
        raise ValueError("retained smoke accounting/profile is invalid")
    binary = record["qualification_inputs"].get("fd_fixed_controller", {})
    if (
        physics.get("binary_sha256") != binary.get("binary_sha256")
        or physics.get("binary_build_identity") != binary.get("build_identity")
    ):
        raise ValueError("retained smoke consumer identity is inconsistent")
    return physics


def load_source(directory, expected_manifest):
    directory = Path(directory).resolve(strict=True)
    if (
        not isinstance(expected_manifest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest)
        or digest(directory / "manifest.json") != expected_manifest
    ):
        raise ValueError("retained smoke manifest pin differs")
    record = verify_bundle(directory)
    physics = validate_source_record(record)
    for name in qualification.REQUIRED_CHECKS:
        for suffix in ("stdout", "stderr"):
            if not (directory / f"{name}.{suffix}").is_file():
                raise ValueError("retained qualification log missing")
    if strict_json((directory / SMOKE_LOGS[0]).read_text()) != physics:
        raise ValueError("retained smoke accounting log differs")
    rt = directory / "consumer-runtime"
    side = rt / native_runtime.SIDECAR
    binary = rt / physics["runtime_identity"]["binary"]
    identity = native_runtime.verify(binary, side)
    if (
        digest(binary) != physics["binary_sha256"]
        or digest(side) != physics["runtime_identity_sha256"]
        or identity != physics["runtime_identity"]
        or (directory / "native-smoke.stderr").stat().st_size != 0
    ):
        raise ValueError("retained smoke runtime/warning identity differs")
    traces = [
        strict_json(line)
        for line in (directory / "native-smoke-fd-trace.jsonl").read_text().splitlines()
    ]
    predictions = [
        strict_json(line)
        for line in (directory / "native-smoke-predictions.jsonl").read_text().splitlines()
    ]
    if (
        len(traces) != 1
        or traces[0].get("call_index") != 1
        or traces[0].get("index_count") != 36
        or [e.get("t") for e in traces[0].get("events", [])] != list(range(36))
        or any(e.get("call_index") != 1 for e in traces[0].get("events", []))
        or len(predictions) != 1
        or predictions[0].get("policy_id") != 1
        or predictions[0].get("private_accounting") != {
            "fd_call_count": 36,
            "fd_step_upper_bound_count": 1752,
            "rollout_mj_step_count": 700,
            "reserved_step_upper_bound": 4096,
        }
    ):
        raise ValueError("retained smoke must contain exactly one accounted call")
    reference = {
        "path": str(directory),
        "manifest_sha256": expected_manifest,
        "producer_head": record["qualification"]["head"],
        "fingerprint": record["qualification_fingerprint"],
    }
    return directory, record, physics, reference


def _package_current(directory, current):
    from .mjpc_floor_registration_diagnostic import R4_PREP, assert_only_floor_z_changed

    binary = ROOT / ".substrate/headless-reliable/go2_mjpc_controller_fd_fixed"
    identity = build_identity(binary, "fixed")
    if current["fd_fixed_controller"] != {
        "binary_sha256": digest(binary), "build_identity": identity
    }:
        raise ValueError("current consumer changed while preparing retained smoke")
    rt = Path(directory) / "consumer-runtime"
    native_runtime.package(binary, rt, ROOT, identity)
    task = rt / "source/mjpc/tasks/quadruped/task_flat.xml"
    text, count = re.subn(
        r'(<geom\b[^>]*\bname="floor"[^>]*\bpos="[^"]*?)-0\.01([^"]*")',
        r"\g<1>0\g<2>", task.read_text(), count=1,
    )
    if count != 1:
        raise ValueError("unique private floor z edit not found")
    task.write_text(text)
    assert_only_floor_z_changed(
        R4_PREP / "runtime/source/mjpc/tasks/quadruped/task_flat.xml", task
    )
    side = rt / native_runtime.SIDECAR
    value = strict_json(side.read_text())
    value["files"] = {
        f.relative_to(rt).as_posix(): digest(f)
        for f in sorted(rt.rglob("*")) if f.is_file() and f != side
    }
    side.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    native_runtime.verify(rt / binary.name, side)
    return rt


def reuse_smoke(source, expected_manifest, output, current):
    directory, record, physics, reference = load_source(source, expected_manifest)
    fingerprint = matching_native_inputs(record, current)
    rt = _package_current(output, current)
    old_rt = directory / "consumer-runtime"
    hashes = lambda base: {
        f.relative_to(base).as_posix(): digest(f)
        for f in base.rglob("*") if f.is_file()
    }
    changes = _differences(hashes(old_rt), hashes(rt))
    if changes:
        raise ValueError("current sealed runtime differs: " + ", ".join(changes))
    copied = {}
    for name in SMOKE_LOGS[1:]:
        shutil.copyfile(directory / name, Path(output) / name)
        copied[name] = digest(Path(output) / name)
    provenance = {
        "schema": 1,
        "mode": "sealed_smoke_reuse",
        "source_qualification": reference,
        "source_smoke_accounting_sha256": digest(directory / SMOKE_LOGS[0]),
        "native_inputs_fingerprint": fingerprint,
        "copied_log_sha256": copied,
        "source_optimizer_calls": 1,
        "new_optimizer_calls": 0,
    }
    return physics, provenance


def validate_reuse_record(record):
    provenance = record.get("smoke_provenance") or {}
    reference = provenance.get("source_qualification") or {}
    if (
        provenance.get("schema") != 1
        or provenance.get("mode") != "sealed_smoke_reuse"
        or type(provenance.get("source_optimizer_calls")) is not int
        or provenance["source_optimizer_calls"] != 1
        or type(provenance.get("new_optimizer_calls")) is not int
        or provenance["new_optimizer_calls"] != 0
        or type(record.get("private_engineering_optimizer_calls")) is not int
        or record["private_engineering_optimizer_calls"] != 0
        or type(record.get("reused_private_engineering_optimizer_calls")) is not int
        or record["reused_private_engineering_optimizer_calls"] != 1
        or not reference.get("path")
    ):
        raise ValueError("retained smoke provenance/accounting is invalid")
    directory, source, physics, actual_ref = load_source(
        reference["path"], reference.get("manifest_sha256")
    )
    if (
        actual_ref != reference
        or record.get("physics_accounting") != physics
        or provenance.get("source_smoke_accounting_sha256")
        != digest(directory / SMOKE_LOGS[0])
        or provenance.get("native_inputs_fingerprint")
        != matching_native_inputs(source, record["qualification_inputs"])
        or provenance.get("copied_log_sha256") != {
            name: digest(directory / name) for name in SMOKE_LOGS[1:]
        }
    ):
        raise ValueError("retained smoke provenance/input fingerprint differs")
    return True
