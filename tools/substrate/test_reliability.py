"""Fault injection for admission infrastructure; no simulation or hardware."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from .contracts import Proprioception, POLICY_JOINTS as P, TorqueCommand, vector
from .evidence import summarize_frames, validate_capture_contract
from .integrity import (
    EvidenceRun,
    experiment_lock,
    run_logged,
    strict_json,
    verify_bundle,
    digest,
)
from .admit import validate_native_result
from .build_identity import verify as verify_build
from .model import dependency_manifest


class Reliability(unittest.TestCase):
    def test_vectors_reject_coercion_and_nonfinite(self):
        for v in ([True] * 3, ["1"] * 3, [float("inf")] * 3, [1, 2]):
            with self.subTest(v=v), self.assertRaises(ValueError):
                vector(v, 3, "test")

    def test_observation_cannot_alias_caller_or_be_made_writable(self):
        q = np.arange(12.0)
        o = Proprioception(P, q, np.zeros(12), np.array([1.0, 0, 0, 0]), np.zeros(3))
        q[0] = 100
        self.assertEqual(o.position[0], 0)
        with self.assertRaises(ValueError):
            o.position[0] = 2
        with self.assertRaises(ValueError):
            o.position.setflags(write=True)

    def test_command_does_not_alias_caller(self):
        a = np.zeros(12)
        c = TorqueCommand(P, a, a, a, a, a)
        a[:] = 123
        self.assertEqual(c.feedforward[0], 0)
        with self.assertRaises(ValueError):
            c.kp.setflags(write=True)

    def test_json_rejects_duplicates_and_nonfinite(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError):
                strict_json(text)

    def native(self):
        return dict(
            backend="MJPC iLQG",
            scope="offline_static_state",
            mujoco="3.3.6",
            planner=2,
            horizon_steps=21,
            finite_bounded=True,
            rollout_failure=False,
            plant_time_s=0,
            cost=0.1,
            initial_cost=0.2,
            torque=[0.0] * 12,
        )

    def test_native_result_positive(self):
        validate_native_result(self.native())

    def test_native_result_rejects_silent_false_passes(self):
        for key, value in (
            ("finite_bounded", "true"),
            ("rollout_failure", True),
            ("planner", True),
            ("horizon_steps", 20),
            ("plant_time_s", 0.002),
            ("cost", float("nan")),
            ("initial_cost", None),
            ("cost", 0.3),
            ("torque", [0.0] * 11),
        ):
            result = self.native()
            result[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_native_result(result)

    def test_wrong_result_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_native_result([])

    def contract(self):
        return dict(
            reviewed_by="fixture reviewer",
            model_sha256="a" * 64,
            backend_sha256="b" * 64,
            information_regime="proprioceptive",
            start_state=dict(qpos=[0.0, 0.0, 0.27, 1.0] + [0.0] * 15, qvel=[0.0] * 18),
            command=[0.0, 0.0, 0.0],
            horizon_s=1.0,
            repeat_count=1,
            thresholds={"fixture_only": 0.1},
            support_semantics="traverse",
            control_period_s=0.02,
        )

    def test_capture_completeness_positive_is_not_execution(self):
        validate_capture_contract(self.contract())

    def test_capture_rejects_bad_numeric_and_support_fields(self):
        for field, value in (
            ("horizon_s", True),
            ("repeat_count", True),
            ("control_period_s", 2.0),
            ("support_semantics", "mandatory_support"),
            ("thresholds", {"a": True}),
            ("model_sha256", "not a hash"),
        ):
            c = self.contract()
            c[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_capture_contract(c)
        c = self.contract()
        c["start_state"]["qpos"][3] = 0
        with self.assertRaises(ValueError):
            validate_capture_contract(c)

    def test_evidence_rejects_string_boolean_and_invalid_supports(self):
        for extra in (
            {"task_complete": "false"},
            {"supports": "top"},
            {"failure": False},
        ):
            row = dict(sequence=0, sim_time_s=0, **extra)
            with self.assertRaises(ValueError):
                summarize_frames([row], 0.02)
        with self.assertRaises(ValueError):
            summarize_frames(
                [dict(sequence=0, sim_time_s=0)], 0.02, "mandatory_support"
            )

    def test_evidence_rejects_post_terminal_samples(self):
        rows = [
            dict(sequence=0, sim_time_s=0, task_complete=True),
            dict(sequence=1, sim_time_s=0.02),
        ]
        with self.assertRaises(ValueError):
            summarize_frames(rows, 0.02)

    def test_evidence_rejects_accumulating_clock_error(self):
        rows = [dict(sequence=i, sim_time_s=i * (0.02 + 5e-10)) for i in range(10)]
        with self.assertRaises(ValueError):
            summarize_frames(rows, 0.02)

    def test_manifest_rejects_unsupported_assets(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "a.xml"
            for node in (
                '<plugin plugin="x"/>',
                '<texture fileup="x.png"/>',
                '<model file="robot.xml"/>',
            ):
                p.write_text("<mujoco><asset>" + node + "</asset></mujoco>")
                with self.assertRaises(ValueError):
                    dependency_manifest(p, p.parent)

    def test_bundle_success_and_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "run"
            with EvidenceRun(p) as run:
                run.result["status"] = "ENGINEERING_ADMITTED"
            verify_bundle(p)
            (p / "started.json").write_text("changed")
            with self.assertRaises(ValueError):
                verify_bundle(p)

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "run"
            p.mkdir()
            (p / "keep").write_text("original")
            with self.assertRaises(FileExistsError):
                with EvidenceRun(p):
                    pass
            self.assertEqual((p / "keep").read_text(), "original")

    def test_exception_is_preserved_and_not_admitted(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "run"
            with self.assertRaisesRegex(RuntimeError, "fixture"):
                with EvidenceRun(p):
                    raise RuntimeError("fixture")
            value = json.loads((p / "admission.json").read_text())
            self.assertEqual(value["status"], "FAILED")
            self.assertIn("fixture", value["errors"][0])
            with self.assertRaises(ValueError):
                verify_bundle(p)

    def test_interrupt_is_not_admitted(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "run"
            with self.assertRaises(KeyboardInterrupt):
                with EvidenceRun(p):
                    raise KeyboardInterrupt()
            self.assertEqual(
                json.loads((p / "admission.json").read_text())["status"], "FAILED"
            )

    def test_incomplete_bundle_is_not_admitted(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            (p / "started.json").write_text("{}")
            with self.assertRaises(FileNotFoundError):
                verify_bundle(p)

    def test_extra_file_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "run"
            with EvidenceRun(p) as run:
                run.result["status"] = "ENGINEERING_ADMITTED"
            (p / "extra").write_text("x")
            with self.assertRaises(ValueError):
                verify_bundle(p)
            # This temporary fixture is not a project raw evidence directory.
            (p / "extra").unlink()
            (p / "link").symlink_to(p / "started.json")
            with self.assertRaises(ValueError):
                verify_bundle(p)

    def test_lock_contention_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            lock = Path(t) / "lock"
            with experiment_lock(lock):
                with self.assertRaises(BlockingIOError):
                    with experiment_lock(lock):
                        pass

    def test_timeout_keeps_partial_diagnostics(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            with self.assertRaises(subprocess.TimeoutExpired):
                run_logged(
                    [
                        sys.executable,
                        "-c",
                        "import time; print('before timeout',flush=True); time.sleep(20)",
                    ],
                    p,
                    "fixture",
                    timeout=0.2,
                )
            self.assertIn("before timeout", (p / "fixture.stdout").read_text())

    def test_child_failure_preserves_stderr(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            with self.assertRaises(subprocess.CalledProcessError):
                run_logged(
                    [
                        sys.executable,
                        "-c",
                        "import sys; print('fixture error',file=sys.stderr); sys.exit(3)",
                    ],
                    p,
                    "fixture",
                )
            self.assertIn("fixture error", (p / "fixture.stderr").read_text())

    def test_nested_run_cannot_modify_sealed_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "run"
            with EvidenceRun(p) as run:
                run.result["status"] = "ENGINEERING_ADMITTED"
            with self.assertRaises(ValueError):
                with EvidenceRun(p / "another"):
                    pass
            verify_bundle(p)

    def test_timeout_terminates_forked_child(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            code = "import os,time,signal; pid=os.fork(); signal.signal(signal.SIGTERM,signal.SIG_IGN); print(os.getpid(),flush=True); time.sleep(30)"
            with self.assertRaises(subprocess.TimeoutExpired):
                run_logged([sys.executable, "-c", code], p, "fork", timeout=0.2)
            for value in (p / "fork.stdout").read_text().splitlines():
                status = Path("/proc") / value / "stat"
                import time

                state = "running"
                for _ in range(50):
                    try:
                        state = status.read_text().rsplit(")", 1)[1].split()[0]
                    except FileNotFoundError:
                        state = "X"
                    if state in ("Z", "X"):
                        break
                    time.sleep(0.01)
                self.assertIn(state, ("Z", "X"))

    def test_sigterm_seals_failure_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "run"
            code = (
                "from pathlib import Path; from tools.substrate.integrity import EvidenceRun; import time; r=EvidenceRun(Path("
                + repr(str(p))
                + ")); r.__enter__(); print('READY',flush=True);\ntry: time.sleep(30)\nexcept BaseException as e: r.__exit__(type(e),e,e.__traceback__)"
            )
            child = subprocess.Popen(
                [sys.executable, "-c", code], stdout=subprocess.PIPE, text=True
            )
            try:
                self.assertEqual(child.stdout.readline().strip(), "READY")
                child.terminate()
                child.wait(timeout=5)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
                child.stdout.close()
            self.assertEqual(
                json.loads((p / "admission.json").read_text())["status"], "FAILED"
            )
            self.assertIn("SIGTERM", (p / "admission.json").read_text())

    def environment_fixture(self, corrupt=False, extra_package=False):
        import base64
        import contextlib
        import hashlib
        from types import SimpleNamespace
        from . import environment

        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "tools/substrate").mkdir(parents=True)
            (root / "tools/substrate/requirements-linux-py310.lock").write_text(
                "fixture==1.0\n"
            )
            (root / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
            payload = b"original source"
            (root / "module.py").write_bytes(b"changed" if corrupt else payload)
            (root / "cache.pyc").write_bytes(b"regenerated cache")
            encoded = (
                base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
                .decode()
                .rstrip("=")
            )
            record = f"module.py,sha256={encoded},{len(payload)}\ncache.pyc,sha256=deliberately_regenerated,1\n"
            dist = SimpleNamespace(
                metadata={"Name": "fixture"},
                version="1.0",
                read_text=lambda name: record,
                locate_file=lambda name: root / name,
            )
            packages = [dist]
            if extra_package:
                packages.append(
                    SimpleNamespace(metadata={"Name": "unexpected"}, version="1.0")
                )
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(environment, "ROOT", root))
                stack.enter_context(patch.object(environment.sys, "prefix", str(root)))
                stack.enter_context(
                    patch.object(environment.sys, "version_info", (3, 10, 0))
                )
                stack.enter_context(
                    patch.object(environment.site, "ENABLE_USER_SITE", False)
                )
                stack.enter_context(
                    patch.object(
                        environment.metadata, "distributions", return_value=packages
                    )
                )
                stack.enter_context(
                    patch.dict(environment.os.environ, {"PYTHONPATH": ""})
                )
                return environment.verify_environment()

    def test_installed_source_payload_verified_with_regenerated_cache(self):
        result = self.environment_fixture()
        self.assertEqual(result["verified_payload_files"], 1)
        self.assertEqual(result["excluded_generated_bytecode_rows"], 1)

    def test_installed_source_corruption_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "payload changed"):
            self.environment_fixture(corrupt=True)

    def test_unlocked_package_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "extra"):
            self.environment_fixture(extra_package=True)

    def test_stale_binary_identity_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            binary = p / "app"
            binary.write_bytes(b"binary")
            (p / "build-identity.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "binary_sha256": digest(binary),
                        "inputs": {"source": "old"},
                    }
                )
            )
            with patch(
                "tools.substrate.build_identity.inputs", return_value={"source": "new"}
            ):
                with self.assertRaisesRegex(ValueError, "stale build"):
                    verify_build(binary)
            binary.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "binary"):
                verify_build(binary)


if __name__ == "__main__":
    unittest.main()
