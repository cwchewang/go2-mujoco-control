# Phase2 V2 schema readjudication closeout

Date: 2026-09-15
Primary classification: SCHEMA_RECOVERY_AMBIGUOUS

This checkpoint was strictly offline. No simulator, controller, runner, DDS, GUI replay, or new experiment was launched; A and V1 B were not rerun and raw C data.csv was not modified.

## Raw and source finding

C has 780 header tokens and 5005 data rows, with raw row widths {776: 5005}. The four extra tokens at raw indices [211, 264, 317, 370] are literal known_step_v2_, not empty tokens. Runtime source \\wsl.localhost\Ubuntu-22.04\home\che\dev\go2-workspace\phase2-known-step-edge-aware-v2-protocol-repair-20260915\example\cpp\trot\trot_experiment_diagnostics.cpp contains the same _s_exit,known_step_v2_ header construction, while LogSample emits s_exit followed by command x/z/vx/vz and actual x/z in one sequence.

The candidate deletion is width-preserving and unique (candidate_mapping_unique=True), but the task's literal empty-token transition gate is false (literal_task_shape_gate=False). Therefore the derived candidate was used only for schema/status audit; frozen scientific V2 analysis was not run.

## Status preservation

run_metadata.txt statuses are {"analysis_status": "1", "completion_status": "1", "controller_status": "0", "dynamics_status": "0", "ground_truth_status": "0", "quality_status": "0", "safety_status": "1"}. The first controller marker is line 57, Trot hard posture limit, immediately followed by line 58, Trot hard safety limit reached; stopping. completion_status=1 is preserved: the log has no normal completion marker and records only the hard-safety stop before the requested run completed.

## Recovery disposition

Raw header SHA-256: 7bd4f1116739a3a65d3a0488d5fbf8a98c232451739f1ffc2016074d5c375ca9. Candidate derived-header SHA-256: b39e0b7c2357623c2555ab3576fda204b779bf4e04cee3343e241997910cf517. Recovery validation checks: [{"detail": ["0", "1"], "gate": "v2_boolean_like_values", "status": "PASS"}, {"detail": ["1"], "gate": "v2_enabled_during_active_locomotion", "status": "PASS"}, {"detail": {"codes": [0, 1, 2], "failures": []}, "gate": "planning_failure_code_enum", "status": "PASS"}, {"detail": {"failures": [], "reasons": ["invalid_edge_ordering", "none", "not_crossing"]}, "gate": "planning_failure_reason_enum", "status": "PASS"}, {"detail": {"errors": [], "populated": 4206, "target": 0.777, "unique": [0.777]}, "gate": "x_entry_m_source_invariant", "status": "PASS"}, {"detail": {"errors": [], "populated": 4206, "target": 0.823, "unique": [0.823]}, "gate": "x_exit_m_source_invariant", "status": "PASS"}, {"detail": {"errors": [], "populated": 20020, "target": 0.85, "unique": [0.85]}, "gate": "x_land_min_m_source_invariant", "status": "PASS"}, {"detail": ["0", "1"], "gate": "scheduled_stance_swing_boolean_like", "status": "PASS"}, {"detail": {"failures": [], "fields": 24, "pass": true, "populated_values": 120120}, "gate": "finite_command_actual_values", "status": "PASS"}, {"detail": {"blocks": [{"end": 218, "leg": "fr", "next": "known_step_fl_scheduled_stance", "start": 184}, {"end": 270, "leg": "fl", "next": "known_step_rr_scheduled_stance", "start": 236}, {"end": 322, "leg": "rr", "next": "known_step_rl_scheduled_stance", "start": 288}, {"end": 374, "leg": "rl", "next": "diag_bounded_stance_dq_FR_hip_stance_selector", "start": 340}], "failures": [], "following_d4_field": "diag_bounded_stance_dq_FR_hip_stance_selector"}, "gate": "v2_leg_blocks_no_column_drift", "status": "PASS"}]. No scientific classification was inferred after the literal gate failure. Logger source fix: PASS: removed one duplicated header prefix in WriteCsvHeader loop; source sha after=7b5c575f8dbad7effb3478ad26ff828d20ea9b3a16ff1b79d9dde595c126140a. No-live regression test: PASS: python test_trot_csv_schema.py; no runtime process.

Raw-hash/provenance details are machine-readable in provenance.csv; the required scientific tables are present with NOT_RUN placeholders because recovery was ambiguous. Stop after this pushed closeout; no C rerun or scientific reinterpretation is authorized.
