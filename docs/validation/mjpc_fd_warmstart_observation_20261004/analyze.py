"""Read sealed matched contrast; no simulator, calls, or writes."""

import hashlib
import json
from pathlib import Path

BASE = Path("/home/che/dev/go2-workspace")
RUN = BASE / "fd-warmstart-observation/_runs/mjpc_fd_warmstart_observation_20261004"
QUAL = RUN.parent / "mjpc_fd_warmstart_qualification_20261004_v2"
A = (
    BASE
    / "current/_runs/mjpc_adaptation_diagnostic_execution_20261002/original_capture_20261002T164948Z"
)
OLD = BASE / "faithful-dedup-observation/_runs/mjpc_faithful_dedup_observation_20261004"
PIN = "43d68bb104338cd322fb1ae1742b84b374f920c6d809fd17989dedde42118844"
QUAL_PIN = "c3c755d4abd1aba5250348d6238f9886e10acb4e50055a2f5c4ee2b3cb15739c"


def read(p):
    return json.loads(p.read_text())


def lines(p):
    return [json.loads(s) for s in p.read_text().splitlines()]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def maximum(a, b):
    assert len(a) == len(b)
    return max(abs(x - y) for x, y in zip(a, b))


def verify(p, pin):
    assert sha(p / "manifest.json") == pin
    m = read(p / "manifest.json")
    assert set(m) == {
        x.relative_to(p).as_posix()
        for x in p.rglob("*")
        if x.is_file() and x != p / "manifest.json"
    }
    assert all(sha(p / n) == h for n, h in m.items())
    return len(m)


def zero_hash():
    h = 14695981039346656037
    for _ in range(18 * 8):
        h = (h * 1099511628211) & ((1 << 64) - 1)
    return format(h, "016x")


