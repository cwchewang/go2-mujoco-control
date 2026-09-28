"""Zero-physics recomputation of the sealed #189 yaw probe from free-joint qvel-z."""
import argparse
import hashlib
import json
import math
from pathlib import Path

TRACE_SHA256 = "4b87f690d9c2e1a88e1dd99f3234574b7adc40b83c1700a3517e50bebe479697"
BUNDLE = Path("cwchewang-go2-mujoco-control-189/20260924T101659Z-e40b09335723")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle = args.evidence_root / BUNDLE
    trace = bundle / "capture-01/flat_yaw_probe.jsonl"
    protocol_path = bundle / "capture-01/protocol.json"
    old_analysis_path = bundle / "capture-01/flat_yaw_probe_analysis.json"
    before = hashlib.sha256(trace.read_bytes()).hexdigest()
    if before != TRACE_SHA256:
        raise SystemExit("sealed yaw trace hash mismatch")
    protocol = json.loads(protocol_path.read_text())
    case = next(row for row in protocol["cases"] if row["id"] == "flat_yaw_probe")
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    commands = case["commands"]
    start = commands[0][0]
    end = commands[1][0] if len(commands) > 1 else case["horizon_ticks"]
    selected = [
        row
        for row in rows
        if start + case["measurement_delay_ticks"] <= row["tick"] < end
    ]
    command = commands[0][3]
    values = [float(row["qvel"][5]) for row in selected]
    mean = math.fsum(values) / len(values)
    mae = math.fsum(abs(value - command) for value in values) / len(values)
    tolerance = max(
        protocol["tracking_absolute_tolerance"],
        protocol["tracking_relative_tolerance"] * abs(command),
    )
    old = json.loads(old_analysis_path.read_text())
    after = hashlib.sha256(trace.read_bytes()).hexdigest()
    record = {
        "operation": "offline raw-trajectory recomputation; no MuJoCo import or physics integration",
        "source_evidence_bundle_relative_to_evidence_root": str(BUNDLE),
        "source_trace": "capture-01/flat_yaw_probe.jsonl",
        "source_protocol": "capture-01/protocol.json",
        "source_trace_sha256_before": before,
        "source_trace_sha256_after": after,
        "source_trace_unchanged": before == after,
        "source_rows": len(rows),
        "selected_rows": len(selected),
        "measurement_window": {
            "start_tick_inclusive": start + case["measurement_delay_ticks"],
            "end_tick_exclusive": end,
        },
        "frozen_command_wz_rad_s": command,
        "corrected_body_local_qvel_z_mean_rad_s": mean,
        "corrected_mae_rad_s": mae,
        "frozen_tracking_tolerance_rad_s": tolerance,
        "corrected_classification": "PERFORMANCE_FAIL" if mae > tolerance else "PASS",
        "historical_schema2_analysis": {
            "mean": old["windows"][0]["axes"]["wz"]["mean"],
            "mae": old["windows"][0]["axes"]["wz"]["mae"],
            "verdict": old["verdict"],
        },
        "physics_steps": 0,
    }
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
