# Praxis v2 Go2 acceptance — detached frozen identity

## Goal

Migrate the Go2 project-level execution identity checks so Praxis v2 detached
task worktrees are a first-class valid execution context without weakening the
scientific exact-identity gates.

This is a **zero-physics acceptance task**. It must not run MuJoCo, construct a
plant, execute `launch prepare` or `launch capture`, reserve/consume a
scientific attempt, or start any simulator/controller process.

## Current problem

Praxis v2 intentionally executes from a detached worktree while exporting the
frozen task identity:

- `PRAXIS_REPOSITORY`
- `PRAXIS_ISSUE_NUMBER`
- `PRAXIS_TASK_BRANCH`
- `PRAXIS_TASK_COMMIT`
- `PRAXIS_TASK_PATH`

Go2 still has current execution paths that treat
`git branch --show-current == expected branch` as mandatory. A detached
worktree must not pass merely because it is detached; it may pass only when the
Praxis identity binding is complete and exact.

## Required semantics

Preserve the existing named-branch path for normal/manual execution.

For the current scientific execution path, a detached worktree is valid only
when all relevant facts agree:

1. current Git HEAD is the exact expected/frozen head for the operation;
2. `PRAXIS_REPOSITORY == cwchewang/go2-mujoco-control`;
3. `PRAXIS_TASK_BRANCH` equals the task/CLI expected logical branch;
4. `PRAXIS_TASK_COMMIT` equals the exact frozen HEAD expected for that
   qualification/preparation operation;
5. the worktree cleanliness and every existing scientific/preflight invariant
   remain unchanged.

Wrong/missing Praxis repository, branch, commit, or a detached HEAD without a
Praxis binding must fail closed.

Inspect the current project code before editing. Cover every **current**
branch-identity assumption that would block the maintained Go2 scientific path,
especially `tools/research/preflight.py` and
`tools/substrate/launch.py::current_identity`. Do not revive or refactor v1
Atlas/Praxis wrappers. Do not modify `.github/**` or `tools/atlas_*`.

Update current documentation that falsely says Praxis must attach a named local
branch. Historical validation records must remain historical.

## Tests

Add focused regression tests proving at least:

- named expected branch still passes;
- detached HEAD + exact Praxis v2 binding passes;
- detached HEAD without Praxis binding fails;
- wrong Praxis repository fails;
- wrong Praxis logical branch fails;
- wrong Praxis task commit fails.

Run the smallest relevant existing test suites plus all new tests. Static/import
tests are allowed. Do not invoke any command that advances physics.

## Acceptance evidence

Preserve under `$PRAXIS_EVIDENCE_DIR`:

- raw `git rev-parse HEAD` and `git branch --show-current`;
- the five Praxis identity environment values (no secrets);
- exact test commands, stdout/stderr and return codes;
- `git diff --check`;
- any failed development/test attempt rather than deleting it.

The final closeout must distinguish observation / inference / conclusion /
uncertainty and cite raw evidence IDs. This task is accepted only if it produces
a committed result, all targeted no-physics tests pass, and the GitHub review
surface makes the material evidence remotely readable.

## Non-goals

- no physics;
- no model/checkpoint execution;
- no attempt ledger changes except tests if strictly necessary;
- no scientific result;
- no v1 formal-runner/trusted-host work;
- no change to Praxis v2 itself.
