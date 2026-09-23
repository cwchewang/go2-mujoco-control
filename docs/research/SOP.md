# Research Execution SOP v0.4

Applies prospectively. Sealed experiments retain their original protocol and
interpretation. The normal path is task → applicable qualification → fresh
preflight → authorized capture → verified closeout.
The [operating guide](../OPERATING_GUIDE.md) covers goal alignment and handoff.
Governance/prose tasks stop at their relevant documentation checks; the capture
path below is only for tasks that actually require an experiment.

## Authority and roles

User instructions define authorization. The active task freezes its scientific
question and design; this SOP governs execution and evidence. Historical results
provide context, not new run permission. Science reviewer owns interpretation;
an independent execution reviewer owns readiness and may veto unsafe or invalid
execution. Roles are capabilities, not model brand names.

A short task states its purpose, mode, parent, scope and completion criteria.
Experiments additionally specify scientific delta, frozen variables, budget,
metrics, classifications, stop conditions, runner and raw root. Reference
existing protocols rather than copying them. One branch per coherent task;
predeclared repeats share the branch.

Before scientific execution, the task must explain the decision served, why the
chosen comparison/parameters fit that decision, and what each possible outcome
changes. Defaults and unverified assumptions remain labelled as such. An
engineering integration candidate is not automatically the chosen capability
baseline. Check this substantive rationale during scientific review, not merely
the presence of a protocol, hashes or complete fields. The short
[task template](TASK_TEMPLATE.md) supplies these fields without another registry.

## Qualification and change review

Runtime, model, protocol, schema or primary interpretation changes require
relevant no-live regression checks and independent scientific review. Execution
plumbing must be reviewed for trajectory neutrality. Documentation-only changes
do not require a repeat scientific judgment; record their relationship to the
accepted implementation and review current execution identity before live.

Substrate prepare requires a sealed clean/non-development qualification receipt.
Its content fingerprint binds tracked runtime/tests/build inputs, model assets,
actual isolated runtime, interpreter, checkpoint, native dependencies and binary,
controller build products and compiler header/link dependencies. Current
lightweight quality checks always rerun, including prose/link hygiene. Selected
protocols must belong to the fingerprinted protocol directory; their positive
integer budget is bound to preparation and explicit authorization.
Changed inputs invalidate reuse; matching inputs may reuse offline tests across
documentation or merge commits. Producer HEAD is retained, never rewritten.
Current task, review, exact execution HEAD and user authorization are not cached.

## Fresh preflight

The Go2 Praxis dispatcher requires a canonical TaskSpec resource manifest on
new queued tasks. Declare the `substrate` root for the CTS checkpoint with the
SHA-256 from `tools/substrate/sources.lock.json`, and declare the runtime modules
and exact distribution versions required by that task. The host binds
`substrate` to its trusted `.substrate` directory and probes those modules with
the reliable substrate Python. A missing or mismatched declared resource stops
before Luna starts and consumes no scientific attempt. The worker's own
provisioning and the scientific preparation checks still verify the complete
source lock, model loading, and execution semantics. Older task documents
without a manifest must be reissued under the new contract before dispatch;
do not silently relax this gate to replay them.

Before capture, the runner continuously holds the experiment lock through
preflight and the whole campaign. Check exact HEAD, expected logical branch
identity, and clean worktree. A named expected branch remains valid for manual
execution; a detached Praxis v2 worktree requires the complete matching Praxis
binding and exact frozen commit. Also check current inputs, fresh output, no
stale runtime processes, and transport-specific constraints. DDS uses actual
domain/port checks; reviewed in-process runners have no fictitious DDS
requirement. Never run a real runner as a preflight test.

Use the accepted parent as diff-base. Automatically classify changed runtime,
runner, schema, scene and analyzer files; explicit surfaces add to this set.
Any runner change records its actual diff, including explicit runner declarations.
Verified applicable qualification replaces duplicate offline tests; it never
replaces fresh lock/process/input checks. Unknown executable substrate files
are conservatively runtime changes. Failed prerequisites prevent launch.

## Attempts, exploration and stopping

The first valid post-handoff state/control sample consumes an attempt, reserved
durably before logging. Prelaunch execution-only faults may be repaired while
preserving failed artifacts. A proven execution-only boot fault may receive one
recovery only if the task permits it. A stricter frozen task overrides this default.

No opportunistic retry, replacement, threshold change or sample selection after
capture. Safety failures and broken execution/evidence stop. A task may predeclare
an exploratory matrix whose expected performance failures are retained outcomes
and whose remaining cases continue; that permission must exist before results.
Confirmatory designs freeze intervention, comparisons, sample plan and stopping.
The sealed rl-flat-compatibility-v1 campaign remains first-nonpass-stop, no retry.

## Evidence and interpretation

Raw evidence is append-only across runs and immutable within a sealed run.
Record source/inputs, environment, command, attempt ledger and terminal status.
Verify capture independently; local verification includes the external ledger.
Portable verification must explicitly say the external ledger was not checked.
Shared runtime formulas are supplemented by independent algebraic checks;
model contact reconstruction is a separate zero-integration audit, not replayed
dynamics or proof of causal attribution.

Deterministic offline salvage is allowed only with unchanged raw bytes, unique
source-grounded mapping and independent invariants. Corrections are new artifacts
and superseding interpretation, never rewriting history. Distinguish execution,
evidence, causal inference and scientific performance boundaries.

Repeated deterministic traces test repeatability, not statistical success rates.
Capability comparisons need a prospective task/terrain/seed or perturbation plan,
information and compute conditions, uncertainty reporting and declared exclusions.
Check pretrained-policy deployment semantics before attributing transfer failure
to policy quality. Same robot name is not equal physics or equal task distribution.

## Closeout and navigation

For experiments, the usual tracked artifacts are RESULTS.md, analysis.json and
provenance.csv. Routine engineering and documentation work use only the records
needed to support their actual claims; do not manufacture empty data artifacts.
Archive source-bound raw evidence, including failed outcomes and the ledger,
verify archive members, then regenerate the workspace catalog. Do not duplicate
protocol text or state records across manually maintained status pages.

docs/research/current.json owns execution navigation; CURRENT.md and START_HERE
are generated views. PROJECT_RECORD owns research conclusions; TOPIC_AUDIT changes
only when topic judgment changes. Historical branch/worktree cleanup is a separate
owned maintenance action, never implicit deletion during an experiment.
