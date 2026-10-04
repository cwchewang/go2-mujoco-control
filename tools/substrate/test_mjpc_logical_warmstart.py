"""No-solver admission and mismatch-recovery contracts."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from . import mjpc_logical_warmstart as m


class LogicalContracts(unittest.TestCase):
    def test_no_old_budget_or_threshold_substitution(self):
        value = m.protocol()
        for key, bad in (
            ("id", "mjpc-adaptation-original-3s-v1"),
            ("max_attempts", 5),
            ("max_private_upper", 1471201),
            ("tolerance", 1e-8),
        ):
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "protocol.json"
                p.write_text(json.dumps({**value, key: bad}))
                with mock.patch.object(m, "PROTOCOL", p), self.assertRaises(ValueError):
                    m.protocol()

    def test_wrong_owner_reaps_new_process(self):
        fake = mock.Mock()
        fake.ready = {
            "warmstart_owner": "worker",
            "worker_count": 4,
            "horizon_steps": 36,
            "planner_dt": 0.01,
        }
        rt = {"canonical_xml": "canonical.xml"}
        with (
            tempfile.TemporaryDirectory() as d,
            mock.patch.object(m.native_runtime, "verify", return_value=rt),
            mock.patch.object(m, "NativeMJPCController", return_value=fake),
        ):
            with self.assertRaises(ValueError):
                m.construct(Path(d) / "binary", Path(d) / "sidecar", "logical", Path(d))
        fake.close.assert_called_once()

    def test_comparison_does_not_hide_over_threshold_delta(self):
        with tempfile.TemporaryDirectory() as d:
            dirs = [Path(d) / x for x in ("a", "b")]
            for p in dirs:
                p.mkdir()
            for i, p in enumerate(dirs):
                rows = []
                for tick in (0, 1500):
                    rows.append(
                        {
                            "tick": tick,
                            "qpos": [0, 0, 0.3, 1, 0, 0, 0] + [0] * 12,
                            "qvel": [0] * 18,
                            "terminal_reason": "horizon" if tick else None,
                            "action": {
                                "ctrl": [i * 2e-9] * 12,
                                "saturated": [False] * 12,
                            },
                            "target": {"position_target": [i * 2e-9] * 12},
                        }
                    )
                (p / "raw.jsonl").write_text("\n".join(json.dumps(x) for x in rows))
            result = m.compare(*dirs)
            self.assertEqual(result["differences"]["target"]["first_over_1e_9"], 0)
            self.assertEqual(result["differences"]["target"]["max_abs"], 2e-9)


if __name__ == "__main__":
    unittest.main()
