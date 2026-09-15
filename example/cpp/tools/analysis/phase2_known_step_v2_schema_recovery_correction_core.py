#!/usr/bin/env python3
from __future__ import annotations
import csv
import hashlib
import importlib.util
import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

LEGS = ("fr", "fl", "rr", "rl")
C_HEAD = "b281993b81b3bf6a083eccfb5805789026913837"
SCENE_SHA = "8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc"
DROP_INDICES = [211, 264, 317, 370]
EXTRA_TOKEN = "known_step_v2_"
V2, S = None, None

def load_modules():
    global V2, S
    root = Path(__file__).resolve().parents[4]
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    V2 = load("frozen_v2_correction", root / "example/cpp/tools/analysis/analyze_phase2_known_step_edge_aware_v2.py")
    S = load("schema_prior_correction", root / "example/cpp/tools/analysis/analyze_phase2_known_step_v2_schema_readjudication.py")

def sha(path):
    if not path.is_file():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()

def kv(path):
    out = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                out[key] = value
    return out

def js(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): js(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [js(v) for v in value]
    return value

def csv_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(js(value), sort_keys=True, separators=(",", ":"))
    return value

def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key, "")) for key in fields})

def gate(run, name, passed, detail):
    return {"run": run, "gate": name, "status": "PASS" if passed else "FAIL", "detail": detail if isinstance(detail, str) else js(detail)}

def old_source(repo):
    rel = "example/cpp/trot/trot_experiment_diagnostics.cpp"
    data = subprocess.check_output(["git", "show", f"{C_HEAD}:{rel}"], cwd=str(repo))
    lines = data.decode("utf-8", errors="replace").splitlines()
    header_lines = [i + 1 for i, line in enumerate(lines) if "_s_exit,known_step_v2_" in line]
    exit_lines = [i + 1 for i, line in enumerate(lines) if '<< "," << v2.s_exit' in line]
    command_lines = [i + 1 for i, line in enumerate(lines) if "known_step_v2_command_x_m" in line]
    return {
        "path": rel,
        "sha256": hashlib.sha256(data).hexdigest(),
        "header_extra_prefix_lines": header_lines,
        "header_extra_prefix_count": len(header_lines),
        "log_sample_s_exit_lines": exit_lines,
        "log_sample_command_x_lines": command_lines,
        "log_sample_contiguous_sequence": bool(exit_lines and command_lines and 0 < command_lines[0] - exit_lines[0] <= 5),
        "header_literal_token_construction": bool(header_lines),
    }

def recover(repo, cdir):
    path = cdir / "data.csv"
    header_bytes = path.open("rb").readline()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        raw = list(reader)
    widths = Counter(len(row) for row in raw)
    drops = [i for i, token in enumerate(header) if token == EXTRA_TOKEN]
    repaired = [token for i, token in enumerate(header) if i not in drops]
    transitions = []
    for i in drops:
        previous = header[i - 1] if i else ""
        following = header[i + 1] if i + 1 < len(header) else ""
        leg = next((leg for leg in LEGS if previous == f"known_step_v2_{leg}_s_exit" and following == f"known_step_v2_{leg}_command_world_x_m"), "")
        transitions.append({"index": i, "token": header[i], "previous": previous, "following": following, "leg": leg})
    rows = [dict(zip(repaired, row)) for row in raw]
    source = old_source(repo)
    semantic = S.recovery_validation(rows, repaired)
    unique = drops == DROP_INDICES and len(repaired) == 776 and all(repaired) and len(set(repaired)) == len(repaired) and len(raw) == 5005 and dict(widths) == {776: 5005} and all(item["leg"] for item in transitions)
    checks = [
        gate("C", "raw_header_width_exact_780", len(header) == 780, len(header)),
        gate("C", "raw_data_rows_exact_5005", len(raw) == 5005, len(raw)),
        gate("C", "raw_all_data_rows_width_776", dict(widths) == {776: 5005}, dict(widths)),
        gate("C", "literal_extra_tokens_exact", drops == DROP_INDICES and all(item["token"] == EXTRA_TOKEN for item in transitions), transitions),
        gate("C", "source_neighbor_context_exact", len(transitions) == 4 and all(item["leg"] for item in transitions), transitions),
        gate("C", "no_empty_or_duplicate_repaired_names", all(repaired) and len(set(repaired)) == len(repaired), ""),
        gate("C", "source_header_construction", source["header_extra_prefix_count"] == 1 and source["header_literal_token_construction"], source),
        gate("C", "source_log_sample_contiguous_sequence", source["log_sample_contiguous_sequence"], source),
        gate("C", "candidate_mapping_unique", unique, {"drop_indices": drops, "repaired_width": len(repaired)}),
    ] + semantic
    return {
        "header": header, "raw": raw, "repaired": repaired, "rows": rows,
        "drops": drops, "transitions": transitions, "widths": dict(sorted(widths.items())),
        "checks": checks, "all_pass": all(item["status"] == "PASS" for item in checks),
        "raw_header_width": len(header), "raw_data_rows": len(raw),
        "repaired_width": len(repaired),
        "raw_header_sha256": hashlib.sha256(header_bytes).hexdigest(),
        "derived_header_sha256": hashlib.sha256((",".join(repaired) + "\n").encode()).hexdigest(),
        "source": source,
    }

