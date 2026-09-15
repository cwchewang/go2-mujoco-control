# Phase2 offline checkpoint: first-swing failure attribution after 5 cm known-step ADAPTATION_FAILED

Date: 2026-09-15
Prepared branch: `research/phase2-known-step-first-swing-failure-audit-20260915`
Parent closeout: `c858955d17ec2395ce98aaff1fe94d2a63401182`

Read `docs/research/PHASE1_AGENT_CONTRACT.md`, the original 5 cm task, the pre-contact readjudication task, and the B-only task before doing anything. This checkpoint is **offline only** and does not authorize a simulator/controller launch.

## 1. Question

Why did the isolated known-step intervention delay failure but not traverse the 5 cm step?

The B-only checkpoint established all of the following:

- exact A/B equality through the row immediately before first terrain adaptation;
- first B adaptation at state time 14.554 s, FR only;
- adaptation math/isolation passed: rise=0.05 m, effective lift=0.08 m, nominal x/y unchanged;
- first plausible contact-risk at 14.616 s;
- first 22-degree hard-posture crossing at 15.222 s, 0.606 s after risk;
- max base x=0.70987936 m;
- no leg achieved the preregistered raised-platform contact criterion;
- at hard-posture: FL actual foot was approximately x=0.861586399, z=0.073836057 m while FR was x=0.788243693, z=0.043537344 m;
- WBC/SRBD/ID remained numerically healthy through the analyzed window.

This audit must distinguish whether the first failed front-leg transition was primarily caused by:

1. **planned trajectory geometric clearance deficit**;
2. **tracking/contact blockage despite a geometrically safe planned swing**;
3. **touchdown placement too shallow relative to the vertical edge**;
4. a combination of the above;
5. insufficient evidence.

Do not tune anything and do not propose a live parameter value before the evidence is computed.

## 2. Immutable inputs

Use only the already captured raw data:

A:
`/home/che/dev/go2-workspace/phase2-known-step-wallclock-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`

B:
`/home/che/dev/go2-workspace/phase2-known-step-b-only-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_b_only_20260915/B`

The B capture must match the provenance recorded in `docs/validation/phase2_known_step_5cm_b_only_20260915/` at parent closeout `c858955...`.

No raw file may be edited. Do not rerun A or B. Do not start MuJoCo, the controller, GUI replay, or any live process.

## 3. Frozen geometry

Use the actual MJCF/controller geometry, not an invented margin:

- step leading edge: `x_edge = 0.800 m`;
- step top: `z_top = 0.050 m`;
- Go2 foot collision sphere radius: `r_foot = 0.022 m`;
- default collision margin: `0.001 m`.

Define for this audit:

- horizontal edge-envelope entry: `x_edge_entry = 0.800 - 0.022 - 0.001 = 0.777 m`;
- full-center placement beyond the vertical face: `x_center_beyond = 0.800 + 0.022 + 0.001 = 0.823 m`;
- conservative center-height clearance over the top corner: `z_center_clear = 0.050 + 0.022 + 0.001 = 0.073 m`.

These are geometry diagnostics, not new traversal acceptance criteria and not proof of a literal MuJoCo geom-pair contact.

Also preserve the previously reported risk proxy (`x>=0.778`, `z<=0.072`) for continuity, but do not confuse it with literal contact truth.

## 4. Required source-faithful swing reconstruction

The current CSV logs the swing start, nominal/final touchdown, effective lift, phase/scheduled swing, and actual world foot position, but `known_step_*_final_target_world_*` is the final touchdown target, not the instantaneous swing command.

For every B swing that has `known_step_<leg>_adaptation_active=1`, reconstruct the instantaneous world swing command exactly from the runtime source at B runtime HEAD `c44314b451ea77d460263052b7f274347881137c`:

- `LegSwingPhase(...)` using the frozen diagonal-trot pattern and the runtime phase/duty semantics;
- `SwingWorldTarget(start, end, swing_phase, effective_lift)`;
- if needed, `SwingWorldVelocity(...)` for supporting evidence.

Use source code, not a generic parabola. Validate the reconstruction against any independently available commanded-foot/IK telemetry where possible. If exact reconstruction is impossible from available fields, state the limitation and use the best directly observed command proxy without inventing values.

## 5. First-front-transition audit

