"""Bounded MJPC adapter diagnosis; no run is authorized by importing this module."""

from dataclasses import replace
from pathlib import Path

import numpy as np

from .aligned_anchor import load_anchor
from .integrity import digest, strict_json
from .model import physical_fingerprint

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "research/mjpc-adaptation-diagnostic-20261002"
LIMIT = 614400
RESERVE = 4096


def load_plan(path):
    raw = strict_json(Path(path).read_text())
    mode = raw.get("mode")
    if mode not in ("original", "corrected"):
        raise ValueError("invalid diagnostic mode")
    exact = {
        "schema": 1,
        "id": "mjpc-adaptation-" + mode + "-3s-v1",
        "branch": BRANCH,
        "parent": "b5547c77898c237ceb883407d64d3ce245c97fc5",
        "canonical_steps_max": 1500,
        "scientific_attempts_max": 1,
        "private_step_upper_bound_max": LIMIT,
        "private_reservation_per_replan": RESERVE,
        "replan_calls_max": 150,
        "horizon_s": 3.0,
        "wall_timeout_s": 300,
        "retry": "none",
        "stop": "first_safety_execution_evidence_budget_failure",
        "capability_claim": "none; short adapter diagnostic",
        "corrected_admission_gate": "new_original_prefix_match_1e-9_and_nonfoot_stop_tick1287",
        "corrected_fields": ["floor_world_z", "effective_pd_torque_clamp"],
        "preserved": [
            "mass",
            "damping",
            "contact_smoothing",
            "cost",
            "gait",
            "pd60_5",
            "0.35s_horizon",
            "10ms_prediction",
            "20ms_replan",
            "2ms_feedback",
            "one_sided_fd1e-6",
        ],
    }
    if any(raw.get(k) != v for k, v in exact.items()) or set(raw) != set(exact) | {
        "mode"
    }:
        raise ValueError("diagnostic protocol drift")
    anchor = load_anchor()
    return {
        **anchor,
        "raw": raw,
        "protocol_sha256": digest(path),
        "task": replace(
            anchor["task"],
            task_id=raw["id"],
            horizon_ticks=1500,
            measurement_start_tick=150,
        ),
    }


def validate_budget_record(value, tick, previous=None):
    keys = {
        "policy_id",
        "private_step_upper_bound_reserved",
        "private_step_limit",
        "rollout_mj_step_count",
        "fd_step_upper_bound_count",
        "fd_call_count",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("missing diagnostic accounting")
    if any(type(v) is not int or v < 0 for v in value.values()):
        raise ValueError("noninteger diagnostic accounting")
    calls = tick // 10 + 1
    if (
        calls > 150
        or value["policy_id"] != calls
        or value["private_step_upper_bound_reserved"] != calls * RESERVE
        or value["private_step_limit"] != LIMIT
        or value["rollout_mj_step_count"] + value["fd_step_upper_bound_count"]
        > value["private_step_upper_bound_reserved"]
    ):
        raise ValueError("private budget/cadence mismatch")
    if previous is not None:
        if any(value[k] < previous[k] for k in keys):
            raise ValueError("private counter regressed")
        if tick % 10 and value != previous:
            raise ValueError("private integration outside replan")
    return dict(value)


def model_audit():
    import mujoco as mj

    plant = mj.MjModel.from_xml_path(str(ROOT / "unitree_robots/go2/phase2_flat.xml"))
    source_path = ROOT / ".substrate/mjpc/mjpc/tasks/quadruped/task_flat.xml"
    source = mj.MjModel.from_xml_path(str(source_path))
    joint_map, collision_map = [], []

    def geom_key(m, i):
        name = mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, int(m.geom_bodyid[i]))
        name = {"trunk": "base_link", "world": "world"}.get(name, name)
        return (
            name,
            int(m.geom_type[i]),
            tuple(m.geom_size[i]),
            tuple(m.geom_pos[i]),
            tuple(m.geom_quat[i]),
        )

    plant_collision = {}
    for i in range(plant.ngeom):
        if plant.geom_contype[i] or plant.geom_conaffinity[i]:
            plant_collision.setdefault(geom_key(plant, i), []).append(i)
    for i in range(source.ngeom):
        if not (source.geom_contype[i] or source.geom_conaffinity[i]):
            continue
        if mj.mj_id2name(source, mj.mjtObj.mjOBJ_GEOM, i) == "floor":
            continue
        matches = plant_collision.get(geom_key(source, i), [])
        if len(matches) != 1:
            raise ValueError("unnamed collision geometry mapping is not unique")
        sb = int(source.geom_bodyid[i])
        pb = int(plant.geom_bodyid[matches[0]])
        if not (
            np.array_equal(source.body_pos[sb], plant.body_pos[pb])
            and np.array_equal(source.body_quat[sb], plant.body_quat[pb])
        ):
            raise ValueError("body-frame registration mismatch")
        collision_map.append(
            {
                "source_geom": i,
                "canonical_geom": matches[0],
                "body": geom_key(source, i)[0],
            }
        )
    for i in range(source.nu):
        sj = int(source.actuator_trnid[i, 0])
        name = mj.mj_id2name(source, mj.mjtObj.mjOBJ_JOINT, sj)
        pj = mj.mj_name2id(plant, mj.mjtObj.mjOBJ_JOINT, name)
        matches = [j for j in range(plant.nu) if plant.actuator_trnid[j, 0] == pj]
        if pj < 0 or len(matches) != 1:
            raise ValueError("joint/actuator mapping ambiguous")
        pa = matches[0]
        if (
            not np.array_equal(source.actuator_gear[i], plant.actuator_gear[pa])
            or source.actuator_gear[i, 0] != 1
        ):
            raise ValueError("nonidentical transmission gear")
        joint_map.append(
            {
                "joint": name,
                "source_actuator": i,
                "canonical_actuator": pa,
                "torque_range": plant.actuator_ctrlrange[pa].tolist(),
            }
        )
        source.actuator_biastype[i] = mj.mjtBias.mjBIAS_AFFINE
    original = mj.MjModel.from_xml_path(str(source_path))
    original.actuator_biastype[:] = mj.mjtBias.mjBIAS_AFFINE
    source.geom_pos[mj.mj_name2id(source, mj.mjtObj.mjOBJ_GEOM, "floor"), 2] = 0
    for row in joint_map:
        i = row["source_actuator"]
        source.actuator_forcelimited[i] = 1
        source.actuator_forcerange[i] = row["torque_range"]
    # Match the C++ optimizer's declared dt and differentiability transformation.
    for m in (original, source):
        m.opt.timestep = 0.01
        m.jnt_solimp[:, 0] = 0
        m.geom_solimp[:, 0] = 0
        m.pair_solimp[:, 0] = 0
    return {
        "canonical_physical_sha256": physical_fingerprint(plant),
        "joint_map": joint_map,
        "collision_map": collision_map,
        "optimization_models": {
            "original-go2-soft-v1": physical_fingerprint(original),
            "corrected-go2-soft-v1": physical_fingerprint(source),
        },
        "canonical_integration_steps": 0,
        "corrected_fields": ["floor_world_z", "effective_pd_torque_clamp"],
        "mass_damping_contact_parameters_preserved": True,
    }
