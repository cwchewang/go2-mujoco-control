"""Open-loop command sensitivity on recorded states; no predicted locomotion."""

import argparse
import math
from pathlib import Path
import numpy as np

from .contracts import Proprioception
from .guards import zero_step_guard
from .integrity import (
    EvidenceRun,
    digest,
    experiment_lock,
    strict_json,
    verify_bundle,
    verify_manifest,
    write_new,
)
from .rl import FrozenPolicy

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    with (
        experiment_lock(),
        zero_step_guard(),
        EvidenceRun(
            args.output, {"operation": "fixed_recorded_state_policy_sensitivity"}
        ) as run,
    ):
        import torch

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        verify_manifest(args.capture)
        prepared = verify_bundle(args.prepared)
        rows = [
            strict_json(line)
            for line in (args.capture / "attempt_01.jsonl").read_text().splitlines()
        ]
        frames = [row for row in rows if row["policy_wall_s"] is not None]
        targets = {}
        # Declared fixed grid, no adaptive search for a favorable trajectory.
        for command in (0.0, 0.15, 0.3, 1.0):
            policy = FrozenPolicy(
                ROOT / ".substrate/rl/policy.pt", prepared["checkpoint_sha256"]
            )
            values = []
            for row in frames:
                q, v = np.array(row["qpos"]), np.array(row["qvel"])
                layout = prepared["layout"]
                obs = Proprioception(
                    tuple(layout["names"]),
                    q[layout["qadr"]],
                    v[layout["vadr"]],
                    q[3:7],
                    v[3:6],
                )
                values.append(policy.act(obs, [command, 0, 0]).position_target)
            targets[str(command)] = np.array(values)
        sensitivity = {
            command: {
                "target_delta_from_zero_rms_rad": float(
                    np.sqrt(np.mean((value - targets["0.0"]) ** 2))
                ),
                "target_temporal_delta_rms_rad": float(
                    np.sqrt(np.mean(np.diff(value, axis=0) ** 2))
                ),
            }
            for command, value in targets.items()
        }
        # Arithmetic illustration of the visible source reward, not recovered
        # training metadata or measured reward from the original training run.
        reward = []
        body_vx = []
        for row in rows[2500:]:
            q = np.array(row["qpos"])[3:7]
            v = np.array(row["qvel"][:3])
            body = (
                v * (2 * q[0] ** 2 - 1)
                - np.cross(q[1:], v) * q[0] * 2
                + q[1:] * np.dot(q[1:], v) * 2
            )
            body_vx.append(float(body[0]))
            reward.append(math.exp(-((0.15 - body[0]) ** 2 + body[1] ** 2) / 0.25))
        result = {
            "physics_steps": 0,
            "new_scientific_attempts": 0,
            "recorded_policy_frames": len(frames),
            "fixed_state_command_grid_mps": [0.0, 0.15, 0.3, 1.0],
            "sensitivity": sensitivity,
            "visible_source_reward_illustration": {
                "sigma": 0.25,
                "standing_at_command_0_15": math.exp(-(0.15**2) / 0.25),
                "standing_at_command_1_0": math.exp(-1 / 0.25),
                "recorded_primary_window_mean": float(np.mean(reward)),
                "recorded_body_vx_mean": float(np.mean(body_vx)),
                "training_run_configuration_proven": False,
            },
            "scope": "Identical measured states with fresh policy history per fixed command; previous actions evolve only inside inference. Not a new plant rollout, speed prediction, causal intervention or tuning recommendation.",
            "raw_sha256": digest(args.capture / "attempt_01.jsonl"),
            "checkpoint_sha256": prepared["checkpoint_sha256"],
        }
        write_new(run.path / "analysis.json", result)
        run.result.update(
            status="OFFLINE_VERIFIED",
            scope="open_loop_inference_only",
            capability_status="NO_NEW_CLAIM",
            physics_steps=0,
            live_runs=0,
        )
    print(result)


if __name__ == "__main__":
    main()
