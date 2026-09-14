# Phase 1 frozen-handoff first-divergence checkpoint — 2026-09-14

## Authority and execution handoff

This checkpoint follows `docs/research/PHASE1_AGENT_CONTRACT.md`.

The planning side has already created and prepared the working branch. The Atlas executor must **pull and execute this branch directly**, not create another branch from `main`.

- Base lineage: `b0921380ca4507bdb08227d8453bde654198cee9`
- Working branch: `research/phase1-frozen-handoff-first-divergence-20260914`
- Prior checkpoint: `TASK_PHASE1_LOCKSTEP_FROZEN_READY_HANDOFF_20260914.md`
- Prepared Stage-A runner: `example/cpp/scripts/run_phase1_frozen_handoff_first_divergence.sh`
- Prepared offline comparator: `example/cpp/tools/analysis/analyze_phase1_frozen_handoff_first_divergence.py`
- D4 / bounded stance `dq_des` intervention: **OFF for every run in this checkpoint**.
- No controller tuning, gait retuning, solver retuning, benchmark substitution, or mainline integration is authorized.

The executor records the exact branch HEAD after `git pull --ff-only` as the preregistered/pre-run code SHA. Do not reset to the base-lineage SHA; the branch HEAD intentionally also contains this task, the current agent contract, runner, and comparator.

## Problem statement

The prior checkpoint established a bitwise-identical frozen READY handoff at physics tick 8000 across repeated runs, while post-release physical trajectories still diverged. The present task is therefore not to improve performance. It is to identify the earliest post-handoff causal boundary at which repeated runs cease to be identical.

The predecessor evidence fixes the authoritative handoff at:

- `sim_tick_ms = 8000`
- `sim_time_s = 7.999999999999341`
- three predecessor handoff binary hashes identical.

## Preregistered hypothesis

H1: with an identical frozen handoff state, the first repeatability failure is observable at one of these ordered boundaries:

1. controller input / published LowState;
2. controller output / LowCmd and lockstep acknowledgement;
3. bridge-applied actuator control (`mjData.ctrl`);
4. MuJoCo integration state / contact-constraint evolution after `mj_step`.

The checkpoint succeeds if the earliest differing boundary and tick can be identified reproducibly. It does **not** require the divergence to be fixed in the same task.

## Required invariants

Before interpreting any divergence, all compared runs must satisfy:

- exact branch and pre-run HEAD recorded;
- clean worktree before the first runtime launch;
- frozen READY handoff occurs at tick 8000;
- frozen handoff integration state is bitwise identical across compared runs;
- same model/configuration, speed script, lockstep settings, environment and binary build;
- exactly one authorized command writer;
- no D4 or other causal intervention enabled;
- raw artifacts are immutable after capture;
- L1/L2/L3 are launched sequentially and exactly once unless Stage B is explicitly triggered below.

If any invariant fails, stop that comparison and report `PROTOCOL_FAILURE` rather than a causal conclusion. Do not rerun a failed ID to obtain a replacement sample.

## Existing instrumentation

Prefer existing instrumentation and avoid changing controller or simulator semantics. `CounterfactualSnapshotLogger` in `simulate/src/main.cc` records per eligible physics step:

- `mjSTATE_INTEGRATION` snapshot;
- pre-step simulation time, qvel[0], ncon, nefc and contact mask;
- atomic bridge record including command sequence;
- command fields for all 12 motors: q, dq, kp, kd, tau_ff;
- bridge sensor q and dq;
- bridge-computed ctrl and actual `mjData.ctrl`;
- post-step qacc[0].

The prepared runner enables the atomic bridge capture and writes `mj_snapshot.bin` only for the bounded handoff window. Because the measured handoff time is slightly below decimal `8.0`, the logger starts at `7.999 s` so the pre-step tick-8000 record itself is captured. Snapshot logging ends at `13.0 s`.

## Atlas executor procedure

### Stage 0 — checkout and preflight

Run on Atlas in the established native WSL/Linux Go2 environment.

