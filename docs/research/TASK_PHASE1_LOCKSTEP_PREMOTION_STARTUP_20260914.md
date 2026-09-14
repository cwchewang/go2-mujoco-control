# TASK: Phase1 pre-motion lockstep startup determinism — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` completely before doing anything. Execute this task exactly once, produce one auditable checkpoint, push it, then stop. Do not continue to D4 or any follow-up experiment.

## Starting point

Branch: `research/phase1-lockstep-premotion-startup-20260914`
Base checkpoint: `6db6f0269d9b71fb19ad53c48eb99d41c0d5086a`.

Established evidence from the immediately preceding checkpoints:

- Wall-clock Phase1 baselines are not reproducible enough for a ±0.03 m/s causal A/B.
- Current lockstep post-engagement protocol is clean: fixed 2 ms physics tick, zero protocol violations, no fail-closed, exact one command update per state tick after the writer gate is engaged.
- The prior apparent `delta>1` problem was entirely pre-engagement free-running traffic; there were zero post-engagement duplicate same-tick writes.
- In checkpoint `6db6f026...`, all three lockstep baselines passed protocol and physical gates and `[32,33)` excess range was only `0.003281964 m/s`, but trajectories still showed sustained divergence before 40 s.
- The first gated publish occurred at nearly identical controller running time (~4.302 s) but different simulator ticks: L1=3950 ms, L2=4074 ms, L3=3486 ms. The current lockstep coordinator explicitly preserves wall-clock startup until the first controller command, and the controller writer gate currently becomes authoritative only later in lifecycle.

Do not reinterpret any earlier D4 result in this task.

## Research question

Does the remaining lockstep baseline divergence come from entering the deterministic control phase from different pre-motion physical states / lifecycle timing?

Hypothesis:

> If verification-only lockstep is established before the first active stand-up / locomotion control motion, with a reproducible frozen physical handoff state and state-tick-driven control from the first active command onward, then repeated Phase1 baselines should no longer show sustained trajectory divergence before 40 s.

This is a verification-infrastructure task, not a controller-tuning task.

## Scope boundaries

Allowed:

- source audit of simulator/controller startup, natural-settle, first LowCmd, ready barrier, lockstep handoff, writer gate, and motion clock;
- verification-only changes needed to create a deterministic pre-motion startup/handoff;
- deterministic simulator pre-roll / pre-settle under `SIM_LOCKSTEP` if and only if needed, provided progression is by exact simulation steps or another deterministic simulation-state rule, never by wall-clock elapsed time as truth;
- moving the verification writer-gate/epoch boundary earlier so the first active command after handoff is already state-tick driven;
- diagnostics required to prove the exact handoff state and first active command pairing;
- unit/integration tests for the verification path and flag-off invariance;
- exactly three sequential frozen baseline launches after implementation.

Forbidden:

- D4 or any other A/B intervention;
- gait, WBC, SRBD, ID-WBC, PD, gains, thresholds, velocity profile, scene, model, timestep, contact logic, safety rules, or analyzer acceptance changes;
- changing the normal wall-clock runner behavior when lockstep verification is disabled;
- choosing a favorable initial pose manually per run;
- resetting the robot after the controller has captured a different start pose;
- using run-specific timing offsets or run-specific startup parameters;
- a fourth launch, retry, gain scan, or follow-up experiment.

If deterministic pre-motion handoff cannot be achieved without changing controller semantics or the physical benchmark, stop and report the blocker instead of improvising.

## Stage 0 — exact lifecycle audit

Before editing behavior, trace and document the exact current sequence from process launch through the first gated control update:

1. simulator model/data creation and initial physics progression;
2. DDS bridge-ready marker;
3. controller subscriber setup;
4. `WaitForNaturalSettle`;
5. start-joint-position capture and world-reference capture;
6. writer-thread start;
7. first production LowCmd;
8. simulator ready-barrier completion;
9. lockstep ack/epoch establishment;
10. writer-gate engagement;
11. stand-up / gait start.

