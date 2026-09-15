# Research Execution SOP v0.1

Status: active for new research checkpoints after adoption. Historical checkpoints remain governed by the contract/task versions frozen with them.

This SOP is intentionally small. Its purpose is not to add paperwork; it is to prevent expensive live runs from being wasted by avoidable execution mistakes while preserving strict scientific causality.

## 1. Core rule

**Scientific variables are strict; execution engineering is flexible before live; after scientific capture begins, results may not be selected or retried opportunistically.**

The workflow has two independent responsibilities:

- **Planner/reviewer (Sol):** decides what scientific question is being tested and freezes the scientific design.
- **Executor (Luna on Atlas):** independently decides whether the prepared implementation is technically qualified to run and has veto authority over live execution.

Neither side alone is sufficient for a high-risk live run when the execution surface has changed.

## 2. What Sol freezes

Before a confirmatory live run, Sol freezes the following in the current task:

- research question / hypothesis;
- exact parent evidence or accepted baseline;
- scientific intervention and variables that must remain unchanged;
- run budget;
- primary measurements;
- acceptance / classification rules;
- scientific stop conditions.

Luna must not silently change any of these. In particular, Luna must not tune speed, gait timing, controller gains, planner mathematics, WBC/MPC/ID behavior, scene geometry, safety limits, scientific thresholds, seed/run count, or add follow-up experiments unless the task explicitly authorizes those changes.

## 3. What Luna owns

Luna must independently audit execution readiness. The task is not an excuse to bypass a known infrastructure constraint.

Before live, Luna may autonomously inspect and make the smallest non-scientific repair to:

- DDS/domain selection and port/lock conflicts;
- output paths and run-directory bookkeeping;
- runner shell plumbing;
- logger/header/schema bookkeeping;
- analyzer parsing/tooling;
- build/test commands;
- provenance/hash collection;
- stale process cleanup;
- no-live regression tests.

Luna may always add a no-live test when it helps prove readiness.

If a requested change could alter the post-handoff state/control trajectory, or Luna cannot prove that it is execution-only, it is a **scientific/runtime-semantic change** and Luna must not make it autonomously.

## 4. Executor veto

Luna has an unconditional live veto.

If the task conflicts with verified infrastructure, source semantics, geometry, protocol limits, prior accepted evidence, or its own preflight results, Luna must not weaken an existing guard merely to satisfy the task.

Examples:

- a task requests an invalid DDS domain;
- a task calls a window “pre-contact” but robot/scene geometry disproves that;
- a runner omitted an argument present in the accepted baseline;
- telemetry header/sample widths differ;
- the primary analyzer cannot parse the generated schema.

The executor should repair a clearly non-scientific issue when authorized by Section 3, otherwise stop with `PLANNER_SPEC_CONFLICT` or the task’s appropriate protocol classification.

## 5. Preflight is executable, not a checklist

Every live run must pass `tools/research/preflight.py` immediately before launch.

At minimum preflight must check:

- exact branch/HEAD and clean worktree;
- runner exists and passes shell syntax validation;
- DDS domain is valid, within the selected safe policy, has legal RTPS UDP ports, and its lock is free;
- run directory is fresh;
- no stale simulator/controller/runner process is active;
- required files/hashes match when specified;
- task-required build/tests/no-live schema tests pass;
- runner diff is recorded when a baseline runner is supplied.

If logger/schema changed, a no-live schema regression test is mandatory.

If analyzer input/schema changed, a no-live parser/fixture test is mandatory.

If scene/geometry changed, geometry-dependent gates must be re-derived and tested.

If runner/environment changed, its actual diff against the relevant accepted runner must be reviewed rather than assumed equivalent.

### Sol review gate

When runtime code, runner semantics, scene, logger/schema, or another execution surface capable of invalidating a costly run has changed, the checkpoint requires a second Sol review after Luna’s implementation is committed.

The reviewed commit SHA must be the exact HEAD used for live. `preflight.py --requires-sol-review --approved-head <sha>` enforces this.

For a frozen replay/replication where none of those surfaces changed, Luna may proceed after preflight without a redundant second Sol review.

## 6. Failure handling before scientific capture

A failed infrastructure check is not automatically a new research checkpoint.

Before scientific capture begins, Luna may fix non-scientific infrastructure problems and rerun preflight within the same checkpoint.

