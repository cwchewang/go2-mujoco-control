"""Zero-integration analysis of the two sealed, permanently closed MJPC traces."""
import argparse
import hashlib
import json
import math
from pathlib import Path

A = "_runs/mjpc_adaptation_diagnostic_execution_20261002/original_capture_20261002T164948Z"
REF = "example/cpp/experiments/_runs/shared_baseline_probes_v1/run_20261002T085338452324Z"
HASHES = {
    A + "/raw.jsonl": "9a4f2711f558b80ac58c803406971f43be7c44f4c5e64f7a50c728e2a7440e55",
    REF + "/mjpc_baseline_1.jsonl": "e5f760c54a57d12e8da6150972cb084414c3f9d84f1827ac9582b292532a3841",
}
THRESHOLDS = (0, 1e-12, 1e-9, 1e-6, 1e-3, 0.1, 1)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def sealed(root, directory):
    path = root / directory
    manifest = read(path / "manifest.json")
    bad = [name for name, sha in manifest.items() if digest(path / name) != sha]
    if bad:
        raise ValueError("sealed member mismatch: " + repr(bad))
    return {"path": directory, "manifest_sha256": digest(path / "manifest.json"),
            "verified_members": len(manifest)}


def rows(path):
    result = [json.loads(line) for line in path.read_text().splitlines()]
    for tick, row in enumerate(result):
        if row["tick"] != tick or abs(row["sim_time_s"] - 0.002 * tick) > 1e-12:
            raise ValueError("nonconsecutive tick/time")
        for key, size in (("qpos", 19), ("qvel", 18), ("command", 3)):
            values = row[key]
            if len(values) != size or any(not math.isfinite(x) for x in values):
                raise ValueError("invalid " + key)
        if tick < len(result) - 1 and (row["target"] is None or row["action"] is None):
            raise ValueError("missing nonterminal action")
    return result


def vector(row, field):
    if field in ("qpos", "qvel", "command"):
        return row[field]
    if field == "q_des":
        return None if row["target"] is None else row["target"]["position_target"]
    if field == "ctrl":
        return None if row["action"] is None else row["action"]["ctrl"]
    raise ValueError(field)


def delta(x, y):
    if len(x) != len(y) or not x:
        raise ValueError("comparison dimension mismatch")
    differences = [abs(u - v) for u, v in zip(x, y)]
    if any(not math.isfinite(d) for d in differences):
        raise ValueError("nonfinite comparison")
    index = max(range(len(x)), key=differences.__getitem__)
    return {"max_abs": differences[index], "index": index, "A": x[index], "reference": y[index]}


def last(row):
    d = row.get("controller_diagnostics")
    return {} if d is None else d["controller"]["last_step"]


def first(trace, predicate):
    return next((row["tick"] for row in trace if predicate(row)), None)


