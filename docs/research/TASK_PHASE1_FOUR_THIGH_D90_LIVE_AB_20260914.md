# Task: Phase1 four-thigh D90 live A/B

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first. Its constraints are part of this task.

## Goal

Test whether the offline-promoted symmetric four-thigh D attenuation improves the real closed-loop 2.3 m/s plateau without destabilizing the gait.

Offline evidence source: `324064c931a68a0fdc637686bd669d8e0498b4fd`.

The validated atomic replay screened three symmetric candidates on the same 552 exact states:

- `THIGH_D_90`: retain 90% D on FR/FL/RR/RL thigh joints; full-window median delta_ax = -0.552166 m/s2; 91.12% negative.
- `THIGH_D_80`: retain 80%; stronger median effect but more sign violations.
- `THIGH_D_70`: retain 70%; stronger median effect but still more sign violations.

`THIGH_D_90` was the smallest pre-registered candidate that passed every full-window, phase, and non-small contact-mask promotion gate. This live task tests only that candidate. Do not scan 80% or 70%.

## Hypothesis

During the 2.3 m/s plateau, retaining 90% of the four thigh-joint D contribution will reduce the real closed-loop velocity excess and improve settling/tracking, while preserving posture/contact stability.

This is a one-variable physical A/B. The offline instantaneous result is not assumed to imply closed-loop benefit.

## Fixed benchmark

Use the existing `varying` profile unchanged:

- 24–32 s: 1.4 -> 2.3 m/s ramp
- 32–40 s: 2.3 m/s plateau
- 40–48 s: 2.3 -> 2.8 m/s ramp

Keep unchanged:

- B semantic: `step = applied * period`, effective-speed convention false;
- period 0.14 s;
- duty 0.44;
- velocity shaper/governor/tracking lead;
- Raibert/preview;
- WBC/SRBD/ID mathematics and weights;
- contact logic;
- q/dq targets;
- P contribution / kp;
- tau_ff;
- hip/calf D;
- model, scene, limits, profile, acceptance thresholds.

Do not set a new explicit seed if the current accepted varying baseline does not use one. A and B must use the same source/binaries and otherwise identical effective environment.

## Unique variable

Motor order is the repository order. The only motors modified in B are thigh indices:

- 1 = FR_thigh
- 4 = FL_thigh
- 7 = RR_thigh
- 10 = RL_thigh

A: normal D for the entire run.

B: only during active-relative `[32.10, 39.90)` s, set the effective thigh `kd` to exactly `0.90 * baseline_kd` on all four thigh motors simultaneously.

Outside that interval, B must be baseline-identical. Do not phase-gate or contact-gate this experiment: the promoted offline candidate was symmetric across the entire target state set.

Implement with one default-off flag cached at initialization. Do not parse the flag in the 500 Hz hot loop.

Suggested flag:

`TROT_FOUR_THIGH_D90_AB=1`

The exact name may differ; record it.

The implementation must leave `q_des`, `dq_des`, `kp`, `tau_ff`, all non-thigh `kd`, and every controller/WBC quantity unchanged by construction.

## Required logging

Add only the minimum diagnostics needed to prove the intervention:

- experiment enabled flag;
- active-relative time;
- gate active flag;
- baseline and effective kd for all four thigh motors;
- existing requested/shaped/applied/measured velocity;
- existing WBC desired ax, SRBD ax, ID qdd_x;
- existing contact/posture/safety diagnostics.

Do not add expensive new shadow dynamics.

## Run plan

Use one source state and one binary for both arms.

1. Run A first with the flag OFF.
2. A gate must pass before B is allowed.
3. If A gate passes, run B once with the flag ON.

Maximum launches: 3 total. A third launch is allowed only to replace an infrastructure-invalid run that did not produce usable benchmark data. Do not repeat a genuine A/B safety or control outcome.

### A gate

A must:

- reach at least active 40 s;
- have no new hard safety failure;
- reproduce the known 2.3 m/s residual-overspeed regime in `[32,33)`;
- show model-side braking in that interval (WBC/ID desired x acceleration predominantly negative).

As a practical reproduction gate, require `[32,33)` median `measured - applied > +0.15 m/s`. If this is not met, stop and classify the experiment invalid/inconclusive; do not run B.