1. `git fetch origin`
2. check out `research/phase1-frozen-handoff-first-divergence-20260914`
3. `git pull --ff-only origin research/phase1-frozen-handoff-first-divergence-20260914`
4. record `git rev-parse HEAD`
5. verify `git status --porcelain` is empty before runtime
6. read this entire task and `docs/research/PHASE1_AGENT_CONTRACT.md`
7. verify the prepared runner and comparator exist
8. run the existing focused lockstep tests, including `bash simulate/src/tests/run_lockstep_sim_tests.sh`; run any additional already-established controller lockstep tests required by the predecessor workflow
9. verify no stale Go2 simulator/controller process is still occupying the intended experiment DDS domains. Do not kill unrelated user processes; if provenance cannot be made clean, stop and report.

A preflight/test failure blocks live runs. Fix only a defect in the prepared diagnostic tooling if the fix is clearly non-semantic and within this task; otherwise stop.

### Stage A — exactly three bounded snapshot captures

Launch exactly, sequentially:

```bash
bash example/cpp/scripts/run_phase1_frozen_handoff_first_divergence.sh L1
bash example/cpp/scripts/run_phase1_frozen_handoff_first_divergence.sh L2
bash example/cpp/scripts/run_phase1_frozen_handoff_first_divergence.sh L3
```

Do not launch in parallel. Do not run L4. Do not rerun L1/L2/L3 after an inconvenient outcome.

Expected snapshot paths:

- `example/cpp/experiments/_runs/phase1_frozen_handoff_first_divergence_20260914/L1/mj_snapshot.bin`
- `example/cpp/experiments/_runs/phase1_frozen_handoff_first_divergence_20260914/L2/mj_snapshot.bin`
- `example/cpp/experiments/_runs/phase1_frozen_handoff_first_divergence_20260914/L3/mj_snapshot.bin`

The first captured pre-step record in each valid file must correspond to tick/time-ms 8000. Treat a different first alignment as a protocol failure, not something to trim away silently.

### Stage A — offline comparison

Create the validation directory and run:

```bash
python3 example/cpp/tools/analysis/analyze_phase1_frozen_handoff_first_divergence.py \
  example/cpp/experiments/_runs/phase1_frozen_handoff_first_divergence_20260914/L1/mj_snapshot.bin \
  example/cpp/experiments/_runs/phase1_frozen_handoff_first_divergence_20260914/L2/mj_snapshot.bin \
  example/cpp/experiments/_runs/phase1_frozen_handoff_first_divergence_20260914/L3/mj_snapshot.bin \
  --output docs/validation/phase1_frozen_handoff_first_divergence_20260914/first_divergence.csv
```

Also compute SHA-256 for all three raw snapshots and record them in the results/provenance table.

Validate directly from the captures or a tiny immutable-read analysis helper that:

- all three snapshot headers match;
- first record is the handoff record at time-ms 8000;
- first-record integration-state bytes are identical across L1/L2/L3;
- the raw files remain unchanged after analysis.

Do not align by wall-clock time.

## Offline comparison order

For each pair of runs, align by frozen-handoff-relative physics record/tick and compare in causal order:

1. integration-state bytes before step;
2. bridge command sequence and full motor command tuple `(q,dq,kp,kd,tau_ff)`;
3. bridge sensor q/dq;
4. bridge-computed ctrl;
5. actual `mjData.ctrl`;
6. ncon, nefc and contact mask;
7. post-step qacc and the next integration state.

Report the first record where any category differs and the earliest differing scalar/byte location for that category.

No numerical tolerance is used for the primary identity test: exact bit/byte equality is the detector. Floating-point deltas are secondary descriptions only.

## Classification rules

Use the earliest supported classification only:

- `INPUT_OR_TRANSPORT_DIVERGENCE`: simulator state is still identical but exact controller-observed state/input differs before command generation.
- `CONTROLLER_DIVERGENCE`: exact controller inputs are identical but LowCmd differs.
- `BRIDGE_DIVERGENCE`: LowCmd is identical but bridge-computed or applied `ctrl` differs.
- `SIMULATOR_DIVERGENCE`: pre-step integration state and applied `ctrl` are identical, but the next MuJoCo integration state/contact/solver result differs.
- `NO_DIVERGENCE_IN_WINDOW`: no difference in the preregistered capture window.
- `PROTOCOL_FAILURE`: invariants or alignment fail.
- `UNRESOLVED_BOUNDARY`: divergence exists but current observables cannot order it causally.

