"""Full real native response regression; no simulated response substituted."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import fd_duplicate_diagnostic as d
from . import fd_duplicate_contract_replay as replay

FIXTURE = d.ROOT / "tools/substrate/fixtures/fd_duplicate_tick0_original"
TRIAL = {"tick": 0, "variant": "original", "repeat": 1}


def data():
    rows = [
        d.strict_json(x) for x in (FIXTURE / "native.jsonl").read_text().splitlines()
    ]
    return (
        rows[0]["ready"],
        rows[1]["response"],
        d.strict_json((FIXTURE / "fd-trace.jsonl").read_text()),
        [d.strict_json((FIXTURE / "predictions.jsonl").read_text())],
        next(
            a
            for a in d.strict_json((FIXTURE / "inputs.json").read_text())["anchors"]
            if a["tick"] == 0
        ),
    )


class RealResponseTest(unittest.TestCase):
    def test_exact_raw_hashes_and_correct_contract(self):
        for name, expected in d.strict_json((FIXTURE / "provenance.json").read_text())[
            "files"
        ].items():
            self.assertEqual(d.digest(FIXTURE / name), expected)
        ready, response, trace, predictions, anchor = data()
        ids = d.strict_json((FIXTURE / "binary-identities.json").read_text())
        parsed = d.parse_trial_logs(TRIAL, anchor, ids, FIXTURE)
        self.assertEqual(len(predictions[0]["states"]), 36)
        self.assertEqual(
            d.candidate_contract(ready)["qpos"] + d.candidate_contract(ready)["qvel"],
            37,
        )
        self.assertEqual(parsed["observation"]["fd_calls"], 37)
        self.assertEqual(parsed["observation"]["private_call_upper_bound"], 2501)

    def test_exact_old_37_expectation_fails_on_complete_real_response(self):
        self.assertEqual(
            replay.legacy_failure(FIXTURE, data()[-1]),
            "candidate horizon/state dimensions mismatch",
        )

    def test_wrong_dimensions_fields_budgets_and_candidates_rejected(self):
        mutations = (
            "short_horizon",
            "old_37_horizon",
            "late_qpos",
            "late_qvel",
            "late_action",
            "missing_action",
            "missing_time",
            "missing_contacts",
            "nonfinite_action",
            "invalid_candidate",
            "bool_candidate",
            "missing_cost",
            "missing_ready_nu",
            "wrong_mode",
            "bad_budget",
            "missing_budget",
            "prediction_budget",
            "bad_trace",
            "wrong_startup_horizon",
            "missing_model_id",
            "bad_contact",
        )
        for mutation in mutations:
            ready, response, trace, predictions, anchor = copy.deepcopy(data())
            candidate = predictions[0]
            states = candidate["states"]
            if mutation == "short_horizon":
                states.pop()
            elif mutation == "old_37_horizon":
                states.append(copy.deepcopy(states[-1]))
            elif mutation == "late_qpos":
                states[33]["qpos"].pop()
            elif mutation == "late_qvel":
                states[33]["qvel"].pop()
            elif mutation == "late_action":
                states[33]["nominal_position_action"].pop()
            elif mutation == "missing_action":
                del states[33]["nominal_position_action"]
            elif mutation == "missing_time":
                del states[33]["time_s"]
            elif mutation == "missing_contacts":
                del states[33]["active_contacts"]
            elif mutation == "nonfinite_action":
                states[33]["nominal_position_action"][0] = float("nan")
            elif mutation == "invalid_candidate":
                candidate["candidate_id"] = 10
            elif mutation == "bool_candidate":
                candidate["candidate_id"] = True
            elif mutation == "missing_cost":
                del response["cost"]
            elif mutation == "missing_ready_nu":
                del ready["nu"]
            elif mutation == "wrong_mode":
                candidate["mode"] = "corrected"
            elif mutation == "bad_budget":
                response["diagnostic"]["rollout_mj_step_count"] += 1
            elif mutation == "missing_budget":
                del response["diagnostic"]["fd_call_count"]
            elif mutation == "prediction_budget":
                candidate["private_accounting"]["reserved_step_upper_bound"] = 0
            elif mutation == "bad_trace":
                trace["events"].pop()
            elif mutation == "wrong_startup_horizon":
                ready["horizon_steps"] = 37
            elif mutation == "missing_model_id":
                del candidate["optimization_model_id"]
            elif mutation == "bad_contact":
                states[33]["active_contacts"] = [{"geom_ids": [0]}]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                d.validate_response(
                    "original", response, trace, predictions, 0, anchor, ready
                )
        ready, response, trace, predictions, anchor = data()
        for variant, stderr in (("fixed", 0), ("arbitrary", 0), ("original", 1)):
            with (
                self.subTest(variant=variant, stderr=stderr),
                self.assertRaises(ValueError),
            ):
                d.validate_response(
                    variant, response, trace, predictions, stderr, anchor, ready
                )

    def test_required_native_fields_cannot_disappear(self):
        groups = {
            "ready": (
                "ready",
                "protocol",
                "nq",
                "nv",
                "nu",
                "worker_count",
                "horizon_steps",
                "planner",
                "planner_dt",
                "warning_channel",
                "policy_freshness",
                "canonical_evaluation_plant_modified",
                "compatibility_correction",
                "source_nominal_biastype",
                "ground_miss_handling",
                "gait_switch",
                "gait",
                "joint_names",
                "position_lower",
                "position_upper",
                "kp",
                "kd",
            ),
            "response": (
                "ok",
                "replanned",
                "current_rollout_valid",
                "diagnostic",
                "cost",
                "q_des",
                "time_s",
                "vx",
                "wz",
            ),
            "prediction": (
                "policy_id",
                "candidate_id",
                "mode",
                "optimization_model_id",
                "contact_semantics",
                "anchor_time_s",
                "private_accounting",
                "states",
            ),
        }
        for group, fields in groups.items():
            for field in fields:
                ready, response, trace, predictions, anchor = copy.deepcopy(data())
                target = {
                    "ready": ready,
                    "response": response,
                    "prediction": predictions[0],
                }[group]
                del target[field]
                with (
                    self.subTest(group=group, field=field),
                    self.assertRaises(ValueError),
                ):
                    d.validate_response(
                        "original", response, trace, predictions, 0, anchor, ready
                    )

    def seal_inputs(self, root):
        prepared = root / "prepared"
        source = root / "source"
        with d.EvidenceRun(prepared) as record:
            for name in ("inputs.json", "binary-identities.json"):
                (prepared / name).write_bytes((FIXTURE / name).read_bytes())
            d.write_new(prepared / "protocol.json", json.loads(d.PROTOCOL.read_text()))
            record.result.update(status="ENGINEERING_ADMITTED", head="source-head")
        with d.EvidenceRun(source) as record:
            trial = source / "tick0_original_repeat1"
            trial.mkdir()
            for name in (
                "native.jsonl",
                "native.stderr.log",
                "fd-trace.jsonl",
                "predictions.jsonl",
            ):
                (trial / name).write_bytes((FIXTURE / name).read_bytes())
            record.result.update(
                status="STOPPED_INCOMPLETE",
                head="source-head",
                optimizer_calls_completed=0,
            )
        return prepared, source

    def test_failed_trial_record_keeps_one_attempt_and_raw_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepared, source = self.seal_inputs(Path(tmp))
            anchor = data()[-1]
            ids = d.strict_json((prepared / "binary-identities.json").read_text())

            def reject(item, anchor, identities, directory):
                raise ValueError(replay.legacy_failure(directory, anchor))

            completed, records, stop = d.collect_trials(
                [TRIAL], {0: anchor}, ids, source, reject
            )
            result = d.make_result(
                {"head": "test"},
                d.strict_json((prepared / "inputs.json").read_text()),
                ids,
                [TRIAL],
                completed,
                records,
                stop,
                prepared,
            )
            with d.EvidenceRun(Path(tmp) / "failed-result") as record:
                d.record_result(record, result)
            d.verify_manifest(Path(tmp) / "failed-result")
            self.assertEqual(result["optimizer_calls_attempted"], 1)
            self.assertEqual(result["optimizer_calls_completed"], 0)
            self.assertEqual(result["private_observed_upper_bound"], 2501)
            self.assertEqual(result["private_configured_reservation"], 4096)

    def test_missing_response_has_unknown_cost_and_nonzero_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            d.write_new(
                p / "optimizer-attempt.json", {"optimizer_call_attempted": True}
            )
            account = d.trial_accounting(TRIAL, p)
            self.assertTrue(account["optimizer_call_attempted"])
            self.assertFalse(account["budget_known"])
            self.assertIsNone(account["private_observed_upper_bound"])
            self.assertEqual(account["private_configured_reservation"], 4096)

    def test_zero_physics_entire_parse_record_result_verification_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared, source = self.seal_inputs(root)
            output = root / "replay"
            before = {p: d.digest(p / "manifest.json") for p in (source, prepared)}
            with (
                patch.object(
                    d,
                    "NativeTransport",
                    side_effect=AssertionError("native launch forbidden"),
                ),
                patch.object(
                    d, "run_trial", side_effect=AssertionError("optimizer forbidden")
                ),
            ):
                result_path = replay.replay(source, prepared, output)
            self.assertEqual(Path(result_path), output / "RESULT.json")
            admission = d.verify_manifest(output)
            result = d.strict_json((output / "RESULT.json").read_text())
            self.assertEqual(result["status"], "OFFLINE_REPLAY_COMPLETE")
            self.assertEqual(result["optimizer_calls_attempted"], 1)
            self.assertEqual(result["optimizer_calls_completed"], 1)
            self.assertEqual(result["new_optimizer_calls"], 0)
            self.assertEqual(result["source_original_accepted_trials"], 0)
            self.assertEqual(result["private_observed_upper_bound"], 2501)
            self.assertEqual(result["private_configured_reservation"], 4096)
            self.assertEqual(admission["capability_status"], "OFFLINE_REPLAY_ONLY")
            for p, h in before.items():
                d.verify_manifest(p)
                self.assertEqual(d.digest(p / "manifest.json"), h)


if __name__ == "__main__":
    unittest.main()
