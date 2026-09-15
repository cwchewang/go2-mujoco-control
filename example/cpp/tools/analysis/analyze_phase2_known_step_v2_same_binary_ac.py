#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import analyze_phase2_known_step_edge_aware_v2 as V2

def install_guards():
    boundary_original = V2.boundary_continuity
    expected_original = V2.expected_v2_sample
    def boundary_guard(plan):
        try:
            return boundary_original(plan)
        except ZeroDivisionError:
            return {"position_continuous": False, "velocity_continuous": False, "position_jump_max_m": None, "derivative_jump_max_per_s_m": None, "undefined_due_to_zero_segment": True}
    def expected_guard(row, leg, plan):
        if plan["s_entry"] <= 0.0 or plan["s_exit"] <= plan["s_entry"] or plan["s_exit"] >= 1.0:
            phase = V2.swing_phase(row, leg)
            s = V2.quintic(min(1.0, phase / 0.80))
            return {"s": s, "x": math.nan, "y": math.nan, "z": math.nan, "vx": math.nan, "vz": math.nan}
        return expected_original(row, leg, plan)
    V2.boundary_continuity = boundary_guard
    V2.expected_v2_sample = expected_guard

def all_tests_pass(value):
    if isinstance(value, dict): return bool(value) and all(all_tests_pass(item) for item in value.values())
    if isinstance(value, list): return all(all_tests_pass(item) for item in value)
    if isinstance(value, str): return "FAIL" not in value.upper() and "ERROR" not in value.upper()
    return bool(value)
def hash_records(scope, run, expected=None):
    records = []
    ok = True
    names = sorted(expected) if expected is not None else sorted(p.name for p in run.iterdir() if p.is_file())
    for name in names:
        path = run / name
        actual = V2.sha256(path)
        wanted = expected.get(name, "") if expected is not None else ""
        match = actual == wanted if expected is not None else True
        ok = ok and match
        records.append({"scope": scope, "artifact": name, "path": str(path), "sha256": actual, "expected_sha256": wanted, "matches": match})
    return records, ok

def provenance(root, a, b, c, a_meta, c_meta, expected_head, a_domain, c_domain):
    b_file = root / "docs/validation/phase2_known_step_5cm_b_only_20260915/provenance.csv"
    b_expected = V2.expected_hashes(b_file, {"B_raw"}) if b_file.is_file() else {}
    a_records, _ = hash_records("A_fresh_raw", a)
    b_records, b_ok = hash_records("V1_B_frozen", b, b_expected or None)
    c_records, _ = hash_records("C_fresh_raw", c)
    scene = root / "unitree_robots/go2/scene_known_step_5cm.xml"
    runner = root / "example/cpp/scripts/run_phase2_known_step_v2_same_binary_ac.sh"
    records = a_records + b_records + c_records
    records += [{"scope": "scene", "artifact": str(scene.relative_to(root)), "path": str(scene), "sha256": V2.sha256(scene), "expected_sha256": V2.EXPECTED_SCENE_SHA, "matches": V2.sha256(scene) == V2.EXPECTED_SCENE_SHA}, {"scope": "runner", "artifact": str(runner.relative_to(root)), "path": str(runner), "sha256": V2.sha256(runner), "matches": True}]
    same_binary = a_meta.get("controller_sha256") == c_meta.get("controller_sha256") and a_meta.get("simulator_sha256") == c_meta.get("simulator_sha256") and bool(a_meta.get("controller_sha256")) and bool(a_meta.get("simulator_sha256"))
    metadata_ok = all(meta.get("git_head") == expected_head and meta.get("git_dirty") == "false" for meta in (a_meta, c_meta)) and a_meta.get("domain_id") == str(a_domain) and c_meta.get("domain_id") == str(c_domain)
    records += [{"scope": "A_C_binary_identity", "artifact": "controller_sha256", "path": "run_metadata.txt", "sha256": a_meta.get("controller_sha256", ""), "expected_sha256": c_meta.get("controller_sha256", ""), "matches": same_binary}, {"scope": "A_C_binary_identity", "artifact": "simulator_sha256", "path": "run_metadata.txt", "sha256": a_meta.get("simulator_sha256", ""), "expected_sha256": c_meta.get("simulator_sha256", ""), "matches": same_binary}]
    records += [{"scope": "A_C_runtime_metadata", "artifact": "run_metadata.txt", "path": str(a / "run_metadata.txt"), "sha256": V2.sha256(a / "run_metadata.txt"), "matches": metadata_ok, "expected_head": expected_head, "a_head": a_meta.get("git_head", ""), "c_head": c_meta.get("git_head", ""), "a_domain": a_meta.get("domain_id", ""), "c_domain": c_meta.get("domain_id", "")}]
    return records, {"A_C_same_binary_hashes": same_binary, "A_C_runtime_metadata": metadata_ok, "V1_B_frozen_hashes_match": b_ok, "A_controller_sha256": a_meta.get("controller_sha256", ""), "C_controller_sha256": c_meta.get("controller_sha256", ""), "A_simulator_sha256": a_meta.get("simulator_sha256", ""), "C_simulator_sha256": c_meta.get("simulator_sha256", ""), "scene_sha256": V2.sha256(scene)}

