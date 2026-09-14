# TASK: Phase1 stance Jacobian-consistent dq counterfactual (2026-09-14)

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first. This is one closed, offline-only attribution checkpoint. Do not run a new MuJoCo trajectory, live A/B, gain scan, gait scan, or follow-up experiment.

## Starting point

Branch: `research/phase1-stance-jacobian-dq-counterfactual-20260914`

Base checkpoint: `4ad9a83803c69dd2a3bcddfd238f88e3cb35d4d4`.

Reuse the exact validated bridge-atomic evidence from the prior checkpoints, especially the 552 target snapshots in active-relative `[31.90,33.00)` and their closure/controller context. Do not substitute another run.

## Question

The previous checkpoint showed that the harmful joint-D marginal is driven more strongly by the target-motion term `kd*dq_des` than by the sensor-damping term, and that current `dq_des` is obtained by finite-differencing IK joint-position targets rather than from a task-space velocity solution.

Test one structural hypothesis:

> For stance legs, replacing only `dq_des` with a Jacobian-consistent joint velocity corresponding to a world-stationary support foot, while preserving the exact same joint position target, kp, kd, tau_ff, WBC/SRBD/ID outputs, state, contacts, and model, should remove part of the forward instantaneous D contribution.

This is a same-state causal test of the velocity reference itself. It is not a controller fix and must not be interpreted as closed-loop trajectory evidence.

## Unique conceptual variable

Only the stance-leg `dq_des` reference may change in the counterfactual branch.

Everything else must remain exactly ACTUAL:

- saved `mjSTATE_INTEGRATION` state;
- LowCmd `q_des`;
- kp and kd;
- `tau_ff`;
- swing-leg `dq_des`;
- WBC/SRBD/ID quantities;
- contact mask used to classify stance;
- model/scene;
- all external inputs.

Do not attenuate gains. Do not zero D. Do not change q targets or foot positions.

## Stance classification

Use the controller/WBC contact mask from the joined closure row (`solver_contact_mask` / the exact equivalent used by the full-WBC command path) as the primary stance definition. Do not select stance from a new heuristic. Record the physical contact mask separately for audit only.

If the exact controller-mask join cannot be made for all target snapshots under the already established timing/join semantics, stop and report INCONCLUSIVE rather than guessing.

## Construct the counterfactual dq reference

For each target snapshot, restore the exact saved state first.

For each leg classified as stance:

1. Take the exact captured LowCmd joint-position target `q_des = [hip, thigh, calf]` for that leg.
2. Compute the target foot position in the body frame from that q target using the repository kinematics (`go2::FootPosition` or the exact common FK used by the controller).
3. Obtain the base/body twist from the restored MuJoCo state using a frame-explicit method. Prefer MuJoCo body spatial velocity with local/body coordinates (`mj_objectVelocity(..., flg_local=1)` or an exactly equivalent, source-audited method). Do not assume a qvel frame without proving it.
4. For a world-stationary support foot, construct the desired foot velocity relative to the body:

   `v_foot_rel_body_des = -(v_base_body + omega_body x r_foot_body_des)`

   where `r_foot_body_des` is the target foot position from step 2.
5. Compute the repository 3x3 leg foot Jacobian at `q_des` using `go2_control::FootJacobian`.
6. Solve

   `J(q_des) * dq_stationary = v_foot_rel_body_des`

   with an SVD or equivalent numerically auditable 3x3 solve.
7. Apply the same per-joint `[-10,+10] rad/s` reference limit used by the existing velocity-feedforward path. Record both unclamped and clamped values and whether clamping occurred.
8. Replace only that stance leg's captured `dq_des` with the clamped `dq_stationary`. Swing-leg `dq_des` remains byte-for-byte/numerically identical to ACTUAL.

Use `q_des`, not measured q, for the Jacobian in the primary branch, because this task tests the velocity reference paired with the unchanged position reference. You may report a measured-q sensitivity as descriptive audit only if it requires no new run, but it must not become a second candidate or affect the decision.

## Numerical validity gates

Before interpreting body acceleration:

