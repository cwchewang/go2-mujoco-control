# Task: Phase1 command-lag matching before any new simulation

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first. Its constraints remain binding.

## Context

The previous same-state counterfactual replay checkpoint is `e6474211d4b60ffe9cb67786eafbc776f5c09935`.

That run established two important facts:

1. Restoring the saved MuJoCo integration state and replaying the snapshot's actual `ctrl` reproduces live `qacc[0]` exactly (`max residual = 0`). The saved MuJoCo state is therefore good enough for instantaneous dynamics replay.
2. The replay was not interpreted causally because controller-side LowCmd fields joined by nominally equal state tick failed to reconstruct the snapshot's actual bridge `ctrl` (`max error ≈45.97 Nm`, p95 ≈31.10 Nm). This strongly suggests that the command consumed by the bridge is temporally offset from the controller row used in the naive join.

The live-vs-replayed `ncon/nefc/contact-mask` mismatch is not, by itself, proof that the saved state is wrong: the snapshot was taken before `mj_step`, while `mj_forward` recomputes derived contact/constraint state. Do not use stale pre-forward contact summary as the primary replay-validity gate.

## Single question

Can each simulator snapshot's actual `ctrl` be explained by a recent controller LowCmd row after accounting for controller→DDS→bridge command latency?

If yes, use the matched command to complete the existing same-state PD counterfactual without any new live simulation.

If no, stop and recommend one atomic bridge-side logging run. Do not improvise a different experiment.

## Stage 1 — offline command-lag matching only

Use the existing raw artifacts from the `e647421` source run. Do **not** run MuJoCo during Stage 1.

For every target snapshot in active `[31.90,33.00)`:

- keep the exact saved MuJoCo integration state and snapshot `ctrl`;
- search controller/closure LowCmd rows from the recent **causal past only**;
- reconstruct the bridge command for each candidate using the snapshot's actuator-side state:

```text
ctrl_reconstructed_i = tau_ff_i
                     + kp_i*(q_des_i - q_snapshot_i)
                     + kd_i*(dq_des_i - dq_snapshot_i)
```

Use the same q/dq sensor semantics as the actual bridge. Confirm this from source before matching.

### Candidate search window

Start with controller rows whose source/state time is within 50 ms before the simulator snapshot. This is intentionally much wider than the nominal 2 ms loop period.

Do not search future controller rows. A future match is non-causal and invalid.

If the clocks have a fixed offset, estimate it once from the data and document it; do not manually tune row-by-row offsets except through the objective below.

### Matching objective

For each snapshot/candidate pair compute:

```text
max_abs_ctrl_error = max_i |ctrl_reconstructed_i - snapshot_ctrl_i|
L2_ctrl_error
```

Choose the causal candidate with minimum `max_abs_ctrl_error`; use L2 only as a tie-breaker.

Record for each snapshot:

- snapshot sim time / active time;
- matched controller row time / source state tick;
- command age / lag in ms;
- best max-abs residual;
- second-best residual and its lag;
- matched `q_des/dq_des/kp/kd/tau_ff`;
- snapshot actual `ctrl`.

## Match validation gate

Do not proceed to causal interpretation unless matching is objectively strong.

Preferred strong gate:

- at least 95% of target snapshots have `max_abs_ctrl_error <= 1e-5 Nm`;
- remaining rows, if any, have an explicit infrastructure/edge explanation and no materially different command candidate;
- lag distribution is physically plausible and concentrated rather than arbitrary row-to-row jumps.

If floating/log precision makes `1e-5` impossible but there is still a clear numerical floor, document the floor and justify any relaxed threshold before using it. Do not silently relax the gate.

Also report lag median, p05/p95, min/max, and histogram/counts by discrete controller tick if appropriate.

A stable one/few-tick DDS lag is a valid result. A highly multimodal/random lag with large residual is not.

## Stage 2 — same-state counterfactual, only if Stage 1 passes

For each validated matched snapshot:

### Actual branch

Restore the exact saved integration state and leave the snapshot's actual `ctrl` unchanged.