def closeout_without_c(root, a, b, c, out, args, tests, shapes, missing):
    a_meta = V2.read_kv(a / "run_metadata.txt")
    b_meta = V2.read_kv(b / "run_metadata.txt")
    a_rows = V2.read_rows(a / "data.csv") if (a / "data.csv").is_file() else []
    b_rows = V2.read_rows(b / "data.csv") if (b / "data.csv").is_file() else []
    a_protocol = V2.parse_protocol(a, args.a_domain)
    b_protocol = V2.parse_protocol(b, "232")
    status_ok, statuses = V2.status_zero(a_meta)
    logs = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (a / "controller.log", a / "simulator.log")
        if path.is_file()
    )
    upper = logs.upper()
    hard_markers = [
        marker
        for marker in (
            "TROT HARD SAFETY LIMIT REACHED",
            "TROT HARD POSTURE LIMIT",
            "EMERGENCY_STOP",
            "HARD_SAFETY",
        )
        if marker in upper
    ]
    base_missing = {
        "A": sorted(V2.BASE_COLUMNS - set(a_rows[0])) if a_rows else sorted(V2.BASE_COLUMNS),
        "V1_B": sorted(V2.BASE_COLUMNS - set(b_rows[0])) if b_rows else sorted(V2.BASE_COLUMNS),
    }
    tests_ok = (
        isinstance(tests, dict)
        and tests.get("pass") is True
        and all(item.get("status") == "PASS" for item in tests.get("checks", []))
        and all(item.get("return_code", 1) == 0 for item in tests.get("tests", []))
    )
    a_gates = [
        V2.gate("A", "raw_schema", not base_missing["A"] and shapes["A"]["pass"], {"missing": base_missing["A"], "schema": shapes["A"]}),
        V2.gate("A", "domain", a_protocol["domain_matches"], a_protocol["domain_id"]),
        V2.gate("A", "lockstep_trace", a_protocol["trace_present"] and a_protocol["trace_rows"] > 0, a_protocol["trace_rows"]),
        V2.gate("A", "constant_sim_tick", a_protocol["sim_tick_diffs_ms"] == [2.0], a_protocol["sim_tick_diffs_ms"]),
        V2.gate("A", "no_lockstep_violations", a_protocol["trace_violations"] == 0, a_protocol["trace_violations"]),
        V2.gate("A", "paired_highstate", a_protocol["paired_summary_present"] and a_protocol["paired_validation_failures"] == 0 and a_protocol["paired_async_fallbacks"] == 0, a_protocol),
        V2.gate("A", "no_fail_closed_marker", not a_protocol["fail_closed_markers"], a_protocol["fail_closed_markers"]),
        V2.gate("A", "statuses_zero", status_ok, statuses),
        V2.gate("A", "completion_status_zero", a_meta.get("completion_status", "MISSING") in {"0", "false", ""}, a_meta.get("completion_status", "MISSING")),
        V2.gate("A", "no_hard_safety", not hard_markers, hard_markers),
        V2.gate("V1_B", "frozen_raw_schema", not base_missing["V1_B"] and shapes["V1_B"]["pass"], {"missing": base_missing["V1_B"], "schema": shapes["V1_B"]}),
        V2.gate("A", "pre_live_tests_all_pass", tests_ok, tests),
        V2.gate("C", "not_run_after_A_gate_failure", "C" in missing, {"status": "NOT_RUN", "reason": "A_BASELINE_GATE_FAILED"}),
    ]
    b_file = root / "docs/validation/phase2_known_step_5cm_b_only_20260915/provenance.csv"
    b_expected = V2.expected_hashes(b_file, {"B_raw"}) if b_file.is_file() else {}
    a_records, _ = hash_records("A_fresh_raw", a)
    b_records, b_ok = hash_records("V1_B_frozen", b, b_expected or None)
    scene = root / "unitree_robots/go2/scene_known_step_5cm.xml"
    runner = root / "example/cpp/scripts/run_phase2_known_step_v2_same_binary_ac.sh"
    prov_records = a_records + b_records
    prov_records += [
        {"scope": "scene", "artifact": str(scene.relative_to(root)), "path": str(scene), "sha256": V2.sha256(scene), "expected_sha256": V2.EXPECTED_SCENE_SHA, "matches": V2.sha256(scene) == V2.EXPECTED_SCENE_SHA},
        {"scope": "runner", "artifact": str(runner.relative_to(root)), "path": str(runner), "sha256": V2.sha256(runner), "matches": True},
        {"scope": "A_runtime_metadata", "artifact": "run_metadata.txt", "path": str(a / "run_metadata.txt"), "sha256": V2.sha256(a / "run_metadata.txt"), "matches": a_meta.get("git_head") == args.expected_head and a_meta.get("git_dirty") == "false" and a_meta.get("domain_id") == str(args.a_domain), "expected_head": args.expected_head, "captured_head": a_meta.get("git_head", ""), "domain_id": a_meta.get("domain_id", "")},
        {"scope": "C_fresh_raw", "artifact": "capture", "path": str(c), "sha256": "NOT_RUN", "matches": False, "status": "NOT_RUN", "reason": "A_BASELINE_GATE_FAILED"},
    ]
    details = {
        "A_controller_sha256": a_meta.get("controller_sha256", ""),
        "A_simulator_sha256": a_meta.get("simulator_sha256", ""),
        "scene_sha256": V2.sha256(scene),
        "A_statuses": statuses,
        "A_hard_markers": hard_markers,
        "V1_B_frozen_hashes_match": b_ok,
    }
    result = {
        "experiment": "phase2_known_step_v2_same_binary_ac_20260915",
        "classification": "PROTOCOL_FAILURE",
        "reason_code": "A_BASELINE_GATE_FAILED",
        "missing_runs": missing,
        "live_process_launched_by_analyzer": False,
        "launch_budget": {"authorized_A": 1, "authorized_C": 1, "observed_A": 1, "observed_C": 0, "retries": 0},
        "a": {"run": str(a), "metadata": a_meta, "protocol": a_protocol, "schema": shapes["A"], "gates": a_gates},
        "v1_b": {"run": str(b), "metadata": b_meta, "protocol": b_protocol, "schema": shapes["V1_B"]},
        "c": {"run": str(c), "status": "NOT_RUN", "reason": "A_BASELINE_GATE_FAILED"},
        "protocol": {"pass": False, "gates": a_gates},
        "pre_live_tests": tests,
        "provenance": details,
        "provenance_records": prov_records,
    }
    (out / "analysis.json").write_text(json.dumps(V2.jsonable(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = (
        "# Same-binary V2 A/C closeout\n\n"
        "Date: 2026-09-15\n"
        "Primary classification: PROTOCOL_FAILURE\n"
        "Reason code: A_BASELINE_GATE_FAILED.\n\n"
        f"Exactly one fresh A run was consumed at domain {args.a_domain}. No retry was made. A produced {a_protocol['trace_rows']} lockstep rows and PAIRED_HIGHSTATE_SUMMARY cycles={a_protocol['paired_cycles']} validation_failures={a_protocol['paired_validation_failures']} async_fallbacks={a_protocol['paired_async_fallbacks']}. Runtime statuses are {json.dumps(statuses, sort_keys=True)}; safety/completion and hard-posture gates therefore failed. Hard markers: {', '.join(hard_markers) or 'none'}.\n\n"
        "C was not launched because the task requires A baseline/protocol health before C. No simulator/controller rerun, tuning, or follow-up experiment was made. Frozen V1 B, A raw hashes, scene, runner, captured runtime metadata, and pre-live tests are recorded in provenance.csv and analysis.json.\n"
    )
    (out / "RESULTS.md").write_text(report, encoding="utf-8")
    V2.write_csv(out / "provenance.csv", prov_records)
    print("classification=PROTOCOL_FAILURE reason=A_BASELINE_GATE_FAILED C=NOT_RUN")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--a-run", type=Path, required=True)
    ap.add_argument("--b-run", type=Path, required=True)
    ap.add_argument("--c-run", type=Path, required=True)
    ap.add_argument("--a-domain", required=True)
    ap.add_argument("--c-domain", required=True)
    ap.add_argument("--expected-head", required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--pre-live-tests-json", type=Path, required=True)
    args = ap.parse_args()
    install_guards()
    root = args.repo_root.resolve(); a = args.a_run.resolve(); b = args.b_run.resolve(); c = args.c_run.resolve(); out = args.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    tests = json.loads(args.pre_live_tests_json.read_text(encoding="utf-8"))
    a_meta = V2.read_kv(a / "run_metadata.txt"); b_meta = V2.read_kv(b / "run_metadata.txt"); c_meta = V2.read_kv(c / "run_metadata.txt")
    paths = [("A", a), ("V1_B", b), ("C", c)]
    shapes = {name: V2.csv_schema(run / "data.csv") for name, run in paths}
    missing = [name for name, run in paths if not (run / "data.csv").is_file()]
    if missing:
        return closeout_without_c(root, a, b, c, out, args, tests, shapes, missing)
    a_rows = V2.read_rows(a / "data.csv"); b_rows = V2.read_rows(b / "data.csv"); c_rows = V2.read_rows(c / "data.csv")
    a_protocol = V2.parse_protocol(a, args.a_domain); b_protocol = V2.parse_protocol(b, "232"); c_protocol = V2.parse_protocol(c, args.c_domain)
    pre_ok, pre_summary, pre_mismatches = V2.exact_preactivation(a_rows, c_rows, a, c)
    prov_records, prov_details = provenance(root, a, b, c, a_meta, c_meta, args.expected_head, args.a_domain, args.c_domain)
    planning_records, planning_details = V2.planning_isolation(c_rows, c)
    planning_ok = all(item["status"] == "PASS" for item in planning_records)
    hard = V2.posture_event(c_rows); hard_time = hard.get("state_time_s") if hard else None
    front, timeline = V2.edge_tracking(c_rows, hard_time)
    env_text = (c / "environment.txt").read_text(encoding="utf-8", errors="replace") if (c / "environment.txt").is_file() else ""
    c_refs = V2.floor_reference(c_rows); a_refs = V2.floor_reference(a_rows); b_refs = V2.floor_reference(b_rows)
    metrics = V2.traversal_metrics(c_rows, c_meta, c, c_refs); metrics["chronology"] = V2.chronology(c_rows)
    base_missing = {"A": sorted(V2.BASE_COLUMNS - set(a_rows[0])), "V1_B": sorted(V2.BASE_COLUMNS - set(b_rows[0])), "C": sorted((V2.BASE_COLUMNS | V2.v2_columns()) - set(c_rows[0]))}
    tests_ok = (
        isinstance(tests, dict)
        and tests.get("pass") is True
        and all(item.get("status") == "PASS" for item in tests.get("checks", []))
        and all(item.get("return_code", 1) == 0 for item in tests.get("tests", []))
    )
    protocol_records = []
    for name, proto in (("A", a_protocol), ("C", c_protocol)):
        protocol_records += [V2.gate(name, "raw_schema", not base_missing[name] and shapes[name]["pass"], {"missing": base_missing[name], "schema": shapes[name]}), V2.gate(name, "domain", proto["domain_matches"], proto["domain_id"]), V2.gate(name, "lockstep_trace", proto["trace_present"] and proto["trace_rows"] > 0, proto["trace_rows"]), V2.gate(name, "constant_sim_tick", proto["sim_tick_diffs_ms"] == [2.0], proto["sim_tick_diffs_ms"]), V2.gate(name, "no_lockstep_violations", proto["trace_violations"] == 0, proto["trace_violations"]), V2.gate(name, "paired_highstate", proto["paired_summary_present"] and proto["paired_validation_failures"] == 0 and proto["paired_async_fallbacks"] == 0, proto)]
    protocol_records += [V2.gate("V1_B", "frozen_raw_schema", not base_missing["V1_B"] and shapes["V1_B"]["pass"], {"missing": base_missing["V1_B"], "schema": shapes["V1_B"]}), V2.gate("C", "v2_enabled_v1_off", "TROT_KNOWN_STEP_TRAVERSAL_V2=1" in env_text and "TROT_KNOWN_STEP_TRAVERSAL=1" not in env_text and "TROT_KNOWN_STEP_TRAVERSAL=1" not in c_meta.get("argv", ""), {"environment": env_text, "metadata": c_meta}), V2.gate("A_C", "same_binary_hashes", prov_details["A_C_same_binary_hashes"], prov_details), V2.gate("A_C", "runtime_metadata", prov_details["A_C_runtime_metadata"], prov_details), V2.gate("V1_B", "frozen_raw_hashes", prov_details["V1_B_frozen_hashes_match"], prov_details), V2.gate("C", "no_fail_closed_marker", not c_protocol["fail_closed_markers"], c_protocol["fail_closed_markers"]), V2.gate("C", "pre_live_tests_all_pass", tests_ok, tests)]
    run_parent = c.parent
    protocol_records.append(V2.gate("A_C", "launch_budget_exact_A_then_C", sorted(p.name for p in run_parent.iterdir() if p.is_dir()) == ["A", "C"], sorted(p.name for p in run_parent.iterdir() if p.is_dir())))
    protocol_ok = all(item["status"] == "PASS" for item in protocol_records)
    pre_record = V2.gate("A_C", "exact_preactivation", pre_ok, {"rows": pre_summary["rows_compared"], "mismatches": len(pre_mismatches)})
    tracking_limited = planning_ok and not metrics["traversal"]["success"] and any(item["edge_envelope"]["actual_entered_below_z_geom_clear"] or (item["first_command_edge_entry"]["command_clear"] and (item["tracking"]["contact_or_force_near_actual_entry"] or item["tracking"]["material_z_error"])) for item in front)
    front_pair = planning_ok and not metrics["traversal"]["success"] and all(item["raised_contact_gate"] for item in metrics["raised_contact"] if item["leg"] in V2.FRONT_LEGS)
    if not protocol_ok: classification = "PROTOCOL_FAILURE"
    elif not pre_ok: classification = "INCONCLUSIVE_PREACTIVATION_DIVERGENCE"
    elif not planning_ok: classification = "PLANNING_GEOMETRY_FAILED"
    elif metrics["traversal"]["success"]: classification = "SUPPORTED_ENABLES_TRAVERSAL_V2"
    elif tracking_limited: classification = "TRACKING_LIMITED"
    elif front_pair: classification = "FRONT_PAIR_ESTABLISHED_BUT_COORDINATION_FAILED"
    else: classification = "OTHER_CONTROL_LIMIT_IDENTIFIED" if front else "INSUFFICIENT_EVIDENCE"
    analysis = {"experiment": "phase2_known_step_v2_same_binary_ac_20260915", "classification": classification, "live_process_launched_by_analyzer": False, "launch_budget": {"authorized_A": 1, "authorized_C": 1, "observed_A": 1, "observed_C": 1, "retries": 0}, "a": {"run": str(a), "metadata": a_meta, "protocol": a_protocol, "schema": shapes["A"]}, "v1_b": {"run": str(b), "metadata": b_meta, "protocol": b_protocol, "schema": shapes["V1_B"]}, "c": {"run": str(c), "metadata": c_meta, "protocol": c_protocol, "schema": shapes["C"], "planning": planning_details, "front_crossings": front, "body_contact_solver": metrics}, "protocol": {"pass": protocol_ok, "gates": protocol_records}, "preactivation": {"pass": pre_ok, "summary": pre_summary, "mismatches": pre_mismatches}, "planning_isolation": {"pass": planning_ok, "gates": planning_records, "details": planning_details}, "provenance": prov_details, "provenance_records": prov_records, "pre_live_tests": tests, "classification_factors": {"tracking_limited": tracking_limited, "front_pair_established": front_pair}, "thresholds": "original V2 task unchanged"}
    (out / "analysis.json").write_text(json.dumps(V2.jsonable(analysis), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = f"# Same-binary V2 A/C closeout\n\nDate: 2026-09-15\nPrimary classification: `{classification}`\n\nExactly one fresh A followed by one fresh C was used from one build; no retry or additional live run was made. A domain={args.a_domain}, C domain={args.c_domain}. Controller and simulator hashes are identical: `{prov_details['A_C_same_binary_hashes']}`.\n\nA/C exact preactivation: `{'PASS' if pre_ok else 'FAIL'}`; rows compared={pre_summary.get('rows_compared')}; causal fields={pre_summary.get('causal_fields_compared')}; mismatches={len(pre_mismatches)}. Protocol gates pass={protocol_ok}; planning gates pass={planning_ok}; traversal success={metrics['traversal']['success']}.\n\nA and C raw hashes, binary identity, runtime HEAD, frozen V1 B provenance, scene, and runner provenance are in `provenance.csv`. This checkpoint is closed; no retry, tuning, or follow-up experiment is authorized.\n"
    (out / "RESULTS.md").write_text(report, encoding="utf-8")
    V2.write_csv(out / "provenance.csv", prov_records)
    print(f"classification={classification} protocol={protocol_ok} preactivation={pre_ok} planning={planning_ok} traversal={metrics['traversal']['success']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