def analyze(root):
    for name, sha in HASHES.items():
        if digest(root / name) != sha:
            raise ValueError("changed raw: " + name)
    bundles = [sealed(root, name) for name in (A, REF)]
    a = rows(root / A / "raw.jsonl")
    b = rows(root / REF / "mjpc_baseline_1.jsonl")
    if len(a) != 887 or len(b) != 1288:
        raise ValueError("sealed terminal dimensions changed")
    pairs = list(zip(a, b))
    fields = {}
    for name in ("qpos", "qvel", "command", "q_des", "ctrl"):
        measured = [(x["tick"], delta(vector(x, name), vector(y, name)))
                    for x, y in pairs if vector(x, name) is not None and vector(y, name) is not None]
        fields[name] = {
            "first_above": {str(t): next(({"tick": tick, **d} for tick, d in measured
                                         if d["max_abs"] > t), None) for t in THRESHOLDS},
            "max_prefix_abs": max(d["max_abs"] for _, d in measured),
        }
    contact = next(({"tick": x["tick"], "A_supports": x["supports"],
                     "reference_supports": y["supports"],
                     "A_forbidden": x["forbidden_contacts"],
                     "reference_forbidden": y["forbidden_contacts"]}
                    for x, y in pairs if x["supports"] != y["supports"]
                    or x["forbidden_contacts"] != y["forbidden_contacts"]), None)
    x, y = a[10], b[10]
    joint = fields["q_des"]["first_above"]["0"]["index"]
    pd_residual = [(x["action"]["pd"][i] - y["action"]["pd"][i])
                   - (x["target"]["kp"][i] * (x["target"]["position_target"][i]
                      - y["target"]["position_target"][i]))
                   for i in range(12)]
    old_prep = read(Path(read(root / REF / "preparation-reference.json")["path"]) / "admission.json")
    old_build = read(Path(old_prep["qualification"]["path"]) / "build-identity.json")
    dependency_equality = {key: old_build["inputs"][key] == read(root / A / "controller-identity.json")["inputs"][key]
                           for key in ("compiler", "mujoco_library", "mujoco_headers", "lock_sha256", "mjpc", "abseil")}
    observation = "_runs/mjpc_short_sequence_observation_launcherfix_20261003"
    bundles.append(sealed(root, observation))
    sequence_audit = []
    for trial in ("original_repeat1", "original_repeat2", "fixed_repeat1", "fixed_repeat2"):
        native = [json.loads(line) for line in (root / observation / "trials" / trial / "native.jsonl").read_text().splitlines()]
        samples = [line for line in native if "tick" in line]
        wire_differences = []
        output_differences = []
        live_wire_differences = []
        canonical_names = old_prep["state_joint_order"]
        native_names = native[0]["ready"]["joint_names"]
        native_indices = [canonical_names.index(name) for name in native_names]
        for line in samples:
            raw = a[line["tick"]]
            values = [float(value) for value in line["request"].split()[2:]]
            expected = [raw["sim_time_s"], *raw["command"], *raw["qpos"], *raw["qvel"]]
            wire_differences.append(delta(values, expected)["max_abs"])
            qpos = raw["qpos"][:7] + [raw["qpos"][7 + i] for i in native_indices]
            qvel = raw["qvel"][:6] + [raw["qvel"][6 + i] for i in native_indices]
            live_wire_differences.append({"tick": line["tick"], "max_abs": delta(values, [raw["sim_time_s"], *raw["command"], *qpos, *qvel])["max_abs"]})
            difference = delta(line["response"]["q_des"], raw["target"]["position_target"])
            output_differences.append({"tick": line["tick"], "max_abs": difference["max_abs"], "index": difference["index"],
                                       "sequence_q_des": difference["A"], "old_A_q_des": difference["reference"]})
        sequence_audit.append({"trial": trial, "reset_requests": sum(line.get("request") == "reset" for line in native),
                               "wire_vs_raw_unreordered_max_abs_difference": max(wire_differences),
                               "canonical_joint_names": canonical_names, "native_joint_names": native_names,
                               "first_production_wire_difference": next((item for item in live_wire_differences if item["max_abs"] > 0), None),
                               "tick10_cost": samples[-1]["response"]["cost"],
                               "tick10_A_cost": last(a[10])["cost"],
                               "first_q_des_difference_from_A": next((item for item in output_differences if item["max_abs"] > 0), None)})

    identity = read(root / A / "controller-identity.json")
    model = read(root / A / "model-audit.json")
    predictions = [json.loads(line) for line in (root / A / "predictions.jsonl").read_text().splitlines()]
    predicted_gap = []
    for p in predictions[:4]:
        anchor = round(p["anchor_time_s"] / 0.002)
        at = anchor + 5
        nominal = dict(p["states"][1])
        native_names = a[0]["target"]["joint_names"]
        canonical_indices = [native_names.index(name) for name in old_prep["state_joint_order"]]
        nominal["qpos"] = nominal["qpos"][:7] + [nominal["qpos"][7 + i] for i in canonical_indices]
        nominal["qvel"] = nominal["qvel"][:6] + [nominal["qvel"][6 + i] for i in canonical_indices]
        predicted_gap.append({"anchor_tick": anchor, "canonical_tick": at,
                              "qpos_abs": delta(nominal["qpos"], a[at]["qpos"])["max_abs"],
                              "qvel_abs": delta(nominal["qvel"], a[at]["qvel"])["max_abs"],
                              "candidate_id": p["candidate_id"],
                              "private_contacts": nominal["active_contacts"]})
    return {
        "schema": 1, "scope": "offline_closed_trace_diagnosis",
        "canonical_integration_steps": 0, "optimizer_calls": 0,
        "sealed_bundles": bundles, "raw_sha256": HASHES,
        "frames": {"A": len(a), "reference": len(b), "paired": len(pairs)},
        "closed_scopes": {"A": "CLOSED_NO_RETRY", "B": "NOT_RUN_REPRODUCTION_GATE_FAILED"},
        "comparisons": fields, "first_contact_semantics_difference": contact,
        "tick10": {"qpos_exact": x["qpos"] == y["qpos"], "qvel_exact": x["qvel"] == y["qvel"],
                   "command_exact": x["command"] == y["command"],
                   "cost_exact": last(x)["cost"] == last(y)["cost"],
                   "cost": last(x)["cost"], "replanned": [last(z)["replanned"] for z in (x, y)],
                   "joint": x["target"]["joint_names"][joint], "kp": x["target"]["kp"][joint],
                   "PD60_difference_residual_max": max(abs(v) for v in pd_residual)},
        "short_sequence_initialization_audit": sequence_audit,
        "archived_dependency_equality": dependency_equality,
        "version": {"reference_head": old_prep["head"], "A_head": read(root / A / "admission.json")["head"],
                    "physical_fingerprints": [old_prep["physical_sha256"], model["canonical_physical_sha256"]],
                    "mjpc_source_commits": [old_prep["mjpc_source_commit"], identity["inputs"]["mjpc"]["head"]],
                    "binary_sha256": [old_prep["mjpc_binary_sha256"], identity["binary_sha256"]]},
        "first_warning_tick": {label: first(trace, lambda r: r.get("controller_diagnostics")
                            and r["controller_diagnostics"]["controller"]["transport"]["stderr_bytes"] > 0)
                            for label, trace in (("A", a), ("reference", b))},
        "first_saturation_tick": {label: first(trace, lambda r: r["action"] is not None
                                 and any(r["action"]["saturated"]))
                                 for label, trace in (("A", a), ("reference", b))},
        "prediction_caveat": "private 10ms nominal versus canonical 2ms closed-loop; not pure model error",
        "early_prediction_actual_gaps": predicted_gap,
        "hidden_state_missing": ["reference selected trajectories", "old worker mjData warmstart arrays",
                                 "old planner feedback/policy arrays", "FD task schedule at old tick10"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.root), indent=2, sort_keys=True, allow_nan=False))
