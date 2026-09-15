#!/usr/bin/env python3
"""No-live regression test for the Trot CSV header/sample schema."""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "example/cpp/tools/analysis"))
import analyze_phase2_known_step_v2_schema_readjudication as schema  # noqa: E402


def main() -> int:
    source = (ROOT / "example/cpp/trot/trot_experiment_diagnostics.cpp").read_text(encoding="utf-8")
    assert "_s_exit,known_step_v2_" not in source
    assert '<< known_step_leg_names[leg] << "_s_exit"' in source

    header = []
    for leg in schema.LEGS:
        header.extend([
            f"known_step_v2_{leg}_s_exit",
            f"known_step_v2_{leg}_command_world_x_m",
            f"known_step_v2_{leg}_command_world_z_m",
        ])
    sample = ["0"] * len(header)
    parsed = list(csv.reader(io.StringIO(",".join(header) + "\n" + ",".join(sample) + "\n")))
    assert len(parsed[0]) == len(parsed[1])
    assert all(token for token in parsed[0])
    assert len(set(parsed[0])) == len(parsed[0])

    malformed = header[:1] + ["known_step_v2_"] + header[1:]
    drops, repaired = schema.candidate_header(malformed)
    assert drops == [1]
    assert repaired == header
    assert all(token for token in repaired)

    print("PASS no-live CSV schema regression: corrected header/sample widths and no empty V2 token")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
