"""Recompute the unique-index-only intervention from sealed bytes; no simulator."""

import hashlib
import json
from pathlib import Path
import runpy

BASE = Path("/home/che/dev/go2-workspace")
ROOT = BASE / "faithful-dedup-observation"
RUN = ROOT / "_runs/mjpc_faithful_dedup_observation_20261004"
QUAL = ROOT / "_runs/mjpc_faithful_dedup_qualification_20261004_v2"
CONTROL = (
    BASE
    / "faithful-original-observation/_runs/mjpc_faithful_original_observation_20261003"
)
A = (
    BASE
    / "current/_runs/mjpc_adaptation_diagnostic_execution_20261002/original_capture_20261002T164948Z"
)
PIN = "2e5fa41e23f9334037c59aeffe0fc064473286bb68af2d81a1006a9f546aecb2"
QUAL_PIN = "30bd091bfa733021d205f118fc366c4746dc3da30a7cb8a74146b7f3577e5980"
CONTROL_PIN = "8b3e6fc4c36a7a188715b8221d7bf4d9347683f1637355c24e4a9fcefe8e79d9"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def verify(path, pin):
    assert sha(path / "manifest.json") == pin
    manifest = read(path / "manifest.json")
    actual = {
        p.relative_to(path).as_posix()
        for p in path.rglob("*")
        if p.is_file() and p != path / "manifest.json"
    }
    assert actual == set(manifest)
    assert not any(p.is_symlink() for p in path.rglob("*"))
    assert all(sha(path / n) == h for n, h in manifest.items())
    return len(manifest)


def maximum(a, b):
    assert len(a) == len(b)
    return max(abs(x - y) for x, y in zip(a, b))


def signature(values):
    return sorted((v["fnv1a64"], v["norm"], v["max_abs"]) for v in values)


