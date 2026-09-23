# Praxis v2 live concurrency acceptance — Go2 B

## Purpose

This is a zero-physics, non-scientific infrastructure acceptance task. Its only purpose is to prove that the deployed Praxis v2 executor pool can overlap real Codex executions while keeping task identity, worktrees, evidence and publication isolated.

## Hard boundaries

- Do not run MuJoCo, simulators, controllers, GPU/CUDA work, training, dataset generation, scientific evaluation, or experiments.
- Do not modify PROJECT_RECORD, TOPIC_AUDIT, CURRENT, protocols, configs, research conclusions or scientific status.
- Do not inspect scientific outputs beyond what is necessary to avoid touching them.
- Do not push to GitHub; Praxis publishes.
- The only intended tracked result change is `docs/validation/praxis_v2_live_concurrency_20260923/GO2_B_RESULT.md`.

## Required live-overlap evidence

Use the Praxis evidence directory supplied to this task.

1. Create `raw/live-start.txt` containing a high-resolution UTC timestamp and the five `PRAXIS_*` frozen identity values.
2. Sleep for 20 seconds.
3. Create `raw/process-snapshot.txt` from a bounded process listing that shows currently running `codex exec` and/or `praxis_v2.cli run` processes. Do not expose secrets or unrelated environment values.
4. Sleep for another 25 seconds.
5. Create `raw/live-end.txt` containing a high-resolution UTC timestamp.
6. Create `docs/validation/praxis_v2_live_concurrency_20260923/GO2_B_RESULT.md` summarizing this task's frozen identity, start/end timestamps, worktree path, and the explicit statement that no physics/GPU/scientific work ran.
7. Run `git diff --check`, verify the worktree contains only the intended tracked result change beyond the frozen task document, and commit the result.
8. Write the required Praxis `closeout.json`. Material observations/conclusions must cite the start/end/process-snapshot evidence and Git result evidence.

## Acceptance meaning

A successful individual task only proves its own bounded execution and publication. Global concurrency is decided later by comparing the three independent tasks' evidence intervals and process snapshots.
