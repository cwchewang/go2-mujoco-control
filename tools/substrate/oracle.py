"""Independent algebraic checks; deliberately no runtime/controller imports."""

import math
import numpy as np


def verify_algebra(rows, protocol, lower, upper, layout):
    initial = rows[0]["qpos"]
    errors = []
    for row in rows:
        tick = row["tick"]
        scale = min(
            1.0,
            max(0.0, (tick - protocol["zero_command_ticks"]) / protocol["ramp_ticks"]),
        )
        if not np.allclose(
            row["command"], np.array(protocol["command"]) * scale, atol=1e-14, rtol=0
        ):
            raise ValueError("independent command oracle mismatch")
        q, dq = np.array(row["qpos"]), np.array(row["qvel"])
        threshold = protocol["thresholds"]
        tilt = math.acos(max(-1.0, min(1.0, 1 - 2 * (q[4] ** 2 + q[5] ** 2))))
        reason = None
        if not (np.isfinite(q).all() and np.isfinite(dq).all()):
            reason = "nonfinite"
        elif abs(math.sqrt(sum(float(v) ** 2 for v in q[3:7])) - 1) > 1e-6:
            reason = "orientation"
        elif row["warning_count"]:
            reason = "physics_warning"
        elif row["forbidden_contacts"]:
            reason = "nonfoot_contact"
        elif (
            not threshold["height_min_m"] <= q[2] <= threshold["height_max_m"]
            or tilt > threshold["tilt_max_rad"]
        ):
            reason = "posture"
        elif abs(q[1] - initial[1]) > threshold["lateral_max_m"]:
            reason = "lateral"
        if row["wall_time_s"] >= protocol["wall_timeout_s"]:
            reason = reason or "wall_timeout"
        if reason != row["failure"]:
            raise ValueError("independent safety oracle mismatch")
        if row["action"] is not None:
            target = row["target"]
            order = [target["joint_names"].index(name) for name in layout["names"]]
            values = {
                key: np.array(target[key])[order]
                for key in (
                    "position_target",
                    "velocity_target",
                    "kp",
                    "kd",
                    "feedforward",
                )
            }
            pd = values["kp"] * (
                values["position_target"] - q[layout["qadr"]]
            ) + values["kd"] * (values["velocity_target"] - dq[layout["vadr"]])
            expected = np.minimum(np.maximum(values["feedforward"] + pd, lower), upper)
            if not np.allclose(expected, row["action"]["ctrl"], rtol=0, atol=1e-12):
                raise ValueError("independent torque oracle mismatch")
        if tick >= protocol["measurement_start_tick"]:
            errors.append(abs(float(dq[0]) - protocol["command"][0]))
    return {
        "progress_m": rows[-1]["qpos"][0] - initial[0],
        "vx_mae_mps": math.fsum(errors) / len(errors) if errors else None,
        "contact_scope": "recorded contacts; model reconstruction is separate",
    }
