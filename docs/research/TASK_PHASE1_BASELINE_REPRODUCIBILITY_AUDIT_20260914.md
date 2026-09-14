# TASK: Phase1 baseline reproducibility audit — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` completely before doing anything. This task is a closed diagnostic checkpoint. Complete the authorized work, write one checkpoint, push it, and stop. Do not automatically continue into D4, controller tuning, or a follow-up experiment.

## Why this task exists

The previous D4 replication could not begin causal testing because the unchanged A baseline physically failed at active-relative `29.020011491 s`, with roll near `-179.88 deg`, before the required 2.3 m/s window. Earlier runs of the same Phase1 lineage reached 80 s and reproduced the residual-overspeed regime. Before interpreting any further live A/B, determine whether the baseline trajectory is reproducible under frozen execution conditions.

This task does **not** test D4. `TROT_BOUNDED_STANCE_DQ_D4_AB` must remain disabled for every launch.

## Research question

Under one frozen source tree, one frozen pair of simulator/controller binaries, one frozen scene/profile, fixed CPU placement, fresh-process startup, and otherwise identical commands, does the unchanged Phase1 varying-profile baseline reproducibly reach the 2.3 m/s regime with similar behavior, or does it materially diverge / intermittently fail?

A secondary diagnostic question is what deterministic or nondeterministic mechanism is actually available on this path: explicit RNG/seed, startup-state variation, wall-clock controller/simulator timing, DDS/thread scheduling, or another source visible from existing logs/source.

## Scope

Allowed:

- source/read-only audit of the benchmark launch path and controller/simulator timing path;
- comparison against the already committed successful and failed A evidence;
- building once if necessary, then freezing and hashing the binaries;
- exactly **three new baseline launches**, sequentially, using the same frozen binaries and command;
- lightweight analysis scripts that do not alter runtime behavior;
- diagnostics derived from existing logs/CSV/metadata.

Forbidden:

- D4 or any other stance-dq intervention;
- gait/gain/governor/WBC/ID/contact/control changes;
- adding synchronization, lockstep, artificial sleeps, seed plumbing, reset behavior, or any other runtime behavior change;
- parameter scans;
- more than three new launches;
- Phase2/terrain work;
- starting a follow-up experiment after this checkpoint.

This task explicitly authorizes completing all three baseline launches even if one physical run hard-fails, because failure frequency/reproducibility is the dependent variable. Stop early only for an infrastructure fault that makes the remaining launches invalid (stale simulator, corrupted binary, failed build, lock failure, missing files, etc.).

## Stage 0 — execution-path audit before launching

Audit the exact path used by:

`example/cpp/scripts/run_phase1_velocity_benchmark.sh varying ... 232`

and `run_trot.sh`, plus the relevant controller/simulator startup/timing code.

Document, with source locations:

1. Whether any RNG affects this exact Phase1 varying-profile path. Search `TROT_SEED`, `RUN_SEED`, `rand`, `srand`, C++ random engines/distributions, MuJoCo noise/randomization hooks, and scene randomization. Do **not** treat a seed written only to metadata as a functional seed.
2. Exact initial-state/reset behavior for simulator and controller.
3. Whether the benchmark uses wall-clock motion and independent simulator/controller processes/threads; identify any asynchronous DDS/update loops that can change command/state tick alignment.
4. CPU affinity actually selected by `TROT_CPU_AUTOPIN=1`; record the concrete simulator/controller CPUs on this host.
5. Any relevant real-time/sleep/startup-ready behavior between simulator-ready and controller start.
6. Compare the prior successful A (`varying_20260914_103232`, checkpoint `e65c8830905c2c744c85d82ec08c3e4b7f6989c4`) and failed A (`varying_20260914_105519`, checkpoint `7a1da59704c49624fc26c7c5e71681e6a519d5a4`): source hashes, scene/profile hashes, environment, CPU affinity, binary SHA256, and metadata. Explain any binary-hash differences without assuming they imply behavior changes. If build IDs/timestamps make byte hashes nondeterministic, say so and use the newly frozen binaries for the three-run audit.

Do not modify code to create a seed or lockstep mechanism. If there is no functional RNG in the path, explicitly conclude that "fixing the seed" is not an available causal control and move on to freezing the actual execution conditions.

## Stage 1 — freeze the audit configuration

Use the current branch source with D4 disabled. Build only if necessary **before** Run 1. Once Run 1 is about to start:

- do not rebuild between runs;
- hash controller and simulator binaries and require identical hashes for Runs 1–3;
- hash scene and varying profile and require identical hashes;
- use the same explicit CPU affinity for all three runs. Prefer the exact CPUs that current autopin resolves to, but set them explicitly via the existing affinity environment variables so the values cannot change between launches;
- use the same DDS domain `232`, sequential launches only, and verify no stale simulator/controller before each launch;
- use fresh run directories;
- leave D4 disabled explicitly;
- keep `TROT_DIAG_ID_CLOSURE=1` as in the recent baseline work;
- do not introduce environment variables that have no proven runtime effect merely to make metadata look fixed.

