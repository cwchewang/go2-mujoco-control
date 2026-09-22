"""Conservative local MJCF dependency closure and compiled physical fingerprint."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dependency_manifest(scene, repository):
    root = Path(repository).resolve()
    scene = Path(scene).resolve()
    files, active = {}, set()

    def confined(path):
        p = path.resolve()
        if not p.is_relative_to(root) or not p.is_file():
            raise ValueError(f"missing or out-of-root dependency: {p}")
        return p

    def visit(path, meshdir=None, texturedir=None):
        path = confined(path)
        if path in active:
            raise ValueError("cyclic MJCF include")
        active.add(path)
        tree = ET.parse(path).getroot()
        files[str(path.relative_to(root))] = digest(path)
        compiler = tree.find("compiler")
        if compiler is not None:
            assetdir = compiler.get("assetdir", "")
            meshdir = path.parent / compiler.get("meshdir", assetdir)
            texturedir = path.parent / compiler.get("texturedir", assetdir)
        for node in tree.iter():
            name = node.get("file")
            if not name:
                continue
            if node.tag == "include":
                visit(path.parent / name, meshdir, texturedir)
            else:
                base = (
                    meshdir
                    if node.tag == "mesh"
                    else texturedir
                    if node.tag == "texture"
                    else path.parent
                )
                asset = confined((base or path.parent) / name)
                files[str(asset.relative_to(root))] = digest(asset)
        active.remove(path)

    visit(scene)
    entries = dict(sorted(files.items()))
    return {
        "files": entries,
        "sha256": hashlib.sha256(
            json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def physical_fingerprint(model):
    # Sensor/custom/task metadata deliberately excluded. Physical arrays are included
    # by prefix, including mesh vertices and collision geometry, not only XML text.
    prefixes = (
        "body_",
        "jnt_",
        "dof_",
        "geom_",
        "mesh_",
        "hfield_",
        "pair_",
        "exclude_",
        "eq_",
        "tendon_",
        "wrap_",
        "actuator_",
    )
    arrays = {}
    for name in dir(model):
        if name.startswith(prefixes):
            value = getattr(model, name)
            if isinstance(value, np.ndarray):
                arrays[name] = {
                    "shape": list(value.shape),
                    "dtype": str(value.dtype),
                    "hash": hashlib.sha256(value.tobytes()).hexdigest(),
                }
    # Addresses affect mechanics too; sensor insertion must not perturb these.
    for name in ("jnt_qposadr", "jnt_dofadr", "actuator_trnid", "dof_parentid"):
        arrays[name] = np.asarray(getattr(model, name)).tolist()
    options = {}
    for name in dir(model.opt):
        if name.startswith("_"):
            continue
        value = getattr(model.opt, name)
        if isinstance(value, np.ndarray):
            options[name] = value.tolist()
        elif isinstance(value, (float, int)):
            options[name] = value
    payload = {
        "arrays": arrays,
        "options": options,
        "nq": model.nq,
        "nv": model.nv,
        "nu": model.nu,
        "qpos0": model.qpos0.tolist(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def joint_layout(model):
    import mujoco
    from .contracts import POLICY_JOINTS

    names, qpos, dof = [], [], []
    for actuator in range(model.nu):
        if (
            model.actuator_trntype[actuator] != mujoco.mjtTrn.mjTRN_JOINT
            or model.actuator_gaintype[actuator] != mujoco.mjtGain.mjGAIN_FIXED
            or model.actuator_biastype[actuator] != mujoco.mjtBias.mjBIAS_NONE
            or model.actuator_dyntype[actuator] != mujoco.mjtDyn.mjDYN_NONE
            or model.actuator_gainprm[actuator, 0] != 1
            or not np.array_equal(model.actuator_gear[actuator], [1, 0, 0, 0, 0, 0])
            or not model.actuator_ctrllimited[actuator]
            or model.actuator_forcelimited[actuator]
        ):
            raise ValueError(
                "shared substrate requires finite-range direct torque motors"
            )
        joint = int(model.actuator_trnid[actuator, 0])
        if (
            model.jnt_type[joint] != mujoco.mjtJoint.mjJNT_HINGE
            or model.jnt_actfrclimited[joint]
        ):
            raise ValueError("unsupported joint transmission or secondary force limit")
        names.append(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint))
        qpos.append(int(model.jnt_qposadr[joint]))
        dof.append(int(model.jnt_dofadr[joint]))
    if len(names) != 12 or len(set(names)) != 12 or set(names) != set(POLICY_JOINTS):
        raise ValueError("unexpected actuated joint set")
    return tuple(names), qpos, dof


def decorate_mjpc(scene, destination):
    # Absolute include preserves the existing model/assets. Usersensors precede
    # ordinary sensors as required by MJPC. No actuator, inertia or contact edits.
    root = ET.Element("mujoco", model="Go2 shared substrate offline admission")
    sensors = ET.SubElement(root, "sensor")
    for name, dim, weight in (
        ("height", 1, 10),
        ("upright", 3, 2),
        ("velocity", 3, 1),
        ("posture", 12, 0.1),
        ("effort", 12, 0.001),
    ):
        ET.SubElement(
            sensors, "user", name=name, dim=str(dim), user=f"0 {weight} 0 100"
        )
    ET.SubElement(root, "include", file=str(Path(scene).resolve()))
    # A wrapper stored outside the scene directory changes MJCF relative asset
    # resolution. Keep the Go2 mesh source explicit; physical hash must match.
    ET.SubElement(
        root, "compiler", meshdir=str(Path(scene).resolve().parent / "assets")
    )
    custom = ET.SubElement(root, "custom")
    for name, value in (
        ("agent_planner", "2"),
        ("agent_horizon", "0.04"),
        ("agent_timestep", "0.002"),
    ):
        ET.SubElement(custom, "numeric", name=name, data=value)
    ET.ElementTree(root).write(destination, encoding="unicode")
