"""Zero-integration diagnosis on a sealed trace and blob-verified upstream source."""

import argparse
import ast
import csv
import json
from pathlib import Path
import re
import numpy as np

from .guards import zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_bundle,
    write_new,
)
from .verify_capture import verify_capture
from .contracts import Proprioception, POLICY_JOINTS
from .rl import FrozenPolicy, observation45

ROOT = Path(__file__).resolve().parents[2]


def yaml_literals(path):
    """Read only this pinned deployment's flat scalar/list configuration."""
    text = "\n".join(line.split("#", 1)[0] for line in path.read_text().splitlines())
    return {
        key: ast.literal_eval(value.strip())
        for key, value in re.findall(r"(?m)^(\w+):\s*(\[[\s\S]*?\]|[^\n]+)", text)
    }


def joint_map(mj, model):
    result = {}
    for a in range(model.nu):
        j = int(model.actuator_trnid[a, 0])
        result[mj.mj_id2name(model, mj.mjtObj.mjOBJ_JOINT, j)] = {
            "joint": j,
            "q": int(model.jnt_qposadr[j]),
            "v": int(model.jnt_dofadr[j]),
            "a": a,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with (
        experiment_lock(),
        zero_step_guard(),
        EvidenceRun(
            args.output, {"operation": "offline_frozen_trace_diagnosis"}
        ) as run,
    ):
        import mujoco as mj
        import torch

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        reference = strict_json(
            (args.reference / "reference-manifest.json").read_text()
        )
        locked = strict_json((ROOT / "tools/substrate/sources.lock.json").read_text())[
            "rl"
        ]
        if reference["commit"] != locked["commit"]:
            raise ValueError("reference commit mismatch")
        for name, expected in reference["files"].items():
            if digest(args.reference / name) != expected:
                raise ValueError("reference changed")
        prepared = verify_bundle(args.prepared)
        protocol = strict_json((args.prepared / "protocol.json").read_text())
        verified = verify_capture(
            args.capture,
            args.prepared,
            ROOT / "_runs/substrate_attempts" / protocol["id"],
        )
        rows = [
            strict_json(line)
            for line in (args.capture / "attempt_01.jsonl").read_text().splitlines()
        ]
        config = yaml_literals(args.reference / locked["configuration"])
        source = ast.parse((args.reference / locked["deployment"]).read_text())
        pure = ast.Module(
            body=[
                node
                for node in source.body
                if isinstance(node, ast.FunctionDef)
                and node.name in ("get_gravity_orientation", "pd_control")
            ],
            type_ignores=[],
        )
        namespace = {"np": np}
        exec(compile(pure, "pinned-upstream-pure-functions", "exec"), namespace)
        policy = FrozenPolicy(ROOT / ".substrate/rl/policy.pt", locked["sha256"])
        upstream = torch.jit.load(
            str(ROOT / ".substrate/rl/policy.pt"), map_location="cpu"
        ).eval()
        names = prepared["layout"]["names"]
        order = [names.index(name) for name in config["mujoco_joint_names"]]
        to_policy = [
            config["mujoco_joint_names"].index(name)
            for name in config["model_joint_names"]
        ]
        default = np.array(config["default_angles"], dtype=np.float32)
        previous = np.zeros(12, dtype=np.float32)
        maximum = {
            "observation_abs": 0.0,
            "target_vs_upstream_abs": 0.0,
            "target_vs_record_abs": 0.0,
            "pd_vs_record_abs": 0.0,
        }
        recorded_actions = []
        for row in rows:
            if row["policy_wall_s"] is None:
                continue
            q, v = np.array(row["qpos"]), np.array(row["qvel"])
            position = q[prepared["layout"]["qadr"]]
            velocity = v[prepared["layout"]["vadr"]]
            obs = Proprioception(tuple(names), position, velocity, q[3:7], v[3:6])
            assembled = np.zeros(config["num_obs"], dtype=np.float32)
            assembled[:3] = v[3:6] * config["ang_vel_scale"]
            assembled[3:6] = namespace["get_gravity_orientation"](q[3:7])
            assembled[6:9] = np.array(row["command"], dtype=np.float32) * np.array(
                config["cmd_scale"], dtype=np.float32
            )
            assembled[9:21] = ((position[order] - default) * config["dof_pos_scale"])[
                to_policy
            ]
            assembled[21:33] = (velocity[order] * config["dof_vel_scale"])[to_policy]
            assembled[33:45] = previous[to_policy]
            own_obs = observation45(obs, row["command"], policy.previous_action)
            maximum["observation_abs"] = max(
                maximum["observation_abs"], float(np.max(np.abs(assembled - own_obs)))
            )
            with torch.inference_mode():
                output = upstream(torch.from_numpy(assembled).unsqueeze(0))
            raw_action = (
                (output[0] if isinstance(output, tuple) else output)[0].cpu().numpy()
            )
            previous = (
                raw_action.copy()
            )  # this pinned config uses identical policy/MuJoCo order
            up_target = default + raw_action * config["action_scale"]
            own = policy.act(obs, row["command"])
            saved = np.array(row["target"]["position_target"])
            maximum["target_vs_upstream_abs"] = max(
                maximum["target_vs_upstream_abs"],
                float(np.max(np.abs(own.position_target - up_target))),
            )
            maximum["target_vs_record_abs"] = max(
                maximum["target_vs_record_abs"],
                float(np.max(np.abs(own.position_target - saved))),
            )
            recorded_actions.append(raw_action.tolist())
        for row in rows[:-1]:
            q, v = np.array(row["qpos"]), np.array(row["qvel"])
            target = row["target"]
            target_order = [target["joint_names"].index(name) for name in names]
            tau = namespace["pd_control"](
                np.array(target["position_target"])[target_order],
                q[prepared["layout"]["qadr"]],
                np.array(target["kp"])[target_order],
                np.array(target["velocity_target"])[target_order],
                v[prepared["layout"]["vadr"]],
                np.array(target["kd"])[target_order],
            )
            maximum["pd_vs_record_abs"] = max(
                maximum["pd_vs_record_abs"],
                float(np.max(np.abs(tau - row["action"]["pd"]))),
            )
        current_model = mj.MjModel.from_xml_path(
            str(args.prepared / "inputs" / protocol["scene"])
        )
        upstream_model = mj.MjModel.from_xml_path(
            str(args.reference / "resources/robots/go2/flat.xml")
        )
        maps = [joint_map(mj, model) for model in (current_model, upstream_model)]
        model_diff = {}
        for name in POLICY_JOINTS:
            items = []
            for model, mapping in zip((current_model, upstream_model), maps):
                idx = mapping[name]
                items.append(
                    {
                        "damping": float(model.dof_damping[idx["v"]]),
                        "frictionloss": float(model.dof_frictionloss[idx["v"]]),
                        "armature": float(model.dof_armature[idx["v"]]),
                        "joint_range": model.jnt_range[idx["joint"]].tolist(),
                        "ctrlrange": model.actuator_ctrlrange[idx["a"]].tolist(),
                        "joint_force_limited": int(
                            model.jnt_actfrclimited[idx["joint"]]
                        ),
                        "joint_force_range": model.jnt_actfrcrange[
                            idx["joint"]
                        ].tolist(),
                    }
                )
            model_diff[name] = {"current": items[0], "upstream": items[1]}
        d = mj.MjData(current_model)
        u = mj.MjData(upstream_model)
        initial_upstream = u.qpos.tolist()
        mismatch = 0
        passive_deltas, extra_damping, actuator_effort = [], [], []
        contacts = {leg: 0 for leg in ("FR", "FL", "RR", "RL")}
        floor = mj.mj_name2id(current_model, mj.mjtObj.mjOBJ_GEOM, "phase2_floor")
        foot_ids = {
            mj.mj_name2id(current_model, mj.mjtObj.mjOBJ_GEOM, leg): leg
            for leg in contacts
        }
        for row in rows:
            d.qpos[:] = row["qpos"]
            d.qvel[:] = row["qvel"]
            d.ctrl[:] = 0 if row["action"] is None else row["action"]["ctrl"]
            before = d.qpos.copy()
            mj.mj_forward(current_model, d)
            assert d.time == 0 and np.array_equal(before, d.qpos)
            supports, forbidden = set(), []
            for contact in d.contact:
                if contact.efc_address < 0:
                    continue
                pair = {int(contact.geom1), int(contact.geom2)}
                if (
                    floor in pair
                    and len(pair) == 2
                    and next(iter(pair - {floor})) in foot_ids
                ):
                    supports.add(foot_ids[next(iter(pair - {floor}))])
                elif any(current_model.geom_bodyid[g] != 0 for g in pair):
                    forbidden.append(sorted(pair))
            mismatch += sorted(supports) != row["supports"] or sorted(
                forbidden
            ) != sorted(row["forbidden_contacts"])
            for leg in supports:
                contacts[leg] += 1
            u.qpos[:7], u.qvel[:6] = d.qpos[:7], d.qvel[:6]
            for name in POLICY_JOINTS:
                a, b = maps[0][name], maps[1][name]
                u.qpos[b["q"]], u.qvel[b["v"]] = d.qpos[a["q"]], d.qvel[a["v"]]
            mj.mj_forward(upstream_model, u)
            assert u.time == 0
            passive_deltas.append(
                [
                    float(
                        d.qfrc_passive[maps[0][name]["v"]]
                        - u.qfrc_passive[maps[1][name]["v"]]
                    )
                    for name in POLICY_JOINTS
                ]
            )
            extra_damping.append(
                [
                    float(
                        (
                            current_model.dof_damping[maps[0][name]["v"]]
                            - upstream_model.dof_damping[maps[1][name]["v"]]
                        )
                        * d.qvel[maps[0][name]["v"]]
                    )
                    for name in POLICY_JOINTS
                ]
            )
            if row["action"] is not None:
                actuator_effort.append(row["action"]["ctrl"])
        phase = []
        for start, stop in ((0, 500), (500, 1000), (1000, 2500), (2500, 5001)):
            subset = rows[start:stop]
            phase.append(
                {
                    "ticks": [start, stop - 1],
                    "mean_vx": float(np.mean([row["qvel"][0] for row in subset])),
                    "four_foot_support_fraction": sum(
                        len(row["supports"]) == 4 for row in subset
                    )
                    / len(subset),
                }
            )
        output = {
            "verification": verified,
            "physics_steps": 0,
            "new_scientific_attempts": 0,
            "capture_head": prepared["head"],
            "upstream_commit": reference["commit"],
            "upstream_configuration": config,
            "policy_interface_maximum_errors": maximum,
            "policy_frames": len(recorded_actions),
            "contact_reconstruction_mismatches": int(mismatch),
            "support_frame_counts": contacts,
            "phase_descriptions": phase,
            "model_joint_parameters": model_diff,
            "current_mass_kg": float(current_model.body_mass.sum()),
            "upstream_mass_kg": float(upstream_model.body_mass.sum()),
            "upstream_initial_qpos": initial_upstream,
            "capture_initial_qpos": rows[0]["qpos"],
            "same_state_passive_torque_difference_rms_nm": float(
                np.sqrt(np.mean(np.square(passive_deltas)))
            ),
            "same_state_extra_damping_rms_nm": float(
                np.sqrt(np.mean(np.square(extra_damping)))
            ),
            "recorded_control_rms_nm": float(
                np.sqrt(np.mean(np.square(actuator_effort)))
            ),
            "causal_scope": "Fixed observed states only; model/startup/command-domain differences are candidates, not isolated closed-loop causes.",
        }
        write_new(run.path / "analysis.json", output)
        write_new(run.path / "reference-manifest.json", reference)
        with (run.path / "provenance.csv").open("x", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["artifact", "sha256"])
            for path in (
                args.capture / "manifest.json",
                args.capture / "attempt_01.jsonl",
                args.prepared / "manifest.json",
                Path(__file__),
                ROOT / ".substrate/rl/policy.pt",
            ):
                writer.writerow([str(path), digest(path)])
            writer.writerows(
                (str(args.reference / name), value)
                for name, value in reference["files"].items()
            )
        run.result.update(
            status="OFFLINE_VERIFIED",
            scope="frozen_trace_diagnosis",
            capability_status="NO_NEW_CLAIM",
            physics_steps=0,
            live_runs=0,
        )
    print(
        json.dumps(
            {
                k: output[k]
                for k in (
                    "physics_steps",
                    "policy_interface_maximum_errors",
                    "contact_reconstruction_mismatches",
                    "phase_descriptions",
                    "current_mass_kg",
                    "upstream_mass_kg",
                    "same_state_extra_damping_rms_nm",
                    "recorded_control_rms_nm",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
