# Bounded MJPC adaptation diagnostic v1

Mode: PREPARATION / NOT_RUN; two independent one-arm protocols, no retry.
Parent: b5547c77898c237ceb883407d64d3ce245c97fc5.
Branch: research/mjpc-adaptation-diagnostic-20261002.

Decision: determine whether correcting proven ground-frame/actuation mappings
changes the adapted MJPC failure, while keeping third-stage topic selection open.
This is a package diagnostic, not a single-factor cause or new method.

A uses the frozen source configuration plus bounded prediction records.
B retains source position references and PD60/5 and changes only floor world
z-0.01 to0 and force-clamps AFTER the source PD law to canonical named motor
ranges40/45.43Nm with unit gear. Never substitute torque actuators while feeding
joint positions. Keep source mass15.806408kg/root7.521kg, damping2.0, contact
impedance, MakeDifferentiable, cost/gait weights, Walk/Manual Trot, reset,
0.1s zero/0.2s ramp to1m/s,0.35s horizon/10ms prediction,20ms replan/2ms feedback,
one-sided fd1e-6/derivative_skip0. Source choices/intentional approximations are
not proven mapping defects. Both models already have impratio100.

[Original protocol](../../tools/substrate/protocols/mjpc-adaptation-original-3s-v1.json)
and [corrected protocol](../../tools/substrate/protocols/mjpc-adaptation-corrected-3s-v1.json)
each freeze one attempt,3s/1500 canonical steps,150 replans,300s wall ceiling
and614400 private integration-step upper bound. Total formal cap is2 attempts,
3000 canonical steps and1228800 private steps. Reserve4096 before each optimizer
call. Counters record exact rollout mj_step calls and FD calls with a source-bound
integration upper bound; do not claim exact internal FD step counts.
Each task permanently ends on first safety/execution/evidence/budget failure.

B requires A's NEW independently verified capture to reproduce the sealed
1287-tick nonfoot stop, qpos/qvel/applied-control prefix within1e-9 and identical
contact classifications. If A does not reproduce, B stays NOT_RUN while
instrumentation/configuration is checked. Never reopen old campaign/17 NOT_RUN.

Record selected policy generation/candidate index, anchor time, optimization
model identity and36 nominal knots with state/position actions and reconstructed
active contacts on a separate smoothed private copy. These are reconstructed
contacts, not stored rollout forces. Canonical raw retains actual2ms target/
resolved torque/state.10ms nominal versus five2ms feedback actions differ by
design; their difference is not automatically model error.

Classification: HORIZON_REACHED, SAFETY_STOP or execution/evidence stop.
Three seconds crosses the known2.574s event; it cannot certify a12s useful
baseline. A reproduced stop/B horizon motivates separate useful-baseline
admission; both stops require prediction/task evidence before zero-forward.
Neither identifies a single parameter or an iLQR family limitation.
Zero-vx in this bridge still trots; no standing/gait ablation is authorized.

[Preparation result](../validation/mjpc_adaptation_diagnostic_v1_prep_20261002/RESULTS.md)
owns current-input qualification/prepared bindings and precheck evidence.
Both tasks require genuine independent exact-clean-head science/execution
reviews and separate protocol/prepared/private-budget-bound START records.
The continuing third-stage delegation supplies intent; closed campaign
START/reviews cannot be reused. No new method or generic platform is in scope.
