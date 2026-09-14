# TASK — Phase1 bounded stance-dq offline screen — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first and obey it. Perform exactly one offline checkpoint, push it, then stop.

## Starting evidence

Use checkpoint `f0d3f2cfd46b49308aa398b8cfe323d51a94b578` as evidence/base. Its exact-state replay showed that replacing controller-stance `dq_des` with the full Jacobian-consistent stationary-support solution produces a strong negative instantaneous base-x effect, but the full solution is too aggressive for live use: many joint references hit ±10 rad/s and the implied D-term changes are tens of Nm.

Do **not** run a new MuJoCo trajectory, live A/B, gain scan, gait scan, controller benchmark, or parameter search. Reuse the same validated 552 bridge-atomic snapshots and joined closure data used by the prior checkpoint.

## Research question

Can a **small, bounded correction of stance `dq_des` toward the Jacobian-consistent stationary-support solution** retain a consistent braking-direction same-state effect while keeping the commanded joint-velocity/D-term change small enough to be a plausible future live intervention?

This task screens a single conceptual variable: correction magnitude. Everything else is fixed.

## Candidate construction

For each target snapshot and each leg selected as controller stance by the joined `solver_contact_mask`:

1. Reproduce the prior checkpoint's full-rank Jacobian stationary-support solution `dq_ss` using the same frames, base local linear/angular velocity, desired-foot position at captured `q_des`, repository `FootJacobian`, SVD validity gates, and stationary-world-foot requirement.
2. Let baseline desired joint velocity be the exact captured bridge/LowCmd value `dq_base`.
3. Define the raw leg correction:

   `delta_dq_raw = dq_ss - dq_base`

4. Preserve the **direction of the entire 3-joint leg correction**. Do not independently clip joints. For each candidate compute one scalar `s_leg in [0,1]` and set:

   `dq_candidate = dq_base + s_leg * delta_dq_raw`

5. `s_leg` is the largest scalar satisfying both limits for all three joints of that leg:

   - `abs(s_leg * delta_dq_raw_i) <= 2.0 rad/s`
   - `abs(kd_i * s_leg * delta_dq_raw_i) <= candidate D-target torque cap`

   Treat `kd_i` as the exact captured bridge value. If `kd_i` is zero, only the dq cap constrains that joint.

6. Apply no change to swing legs. Keep `q_des`, `kp`, `kd`, `tau_ff`, state, contacts, WBC/SRBD/ID outputs, model, and all other motor commands unchanged.

Screen exactly these three predeclared candidates:

- `BOUND_D2`: per-joint absolute D-target change cap `2 Nm`
- `BOUND_D4`: cap `4 Nm`
- `BOUND_D6`: cap `6 Nm`

No other cap values are authorized.

## Replay and validation gates

Use the same target window and 552 exact snapshots as the prior atomic/stance-dq work. Before interpreting any candidate, all of these must pass:

- exact snapshot ↔ atomic bridge `ctrl` reconstruction;
- exact ACTUAL restored-state `qacc[0]` replay;
- same model/state signature as the validated source evidence;
- candidate changes only controller-stance `dq_des`;
- swing `dq_des`, all `q_des/kp/kd/tau_ff`, state, and contacts remain unchanged;
- candidate bridge formula is exact to numerical precision;
- the prior full stationary-support solve validity/rank/conditioning gates are reproduced;
- observed `abs(delta dq)` never exceeds `2.0 rad/s` except numerical epsilon;
- observed per-joint `abs(delta D-target)` never exceeds the candidate cap except numerical epsilon.

If any gate fails, stop and report `INCONCLUSIVE`; do not improvise.

## Metrics

For every candidate compute

`delta_ax = qacc_candidate_x - qacc_actual_x`

Negative is the desired instantaneous braking direction.

Report full-window median, p05, p95, fraction negative, fraction positive, median absolute effect, and zero fraction.

Stratify the same metrics by:

- gait phase `[0,.25)`, `[.25,.5)`, `[.5,.75)`, `[.75,1)`;
- controller contact mask (`solver_contact_mask`), marking `n < 20` as small-n;
- physical contact mask for audit only.

For stance-leg samples also report:

- distribution of `s_leg`;
- fraction limited first by the 2 rad/s dq cap versus D-torque cap;
- per-leg/per-joint `delta dq` and `delta D-target` distributions;
- baseline versus candidate stationary-support foot-velocity mismatch norm and x component;
- how often the correction is exactly zero.

## Pre-registered promotion rule

A candidate is eligible for **one future live A/B** only if all validation gates pass and all of the following hold:

1. full-window median `delta_ax <= -0.25 m/s²`;
2. full-window fraction negative `>= 0.75`;
3. full-window fraction positive `<= 0.10`;
4. every non-small controller-contact-mask median `delta_ax <= 0`;
5. every phase-bin median `delta_ax < 0`;
6. median stance foot-velocity mismatch norm is lower than baseline by at least `0.15 m/s`;
7. all commanded correction caps are respected.

If multiple candidates pass, recommend the **smallest D-torque cap** only. If `BOUND_D2` passes, do not prefer a larger candidate merely because its instantaneous effect is stronger.

If none pass, conclusion is `NO LIVE CANDIDATE`; do not invent another cap or run live.

## Interpretation boundaries

- This is same-state instantaneous evidence, not closed-loop trajectory evidence.
- Do not call a passing candidate a controller fix.
- Do not interpret individual joint torque signs as body propulsion/braking; body-x claims come only from exact MuJoCo `qacc[0]` replay.
- Do not change `kd`; the purpose is to test a bounded **reference correction**, not another gain experiment.
- Do not change stance position targets or WBC behavior.

## Deliverables

Commit at minimum:

- `docs/validation/phase1_bounded_stance_dq_screen_20260914/RESULTS.md`
- `docs/validation/phase1_bounded_stance_dq_screen_20260914/screen.csv`

Add a compact leg/joint derived CSV if needed for audit. Record source/run hashes and exact reproduction commands.

End `RESULTS.md` with exactly one next-step recommendation, not executed. Push one checkpoint and stop.