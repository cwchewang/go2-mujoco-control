# Phase1 reference/WBC structural attribution — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first and obey it. Complete exactly one checkpoint, push it, then stop.

## Why this task exists

The validated evidence now rules out simple gain tuning as the Phase1 fix:

- ID/WBC dynamics closure passed exactly in the overspeed window.
- Atomic bridge replay proved that joint PD changes instantaneous base-x acceleration materially.
- Global D removal is instantaneously braking; P removal is instantaneously accelerating.
- Four-thigh D attenuation was promising in same-state offline replay, but both the single-RR-thigh live intervention and symmetric four-thigh D90 live A/B failed to improve closed-loop velocity tracking.

Therefore do **not** scan gains. The remaining question is structural: does the gait/IK joint-velocity reference delivered to joint D control conflict with the body-x braking objective delivered through WBC/SRBD/ID?

## Scope

This checkpoint is **offline/source-analysis only**.

Forbidden:
- no new MuJoCo trajectory;
- no live A/B;
- no gain scan;
- no gait/period/duty/Raibert/governor tuning;
- no controller behavior change;
- no Phase2/terrain work.

You may build/run offline analysis/replay tools against already captured evidence.

Primary evidence:
- validated atomic snapshot run from checkpoint `6cd37e02385eaa98a1ea75002b21378a70120740`;
- its `bridge_atomic_snapshots.bin` and matching `data.csv.id_closure.csv`;
- existing Phase1 logs/checkpoints, especially `bab9f56`, `324064c`, and `45f7338`.

## Stage 1 — trace the two command paths exactly

Document the exact source path, formulas, state variables, and timing for both paths.

### Path A: kinematic reference → joint PD

Trace at minimum:

`runtime velocity command`
→ `ScheduleContinuousVelocityGait`
→ `RaibertTrotKernel::Compute`
→ commanded body-frame feet
→ IK joint targets
→ `UpdateJointVelocityFeedforward`
→ LowCmd `q`, `dq`, `kp`, `kd`
→ bridge PD torque.

Explicitly verify from source, do not assume:

1. how `step_length`, `period`, and `duty` determine the stance-foot x trajectory;
2. the exact stance interpolation function and its derivative;
3. whether stance desired foot speed is constant or phase-shaped;
4. how `joint_velocities` / LowCmd `dq` are produced;
5. whether LowCmd `dq` is an analytic task-space velocity solution or merely finite-difference IK position targets;
6. whether the same joint dq target is used for stance and swing legs;
7. how contact blending changes `kd` but not `dq_des` itself.

For the current running-trot kernel, derive the stance x-velocity implied by the actual source formula. If the source still uses Smoothstep over stance, show the closed-form phase dependence and peak/mean ratio. Do not silently replace it with a linear approximation.

### Path B: body velocity objective → WBC/SRBD/ID

Trace at minimum:

`applied/nominal body velocity`
→ body velocity error / desired base-x acceleration
→ SRBD/contact-force target
→ ID-WBC qdd/contact forces/tau
→ LowCmd `tau_ff`
→ bridge.

Also document any place where commanded foot position/velocity enters WBC. In particular, check whether `commanded_body_feet_velocity_` is used for swing-foot tasks and whether stance contacts are treated kinematically differently from swing feet.

Output a compact side-by-side dependency graph. Identify variables shared by both paths versus variables that can disagree.

## Stage 2 — exact same-state D-term decomposition

Use the already validated atomic snapshots. Preserve all original validation gates:

- atomic snapshot ↔ bridge ctrl equality;
- bridge formula equality;
- ACTUAL replay reproduces live `qacc[0]` exactly/tightly before any interpretation;
- independent state restore for every branch.

For each snapshot define the bridge D torque for motor i:

`D_i = kd_i * (dq_des_i - dq_sensor_i)`

and decompose it algebraically into:

- target-motion component: `D_target_i = kd_i * dq_des_i`
- sensor-damping component: `D_sensor_i = -kd_i * dq_sensor_i`

