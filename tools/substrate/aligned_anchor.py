"""Fail-closed loader for the first prospective aligned flat integration anchor."""

from pathlib import Path

import numpy as np

from .clock import TimingSpec
from .contracts import InformationSpec
from .integrity import strict_json
from .model import joint_layout
from .specs import ScenarioSpec, TaskSpec, TaskThresholds

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANCHOR = Path(__file__).with_name("protocols") / "aligned_flat_anchor_v1.json"
LOCK = Path(__file__).with_name("sources.lock.json")


def _controller(name, raw, lock, physics_period_s):
    if name == "rl":
        if raw.get("backend") != "public_cts_cpu":
            raise ValueError("RL backend drifted")
        if raw.get("adapter") != "ProprioceptivePolicyAdapter":
            raise ValueError("RL adapter drifted")
        if raw.get("source_commit") != lock["rl"]["commit"]:
            raise ValueError("RL source commit drifted")
        if raw.get("checkpoint_sha256") != lock["rl"]["sha256"]:
            raise ValueError("RL checkpoint identity drifted")
    elif name == "mjpc":
        if raw.get("backend") != "native_mjpc_ilqg":
            raise ValueError("MJPC backend drifted")
        if raw.get("adapter") != "PositionTargetControllerAdapter":
            raise ValueError("MJPC adapter drifted")
        if raw.get("source_commit") != lock["mjpc"]["commit"]:
            raise ValueError("MJPC source commit drifted")
        if raw.get("protocol") != 3:
            raise ValueError("MJPC process protocol drifted")
        if raw.get("compatibility_correction") != "private_model_mjBIAS_AFFINE":
            raise ValueError("MJPC compatibility correction drifted")
    else:
        raise ValueError("unexpected aligned-anchor controller")

    information = InformationSpec(**raw["information"])
    timing = TimingSpec(**raw["timing"])
    if not np.isclose(timing.physics_period_s, physics_period_s, rtol=0, atol=1e-12):
        raise ValueError("controller physics period differs from canonical physics")
    return {"information": information, "timing": timing, "raw": raw}


