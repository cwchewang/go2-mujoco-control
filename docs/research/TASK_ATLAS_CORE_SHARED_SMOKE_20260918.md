# TASK_ATLAS_CORE_SHARED_SMOKE_20260918

## Goal
Validate the new shared multi-project Atlas Dispatch Core on the existing Go2 adapter without launching any live experiment.

## Frozen base
- Parent main: `780a4363b1dbcb3af2f46115e8dfa341440c66d8`
- Branch: `research/atlas-core-shared-smoke-20260918`

## Hard prohibitions
- Do not launch MuJoCo, DDS, controller/simulator, hardware, or any host-live capability.
- Do not modify controller, gait, MPC, WBC, IK, terrain, `.github/**`, `tools/atlas_*`, or raw `_runs` evidence.

## Task
1. Read the project instructions required by the normal worker contract.
2. Run `python3 -c 'import time; time.sleep(10)'` exactly once.
3. Write only `docs/validation/atlas_core_shared_smoke_20260918/RESULTS.md` containing the exact task commit, UTC start/end, command return code, and classification.
4. Run `git diff --check` and stop with the intended validation file uncommitted for the trusted wrapper.

## Acceptance
Classify `ATLAS_CORE_SHARED_GO2_SMOKE_PASS` only if the wait returns 0, no live capability is launched, and the trusted shared Core can push the closeout through the existing Go2 adapter.
