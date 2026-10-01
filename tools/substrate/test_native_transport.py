"""Real child pipes, bounded diagnostics, deadlines and cleanup; no physics."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from .native_transport import NativeTransport
from .native_mjpc import NativeMJPCController
from .clock import TimingSpec
from . import test_native_mjpc as protocol_fixtures


class NativeTransportTest(unittest.TestCase):
    def child(self, code, root):
        return NativeTransport(
            [sys.executable, "-u", "-c", code],
            stderr_log_path=Path(root) / "stderr.log",
        )

    def test_stderr_larger_than_pipe_drains_and_full_log_survives_close(self):
        with tempfile.TemporaryDirectory() as root:
            size = 2 * 1024 * 1024
            transport = self.child(
                "import sys; sys.stderr.write('x'*"
                + str(size)
                + "); sys.stderr.flush(); "
                "print('{\\\"ready\\\":true}',flush=True); sys.stdin.readline()",
                root,
            )
            try:
                self.assertEqual(transport.read_json(5), {"ready": True})
            finally:
                transport.close()
            diag = transport.diagnostics()
            self.assertEqual(diag["stderr_bytes"], size)
            self.assertLessEqual(len(diag["stderr_tail"]), 65536)
            self.assertEqual(Path(diag["stderr_log"]).stat().st_size, size)
            self.assertIsNotNone(transport.process.poll())
            self.assertFalse(transport._reader.is_alive())

    def test_startup_and_response_timeout_reap_child(self):
        for ready in (False, True):
            with self.subTest(ready=ready), tempfile.TemporaryDirectory() as root:
                code = "import time; "
                if ready:
                    code += "print('{\\\"ready\\\":true}',flush=True); "
                code += "time.sleep(20)"
                transport = self.child(code, root)
                start = time.monotonic()
                with self.assertRaises(TimeoutError):
                    if ready:
                        transport.read_json(2)
                        transport.request("blocked", 0.05)
                    else:
                        transport.read_json(0.05)
                self.assertIsNotNone(transport.process.poll())
                self.assertFalse(transport._reader.is_alive())
                self.assertLess(time.monotonic() - start, 3)

    def test_bad_json_oversize_and_duplicate_keys_close_child(self):
        for line in ("not-json", "x" * 70000, '{"ok":true,"ok":false}'):
            with tempfile.TemporaryDirectory() as root:
                transport = self.child(
                    "import sys,time; sys.stdout.write("
                    + repr(line + "\n")
                    + "); sys.stdout.flush(); time.sleep(20)",
                    root,
                )
                with self.assertRaises(ValueError):
                    transport.read_json(2)
                self.assertIsNotNone(transport.process.poll())

    def test_oversized_request_is_rejected_and_child_reaped(self):
        with tempfile.TemporaryDirectory() as root:
            transport = self.child(
                "import time; print("
                + repr(json.dumps({"ready": True}))
                + ",flush=True); time.sleep(20)",
                root,
            )
            transport.read_json(2)
            with self.assertRaisesRegex(ValueError, "request exceeds"):
                transport.request("x" * 4096, 1)
            self.assertIsNotNone(transport.process.poll())

    def test_exit_preserves_stderr_and_closes_descriptors(self):
        with tempfile.TemporaryDirectory() as root:
            transport = self.child(
                "import sys; sys.stderr.write('expected failure'); sys.exit(3)", root
            )
            with self.assertRaises(RuntimeError):
                transport.read_json(2)
            self.assertEqual(transport.process.returncode, 3)
            self.assertIn("expected failure", transport.diagnostics()["stderr_tail"])
            self.assertTrue(transport.process.stdout.closed)


class NativeControllerLifecycleTest(unittest.TestCase):
    def test_invalid_ready_closes_started_native_child(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root)
            task = source / "mjpc/tasks/quadruped/task_flat.xml"
            task.parent.mkdir(parents=True)
            task.write_text("fixture")
            children = []
            code = (
                "import time; print("
                + repr(json.dumps({"ready": False}))
                + ",flush=True); time.sleep(20)"
            )

            def popen(argv, **kwargs):
                child = subprocess.Popen(
                    [sys.executable, "-u", "-c", code],
                    **kwargs,
                )
                children.append(child)
                return child

            with (
                patch("tools.substrate.native_mjpc.verify_controller", return_value={}),
                patch(
                    "tools.substrate.native_mjpc.cache_values",
                    return_value={"MJPC_SOURCE_DIR": str(source)},
                ),
            ):
                with self.assertRaises(ValueError):
                    NativeMJPCController(
                        sys.executable,
                        TimingSpec(0.002, 0.02),
                        popen=popen,
                        stderr_log_path=source / "invalid-ready.stderr.log",
                    )
            self.assertIsNotNone(children[0].poll())
            self.assertTrue(children[0].stderr.closed)

    def test_failed_candidate_requires_reset_before_success(self):
        fixture = protocol_fixtures.NativeMJPCProtocolTest()
        ready = fixture.ready()
        response = {
            "ok": True,
            "time_s": 1.24,
            "cost": 1.0,
            "replanned": True,
            "current_rollout_valid": True,
            "planning_compute_us": 1,
            "action_compute_us": 1,
            "q_des": [0.0] * 12,
        }
        code = (
            "import json,sys\n"
            "print(" + repr(json.dumps(ready)) + ",flush=True)\n"
            "failed=False\n"
            "for line in sys.stdin:\n"
            " if line.strip()=='quit': break\n"
            " if line.strip()=='reset': print('{\\\"ok\\\":true,\\\"reset\\\":true}',flush=True); continue\n"
            ' if not failed: failed=True; print(\'{\\"ok\\":false,\\"error\\":\\"no current candidates\\"}\',flush=True)\n'
            " else: print(" + repr(json.dumps(response)) + ",flush=True)\n"
        )
        with tempfile.TemporaryDirectory() as root:
            source = Path(root)
            task = source / "mjpc/tasks/quadruped/task_flat.xml"
            task.parent.mkdir(parents=True)
            task.write_text("fixture")

            def popen(argv, **kwargs):
                return subprocess.Popen([sys.executable, "-u", "-c", code], **kwargs)

            with (
                patch("tools.substrate.native_mjpc.verify_controller", return_value={}),
                patch(
                    "tools.substrate.native_mjpc.cache_values",
                    return_value={"MJPC_SOURCE_DIR": str(source)},
                ),
                NativeMJPCController(
                    sys.executable,
                    TimingSpec(0.002, 0.02),
                    popen=popen,
                    stderr_log_path=source / "controller.stderr.log",
                ) as controller,
            ):
                obs = fixture.state(time_s=1.24)
                with self.assertRaisesRegex(RuntimeError, "no current candidates"):
                    controller.step(obs, [1, 0, 0])
                with self.assertRaisesRegex(RuntimeError, "requires reset"):
                    controller.step(obs, [1, 0, 0])
                controller.reset(obs)
                self.assertEqual(controller.step(obs, [1, 0, 0]).shape, (12,))
            self.assertIsNotNone(controller.process.poll())


if __name__ == "__main__":
    unittest.main()
