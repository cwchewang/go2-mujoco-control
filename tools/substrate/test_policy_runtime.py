"""Real TorchScript state isolation tests using tiny deterministic synthetic policies."""

import hashlib
from pathlib import Path
import tempfile
import unittest
import numpy as np
import torch
from .contracts import Proprioception, POLICY_JOINTS
from .rl import FrozenPolicy, DEFAULT, observation45


class Counter(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.register_buffer("counter", torch.zeros(1))

    def forward(self, x):
        self.counter.add_(1)
        return torch.ones((1, 12)) * self.counter


class Bad(torch.nn.Module):
    def forward(self, x):
        return torch.full((1, 12), float("nan"))


class PolicyIsolation(unittest.TestCase):
    def obs(self):
        return Proprioception(
            POLICY_JOINTS,
            DEFAULT,
            np.zeros(12),
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.zeros(3),
        )

    def save(self, path, model):
        torch.jit.script(model).save(str(path))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_state_reset_uses_verified_bytes_not_changed_path(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "model.pt"
            sha = self.save(p, Counter())
            policy = FrozenPolicy(p, sha)
            first = policy.act(self.obs(), [0, 0, 0]).position_target
            second = policy.act(self.obs(), [0, 0, 0]).position_target
            self.assertFalse(np.array_equal(first, second))
            p.write_bytes(b"corrupted after initialization")
            policy.reset()
            np.testing.assert_array_equal(
                first, policy.act(self.obs(), [0, 0, 0]).position_target
            )

    def test_instances_have_independent_history(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "model.pt"
            sha = self.save(p, Counter())
            a, b = FrozenPolicy(p, sha), FrozenPolicy(p, sha)
            first = a.act(self.obs(), [0, 0, 0]).position_target
            a.act(self.obs(), [0, 0, 0])
            np.testing.assert_array_equal(
                first, b.act(self.obs(), [0, 0, 0]).position_target
            )

    def test_bad_inference_latches_failure_until_reset(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "model.pt"
            sha = self.save(p, Bad())
            policy = FrozenPolicy(p, sha)
            with self.assertRaises(ValueError):
                policy.act(self.obs(), [0, 0, 0])
            with self.assertRaisesRegex(RuntimeError, "reset"):
                policy.act(self.obs(), [0, 0, 0])
            policy.reset()
            self.assertFalse(policy.failed)

    def test_float32_overflow_never_enters_network(self):
        obs = Proprioception(
            POLICY_JOINTS,
            DEFAULT,
            np.zeros(12),
            np.array([1.0, 0, 0, 0]),
            np.full(3, 1e100),
        )
        with np.errstate(over="ignore"), self.assertRaises(ValueError):
            observation45(obs, [0, 0, 0], np.zeros(12))


if __name__ == "__main__":
    unittest.main()
