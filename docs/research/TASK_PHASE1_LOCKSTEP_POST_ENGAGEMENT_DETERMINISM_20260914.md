# TASK — Phase1 post-engagement lockstep determinism

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first and obey it. Execute exactly one checkpoint, then stop.

## Purpose

Checkpoint `522d38e47c770f6a087b2113c6f7da1f10bb447b` established that every observed `delta>1` LowCmd interval was `PRE_ENGAGEMENT_ONLY`: the controller was still in the free-running lifecycle before the lockstep writer gate took authority. Post-engagement same-state duplicate publishes were zero; there was no second production publication path and simulator accounting joined losslessly.

This task changes only the **verification/accounting boundary** and re-tests baseline determinism. It must not change locomotion/control behavior.

## Fixed hypothesis

Once strict one-command-per-state accounting begins at the first production publish for which the lockstep writer gate is actually engaged, the Phase1 varying-profile baseline will satisfy the lockstep protocol and become sufficiently reproducible for a causal D4 A/B.

## Allowed changes

You may change only verification/harness/analysis code needed to:

1. identify the first `gate=1` / gated-writer production publish unambiguously;
2. exclude all earlier free-running lifecycle intervals from the strict `one_command_update_per_state_tick` gate;
3. retain those pre-engagement intervals as separately reported audit data;
4. analyze three frozen post-engagement baseline runs.

The existing publish diagnostic may be retained or minimally adapted. Diagnostic-only changes must be default-off outside this lockstep harness.

## Forbidden changes

Do not change controller math, gait parameters, WBC/SRBD/ID behavior, PD gains, D4, velocity shaper/governor, safety limits, scene, profile, MuJoCo model, timestep, DDS semantics, lockstep causal handshake, writer-gate behavior, motion-clock behavior, or physical acceptance thresholds. Do not run D4. Do not tune anything after seeing results.

## Protocol boundary

The strict post-engagement interval set begins only after the controller has made its first production LowCmd publish with the lockstep writer gate engaged (`gate=1`, gated writer branch). The exact boundary must be derivable from emitted audit data and documented.

For intervals before this boundary:
- report command-delta counts and duration;
- do **not** use them in `one_command_update_per_state_tick` PASS/FAIL.

For every interval at or after this boundary, require all of:
- constant simulator tick increment of exactly 2 ms;
- zero lockstep protocol violations;
- no `SIM_LOCKSTEP_FAIL_CLOSED` marker;
- ack state sequence equals the frozen published simulator tick;
- matched exchange trigger is the expected exact-pair trigger;
- command-arrival delta is exactly `1` for every included interval;
- no controller same-state duplicate publish after engagement.

Any post-engagement interval with command delta other than 1 is a protocol FAIL. Do not waive it.

## Execution

Build the required simulator/controller/analyzer targets once from a clean tree, then freeze the binaries for the launches.

Run exactly three sequential baseline launches, `L1`, `L2`, `L3`, using:
- Phase1 `varying` profile;
- running-trot, WBC-full;
- period `0.14 s`, duty `0.44`;
- D4 OFF and all prior experimental A/B flags OFF;
- same scene/profile and existing Phase1 lockstep handshake;
- fixed CPU affinity as in the preceding determinism checkpoint;
- distinct DDS domains;
- identical environment and command except run name/domain.

Do not add a fourth run.

## Physical baseline gate

Each run must:
- reach at least active-relative 40 s;
- have no hard safety stop before 40 s;
- remain continuous-trot through `[32,33)`;
- contain the normal residual-overspeed/braking-demand regime in `[32,33)` (report measured, applied, excess, WBC desired ax, SRBD ax, ID qdd-x).

A physical failure is reported separately from protocol failure; do not hide it.

## Determinism analysis

Align only **post-engagement** controller data by active-relative/control time without using wall-clock timestamps as truth.

For `L1/L2/L3`, report:
- `[32,33)` median measured velocity, applied velocity, and velocity excess;
- range of the three median velocity-excess values;
- pairwise p50/p95/max absolute differences for measured velocity, applied velocity, velocity excess, roll, pitch, contact count/mask, and gait phase over the common post-engagement prefix;
- first sustained divergence time using the already used locator: measured-velocity difference `>0.05 m/s` OR roll/pitch difference `>2 deg` continuously for `100 ms`.

Pre-registered determinism gate:
1. all three post-engagement protocol gates PASS;
2. all three physical baseline gates PASS;
3. `[32,33)` median velocity-excess range across L1/L2/L3 is `<=0.01 m/s`;
4. no pair has a sustained divergence by the above locator before active-relative `40 s`.

If all four pass, classify exactly `READY_FOR_CAUSAL_AB`.
If protocol passes but determinism gate 3 or 4 fails, classify `LOCKSTEP_BASELINE_STILL_NONDETERMINISTIC`.
If any post-engagement protocol gate fails, classify `LOCKSTEP_PROTOCOL_FAIL`.
If a physical baseline gate fails before the determinism decision is available, classify `BASELINE_PHYSICAL_FAIL`.

Do not relax thresholds after results.

## Required deliverables

Create:
- `docs/validation/phase1_lockstep_post_engagement_determinism_20260914/RESULTS.md`
- `protocol_gates.csv`
- `run_summary.csv`
- `pairwise.csv`
- any minimal derived boundary/audit CSV needed to prove the first engaged publish and pre/post interval counts.

Record source SHA, branch, binary/input SHA256, exact commands/run IDs, protocol boundary, raw artifact hashes, and whether the tree was clean at launch.

## Stop rule

After the three authorized baseline launches and analysis, commit/push exactly one checkpoint and stop. Do not run D4, do not start another baseline, and do not implement the next experiment. End `RESULTS.md` with exactly one recommended next step, not executed.