Identify every portion whose progression depends on wall-clock scheduling or asynchronous DDS arrival. Explicitly identify the earliest point at which the physical plant can be frozen and the controller can begin from a reproducible state without changing control math.

Record the audit in `RESULTS.md` even if implementation later fails.

## Stage 1 — implement one verification-only pre-motion deterministic handoff

Implement the smallest coherent mechanism that satisfies all of the following invariants.

### A. Reproducible physical handoff state

Before the first active stand-up/motion control update, the simulator must reach a handoff state by deterministic simulation progression, not by a variable number of wall-clock physics steps.

A deterministic pre-settle/pre-roll is permitted if required. If used:

- it must be identical across all runs;
- its progression must be expressed in exact simulation steps / simulation time or a deterministic state rule;
- no controller motion command may influence the pre-settle plant;
- the same scene/model and authored initial condition remain in force;
- do not introduce randomization.

The simulator must emit an auditable handoff record containing at minimum simulation tick and the full floating-base qpos/qvel plus actuated joint q/dq (or an equivalent exact simulator-state hash plus a numeric state vector sufficient to audit equality).

The controller must capture its start pose/reference from that same frozen handoff state. Do not reset or alter the simulator state after the controller captures it.

### B. State-tick control from the first active command

Once the handoff occurs, there must be no free-running active control phase before writer-gate authority.

The first active stand-up/motion LowCmd after the handoff must be associated with the frozen handoff state, and every subsequent active update must be exactly one controller update per strictly new physics state tick.

Do not wait until `task_.gait_started_` to make state-tick scheduling authoritative if doing so leaves a free-running stand-up interval. The verification-only epoch/handoff may be moved earlier, but flag-off behavior must remain unchanged.

### C. Causal lockstep invariants retained

Retain the validated exact-pair causal protocol:

- exact `{state_seq, command_seq}` matching;
- one `mj_step` only after the exact command/ack pair for the frozen state;
- exact 2 ms tick progression;
- stale/future/timeout fail-closed behavior;
- duplicate republish of the same frozen state must not cause an additional controller update;
- simulator trace and controller diagnostics remain auditable.

Do not regress to an older simplified lockstep implementation.

## Stage 2 — tests before launches

Run the existing relevant simulator/controller lockstep tests plus new focused tests required by the change.

At minimum prove:

1. lockstep disabled => legacy/wall-clock behavior path is unchanged;
2. pre-motion verification handoff happens before the first active stand-up/motion update;
3. the first active command consumes the recorded frozen handoff state;
4. after handoff, duplicate frozen-state republishes cannot trigger a second LowCmd update;
5. exactly one control update occurs for each strictly new tick;
6. motion time is state-tick based after handoff;
7. stale/future/reordered/missing handshake cases still fail closed.

If tests fail, do not launch the three baselines. Report and stop.

## Stage 3 — exactly three frozen baseline launches

If and only if Stage 2 passes, build simulator/controller once and freeze the binaries. Launch exactly three sequential Phase1 `varying` baselines, L1/L2/L3, with:

- D4 OFF and all prior A/B flags OFF;
- same profile, scene, model, period `0.14`, duty `0.44`, WBC-full and all existing Phase1 parameters;
- fixed CPU affinity;
- fresh processes;
- distinct valid DDS domains;
- the new pre-motion lockstep verification path ON;
- publish/handoff diagnostics ON only as needed for audit.

No fourth launch under any outcome.

Record source SHA, dirty state, simulator/controller SHA256, scene/profile SHA256, exact commands, run IDs, domains, raw-file hashes, and handoff-state hashes.

## Pre-registered gates

### 1. Protocol gate — every run must pass

After the deterministic handoff:

