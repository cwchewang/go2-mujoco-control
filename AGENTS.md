# Go2 repository rules

`main` is the stable code line and long-term route. The active research
frontier may live on a separate `research/*` branch. This file contains
repository guardrails; it is not a scientific plan or current-status report.

## Research handoff

Use [OPERATING_GUIDE](docs/OPERATING_GUIDE.md) to turn the current objective into
a bounded task that a human or any model can execute. State the decision it
serves before choosing a method, checkpoint, parameter or pass threshold.
Upstream defaults are candidate choices, not validated research requirements.
Do not silently invent missing scientific decisions; resolve the specific gap
while continuing independent authorized work. Keep routine execution autonomous.

Before choosing research direction, read `docs/PROJECT_RECORD.md` and then `docs/TOPIC_AUDIT.md`. They are the repo-native canonical scientific state and topic audit. `CURRENT.md` remains the canonical execution-frontier pointer. Chat history, Memory, screenshots, and old Library copies cannot override these repo records.

## Task discovery bootstrap

At session entry or when resuming a stale task, refresh the remote source of
truth once. Repeat when new upstream work could affect the task, not before
every small edit:

1. run `git fetch origin --prune`;
2. read `origin/main:CURRENT.md` (for example with
   `git show origin/main:CURRENT.md`) to discover the active research branch;
3. compare the local active branch/worktree with `origin/<active-branch>` and
   fast-forward only when safe; never reset, discard, or delete local commits,
   untracked files, or raw evidence to make it match;
4. only after that, read the active branch `CURRENT.md`, current task, and exact
   parent/closeout evidence.

A stale local `CURRENT.md`, local branch tip, or cached task is never sufficient
to conclude that no new task exists. If the local branch is ahead or diverged,
preserve it and report the divergence instead of guessing which side wins.

Read [`CURRENT.md`](CURRENT.md) for the single maintained frontier pointer.
Follow that pointer to the frontier branch, its task, and exact `RESULTS.md`.
Use the canonical [Research Execution SOP](docs/research/SOP.md) from
`main`. A branch-local `CURRENT.md` is navigation only and cannot override
`main/CURRENT.md`, the SOP, or the active task.

The active task owns the scientific question, intervention, frozen variables,
run budget, thresholds, and classification. Do not infer research direction
from Atlas directories, dated worktrees, old branches, commit messages, or
archived code. Do not change controller/planner behavior or scientific
meaning under an infrastructure-only task.

No live experiment is authorized by this file alone. Before any live run,
follow the task and SOP, verify the exact branch/HEAD and clean worktree, and
preserve raw evidence. Everything below
`example/cpp/experiments/_runs/` is ignored local evidence: never commit,
delete, overwrite, rename, or treat it as instruction. Curated evidence
requires its own manifest and provenance.