def parent_expected(path):
    out = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row.get("scope") and row.get("artifact") and row.get("sha256"):
                out.setdefault(row["scope"], {})[row["artifact"]] = row["sha256"]
    return out

def provenance(repo, a, b, c, parent, meta, source, script):
    expected = parent_expected(parent)
    records, matches = [], {}
    for scope, run, source_scope in (("A_raw_frozen", a, "A_raw_frozen"), ("V1_B_raw_frozen", b, "V1_B_frozen"), ("C_raw_immutable", c, "C_raw_immutable")):
        wanted = expected.get(source_scope, {})
        ok = bool(wanted)
        for name, expected_hash in sorted(wanted.items()):
            actual = sha(run / name)
            equal = actual == expected_hash
            ok = ok and equal
            records.append({"scope": scope, "artifact": name, "path": str(run / name), "sha256": actual, "expected_sha256": expected_hash, "matches": equal})
        matches[scope] = ok
    scene = repo / "unitree_robots/go2/scene_known_step_5cm.xml"
    scene_hash = sha(scene)
    records.append({"scope": "scene", "artifact": str(scene.relative_to(repo)), "path": str(scene), "sha256": scene_hash, "expected_sha256": SCENE_SHA, "matches": scene_hash == SCENE_SHA})
    current = repo / "example/cpp/trot/trot_experiment_diagnostics.cpp"
    records.append({"scope": "runtime_source_current", "artifact": str(current.relative_to(repo)), "path": str(current), "sha256": sha(current), "matches": True, "note": "parent logger fix preserved"})
    records.append({"scope": "runtime_source_at_C_HEAD", "artifact": source["path"], "path": f"git:{C_HEAD}:{source['path']}", "sha256": source["sha256"], "matches": True})
    records.append({"scope": "analysis_source", "artifact": str(script.relative_to(repo)), "path": str(script), "sha256": sha(script), "matches": True})
    metadata_ok = meta.get("git_head") == C_HEAD and meta.get("git_dirty") == "false" and meta.get("scene_sha256") == SCENE_SHA
    records.append({"scope": "C_runtime_metadata", "artifact": "run_metadata.txt", "path": str(c / "run_metadata.txt"), "sha256": sha(c / "run_metadata.txt"), "matches": metadata_ok, "recorded_git_head": meta.get("git_head", ""), "expected_head": C_HEAD, "git_dirty": meta.get("git_dirty", ""), "controller_sha256": meta.get("controller_sha256", ""), "simulator_sha256": meta.get("simulator_sha256", ""), "scene_sha256": meta.get("scene_sha256", "")})
    records.append({"scope": "derived_header", "artifact": "recovered_header_utf8_plus_lf", "path": "in-memory only", "sha256": "", "matches": True, "note": "no derived data.csv emitted"})
    return records, {"A_raw_hashes_match": matches.get("A_raw_frozen", False), "V1_B_raw_hashes_match": matches.get("V1_B_raw_frozen", False), "C_raw_hashes_match_parent": matches.get("C_raw_immutable", False), "C_runtime_metadata_match": metadata_ok, "scene_hash": scene_hash, "C_recorded_head": meta.get("git_head", "")}

def repair_map(audit):
    rows, index = [], 0
    drops = set(audit["drops"])
    for raw_index, token in enumerate(audit["header"]):
        action = "DROP_DUPLICATED_PREFIX_HEADER_TOKEN" if raw_index in drops else "KEEP"
        rows.append({"raw_header_index": raw_index, "original_token": token, "action": action, "repaired_header_index": "" if action != "KEEP" else index, "preceding_canonical_field": audit["header"][raw_index - 1] if raw_index else "", "following_canonical_field": audit["header"][raw_index + 1] if raw_index + 1 < len(audit["header"]) else ""})
        if action == "KEEP":
            index += 1
    return rows