Run same-state instantaneous counterfactuals, at least:

1. `ACTUAL`
2. `NO_D_ALL` — regression check against the prior validated D-removal result
3. `NO_D_TARGET_ALL` — set only the target-motion component to zero, retaining `-kd*dq_sensor`
4. `NO_D_SENSOR_ALL` — remove only the sensor-damping component, retaining `kd*dq_des`
5. `NO_D_TARGET_THIGHS` — target-motion removal only on FR/FL/RR/RL thigh indices 1,4,7,10
6. `NO_D_SENSOR_THIGHS` — sensor-damping removal only on those four thighs

Do not infer physical effect from raw torque sign. For every branch use replayed `qacc[0]` and report

`delta_ax = qacc_branch_x - qacc_ACTUAL_x`.

Report full-window median/p05/p95/sign fractions and stratify by replay contact mask and gait phase. Regress `NO_D_ALL` against the previously committed value to double precision or explain any difference before continuing.

Important: these are marginal same-state counterfactuals. Do not claim additivity unless explicitly audited.

## Stage 3 — test the structural conflict hypothesis

Using source formulas plus existing logs/snapshots, test the following hypothesis rather than assuming it:

> During stance, the IK-derived `dq_des` follows a phase-shaped body-frame foot trajectory tied mainly to the gait schedule/nominal speed. When measured body speed differs from that schedule — especially during overspeed while WBC requests braking — joint D tracking can oppose the base-x braking objective.

Quantify as much of the following as existing evidence permits without a new trajectory:

- commanded stance foot x velocity versus gait phase;
- nominal/applied body speed and measured body speed;
- sagittal world-stationary stance requirement. At minimum use the clearly stated approximation `v_foot,body,x ≈ -v_body,x`; if all orientation/angular-rate/foot-position terms are available, compute the full rigid-body expression instead;
- `dq_des - dq_sensor` on thigh joints by stance/swing and phase;
- D-target and D-sensor instantaneous base-x effects from Stage 2;
- whether the harmful D effect is concentrated where commanded stance velocity and the measured-speed-consistent stance requirement disagree.

If `commanded_body_feet_velocity_` or equivalent existing logs are sufficient, use them. If not, reconstruct the commanded derivative from the exact kernel formula/source state only when the reconstruction is auditable. Do not launch a new run just to add logging in this checkpoint.

## Required conclusions

The checkpoint must answer these questions explicitly:

1. What exactly generates LowCmd `dq_des` in Phase1?
2. Is the harmful D marginal primarily attributable to `kd*dq_des`, to `-kd*dq_sensor`, or is it genuinely mixed/context-dependent?
3. Does the stance reference velocity have a structural phase shape that is inconsistent with approximately world-stationary support at constant body speed?
4. During the overspeed/braking window, is there evidence that the kinematic reference path and WBC base-x path demand incompatible actuator behavior?
5. Is the structural-conflict hypothesis **SUPPORTED**, **PARTIALLY SUPPORTED**, **NOT SUPPORTED**, or **INCONCLUSIVE**? State exactly which evidence earns that label.
6. Recommend exactly **one** next experiment/design step. Do not execute it.

## Decision discipline

Do not conclude that finite-difference `dq_des`, Smoothstep stance, or PD is a bug merely because it exists. A structural conflict requires measured/replayed evidence connecting the reference construction to the harmful base-x marginal.

Likewise, do not reopen governor, period, duty, simple kd tuning, or ID dynamics closure unless new evidence directly falsifies prior validated checkpoints.

If Stage 2 cannot be validated from the existing atomic data, stop as INCONCLUSIVE and state the minimum missing observable. Do not run a new trajectory.

## Deliverables

Create:

- `docs/validation/phase1_reference_wbc_structural_attribution_20260914/RESULTS.md`
- one or more CSVs containing the D decomposition and any kinematic/phase attribution used in the result
- offline analysis source/tool if needed

Push one checkpoint commit on this branch and stop.