# Task: four-thigh D symmetric offline screen

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first. Its constraints remain binding.

## Context

The validated atomic replay from `6cd37e02385eaa98a1ea75002b21378a70120740` established that, at the same MuJoCo state, removing all joint D makes base-x acceleration substantially more negative, while removing P makes it more positive. The component decomposition checkpoint `bab9f56288dd74734a91945117d94c74c8b4d32f` further showed that the thigh joints dominate the D-side marginal.

A subsequent live A/B that attenuated only RR_thigh D by 25% in phase `[0.50,0.75)` was NOT SUPPORTED: the closed loop compensated and no braking/tracking improvement was obtained. Do not repeat that single-joint experiment and do not scan live gains.

## Goal

Before any further live intervention, use the already validated 552 atomic snapshots to screen one very small family of symmetric four-thigh D attenuations offline.

Question:

**If the D contribution is attenuated equally on all four thigh motors, does the same-state instantaneous base-x effect remain consistently in the desired braking direction across contact masks and gait phases, and what is the smallest attenuation that is worth a future live A/B?**

This task is offline only. Do not run MuJoCo trajectories.

## Fixed evidence

Reuse the exact atomic evidence used by `bab9f56`:

- snapshot source from the validated bridge-atomic run;
- same scene/model;
- same 552 target snapshots in active `[31.90,33.00)`;
- ACTUAL replay must reproduce live `qacc[0]` exactly before interpreting any candidate.

Use repository motor order:

`0..11 = FR_hip, FR_thigh, FR_calf, FL_hip, FL_thigh, FL_calf, RR_hip, RR_thigh, RR_calf, RL_hip, RL_thigh, RL_calf`

The four thigh motors are therefore indices:

`1, 4, 7, 10`.

## Candidate branches

Evaluate exactly three symmetric attenuation candidates:

- `THIGH_D_90`: retain 90% of the D contribution on each of the four thigh motors (10% attenuation);
- `THIGH_D_80`: retain 80% (20% attenuation);
- `THIGH_D_70`: retain 70% (30% attenuation).

Do not add more candidates.

For each snapshot and each candidate, start from an independently restored copy of the exact saved integration state and exact ACTUAL atomic bridge command.

For each thigh motor `i`, reconstruct its exact bridge D contribution using the bound atomic record:

`D_i = kd_i * (dq_des_i - dq_sensor_i)`

Then set candidate control only on thigh motors:

`ctrl_candidate_i = ctrl_actual_i - attenuation_fraction * D_i`

All non-thigh motors remain exactly `ctrl_actual`.

P, tau_ff, q/dq targets, model state, contacts, actuator model, and every other input remain unchanged.

Run `mj_forward` only. No candidate state may feed into another candidate or the live trajectory.

Define:

`delta_ax = qacc_candidate_x - qacc_actual_x`

Negative is the desired instantaneous direction for the current overspeed/braking problem.

## Validation gates

Before interpreting candidates, require all of the following:

1. atomic bridge binding remains exact;
2. bridge formula reconstruction remains exact;
3. ACTUAL replay reproduces live `qacc[0]` for all 552 target snapshots with max residual <= `1e-5 m/s2`;
4. candidate branches differ from ACTUAL only by the declared scaled D contribution on motors `1,4,7,10`;
5. each candidate restores the original integration state independently.

If any gate fails, stop and report INCONCLUSIVE. Do not repair by running a new trajectory.

## Required analysis

For each of the three candidates report, over full `[31.90,33.00)`:

- n;
- median delta_ax;
- p05/p95;
- fraction negative / positive;
- median absolute effect.

Also stratify by:

- replay physical contact mask;
- gait phase bins `[0,0.25)`, `[0.25,0.5)`, `[0.5,0.75)`, `[0.75,1)`.

Mark any stratum with `n < 20` as small-n and do not use it for promotion decisions.

Additionally compare the three candidates for approximate monotonicity. For each snapshot, the 10/20/30% attenuation effects should be ordered approximately with attenuation magnitude. Report how often the sign or ordering violates a simple monotonic expectation; do not assume linearity.

## Pre-registered promotion rule

A candidate may be recommended for one future live A/B only if:

- full-window median `delta_ax < -0.25 m/s2`;
- full-window fraction negative >= 70%;
- every non-small-n phase-bin median is <= 0;
- every non-small-n contact-mask median is <= 0;
- no smaller attenuation candidate also satisfies all of the above.

Choose the smallest attenuation satisfying all rules.

If none satisfies all rules, conclude `NO LIVE CANDIDATE` and stop. Do not weaken the rule after seeing results.

This promotion rule is intentionally conservative because the prior RR_thigh live result demonstrated that same-state instantaneous benefit does not guarantee closed-loop improvement.

## Interpretation limits

Do not claim that a passing candidate is a controller fix or root cause. This task only screens whether a symmetric four-thigh D intervention has a cleaner same-state instantaneous signature than the failed single-joint intervention.

Do not infer trajectory stability from `mj_forward` replay.

Do not change P, tau_ff, other joints, gait parameters, WBC/SRBD/ID, contact logic, model, or benchmark.

## Output

Commit one compact checkpoint containing:

- `docs/validation/phase1_four_thigh_d_offline_screen_20260914/RESULTS.md`
- `docs/validation/phase1_four_thigh_d_offline_screen_20260914/screen.csv`
- minimal offline replay-tool changes only, if needed.

`RESULTS.md` must state:

- validation-gate status;
- exact candidate definitions;
- full-window results;
- contact/phase stratification;
- monotonicity audit;
- promotion-rule result;
- either the single smallest recommended live candidate or `NO LIVE CANDIDATE`;
- no executed follow-up.

Do not run a live A/B. Push one checkpoint and stop.