"""Independent, strict recomputation of the prospective flat compatibility gate."""

import math
import hashlib
import json
import numpy as np
from .contracts import vector, Proprioception, TorqueCommand
from .episode import command_at, safety


def analyze(rows, protocol, lower, upper, layout, reference_trace_sha256=None):
    if not rows:
        raise ValueError("empty capture")
    initial_x, initial_y = rows[0]["qpos"][:2]
    errors, latencies, saturated = [], [], 0
    first_failure = None
    previous_target = None
    decimation = round(protocol["control_period_s"] / protocol["physics_period_s"])
    for tick, row in enumerate(rows):
        if type(row["tick"]) is not int or row["tick"] != tick:
            raise ValueError("missing or duplicate tick")
        if type(row["sim_time_s"]) not in (int, float) or not math.isclose(row["sim_time_s"], tick * protocol["physics_period_s"], abs_tol=1e-9, rel_tol=0):
            raise ValueError("clock mismatch")
        qpos, qvel = vector(row["qpos"], 19, "qpos"), vector(row["qvel"], 18, "qvel")
        if row["initial_y"] != initial_y:
            raise ValueError("state invariant mismatch")
        if type(row["warning_count"]) is not int or row["warning_count"] < 0:
            raise ValueError("invalid warning count")
        if not isinstance(row["forbidden_contacts"], list) or not isinstance(row["supports"], list):
            raise ValueError("invalid contact evidence")
        if any(x not in ("FR", "FL", "RR", "RL") for x in row["supports"]) or len(set(row["supports"])) != len(row["supports"]):
            raise ValueError("invalid support evidence")
        if row["terminal_reason"] and tick != len(rows) - 1:
            raise ValueError("samples after termination")
        if tick > protocol["horizon_ticks"]:
            raise ValueError("horizon exceeded")
        wall = row["wall_time_s"]
        if type(wall) not in (int, float) or not math.isfinite(wall) or wall < 0:
            raise ValueError("invalid wall time")
        reason = safety(row, protocol)
        if wall >= protocol["wall_timeout_s"]:
            reason = reason or "wall_timeout"
        if row["failure"] != reason:
            raise ValueError("failure label disagrees with raw state")
        if reason and first_failure is None:
            first_failure = {"tick": tick, "reason": reason}
        if row["command"] != command_at(protocol, tick).tolist():
            raise ValueError("command schedule mismatch")
        if row["action"] is not None:
            if reason or tick == protocol["horizon_ticks"] or row["terminal_reason"]:
                raise ValueError("action after terminal condition")
            action = row["action"]
            ff, pd, total, ctrl = [vector(action[k], 12, k) for k in ("feedforward", "pd", "total_unclipped", "ctrl")]
            if not np.array_equal(ff + pd, total) or not np.array_equal(np.clip(total, lower, upper), ctrl):
                raise ValueError("torque accounting mismatch")
            mask = np.asarray(action["saturated"])
            if mask.shape != (12,) or mask.dtype.kind != "b" or not np.array_equal(mask, (total < lower) | (total > upper)):
                raise ValueError("saturation evidence mismatch")
            saturated += int(mask.sum())
            target = row["target"]
            packet = TorqueCommand(**target)
            obs = Proprioception(tuple(layout["names"]), qpos[layout["qadr"]], qvel[layout["vadr"]], qpos[3:7], qvel[3:6])
            recomputed = packet.resolve(obs, lower, upper, layout["names"])
            if any(not np.array_equal(recomputed[k], action[k]) for k in recomputed):
                raise ValueError("PD or joint mapping differs from raw state and target")
            if tick % decimation:
                if row["policy_wall_s"] is not None or target != previous_target:
                    raise ValueError("policy updated outside control tick")
            else:
                duration = row["policy_wall_s"]
                if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
                    raise ValueError("missing policy timing")
                latencies.append(duration)
            previous_target = target
        elif tick != len(rows) - 1 or not row["terminal_reason"]:
            raise ValueError("missing action before endpoint")
        if tick >= protocol["measurement_start_tick"]:
            errors.append(abs(float(qvel[0]) - protocol["command"][0]))
    last = rows[-1]
    if not last["terminal_reason"] or last["terminal_reason"] != (last["failure"] or "horizon"):
        raise ValueError("incomplete or inconsistent terminal evidence")
    if last["terminal_reason"] == "horizon" and last["tick"] != protocol["horizon_ticks"]:
        raise ValueError("premature horizon")
    progress = last["qpos"][0] - initial_x
    mae = float(np.mean(errors)) if errors else None
    trace = [{k: v for k, v in row.items() if k not in ("wall_time_s", "policy_wall_s")} for row in rows]
    signature = hashlib.sha256(json.dumps(trace, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()
    repeatable = reference_trace_sha256 is None or signature == reference_trace_sha256
    passed = repeatable and first_failure is None and last["tick"] == protocol["horizon_ticks"] and progress >= protocol["thresholds"]["progress_min_m"] and mae is not None and mae <= protocol["thresholds"]["vx_mae_max_mps"]
    return {
        "verdict": "PASS" if passed else "FAIL", "first_failure": first_failure,
        "trace_sha256": signature, "repeatability_matches": repeatable,
        "terminal_reason": last["terminal_reason"], "frames": len(rows),
        "progress_m": progress, "vx_mae_mps": mae,
        "saturated_motor_ticks": saturated,
        "policy_updates": len(latencies),
        "policy_wall_p50_s": float(np.median(latencies)) if latencies else None,
        "policy_wall_p95_s": float(np.quantile(latencies, .95)) if latencies else None,
        "wall_time_s": last["wall_time_s"],
        "real_time_factor": last["sim_time_s"] / last["wall_time_s"] if last["wall_time_s"] > 0 else None,
    }
