"""Pinned upstream deployment semantics with isolated, zero-step telemetry."""

import ast
import hashlib
import io
import json
import math
import time
import numpy as np

from .contracts import POLICY_JOINTS, Proprioception
from .diagnose import joint_map, yaml_literals
from .integrity import digest, strict_json
from .rl import FrozenPolicy, observation45


class UnsupportedSceneError(ValueError):
    """The runner cannot make its declared telemetry claims for this scene."""


def reference_inputs(root):
    lock = strict_json((root / "tools/substrate/rl_reference.lock.json").read_text())
    directory = root / ".substrate/upstream-go2-30e74dc5"
    for name, expected in lock["files"].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or digest(path) != expected:
            raise ValueError("upstream reference changed: " + name)
    return directory, lock


class SourcePolicy:
    """Independent source assembly; only pure helper AST from the pinned file."""

    def __init__(self, reference, checkpoint, expected):
        import torch

        data = checkpoint.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("checkpoint changed")
        self.torch = torch
        self.policy = torch.jit.load(io.BytesIO(data), map_location="cpu").eval()
        self.config = yaml_literals(reference / "deploy/deploy_mujoco/configs/go2.yaml")
        c = self.config
        if (
            tuple(c["mujoco_joint_names"]) != POLICY_JOINTS
            or tuple(c["model_joint_names"]) != POLICY_JOINTS
        ):
            raise ValueError("pinned source joint order changed")
        source = ast.parse(
            (reference / "deploy/deploy_mujoco/deploy_go2.py").read_text()
        )
        pure = ast.Module(
            body=[
                n
                for n in source.body
                if isinstance(n, ast.FunctionDef)
                and n.name in ("pd_control", "get_gravity_orientation")
            ],
            type_ignores=[],
        )
        self.functions = {"np": np}
        exec(compile(pure, "pinned-source-helpers", "exec"), self.functions)
        self.default = np.array(c["default_angles"], dtype=np.float32)
        self.previous = np.zeros(12, dtype=np.float32)

    def observation(self, obs, command):
        c = self.config
        result = np.zeros(c["num_obs"], dtype=np.float32)
        result[:3] = obs.angular_velocity_body * c["ang_vel_scale"]
        result[3:6] = self.functions["get_gravity_orientation"](obs.quaternion_wxyz)
        result[6:9] = np.array(command, dtype=np.float32) * np.array(
            c["cmd_scale"], dtype=np.float32
        )
        result[9:21] = (obs.position - self.default) * c["dof_pos_scale"]
        result[21:33] = obs.velocity * c["dof_vel_scale"]
        result[33:45] = self.previous
        return result

    def act(self, obs, command):
        assembled = self.observation(obs, command)
        with self.torch.inference_mode():
            result = self.policy(self.torch.from_numpy(assembled).unsqueeze(0))
        action = (
            (result[0] if isinstance(result, tuple) else result)
            .detach()
            .cpu()
            .numpy()
            .squeeze()
        )
        if action.shape != (12,) or not np.isfinite(action).all():
            raise ValueError("invalid source policy output")
        self.previous = action.copy()
        return assembled, action * self.config["action_scale"] + self.default


