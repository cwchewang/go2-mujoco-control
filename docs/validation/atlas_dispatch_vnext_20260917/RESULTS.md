# Atlas dispatch vNext closeout

Date: `2026-09-17`

Task commit: `442b875bfb23f3e0c7f5cb9e90130a2423ce54e2`

Exact main parent: `e30782ad916ef1614a877d7a3c122f62682c8f19`

Mode: `infrastructure / no-live / veto`

Proposed Luna classification: `ATLAS_DISPATCH_VNEXT_VETOED_PROTECTED_SURFACES`

## FACTS

- No MuJoCo, DDS, controller, hardware, or scientific experiment was
  launched. No raw `_runs` evidence was created or modified.
- The checkout is exactly the requested task commit and matches
  `origin/research/atlas-dispatch-vnext-20260917`. It is detached by the
  managed task-worker wrapper.
- The required remote refresh was attempted. Git could not write the linked
  worktree's external `FETCH_HEAD` because that metadata path is read-only.
  Read-only verification of `HEAD`, `origin/main`, and the requested research
  ref succeeded.
- The current workflow uses one global `atlas-task-runner` concurrency group,
  triggers only on `issues.opened`, and invokes `tools/atlas_dispatch_v2.py`.
- The current v4 host worker acquires its exclusive lock before preparation and
  holds it through the host/analysis lifecycle. The current issue-state helper
  creates a new comment for each state update rather than updating one comment
  in place.
- The worker contract explicitly rejects changed paths beginning with
  `.github/` or `tools/atlas_`; the architecture contract states the same
  protection. The requested queue/workflow and trusted-dispatcher changes
  therefore cannot be made in this worker.
- Existing no-live Atlas contract tests passed: `13/13`. Repository hygiene
  passed. Python compilation passed. `git diff --check` passed.
- The required new tests for concurrent preparation, host serialization,
  issue-queue discovery, duplicate wake-up idempotence, resumability,
  progress comments, safe-field filtering, and API-failure tolerance were not
  run because no implementation was permitted and no compliant test seam was
  present. The existing 13 tests do not demonstrate those properties.

## DERIVED DIAGNOSIS

The acceptance condition cannot be satisfied without changing protected
surfaces. Leaving the workflow and trusted dispatcher untouched would preserve
the current event-driven, whole-task-serialized behavior; adding an isolated
unconnected prototype elsewhere would not change runtime semantics and would
not prove queue task-loss or lock-boundary safety. Implementing the required
behavior by editing the protected paths would violate the task-worker contract
and would be rejected by the trusted wrapper.

This is an execution/infrastructure veto, not a scientific failure. There is
no basis for `ATLAS_DISPATCH_VNEXT_READY`.

## IMPLEMENTATION

- Updated `docs/research/ATLAS_AGENT_ARCHITECTURE_20260917.md` with the
  queue, worker-pool, host-lock, observability, and configuration-seam design,
  explicitly marked as uninstalled because of the protected-surface veto.
- Added this closeout, `analysis.json`, and `provenance.csv`.
- No `.github/**`, `tools/atlas_*`, runtime/controller, scientific, or raw
  evidence files were changed.

## LUNA INTERPRETATION

`ATLAS_DISPATCH_VNEXT_VETOED_PROTECTED_SURFACES` is the narrowest supported
classification. A trusted wrapper with explicit authorization to modify the
workflow and Atlas dispatcher surface must rerun this infrastructure task and
execute the eight deferred vNext behavioral tests before any ready
classification can be considered.
