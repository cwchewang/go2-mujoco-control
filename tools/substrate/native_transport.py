"""Bounded JSON framing, continuously drained diagnostics and owned-child cleanup."""

from collections import deque
from .integrity import strict_json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import threading
import time


class NativeTransport:
    MAX_FRAME = 65536
    CHUNK = 4096
    MAX_REQUEST = 4096

    def __init__(self, argv, *, popen=subprocess.Popen, stderr_log_path=None, env=None):
        if stderr_log_path is None:
            fd, name = tempfile.mkstemp(prefix="go2-native-stderr-", suffix=".log")
            self.stderr_path = Path(name)
            self._log = os.fdopen(fd, "wb")
        else:
            self.stderr_path = Path(stderr_log_path)
            self._log = self.stderr_path.open("xb")
        self._tail = deque(maxlen=16)
        self._stderr_bytes = 0
        self._stderr_error = None
        self._tail_lock = threading.Lock()
        self._buffer = b""
        self._closed = False
        self._selector = selectors.DefaultSelector()
        try:
            self.process = popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                bufsize=0,
                **({"env": env} if env is not None else {}),
            )
            os.set_blocking(self.process.stdin.fileno(), False)
            self._selector.register(self.process.stdout, selectors.EVENT_READ)
            self._reader = threading.Thread(
                target=self._drain_stderr, name="go2-native-stderr", daemon=True
            )
            self._reader.start()
        except Exception:
            self._selector.close()
            self._log.close()
            if hasattr(self, "process"):
                self.close()
            raise

    def _drain_stderr(self):
        try:
            while True:
                chunk = os.read(self.process.stderr.fileno(), self.CHUNK)
                if not chunk:
                    break
                self._log.write(chunk)
                self._log.flush()
                with self._tail_lock:
                    self._tail.append(chunk)
                    self._stderr_bytes += len(chunk)
        except (OSError, ValueError) as exc:
            self._stderr_error = str(exc)

    def diagnostics(self):
        with self._tail_lock:
            tail = b"".join(self._tail).decode("utf-8", errors="replace")
            total = self._stderr_bytes
        return {
            "stderr_log": str(self.stderr_path.resolve()),
            "stderr_bytes": total,
            "stderr_tail": tail,
            "stderr_read_error": self._stderr_error,
        }

    def read_json(self, timeout_s):
        if timeout_s <= 0:
            raise ValueError("native response timeout must be positive")
        deadline = time.monotonic() + timeout_s
        try:
            while b"\n" not in self._buffer:
                left = deadline - time.monotonic()
                if left <= 0 or not self._selector.select(left):
                    raise TimeoutError("native JSON response timed out")
                chunk = os.read(self.process.stdout.fileno(), self.CHUNK)
                if not chunk:
                    raise RuntimeError("native controller closed output")
                self._buffer += chunk
                if len(self._buffer) > self.MAX_FRAME:
                    raise ValueError("native JSON frame exceeds limit")
            line, self._buffer = self._buffer.split(b"\n", 1)
            if self._stderr_error:
                raise RuntimeError("native stderr reader failed")
            try:
                return strict_json(line.decode("utf-8"))
            except (ValueError, UnicodeError) as exc:
                raise ValueError("native MJPC emitted invalid JSON") from exc
        except Exception:
            self.close()
            raise

    def request(self, line, timeout_s):
        if self._closed or self.process.poll() is not None:
            raise RuntimeError("native MJPC controller is not running")
        payload = (line + "\n").encode()
        deadline = time.monotonic() + timeout_s
        try:
            if len(payload) > self.MAX_REQUEST:
                raise ValueError("native request exceeds limit")
            with selectors.DefaultSelector() as writable:
                writable.register(self.process.stdin, selectors.EVENT_WRITE)
                offset = 0
                while offset < len(payload):
                    left = deadline - time.monotonic()
                    if left <= 0 or not writable.select(left):
                        raise TimeoutError("native input timed out")
                    try:
                        offset += os.write(
                            self.process.stdin.fileno(), payload[offset:]
                        )
                    except BlockingIOError:
                        continue
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError("native response timed out")
            return self.read_json(left)
        except Exception:
            self.close()
            raise

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.process.poll() is None:
            try:
                os.write(self.process.stdin.fileno(), b"quit\n")
                self.process.wait(timeout=0.5)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    if self.process.poll() is not None:
                        break
                    try:
                        os.killpg(self.process.pid, sig)
                    except ProcessLookupError:
                        pass
                    try:
                        self.process.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        pass
        # Reap owned descendants even if the leader exited before its pipes did.
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        if hasattr(self, "_reader"):
            self._reader.join(timeout=1)
            if self._reader.is_alive():
                self._stderr_error = "stderr drain did not stop"
        self._selector.close()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()
        self._log.close()