class Plant:
    def __init__(self, scene, case, dt):
        import mujoco as mj

        self.mj = mj
        self.model = m = mj.MjModel.from_xml_path(str(scene))
        m.opt.timestep = dt
        self.data = d = mj.MjData(m)
        self.telemetry = mj.MjData(m)
        layout = joint_map(mj, m)
        if set(layout) != set(POLICY_JOINTS) or m.nu != 12 or m.nq != 19 or m.nv != 18:
            raise ValueError("unexpected embodiment")
        self.qadr = [layout[n]["q"] for n in POLICY_JOINTS]
        self.vadr = [layout[n]["v"] for n in POLICY_JOINTS]
        self.aids = [layout[n]["a"] for n in POLICY_JOINTS]
        if not np.all(m.actuator_gear[:, 0] == 1) or np.any(m.actuator_gear[:, 1:]):
            raise ValueError("non-unit transmission")
        self.base = int(m.jnt_bodyid[0])
        if mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, self.base) not in (
            "base",
            "base_link",
        ):
            raise ValueError("unknown floating base")
        self.robot_bodies = set()
        for body in range(1, m.nbody):
            parent = body
            while parent > 0:
                if parent == self.base:
                    self.robot_bodies.add(body)
                    break
                parent = int(m.body_parentid[parent])
        self.feet = []
        for leg in ("FL", "FR", "RL", "RR"):
            body = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, leg + "_calf")
            matches = [
                g
                for g in range(m.ngeom)
                if m.geom_bodyid[g] == body
                and m.geom_type[g] == mj.mjtGeom.mjGEOM_SPHERE
                and m.geom_contype[g]
                and abs(m.geom_size[g, 0] - 0.022) < 1e-9
            ]
            if len(matches) != 1:
                raise ValueError("ambiguous foot: " + leg)
            self.feet.append(matches[0])
        self.terrain = [
            g
            for g in range(m.ngeom)
            if m.geom_bodyid[g] == 0 and (m.geom_contype[g] or m.geom_conaffinity[g])
        ]
        if self.base < 1 or not self.terrain:
            raise ValueError("missing base/terrain")
        if "scene_geoms" in case:
            foreign = [
                g
                for g in range(m.ngeom)
                if m.geom_bodyid[g] != 0
                and m.geom_bodyid[g] not in self.robot_bodies
                and (m.geom_contype[g] or m.geom_conaffinity[g])
            ]
            if foreign:
                names = [mj.mj_id2name(m, mj.mjtObj.mjOBJ_GEOM, g) for g in foreign]
                raise UnsupportedSceneError(
                    "collision geometry is attached outside the Go2/world contract: "
                    + repr(sorted(str(name) for name in names))
                )
            actual = {
                mj.mj_id2name(m, mj.mjtObj.mjOBJ_GEOM, g)
                for g in self.terrain
            }
            expected = set(case["scene_geoms"])
            if None in actual or actual != expected:
                raise UnsupportedSceneError(
                    "world collision geometry contract mismatch: expected "
                    + repr(sorted(expected))
                    + ", got "
                    + repr(sorted(name for name in actual if name is not None))
                )
        for g in self.terrain:
            if m.geom_type[g] not in (
                mj.mjtGeom.mjGEOM_PLANE,
                mj.mjtGeom.mjGEOM_BOX,
            ):
                raise UnsupportedSceneError(
                    "unsupported world terrain geometry: "
                    + str(mj.mj_id2name(m, mj.mjtObj.mjOBJ_GEOM, g))
                )
        if case["reset"] == "source":
            # Source MjData defaults; mapping only matters in the model-only arm.
            d.qpos[:7] = [0, 0, 0.445, 1, 0, 0, 0]
            d.qpos[self.qadr] = 0
        elif case["reset"] == "shared_home":
            d.qpos[:7] = [0, 0, 0.27, 1, 0, 0, 0]
            d.qpos[self.qadr] = [0, 0.9, -1.8] * 4
        else:
            raise ValueError("unknown reset")
        # No mj_forward on the live MjData: preserve original solver startup.
        self.steps = 0

    def observe(self):
        d = self.data
        return Proprioception(
            POLICY_JOINTS,
            d.qpos[self.qadr],
            d.qvel[self.vadr],
            d.qpos[3:7],
            d.qvel[3:6],
        )

    def snapshot(self, tick):
        m, d, t = self.model, self.data, self.telemetry
        for name in (
            "qpos",
            "qvel",
            "act",
            "ctrl",
            "qacc_warmstart",
            "qfrc_applied",
            "xfrc_applied",
            "mocap_pos",
            "mocap_quat",
            "eq_active",
            "userdata",
        ):
            getattr(t, name)[:] = getattr(d, name)
        t.time = d.time
        self.mj.mj_forward(m, t)
        ground = []
        base_contacts = []
        for contact in t.contact:
            if contact.efc_address < 0:
                continue
            a, b = int(contact.geom1), int(contact.geom2)
            if a in self.terrain or b in self.terrain:
                ground.append([a, b])
                if m.geom_bodyid[a] == self.base or m.geom_bodyid[b] == self.base:
                    base_contacts.append([a, b])
        # Exact vertical query for this protocol's horizontal planes/boxes.
        height = -math.inf
        for g in self.terrain:
            rotation = t.geom_xmat[g].reshape(3, 3)
            if not np.allclose(rotation[2], [0, 0, 1], atol=1e-12):
                raise UnsupportedSceneError("unsupported tilted terrain")
            if m.geom_type[g] == self.mj.mjtGeom.mjGEOM_PLANE:
                height = max(height, float(t.geom_xpos[g, 2]))
            elif m.geom_type[g] == self.mj.mjtGeom.mjGEOM_BOX:
                local = rotation.T @ (d.qpos[:3] - t.geom_xpos[g])
                if np.all(np.abs(local[:2]) <= m.geom_size[g, :2]):
                    height = max(height, float(t.geom_xpos[g, 2] + m.geom_size[g, 2]))
            else:
                raise UnsupportedSceneError("unsupported terrain type")
        return dict(
            tick=tick,
            time=float(d.time),
            qpos=d.qpos.tolist(),
            qvel=d.qvel.tolist(),
            terrain_height=height,
            clearance=float(d.qpos[2] - height),
            feet=t.geom_xpos[self.feet].tolist(),
            ground_contacts=ground,
            base_contacts=base_contacts,
            actuator_force_previous_ctrl=t.qfrc_actuator[self.vadr].tolist(),
            warnings=int(sum(w.number for w in d.warning)),
        )

    def control(self, target):
        d = self.data
        requested = (target - d.qpos[self.qadr]) * 20 + (0 - d.qvel[self.vadr]) * 0.5
        limits = self.model.actuator_ctrlrange[self.aids]
        applied = np.where(
            self.model.actuator_ctrllimited[self.aids],
            np.clip(requested, limits[:, 0], limits[:, 1]),
            requested,
        )
        if not np.isfinite(applied).all():
            raise ValueError("nonfinite torque")
        return requested, applied

    def step(self, applied):
        self.data.ctrl[self.aids] = applied
        self.mj.mj_step(self.model, self.data)
        self.steps += 1


