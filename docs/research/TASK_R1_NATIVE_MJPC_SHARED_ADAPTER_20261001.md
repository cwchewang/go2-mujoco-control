# R1 native MJPC shared adapter — 2026-10-01

Goal: move the already audited author Go2 MJPC implementation into the new shared controller boundary without rewriting the controller or changing canonical evaluation physics.

Scope:
- reuse johnzhang3/mujoco_mpc at pinned commit e00c47a5adb9856af2e0f24231bb3a60d5be23c4;
- keep a persistent headless native controller process;
- require WholeBodyState input and emit source joint-position targets;
- validate the pinned nominal actuator defect first, then apply mjBIAS_AFFINE only to the controller-private planning model;
- convert source q_des through PositionTargetControllerAdapter into canonical direct torque;
- preserve explicit Manual/Trot Walk selection and current-state iLQG feedback;
- seal the native binary against source/build inputs.

This is infrastructure only. Scientific attempts are 0. No canonical plant stepping, capability classification, tuning, or controller ranking is authorized by this task.

Acceptance:
1. portable protocol/contract tests pass;
2. native build is source-pinned and sealed;
3. one zero-canonical-step state -> MJPC -> q_des -> torque integration smoke succeeds with finite output;
4. canonical plant remains at time 0 and steps 0;
5. legacy launch/qualification/native boundaries remain intact;
6. PROJECT_RECORD and CURRENT navigation describe the implemented engineering state without claiming Gate 0 completion.