At minimum analyze the interval from `14.45 s` through the first hard-posture crossing plus `0.10 s`, and identify all adapted front-leg swings (FR and FL) that begin before hard-posture.

For each such swing report:

- swing start time and world x/z;
- first adaptation-active time;
- nominal touchdown x/y/z;
- final touchdown x/y/z;
- touchdown center margin `final_x - 0.823`;
- effective lift;
- reconstructed command x/z versus state time and swing phase;
- actual foot x/z;
- `actual_z - commanded_z` and 3D command/actual tracking error where reconstructable;
- first time commanded center enters `x>=0.777`;
- commanded z at that instant;
- whether commanded z is >=0.073 at edge-envelope entry;
- first time actual center enters `x>=0.777`;
- actual z at that instant;
- whether actual z is >=0.073;
- foot-force/contact flag near the edge event;
- relevant three joint q_target/q_state errors, dq, tau_est, and effective torque/saturation evidence if available;
- whether the leg ever achieves physical contact with x>=0.85 and z>=z0+0.035 before hard-posture.

Explicitly compare FR versus FL. The purpose is to explain why FL reached x>0.86/z~0.074 while FR remained near x~0.788/z~0.044 at hard-posture.

## 6. Touchdown-placement audit

For every adapted swing before hard-posture, report the nominal/final touchdown x relative to:

- edge `0.800`;
- full-center-beyond threshold `0.823`.

Classify each planned touchdown as:

- `BEFORE_EDGE` if `<0.800`;
- `OVERLAPS_EDGE_ENVELOPE` if `[0.800,0.823)`;
- `CENTER_FULLY_BEYOND_EDGE` if `>=0.823`.

Do not move the threshold after seeing results.

Also report whether x/y truly remained unchanged by the terrain adapter for these specific swings.

## 7. Body/contact chronology

Build a compact chronology from first B adaptation through hard-posture containing at least:

- first FR adaptation;
- first FL adaptation;
- first planned command edge-envelope entry per front leg;
- first actual foot edge-envelope entry per front leg;
- first contact/force evidence change plausibly associated with the edge, without claiming literal step geom contact unless directly available;
- first pitch 10°, 16°, and 22° crossings;
- first roll 10°, 16°, and 22° crossings if any;
- max base x and its time;
- contact-count trajectory / loss of support around the event;
- solver status/residual to show whether failure is kinematic/contact versus numerical.

Compare the analogous A chronology where meaningful, especially A versus B time from first geometric risk to 22° posture crossing.

## 8. Classification

Return exactly one primary label:

- `PLANNED_EDGE_CLEARANCE_DEFICIT`: the reconstructed intended swing itself enters the edge envelope with commanded center z <0.073 m before the failure sequence.
- `TRACKING_OR_CONTACT_BLOCKED`: intended center is geometrically clear at edge-envelope entry, but actual center is not, with material command/actual deviation and/or contact/actuation evidence consistent with blockage.
- `TOUCHDOWN_PLACEMENT_DEFICIT`: intended touchdown center lies in `[0.800,0.823)` for the critical failed swing and the evidence supports shallow placement as the dominant boundary condition.
- `MIXED_CLEARANCE_TRACKING_PLACEMENT`: more than one of the above is materially implicated and no single one dominates.
- `OTHER_MECHANISM_IDENTIFIED`: another mechanism is directly evidenced; name it.
- `INSUFFICIENT_EVIDENCE`: available raw telemetry cannot distinguish the above.

A secondary list of contributing factors is allowed, but do not invent causal certainty beyond the measurements.

## 9. Required outputs

Create:

`example/cpp/tools/analysis/analyze_phase2_known_step_first_swing_failure.py`

and write results under:

`docs/validation/phase2_known_step_first_swing_failure_20260915/`

At minimum:

- `RESULTS.md`;
- `analysis.json`;
- `front_swing_summary.csv`;
- `edge_clearance_timeline.csv`;
- `body_contact_chronology.csv`;
- `provenance.csv`.

Plots may be added for command-vs-actual front-foot x/z and pitch/contact chronology, but machine-readable outputs are authoritative.

## 10. Stop

Commit and push the offline closeout, then stop.

Do not prepare or run a new controller variant, do not change lift, touchdown x, speed, gait timing, body pitch/height, WBC, D4, scene geometry, safety limits, or acceptance criteria in this checkpoint.