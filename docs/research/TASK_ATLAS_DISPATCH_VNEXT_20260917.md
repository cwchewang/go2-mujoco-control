# TASK_ATLAS_DISPATCH_VNEXT_20260917

## Goal
Replace the current one-workflow/one-worker serial execution model with a small queue-aware Atlas dispatcher that can run multiple Luna preparation/analysis workers concurrently while keeping host live experiments strictly serialized. Add safe mid-run observability. Do not touch locomotion/control/scientific behavior.

## Frozen base
- Canonical main: `e30782ad916ef1614a877d7a3c122f62682c8f19`
- Branch: `research/atlas-dispatch-vnext-20260917`
- This is infrastructure-only. No MuJoCo live locomotion run and no scientific attempt.

## Why
Current `.github/workflows/atlas-task.yml` uses one global concurrency group, and the worker also holds a global `fcntl` lock for its whole lifetime. This causes all preparation/analysis to serialize and allows newer queued workflow invocations to cancel an older pending invocation. The task queue must live in GitHub Issues, not in workflow-run ordering.

## Required architecture

### 1. Queue-aware dispatcher
Add a trusted dispatcher (prefer a small Python module) which treats open GitHub issues carrying `atlas-task` as the authoritative queue.

A workflow invocation is only a wake-up signal. The dispatcher must scan the queue and claim runnable tasks; correctness must not depend on every issue event producing a surviving workflow run.

Requirements:
- deterministic FIFO by issue creation time unless an issue is already in a resumable local state;
- no task loss if intermediate GitHub Actions runs are cancelled while another dispatcher run is active;
- idempotent claim: the same issue/task commit cannot be executed twice concurrently;
- reuse the existing trusted task-commit/branch verification and resume semantics;
- configuration knob `ATLAS_MAX_WORKERS`, default 2;
- preparation and post-host Luna analysis may overlap across tasks;
- isolated worktree/state/artifact paths per issue/task.

### 2. Narrow the lock boundary
Remove the whole-task global exclusive lock from the v4 path.

Introduce two separate concepts:
- per-task/branch ownership: prevents duplicate execution of the same task;
- host-live lock: a blocking exclusive lock held only while executing a trusted host capability that can affect MuJoCo/DDS/hardware/shared runtime state.

The host-live lock must queue/wait, not fail the task merely because another task currently owns the host-live phase. Preparation and analysis must not hold it.

No two host live experiments may overlap.

### 3. Safe progress/observability
Add an allow-listed progress event model; never publish model chain-of-thought or raw hidden reasoning.

Expose at least:
- queued / claimed / preparing / candidate_committed / waiting_for_host / host_running / host_completed / analyzing / complete / failed;
- elapsed time;
- task issue, branch, task commit, candidate/result commit when available;
- tests/build summary when available;
- host-live facts when available: DDS ready, controller handoff, scientific attempt consumed yes/no, current gait cycle/total if the host runner emits it, raw evidence file count/bytes, host return code;
- most recent safe event and timestamp.

Surfaces:
1. emit safe progress lines to GitHub Actions stdout in real time;
2. maintain exactly one progress comment per issue and update it in place (target cadence ~30-60 s; do not spam comments);
3. persist the same safe state locally so status survives transient GitHub API failure.

Progress publishing is best-effort observability only: failure to update a comment must not fail or alter the scientific task.

### 4. Queue semantics / workflow
Modify `.github/workflows/atlas-task.yml` so workflow-run concurrency cannot cause task loss. It is acceptable to keep one global dispatcher workflow if the dispatcher drains/scans the authoritative issue queue. Do not rely on pending workflow-run order as the task queue.

The dispatcher should remain alive long enough to notice newly queued tasks during an active run (short polling/idle grace is fine), then exit cleanly when the queue is empty.

### 5. Reuse seam for other repos
Do not attempt a huge framework rewrite. Introduce a small repo-config seam so dispatcher core is not hard-coded to Go2 paths where unnecessary. At minimum make task-root, allowed branch prefix, protected paths/evidence roots, max workers, and host-capability policy configuration-driven or cleanly injectable. Go2 remains the first concrete config.

## Non-goals / prohibitions
- Do not change controller, gait, MPC, WBC, IK, terrain, or scientific thresholds.
- Do not run a live locomotion/scientific experiment.
- Do not weaken exact-SHA/provenance/raw-evidence integrity rules.
- Do not expose chain-of-thought in GitHub comments/logs.
- Do not grant Luna unrestricted host shell as a shortcut.
- Do not silently delete old state/artifacts.

## Required tests
Use fake/local workers and fake host capabilities only.

Must demonstrate:
1. two offline tasks overlap in preparation/analysis when `ATLAS_MAX_WORKERS=2`;
2. two tasks requesting host-live serialize only that host phase; host intervals never overlap;
3. a third issue arriving while dispatcher is running is discovered from the issue queue without depending on its own workflow run surviving;
4. duplicate wake-ups do not duplicate the same task;
5. interrupted/resumable task is resumed rather than restarted from scratch;
6. progress state transitions are correct and a single issue comment is updated in place;
7. progress output contains only allow-listed safe fields;
8. GitHub API/comment failure does not fail the underlying worker;
9. existing Atlas dispatcher/host experiment contract tests remain green;
10. repository hygiene and portable checks pass.

## Deliverables
- implementation and focused tests;
- updated `docs/research/ATLAS_AGENT_ARCHITECTURE_20260917.md` describing queue, worker pool, host-live lock, and observability;
- closeout under `docs/validation/atlas_dispatch_vnext_20260917/` with:
  - `RESULTS.md`
  - `analysis.json`
  - `provenance.csv`
- `RESULTS.md` must separate `FACTS`, `DERIVED DIAGNOSIS`, `IMPLEMENTATION`, `LUNA INTERPRETATION`.

## Acceptance
Primary classification may be `ATLAS_DISPATCH_VNEXT_READY` only if all required tests pass and the implementation demonstrably removes whole-task serialization without allowing overlapping host-live phases or task loss. Otherwise close out with the narrowest failure classification and evidence; do not paper over blockers.
