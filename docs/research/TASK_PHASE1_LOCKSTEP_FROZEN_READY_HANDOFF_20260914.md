# Phase1 task — frozen-state READY handoff

## Authority and scope

Base this task on checkpoint `e7c7c88edd4e461c7b819397d5038b7d8786e9b6` from the pre-motion startup experiment. Read `docs/research/PHASE1_AGENT_CONTRACT.md` first and obey it.

This is one infrastructure hypothesis only. Do not change gait/control math, WBC/SRBD/ID, gains, D4, scene, profile, timestep, safety thresholds, or physical acceptance criteria. Do not run D4. Do not add a fourth baseline. One checkpoint, then stop.

## Hypothesis

The remaining failure is the handoff gap between the deterministic simulator snapshot at tick 8000 and the controller's actual lockstep epoch. The simulator state itself was exactly reproducible at tick 8000, but controller handoff occurred at 9496 / 9090 / 9122 and L3 later hit tick-gap fail-closed.

If the simulator freezes permanently at the deterministic tick-8000 state, repeatedly publishes that same immutable state while the controller finishes natural-settle and capture, and advances only after an explicit controller READY for tick 8000 plus the first exact LowCmd/ack pair computed from that same tick, then all runs should enter active control from the identical physical state and identical control epoch.

## Stage 0 — source audit before edits

Audit the exact current call chain at `e7c7c88...` and record it in the result:

1. where the 4000-step zero-control pre-settle ends and the tick-8000 snapshot is serialized;
2. every path capable of calling `mj_step` after that point;
3. the bridge's LowState publication behavior while the plant is frozen;
4. controller ordering of subscriber startup, `WaitForNaturalSettle`, start-joint capture, world-reference capture, writer-thread start, writer-gate engagement, motion-clock epoch establishment, LowCmd publish, and lockstep ack;
5. the precise reason tick 8000 advanced to 9090–9496 before the controller's first gated publish in the previous checkpoint.

Do not infer this from logs alone. Establish the source-level reason before behavior edits.

## Stage 1 — minimal verification-only handshake

Implement the smallest explicit READY handshake that satisfies all of the following.

### Simulator side

- With the new verification mode enabled, perform the inherited deterministic 4000 zero-control MuJoCo steps and serialize the authoritative handoff state exactly as before.
- At tick 8000, freeze physics. From this point until the exact first control exchange completes, **no `mj_step` is allowed**.
- Re-publish the identical frozen LowState as needed for DDS delivery/natural-settle observation, always with state tick 8000. Republishing is not a physics step.
- Accept an explicit controller READY message only if it names the currently frozen state tick 8000. Stale/future/wrong READY must fail closed.
- READY alone must not step physics.
- After READY, accept the first exact LowCmd + lockstep ack pair only when both are causally bound to state tick 8000 under the existing command-sequence discipline.
- Only then permit exactly one `mj_step`, producing tick 8002, and continue the inherited one-state/one-command lockstep protocol.
- Timeouts or protocol ambiguity fail closed; do not silently fall back to wall-clock stepping.

### Controller side

- The controller must subscribe to the repeated frozen state before readiness.
- Complete the inherited natural-settle check and start-joint/world-reference capture while observing the frozen tick-8000 state.
- Immediately after capture, send explicit READY carrying the exact consumed frozen state tick.
- Establish the lockstep writer gate and motion-clock epoch on that same frozen tick **before any active writer cycle is allowed to publish**.
- The first writer cycle after READY must consume tick 8000 and publish exactly one LowCmd plus its exact ack pair for tick 8000.
- There must be no free-running LowCmd after the simulator enters the tick-8000 freeze.
- After handoff, duplicate frozen-state republishes must not trigger additional control updates.

The READY channel/message is verification metadata only. Keep flag-off production behavior unchanged. Reuse existing lockstep metadata/message conventions where practical; do not redesign transport or controller architecture beyond what is required for this handshake.

## Stage 2 — tests before live runs

Add focused tests that prove at minimum:

- frozen state stays at tick 8000 for arbitrarily many repeated publishes before READY;
- no physics step is granted by READY alone;
- wrong/stale/future READY fails closed;
- first valid READY + exact LowCmd/ack for 8000 grants exactly one step to 8002;
- controller READY is emitted only after capture and before writer publication;
- first gated control update consumes 8000 exactly once;
- duplicate tick-8000 republishes do not create extra updates;
- subsequent ticks remain 2 ms, one update each;
- verification flag OFF preserves legacy behavior.

Run the relevant simulator and controller test suites. If Stage 2 fails, fix only this handshake and rerun tests; do not launch baselines until tests pass.

## Stage 3 — exactly three frozen baseline launches

Run exactly L1, L2, L3 sequentially using the same frozen Phase1 varying-profile baseline used in the previous checkpoint, D4 OFF, fixed CPU affinity, clean source tree, distinct DDS domains. Do not run a fourth attempt regardless of outcome.

Capture enough evidence to audit the freeze/READY/first-command transition directly, not just infer it from ordinary data.csv. At minimum report per run:

- authoritative frozen-state hash and full qpos/qvel equality checks;
- simulator freeze tick;
- controller captured tick;
- READY tick;
- first gated writer-consumed tick;
- first LowCmd state tick and command sequence;
- first matching ack pair;
- first post-command simulator tick;
- count of `mj_step` between snapshot and valid first command (must be zero);
- count of LowCmd publishes after freeze but before READY (must be zero);
- post-handoff command delta histogram, protocol violations, fail-closed markers.

## Gates and decision

All three runs must independently satisfy:

1. authoritative handoff state identical across L1/L2/L3, with the inherited <=1e-12 numeric equality gate and identical binary hash;
2. simulator freeze tick = controller captured tick = READY tick = first gated consumed tick = first LowCmd/ack state tick = **8000**;
3. first simulator state after the accepted exact command = 8002;
4. zero `mj_step` between freeze and accepted first exact command;
5. zero LowCmd publishes between freeze and READY;
6. post-handoff dt exactly 2 ms, command delta exactly 1, zero duplicate active updates, zero protocol violations, no fail-closed;
7. inherited physical baseline gates PASS for all three runs;
8. `[32,33)` excess-median range across runs <= 0.010 m/s;
9. no sustained pairwise divergence before active-relative 40 s using the same preregistered divergence definition from the previous determinism task.

Decision labels:

- `READY_FOR_CAUSAL_AB`: every gate above passes.
- `FROZEN_HANDOFF_PROTOCOL_FAIL`: any freeze/READY/first-command protocol gate fails.
- `FROZEN_HANDOFF_PHYSICAL_FAIL`: protocol passes but any inherited physical baseline gate fails.
- `FROZEN_HANDOFF_STILL_NONDETERMINISTIC`: protocol and physical gates pass but reproducibility gates 8–9 fail.

Do not weaken or invent thresholds after seeing results.

## Stop rule

After L1/L2/L3 analysis, write one concise `RESULTS.md`, commit all source/test/derived evidence appropriate for the repository, push one checkpoint, verify worktree clean and remote SHA, then STOP. Do not run D4, do not tune, do not start another infrastructure experiment, and do not autonomously choose a follow-up hypothesis.