# Praxis v2 Go2 identity acceptance

Status: complete; zero physics was run.

Frozen task identity: issue `#158`, branch
`research/praxis-v2-identity-acceptance-20260923`, starting commit
`aa174694ffcee2005983e0d20975f2b8dceb6a0d`.

## Result

The maintained Go2 scientific path now accepts the existing named expected
branch for manual execution and accepts a detached worktree only when all five
Praxis identity values are present, `PRAXIS_REPOSITORY`, `PRAXIS_TASK_BRANCH`,
and `PRAXIS_TASK_COMMIT` match the operation, current HEAD equals the expected
frozen commit, and the worktree is clean. Partial or conflicting bindings fail
closed. The preflight still checks its exact expected HEAD and all existing
cleanliness, locking, process, input, review, and test invariants.

The shared identity rule is used by `tools/research/preflight.py` and
`tools/substrate/launch.py::current_identity`. The preflight report records
whether the route was named or detached and identifies missing or mismatched
Praxis fields. Current execution documentation distinguishes Praxis v2's
detached path from the Atlas-backed Praxis v6 named-branch path.

## Regression checks

The tests cover both preflight and launcher identity checks. Named branches
pass without Praxis variables. Detached HEAD passes with an exact binding and
fails without one, with an incomplete binding, or with a wrong repository,
logical branch, or task commit. The launcher also verifies that a detached
worktree with an otherwise exact binding still fails when dirty.

Command:

```text
python3 -m unittest tools.research.test_preflight tools.research.test_preflight_integration tools.substrate.test_launch
```

Result: return code `0`; 67 tests passed.

Command:

```text
git diff --check
```

Result: return code `0`; no output.

These tests use temporary Git repositories and synthetic fixtures. No MuJoCo
plant, simulator/controller process, `launch prepare`, or `launch capture` was
started. Raw command arguments, stdout, stderr, return codes, and the initial
Praxis environment snapshot are preserved in the task's Praxis evidence
directory.