Record a single canonical command template and the exact environment shared by all three runs.

## Stage 2 — exactly three identical A runs

Run three sequential baseline `varying` launches with the frozen configuration. Label them A1, A2, A3.

The intent is reproducibility, so do not stop after a physical failure. Complete A1/A2/A3 unless an infrastructure fault invalidates the experiment.

For each run record:

- run ID;
- controller/simulator/scene/profile SHA256;
- statuses and strict analyzer result;
- active-relative duration;
- whether/when hard safety occurred and the hard-safety reason;
- max |roll|, max |pitch|, minimum base height;
- measured/applied/excess medians for the common velocity windows that exist;
- if `[32,33)` exists: measured, applied, excess, realized ax, WBC desired ax, SRBD ax, ID qdd-x, and negative fractions;
- contact summary and torque-saturation fraction if already available from existing outputs.

Do not classify a run that fails before a window as having an endpoint value.

## Stage 3 — trajectory divergence audit

Use only existing data from the three new runs plus the two prior A runs named above. No new launch.

Align new runs by active-relative time. At minimum compare A1/A2/A3 over their common valid prefix for:

- measured forward velocity;
- applied velocity;
- velocity excess;
- roll and pitch;
- controller contact mask / physical contact count if available;
- gait phase if available.

Report pairwise time-series differences on a fixed common grid or nearest-time join with a stated maximum time tolerance. Include median/p95 absolute differences, not just endpoint medians.

Find the earliest meaningful divergence among A1/A2/A3. Use a descriptive threshold chosen **before looking at the late failure result** in the analysis script/report, such as the first sustained interval where either forward-velocity difference exceeds `0.05 m/s` or roll/pitch difference exceeds `2 deg` for at least `100 ms`. The threshold is for locating divergence, not an acceptance gate; clearly label it descriptive.

If a run hard-fails, inspect the several seconds before failure and state whether divergence is already visible well before the final posture collapse.

## Pre-registered reproducibility classification

Classify the three-run baseline audit using these rules.

### `REPRODUCIBLE_PASS_REGIME`

All three new runs:

- reach active-relative at least 40 s without hard safety;
- remain continuous-trot through `[32,33)`;
- `[32,33)` median velocity excess lies in the existing baseline-gate band `[+0.15,+0.35] m/s`;
- WBC desired ax, SRBD ax, and ID qdd-x medians in `[32,33)` are negative;
- range across A1/A2/A3 of `[32,33)` median velocity excess is `<= 0.03 m/s`.

This means the baseline is reproducible enough to resume a paired D4 test. It does not mean the controller is good.

### `REPRODUCIBLE_FAILURE_REGIME`

All three new runs physically hard-fail, and the failure timing/mechanism is closely clustered: active-relative hard-failure times span `<= 2.0 s`, with the same primary hard-safety class. This means the current frozen baseline has a reproducible stability failure and D4 testing remains blocked.

### `NONREPRODUCIBLE_BASELINE`

Anything materially mixed, including:

- some new runs reach the gate and others hard-fail;
- all reach the gate but `[32,33)` excess range is `>0.03 m/s`;
- failures differ substantially in time/mechanism;
- large trajectory divergence occurs under the frozen binaries/affinity before the gate.

### `INFRASTRUCTURE_INVALID`

Only if an infrastructure fault invalidates the frozen-run protocol itself. Do not use this label for a physical robot/simulation posture failure.

## Interpretation rules

- Do not blame RNG unless functional RNG is actually present on this path.
- Do not call differing binary SHA256 across historical builds a cause by itself. The three new runs must use the exact same frozen binaries.
- Do not infer that wall-clock/DDS scheduling is causal merely because it exists. If the three frozen runs diverge, it becomes a leading mechanism; identify the earliest evidence and what would be required to test it next.
- Do not reinterpret the prior D4 live result as supported or rejected.
- Do not tune the baseline to make the audit pass.

## Required deliverables

Create:

`docs/validation/phase1_baseline_reproducibility_audit_20260914/RESULTS.md`

and compact derived CSV(s) sufficient to audit the three-run comparison. Keep raw runs under the normal `_runs` location and record hashes/provenance.

`RESULTS.md` must contain:

1. source-level nondeterminism/timing audit;
2. frozen binary/environment provenance;
3. A1/A2/A3 run table;
4. `[32,33)` comparison where available;
5. pairwise trajectory-difference and earliest-divergence summary;
6. one of the four classification labels above;
7. exactly one recommended next step, **not executed**.

Push one checkpoint and stop.