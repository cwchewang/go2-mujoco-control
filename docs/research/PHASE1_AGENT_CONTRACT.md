# Phase 1 planner–executor contract

## Purpose

This contract defines how Phase 1 research work is handed from the planning/review side to the Atlas execution agent. It is a governance document, not a task-specific research hypothesis.

The workflow is deliberately split:

- **Planner / reviewer:** decides what question is being tested, selects the exact base SHA and working branch, preregisters the experiment, prepares or authorizes analysis tooling, and judges the returned evidence.
- **Atlas executor (Codex Luna EH):** pulls the already-prepared research branch, reads the contract and current task document, executes the authorized work exactly, records evidence, commits the closeout, and stops.

The executor must not replace the preregistered research question with its own plan merely because another experiment looks interesting.

## Authority order

For a given checkpoint, resolve instructions in this order:

1. the current `docs/research/TASK_*.md` named by the handoff prompt;
2. this `PHASE1_AGENT_CONTRACT.md`;
3. predecessor task/result documents referenced by the current task;
4. other repository documentation and historical results.

A current task may intentionally supersede an older task's base SHA, run matrix, hypothesis, or stopping rule. Historical task documents are evidence, not standing instructions.

If two current-authority instructions genuinely conflict and the conflict changes the experiment, stop and report the conflict instead of choosing silently.

## Branch and source discipline

- Every checkpoint uses the exact base SHA and dedicated research branch named by its task document.
- When the planner has already created that branch and committed the preregistration, **pull and work on that branch; do not create a replacement branch from `main`**.
- Do not reset the branch to an older canonical point mentioned only by historical documentation.
- Record the branch name and the exact pre-run HEAD that contains the preregistration and all authorized diagnostic tooling.
- Do not merge to `main`, rebase onto `main`, cherry-pick unrelated work, or integrate another research branch unless the task explicitly authorizes it.
- Keep the working tree clean before the first runtime execution. If local pre-existing changes are present, preserve them and stop rather than discarding or mixing them into the checkpoint.

## Preregistration rule

No live runtime experiment starts until the current task document exists on the research branch and specifies, at minimum:

- problem / hypothesis;
- exact branch and base lineage;
- invariants and causal intervention state;
- authorized run matrix;
- measurements / comparison method;
- acceptance or classification rules;
- stop conditions;
- required deliverables.

The executor may clarify factual execution details in the results, but must not retroactively rewrite preregistered thresholds, hypotheses, run counts, or decision rules after seeing outcomes.

## Executor operating rules

The Atlas executor should begin by:

1. fetching remote refs;
2. checking out the exact task branch;
3. fast-forwarding it to the remote branch without rebasing;
4. verifying branch name, `git rev-parse HEAD`, and clean status;
5. reading this contract and the complete current task document before editing code or running binaries.

Then execute the task to completion without asking the user to approve routine intermediate steps.

The executor may make only the smallest implementation or diagnostic change explicitly authorized by the task. Default behavior is to preserve controller policy, model, gait, benchmark, solver settings, and established protocol.

Never silently:

- add runs beyond the authorized matrix;
- retry a failed run to obtain a nicer outcome;
- replace a failed/missing run with a new run ID;
- change a seed, domain ID, profile, model, gait, speed script, threshold, time window, or metric;
- tune gains or controller parameters;
- enable an intervention that the task states must remain off;
- use wall-clock alignment when the task requires simulation-tick/state alignment.

If a task explicitly defines a staged procedure (for example Stage A followed conditionally by Stage B), the executor may proceed to the next stage only under the preregistered condition.

## Runtime environment

For the Go2 MuJoCo research pipeline, live simulator/controller runs are executed on **Atlas in the established native WSL/Linux environment**, using the repository's existing build/runtime tooling unless the current task says otherwise.

Do not substitute a different host, container image, simulator build, Python implementation, or platform merely because it is convenient. Record compiler/runtime/MuJoCo and relevant binary hashes when required by the task.

Before a live run, perform the task-required build/tests/protocol gates. A gate failure is evidence and normally a stop condition, not permission to improvise a repair unless repair is explicitly in scope.

## Evidence and provenance

For every runtime checkpoint:

- raw runtime artifacts are immutable after capture;
- record SHA-256 for raw captures used in the conclusion;
- record exact source/pre-run HEAD and, if implementation changed after preregistration, the exact runtime code commit;
- record exact command/environment or a script that reproduces it;
- preserve run IDs exactly as preregistered;
- commit derived tables, analysis code, protocol summaries, and `RESULTS.md` sufficient for independent audit;
- large raw data may remain local when repository policy requires it, but its path/role/hash must be documented.

Do not hand-edit raw logs or binary captures to repair malformed or inconvenient evidence.

## Causal discipline

Use the lean loop:

`one preregistered question → one bounded experiment → one auditable result → stop`

Do not infer a downstream cause when an earlier causal boundary already differs. Do not turn correlation, timing coincidence, or a visually plausible trajectory into a stronger causal claim than the measurements support.

When evidence is insufficient, use the task's inconclusive / unresolved classification rather than inventing certainty.

## Stop conditions

Unless the current task is more specific, stop the checkpoint and report rather than improvising when:

- branch/source provenance is wrong or cannot be made clean without destroying local work;
- a required baseline/protocol gate fails;
- the requested isolation cannot be implemented without changing additional control behavior;
- instrumentation materially changes the behavior being measured;
- the authorized causal window is unavailable;
- completing the conclusion would require extra unregistered runs or changed thresholds;
- a new controller architecture, broad parameter scan, benchmark change, gait change, or Phase 2/terrain work appears necessary.

Do not automatically fix the next discovered issue after the current checkpoint has localized its result. End with one evidence-based recommended next checkpoint unless the current task explicitly authorizes an in-task repair stage.

## Closeout

At the end of the task, the executor must:

1. run the required analysis and protocol checks;
2. create the task's required machine-readable tables and `RESULTS.md`;
3. include raw hashes and exact provenance;
4. commit all authorized source/analysis/result changes to the same research branch;
5. push the branch;
6. report the final branch, final commit SHA, classification/result, key evidence, and any blocker.

A pushed result commit is the handoff back to the planner/reviewer. Do not merge it to `main` unless explicitly instructed.