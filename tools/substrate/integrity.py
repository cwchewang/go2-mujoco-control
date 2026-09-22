"""Small shared primitives for typed, immutable, independently verifiable evidence."""

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

LOCK_PATH = Path("/tmp/go2_mujoco_experiment.lock")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def strict_json(text):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate JSON key: " + key)
            out[key] = value
        return out

    def bad(value):
        raise ValueError("nonfinite JSON value: " + value)

    return json.loads(text, parse_constant=bad, object_pairs_hook=unique)


def write_new(path, value):
    path = Path(path)
    encoded = (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()
    with path.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def experiment_lock(path=LOCK_PATH):
    with Path(path).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def verify_manifest(directory):
    directory = Path(directory).resolve()
    manifest = strict_json((directory / "manifest.json").read_text())
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("empty manifest")
    actual = set()
    for item in directory.rglob("*"):
        if item.is_symlink():
            raise ValueError("symlink in evidence")
        if item.is_file() and item != directory / "manifest.json":
            actual.add(item.relative_to(directory).as_posix())
    if set(manifest) != actual:
        raise ValueError("manifest file set differs")
    for name, expected in manifest.items():
        path = directory / name
        if not path.resolve().is_relative_to(directory) or digest(path) != expected:
            raise ValueError("evidence digest mismatch: " + name)
    return strict_json((directory / "admission.json").read_text())


def verify_bundle(directory):
    result = verify_manifest(directory)
    if result.get("status") != "ENGINEERING_ADMITTED":
        raise ValueError("bundle is not admitted")
    return result


class EvidenceRun:
    """Exclusive output, persistent interruption marker, terminal manifest last."""

    def __init__(self, directory, metadata=None):
        self.path = Path(directory)
        self.result = {
            "scope": "offline_engineering_admission",
            "status": "FAILED",
            "capability_status": "NOT_RUN",
            "live_runs": 0,
            "errors": [],
        }
        self.metadata = metadata or {}

    def __enter__(self):
        for parent in self.path.absolute().parents:
            if (parent / "manifest.json").exists() and (
                parent / "admission.json"
            ).exists():
                raise ValueError("cannot append a run inside sealed evidence")
        if (
            self.path.is_symlink()
            or self.path.parent.resolve() != self.path.parent.absolute()
        ):
            raise ValueError(
                "output must not traverse symlinks or relative parent aliases"
            )
        self.path.mkdir(parents=True, exist_ok=False)
        write_new(
            self.path / "started.json",
            {
                "schema": 1,
                "unix_time": time.time(),
                "pid": os.getpid(),
                **self.metadata,
            },
        )
        self.previous_signal = signal.getsignal(signal.SIGTERM)

        def stop(signum, frame):
            raise RuntimeError("SIGTERM")

        signal.signal(signal.SIGTERM, stop)
        return self

    def __exit__(self, kind, error, traceback):
        signal.signal(signal.SIGTERM, self.previous_signal)
        if error is not None:
            self.result["status"] = "FAILED"
            self.result["errors"].append(type(error).__name__ + ": " + str(error))
        write_new(self.path / "admission.json", self.result)
        files = {}
        for path in self.path.rglob("*"):
            if path.is_symlink():
                raise ValueError("symlink in output")
            if path.is_file():
                files[path.relative_to(self.path).as_posix()] = digest(path)
        write_new(self.path / "manifest.json", files)
        fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return False


def run_logged(argv, directory, name, timeout=120, cwd=None, pass_fds=(), termination_grace=0.5):
    """Preserve partial output and reap the process group on all exit paths."""
    if not name.replace("_", "").isalnum():
        raise ValueError("invalid log name")
    directory = Path(directory)
    started = time.monotonic()
    with (
        (directory / (name + ".stdout")).open("xb") as out,
        (directory / (name + ".stderr")).open("xb") as err,
    ):
        process = subprocess.Popen(
            [str(v) for v in argv],
            cwd=cwd,
            stdout=out,
            stderr=err,
            start_new_session=True,
            pass_fds=pass_fds,
        )
        try:
            status = process.wait(timeout=timeout)
            if status:
                raise subprocess.CalledProcessError(status, argv)
        finally:
            # A finished parent can leave children alive. Reap its whole group.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=termination_grace)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            out.flush()
            err.flush()
            os.fsync(out.fileno())
            os.fsync(err.fileno())
    return {
        "argv": [str(v) for v in argv],
        "returncode": status,
        "wall_time_s": time.monotonic() - started,
    }
