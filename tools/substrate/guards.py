"""Zero-step preparation and bounded native-call supervision."""

import contextlib
import os
from pathlib import Path
import signal
import subprocess
import sys


@contextlib.contextmanager
def zero_step_guard():
    import mujoco

    def forbidden(*args, **kwargs):
        raise RuntimeError("prepare forbids real plant integration")

    originals = {
        name: getattr(mujoco, name) for name in ("mj_step", "mj_step1", "mj_step2")
    }
    try:
        for name in originals:
            setattr(mujoco, name, forbidden)
        yield
    finally:
        for name, value in originals.items():
            setattr(mujoco, name, value)


@contextlib.contextmanager
def wall_deadline(seconds):
    def expired(*args):
        raise TimeoutError("wall_timeout")

    guard = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).with_name("watchdog.py")),
            str(os.getpid()),
            str(seconds),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        guard.stdin.close()
        try:
            guard.wait(timeout=3)
        except subprocess.TimeoutExpired:
            guard.kill()
            guard.wait()
