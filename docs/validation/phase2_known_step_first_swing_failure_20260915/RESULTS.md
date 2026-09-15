# Phase2 first-swing failure attribution closeout

Date: 2026-09-15
Primary classification: `MIXED_CLEARANCE_TRACKING_PLACEMENT`

## Scope and immutable evidence

This is a pure offline audit of the existing A and B raw captures. No simulator, controller, replay, GUI, runner, or live process was launched. No raw file, runtime source, scene, gait, WBC/MPC/ID, threshold, or parameter was modified. B raw provenance is checked against parent closeout `c858955d17ec2395ce98aaff1fe94d2a63401182`.

A raw root: `/home/che/dev/go2-workspace/phase2-known-step-wallclock-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`
B raw root: `/home/che/dev/go2-workspace/phase2-known-step-b-only-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_b_only_20260915/B`
B runtime HEAD at capture: `c44314b451ea77d460263052b7f274347881137c`; launch count=0 in this audit.

## Source-faithful reconstruction

The reconstruction uses the B runtime source at `c44314b451ea77d460263052b7f274347881137c`: diagonal offsets `[0, 0.5, 0.5, 0]`, `LegSwingPhase`, `SwingWorldTarget`, quintic x/y interpolation over `swing_phase/0.80`, and squared-sine z lift over `swing_phase/0.85`. Each row's logged final target is used as that row's runtime swing endpoint because the source recomputes the touchdown plan while the leg is in swing; it is not treated as the instantaneous command. Activity is selected only from `known_step_*_adaptation_active`; `velocity_command_active` is not used. The CSV has no actual world-foot y channel or swing-start y, so full 3D command/actual error is unavailable; x/z error is exact for the reconstructed command and logged actual x/z.

Endpoint self-check: maximum reconstructed command-minus-final-target error is `0.0` m across adapted front swings.

## Frozen geometry diagnostics

`x_edge=0.8` m, `x_edge_entry=0.777` m, `x_center_beyond=0.8230000000000001` m, `z_center_clear=0.07300000000000001` m. The previous continuity proxy remains `x>=0.778 m AND z<=0.072 m`; it is not literal geom-pair contact truth.

B first plausible risk: `14.616` s, leg=fr, foot=(0.780658512, 0.048394126) m. B first 22-degree crossing: `15.222` s, roll=0.051400684 rad, pitch=0.386372328 rad. Risk-to-hard delta: `0.6059999999999999` s.

Pre-contact floor references A/B are compatible: `{'A_z0_m': {'fr': 0.02349693, 'fl': 0.023444499, 'rr': 0.023452305, 'rl': 0.023179432}, 'B_z0_m': {'fr': 0.02349693, 'fl': 0.023444499, 'rr': 0.023452305, 'rl': 0.023179432}, 'B_minus_A_m': {'fr': 0.0, 'fl': 0.0, 'rr': 0.0, 'rl': 0.0}, 'compatible': True}`.

## Adapted front-leg swings

- `B_FR_1`: start=14.554 s, final x=0.82548555 m (CENTER_FULLY_BEYOND_EDGE), margin vs 0.823=0.0024855499999999475 m; command edge=(14.612, z=0.12949227198735605), actual edge=(14.616, z=0.048394126), raised-contact-before-hard=False
- `B_FR_2`: start=15.154 s, final x=0.871502674 m (CENTER_FULLY_BEYOND_EDGE), margin vs 0.823=0.04850267399999997 m; command edge=(15.154, z=0.06801218163449962), actual edge=(15.212, z=0.044086009), raised-contact-before-hard=False
- `B_FL_1`: start=14.854 s, final x=0.854343243 m (CENTER_FULLY_BEYOND_EDGE), margin vs 0.823=0.03134324299999991 m; command edge=(14.878, z=0.05652277435531372), actual edge=(14.866, z=0.025903312), raised-contact-before-hard=False

The first FR swing has a geometrically clear reconstructed command at edge-envelope entry but its actual foot is materially behind/below command with force/contact evidence. FL and the later FR swing enter the frozen edge envelope below the conservative center-height clearance in the intended command. All reported final touchdown centers are classified against the frozen x thresholds; no threshold was changed.

## A/B body and contact chronology

A risk=14.616 s; A hard posture=14.956 s; A risk-to-hard delta=0.33999999999999986 s. B max base x=0.70987936 m at t=15.408 s. B solver summary: `{"all_id_ok": false, "all_srbd_ok": true, "id_success_fraction": 0.9998004788507582, "residual": {"absolute_max": 0.000295598, "absolute_p95": 3.637464999999959e-05, "count": 5012, "max": 0.000295598, "min": 0.0, "p95": 3.637464999999959e-05, "rms": 1.8495182299633835e-05}, "srbd_success_fraction": 1.0, "valid_rows": 5012}`. Full event chronology is machine-readable in `body_contact_chronology.csv`; per-sample command/actual and joint/torque timeline is in `edge_clearance_timeline.csv`.

## Contributing factors

[
  "planned_edge_clearance_deficit:B_FR_2,B_FL_1",
  "tracking_or_contact_blocked:B_FR_1"
]

## Provenance and stop

Raw hash audit: `True`. A/B metadata and source-faithful runtime source commit checks: `True`. The closeout contains only offline analyzer/results changes. After this closeout, do not run or prepare a live variant in this checkpoint.
