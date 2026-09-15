# Research Execution SOP v0.2

Status: active for new research checkpoints after adoption. Historical checkpoints keep the rules frozen with them.

This SOP is intentionally small. The normal path should feel like: **short task → preflight → run → closeout**.

## 1. Core rule

**Scientific variables are strict; execution engineering is flexible before live; after scientific capture begins, results may not be selected or retried opportunistically.**

- **Sol** owns the scientific question and final scientific judgment.
- **Luna** independently owns execution readiness and has unconditional live veto.

A task is not permission to bypass a verified infrastructure constraint.

## 2. What a task contains

A task describes the **delta from its exact parent**, not the whole project.

For a live checkpoint it needs only:

- mode: `infrastructure`, `exploratory`, or `confirmatory`;
- question;
- exact parent/base;
- scientific change;
- variables that must remain frozen;
- run budget;
- primary measurements / classification rule;
- runner and run directory;
- genuinely task-specific preflight requirements, if any.

Do not restate SOP rules, parent results, unchanged thresholds, or long historical narratives. Read the current task, this SOP, and the exact parent `RESULTS.md`; consult older tasks only when evidence actually requires them.

## 3. Scientific authority

For confirmatory work, Sol freezes the intervention, baseline, run budget, primary metrics, thresholds/classification, and scientific stop conditions.

Luna must not autonomously change anything that could alter the post-handoff state/control trajectory or the scientific meaning of the primary evidence. This includes speed policy, gait timing, planner mathematics, WBC/MPC/ID behavior, controller gains, scene geometry, safety limits, scientific thresholds, seed/run count, or follow-up experiments.

If uncertain whether a change is execution-only or scientific/runtime-semantic, treat it as scientific and veto live.

## 4. Luna autonomy and veto

Before scientific capture, Luna may independently inspect and minimally repair execution-only issues such as:

- DDS/domain choice, locks and port conflicts;
- paths, run-directory bookkeeping and executable bits;
- runner shell plumbing that is proven trajectory-neutral;
- logger/schema bookkeeping;
- analyzer/tooling plumbing that does not change primary evidence meaning;
- provenance collection, stale process cleanup, and no-live tests.

Luna may add no-live tests without asking.

If the task conflicts with verified source semantics, geometry, protocol limits, accepted evidence, or preflight, Luna must veto rather than weaken an existing guard to obey the task.

## 5. Preflight

Every live run must pass `tools/research/preflight.py` immediately before launch.

Always check:

- exact branch/HEAD and clean worktree;
- runner existence/syntax and actual DDS domain;
- DDS/RTPS port legality, selected safe policy and free lock;
- fresh run directory;
- no stale simulator/controller/runner process;
- task-required files/hashes/tests.

Use `--diff-base <accepted-ref>` whenever an accepted parent/baseline exists. Preflight auto-detects changed execution surfaces from Git diff; `--changed-surface` is only an override/addition.

Change-triggered checks:

- runtime/schema/scene change → at least one relevant no-live/build test;
- schema change → schema regression test;
- primary analyzer semantics change → parser/fixture test;
- runner change → record a baseline runner diff summary and inspect the actual Git diff;
- geometry-dependent scientific gate change → re-derive it from source/scene geometry.

### Sol review gate

Second Sol review is required only when the committed change can alter either:

1. the post-handoff state/control trajectory; or
2. the meaning/mapping/classification of primary evidence.

Runtime, scene and schema changes trigger this automatically. A runner or analyzer change triggers it only when its actual semantics meet one of those two conditions; Luna must pass `--requires-sol-review` in that case.

Pure paths, output locations, report rendering, bookkeeping, or presentation-only analysis changes do not require redundant Sol review.

When review is required, the exact reviewed SHA must equal the live HEAD via `--approved-head`.

## 6. Attempt boundary and retry

A scientific attempt is consumed at the first valid **post-handoff state/control sample** used by the experiment.

- **Prelaunch failure:** no attempt consumed; Luna may fix execution-only issues and rerun preflight.
- **Boot failure before that sample:** no scientific attempt consumed. One automatic recovery launch is allowed only if the cause is proven execution-only, failed artifacts are preserved, scientific/runtime semantics are unchanged, and preflight passes again.
- **Scientific capture started:** run budget is consumed. No autonomous retry, replacement run, domain change, or tuning.

Scientific gate failures stop; infrastructure gate failures before capture may be repaired in the same checkpoint.

## 7. Evidence

Once capture starts, raw artifacts are immutable. Do not overwrite, normalize, or hand-edit raw evidence.

Prefer deterministic offline salvage over rerunning. A repair is scientifically usable only when:

- raw bytes remain unchanged;
- the mapping/repair is unique;
- it follows from frozen runtime source/protocol rather than outcome preference;
- independent semantic invariants validate it;
- derivation and provenance are recorded.

Do not preregister a guessed bug shape when uniqueness/source-grounded recoverability is the real requirement.

Historical conclusions are append-only; a later correction may supersede an interpretation without erasing it.

## 8. Failure triage

After a failed run, identify the earliest failed boundary before designing another experiment:

1. `execution`
2. `evidence`
3. `causal`
4. `scientific`

Do not invent a new generic classification label for every infrastructure failure. Record the boundary plus a specific `reason_code`; scientific labels remain task-specific.

## 9. Exploratory vs confirmatory

- `infrastructure`: tooling/repair only; no scientific claim.
- `exploratory`: bounded search/debugging authorized in advance; useful for design, not confirmatory evidence.
- `confirmatory`: intervention, run budget, thresholds and classification frozen before live.

Do not force tuning into repeated fake one-run confirmatory checkpoints. Explore first when necessary, then freeze and validate.

## 10. Branches and outputs

Create a new research branch for a new scientific question, new live attempt, or runtime-semantic change.

Pure offline correction, evidence salvage, analyzer repair, or additional derived analysis may continue on the same research branch when raw evidence and scientific design are unchanged. Append a new commit/closeout and mark supersession when needed.

Default closeout artifacts are only:

- `RESULTS.md`
- `analysis.json`
- `provenance.csv`

Create extra CSV/tables only when they are actual evidence needed to audit that checkpoint.

Provenance should hash what matters to the conclusion: raw evidence, scene/model/config where relevant, and exact runtime/source/binary identity. Do not hash every derived report by ritual.

## 11. Lessons already encoded

This SOP specifically addresses failures already seen in this project:

- DDS domain 233 → actual RTPS/domain preflight + Luna veto;
- missing `--wall-clock-motion` → runner comparison against accepted baseline;
- invalid `base x < 0.65` pre-step gate → source/scene-derived geometry review;
- 780/776 CSV mismatch → schema regression test before live;
- guessed empty-token recovery rule → general uniqueness/source-invariant evidence recovery;
- unnecessary branch/checkpoint churn → execution repair before capture and same-branch offline corrections.

## 12. Authority and version

For checkpoints adopting this SOP:

1. frozen scientific delta in the current task;
2. this SOP for execution/veto/retry/evidence rules;
3. exact parent/baseline evidence;
4. older history as needed.

`PHASE1_AGENT_CONTRACT.md` remains historical authority only for checkpoints created under it.

Current version: **v0.2**. Git history is the changelog; no separate release ceremony is required.