Examples: invalid/free DDS domain, malformed output path, missing executable bit, header-only logger defect caught by a no-live test.

Scientific gate failures still stop the checkpoint.

## 7. Attempt boundary and retry rule

The live attempt is considered scientifically consumed at the first valid **post-handoff state/control sample** used by the experiment.

Three cases:

1. **Prelaunch failure:** simulator/controller did not start. No scientific attempt consumed. Luna may repair execution-only issues and continue after preflight.
2. **Boot failure before the first valid post-handoff scientific sample:** the attempt is not scientifically consumed. Luna may perform root-cause analysis. One automatic recovery launch is allowed only when the cause is proven execution-only, the failed artifacts are preserved, scientific/runtime semantics are unchanged, and preflight passes again. If uncertain, stop.
3. **Scientific capture started:** run budget is consumed. Luna must not retry, change domain, tune, or launch a replacement run unless a new task explicitly authorizes it.

This rule prevents both needless checkpoint churn and result-shopping.

## 8. Raw evidence and salvage

Once capture starts, raw artifacts are immutable.

Never edit or overwrite raw data to make a run pass analysis. Record hashes and exact source/runtime provenance.

When evidence is malformed, incomplete, or tooling fails, **offline salvage is preferred over rerunning**.

A deterministic evidence repair is permitted only when:

- raw bytes remain unchanged;
- the repair mapping is unique;
- the mapping is derivable from the frozen runtime source/protocol rather than from whether the outcome looks favorable;
- independent semantic invariants validate the mapping;
- the repair procedure and provenance are recorded.

Do not preregister an overly specific guess about the exact bug shape. Gate on uniqueness and source-grounded recoverability instead.

Historical closeouts are append-only. A later correction may `supersede` an older interpretation but does not erase it.

## 9. Triage order after a run

Do not immediately design another experiment after seeing a failure. Classify the failure boundary first:

1. protocol / execution integrity;
2. evidence/schema integrity;
3. causal comparability / preactivation equality;
4. scientific mechanism / controller behavior.

Stop at the earliest failed boundary. Only when earlier boundaries pass should later scientific conclusions be made.

## 10. Exploratory vs confirmatory

Every task must state one mode:

- **infrastructure:** no scientific claim; repairs/tests/tooling only;
- **exploratory:** bounded debugging or search explicitly authorized in advance; results guide design but are not treated as confirmatory evidence;
- **confirmatory:** intervention, run budget, thresholds and classification rules frozen before live.

Do not force tuning/debugging into a fake one-run confirmatory workflow. Explore when necessary, then freeze and validate separately.

## 11. Minimal task requirements

A new live task does not need a large governance document. It only needs to state:

- mode;
- question;
- exact parent/base;
- scientific change;
- frozen variables;
- run budget;
- measurements/classification;
- runner/run directory;
- task-specific preflight checks, if any.

Everything else comes from this SOP.

## 12. Lessons encoded from this project

The following prior failures are specifically prevented by this SOP:

- invalid DDS domain 233: executor veto + actual DDS port validation;
- omission of `--wall-clock-motion`: baseline runner diff;
- invalid `base x < 0.65` “pre-step” gate: geometry-derived scientific gate review;
- 780/776 V2 CSV mismatch: mandatory no-live schema test when telemetry changes;
- over-specific “empty header token” recovery assumption: evidence repair based on uniqueness/source invariants, not a guessed defect shape;
- repeated new checkpoints for repairable pre-capture infrastructure failures: pre-capture autonomous repair policy.

## 13. Authority

For checkpoints that explicitly adopt this SOP, authority is:

1. frozen scientific design in the current task;
2. this SOP for execution, veto, retry, evidence and provenance rules;
3. accepted parent/baseline evidence;
4. historical documents.

A task may intentionally change a scientific variable, but it may not disable executor veto, evidence immutability, or the no-result-shopping rule merely by omission.

`docs/research/PHASE1_AGENT_CONTRACT.md` remains historical authority for checkpoints that were created under it. New tasks should cite this SOP instead.

## 14. Versioning

Current SOP version: **v0.1**.

Keep versioning lightweight. Change the version only when the actual operating rules change. Git history is the changelog; no separate release process is required at this stage.