Run `mj_forward` only (or the exact same instantaneous operation used by the previous replay) and confirm:

```text
qacc_actual[0] == saved live qacc[0]
```

Maintain the previous stringent qacc replay gate.

### Counterfactual branch

Restore the same saved state again, then replace actuator control with the **matched command's `tau_ff` only**:

```text
ctrl_cf_i = matched_tau_ff_i
```

Do not alter qpos, qvel, warmstart, applied forces, contact state, model parameters, timestep, or any controller state. Do not integrate the counterfactual forward in time. This is an instantaneous same-state acceleration query only.

Run `mj_forward` and compute:

```text
delta_ax = qacc_cf[0] - qacc_actual[0]
```

Interpretation:

- `delta_ax < 0`: removing PD makes instantaneous x acceleration more braking / less propulsive at that exact state;
- `delta_ax > 0`: removing PD makes instantaneous x acceleration more propulsive / less braking;
- near zero: little instantaneous body-x effect.

This is a local instantaneous causal derivative, **not** a claim that tau_ff-only is a stable controller.

## Stratification

Because the previous unvalidated replay showed strong contact-mask dependence, report results both pooled and stratified by replay-derived physical contact topology.

At minimum report:

- full target `[31.90,33.00)`;
- `[31.90,32.10)`;
- `[32.10,32.20)`;
- `[32.20,32.40)`;
- `[32.40,32.60)`;
- `[32.60,33.00)`;
- dominant physical contact masks;
- gait phase bins if sign changes strongly with phase.

For each group report n, median delta_ax, p05/p95, fraction `<0`, fraction `>0`, and median absolute effect.

Also compare delta_ax with velocity error and with the ID/WBC requested braking state, but do not infer long-horizon tracking from one-step acceleration alone.

## Important validity rules

- Do not require pre-forward stored `ncon/nefc` to equal post-`mj_forward` derived values as a hard gate. Explain the phase-of-step distinction instead.
- Actual and counterfactual replay branches must start from the exact same saved state.
- The actual branch must continue to reproduce saved live `qacc[0]` to numerical tolerance.
- The matched LowCmd must reconstruct snapshot actual `ctrl` to the declared validation tolerance before its `tau_ff` may be used for counterfactual attribution.
- Do not use the naive same-state-tick controller row if another causal row is the actual numerical match.
- Do not run live PD-off or a PD pulse.
- Do not tune gains, period/duty, WBC/SRBD, contact logic, Raibert, governor, model, or acceptance thresholds.

## If Stage 1 fails

Do not run a new simulation automatically.

Stop with `INCONCLUSIVE` and specify the minimum next instrumentation:

Inside the simulator/bridge, under the same mutex and immediately before the real `mj_step`, atomically log:

- exact consumed LowCmd `q/dq/kp/kd/tau`;
- resulting actual `mj_data->ctrl[12]`;
- the exact integration state snapshot;
- simulator time / sequence number;
- contact summary with an explicit statement whether it is pre- or post-forward.

That future run must be ordinary-PD baseline only. But it is **not authorized in this task**.

## Outputs

Create a compact checkpoint under:

`docs/validation/phase1_command_lag_match_20260913/`

Required:

- `RESULTS.md`
- `lag_match.csv`
- if Stage 2 passes: `counterfactual_validated.csv`

Raw existing files may remain local; record hashes and run IDs.

`RESULTS.md` must answer, in order:

1. Did causal command-lag matching pass?
2. What is the measured controller→bridge lag distribution?
3. Can matched LowCmd reconstruct actual simulator `ctrl`?
4. If yes, what is the validated instantaneous PD contribution to base-x acceleration, pooled and by contact topology/phase?
5. Does the evidence support PD as an instantaneous contributor to overspeed, oppose that hypothesis, or show phase/contact-dependent mixed effect?
6. One next step only, not executed.

Use `SUPPORTED`, `NOT SUPPORTED`, `MIXED/CONTEXT-DEPENDENT`, or `INCONCLUSIVE` with precise scope. Do not call PD the sole root cause from this local replay.

Push one checkpoint and stop.