def analyze():
    manifests = {
        "fixed": verify(RUN, PIN),
        "qualification": verify(QUAL, QUAL_PIN),
        "original_control": verify(CONTROL, CONTROL_PIN),
    }
    assert (
        sha(A / "raw.jsonl")
        == "9a4f2711f558b80ac58c803406971f43be7c44f4c5e64f7a50c728e2a7440e55"
    )
    control_analysis = runpy.run_path(
        str(
            BASE
            / "current/docs/validation/mjpc_faithful_original_observation_20261004/analyze.py"
        )
    )["analyze"]()
    result = read(RUN / "RESULT.json")
    qual = read(QUAL / "packet.json")
    original_qual = read(
        BASE
        / "faithful-original-observation/_runs/mjpc_faithful_original_qualification_20261003_v4/packet.json"
    )
    for key in ("libraries", "task_xml", "canonical_xml", "loader"):
        assert qual["runtime"][key] == original_qual["runtime"][key]
    for name, h in original_qual["runtime"]["files"].items():
        if name not in ("go2_mjpc_controller_fd_original", "build-provenance.json"):
            assert qual["runtime"]["files"][name] == h
    historical = rows(A / "raw.jsonl")
    logs = [rows(RUN / f"fixed_repeat{i}/native.jsonl") for i in (1, 2)]
    originals = [rows(CONTROL / f"original_repeat{i}/native.jsonl") for i in (1, 2)]
    traces = [rows(RUN / f"fixed_repeat{i}/fd-trace.jsonl") for i in (1, 2)]
    predictions = [rows(RUN / f"fixed_repeat{i}/predictions.jsonl") for i in (1, 2)]
    permutation = [3, 4, 5, 0, 1, 2, 9, 10, 11, 6, 7, 8]
    per_call = []
    completed = attempted = reserved = upper = 0
    fixed_vs_original = []
    repeat_comparisons = []
    for i, native in enumerate(logs, 1):
        trial = RUN / f"fixed_repeat{i}"
        assert (trial / "native.stderr.log").stat().st_size == 0
        assert native[1] == {
            "request": "reset",
            "response": {"ok": True, "reset": True},
        }
        assert [r["tick"] for r in native[2:]] == list(range(11))
        ledger = rows(trial / "optimizer-attempts.jsonl")
        assert [r["tick"] for r in ledger] == [0, 10]
        assert all(r["reserved_upper_bound"] == 4096 for r in ledger)
        attempted += len(ledger)
        reserved += sum(r["reserved_upper_bound"] for r in ledger)
        for row in native[2:]:
            tick = row["tick"]
            old = historical[tick]
            q = old["qpos"][:7] + [old["qpos"][7 + j] for j in permutation]
            v = old["qvel"][:6] + [old["qvel"][6 + j] for j in permutation]
            request = (
                "step "
                + str(int(tick in (0, 10)))
                + " "
                + " ".join(
                    format(float(x), ".17g")
                    for x in [old["sim_time_s"], *old["command"], *q, *v]
                )
            )
            assert row["request"] == request
            assert (
                row["request"]
                == originals[0][tick + 2]["request"]
                == originals[1][tick + 2]["request"]
            )
            response = row["response"]
            assert response["ok"] is True and response["current_rollout_valid"] is True
            assert response["replanned"] is (tick in (0, 10))
            if tick in (0, 10):
                call = 1 if tick == 0 else 2
                diag = response["diagnostic"]
                for key, value in {
                    "fd_call_count": call * 36,
                    "fd_step_upper_bound_count": call * 1752,
                    "rollout_mj_step_count": call * 700,
                    "private_step_upper_bound_reserved": call * 4096,
                    "policy_id": call,
                    "private_step_limit": 614400,
                }.items():
                    assert type(diag[key]) is int and diag[key] == value
                trace = traces[i - 1][call - 1]
                assert trace["call_index"] == call and trace["index_count"] == 36
                assert [e["t"] for e in trace["events"]] == list(range(36))
                assert sum(e["t"] == 34 for e in trace["events"]) == 1
                completed += 1
                upper += 1752 + 700
                per_call.append(
                    {
                        "repeat": i,
                        "tick": tick,
                        "fd_calls": 36,
                        "fd_upper": 1752,
                        "rollout_steps": 700,
                        "accounted_upper": 2452,
                        "reserved": 4096,
                    }
                )
            for j, original in enumerate(originals, 1):
                before = original[tick + 2]["response"]
                fixed_vs_original.append(
                    {
                        "fixed_repeat": i,
                        "original_repeat": j,
                        "tick": tick,
                        "q_des_max_abs_diff": maximum(
                            response["q_des"], before["q_des"]
                        ),
                        "cost_abs_diff": abs(response["cost"] - before["cost"]),
                    }
                )
    assert (attempted, completed, reserved, upper) == (4, 4, 16384, 9808)
    accounting = read(RUN / "accounting.json")
    assert (
        accounting["accounting_complete"] is True
        and not accounting["accounting_errors"]
    )
    assert accounting["unverified_reserved_upper"] == 0
    assert (
        accounting["private_accounted_upper"] == upper
        and accounting["private_reserved"] == reserved
    )
    for tick in range(11):
        a, b = [log[tick + 2]["response"] for log in logs]
        repeat_comparisons.append(
            {
                "tick": tick,
                "q_des_max_abs_diff": maximum(a["q_des"], b["q_des"]),
                "cost_abs_diff": abs(a["cost"] - b["cost"]),
            }
        )
    optimizer = []
    for call in (0, 1):
        histories = [p[call]["planner_history"] for p in predictions]
        events = [t[call]["events"] for t in traces]
        seeds = [
            {
                "knot": a["t"],
                "slot": slot,
                "hashes": [
                    a["warmstart_before_fnv1a64"],
                    b["warmstart_before_fnv1a64"],
                ],
                "norms": [a["warmstart_before_norm"], b["warmstart_before_norm"]],
            }
            for slot, (a, b) in enumerate(zip(*events))
            if a["warmstart_before_fnv1a64"] != b["warmstart_before_fnv1a64"]
        ]
        optimizer.append(
            {
                "call": call + 1,
                "tick": call * 10,
                "first_logged_seed_difference": seeds[0] if seeds else None,
                "different_seed_knots": [r["knot"] for r in seeds],
                "t34_tasks_per_repeat": [
                    sum(e["t"] == 34 for e in es) for es in events
                ],
                "t34_jacobian_hashes": [
                    t[call]["jacobian_t34_fnv1a64"] for t in traces
                ],
                "selected_policy_hashes": [
                    h["post_policy"]["fnv1a64"] for h in histories
                ],
                "candidate_ids": [p[call]["candidate_id"] for p in predictions],
                "pre_worker_assignments_equal": histories[0]["worker_warmstart"]["pre"]
                == histories[1]["worker_warmstart"]["pre"],
                "post_worker_assignments_equal": histories[0]["worker_warmstart"][
                    "post"
                ]
                == histories[1]["worker_warmstart"]["post"],
                "post_worker_summary_multisets_equal": signature(
                    histories[0]["worker_warmstart"]["post"]
                )
                == signature(histories[1]["worker_warmstart"]["post"]),
                "pre_policy_summaries_equal": histories[0]["pre_policy"]
                == histories[1]["pre_policy"],
                "pre_previous_policy_summaries_equal": histories[0][
                    "pre_previous_policy"
                ]
                == histories[1]["pre_previous_policy"],
                "selected_trajectory_max_abs_differences": {
                    key: max(
                        maximum(a[key], b[key])
                        for a, b in zip(
                            predictions[0][call]["states"],
                            predictions[1][call]["states"],
                        )
                    )
                    for key in ("qpos", "qvel", "nominal_position_action")
                },
            }
        )
    output_difference = max(r["q_des_max_abs_diff"] for r in repeat_comparisons)
    exact_difference = output_difference > 0 or any(
        r["cost_abs_diff"] > 0 for r in repeat_comparisons
    )
    return {
        "schema": 1,
        "status": "VERIFIED_SINGLE_FACTOR_OBSERVATION",
        "producer_head": result["head"],
        "evidence": {
            "run": str(RUN),
            "manifest_sha256": PIN,
            "qualification_manifest_sha256": QUAL_PIN,
            "control_manifest_sha256": CONTROL_PIN,
            "manifest_members": manifests,
        },
        "intervention": "unique FD indices only; warmstart untouched",
        "accounting": {
            "optimizer_calls": completed,
            "private_reserved": reserved,
            "private_accounted_upper": upper,
            "canonical_steps": 0,
            "formal_scientific_attempts": 0,
            "per_call": per_call,
            "budget_status": "CLOSED",
        },
        "wire_inputs_verified": 22,
        "fixed_repeat_comparisons": repeat_comparisons,
        "fixed_vs_original_comparisons": fixed_vs_original,
        "optimizer": optimizer,
        "original_repeat_q_des_max_abs_diff": control_analysis["repeat_comparisons"][
            -1
        ]["q_des_max_abs_diff"],
        "original_repeat_threshold_fraction": control_analysis["repeat_comparisons"][
            -1
        ]["q_des_max_abs_diff"]
        / 1e-9,
        "tolerance": 1e-9,
        "all_comparisons_within_original_tolerance": all(
            max(r["q_des_max_abs_diff"], r["cost_abs_diff"]) <= 1e-9
            for r in repeat_comparisons + fixed_vs_original
        ),
        "not_exactly_repeatable": exact_difference,
        "duplicate_parallel_t34_writes_necessary_for_observed_repeat_drift": False
        if exact_difference
        else "UNRESOLVED",
        "interpretation": "Drift survives without duplicate t34; duplicate simultaneous writes are not necessary."
        if exact_difference
        else "No selected-output drift observed; deduplication also changes worker histories, so race versus history contribution unresolved.",
        "causal_limits": [
            "two repeats cannot estimate frequency",
            "hidden worker histories not controlled across source variants",
            "not a warmstart-only intervention",
            "does not prove unique cause of historical A/reference drift",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(analyze(), indent=2, sort_keys=True, allow_nan=False))