def command_at(case, tick):
    command = next(row for row in reversed(case["commands"]) if tick >= row[0])
    if len(command) == 2:
        return [command[1], 0.0, 0.0]
    if len(command) == 4:
        return list(command[1:])
    raise ValueError("command rows must contain tick plus vx or tick plus vx/vy/wz")


def repeat_reference(case):
    if "repeat_of" in case:
        return case["repeat_of"]
    # Preserve the sealed v1 comparison semantics without changing its protocol.
    if case["id"] in ("source_repeat", "shared_adapter"):
        return "source_1"
    return None


def expected_reference_digest(protocol):
    """Return the frozen schema-2 reference digest and reject missing bindings."""
    if protocol.get("schema") != 2:
        return None
    cases = protocol.get("cases", [])
    if not cases or cases[0].get("id") != "flat_reference":
        raise ValueError("sealed reference must be the first capability case")
    expected = cases[0].get("reference_trace_sha256")
    if (
        not isinstance(expected, str)
        or len(expected) != 64
        or any(char not in "0123456789abcdef" for char in expected)
        or any("reference_trace_sha256" in case for case in cases[1:])
    ):
        raise ValueError("invalid sealed reference trace digest")
    return expected


def enforce_reference_digest(result, case, expected=None):
    """Classify a changed sealed reference after independently hashing its trace."""
    if expected is None:
        expected = case.get("reference_trace_sha256")
    if expected is None:
        return result
    observed = result["trace_sha256"]
    matched = observed == expected
    result["reference_integrity"] = {
        "expected_trace_sha256": expected,
        "observed_trace_sha256": observed,
        "matches": matched,
    }
    if not matched:
        result["verdict"] = "INTEGRITY_STOP"
        result["integrity_failure"] = "sealed_reference_trace_mismatch"
        result["failure_classes"] = ["INTEGRITY_STOP"]
    return result


def stop_after(protocol, verdict):
    if verdict in ("SAFETY_STOP", "INTEGRITY_STOP"):
        return True
    progression = protocol["progression"]
    if progression == "first_nonpass_stop":
        return verdict != "PASS"
    if progression == "performance_continue_safety_integrity_stop":
        return False
    raise ValueError("unknown campaign progression: " + str(progression))


def safety(row, protocol):
    q = row["qpos"]
    if not np.isfinite(q + row["qvel"]).all():
        return "nonfinite"
    if abs(np.linalg.norm(q[3:7]) - 1) > 1e-6:
        return "orientation"
    if row["warnings"]:
        return "physics_warning"
    if row["base_contacts"]:
        return "base_contact"
    tilt = math.acos(float(np.clip(1 - 2 * (q[4] ** 2 + q[5] ** 2), -1, 1)))
    if (
        tilt > protocol["safety"]["tilt_max"]
        or row["clearance"] < protocol["safety"]["clearance_min"]
    ):
        return "posture"
    if abs(q[1]) > protocol["safety"]["lateral_max"]:
        return "lateral"
    return None