- Atomic bridge binding must still pass exactly as in the validated replay.
- Reconstructed ACTUAL bridge ctrl must match captured ctrl at the prior precision.
- ACTUAL restored-state replay must reproduce live `qacc[0]` for all 552 target snapshots at the prior precision.
- Verify non-stance/swing `dq_des` and all `q_des/kp/kd/tau_ff` are unchanged in the candidate.
- For every stance leg, report Jacobian singular values / condition number and solve residual before clamp.
- Treat a leg-snapshot as numerically invalid if the Jacobian solve is rank-deficient or condition number exceeds `1e4`, or if the pre-clamp Cartesian velocity residual exceeds `1e-6 m/s` under a full-rank solve.
- If more than 5% of stance leg-samples are numerically invalid, stop and report INCONCLUSIVE.
- Report the fraction of solved joints that hit the ±10 rad/s clamp. Do not silently change the clamp or introduce damping/tuning to improve the result.

## Required descriptive audit

For each stance leg/sample, compute from the ACTUAL captured reference:

`v_implied_actual = J(q_des) * dq_des_actual`

and compare it with the stationary-support requirement above.

Report at minimum:

- x-component and vector-norm mismatch distributions;
- per-leg results;
- gait-phase bins `[0,.25)`, `[.25,.5)`, `[.5,.75)`, `[.75,1)`;
- controller contact-mask strata with `n<20` marked small-n.

This audit determines whether the joint reference itself is kinematically inconsistent with stationary support; it is not an acceptance threshold by itself.

## Same-state counterfactual replay

For each snapshot, independently restore the same saved integration state for ACTUAL and CANDIDATE.

ACTUAL uses exact captured `ctrl`.

CANDIDATE must rebuild only the changed D target contribution through the exact bridge formula, equivalently:

`ctrl_candidate_i = tau_ff_i + kp_i*(q_des_i-q_sensor_i) + kd_i*(dq_candidate_i-dq_sensor_i)`

with `dq_candidate=dq_stationary` only on stance-leg joints and `dq_candidate=dq_actual` otherwise.

Then run `mj_forward` only. No time integration and no counterfactual feedback into the controller.

Define:

`delta_ax = qacc_candidate[0] - qacc_actual[0]`

Negative means the stationary-support velocity reference produces more instantaneous braking / less forward acceleration in that exact state.

## Required metrics

Report full-window and stratified statistics for `delta_ax`:

- n;
- median;
- p05 / p95;
- fraction negative / positive;
- median absolute effect.

Stratify by:

- gait phase bins above;
- controller/WBC contact mask;
- physical contact mask as audit;
- each leg where useful.

Also report:

- ACTUAL versus CANDIDATE D target torque change by joint and leg, especially thighs;
- actual `dq_des-dq_sensor` versus candidate `dq_stationary-dq_sensor`;
- stationary-support Cartesian residual after the ±10 rad/s clamp;
- whether effect direction is concentrated in particular phase/contact strata.

Do not infer propulsion from raw individual joint torque signs; body-x attribution comes from exact MuJoCo same-state `qacc[0]` replay.

## Predeclared interpretation

Use these labels only after all validation gates pass:

- **SUPPORTED**: full-window median `delta_ax <= -0.50 m/s²`, at least 80% of snapshots have `delta_ax < 0`, and every non-small (`n>=20`) gait-phase and controller-contact-mask stratum has median `delta_ax <= 0`.
- **PARTIALLY SUPPORTED**: full-window median `delta_ax < 0` but one or more SUPPORT conditions above fail.
- **NOT SUPPORTED**: full-window median `delta_ax >= 0`, or fewer than 50% of snapshots have `delta_ax < 0`.
- **INCONCLUSIVE**: a validation/numerical gate fails.

These thresholds classify this same-state structural hypothesis only. Even SUPPORTED does not authorize a live controller modification.

## Outputs

Commit:

- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/RESULTS.md`
- a derived CSV sufficient to audit every primary statistic, preferably `counterfactual.csv`
- any small analysis/replay source required to reproduce the result.

Record exact source SHA, tool/binary hashes, raw evidence hashes, model/scene hash, and exact command.

## Stop rule

Do not run a new trajectory or live A/B in this task.

After producing one checkpoint, push it and stop.

End `RESULTS.md` with exactly one recommended next step, not executed:

- if SUPPORTED or meaningfully PARTIALLY SUPPORTED, recommend a separately approved minimal live A/B that changes only stance `dq_des` construction;
- if NOT SUPPORTED, recommend abandoning this velocity-reference candidate and name the next structural layer to inspect;
- if INCONCLUSIVE, recommend only the minimum instrumentation/math fix required to make the same test observable.