def analyze():
    counts = {
        "raw": verify(RUN, PIN),
        "qualification": verify(QUAL, QUAL_PIN),
        "previous_unique_index": verify(
            OLD, "2e5fa41e23f9334037c59aeffe0fc064473286bb68af2d81a1006a9f546aecb2"
        ),
    }
    assert (
        sha(A / "raw.jsonl")
        == "9a4f2711f558b80ac58c803406971f43be7c44f4c5e64f7a50c728e2a7440e55"
    )
    source = lines(A / "raw.jsonl")
    result = read(RUN / "RESULT.json")
    packet = read(QUAL / "packet.json")
    permutation = [3, 4, 5, 0, 1, 2, 9, 10, 11, 6, 7, 8]
    data = {}
    per_call = []
    all_seed_records = 0
    for mode in ("retain", "zero"):
        trials = []
        for repeat in (1, 2):
            root = RUN / (mode + "_repeat" + str(repeat))
            native = lines(root / "native.jsonl")
            trace = lines(root / "fd-trace.jsonl")
            pred = lines(root / "predictions.jsonl")
            seed = lines(root / "warmstart-seeds.jsonl")
            ledger = lines(root / "optimizer-attempts.jsonl")
            assert [r["tick"] for r in ledger] == [0, 10]
            assert all(r["reserved_upper_bound"] == 4096 for r in ledger)
            assert native[1] == {
                "request": "reset",
                "response": {"ok": True, "reset": True},
            }
            assert (root / "native.stderr.log").stat().st_size == 0
            assert [r["tick"] for r in native[2:]] == list(range(11))
            assert len(trace) == len(pred) == 2
            assert len(seed) == 73 and seed[0]["mode"] == mode
            assert (
                Path(seed[0]["delegate"]).resolve()
                == QUAL / "runtime/lib/libmujoco.so.3.3.6"
            )
            assert {s["index"] for s in seed[1:]} == set(range(1, 73))
            for s in seed[1:]:
                assert s["end_ns"] >= s["start_ns"]
                if mode == "zero":
                    assert (
                        s["effective_zero"] is True
                        and s["effective_hash"] == zero_hash()
                    )
                else:
                    assert s["before_hash"] == s["effective_hash"]
            all_seed_records += 72
            for row in native[2:]:
                tick = row["tick"]
                old = source[tick]
                q = old["qpos"][:7] + [old["qpos"][7 + j] for j in permutation]
                v = old["qvel"][:6] + [old["qvel"][6 + j] for j in permutation]
                expected = (
                    "step "
                    + str(int(tick in (0, 10)))
                    + " "
                    + " ".join(
                        format(float(x), ".17g")
                        for x in [old["sim_time_s"], *old["command"], *q, *v]
                    )
                )
                assert row["request"] == expected
                r = row["response"]
                assert r["ok"] is True and r["replanned"] is (tick in (0, 10))
                if tick in (0, 10):
                    c = 1 if tick == 0 else 2
                    d = r["diagnostic"]
                    expected = {
                        "fd_call_count": 36 * c,
                        "fd_step_upper_bound_count": 1752 * c,
                        "rollout_mj_step_count": 700 * c,
                        "private_step_upper_bound_reserved": 4096 * c,
                        "private_step_limit": 614400,
                        "policy_id": c,
                    }
                    assert all(
                        type(d[k]) is int and d[k] == val for k, val in expected.items()
                    )
                    t = trace[c - 1]
                    assert t["call_index"] == c and t["index_count"] == 36
                    assert [e["t"] for e in t["events"]] == list(range(36))
                    per_call.append(
                        {
                            "mode": mode,
                            "repeat": repeat,
                            "tick": tick,
                            "upper": 2452,
                            "reserved": 4096,
                        }
                    )
            loaded = read(root / "loaded-libraries.json")
            assert (
                loaded["lib/libgo2_fd_warmstart.so"]
                == packet["runtime"]["fd_warmstart_shim"]["sha256"]
            )
            assert all(packet["runtime"]["files"][n] == h for n, h in loaded.items())
            trials.append(
                {
                    "native": native,
                    "traces": trace,
                    "predictions": pred,
                    "seed_records": seed,
                }
            )
        data[mode] = trials
    assert len(per_call) == 8 and all_seed_records == 288
    budget = read(RUN / "accounting.json")
    assert budget["accounting_complete"] and not budget["accounting_errors"]
    assert (
        budget["reserved_optimizer_calls"] == budget["completed_optimizer_calls"] == 8
    )
    assert (
        budget["private_accounted_upper"] == 19616
        and budget["private_reserved"] == 32768
    )
    assert budget["unverified_reserved_upper"] == 0
    arms = {}
    for mode, trials in data.items():
        pairs = []
        for tick in range(11):
            a, b = [x["native"][tick + 2]["response"] for x in trials]
            pairs.append(
                {
                    "tick": tick,
                    "q_des_max_abs_diff": maximum(a["q_des"], b["q_des"]),
                    "cost_abs_diff": abs(a["cost"] - b["cost"]),
                }
            )
        calls = []
        for call in range(2):
            p = [x["predictions"][call] for x in trials]
            t = [x["traces"][call] for x in trials]
            calls.append(
                {
                    "tick": call * 10,
                    "t34_jacobian_hashes": [x["jacobian_t34_fnv1a64"] for x in t],
                    "policy_hashes": [
                        x["planner_history"]["post_policy"]["fnv1a64"] for x in p
                    ],
                    "candidate_ids": [x["candidate_id"] for x in p],
                    "nominal_action_max_abs_diff": max(
                        maximum(
                            a["nominal_position_action"], b["nominal_position_action"]
                        )
                        for a, b in zip(p[0]["states"], p[1]["states"])
                    ),
                    "qpos_max_abs_diff": max(
                        maximum(a["qpos"], b["qpos"])
                        for a, b in zip(p[0]["states"], p[1]["states"])
                    ),
                    "qvel_max_abs_diff": max(
                        maximum(a["qvel"], b["qvel"])
                        for a, b in zip(p[0]["states"], p[1]["states"])
                    ),
                    "post_worker_assignments_equal": p[0]["planner_history"][
                        "worker_warmstart"
                    ]["post"]
                    == p[1]["planner_history"]["worker_warmstart"]["post"],
                }
            )
        arms[mode] = {
            "repeat_comparisons": pairs,
            "calls": calls,
            "exact_q_des_and_cost": all(
                r["q_des_max_abs_diff"] == r["cost_abs_diff"] == 0 for r in pairs
            ),
            "within_1e_9": all(
                max(r["q_des_max_abs_diff"], r["cost_abs_diff"]) <= 1e-9 for r in pairs
            ),
        }
    cross = []
    for tick in (0, 10):
        diffs = []
        for a in data["retain"]:
            for b in data["zero"]:
                x, y = (
                    a["native"][tick + 2]["response"],
                    b["native"][tick + 2]["response"],
                )
                diffs.append(
                    {
                        "q_des": maximum(x["q_des"], y["q_des"]),
                        "cost": abs(x["cost"] - y["cost"]),
                    }
                )
        cross.append(
            {
                "tick": tick,
                "max_q_des_difference": max(r["q_des"] for r in diffs),
                "max_cost_difference": max(r["cost"] for r in diffs),
            }
        )
    if arms["retain"]["exact_q_des_and_cost"]:
        verdict = "INCONCLUSIVE_RETAIN_PAIR_EXACT"
    elif arms["zero"]["exact_q_des_and_cost"]:
        verdict = "FD_WARMSTART_CLEAR_REMOVES_OBSERVED_REPEAT_DRIFT"
    else:
        verdict = "FD_WARMSTART_CLEAR_ALONE_INSUFFICIENT"
    return {
        "status": "VERIFIED_MATCHED_FD_WARMSTART_OBSERVATION",
        "producer_head": result["head"],
        "raw_manifest_sha256": PIN,
        "qualification_manifest_sha256": QUAL_PIN,
        "manifest_members": counts,
        "budget": {
            "optimizer_calls": 8,
            "private_accounted_upper": 19616,
            "private_reserved": 32768,
            "canonical_steps": 0,
            "formal_live_attempts": 0,
            "status": "CLOSED",
            "per_call": per_call,
        },
        "wire_inputs_verified": 44,
        "intercepted_real_FD_calls_verified": 288,
        "zero_effective_seed_hash": zero_hash(),
        "arms": arms,
        "cross_mode_comparisons": cross,
        "outcome": verdict,
        "tolerance": 1e-9,
        "limitations": [
            "FD incoming warmstart only; rollout warmstarts retained",
            "two repeats cannot estimate frequency",
            "no new canonical feedback or historical A stop reproduction",
            "same logging exists in both arms, but scheduling effects remain downstream",
        ],
        "historical_feedback_evidence": "Old traces first differ at target tick10 then state tick11, consistent with amplification; this private test does not establish cause of886/1287 stops.",
    }


if __name__ == "__main__":
    print(json.dumps(analyze(), indent=2, sort_keys=True, allow_nan=False))
