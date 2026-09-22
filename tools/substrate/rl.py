"""Pinned wty-yy Go2 CTS deployment convention; no terrain or privileged state."""

import hashlib
import io
from pathlib import Path
import numpy as np
from .contracts import POLICY_JOINTS, TorqueCommand, reorder, vector

DEFAULT = np.array(
    [0.1, 0.8, -1.5, -0.1, 0.8, -1.5, 0.1, 1.0, -1.5, -0.1, 1.0, -1.5], dtype=np.float32
)


def observation45(observation, command, previous_action):
    observation.validate()
    cmd = vector(command, 3, "command").astype(np.float32)
    if (np.abs(cmd) > [2.0, 1.0, 2.5]).any():
        raise ValueError("command outside declared checkpoint envelope")
    w, x, y, z = observation.quaternion_wxyz
    gravity = np.array(
        [2 * (-z * x + w * y), -2 * (z * y + w * x), 1 - 2 * (w * w + z * z)]
    )
    result = np.concatenate(
        (
            vector(observation.angular_velocity_body, 3, "omega") * 0.25,
            gravity,
            cmd * np.array([2.0, 2.0, 0.25], dtype=np.float32),
            reorder(observation.position, observation.joint_names, POLICY_JOINTS)
            - DEFAULT,
            reorder(observation.velocity, observation.joint_names, POLICY_JOINTS)
            * 0.05,
            vector(previous_action, 12, "previous action"),
        )
    ).astype(np.float32)
    if not np.isfinite(result).all():
        raise ValueError("float32 observation overflow")
    return result


class FrozenPolicy:
    frequency_hz = 50
    information_regime = "proprioceptive"

    def __init__(self, checkpoint, expected_sha256):
        import torch

        path = Path(checkpoint)
        self.checkpoint_bytes = path.read_bytes()
        if hashlib.sha256(self.checkpoint_bytes).hexdigest() != expected_sha256:
            raise ValueError("checkpoint SHA-256 mismatch")
        self.torch = torch
        self.path = path
        self.reset()

    def reset(self):
        # Exported policies may contain internal observation history.
        # Reloading restores it as well as the explicit previous-action vector.
        self.policy = self.torch.jit.load(
            io.BytesIO(self.checkpoint_bytes), map_location="cpu"
        ).eval()
        self.previous_action = np.zeros(12)
        self.failed = False

    def act(self, observation, command):
        if self.failed:
            raise RuntimeError("policy failure requires explicit reset")
        # Validate before stateful inference. After inference failure, history may
        # have advanced, so continuing the episode is forbidden until reset.
        obs = observation45(observation, command, self.previous_action)
        try:
            with self.torch.inference_mode():
                result = self.policy(self.torch.from_numpy(obs).unsqueeze(0))
            action = result[0] if isinstance(result, tuple) else result
            if tuple(action.shape) != (1, 12):
                raise ValueError("invalid policy action shape")
            action = vector(action.detach().cpu().numpy()[0], 12, "policy action")
            target = DEFAULT + np.float32(0.25) * action.astype(np.float32)
            output = TorqueCommand(
                POLICY_JOINTS,
                np.zeros(12),
                target,
                np.zeros(12),
                np.full(12, 20.0),
                np.full(12, 0.5),
            )
            self.previous_action = action.copy()
            return output
        except Exception:
            self.failed = True
            raise