def episode(plant, policy, case, protocol, emit, consume):
    target = np.array(
        [0.1, 0.8, -1.5, -0.1, 0.8, -1.5, 0.1, 1.0, -1.5, -0.1, 1.0, -1.5],
        dtype=np.float32,
    )
    consumed = False
    for tick in range(case["horizon_ticks"] + 1):
        row = plant.snapshot(tick)
        if abs(row["time"] - tick * protocol["physics_period_s"]) > 1e-8:
            raise ValueError("clock mismatch")
        row.update(
            command=command_at(case, tick),
            failure=safety(row, protocol),
            observation=None,
            policy_wall_s=None,
            requested=None,
            applied=None,
        )
        if not row["failure"] and tick < case["horizon_ticks"]:
            if (
                tick >= case["first_inference_tick"]
                and tick % protocol["decimation"] == 0
            ):
                obs = plant.observe()
                start = time.monotonic()
                if case["adapter"]:
                    assembled = observation45(
                        obs, row["command"], policy.previous_action
                    )
                    target = policy.act(obs, row["command"]).position_target
                else:
                    assembled, target = policy.act(obs, row["command"])
                row["policy_wall_s"] = time.monotonic() - start
                row["observation"] = assembled.tolist()
            requested, applied = plant.control(target)
            row.update(requested=requested.tolist(), applied=applied.tolist())
            if not consumed:
                consume()
                consumed = True
        row["target"] = target.tolist()
        emit(row)
        if row["failure"] or tick == case["horizon_ticks"]:
            break
        plant.step(applied)


