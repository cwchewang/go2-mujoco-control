"""No-solver scope and effective seed-log checks."""

import json
import tempfile
import unittest
from pathlib import Path
from . import mjpc_warmstart_observation as warm


class WarmstartTests(unittest.TestCase):
    def test_frozen_scope(self):
        self.assertEqual(warm.DESIGN["modes"], ["retain", "zero"])
        self.assertEqual(warm.DESIGN["optimizer_calls_max"], 8)
        self.assertEqual(warm.DESIGN["private_derived_upper"], 8 * (35 * 49 + 37 + 700))
        self.assertEqual(warm.DESIGN["private_reserved_max"], 8 * 4096)
        self.assertEqual(warm.DESIGN["tolerance"], 1e-9)

    def test_retain_must_not_change_seed_and_zero_must_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "trace"
            rows = [
                {"mode": "retain", "delegate": "fake"},
                {
                    "index": 1,
                    "start_ns": 1,
                    "end_ns": 2,
                    "before_hash": "a",
                    "effective_hash": "a",
                    "effective_zero": False,
                },
            ]
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            warm.seed_records(p, "retain", 1)
            rows[1]["effective_hash"] = "b"
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            with self.assertRaises(ValueError):
                warm.seed_records(p, "retain", 1)
            rows[0]["mode"] = "zero"
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            with self.assertRaises(ValueError):
                warm.seed_records(p, "zero", 1)
            rows[1]["effective_zero"] = True
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            warm.seed_records(p, "zero", 1)
            with self.assertRaises(ValueError):
                warm.seed_records(p, "zero", 2)
