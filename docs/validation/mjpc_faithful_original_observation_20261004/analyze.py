"""Recompute the sealed prefix observation using only standard-library reads."""

import hashlib
import json
from pathlib import Path

BASE = Path("/home/che/dev/go2-workspace")
RUN = (
    BASE
    / "faithful-original-observation/_runs/mjpc_faithful_original_observation_20261003"
)
QUAL = RUN.parent / "mjpc_faithful_original_qualification_20261003_v4"
A = (
    BASE
    / "current/_runs/mjpc_adaptation_diagnostic_execution_20261002/original_capture_20261002T164948Z"
)
REF = (
    BASE
    / "current/example/cpp/experiments/_runs/shared_baseline_probes_v1/run_20261002T085338452324Z/mjpc_baseline_1.jsonl"
)
PIN = "8b3e6fc4c36a7a188715b8221d7bf4d9347683f1637355c24e4a9fcefe8e79d9"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def verify(directory):
    manifest = load(directory / "manifest.json")
    actual = {
        p.relative_to(directory).as_posix()
        for p in directory.rglob("*")
        if p.is_file() and p.name != "manifest.json"
    }
    assert not any(p.is_symlink() for p in directory.rglob("*"))
    assert actual == set(manifest)
    assert all(sha(directory / name) == value for name, value in manifest.items())
    return len(manifest)


def maximum(left, right):
    assert len(left) == len(right)
    return max(abs(a - b) for a, b in zip(left, right))