The prepared Stage-A snapshot does not contain the exact controller-observed LowState payload. Therefore, if the earliest observed difference is LowCmd, bridge sequence, or another boundary that cannot distinguish input/transport from controller generation, Stage A must remain `UNRESOLVED_BOUNDARY`; do not overclaim `CONTROLLER_DIVERGENCE`.

Do not label a downstream difference as causal if an earlier boundary already differs.

## Stage B — conditional targeted expansion only

Stage B is authorized **only if Stage A returns `UNRESOLVED_BOUNDARY` because the existing snapshot lacks the immediately upstream observable needed to order the first difference**.

In that case:

1. add the smallest diagnostic observable needed, in priority order:
   - exact controller-observed LowState payload hash/values for each acknowledged state tick;
   - exact LowCmd payload hash immediately before publish;
   - only if still necessary, selected post-`mj_step` solver/contact metadata;
2. do not instrument WBC internals unless exact controller input is identical while exact pre-publish LowCmd differs;
3. keep all controller/gait/model/solver behavior unchanged;
4. commit the minimal instrumentation before the Stage-B live launches and record that runtime code SHA;
5. repeat exactly L1/L2/L3 once using the same bounded matrix and distinct clean output paths; no additional retry set is authorized.

If Stage A already establishes `BRIDGE_DIVERGENCE` or `SIMULATOR_DIVERGENCE`, Stage B is not authorized. If Stage A shows `NO_DIVERGENCE_IN_WINDOW`, do not extend beyond 5 s in this task; close out with that label.

## Acceptance criteria

A successful first-divergence checkpoint requires all of the following:

1. at least two valid pairwise comparisons from three preregistered repetitions;
2. identical frozen handoff state at tick 8000 in all valid runs;
3. a machine-readable `first_divergence.csv` containing pair, record/tick, category, first differing field/index and magnitude or byte mismatch;
4. the same causal-boundary classification in all valid pairs, or an explicit `UNRESOLVED_BOUNDARY` if pair classifications conflict or required upstream observables are absent;
5. a results note binding raw artifact hashes, pre-run/runtime code SHA, exact runner, environment and relevant binary provenance.

## Stop conditions

Stop and do not resume D4 if:

- frozen handoff is no longer bitwise identical;
- command-writer or lockstep protocol gates fail;
- run provenance differs unexpectedly;
- the current stage has localized the first divergence sufficiently to authorize a narrower follow-up checkpoint;
- Stage A reports `NO_DIVERGENCE_IN_WINDOW`;
- the next step would require changing controller behavior, gait/model/solver parameters, benchmark, or runtime window beyond what is preregistered here.

Do not autonomously fix the localized nondeterminism in this checkpoint. Localization is the deliverable.

## Deliverables

Minimum closeout deliverables:

- `docs/validation/phase1_frozen_handoff_first_divergence_20260914/RESULTS.md`
- `docs/validation/phase1_frozen_handoff_first_divergence_20260914/first_divergence.csv`
- a run/protocol provenance table with SHA-256 hashes of all raw capture files used
- the offline comparator and any Stage-B diagnostic code actually used
- one concise recommended next checkpoint, not executed

Large raw snapshot binaries should not be committed unless repository policy clearly allows them; record exact local paths and SHA-256 instead.

## Closeout / handback to planner

After analysis:

1. write `RESULTS.md` with calibrated conclusion and key evidence;
2. run repository hygiene / relevant tests for any source changes made;
3. commit authorized analysis/results changes on this same research branch;
4. push the branch;
5. verify clean worktree and remote branch SHA;
6. report final branch, final commit SHA, classification, first divergent tick/record and boundary, plus any blocker;
7. STOP.

Do not run D4, do not tune, do not start the recommended follow-up checkpoint, and do not merge to `main`.

## Follow-up decision rule

After this checkpoint, the planner/reviewer will choose the next task:

- controller-side divergence -> inspect controller scheduling, hidden mutable state, initialization and deterministic math in a new checkpoint;
- bridge-side divergence -> inspect message/ack ordering and bridge state in a new checkpoint;
- simulator-side divergence -> inspect MuJoCo/contact/solver deterministic settings and threading/order in a new checkpoint;
- no divergence in window -> authorize a larger but still bounded window only as a new checkpoint.

D4 A/B remains blocked until baseline continuation from the frozen handoff is reproducible enough for causal comparison.