"""Run offline admission only. Never starts a locomotion experiment."""

import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import numpy as np
from .contracts import Proprioception, TorqueCommand
from .model import (
    dependency_manifest,
    digest,
    physical_fingerprint,
    joint_layout,
    decorate_mjpc,
)
from .rl import FrozenPolicy

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="new directory; never overwritten"
    )
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--mjpc-binary", type=Path, required=True)
    args = parser.parse_args()
    lock = open("/tmp/go2_mujoco_experiment.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    args.output.mkdir(parents=True, exist_ok=False)
    result = {
        "scope": "offline_engineering_admission",
        "live_runs": 0,
        "capability_status": "NOT_RUN",
        "status": "FAILED",
        "errors": [],
    }
    try:
        import mujoco
        import torch

        sources = json.loads(
            (Path(__file__).with_name("sources.lock.json")).read_text()
        )
        if (
            mujoco.__version__ != sources["mujoco"]
            or torch.__version__ != sources["torch"]
        ):
            raise ValueError("runtime version mismatch")
        result["runtime"] = {
            "python": platform.python_version(),
            "mujoco": mujoco.__version__,
            "torch": torch.__version__,
            "numpy": np.__version__,
        }
        result["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        diff = subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=ROOT)
        (args.output / "working_tree.patch").write_bytes(diff)
        result["working_tree_patch_sha256"] = hashlib.sha256(diff).hexdigest()
        # Hash untracked implementation too; HEAD alone cannot identify admission code.
        code = list((ROOT / "tools/substrate").rglob("*.py")) + list(
            (ROOT / "tools/substrate/native").glob("*")
        )
        code.append(ROOT / "tools/substrate/sources.lock.json")
        result["source_files"] = {
            str(p.relative_to(ROOT)): digest(p) for p in sorted(code) if p.is_file()
        }
        mjpc_source = ROOT / ".substrate/mjpc"
        actual_source = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=mjpc_source, text=True
        ).strip()
        if actual_source != sources["mjpc"]["commit"] or subprocess.check_output(
            ["git", "diff", "HEAD"], cwd=mjpc_source
        ):
            raise ValueError("MJPC source differs from lock")
        result["mjpc_source_commit"] = actual_source
        result["mjpc_binary_sha256"] = digest(args.mjpc_binary)
        linkage = subprocess.check_output(
            ["ldd", str(args.mjpc_binary.resolve())], text=True
        )
        (args.output / "native-linkage.txt").write_text(linkage)
        native_libs = [
            line.split("=>", 1)[1].strip().split()[0]
            for line in linkage.splitlines()
            if "libmujoco.so" in line and "=>" in line
        ]
        if len(native_libs) != 1:
            raise ValueError("cannot identify the native MuJoCo library")
        python_library = next(Path(mujoco.__file__).parent.glob("libmujoco.so.*"))
        result["mujoco_libraries"] = {
            "native": digest(native_libs[0]),
            "python": digest(python_library),
        }
        if result["mujoco_libraries"]["native"] != result["mujoco_libraries"]["python"]:
            raise ValueError("native and Python MuJoCo library bytes differ")
        result["checkpoint_sha256"] = digest(args.checkpoint)
        policy = FrozenPolicy(args.checkpoint, sources["rl"]["sha256"])
        result["models"] = {}
        for name in (
            "phase2_flat",
            "phase2_step_5cm",
            "phase2_step_10cm",
            "phase2_repeated_steps",
        ):
            path = ROOT / "unitree_robots/go2" / (name + ".xml")
            manifest = dependency_manifest(path, ROOT)
            model = mujoco.MjModel.from_xml_path(str(path))
            data = mujoco.MjData(model)
            mujoco.mj_resetDataKeyframe(model, data, 0)
            mujoco.mj_forward(model, data)
            names, qadr, vadr = joint_layout(model)
            result["models"][name] = {
                "closure": manifest,
                "physical_sha256": physical_fingerprint(model),
                "joint_names": names,
                "qpos_addresses": qadr,
                "dof_addresses": vadr,
                "actuator_range": model.actuator_ctrlrange.tolist(),
                "timestep_s": model.opt.timestep,
            }
        path = ROOT / "unitree_robots/go2/phase2_flat.xml"
        model = mujoco.MjModel.from_xml_path(str(path))
        data = mujoco.MjData(model)
        mujoco.mj_resetDataKeyframe(model, data, 0)
        mujoco.mj_forward(model, data)
        names, qadr, vadr = joint_layout(model)
        obs = Proprioception(
            names,
            data.qpos[qadr].copy(),
            data.qvel[vadr].copy(),
            data.qpos[3:7].copy(),
            data.qvel[3:6].copy(),
        )
        command = policy.act(obs, [0.0, 0.0, 0.0])
        resolved = command.resolve(
            obs, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], names
        )
        first = command.position_target.copy()
        policy.reset()
        if not np.array_equal(first, policy.act(obs, [0.0, 0.0, 0.0]).position_target):
            raise ValueError("policy reset does not reproduce first inference")
        result["rl"] = {
            "information_regime": policy.information_regime,
            "frequency_hz": policy.frequency_hz,
            "reset_reproducible": True,
            "position_target": first.tolist(),
            "resolved_action": {k: v.tolist() for k, v in resolved.items()},
        }
        decorated = args.output.resolve() / "mjpc_flat.xml"
        decorate_mjpc(path, decorated)
        augmented = mujoco.MjModel.from_xml_path(str(decorated))
        if physical_fingerprint(model) != physical_fingerprint(augmented):
            raise ValueError("MJPC decoration changed the physical model")
        result["mjpc_physics_identical"] = True
        started = time.monotonic()
        run = subprocess.run(
            [str(args.mjpc_binary.resolve()), str(decorated)],
            text=True,
            capture_output=True,
            timeout=120,
        )
        (args.output / "mjpc.stdout").write_text(run.stdout)
        (args.output / "mjpc.stderr").write_text(run.stderr)
        run.check_returncode()
        result["mjpc"] = json.loads(run.stdout.strip().splitlines()[-1])
        result["mjpc"]["wall_time_s"] = time.monotonic() - started
        result["mjpc"]["information_regime"] = "known_model_oracle"
        # Both backend outputs enter the same named torque/PD resolution boundary.
        mjpc_command = TorqueCommand(
            names,
            np.asarray(result["mjpc"]["torque"]),
            np.zeros(12),
            np.zeros(12),
            np.zeros(12),
            np.zeros(12),
        )
        mjpc_action = mjpc_command.resolve(
            obs, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], names
        )
        result["mjpc"]["joint_names"] = names
        result["mjpc"]["resolved_action"] = {
            k: v.tolist() for k, v in mjpc_action.items()
        }
        if mjpc_action["saturated"].any():
            raise ValueError("planner output required post-optimization clipping")
        if not result["mjpc"]["finite_bounded"] or result["mjpc"]["plant_time_s"] != 0:
            raise ValueError("invalid offline planner result")
        result["status"] = "ENGINEERING_ADMITTED"
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        (args.output / "admission.json").write_text(json.dumps(result, indent=2) + "\n")
        hashes = {p.name: digest(p) for p in args.output.iterdir() if p.is_file()}
        (args.output / "manifest.json").write_text(json.dumps(hashes, indent=2) + "\n")
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    print(
        json.dumps(
            {k: result[k] for k in ("scope", "status", "capability_status", "errors")}
        )
    )
    return 0 if result["status"] == "ENGINEERING_ADMITTED" else 1


if __name__ == "__main__":
    sys.exit(main())