def analyze():
    assert sha(RUN / "manifest.json") == PIN
    counts = {
        "observation": verify(RUN),
        "qualification": verify(QUAL),
        "historical_A": verify(A),
    }
    assert (
        sha(A / "raw.jsonl")
        == "9a4f2711f558b80ac58c803406971f43be7c44f4c5e64f7a50c728e2a7440e55"
    )
    assert (
        sha(REF) == "e5f760c54a57d12e8da6150972cb084414c3f9d84f1827ac9582b292532a3841"
    )
    historical, reference = lines(A / "raw.jsonl"), lines(REF)
    result = load(RUN / "RESULT.json")
    native = [lines(RUN / f"original_repeat{i}/native.jsonl") for i in (1, 2)]
    predictions = [lines(RUN / f"original_repeat{i}/predictions.jsonl") for i in (1, 2)]
    traces = [lines(RUN / f"original_repeat{i}/fd-trace.jsonl") for i in (1, 2)]
    attempted = reserved = upper = 0
    per_call = []
    rows = []
    permutation = [3, 4, 5, 0, 1, 2, 9, 10, 11, 6, 7, 8]
    for repeat in (1, 2):
        directory = RUN / f"original_repeat{repeat}"
        ledgers = lines(directory / "optimizer-attempts.jsonl")
        attempted += len(ledgers)
        reserved += sum(row["reserved_upper_bound"] for row in ledgers)
        logs = native[repeat - 1]
        assert logs[1] == {"request": "reset", "response": {"ok": True, "reset": True}}
        assert directory.joinpath("native.stderr.log").stat().st_size == 0
        assert [row["tick"] for row in logs[2:]] == list(range(11))
        previous = 0
        for row in logs[2:]:
            tick = row["tick"]
            source = historical[tick]
            expected_q = source["qpos"][:7] + [
                source["qpos"][7 + j] for j in permutation
            ]
            expected_v = source["qvel"][:6] + [
                source["qvel"][6 + j] for j in permutation
            ]
            expected = (
                "step "
                + str(int(tick in (0, 10)))
                + " "
                + " ".join(
                    format(float(v), ".17g")
                    for v in [
                        source["sim_time_s"],
                        *source["command"],
                        *expected_q,
                        *expected_v,
                    ]
                )
            )
            assert row["request"] == expected
            response = row["response"]
            assert response["ok"] is True and response["replanned"] is (tick in (0, 10))
            if tick in (0, 10):
                diag = response["diagnostic"]
                call = 1 if tick == 0 else 2
                assert diag["fd_call_count"] == call * 37
                assert diag["fd_step_upper_bound_count"] == call * 1801
                assert diag["rollout_mj_step_count"] == call * 700
                assert diag["private_step_upper_bound_reserved"] == call * 4096
                cumulative = (
                    diag["fd_step_upper_bound_count"] + diag["rollout_mj_step_count"]
                )
                per_call.append(
                    {
                        "repeat": repeat,
                        "tick": tick,
                        "accounted_upper": cumulative - previous,
                        "reserved": 4096,
                    }
                )
                previous = cumulative
            observed = result["results"][repeat - 1]["inputs"][tick]
            assert (
                observed["q_des"] == response["q_des"]
                and observed["cost"] == response["cost"]
            )
            entry = {"repeat": repeat, "tick": tick}
            for label, old in (("A", historical[tick]), ("reference", reference[tick])):
                assert old["target"]["joint_names"] == logs[0]["ready"]["joint_names"]
                entry[label + "_q_des_max_abs_diff"] = maximum(
                    response["q_des"], old["target"]["position_target"]
                )
                entry[label + "_cost_abs_diff"] = abs(
                    response["cost"]
                    - old["controller_diagnostics"]["controller"]["last_step"]["cost"]
                )
            rows.append(entry)
        upper += previous
    assert (attempted, reserved, upper) == (4, 16384, 10004)
    pair = [
        {
            "tick": tick,
            "q_des_max_abs_diff": maximum(
                native[0][tick + 2]["response"]["q_des"],
                native[1][tick + 2]["response"]["q_des"],
            ),
            "cost_abs_diff": abs(
                native[0][tick + 2]["response"]["cost"]
                - native[1][tick + 2]["response"]["cost"]
            ),
        }
        for tick in range(11)
    ]
    optimizer = []
    for call in (0, 1):
        histories = [p[call]["planner_history"] for p in predictions]
        ts = [t[call] for t in traces]
        seeds = [
            {
                "slot": i,
                "knot": left["t"],
                "hashes": [
                    left["warmstart_before_fnv1a64"],
                    right["warmstart_before_fnv1a64"],
                ],
            }
            for i, (left, right) in enumerate(zip(ts[0]["events"], ts[1]["events"]))
            if left["warmstart_before_fnv1a64"] != right["warmstart_before_fnv1a64"]
        ]
        duplicates = []
        for repeat in (0, 1):
            events = [e for e in ts[repeat]["events"] if e["t"] == 34]
            assert len(events) == 2
            duplicates.append(
                {
                    "repeat": repeat + 1,
                    "overlap_ns": max(
                        0,
                        min(e["end_ns"] for e in events)
                        - max(e["start_ns"] for e in events),
                    ),
                    "workers": [e["worker"] for e in events],
                    "incoming_warmstart_hashes": [
                        e["warmstart_before_fnv1a64"] for e in events
                    ],
                }
            )
        logged_state_differences = {
            name: max(
                maximum(a[name], b[name])
                for a, b in zip(
                    predictions[0][call]["states"], predictions[1][call]["states"]
                )
            )
            for name in ("qpos", "qvel", "nominal_position_action")
        }

        def signature(values):
            return sorted((v["fnv1a64"], v["norm"], v["max_abs"]) for v in values)

        optimizer.append(
            {
                "call": call + 1,
                "tick": call * 10,
                "pre_policy_summaries_equal": histories[0]["pre_policy"]
                == histories[1]["pre_policy"],
                "pre_previous_policy_summaries_equal": histories[0][
                    "pre_previous_policy"
                ]
                == histories[1]["pre_previous_policy"],
                "post_worker_summary_multisets_equal": signature(
                    histories[0]["worker_warmstart"]["post"]
                )
                == signature(histories[1]["worker_warmstart"]["post"]),
                "pre_worker_assignments_equal": histories[0]["worker_warmstart"]["pre"]
                == histories[1]["worker_warmstart"]["pre"],
                "post_worker_assignments_equal": histories[0]["worker_warmstart"][
                    "post"
                ]
                == histories[1]["worker_warmstart"]["post"],
                "first_logged_FD_seed_difference": seeds[0] if seeds else None,
                "jacobian_t34_hashes": [t["jacobian_t34_fnv1a64"] for t in ts],
                "selected_policy_hashes": [
                    h["post_policy"]["fnv1a64"] for h in histories
                ],
                "selected_candidate_ids": [
                    p[call]["candidate_id"] for p in predictions
                ],
                "duplicate_t34": duplicates,
                "logged_selected_trajectory_max_abs_differences": logged_state_differences,
            }
        )
    return {
        "schema": 1,
        "status": "VERIFIED_PRIVATE_OBSERVATION",
        "producer_head": result["head"],
        "evidence": {
            "observation": str(RUN),
            "manifest_sha256": PIN,
            "manifest_members": counts,
            "qualification_manifest_sha256": sha(QUAL / "manifest.json"),
            "historical_A_raw_sha256": sha(A / "raw.jsonl"),
            "reference_raw_sha256": sha(REF),
        },
        "accounting": {
            "private_optimizer_calls": attempted,
            "private_reserved": reserved,
            "private_accounted_upper": upper,
            "canonical_steps": 0,
            "formal_scientific_attempts": 0,
            "per_call": per_call,
        },
        "wire_inputs_verified": 22,
        "historical_comparisons": rows,
        "repeat_comparisons": pair,
        "first_exact_output_difference_tick": next(
            (p["tick"] for p in pair if p["q_des_max_abs_diff"]), None
        ),
        "optimizer": optimizer,
        "tolerance": 1e-9,
        "all_output_and_cost_comparisons_within_original_tolerance": all(
            max(
                row["A_q_des_max_abs_diff"],
                row["reference_q_des_max_abs_diff"],
                row["A_cost_abs_diff"],
                row["reference_cost_abs_diff"],
            )
            <= 1e-9
            for row in rows
        )
        and all(
            max(row["q_des_max_abs_diff"], row["cost_abs_diff"]) <= 1e-9 for row in pair
        ),
        "new_integration_in_this_analysis": 0,
    }


if __name__ == "__main__":
    print(json.dumps(analyze(), indent=2, sort_keys=True, allow_nan=False))
