"""Admission requires the isolated, hash-installed Linux CPython 3.10 environment."""

from importlib import metadata
import base64
import csv
import hashlib
import io
from pathlib import Path
import os
import platform
import re
import site
import sys
from .integrity import digest

ROOT = Path(__file__).resolve().parents[2]


def verify_environment():
    if (
        sys.version_info[:2] != (3, 10)
        or platform.system() != "Linux"
        or platform.machine() != "x86_64"
    ):
        raise ValueError("runtime lock targets Linux x86_64 CPython 3.10")
    if (
        sys.prefix == sys.base_prefix
        or site.ENABLE_USER_SITE
        or os.environ.get("PYTHONPATH")
    ):
        raise ValueError(
            "isolated venv required; PYTHONPATH/user site must be disabled"
        )
    config = (Path(sys.prefix) / "pyvenv.cfg").read_text().lower()
    if "include-system-site-packages = false" not in config:
        raise ValueError("system-site-packages is enabled")
    lock = ROOT / "tools/substrate/requirements-linux-py310.lock"
    expected = dict(re.findall(r"^([a-zA-Z0-9_.-]+)==(\S+)", lock.read_text(), re.M))
    canonical = lambda s: re.sub(r"[-_.]+", "-", s).lower()
    expected = {canonical(k): v for k, v in expected.items()}
    actual = {
        canonical(d.metadata["Name"]): d.version for d in metadata.distributions()
    }
    wrong = {k: (v, actual.get(k)) for k, v in expected.items() if actual.get(k) != v}
    extra = set(actual) - set(expected) - {"pip", "setuptools", "wheel"}
    if not expected or wrong or extra:
        raise ValueError(
            f"environment differs from lock: {wrong}; extra={sorted(extra)}"
        )
    # Check installed payloads against the wheel RECORD, including Python and
    # shared-library files. Version labels alone do not detect local corruption.
    checked = 0
    generated_bytecode = 0
    records = {}
    for dist in metadata.distributions():
        name = canonical(dist.metadata["Name"])
        if name not in expected:
            continue
        record = dist.read_text("RECORD")
        if record is None:
            raise ValueError("missing wheel RECORD: " + name)
        records[name] = hashlib.sha256(record.encode()).hexdigest()
        for filename, hashed, size in csv.reader(io.StringIO(record)):
            # Some wheels contain precompiled bytecode which pip regenerates
            # for the installation path and also appends an unhashed RECORD row.
            # Verify its source, not this documented mutable compilation cache.
            if Path(filename).suffix in (".pyc", ".pyo"):
                generated_bytecode += 1
                continue
            if not hashed:
                continue  # RECORD itself and generated pyc files
            algorithm, encoded = hashed.split("=", 1)
            if algorithm != "sha256":
                raise ValueError("unsupported wheel digest")
            path = Path(dist.locate_file(filename)).resolve()
            if (
                not path.is_relative_to(Path(sys.prefix).resolve())
                or not path.is_file()
            ):
                raise ValueError("missing/out-of-env package payload: " + filename)
            actual_hash = (
                base64.urlsafe_b64encode(bytes.fromhex(digest(path)))
                .decode()
                .rstrip("=")
            )
            if actual_hash != encoded or (size and path.stat().st_size != int(size)):
                raise ValueError("installed package payload changed: " + filename)
            checked += 1
    return {
        "wheel_records": records,
        "verified_payload_files": checked,
        "excluded_generated_bytecode_rows": generated_bytecode,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {k: actual[k] for k in sorted(expected)},
        "lock_sha256": digest(lock),
        "isolated": True,
    }
