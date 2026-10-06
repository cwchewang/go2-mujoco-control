"""No-native regression for live-adapter initialization in sequence replay."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.substrate import mjpc_short_sequence as sequence


class EndOfPrelaunch(Exception):
    pass


class FakeTransport:
    def __init__(self, response, stderr_bytes=0):
        self.response = response
        self.stderr_bytes = stderr_bytes
        self.requests = []
        self.closed = False

    def read_json(self, timeout):
        return {"worker_count": 4, "joint_names": list(sequence.POLICY_JOINTS)}

    def request(self, request, timeout):
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def diagnostics(self):
        return {"stderr_bytes": self.stderr_bytes, "stderr_read_error": None}

    def close(self):
        self.closed = True


class SequenceResetTests(unittest.TestCase):
    def run_trial(self, fake, directory):
        root = Path(directory)
        capture = root / "capture"
        capture.mkdir()
        row = {
            "time_s": 0.0,
            "replan": True,
            "command": [0.0] * 3,
            "qpos": [0.0, 0.0, 0.27, 1.0, 0.0, 0.0, 0.0] + [0.0] * 12,
            "qvel": [0.0] * 18,
        }
        with (
            patch.object(sequence, "validate_sequence_bundle", return_value=[row]),
            patch.object(sequence.d, "candidate_contract"),
            patch.object(
                sequence, "live_step_packet", side_effect=EndOfPrelaunch
            ) as packet,
        ):
            try:
                sequence.run_sequence_trial(
                    {"variant": "original", "repeat": 1},
                    {"source_capture": str(capture)},
                    {"original": Path("/never-launched")},
                    {},
                    root / "trial",
                    native_transport=lambda *args, **kwargs: fake,
                )
            finally:
                self.assertTrue(fake.closed)
                self.assertFalse((root / "trial/optimizer-attempts.jsonl").exists())
                self.assertFalse((root / "trial/predictions.jsonl").exists())
                if fake.response != {"ok": True, "reset": True} or fake.stderr_bytes:
                    packet.assert_not_called()

    def test_live_reset_is_logged_before_encoding_or_attempt_reservation(self):
        fake = FakeTransport({"ok": True, "reset": True})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(EndOfPrelaunch):
                self.run_trial(fake, directory)
            self.assertEqual(fake.requests, ["reset"])
            logs = [
                json.loads(x)
                for x in (Path(directory) / "trial/native.jsonl")
                .read_text()
                .splitlines()
            ]
            self.assertEqual(logs[1]["request"], "reset")
            self.assertEqual(logs[1]["response"], {"ok": True, "reset": True})

    def test_reset_rejection_never_reserves_optimizer_attempt(self):
        for response in (
            {},
            {"ok": False, "reset": True},
            {"ok": True, "reset": False},
            {"ok": 1, "reset": True},
            {"ok": True, "reset": True, "extra": 0},
        ):
            with (
                self.subTest(response=response),
                tempfile.TemporaryDirectory() as directory,
            ):
                fake = FakeTransport(response)
                with self.assertRaisesRegex(ValueError, "reset"):
                    self.run_trial(fake, directory)
                self.assertEqual(fake.requests, ["reset"])

    def test_reset_timeout_never_reserves_optimizer_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(TimeoutError):
                self.run_trial(FakeTransport(TimeoutError("reset timeout")), directory)

    def test_reset_warning_stops_before_optimizer_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "stderr"):
                self.run_trial(
                    FakeTransport({"ok": True, "reset": True}, stderr_bytes=1),
                    directory,
                )