def analyze(rows, case, protocol):
    if protocol.get("schema") == 2:
        return analyze_capability_map(rows, case, protocol)
    trajectory = hashlib.sha256()
    for row in rows:
        trajectory.update(
            json.dumps(
                {k: row[k] for k in ("qpos", "qvel", "target", "applied")},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
    complete = rows[-1]["tick"] == case["horizon_ticks"]
    windows = []
    for index, (start, speed) in enumerate(case["commands"]):
        end = (
            case["commands"][index + 1][0]
            if index + 1 < len(case["commands"])
            else case["horizon_ticks"]
        )
        selected = [
            r
            for r in rows
            if start + case["measurement_delay_ticks"] <= r["tick"] < end
        ]
        velocity = []
        for r in selected:
            w, x, y, z = r["qpos"][3:7]
            velocity.append(
                np.dot(
                    [1 - 2 * (y * y + z * z), 2 * (x * y + w * z), 2 * (x * z - w * y)],
                    r["qvel"][:3],
                )
            )
        error = np.asarray(velocity) - speed
        windows.append(
            dict(
                start_tick=start,
                end_tick=end,
                command=speed,
                samples=len(selected),
                mean_vx=float(np.mean(velocity)) if selected else None,
                mae=float(np.mean(np.abs(error))) if selected else None,
                rmse=float(np.sqrt(np.mean(error**2))) if selected else None,
            )
        )
    yaw = [
        math.atan2(
            2 * (r["qpos"][3] * r["qpos"][6] + r["qpos"][4] * r["qpos"][5]),
            1 - 2 * (r["qpos"][5] ** 2 + r["qpos"][6] ** 2),
        )
        for r in rows
    ]
    yaw = np.unwrap(yaw) - yaw[0]
    lateral = max(abs(r["qpos"][1] - rows[0]["qpos"][1]) for r in rows)
    tracking = complete and all(
        w["mae"] is not None
        and w["mae"]
        <= max(
            protocol["tracking_absolute_tolerance"],
            protocol["tracking_relative_tolerance"] * abs(w["command"]),
        )
        for w in windows
    )
    usable = (
        tracking
        and lateral <= protocol["flat_lateral_max"]
        and max(map(abs, yaw)) <= protocol["flat_yaw_max"]
    )
    if case.get(
        "reference_gate",
        case["id"] in ("source_1", "source_repeat", "shared_adapter"),
    ):
        usable = usable and windows[0]["mean_vx"] >= protocol["reference_mean_min"]
    goal_pass = None
    if "stairs_goal" in protocol:
        hold = maximum_hold = 0
        goal = protocol["stairs_goal"]
        for row in rows:
            reached = (
                row["qpos"][0] >= goal["base_x"]
                and abs(row["qpos"][1]) <= goal["lateral_max"]
                and min(f[0] for f in row["feet"]) >= goal["foot_x"]
            )
            hold = hold + 1 if reached else 0
            maximum_hold = max(maximum_hold, hold)
        goal_pass = maximum_hold > goal["hold_ticks"]
        if case["id"] == "source_stairs":
            usable = complete and goal_pass
    latency = [r["policy_wall_s"] for r in rows if r["policy_wall_s"] is not None]
    return dict(
        verdict="SAFETY_STOP"
        if rows[-1]["failure"]
        else ("PASS" if usable else "PERFORMANCE_FAIL"),
        failure=rows[-1]["failure"],
        complete=complete,
        steps=rows[-1]["tick"],
        trace_sha256=trajectory.hexdigest(),
        windows=windows,
        progress_m=rows[-1]["qpos"][0] - rows[0]["qpos"][0],
        lateral_max_m=lateral,
        yaw_max_rad=max(map(abs, yaw)),
        min_clearance_m=min(r["clearance"] for r in rows),
        goal_pass=goal_pass,
        policy_updates=len(latency),
        policy_p50_ms=float(np.median(latency)) * 1000 if latency else None,
        policy_p99_ms=float(np.quantile(latency, 0.99)) * 1000 if latency else None,
    )


def rotate_world_to_body(quaternion_wxyz, vector):
    """Use the pinned deployment's inverse-quaternion rotation convention."""
    w, x, y, z = quaternion_wxyz
    q = np.asarray([x, y, z], dtype=np.float64)
    v = np.asarray(vector, dtype=np.float64)
    return v * (2 * w * w - 1) - 2 * w * np.cross(q, v) + 2 * q * np.dot(q, v)


def body_twist(row):
    q = row["qpos"][3:7]
    v = row["qvel"]
    linear = rotate_world_to_body(q, v[:3])
    angular = rotate_world_to_body(q, v[3:6])
    return dict(vx=float(linear[0]), vy=float(linear[1]), wz=float(angular[2]))


def yaw_series(rows):
    result = []
    for row in rows:
        w, x, y, z = row["qpos"][3:7]
        result.append(
            math.atan2(
                2 * (w * z + x * y),
                1 - 2 * (y * y + z * z),
            )
        )
    return np.unwrap(result) - result[0]


def analyze_capability_map(rows, case, protocol):
    trajectory = hashlib.sha256()
    for row in rows:
        trajectory.update(
            json.dumps(
                {k: row[k] for k in ("qpos", "qvel", "target", "applied")},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
    complete = rows[-1]["tick"] == case["horizon_ticks"]
    twists = [body_twist(row) for row in rows]
    windows = []
    for index, command in enumerate(case["commands"]):
        start = command[0]
        target = command[1:] if len(command) == 4 else [command[1], 0.0, 0.0]
        end = (
            case["commands"][index + 1][0]
            if index + 1 < len(case["commands"])
            else case["horizon_ticks"]
        )
        selected_indices = [
            i
            for i, row in enumerate(rows)
            if start + case["measurement_delay_ticks"] <= row["tick"] < end
        ]
        axes = {}
        for name, value in zip(("vx", "vy", "wz"), target):
            if name not in case["track_axes"]:
                continue
            actual = np.asarray([twists[i][name] for i in selected_indices])
            error = actual - value
            axes[name] = dict(
                command=float(value),
                samples=len(actual),
                mean=float(np.mean(actual)) if len(actual) else None,
                mae=float(np.mean(np.abs(error))) if len(actual) else None,
                rmse=float(np.sqrt(np.mean(error**2))) if len(actual) else None,
            )
        windows.append(dict(start_tick=start, end_tick=end, axes=axes))

    tracked = [axis for window in windows for axis in window["axes"].values()]
    tracking_pass = complete and bool(tracked) and all(
        metric["mae"] is not None
        and metric["mae"]
        <= max(
            protocol["tracking_absolute_tolerance"],
            protocol["tracking_relative_tolerance"] * abs(metric["command"]),
        )
        for metric in tracked
    )
    yaw = yaw_series(rows)
    initial = rows[0]["qpos"]
    displacement = [
        [row["qpos"][0] - initial[0], row["qpos"][1] - initial[1]]
        for row in rows
    ]
    flat_cross_axis_pass = True
    if case.get("flat_probe", False):
        max_x = max(abs(point[0]) for point in displacement)
        max_y = max(abs(point[1]) for point in displacement)
        if "wz" in case["track_axes"]:
            flat_cross_axis_pass = max(
                max_x, max_y
            ) <= protocol["flat_cross_axis_max"]
        elif "vy" in case["track_axes"]:
            flat_cross_axis_pass = max_x <= protocol["flat_cross_axis_max"]
        else:
            flat_cross_axis_pass = max_y <= protocol["flat_cross_axis_max"]
        if "wz" not in case["track_axes"]:
            flat_cross_axis_pass = flat_cross_axis_pass and max(map(abs, yaw)) <= protocol[
                "flat_cross_axis_max"
            ]
    flat_cross_axis_pass = bool(flat_cross_axis_pass)

    reference_pass = True
    reference_mean_vx = None
    if case.get("reference_gate", False):
        first_window = windows[0]["axes"].get("vx")
        reference_mean_vx = first_window["mean"] if first_window else None
        reference_pass = (
            reference_mean_vx is not None
            and reference_mean_vx >= protocol["reference_mean_min"]
        )

    task_goal_pass = None
    route_pass = None
    maximum_hold = 0
    if "terrain_goal" in case:
        goal = case["terrain_goal"]
        edge = goal["terrain_x_max"]
        initial_y = initial[1]
        hold = 0
        for row in rows:
            cleared = (
                row["qpos"][0] >= edge + goal["base_clearance_m"]
                and min(foot[0] for foot in row["feet"])
                >= edge + goal["foot_clearance_m"]
                and abs(row["qpos"][1] - initial_y)
                <= goal["route_lateral_max_m"]
            )
            hold = hold + 1 if cleared else 0
            maximum_hold = max(maximum_hold, hold)
        route_rows = [
            row
            for row in rows
            if goal["terrain_x_min"]
            <= row["qpos"][0]
            <= goal["terrain_x_max"]
        ]
        route_pass = bool(route_rows) and all(
            abs(row["qpos"][1] - initial_y) <= goal["route_lateral_max_m"]
            for row in route_rows
        )
        task_goal_pass = complete and route_pass and maximum_hold >= goal["hold_ticks"]

    failure_classes = []
    if rows[-1]["failure"]:
        failure_classes.append("SAFETY_STOP")
    else:
        if not tracking_pass or not flat_cross_axis_pass or not reference_pass:
            failure_classes.append("TRACKING_FAILURE")
        if task_goal_pass is False:
            failure_classes.append("TASK_GOAL_FAILURE")
    if "SAFETY_STOP" in failure_classes:
        verdict = "SAFETY_STOP"
    elif failure_classes:
        verdict = "PERFORMANCE_FAIL"
    else:
        verdict = "PASS"

    latency = [row["policy_wall_s"] for row in rows if row["policy_wall_s"] is not None]
    return dict(
        verdict=verdict,
        failure=rows[-1]["failure"],
        failure_classes=failure_classes,
        complete=complete,
        steps=rows[-1]["tick"],
        trace_sha256=trajectory.hexdigest(),
        windows=windows,
        tracked_axes=case["track_axes"],
        tracking_pass=tracking_pass,
        flat_cross_axis_pass=flat_cross_axis_pass,
        reference_mean_vx=reference_mean_vx,
        reference_pass=reference_pass,
        task_goal_pass=task_goal_pass,
        route_pass=route_pass,
        task_goal_maximum_hold_ticks=maximum_hold,
        progress_m=rows[-1]["qpos"][0] - initial[0],
        lateral_max_m=max(abs(row["qpos"][1] - initial[1]) for row in rows),
        yaw_max_rad=float(max(map(abs, yaw))),
        min_clearance_m=min(row["clearance"] for row in rows),
        policy_updates=len(latency),
        policy_p50_ms=float(np.median(latency)) * 1000 if latency else None,
        policy_p99_ms=float(np.quantile(latency, 0.99)) * 1000 if latency else None,
    )


def make_policy(root, case, checkpoint_hash):
    path = root / ".substrate/rl/policy.pt"
    if case["adapter"]:
        return FrozenPolicy(path, checkpoint_hash)
    return SourcePolicy(
        root / ".substrate/upstream-go2-30e74dc5", path, checkpoint_hash
    )
