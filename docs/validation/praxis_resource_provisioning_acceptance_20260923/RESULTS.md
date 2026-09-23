# Praxis resource provisioning acceptance — 2026-09-23

Task branch: `research/praxis-resource-provisioning-acceptance-20260923`
Frozen task commit: `c19ddd8ee7c0a22639fb1cd96f652a3a4fde7741`
Execution mode: infrastructure acceptance; zero scientific execution.

## Acceptance checks

1. **PASS** — `git branch --show-current` returned the required task branch.
2. **PASS** — `HEAD` equals the frozen task commit, so it remains descended from it.
3. **PASS** — `.substrate/rl/policy.pt` exists and its SHA-256 is
   `9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d`.
4. **PASS** — All 50 files declared by
   `tools/substrate/rl_reference.lock.json` exist under
   `.substrate/upstream-go2-30e74dc5` and match their declared SHA-256 values.
5. **PASS** — The bound Python imports Torch `2.6.0+cpu`, MuJoCo `3.3.6`, and
   NumPy `2.2.6`.
6. **PASS** — `.substrate/headless-reliable/go2_mjpc_admit` exists and is
   executable.
7. **PASS** — The policy, upstream tree, Python environment, and headless
   runtime are symlinks into `/home/che/dev/go2-workspace/current/.substrate`.
8. **PASS** — `git status --porcelain --untracked-files=all` showed no substrate
   resources; `.substrate` is ignored and has no tracked files.

## Worker configuration observed

The checked-in `.atlas/project.json` selects model `gpt-6-luna` and adapter
`tools/atlas_research_task_v6.py`. Its Codex command, defined in
`tools/atlas_research_task.py`, sets `model_reasoning_effort="max"`.

## Verdict

**ACCEPTED** — The isolated Praxis task worktree received the expected
hash-bound resources through links into the persistent canonical resource root.
No network access, downloads, installs, physics, policy inference, qualification,
or scientific capture were performed; zero scientific attempts were consumed.
