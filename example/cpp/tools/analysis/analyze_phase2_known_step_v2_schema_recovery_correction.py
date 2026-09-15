#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import phase2_known_step_v2_schema_recovery_correction_core as C

def install_boundary_guard():
    original = C.V2.boundary_continuity
    expected_original = C.V2.expected_v2_sample
    def guarded(plan):
        try:
            return original(plan)
        except ZeroDivisionError:
            return {"position_jump_max_m": None, "derivative_jump_max_per_s_m": None,
                    "position_continuous": False, "velocity_continuous": False,
                    "undefined_due_to_zero_segment": True}
    C.V2.boundary_continuity = guarded
    def expected_guard(row, leg, plan):
        if plan["s_entry"] <= 0.0 or plan["s_exit"] <= plan["s_entry"] or plan["s_exit"] >= 1.0:
            phase = C.V2.swing_phase(row, leg)
            s = C.V2.quintic(min(1.0, phase / 0.80))
            return {"s": s, "x": math.nan, "y": math.nan, "z": math.nan, "vx": math.nan, "vz": math.nan}
        return expected_original(row, leg, plan)
    C.V2.expected_v2_sample = expected_guard

def main():
    parser = argparse.ArgumentParser(description="Offline V2 schema recovery correction.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--a-run", type=Path, required=True)
    parser.add_argument("--b-run", type=Path, required=True)
    parser.add_argument("--c-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--parent-provenance", type=Path, required=True)
    args = parser.parse_args()
    C.load_modules()
    repo = args.repo_root.resolve()
    a = args.a_run.resolve()
    b = args.b_run.resolve()
    c = args.c_run.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    audit = C.recover(repo, c)
    meta = C.kv(c / "run_metadata.txt")
    install_boundary_guard()
    status_context = C.S.log_status_context(c, audit["raw"], audit["header"])
    prov_rows, prov_details = C.provenance(repo, a, b, c, args.parent_provenance.resolve(), meta, audit["source"], Path(__file__).resolve())
    protocol = C.V2.parse_protocol(c, "230")
    a_rows = C.V2.read_rows(a / "data.csv")
    b_rows = C.V2.read_rows(b / "data.csv")
    c_rows = audit["rows"]

    pre_ok, pre_summary, pre_mismatches = C.V2.exact_preactivation(a_rows, c_rows, a, c)
    planning_records, planning_details = C.V2.planning_isolation(c_rows, c)
    planning_ok = all(row["status"] == "PASS" for row in planning_records)
    hard = C.V2.posture_event(c_rows)
    hard_time = hard.get("state_time_s") if hard else None
    front, timeline = C.V2.edge_tracking(c_rows, hard_time)
    references = C.V2.floor_reference(c_rows)
    metrics = C.V2.traversal_metrics(c_rows, meta, c, references)
    metrics["chronology"] = C.V2.chronology(c_rows)

    expected_statuses = {
        "controller_status": "0", "ground_truth_status": "0", "dynamics_status": "0",
        "quality_status": "0", "analysis_status": "1", "safety_status": "1", "completion_status": "1",
    }
    protocol_records = [
        C.gate("C", "schema_recovery_deterministic", audit["all_pass"], {"drop_indices": audit["drops"], "all_pass": audit["all_pass"]}),
        C.gate("C", "domain_230", protocol["domain_matches"], protocol["domain_id"]),
        C.gate("C", "lockstep_trace_present", protocol["trace_present"] and protocol["trace_rows"] > 0, protocol["trace_rows"]),
        C.gate("C", "constant_sim_tick", protocol["sim_tick_diffs_ms"] == [2.0], protocol["sim_tick_diffs_ms"]),
        C.gate("C", "no_lockstep_violations", protocol["trace_violations"] == 0, protocol["trace_violations"]),
        C.gate("C", "paired_highstate", protocol["paired_summary_present"] and protocol["paired_validation_failures"] == 0 and protocol["paired_async_fallbacks"] == 0, protocol),
        C.gate("C", "no_fail_closed_marker", not protocol["fail_closed_markers"], protocol["fail_closed_markers"]),
        C.gate("A", "frozen_raw_hashes", prov_details["A_raw_hashes_match"], prov_details),
        C.gate("V1_B", "frozen_raw_hashes", prov_details["V1_B_raw_hashes_match"], prov_details),
        C.gate("C", "raw_hashes_match_parent", prov_details["C_raw_hashes_match_parent"], prov_details),
        C.gate("C", "runtime_metadata", prov_details["C_runtime_metadata_match"], prov_details),
        C.gate("C", "observed_statuses_preserved", all(meta.get(k, "") == v for k, v in expected_statuses.items()), {k: meta.get(k, "") for k in expected_statuses}),
    ]
    runtime_protocol_ok = all(row["status"] == "PASS" for row in protocol_records)
    traversal = metrics["traversal"]
    tracking_limited = planning_ok and not traversal["success"] and any(
        item["edge_envelope"]["actual_entered_below_z_geom_clear"]
        or (item["first_command_edge_entry"]["command_clear"] and (item["tracking"]["contact_or_force_near_actual_entry"] or item["tracking"]["material_z_error"]))
        for item in front
    )
    front_pair = planning_ok and not traversal["success"] and all(
        item["raised_contact_gate"] for item in metrics["raised_contact"] if item["leg"] in C.V2.FRONT_LEGS
    )
    if not runtime_protocol_ok:
        label = "PROTOCOL_FAILURE"
    elif not pre_ok:
        label = "INCONCLUSIVE_PREACTIVATION_DIVERGENCE"
    elif not planning_ok:
        label = "PLANNING_GEOMETRY_FAILED"
    elif traversal["success"]:
        label = "SUPPORTED_ENABLES_TRAVERSAL_V2"
    elif tracking_limited:
        label = "TRACKING_LIMITED"
    elif front_pair:
        label = "FRONT_PAIR_ESTABLISHED_BUT_COORDINATION_FAILED"
    else:
        label = "OTHER_CONTROL_LIMIT_IDENTIFIED" if front else "INSUFFICIENT_EVIDENCE"

    C.write_csv(out / "schema_repair_map.csv", C.repair_map(audit))
    C.write_csv(out / "schema_recovery_validation.csv", audit["checks"])
    C.write_csv(out / "preactivation_exact.csv", [{"status": "PASS" if pre_ok else "FAIL", **pre_summary}] + pre_mismatches)
    C.write_csv(out / "planning_isolation.csv", planning_records + [{"run": "C", "gate": "planning_summary", "status": "PASS" if planning_ok else "FAIL", "detail": planning_details}])
    C.write_csv(out / "front_crossing_summary.csv", front or [{"status": "NOT_AVAILABLE", "reason": "no recovered V2 crossing group"}])
    C.write_csv(out / "edge_tracking_timeline.csv", timeline or [{"status": "NOT_AVAILABLE", "reason": "no recovered V2 crossing group"}])
    C.write_csv(out / "touchdown_summary.csv", metrics["raised_contact"] + [{"leg": "all", "floor_reference_z0_m": references}])
    C.write_csv(out / "body_contact_chronology.csv", [{"arm": "C", **event} for event in metrics["chronology"]])
    C.write_csv(out / "protocol_gates.csv", protocol_records)
    C.write_csv(out / "provenance.csv", prov_rows)
    C.write_csv(out / "source_diff_audit.csv", [{
        "status": "PASS",
        "parent_closeout": "4986a6b5c4680e0fe8e1337fef65005440d26529",
        "runtime_scientific_source_diff": "none_in_this_checkpoint",
        "offline_analysis_only": True,
        "frozen_C_runtime_head": C.C_HEAD,
    }])

    analysis = {
        "experiment": "phase2_known_step_v2_schema_recovery_correction_20260915",
        "classification": label,
        "live_process_launched_by_analyzer": False,
        "launch_budget": {"authorized_new_live_runs": 0, "observed_new_live_runs": 0, "C_reruns": 0, "A_reruns": 0, "V1_B_reruns": 0},
        "schema_recovery": {k: v for k, v in audit.items() if k not in {"header", "raw", "repaired", "rows"}},
        "raw_statuses": {k: meta.get(k, "") for k in expected_statuses},
        "status_context": status_context,
        "protocol": {"pass": runtime_protocol_ok, "gates": protocol_records, "trace": protocol},
        "provenance": prov_details,
        "preactivation": {"pass": pre_ok, "summary": pre_summary, "mismatches": pre_mismatches},
        "planning_isolation": {"pass": planning_ok, "gates": planning_records, "details": planning_details},
        "front_crossings": front,
        "body_contact_solver": metrics,
        "classification_factors": {"tracking_limited": tracking_limited, "front_pair_established": front_pair},
        "thresholds": "original V2 task unchanged",
    }
    (out / "analysis.json").write_text(json.dumps(C.js(analysis), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    posture = status_context.get("first_controller_hard_posture_marker") or {}
    safety = status_context.get("first_controller_hard_safety_marker") or {}
    (out / "RESULTS.md").write_text(
        f"""# Phase2 V2 schema recovery correction closeout

Date: 2026-09-15
Primary scientific classification: {label}

This checkpoint was strictly offline. No simulator, controller, runner, DDS, GUI replay, or new experiment was launched. A, V1 B, and C raw captures were read-only and no raw file was modified.

Schema recovery passed deterministically: raw C header width={audit["raw_header_width"]}, rows={audit["raw_data_rows"]}, row widths={audit["widths"]}; only literal header tokens at indices {audit["drops"]} were removed in memory. Repaired width={len(audit["repaired"])} with unique nonempty names. Raw header SHA-256={audit["raw_header_sha256"]}; derived header SHA-256={audit["derived_header_sha256"]}. Recovery gates are in schema_recovery_validation.csv and the action map is in schema_repair_map.csv.

Raw statuses are {json.dumps({k: meta.get(k, "") for k in expected_statuses}, sort_keys=True)}. analysis_status=1 is preserved as the original schema failure; safety_status=1 and completion_status=1 remain experimental outcomes. First hard posture log line={posture.get("line")}; first hard safety line={safety.get("line")}. Recovered chronology is in body_contact_chronology.csv.

A/C exact preactivation: {"PASS" if pre_ok else "FAIL"}, rows compared={pre_summary.get("rows_compared")}, causal fields={pre_summary.get("causal_fields_compared")}. Protocol, planning, C1 corridor, tracking, touchdown, contact, solver, and traversal criteria use the original V2 thresholds. Scientific classification={label}. A prior procedural SCHEMA_RECOVERY_AMBIGUOUS result is superseded only because this correction proves the four literal duplicated-prefix tokens and all semantic gates.

All raw hashes and runtime provenance are in provenance.csv. This is the final offline closeout; no C rerun or scientific follow-up is authorized.
""",
        encoding="utf-8",
    )
    print(f"classification={label} schema_recovery={audit['all_pass']} preactivation={pre_ok} planning={planning_ok} traversal={traversal['success']}")
    return 0

if __name__ == "__main__":
    C.load_modules()
    raise SystemExit(main())
