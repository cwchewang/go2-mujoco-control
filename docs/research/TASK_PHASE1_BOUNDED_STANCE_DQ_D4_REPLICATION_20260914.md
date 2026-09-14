# Task: Phase1 bounded stance-dq D4 live replication — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first and obey it. Complete exactly one checkpoint, push it, then stop.

## Purpose

Replicate the prior `BOUND_D4` live A/B without changing the intervention. The previous checkpoint `e65c8830905c2c744c85d82ec08c3e4b7f6989c4` was **INCONCLUSIVE** only because the pre-window A/B velocity-excess difference was `-0.037243499 m/s`, outside the preregistered `±0.03 m/s` comparability band. Do not reinterpret that run as causal evidence.

This task asks only whether an exact clean replication can establish the tracking effect and whether the prior posture/contact degradation reproduces.

## Fixed intervention

Use the implementation already present on this branch. Do not alter controller behavior, thresholds, gains, gait parameters, model, scene, profile, logging semantics, or acceptance behavior.

Arm A: `TROT_BOUNDED_STANCE_DQ_D4_AB=0`.

Arm B: `TROT_BOUNDED_STANCE_DQ_D4_AB=1`.

During active-relative `[32.10,39.90)`, and only for controller/WBC stance legs, B replaces baseline `dq_des` by the same bounded whole-leg Jacobian correction already implemented:

`delta = dq_ss - dq_base`

`s = min(1, 2/max|delta|, 4/max|kd*delta|)`

`dq_new = dq_base + s*delta`

The unique conceptual variable is this stance `dq_des` correction. Swing dq, q, kp, kd, tau_ff, WBC/SRBD/ID outputs, contacts, model, scene, velocity profile, period, duty, step semantics, governor, Raibert, preview, and all other behavior must remain unchanged.

## Authorized runs

Exactly two launches are authorized: A first, then B. No retry, no third launch, no gain scan, no D2/D6 substitution, no phase/contact gating, no follow-up experiment.

If A fails to reproduce the expected continuous-trot baseline or any infrastructure/logging failure prevents the requested comparison, stop and report instead of improvising.

## Frozen run entry point

Use the same varying profile and benchmark entry point as the prior checkpoint, with no explicit seed:

`TROT_CPU_AUTOPIN=1 TROT_DIAG_ID_CLOSURE=1 TROT_BOUNDED_STANCE_DQ_D4_AB={0|1} GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv bash example/cpp/scripts/run_phase1_velocity_benchmark.sh varying <output-root> 232`

A and B must use the same built controller binary, simulator binary, scene, profile, domain and environment except for the single A/B flag.

## A baseline gate

Before interpreting B, A must reach the active `2.3 m/s` continuous-trot region and reproduce the established residual overspeed regime. Report at minimum for `[32,33)`:

- row count;
- median measured, applied, and `velocity_excess = measured-applied`;
- WBC desired ax, SRBD ax, ID qdd-x medians and negative fractions;
- regime/status and safety outcome.

If A does not show the expected continuous-trot residual-overspeed/braking-demand pattern, stop before launching B only if the failure is known before B is started; otherwise report the invalid checkpoint and stop.

## B isolation gate

Audit that B:

- enables the correction only in active `[32.10,39.90)`;
- changes only controller-stance leg dq;
- leaves swing dq identical to baseline command generation;
- leaves q/kp/kd/tau_ff unchanged;
- has valid rank/condition/residual solves or documented baseline fallback;
- respects max `|Δdq| <= 2 rad/s` and max `|kd*Δdq| <= 4 Nm`;
- uses no correction in A.

If isolation fails, result is invalid and causal interpretation is forbidden.

## Pre-window comparability gate

Use pre-window active `[31.90,32.10)` and the same metric as the prior task.

Compute median velocity excess for A and B. Require:

`abs(B_pre_excess - A_pre_excess) <= 0.03 m/s`.

If this gate fails, the decision is **INCONCLUSIVE** and DID must not be interpreted causally. Still report intervention-window and stability measurements descriptively, then stop. Do not rerun.

## Primary tracking endpoint

For the full intervention `[32.10,39.90)`, compute median velocity excess for A and B and

`DID_excess = (B_full - B_pre) - (A_full - A_pre)`.

Negative is improvement. The preregistered tracking-support threshold remains:

`DID_excess <= -0.02 m/s`.

Also report direct B-A excess for early/middle/late/full windows, measured velocity, applied velocity, realized 100-ms ax, overspeed peak, and the existing 1.4→2.3 settling result.

Do not replace the DID decision with any secondary endpoint.

## Stability / trade-off audit

This replication must explicitly determine whether the large posture/contact cost seen previously reproduces. Report for A and B over the full intervention:

- roll and pitch p95 and max absolute degrees;
- physical contact-count median/min and physical contact-mask distribution;
- internal/physical mask mismatch fraction;
- governor/emergency-support-cap messages or other recovery actions;
- torque-saturation fraction;
- hard safety outcome;
- solver/SRBD/ID success fractions.

Do not create a new gain or stability threshold after seeing the data. State plainly whether B is comparable to A, mildly degraded, or materially degraded, and support that wording with the measurements. A tracking improvement with clear posture/contact degradation is a **tracking-vs-stability trade-off**, not a controller fix.

## Decision labels

Use exactly one top-level result:

- `INCONCLUSIVE` — comparability or isolation/infrastructure gate fails.
- `NOT SUPPORTED` — all gates pass but `DID_excess > -0.02 m/s`.
- `SUPPORTED WITH STABILITY COST` — gates pass, `DID_excess <= -0.02 m/s`, and B clearly reproduces meaningful posture/contact degradation relative to A.
- `SUPPORTED` — gates pass, `DID_excess <= -0.02 m/s`, and no meaningful posture/contact degradation is observed.

Do not promote D4 to a baseline controller in this task regardless of result.

## Outputs

Write:

- `docs/validation/phase1_bounded_stance_dq_d4_replication_20260914/RESULTS.md`
- `docs/validation/phase1_bounded_stance_dq_d4_replication_20260914/ab.csv`

Record exact branch/source commit, run IDs, commands, controller/simulator SHA256, scene/profile SHA256, raw data/log/manifest/environment hashes, and the exact A/B comparison.

Push one checkpoint and stop. End with one recommended next step only; do not execute it.