- lockstep trace present;
- exact tick delta = `2 ms` throughout;
- protocol violations = 0;
- no fail-closed marker;
- ack state matches published state;
- exchange trigger is exact matched command/ack;
- one and only one controller update per physics tick;
- zero same-tick duplicate active LowCmd updates.

Pre-handoff diagnostics may exist but no active stand-up/motion command is allowed before the deterministic handoff.

### 2. Handoff-state identity gate — every pair must pass

Compare L1/L2/L3 at the exact recorded handoff.

Preferred criterion: identical exact simulator-state SHA256 when serialized in a stable binary representation.

Also report numeric pairwise maxima. Require:

- max absolute qpos difference <= `1e-12` in simulator double precision;
- max absolute qvel difference <= `1e-12`;
- actuated joint q/dq differences <= `1e-12` where represented as simulator doubles.

If a transport/log representation is float-limited, use the simulator-side double state as authority and report transport quantization separately. Do not loosen the simulator-state criterion after observing results.

### 3. Physical baseline gate — every run must pass

Use the same Phase1 physical gate as the previous checkpoint:

- active-relative time >= 40 s;
- no hard safety stop before 40 s;
- continuous-trot in `[32,33)`;
- median measured-minus-applied velocity excess in the established residual-overspeed range `[+0.15,+0.35] m/s`;
- median WBC desired ax < 0;
- median SRBD ax < 0;
- median ID qdd-x < 0.

Do not weaken these conditions.

### 4. Endpoint reproducibility gate

For `[32,33)` median velocity excess across L1/L2/L3:

`max - min <= 0.010 m/s`.

### 5. Trajectory determinism gate

Align only by simulation/active-relative time after deterministic handoff; wall-clock timestamps are not truth.

Use the same sustained-divergence locator as checkpoint `6db6f026...`:

- forward measured-velocity pairwise difference > `0.05 m/s`, OR
- absolute roll or pitch pairwise difference > `2 deg`,
- sustained for >= `100 ms`.

Gate requirement: **no pair may show sustained divergence before active-relative 40 s**.

Report p50/p95/max pairwise differences for at least measured velocity, applied velocity, velocity excess, roll, pitch, physical contact count/mask, controller contact mask, and gait phase.

## Decision labels

Use exactly one primary label:

- `READY_FOR_CAUSAL_AB` — all protocol, handoff-state identity, physical, endpoint reproducibility, and trajectory determinism gates pass.
- `HANDOFF_STATE_NOT_IDENTICAL` — protocol may work, but the physical handoff state is not reproducible.
- `LOCKSTEP_PROTOCOL_FAIL` — causal/tick/update protocol fails.
- `PHYSICAL_BASELINE_FAIL` — protocol/handoff are valid but the inherited baseline no longer reaches the required regime safely.
- `LOCKSTEP_BASELINE_STILL_NONDETERMINISTIC` — protocol, handoff identity, physical, and endpoint gates pass but sustained trajectory divergence still appears before 40 s.
- `BLOCKED` — the required pre-motion handoff cannot be implemented without changing controller/benchmark semantics.

Do not use D4 evidence to choose the label.

## Deliverables

Commit at least:

- `docs/validation/phase1_lockstep_premotion_startup_20260914/RESULTS.md`
- `docs/validation/phase1_lockstep_premotion_startup_20260914/handoff_states.csv`
- `docs/validation/phase1_lockstep_premotion_startup_20260914/protocol_gates.csv`
- `docs/validation/phase1_lockstep_premotion_startup_20260914/run_summary.csv`
- `docs/validation/phase1_lockstep_premotion_startup_20260914/pairwise.csv`

Keep large raw traces in `_runs/` and record SHA256/provenance in `RESULTS.md`.

## Stop rule

After one checkpoint is produced and pushed, stop. Do not run D4, do not tune startup duration after seeing outcomes, do not add a fourth baseline, and do not automatically attempt a follow-up fix.

End `RESULTS.md` with exactly one recommended next step, not executed.