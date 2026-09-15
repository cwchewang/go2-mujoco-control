# Phase2 known-step B-only closeout

Date: 2026-09-15
Classification: `ADAPTATION_FAILED`

## Scope and provenance

Exactly one B-only live launch was authorized and performed with DDS domain 232 using `example/cpp/scripts/run_phase2_known_step_5cm_b_only.sh`. A was not rerun. The immutable A capture remained at `/home/che/dev/go2-workspace/phase2-known-step-wallclock-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`; B capture is `/home/che/dev/go2-workspace/phase2-known-step-b-only-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_b_only_20260915/B`. No retry, parameter change, extra experiment, or raw-file edit was performed.

Accepted A runtime HEAD: `df5d7663adc9e96d153107e071d7b49676bcdad6`. B runtime HEAD: `c44314b451ea77d460263052b7f274347881137c`. A frozen raw hashes match readjudication provenance: `True`. B runtime/source/binary/scene provenance gate: `True`. Binary disposition: accepted controller `80c05a7750ef6782ff24955f7952dd391afce4c5406a15182bc712b36ef49ab3` -> observed `6d9931fce67ec3092fb8867828ae6447a5f44f89c3dd08b7c4104efa1134ce2e`; accepted simulator `b9f9e44a40d9b08cd6dce6632038819fab5ec0099e1628078c07185d5a808c9d` -> observed `a24721b84bea2854df36428190e38d163a780e9fead37258bd590e974117e280`; rebuild allowed/recorded=`True`.

Pre-live tests: {"analyzer_syntax_and_help": "PASS", "binary_scene_provenance_audit": "PASS", "controller_ctest": "31/31 PASS", "frozen_A_raw_hash_audit": "12/12 PASS", "known_step_terrain_adapter": "PASS", "live_launch": "B only once, DDS domain 232", "lockstep_motion_clock_integration": "PASS", "prelive_analyzer_head": "c44314b451ea77d460263052b7f274347881137c", "simulator_ctest": "2/2 PASS", "simulator_test_lockstep": "PASS", "source_diff_allowlist": "PASS"}

Clean B pre-contact mask: {'predicate': 'motion_stage == 2 AND world_base_x_m <= 0.40 AND every actual foot-center x < 0.75', 'base_x_limit_m': 0.4, 'actual_foot_x_limit_m': 0.75, 'rows': 870, 'state_time_start_s': 12.302, 'state_time_end_s': 14.04, 'state_time_span_s': 1.7379999999999995}. B floor-contact references z0={'fr': 0.02349693, 'fl': 0.023444499, 'rr': 0.023452305, 'rl': 0.023179432}; these match the independently derived A references.

## Exact pre-activation comparison

Result: `PASS`. Compared 3277 rows and 629 causal fields from common deterministic handoff state tick 8.0 through the final row before first B adaptation. Allowed metadata-only differences were `['known_step_edge_x_m', 'known_step_feature_enabled', 'known_step_half_width_y_m', 'known_step_height_m']`; ignored noncausal diagnostics were `['motion_clock_wall_dt_s', 'wbc_shadow_elapsed_us']`. First adaptation: time=14.554 s, base_x=0.584462284 m, legs=['fr'].

The comparator and active-locomotion isolation gate were corrected after capture as analysis-only repairs. Raw A/B captures were not edited and B was not rerun.

## B isolation and traversal

First plausible contact-risk: time=14.616 s, leg=fr, foot=(0.780658512, 0.048394126) m, base_x=0.614580451 m. This is a geometry risk proxy, not a literal geom-pair contact claim.

First 22-degree hard-posture crossing: time=15.222 s, roll=0.051400684 rad, pitch=0.386372328 rad, base_x=0.686256249 m, feet={"fl": {"x_m": 0.861586399, "z_m": 0.073836057}, "fr": {"x_m": 0.788243693, "z_m": 0.043537344}, "rl": {"x_m": 0.536611023, "z_m": 0.05038779}, "rr": {"x_m": 0.504233253, "z_m": 0.022873117}}. Temporal ordering: risk precedes hard posture by 0.606 s.

Raised-platform qualified contact time: fr=0 s, fl=0 s, rr=0 s, rl=0 s.

Traversal metrics: max_base_x=0.70987936 m; x=0.80 time=not observed s; x=1.45 time=not observed s; hold=False; solver_p95=4.502600000000001e-06; max_abs_roll=0.903528988; max_abs_pitch=0.398935854.

Gate record:

- `PASS` A raw_schema: missing=none
- `PASS` B raw_schema: missing=none
- `PASS` B clean_precontact_mask: rows=870 span_s=1.7379999999999995
- `PASS` A_B floor_reference_compatible: a={'fr': 0.02349693, 'fl': 0.023444499, 'rr': 0.023452305, 'rl': 0.023179432} b={'fr': 0.02349693, 'fl': 0.023444499, 'rr': 0.023452305, 'rl': 0.023179432} diffs={'fr': 0.0, 'fl': 0.0, 'rr': 0.0, 'rl': 0.0}
- `PASS` A frozen_raw_hashes: matches=True
- `PASS` A accepted_runtime_provenance: head=df5d7663adc9e96d153107e071d7b49676bcdad6
- `PASS` B domain_232: domain=232
- `PASS` B lockstep_trace_present: rows=5013
- `PASS` B constant_sim_tick: diffs=[2.0]
- `PASS` B no_protocol_violations: violations=0
- `PASS` B paired_highstate: cycles=5012 failures=0 fallbacks=0
- `PASS` B no_fail_closed_marker: markers=[]
- `PASS` B runtime_binary_scene_provenance: head=c44314b451ea77d460263052b7f274347881137c controller=6d9931fce67ec3092fb8867828ae6447a5f44f89c3dd08b7c4104efa1134ce2e simulator=a24721b84bea2854df36428190e38d163a780e9fead37258bd590e974117e280 scene=8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc
- `PASS` A_B exact_preactivation: rows=3277 mismatches=0
- `PASS` B feature_enabled: capture_values=['0', '1'] active_values=['1'] active_rows=1460
- `PASS` B d4_enabled: field=diag_bounded_stance_dq_enabled values=[0.0]
- `PASS` B d4_gate_active: field=diag_bounded_stance_dq_gate_active values=[0.0]
- `PASS` B d90_enabled: field=diag_four_thigh_d90_enabled values=[0.0]
- `PASS` B d90_gate_active: field=diag_four_thigh_d90_gate_active values=[0.0]
- `PASS` B pd_pulse_off: PD_PULSE absent from captured environment/argv
- `PASS` B adaptation_scope: active_samples=1585 errors=none
- `PASS` B nominal_xy_unchanged: max_error_m=0.0
- `PASS` B final_z_formula: max_error_m=1.3877787807814457e-17
- `PASS` B floor_to_plateau_rise: values=[0.05]
- `PASS` B floor_to_plateau_lift: values=[0.08]
- `PASS` B plateau_to_plateau_no_accumulation: errors=none

## Stop disposition

The frozen classification is limited to this B-only checkpoint. After this closeout, do not run another terrain experiment, rerun A/B, tune, or modify runtime source.
