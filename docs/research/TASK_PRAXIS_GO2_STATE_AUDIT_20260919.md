# Praxis / Go2 actual-state audit — 2026-09-19

Mode: infrastructure / diagnostic only

## Objective

Independently establish the actual Atlas + Go2 + Praxis state before any further
migration or MuJoCo canary. Do not inherit assumptions from earlier assistant
diagnoses. Verify the machine and repository state yourself and report what is
true, what is false, and what remains uncertain.

You have broad latitude for READ-ONLY diagnosis. Do not launch MuJoCo/DDS, do
not run a scientific experiment, do not alter services, do not delete/move
worktrees, and do not repair anything yet.

## Inspect as needed

At minimum, independently inspect:

- the real type and Git semantics of `~/dev/go2-workspace/current`, including
  `.git`, HEAD, branch, remotes, worktree list, dirty state, and relation to
  origin/main;
- `~/dev/go2-workspace`, `~/dev/go2-agent/tasks`, relevant worker state,
  and surviving task worktrees;
- the GitHub runner workspace(s) for this repository and how they differ from
  the persistent Go2 anchor;
- current and historical `.github/workflows/atlas-task.yml`,
  `.atlas/project.json`, and the project adapter scripts;
- current Praxis core pin and how the central dispatcher invokes the Go2 adapter;
- read-only runner/service status where useful;
- the failure evidence from the recent central-Praxis migration attempts, and
  which failures were real host faults versus bad assumptions/checks.

Use Git history and filesystem evidence rather than guessing. If two facts
conflict, trace the conflict until you can explain it or explicitly mark it
unresolved.

## Deliverable

Write only:

`docs/validation/praxis_go2_state_audit_20260919/RESULTS.md`

Structure it as:

1. VERIFIED FACTS
2. FALSE ASSUMPTIONS / MISDIAGNOSES
3. ACTUAL TOPOLOGY (persistent repo, task worktrees, runner checkout, Praxis core)
4. RECENT FAILURE CHAIN with exact earliest failing boundary for each attempt
5. MINIMAL SAFE MIGRATION PLAN
6. WHAT MUST BE VERIFIED BEFORE ANY LIVE MUJOCO CANARY

Do not implement the migration in this task. The purpose is to give Sol a clean,
independently verified picture before choosing the next change.
