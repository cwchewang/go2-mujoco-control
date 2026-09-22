"""Source-bound, isolated offline admission; never starts a locomotion experiment."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from .contracts import Proprioception, TorqueCommand
from .model import (
    dependency_manifest,
    physical_fingerprint,
    joint_layout,
    decorate_mjpc,
)
from .rl import FrozenPolicy
from .integrity import (
    EvidenceRun,
    experiment_lock,
    digest,
    run_logged,
    strict_json,
    write_new,
)
from .environment import verify_environment
from .build_identity import verify as verify_build

ROOT = Path(__file__).resolve().parents[2]
SCENES = ("phase2_flat", "phase2_step_5cm", "phase2_step_10cm", "phase2_repeated_steps")


def validate_native_result(value):
    if not isinstance(value, dict):
        raise ValueError("native result must be an object")
    expected = {
        "backend": "MJPC iLQG",
        "scope": "offline_static_state",
        "mujoco": "3.3.6",
        "planner": 2,
        "horizon_steps": 21,
        "finite_bounded": True,
        "rollout_failure": False,
    }
    for key, wanted in expected.items():
        actual = value.get(key)
        if type(actual) is not type(wanted) or actual != wanted:
            raise ValueError("invalid native result field: " + key)
    for key in ("plant_time_s", "cost", "initial_cost"):
        x = value.get(key)
        if type(x) not in (float, int) or not np.isfinite(x) or x < 0:
            raise ValueError("invalid native " + key)
    if value["plant_time_s"] != 0:
        raise ValueError("external plant advanced")
    if value["cost"] > value["initial_cost"] + 1e-10 * max(1.0, value["initial_cost"]):
        raise ValueError("optimizer regressed from its nominal fixture")
    from .contracts import vector

    vector(value.get("torque"), 12, "native torque")
    return value


def source_manifest():
    paths = [
        p
        for directory in (ROOT / "tools/substrate", ROOT / "tools/research")
        for p in directory.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix in (".py", ".cc", ".txt", ".json", ".lock", ".in")
    ]
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(paths)}


def policy_replay(policy, base):
    def trace():
        rows = []
        for tick in range(12):
            # Synthetic proprioceptive packets, not a closed-loop trajectory.
            angle = 0.01 * tick
            obs = Proprioception(
                base.joint_names,
                base.position + 0.002 * tick,
                np.linspace(-0.1, 0.1, 12) * tick,
                np.array([np.cos(angle), np.sin(angle), 0.0, 0.0]),
                np.array([0.1, -0.05, 0.02]) * tick,
            )
            rows.append(policy.act(obs, [0.1, 0.0, 0.05]).position_target.tolist())
        return rows

    policy.reset()
    first = trace()
    policy.reset()
    second = trace()
    if first != second:
        raise ValueError("stateful policy replay differs after reset")
    return {
        "packets": 12,
        "reset_reproducible": True,
        "targets": first,
        "trace_sha256": hashlib.sha256(
            json.dumps(first, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def admit(run, checkpoint, binary):
    import mujoco
    import torch

    result = run.result
    output = run.path
    result["runtime"] = verify_environment()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    result["torch_threads"] = {
        "intra": torch.get_num_threads(),
        "inter": torch.get_num_interop_threads(),
    }
    identity = verify_build(binary)
    write_new(output / "build-identity.json", identity)
    sources = strict_json((ROOT / "tools/substrate/sources.lock.json").read_text())
    result["git_head"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    result["git_status"] = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    )
    result["source_files"] = source_manifest()
    diff = subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=ROOT)
    with (output / "working_tree.patch").open("xb") as stream:
        stream.write(diff)
    result["mjpc_binary_sha256"] = digest(binary)
    linkage = subprocess.check_output(["ldd", str(binary.resolve())], text=True)
    with (output / "native-linkage.txt").open("x") as stream:
        stream.write(linkage)
    native = [
        line.split("=>", 1)[1].strip().split()[0]
        for line in linkage.splitlines()
        if "libmujoco.so" in line and "=>" in line
    ]
    libraries = list(Path(mujoco.__file__).parent.glob("libmujoco.so.*"))
    if len(native) != 1 or len(libraries) != 1:
        raise ValueError("ambiguous MuJoCo linkage")
    result["mujoco_libraries"] = {
        "native": digest(native[0]),
        "python": digest(libraries[0]),
    }
    if (
        len(set(result["mujoco_libraries"].values())) != 1
        or digest(native[0]) != identity["inputs"]["mujoco_library"]
    ):
        raise ValueError("MuJoCo library identity mismatch")
    result["checkpoint_sha256"] = digest(checkpoint)
    policy = FrozenPolicy(checkpoint, sources["rl"]["sha256"])
    # Snapshot the complete registered asset closure before loading a model.
    input_root = output / "inputs"
    closures = {}
    for name in SCENES:
        path = ROOT / "unitree_robots/go2" / (name + ".xml")
        closure = dependency_manifest(path, ROOT)
        closures[name] = closure
        for filename, expected in closure["files"].items():
            dest = input_root / filename
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as stream:
                    stream.write((ROOT / filename).read_bytes())
            if digest(dest) != expected:
                raise ValueError("asset changed during snapshot")
    result["models"] = {}
    for name in SCENES:
        path = input_root / "unitree_robots/go2" / (name + ".xml")
        model = mujoco.MjModel.from_xml_path(str(path))
        data = mujoco.MjData(model)
        if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home") != 0:
            raise ValueError("home keyframe mismatch")
        mujoco.mj_resetDataKeyframe(model, data, 0)
        mujoco.mj_forward(model, data)
        if not np.isfinite(data.qacc).all():
            raise ValueError("nonfinite model forward")
        names, qadr, vadr = joint_layout(model)
        result["models"][name] = {
            "closure": closures[name],
            "physical_sha256": physical_fingerprint(model),
            "joint_names": names,
            "qpos_addresses": qadr,
            "dof_addresses": vadr,
            "actuator_range": model.actuator_ctrlrange.tolist(),
            "timestep_s": model.opt.timestep,
        }
    path = input_root / "unitree_robots/go2/phase2_flat.xml"
    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    names, qadr, vadr = joint_layout(model)
    obs = Proprioception(
        names, data.qpos[qadr], data.qvel[vadr], data.qpos[3:7], data.qvel[3:6]
    )
    result["rl"] = policy_replay(policy, obs)
    result["rl"].update(
        {
            "information_regime": policy.information_regime,
            "frequency_hz": policy.frequency_hz,
        }
    )
    policy.reset()
    command = policy.act(obs, [0.0, 0.0, 0.0])
    result["rl"]["resolved_action"] = {
        k: v.tolist()
        for k, v in command.resolve(
            obs, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], names
        ).items()
    }
    decorated = output.resolve() / "mjpc_flat.xml"
    decorate_mjpc(path, decorated)
    augmented = mujoco.MjModel.from_xml_path(str(decorated))
    if physical_fingerprint(model) != physical_fingerprint(augmented):
        raise ValueError("decoration changed model/reset physics")
    result["mjpc_physics_identical"] = True
    result["native_invocation"] = run_logged(
        [binary.resolve(), decorated], output, "mjpc"
    )
    value = validate_native_result(strict_json((output / "mjpc.stdout").read_text()))
    value.update({"information_regime": "known_model_oracle", "joint_names": names})
    cmd = TorqueCommand(
        names,
        np.asarray(value["torque"]),
        np.zeros(12),
        np.zeros(12),
        np.zeros(12),
        np.zeros(12),
    )
    action = cmd.resolve(
        obs, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], names
    )
    if action["saturated"].any():
        raise ValueError("post-optimization clipping required")
    value["resolved_action"] = {k: v.tolist() for k, v in action.items()}
    result["mjpc"] = value
    if result["source_files"] != source_manifest() or verify_build(binary) != identity:
        raise ValueError("source/build changed during admission")
    for name in SCENES:
        if (
            dependency_manifest(ROOT / "unitree_robots/go2" / (name + ".xml"), ROOT)
            != closures[name]
        ):
            raise ValueError("original model changed during admission")
    result["status"] = "ENGINEERING_ADMITTED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--mjpc-binary", type=Path, required=True)
    args = parser.parse_args()
    run = None
    try:
        with experiment_lock(), EvidenceRun(args.output, {"argv": sys.argv}) as run:
            admit(run, args.checkpoint, args.mjpc_binary)
    except (Exception, KeyboardInterrupt) as exc:
        print(
            json.dumps(
                {"status": "FAILED", "reason": type(exc).__name__ + ": " + str(exc)}
            )
        )
        return 1
    print(
        json.dumps({k: run.result[k] for k in ("status", "scope", "capability_status")})
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