def validate_anchor(raw, lock):
    if type(raw.get("schema")) is not int or raw.get("schema") != 1:
        raise ValueError("unsupported aligned-anchor schema")
    if raw.get("mode") != "engineering_anchor":
        raise ValueError("aligned anchor must remain engineering-only")
    if raw.get("physics_step_authorized") is not False:
        raise ValueError("aligned anchor must not authorize physics")
    if (
        type(raw.get("scientific_attempts_authorized")) is not int
        or raw.get("scientific_attempts_authorized") != 0
    ):
        raise ValueError("aligned anchor must not authorize scientific attempts")
    if raw.get("requires_independent_review") is not True:
        raise ValueError("aligned anchor requires independent review")

    if raw.get("id") != "aligned-flat-forward-integration-v1":
        raise ValueError("aligned anchor id drifted")
    if not isinstance(raw.get("question"), str) or not raw["question"]:
        raise ValueError("aligned anchor question required")

    canonical = raw["canonical"]
    if canonical.get("scene") != "unitree_robots/go2/phase2_flat.xml":
        raise ValueError("canonical scene drifted")
    if canonical.get("physical_sha256") != (
        "1c7ec61af1297fe1715e3d412481709bf4ad3ad42196e483c444d1a54db73e94"
    ):
        raise ValueError("canonical physical fingerprint drifted")
    if canonical.get("reset") != "home_key0_zero_qvel_zero_ctrl":
        raise ValueError("canonical reset drifted")
    physics_period_s = canonical["physics_period_s"]
    if not np.isclose(physics_period_s, 0.002, rtol=0, atol=1e-12):
        raise ValueError("canonical physics period drifted")
    scenario = ScenarioSpec(
        scene=canonical["scene"],
        reset=canonical["reset"],
        physical_sha256=canonical["physical_sha256"],
    )

    task_raw = dict(raw["task"])
    threshold_raw = dict(task_raw.pop("thresholds"))
    expected_task = {
        "task_id": "aligned-flat-forward-integration-v1",
        "command_target": [1.0, 0.0, 0.0],
        "command_frame": "body",
        "zero_command_ticks": 50,
        "ramp_ticks": 100,
        "horizon_ticks": 500,
        "measurement_start_tick": 250,
        "support_semantics": "traverse",
        "required_supports": [],
        "stop_on": [
            "nonfinite",
            "orientation",
            "physics_warning",
            "nonfoot_contact",
            "posture",
            "lateral",
        ],
        "longitudinal_metric": "body_vx",
    }
    if task_raw != expected_task:
        raise ValueError("aligned task definition drifted")
    expected_thresholds = {
        "progress_min_m": 0.05,
        "vx_mae_max_mps": 2.0,
        "lateral_max_m": 0.4,
        "tilt_max_rad": 0.8,
        "height_min_m": 0.12,
        "height_max_m": 0.55,
    }
    if threshold_raw != expected_thresholds:
        raise ValueError("aligned task thresholds drifted")
    thresholds = TaskThresholds(**threshold_raw)
    task = TaskSpec(thresholds=thresholds, **task_raw)
    if task.command_frame != "body" or task.longitudinal_metric != "body_vx":
        raise ValueError("flat anchor must use body-frame longitudinal semantics")
    if not np.array_equal(task.command_target, [1.0, 0.0, 0.0]):
        raise ValueError("flat anchor command drifted")

    controllers_raw = raw["controllers"]
    if set(controllers_raw) != {"rl", "mjpc"}:
        raise ValueError("aligned anchor requires exactly RL and MJPC")
    controllers = {
        name: _controller(name, controllers_raw[name], lock, physics_period_s)
        for name in ("rl", "mjpc")
    }

    rl = controllers["rl"]
    mjpc = controllers["mjpc"]
    if (
        rl["information"].observation != "proprioceptive"
        or rl["information"].model_access != "none"
        or rl["timing"].control_period_s != 0.02
        or rl["timing"].feedback_period_s != 0.02
    ):
        raise ValueError("RL information/timing regime drifted")
    if (
        mjpc["information"].observation != "whole_body_state"
        or mjpc["information"].model_access != "controller_model"
        or mjpc["timing"].control_period_s != 0.02
        or mjpc["timing"].feedback_period_s != 0.002
    ):
        raise ValueError("MJPC information/timing regime drifted")
    if (
        rl["timing"].compute_semantics != "offline_unbounded"
        or mjpc["timing"].compute_semantics != "offline_unbounded"
    ):
        raise ValueError("first anchor must remain offline_unbounded")

    return {
        "raw": raw,
        "task": task,
        "scenario": scenario,
        "controllers": controllers,
        "physics_period_s": float(physics_period_s),
    }


def load_anchor(path=DEFAULT_ANCHOR):
    raw = strict_json(Path(path).read_text())
    lock = strict_json(LOCK.read_text())
    return validate_anchor(raw, lock)


def validate_canonical_reset(model):
    import mujoco

    home = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home")
    if home != 0:
        raise ValueError("canonical home key identity drifted")
    base = np.asarray(model.key_qpos[home, :7], dtype=np.float64)
    if base.shape != (7,) or not np.isfinite(base).all():
        raise ValueError("canonical home base pose is invalid")
    if not np.allclose(base[3:7], [1.0, 0.0, 0.0, 0.0], rtol=0, atol=1e-12):
        raise ValueError("canonical home heading no longer aligns with world +x")
    return True


def validate_canonical_model(anchor, model):
    anchor["scenario"].verify_model(model)
    if not np.isclose(
        model.opt.timestep, anchor["physics_period_s"], rtol=0, atol=1e-12
    ):
        raise ValueError("compiled canonical timestep drifted")
    validate_canonical_reset(model)
    joint_layout(model)
    return True
