# Task: bridge-atomic PD counterfactual replay

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first. Its constraints are part of this task.

## Goal

Close the remaining logging boundary and answer one narrow question:

> At the same MuJoCo state during the known `varying 1.4→2.3` residual-overspeed window, what is the instantaneous base-x acceleration effect of the bridge-side joint PD contribution, compared with applying only the exact `tau_ff` consumed by the bridge?

Previous offline replay failed because controller CSV rows were not the exact LowCmd instance consumed by the bridge. Do **not** do more lag guessing.

## Starting point

Branch: `research/phase1-bridge-atomic-replay-20260913`

Base checkpoint: `2814b8a473e57063e70b5ab6174e27ae76053f7c`

Known facts:

- B semantic baseline is the current accepted diagnostic base.
- A normal-PD baseline reproduces the residual overspeed around active `[32,33)`.
- ID-WBC same-tick dynamics closure is numerically self-consistent.
- Live PD-off pulses destabilize the gait and cannot isolate the instantaneous body-x effect.
- Exact-state replay can reproduce live `qacc[0]`, but controller-log reconstruction of the bridge-applied `ctrl` failed because the logging boundary is asynchronous.

## This task has two stages

### Stage 1 — one bridge-atomic ordinary-PD A run

Run **exactly one** ordinary-PD `varying` baseline. No live PD-off pulse, no tau-ff-only live run, no parameter change.

Add minimal default-off diagnostic instrumentation so that the bridge and simulator expose the exact actuator command that is actually consumed/applied.

The diagnostic must be atomic with respect to the simulator mutex.

### Required bridge record

Inside `UnitreeSDK2Bridge::run()`, while holding the same simulation lock and the LowCmd mutex, immediately after computing/writing `mj_data_->ctrl[0:12]`, capture a monotonically increasing `bridge_ctrl_seq` and the exact values used for that write:

- simulator time visible at that bridge update;
- LowCmd `q[12]`;
- LowCmd `dq[12]`;
- LowCmd `kp[12]`;
- LowCmd `kd[12]`;
- LowCmd `tau[12]` (this is the consumed `tau_ff`);
- sensor q[12] used in the bridge PD expression;
- sensor dq[12] used in the bridge PD expression;
- resulting `ctrl[12]` actually written to `mj_data_->ctrl`.

The record must represent one internally consistent bridge update. Do not reconstruct these fields later from controller CSV.

### Required pre-step snapshot binding

In the simulator loop, under the same simulator mutex and immediately before the real `mj_step`, capture:

- full `mjSTATE_INTEGRATION` state as in the previous replay work;
- current simulator time;
- current `mj_data_->ctrl[12]`;
- the latest `bridge_ctrl_seq` and its full atomic bridge record;
- pre-step state/contact metadata needed for audit;
- after the real `mj_step`, the corresponding live `qacc[0]` as previously done.

Because bridge updates and pre-step snapshots share the same simulation mutex, the snapshot must bind to the latest bridge record whose `ctrl` is currently resident in `mj_data_->ctrl`.

It is valid for the same `bridge_ctrl_seq` to be reused by multiple consecutive simulator steps if the bridge has not updated again. Record this explicitly; do not force one-to-one controller/simulator rates.

### Mandatory atomic consistency checks

Before any counterfactual interpretation, prove for every target snapshot that:

1. `snapshot.ctrl[12]` equals the bound atomic bridge record's `ctrl[12]` to numerical precision;
2. bridge-record `ctrl[i]` equals the bridge formula evaluated from **that same atomic record**:
   `tau_ff + kp*(q_des-q_sensor) + kd*(dq_des-dq_sensor)`;
3. the restored ACTUAL replay using the snapshot state and snapshot actual `ctrl` reproduces the corresponding live `qacc[0]` within `1e-5 m/s²` (or tighter if naturally achieved);
4. snapshot/model signatures and sequence binding are unambiguous.

If any of these fail materially, stop and classify `INCONCLUSIVE`. Do not run another simulation and do not infer PD causality.

