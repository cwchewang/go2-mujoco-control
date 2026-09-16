# Go2 repository rules

`main` is the stable code line and long-term route. The active research
frontier may live on a separate `research/*` branch. This file contains
repository guardrails; it is not a scientific plan or current-status report.

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
