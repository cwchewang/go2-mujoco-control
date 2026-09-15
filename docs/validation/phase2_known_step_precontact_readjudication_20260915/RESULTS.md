# Phase2 known-step pre-contact readjudication

Date: 2026-09-15
Classification: `PRECONTACT_BASELINE_HEALTHY_CONTACT_CONFOUNDED`

## Evidence boundary

This is a pure offline readjudication of the frozen A capture at `/home/che/dev/go2-workspace/phase2-known-step-wallclock-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`. No simulator, controller, B arm, runner, or live process was launched. Raw capture bytes were not modified. Runtime source, terrain adapter, scene, gait, WBC/MPC/ID, and thresholds were not modified.

Frozen runtime provenance: `git_head=df5d7663adc9e96d153107e071d7b49676bcdad6`; raw hashes match the prior wall-clock-repair provenance: `True`; runtime metadata/source hashes match: `True`.

## Corrected activity predicate and clean mask

The old analyzer used `motion_stage == 2 AND velocity_command_active` and selected 0 rows. This checkpoint uses `motion_stage == 2` and selects 1327 rows; `velocity_command_active` is not an activity gate because this full2 capture has no runtime velocity command.

Clean pre-contact is `motion_stage == 2`, `world_base_x_m <= 0.40 m`, and every actual foot-center x `< 0.75 m`. It contains 870 rows with state-time span 1.7379999999999995 s.

## Clean pre-contact health

- roll: signed min/max/p95 = -0.034321602/0.029665351/0.022157871899999994 rad; absolute max/p95 = 0.034321602/0.029366392349999992 rad
- pitch: signed min/max/p95 = -0.086465485/0.086687908/0.07812565749999997 rad; absolute max/p95 = 0.086687908/0.08328978395 rad
- WBC valid rows=870; SRBD success=1.0; ID success=1.0; equality residual p95=6.427199999999998e-06
- adaptation enabled samples=0; adaptation-active samples=0; protocol/paired checks=True

Gate disposition:

- `PASS` required_columns: missing=none
- `PASS` clean_row_count: rows=870 required>=250
- `PASS` clean_state_time_span: span_s=1.7379999999999995 required>=0.50
- `PASS` known_step_adaptation_disabled: enabled=0 active=0
- `PASS` roll_abs_max: max_abs_rad=0.034321602
- `PASS` pitch_abs_max: max_abs_rad=0.086687908
- `PASS` clean_no_22_degree_crossing: crossing_rows=0
- `PASS` wbc_solver_valid_rows: valid_rows=870 required>=100
- `PASS` wbc_solver_success: srbd=1.0 id=1.0
- `PASS` wbc_equality_residual_p95: p95=6.427199999999998e-06 required<=1e-3
- `PASS` lockstep_and_paired_highstate: {"fail_closed_markers": [], "paired_async_fallbacks": 0, "paired_cycles": 4879, "paired_summary_present": true, "paired_validation_failures": 0, "sim_tick_diffs_ms": [2.0], "trace_present": true, "trace_rows": 4880, "trace_violations": 0}
- `PASS` runtime_and_raw_provenance: runtime_head=df5d7663adc9e96d153107e071d7b49676bcdad6 raw_hashes_match=True source_hashes_match=True

## Contact-risk chronology

First `plausible_contact_risk` (not literal geom-pair contact): t=14.616 s, leg=fr, foot=(0.782261435, 0.040634785) m, base_x=0.613635701 m; coincident legs=['fr']

First raw 22-degree hard-posture crossing: t=14.956 s, roll=-0.033537924 rad, pitch=0.386607796 rad, base_x=0.607232999 m; fr=(0.764411865, 0.024527419), fl=(0.777681812, 0.025341173), rr=(0.465088789, 0.0349651), rl=(0.437802035, 0.024180513)

Ordering: `first_plausible_contact_risk_at_or_before_first_hard_posture_crossing`; hard-posture time minus risk time = `0.33999999999999986` s.

## Stop disposition

This result does not authorize B or any follow-up runtime experiment. It is a readjudication of the old base-x proxy and the activity predicate only; any favorable result may be used by the planner/reviewer to prepare a separately preregistered checkpoint.
