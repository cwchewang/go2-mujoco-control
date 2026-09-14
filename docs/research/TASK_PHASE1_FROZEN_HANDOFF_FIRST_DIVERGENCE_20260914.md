# Phase 1 frozen-handoff first-divergence checkpoint — 2026-09-14

## Authority and scope

This checkpoint follows `docs/research/PHASE1_AGENT_CONTRACT.md`.

- Base commit: `b0921380ca4507bdb08227d8453bde654198cee9`
- Working branch: `research/phase1-frozen-handoff-first-divergence-20260914`
- Prior checkpoint: `TASK_PHASE1_LOCKSTEP_FROZEN_READY_HANDOFF_20260914.md`
- D4 / bounded stance `dq_des` intervention: **OFF for every run in this checkpoint**.
- No controller tuning, gait retuning, solver retuning, or mainline integration is authorized by this task.

## Problem statement

The prior checkpoint established a bitwise-identical frozen READY handoff at physics tick 8000 across repeated runs, while post-release physical trajectories still diverged. The present task is therefore not to improve performance. It is to identify the earliest post-handoff causal boundary at which repeated runs cease to be identical.

## Preregistered hypothesis

H1: with an identical frozen handoff state, the first repeatability failure is observable at one of these ordered boundaries:

1. controller input / published LowState;
2. controller output / LowCmd and lockstep acknowledgement;
3. bridge-applied actuator control (`mjData.ctrl`);
4. MuJoCo integration state / contact-constraint evolution after `mj_step`.

The checkpoint succeeds if the earliest differing boundary and tick can be identified reproducibly. It does **not** require the divergence to be fixed in the same task.

## Required invariants

Before interpreting any divergence, all compared runs must satisfy:

- exact source commit and branch provenance recorded;
- frozen READY handoff occurs at tick 8000;
- frozen handoff integration state is bitwise identical across compared runs;
- same model/configuration, speed script, lockstep settings, environment and binary build;
- exactly one authorized command writer;
- no D4 or other causal intervention enabled;
- raw artifacts are immutable after capture.

If any invariant fails, stop that comparison and report a protocol failure rather than a causal conclusion.

## Instrumentation strategy

Prefer existing instrumentation and avoid changing controller or simulator semantics. The existing `CounterfactualSnapshotLogger` in `simulate/src/main.cc` already records per eligible physics step:

- `mjSTATE_INTEGRATION` snapshot;
- pre-step simulation time, qvel[0], ncon, nefc and contact mask;
- atomic bridge record including command sequence;
- command fields for all motors: q, dq, kp, kd, tau_ff;
- sensor q and dq used by the bridge;
- bridge-computed ctrl and the actual `mjData.ctrl` snapshot;
- post-step qacc[0].

The first implementation should therefore add only an offline decoder/comparator and, only if evidence remains ambiguous, minimal extra logging at a missing causal boundary.

## Run matrix

### Stage A — shortest-window paired capture

Run three baseline repetitions using the exact frozen READY protocol. Capture snapshots only in an early post-release window. Start with a 5.0 s maximum post-release window; if the first divergence is found earlier, analysis may stop there.

The runtime window must be identical for all repetitions. Do not substitute failed runs or silently rerun individual repetitions.

### Stage B — targeted boundary expansion

Only if Stage A shows that the integration state diverges but existing fields cannot identify whether the source is controller-side or simulator-side, add the smallest extra observable needed and repeat the same matrix once.

Examples of authorized additions, in order of preference:

1. exact LowState payload hash / values observed by the controller for each acknowledged state tick;
2. exact LowCmd payload hash immediately before publish;
3. post-`mj_step` integration-state hash and selected solver/contact metadata.

Do not instrument WBC internals unless controller input is identical while LowCmd differs.

## Offline comparison method

For each pair of runs, align records by frozen-handoff-relative physics tick / record index, not by wall-clock time.

For each aligned record compare, in causal order:

1. integration-state bytes before step;
2. bridge command sequence and full motor command tuple `(q,dq,kp,kd,tau_ff)`;
3. bridge sensor q/dq;
4. bridge-computed ctrl;
5. actual `mjData.ctrl`;
6. ncon, nefc and contact mask;
7. next integration state.

Report the first record where any category differs and the earliest differing scalar/byte location for that category.

## Classification rules

Use the earliest supported classification only:

- `INPUT_OR_TRANSPORT_DIVERGENCE`: simulator state is still identical but controller-observed state/input differs before command generation.
- `CONTROLLER_DIVERGENCE`: controller inputs are identical but LowCmd differs.
- `BRIDGE_DIVERGENCE`: LowCmd is identical but bridge-computed or applied `ctrl` differs.
- `SIMULATOR_DIVERGENCE`: pre-step integration state and applied `ctrl` are identical, but the next MuJoCo integration state/contact/solver result differs.
- `NO_DIVERGENCE_IN_WINDOW`: no difference in the preregistered capture window.
- `PROTOCOL_FAILURE`: invariants or alignment fail.
- `UNRESOLVED_BOUNDARY`: divergence exists but current observables cannot order it causally.

Do not label a downstream difference as causal if an earlier boundary already differs.

## Acceptance criteria

A successful first-divergence checkpoint requires all of the following:

1. at least two valid pairwise comparisons from three preregistered repetitions;
2. identical frozen handoff state at tick 8000 in all valid runs;
3. a machine-readable first-divergence table containing pair, record/tick, category, first differing field/index and magnitude or byte mismatch;
4. the same causal boundary classification in all valid pairs, or an explicit `UNRESOLVED_BOUNDARY` outcome if pair classifications conflict;
5. a results note binding raw artifact hashes, code commit and exact run command/environment.

No numerical tolerance is used for the primary identity test: exact bit/byte equality is the primary detector. Floating-point deltas may be reported secondarily to describe magnitude.

## Stop conditions

Stop immediately and do not resume D4 if:

- frozen handoff is no longer bitwise identical;
- command-writer or lockstep protocol gates fail;
- run provenance differs unexpectedly;
- first divergence is localized sufficiently to authorize a narrower follow-up checkpoint.

If no divergence appears in 5.0 s after release, report `NO_DIVERGENCE_IN_WINDOW`; do not extend the runtime without a new authorization/checkpoint.

## Deliverables

Minimum deliverables for closeout:

- `docs/validation/phase1_frozen_handoff_first_divergence_20260914/RESULTS.md`
- `docs/validation/phase1_frozen_handoff_first_divergence_20260914/first_divergence.csv`
- run/protocol provenance table and SHA-256 hashes of all raw capture files
- offline decoder/comparator used to produce the table

## Follow-up decision rule

After this checkpoint:

- controller-side divergence -> inspect controller scheduling, hidden mutable state, initialization and deterministic math in a new checkpoint;
- bridge-side divergence -> inspect message/ack ordering and bridge state in a new checkpoint;
- simulator-side divergence -> inspect MuJoCo/contact/solver deterministic settings and threading/order in a new checkpoint;
- no divergence in window -> authorize a larger but still bounded window only as a new checkpoint.

D4 A/B remains blocked until baseline continuation from the frozen handoff is reproducible enough for causal comparison.