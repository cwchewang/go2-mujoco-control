# TASK_ATLAS_DISPATCH_SMOKE_A_20260918

## Goal
Validate Atlas dispatch vNext on the real self-hosted runner with a harmless offline research task. This is infrastructure smoke only.

## Frozen base
- Canonical main parent: `b8fb43e8bcecafb768ed05ee133eca2b0d687414`
- Branch: `research/atlas-dispatch-smoke-a-20260918`
- No `ATLAS_HOST_EXPERIMENT` manifest.

## Rules
- Do not launch MuJoCo, DDS, controller, simulator, hardware, or any scientific capture.
- Do not change controller, gait, MPC, WBC, IK, terrain, scripts, workflows, or `tools/atlas_*`.
- Only create files under `docs/validation/atlas_dispatch_smoke_a_20260918/`.
- Do not push or write Git metadata; the trusted wrapper owns commit/push.

## Work
1. Record a UTC start timestamp.
2. Run exactly one harmless local wait inside the sandbox: `python3 -c 'import time; time.sleep(45)'`.
3. Record a UTC end timestamp.
4. Write `docs/validation/atlas_dispatch_smoke_a_20260918/RESULTS.md` containing the start/end timestamps, elapsed wall time, exact task identity, and classification `ATLAS_DISPATCH_SMOKE_A_PASS` if the wait completed normally.
5. Run `git diff --check` and `git status --porcelain`.

## Acceptance
Pass only if the offline wait completes and the validation file is the only task-produced repository change. This task is intentionally long enough to overlap with smoke B when the dispatcher worker pool is functioning.
