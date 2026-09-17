# Atlas worker end-to-end smoke task

Mode: infrastructure-only, no live simulation  
Exact parent/base: `db5591724e4a5101633811c4e3a5562422be10bc`  
Branch: `research/atlas-worker-e2e-smoke-20260917`

## Question

Can the unattended Atlas research worker receive this repository-defined task, launch Luna, make a bounded task-local change, hand the uncommitted change back to the trusted wrapper, and have that wrapper commit/push it without touching research/runtime state?

## Authorized work

Do not modify controller, simulator, experiment, research-result, task-dispatch, workflow, or raw-evidence code/data.

Create exactly one tracked file:

`docs/validation/atlas_worker_e2e_smoke_20260917/RESULTS.md`

Its content must state:

- this was an infrastructure-only unattended worker smoke test;
- the exact task commit you started from;
- the exact model requested by the worker if visible from the execution environment/log context, otherwise state `worker-selected model not independently inspected by task`;
- `git status --porcelain` was checked before handoff to the trusted closeout wrapper;
- no live simulation or scientific experiment was run.

Do not create any other tracked file and do not modify an existing tracked file.

## Closeout

Run `git diff --check` and `git status --porcelain`. Do not run `git add`, `git commit`, or `git push`; the trusted Atlas wrapper owns those mechanical closeout steps. Leave exactly the required RESULTS file as the intended working-tree change, then stop.