## A/B comparability gate

Before interpreting the intervention, compare A and B over pre-window `[31.90,32.10)`.

Require no obvious pre-existing divergence. At minimum report:

- median measured velocity;
- median applied velocity;
- median velocity excess;
- realized ax;
- roll/pitch p95;
- physical contact-mask distribution.

If pre-window velocity-excess medians differ by more than 0.03 m/s, or posture/contact behavior is clearly non-comparable, classify the causal result INCONCLUSIVE rather than forcing an interpretation.

## Analysis windows

Use active-relative time.

Report at least:

- pre: `[31.90,32.10)`
- early plateau: `[32.10,33.00)`
- middle plateau: `[33.00,36.00)`
- late plateau: `[36.00,39.90)`
- full intervention: `[32.10,39.90)`

For each arm/window report:

- requested/shaped/applied/kernel nominal velocity;
- measured velocity;
- velocity excess = measured - applied;
- absolute target error to 2.3 m/s where applicable;
- realized body-x acceleration using the same 100 ms local linear fit used in prior work;
- WBC desired ax;
- SRBD ax;
- ID qdd_x;
- governor activity / shaped-applied gap;
- roll/pitch p95 and max;
- physical contact counts/masks and internal-vs-physical mismatch if already available;
- torque maxima / safety / solver status.

Also run the existing Phase1 analyzer unchanged and report its original settling result/latency for the 1.4->2.3 transition for A and B.

## Primary causal effects

Because these wall-clock runs are not bitwise replays, report both direct B-A effects and a pre-window difference-in-differences (DID).

Primary tracking metric:

`DID_excess = (B_full_intervention_excess - B_pre_excess) - (A_full_intervention_excess - A_pre_excess)`

Negative is improvement.

Also report:

- B-A median velocity excess in early/middle/late/full intervention;
- B-A measured velocity;
- B-A realized ax;
- settling pass/fail and latency change;
- overspeed peak change;
- posture/contact changes.

## Pre-registered interpretation

`SUPPORTED` requires all of the following:

1. pre-window comparability gate passes;
2. no hard safety failure or clear gait/contact collapse in B;
3. full-intervention `DID_excess <= -0.02 m/s`;
4. early plateau velocity excess is not worse by more than +0.01 m/s;
5. at least one of these is additionally true:
   - original Phase1 1.4->2.3 settling result improves;
   - settling latency improves materially;
   - full-intervention overspeed peak decreases by at least 0.02 m/s;
6. posture/contact quality does not show a clearly worse failure mode.

`NOT SUPPORTED` if the comparability gate passes but B produces no meaningful tracking benefit, worsens velocity excess, or causes stability/contact degradation.

`INCONCLUSIVE` if A fails the gate, A/B are not comparable before intervention, infrastructure/instrumentation is invalid, or a confound prevents attribution.

Do not use `PARTIALLY SUPPORTED` unless the exact supported and unsupported subclaims are separately stated and the primary tracking criterion itself is not misrepresented.

## Stop rules

Do not:

- test THIGH_D_80 or THIGH_D_70;
- change the 0.90 scale;
- add phase/contact gates;
- tune any WBC/SRBD/Raibert/gait parameter;
- retry a genuine B safety failure;
- extend into Phase2/terrain;
- auto-fix the controller after seeing the result.

If B fails safety, preserve the failure timing and treat it as the experimental result.

## Output

Commit one compact checkpoint only:

- `docs/validation/phase1_four_thigh_d90_live_ab_20260914/RESULTS.md`
- `docs/validation/phase1_four_thigh_d90_live_ab_20260914/ab.csv`
- the minimal default-off source diff and diagnostics.

Raw logs may remain local; record run IDs, commands, binary/source hashes, and SHA256 for raw evidence.

`RESULTS.md` must state:

- exact A/B unique variable;
- A gate result;
- pre-window comparability result;
- proof that only four thigh kd values were scaled to 0.90 inside `[32.10,39.90)`;
- all requested windows;
- DID and direct tracking effects;
- original Phase1 settling comparison;
- safety/posture/contact result;
- outcome: SUPPORTED / NOT SUPPORTED / INCONCLUSIVE;
- one next recommendation, not executed.

Push one checkpoint and stop.