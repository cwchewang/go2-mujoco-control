import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from . import mjpc_fixed_baseline as baseline
from .aligned_anchor import load_anchor


@contextmanager
def fake_lock():
    with open(os.devnull, "rb") as stream:
        yield stream


def pair_fixture(root):
    runs = root / "_runs"
    runs.mkdir()
    packet = runs / "packet.json"
    packet.write_text(json.dumps({"head": "head-1", "protocol_sha256": "proto-1"}))
    manifest = runs / "manifest.json"
    manifest.write_text("{}")
    auth = runs / "authorization.json"
    auth.write_text('{"action":"START_FORMAL_CAPTURE"}')
    review = runs / "review.json"
    review.write_text("{}")
    return runs, packet, review, auth


class FixedBaselineContractTests(unittest.TestCase):
    def test_design_matches_frozen_protocol_and_budget(self):
        self.assertEqual(baseline.design(), json.loads(baseline.PROTOCOL.read_text()))
        d = baseline.design()
        self.assertEqual(
            d["private_upper_bound_per_repeat"],
            d["replans"] * d["private_reservation_per_replan"],
        )
        self.assertEqual(
            d["private_upper_bound_total"],
            d["repeats"] * d["private_upper_bound_per_repeat"],
        )
        self.assertEqual(d["workers"], 4)
        self.assertEqual(d["binary_sha256"], baseline.BINARY_SHA)

    def test_original_anchor_task_commands_and_horizon(self):
        anchor = load_anchor()
        task = baseline.replace(
            anchor["task"],
            task_id="mjpc-fixed-baseline-3s-v1",
            horizon_ticks=1500,
            measurement_start_tick=150,
        )
        self.assertEqual(task.horizon_ticks, 1500)
        self.assertEqual(task.command_at(0).tolist(), [0.0, 0.0, 0.0])
        self.assertEqual(task.command_at(150).tolist(), [1.0, 0.0, 0.0])
        self.assertEqual(
            anchor["controllers"]["mjpc"]["timing"].feedback_period_s, 0.002
        )

    def test_no_launch_path_never_calls_episode_or_controller(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp) / "_runs"
            runs.mkdir()
            out = runs / "preflight"
            report = {"head": "head", "output": str(out), "canonical_physics_steps": 0}
            with (
                mock.patch.object(baseline, "RUNS", runs),
                mock.patch.object(
                    baseline, "validate", return_value=({}, Path("/fixed"), report)
                ),
                mock.patch.object(
                    baseline,
                    "run_aligned_episode",
                    side_effect=AssertionError("physics"),
                ),
                mock.patch.object(
                    baseline,
                    "NativeMJPCController",
                    side_effect=AssertionError("native"),
                ),
            ):
                result = baseline.no_launch("packet.json", out)
            self.assertEqual(result["status"], "PRECHECK_PASS_NO_LAUNCH")
            self.assertEqual(result["canonical_physics_steps"], 0)

    def test_same_packet_and_start_cannot_reserve_a_different_output(self):
        with tempfile.TemporaryDirectory() as temp:
            runs, packet, _review, auth = pair_fixture(Path(temp))
            with mock.patch.object(baseline, "RUNS", runs):
                reservation, _tokens = baseline.reserve_campaign(
                    packet, auth, runs / "first"
                )
                self.assertTrue(reservation.is_file())
                with self.assertRaises(FileExistsError):
                    baseline.reserve_campaign(packet, auth, runs / "different-output")
                record = json.loads(reservation.read_text())
            self.assertEqual(
                record["outputs"],
                [str(runs / "first_repeat1"), str(runs / "first_repeat2")],
            )
            self.assertEqual(record["max_attempts"], 2)

    def test_concurrent_campaign_reservation_has_exactly_one_winner(self):
        with tempfile.TemporaryDirectory() as temp:
            runs, packet, _review, auth = pair_fixture(Path(temp))
            barrier = threading.Barrier(2)
            outcomes = []

            def reserve(name):
                barrier.wait()
                try:
                    baseline.reserve_campaign(packet, auth, runs / name)
                    outcomes.append("won")
                except FileExistsError:
                    outcomes.append("lost")

            with mock.patch.object(baseline, "RUNS", runs):
                threads = [
                    threading.Thread(target=reserve, args=(name,))
                    for name in ("left", "right")
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
            self.assertCountEqual(outcomes, ["won", "lost"])

    def test_direct_worker_without_pair_capability_is_rejected(self):
        command = [
            sys.executable,
            "-B",
            "-m",
            "tools.substrate.mjpc_fixed_baseline",
            "--worker",
            "--output",
            "/tmp/should-not-run",
        ]
        result = subprocess.run(
            command, cwd=baseline.ROOT, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("inherited lock and one-use capability", result.stderr)

    def _mock_pair(self, temp, classifications):
        runs, packet, review, auth = pair_fixture(Path(temp))
        responses = [
            SimpleNamespace(
                returncode=0,
                communicate=lambda timeout, c=c: (
                    json.dumps({"classification": c, "canonical_physics_steps": 1500}),
                    "",
                ),
            )
            for c in classifications
        ]
        return runs, packet, review, auth, responses

    def test_pair_stops_after_first_failure_without_starting_repeat_two(self):
        with tempfile.TemporaryDirectory() as temp:
            runs, packet, review, auth, responses = self._mock_pair(
                temp, ["SAFETY_STOP"]
            )
            with (
                mock.patch.object(baseline, "RUNS", runs),
                mock.patch.object(baseline, "validate_start", return_value=packet),
                mock.patch.object(baseline, "experiment_lock", fake_lock),
                mock.patch.object(
                    baseline, "validate", return_value=({}, Path("/fixed"), {})
                ),
                mock.patch.object(
                    baseline,
                    "reserve_campaign",
                    return_value=(runs / "reservation.json", ["token1", "token2"]),
                ),
                mock.patch.object(
                    baseline.subprocess, "Popen", side_effect=responses
                ) as launched,
                mock.patch.object(
                    baseline.os, "write", side_effect=lambda fd, data: len(data)
                ),
            ):
                result = baseline.run_pair(packet, runs / "pair", review, auth)
            self.assertEqual(result["status"], "STOPPED_NO_RETRY")
            self.assertEqual(launched.call_count, 1)

    def test_pair_runs_two_fresh_workers_in_order_after_first_horizon(self):
        with tempfile.TemporaryDirectory() as temp:
            runs, packet, review, auth, responses = self._mock_pair(
                temp, ["HORIZON_REACHED", "HORIZON_REACHED"]
            )
            with (
                mock.patch.object(baseline, "RUNS", runs),
                mock.patch.object(baseline, "validate_start", return_value=packet),
                mock.patch.object(baseline, "experiment_lock", fake_lock),
                mock.patch.object(
                    baseline, "validate", return_value=({}, Path("/fixed"), {})
                ),
                mock.patch.object(
                    baseline,
                    "reserve_campaign",
                    return_value=(runs / "reservation.json", ["token1", "token2"]),
                ),
                mock.patch.object(
                    baseline.subprocess, "Popen", side_effect=responses
                ) as launched,
                mock.patch.object(
                    baseline.os, "write", side_effect=lambda fd, data: len(data)
                ),
            ):
                result = baseline.run_pair(packet, runs / "pair", review, auth)
            self.assertEqual(result["status"], "TWO_REPEAT_HORIZON_REACHED")
            self.assertEqual(launched.call_count, 2)
            self.assertIn(
                str(runs / "pair_repeat1"), launched.call_args_list[0].args[0]
            )
            self.assertIn(
                str(runs / "pair_repeat2"), launched.call_args_list[1].args[0]
            )
            commands = [call.args[0] for call in launched.call_args_list]
            self.assertEqual(commands[0][commands[0].index("--attempt") + 1], "1")
            self.assertEqual(commands[1][commands[1].index("--attempt") + 1], "2")

    def test_output_must_be_fresh_top_level_run(self):
        with self.assertRaises(ValueError):
            baseline.fresh(Path("/tmp/not-a-run"))


if __name__ == "__main__":
    unittest.main()
