# Phase2 V2 schema recovery correction closeout

Date: 2026-09-15
Primary scientific classification: INCONCLUSIVE_PREACTIVATION_DIVERGENCE

This checkpoint was strictly offline. No simulator, controller, runner, DDS, GUI replay, or new experiment was launched. A, V1 B, and C raw captures were read-only and no raw file was modified.

Schema recovery passed deterministically: raw C header width=780, rows=5005, row widths={776: 5005}; only literal header tokens at indices [211, 264, 317, 370] were removed in memory. Repaired width=776 with unique nonempty names. Raw header SHA-256=7bd4f1116739a3a65d3a0488d5fbf8a98c232451739f1ffc2016074d5c375ca9; derived header SHA-256=b39e0b7c2357623c2555ab3576fda204b779bf4e04cee3343e241997910cf517. Recovery gates are in schema_recovery_validation.csv and the action map is in schema_repair_map.csv.

Raw statuses are {"analysis_status": "1", "completion_status": "1", "controller_status": "0", "dynamics_status": "0", "ground_truth_status": "0", "quality_status": "0", "safety_status": "1"}. analysis_status=1 is preserved as the original schema failure; safety_status=1 and completion_status=1 remain experimental outcomes. First hard posture log line=57; first hard safety line=58. Recovered chronology is in body_contact_chronology.csv.

A/C exact preactivation: FAIL, rows compared=3127, causal fields=629. Protocol, planning, C1 corridor, tracking, touchdown, contact, solver, and traversal criteria use the original V2 thresholds. Scientific classification=INCONCLUSIVE_PREACTIVATION_DIVERGENCE. A prior procedural SCHEMA_RECOVERY_AMBIGUOUS result is superseded only because this correction proves the four literal duplicated-prefix tokens and all semantic gates.

All raw hashes and runtime provenance are in provenance.csv. This is the final offline closeout; no C rerun or scientific follow-up is authorized.
