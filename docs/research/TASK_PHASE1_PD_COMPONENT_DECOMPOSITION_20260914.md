# Task: Phase1 validated PD component decomposition

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first. Its constraints are part of this task.

## Starting point

Branch base/checkpoint:

`6cd37e02385eaa98a1ea75002b21378a70120740`

The previous bridge-atomic replay is now considered the trusted causal substrate for this task.

Validated facts from that checkpoint:

- one ordinary-PD `varying` run completed normally;
- atomic bridge/snapshot binding passed;
- snapshot `ctrl[12]` exactly matched the bound bridge atomic record;
- ACTUAL same-state replay reproduced live `qacc[0]` for 552/552 target snapshots with max residual 0;
- counterfactual definition was `delta_ax = qacc_cf_x - qacc_actual_x`;
- removing all joint PD while preserving exact same state/contact produced full-window median `delta_ax = -1.617932 m/s^2`;
- 72.64% of the 552 snapshots had `delta_ax < 0`;
- the effect was strongly phase/contact dependent;
- this is instantaneous same-state causality only, not a closed-loop trajectory claim.

Do not revisit command-lag matching, old non-atomic replay, global tau-ff-only live runs, or live PD-off pulse experiments in this task.

## Question

Which part of the bridge-side joint PD term is responsible for the validated instantaneous base-x acceleration effect?

Specifically separate:

1. P versus D contribution;
2. each leg's contribution;
3. each joint's contribution;
4. dependence on contact mask and gait phase.

The purpose is to identify a minimal candidate interaction for a future live validation. This task itself is offline only.

## Hard constraints

- Do **not** run a new MuJoCo trajectory/simulation.
- Do **not** change controller, gains, WBC/SRBD, gait, contact logic, model, profile, thresholds, or bridge behavior.
- Use the exact validated atomic snapshot/raw evidence from checkpoint `6cd37e0`.
- Every counterfactual branch must start from an independently restored copy of the same snapshot state.
- ACTUAL replay must continue to pass before interpreting any derived branch.
- Do not infer whole-body braking from raw joint-torque sign alone; use replayed `qacc[0]`.
- Do not sum component effects as if guaranteed linear unless additivity is explicitly checked.

## Required replay branches

For each of the 552 validated target snapshots in active `[31.90,33.00)`:

### Baselines

- `ACTUAL`: exact captured `tau_ff + P + D` control.
- `NO_PD`: exact captured `tau_ff` only. Reproduce the prior validated result as a regression check.

### Global split

- `NO_P`: `tau_ff + D`.
- `NO_D`: `tau_ff + P`.

Define for every branch:

`delta_ax_branch = qacc_branch_x - qacc_actual_x`

Thus negative delta means removing that component makes base-x acceleration more negative at the same state.

### Per-leg ablations

For each leg `FR, FL, RR, RL`:

- preserve ACTUAL control on the other 9 joints;
- remove only that leg's P contribution on its 3 joints;
- separately remove only that leg's D contribution on its 3 joints;
- separately remove that leg's full PD contribution on its 3 joints.

### Per-joint ablations

For each of the 12 motors:

- remove only that joint's P contribution;
- remove only that joint's D contribution;
- remove only that joint's full PD contribution.

Use the repository's established motor order and label it explicitly.

## Additivity / interaction audit

Because constrained MuJoCo forward dynamics may be piecewise/nonlinear with contact constraints, do not assume:

`NO_PD effect = sum(per-joint PD removal effects)`

Check at minimum:

- global `NO_PD` versus `NO_P + NO_D` effect reconstruction;
- global `NO_P` versus sum of per-leg P removals;
- global `NO_D` versus sum of per-leg D removals;
- global `NO_PD` versus sum of four per-leg full-PD removals.

For each, report an interaction/additivity residual per snapshot and pooled median/p95 absolute residual.

If additivity residual is materially large, explicitly treat component ranking as context-dependent marginal effects rather than additive force decomposition.

## Stratification

Report all major branches over:

1. full `[31.90,33.00)` target interval;
2. contact mask, using replay contact mask;
3. gait phase bins:
   - `[0,0.25)`
   - `[0.25,0.5)`
   - `[0.5,0.75)`
   - `[0.75,1)`
4. optionally target subwindows if useful:
   - `[31.90,32.10)`
   - `[32.10,32.20)`
   - `[32.20,32.40)`
   - `[32.40,32.60)`
   - `[32.60,33.00)`

Do not over-fragment strata with tiny sample counts. Mark small-n strata rather than overinterpreting them.

## Primary outputs

For each global, leg, and joint ablation report at least:

- n;
- median `delta_ax`;
- p05 / p95;
- fraction `<0`;
- fraction `>0`;
- median absolute effect;
- contact/phase dependence.

For joint-level ranking, provide separate rankings for:

- P removal;
- D removal;
- full PD removal.

Ranking should be by robust instantaneous causal effect, not raw torque magnitude. Prefer median `delta_ax`; include variability/sign consistency so a large but phase-flipping joint is not mislabeled as universally dominant.

## Questions to answer

1. Is the aggregate forward/opposing-braking effect driven more by P or by D?
2. Which leg(s) dominate that effect?
3. Which joint(s) dominate it?
4. Are the dominant contributors consistent across contact masks/phases, or do they flip sign?
5. Can the prior `-1.617932 m/s^2` full-PD result be approximately reconstructed from component marginal effects, or are interactions large?
6. What is the **single smallest live intervention** that would best test the leading mechanism while minimizing gait-stability risk?

The last item is a recommendation only. Do not execute it.

## Interpretation rules

A component is a plausible contributor to residual overspeed only if its removal has a robust negative `delta_ax` in the relevant states. A component that flips sign strongly by phase/contact should be described as coordination-dependent, not globally bad.

Do not conclude that a component should simply be deleted from the controller. The earlier live pulse showed that full PD is important for gait stability.

The preferred endpoint is likely a phase/contact-aware coordination hypothesis, but do not force that conclusion if the data do not support it.

## Validation gates

Before interpreting decomposition results, verify:

- snapshot/atomic-record binding remains exact;
- ACTUAL replay qacc gate remains exact/tight;
- reproduced global `NO_PD` full-window median matches the prior checkpoint within numerical tolerance;
- no replay branch mutates shared state used by another branch.

If any gate fails, stop with `INCONCLUSIVE` and do not rank components.

## Output

Commit only a compact checkpoint containing:

`docs/validation/phase1_pd_component_decomposition_20260914/RESULTS.md`

`docs/validation/phase1_pd_component_decomposition_20260914/components.csv`

plus the minimal offline replay-tool/source changes needed for decomposition.

Raw atomic snapshots may remain local; record source hashes and exact analysis command.

`RESULTS.md` should state:

- validation-gate status;
- reproduced all-PD-off result;
- P versus D result;
- leg ranking;
- joint ranking;
- contact/phase sign flips;
- additivity/interaction residuals;
- one smallest recommended future live intervention, not executed.

Push one checkpoint and stop. Do not run any new simulator trajectory, parameter scan, gain tuning, controller fix, terrain, or Phase2 work.