Do **not** require stale live pre-step `ncon/nefc` to equal a newly `mj_forward`-recomputed contact summary if the only difference is derived-state timing. The primary replay gate is exact state + actual ctrl → live qacc reproduction. Still record replay contact topology for stratification and confirm ACTUAL and CF start from the same restored state.

## Stage 2 — offline same-state counterfactual, only if Stage 1 passes

For each valid target snapshot in active `[31.90,33.00) s`:

1. Restore the exact same integration state into two independent `mjData` objects.
2. **ACTUAL branch:** set `ctrl` to the exact snapshot/bridge-applied `ctrl[12]`, then run the minimum MuJoCo forward computation required to obtain instantaneous `qacc[0]` without advancing the state.
3. **CF branch:** set `ctrl[i] = consumed_tau_ff[i]` from the **bound atomic bridge record**, leaving the entire state unchanged, then run the same forward computation.
4. Compute:
   `delta_ax = qacc_cf_x - qacc_actual_x`.

This removes only the bridge PD contribution from the actuator command at a fixed state. There must be no feedback of the CF branch into the real trajectory.

Also compute per snapshot:

- actual PD contribution per joint = `actual_ctrl - consumed_tau_ff`;
- actual and CF qacc_x;
- velocity error `measured-applied` from the nearest diagnostic state only for context; do not use controller CSV to reconstruct actuator command;
- gait phase;
- replay contact mask/topology;
- roll/pitch;
- bound `bridge_ctrl_seq` and how many simulator steps reused that sequence.

## Interpretation

Use the full `[31.90,33.00)` window and also report:

- `[31.90,32.10)`
- `[32.10,32.20)`
- `[32.20,32.40)`
- `[32.40,32.60)`
- `[32.60,33.00)`

Report median/p05/p95 `delta_ax`, fraction `<0`, fraction `>0`, and stratify at least by dominant replay contact mask. If phase dependence is strong, report it rather than averaging it away.

Interpret sign literally:

- `delta_ax < 0`: removing PD makes instantaneous x acceleration more negative; at that fixed state PD was contributing net forward acceleration / opposing braking.
- `delta_ax > 0`: removing PD makes instantaneous x acceleration more positive; at that fixed state PD was contributing net braking.

A mixed sign across contact topology/phase is an acceptable and potentially important result.

Do **not** claim PD is the sole root cause of residual overspeed from this test. This test only establishes the instantaneous same-state contribution of the bridge PD term.

## Fixed baseline

Do not change:

- B semantic mapping;
- period/duty;
- shaper/governor;
- Raibert/preview;
- SRBD/MPC;
- WBC gains/weights;
- gait/contact logic;
- model/scene;
- torque limits;
- profile;
- acceptance/safety thresholds.

The diagnostic flag must be default-off. Cache any environment flag outside hot control/simulation loops where practical. Instrumentation must not alter the control expression or timing semantics beyond unavoidable logging overhead.

## Run budget

One new ordinary-PD `varying` A run maximum.

A replacement run is allowed only for a clearly infrastructure-invalid launch that produced no usable simulation data (for example DDS participant startup failure). Do not retry a genuine controller/safety failure to obtain nicer data.

No live B run exists in this task.

## Outputs

Commit a compact checkpoint containing:

- `docs/validation/phase1_bridge_atomic_replay_20260913/RESULTS.md`
- `docs/validation/phase1_bridge_atomic_replay_20260913/counterfactual_atomic.csv`
- minimal diagnostic/replay source changes.

Raw binary snapshots may remain local; record run ID and SHA256 hashes.

`RESULTS.md` must answer, in order:

1. Did the atomic bridge/snapshot binding pass?
2. Did ACTUAL replay reproduce live qacc?
3. What is the validated instantaneous `delta_ax` of removing PD?
4. Is the sign consistent or contact/phase dependent?
5. Does this support PD as an instantaneous forward contributor, braking contributor, mixed contributor, or remain inconclusive?
6. One next step only, not executed.

Push one checkpoint and stop. Do not tune gains, modify WBC/SRBD/contact logic, run a live PD intervention, or expand into terrain/Phase2.