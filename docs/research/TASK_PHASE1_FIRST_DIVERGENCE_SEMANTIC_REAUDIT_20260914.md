# Phase 1 first-divergence semantic re-audit — 2026-09-14

## Authority and scope

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first and obey it.

This is an **offline evidence re-audit only**. It exists because the prior closeout at `6fe262a0e0dc88e145ac1a78dd6ca95f86bbc0a3` may have over-classified the earliest divergence as `SIMULATOR_DIVERGENCE`.

- Parent evidence commit: `6fe262a0e0dc88e145ac1a78dd6ca95f86bbc0a3`
- Working branch: `research/phase1-first-divergence-semantic-reaudit-20260914`
- Prior raw captures: the existing L1/L2/L3 `mj_snapshot.bin` files under `_runs/phase1_frozen_handoff_first_divergence_20260914/`
- **No new simulator/controller live runs are authorized.**
- D4 and all causal interventions remain OFF and must not be run.
- Do not overwrite or rewrite the prior `RESULTS.md`; preserve it as historical evidence and place this review in a new validation directory.

The executor must use the existing local raw captures if their SHA-256 hashes match `docs/validation/phase1_frozen_handoff_first_divergence_20260914/run_provenance.csv`. If those raw files are unavailable or hashes do not match, stop with a blocker. Do not regenerate them.

## Why this re-audit is required

The prior analyzer `example/cpp/tools/analysis/analyze_phase1_frozen_handoff_first_divergence.py` has two relevant assumptions that must be reviewed before accepting the simulator attribution:

1. At each record it compares the **entire** `mjSTATE_INTEGRATION` byte vector before explicit LowCmd / bridge / `mjData.ctrl` fields. But `mjSTATE_INTEGRATION` is not purely plant state: it also includes control/user input state such as `ctrl`.
2. After a record whose pre-state and explicit control fields compare equal, it checks the **next record's** full integration state and immediately labels any difference `SIMULATOR_DIVERGENCE`. The logger captures the next record in the next `Begin()` call, not as a full integration-state snapshot inside the previous `End()`. Therefore intervening command/bridge writes between the previous `End()` and next `Begin()` must be excluded before a next-record difference can be attributed to `mj_step` itself.

The prior pairwise results all reported their first differing integration scalar as `state[56]` around 12.300–12.304 s. That index must be mapped to its actual MuJoCo state component before any causal label is accepted.

## Preregistered question

Using only the already-captured L1/L2/L3 GO2PDSNP v2 files, what is the earliest **semantically valid causal boundary** at which the runs cease to be identical?

The re-audit must distinguish at minimum:

1. non-control integration/plant state;
2. bridge-observed sensor state;
3. LowCmd;
4. bridge-computed actuator control;
5. actual `mjData.ctrl` at snapshot `Begin()`;
6. immediate post-`mj_step` observable already present in v2 (`qacc0_after`);
7. next-record integration state, with its component identity explicitly mapped rather than treated as a monolithic simulator output.

## Stage 0 — source-level audit, no runtime

Before changing analysis code, inspect the exact parent sources and record in the result:

- serialization order of `CounterfactualSnapshotLogger::Begin()` and `End()` in `simulate/src/main.cc`;
- where `mj_getState(..., mjSTATE_INTEGRATION)` is called;
- when `pending_snapshot_ctrl_` / actual `d->ctrl` is captured;
- what `End()` records after `mj_step`;
- what can execute between `End()` of record *i* and `Begin()` of record *i+1*, especially bridge/command publication or application;
- the old comparator's ordering and its special `next_state => SIMULATOR_DIVERGENCE` rule.

This audit must answer whether the full next-record integration state is guaranteed to be an immediate, uncontaminated post-step state. Do not assume that it is.

## Stage 1 — prove the state-component mapping from existing evidence

Do not merely infer `state[56]` from a hand-written offset formula. Prove the mapping using at least one of these methods, preferring both when convenient:

### Method A — capture-internal byte identity

For records around the reported first divergence, test aligned `mjtNum` slices of `state_raw` against the separately serialized `actual_ctrl_raw` from the same `Begin()` call. If a 12-scalar integration-state slice is byte-identical to all 12 actual `mjData.ctrl` values in the same record, across multiple neighboring records and all three runs, report the exact state index range and treat that as direct evidence for the `ctrl` component location.

### Method B — exact-model MuJoCo introspection

Using the exact scene/model and MuJoCo build already identified by provenance, inspect the `mjSTATE_INTEGRATION` component layout without stepping the simulation. A tiny one-shot utility or existing API may be used. Do not launch a locomotion run.

The result must explicitly state what `state[56]` is. If it cannot be established, return `UNRESOLVED_STATE_COMPONENT` and stop.

## Stage 2 — corrected offline comparator

Create a new analyzer; do not mutate the historical CSV in place. Suggested path:

`example/cpp/tools/analysis/analyze_phase1_frozen_handoff_semantic_reaudit.py`

It may reuse/import the v2 decoder from the previous analyzer.

The corrected comparison must not allow a control/user-input component embedded in `mjSTATE_INTEGRATION` to pre-empt the explicit causal fields that duplicate it.

At each aligned record, compare and report in a semantically meaningful order:

1. record/time alignment;
2. integration-state components that are genuinely upstream plant/solver state, with `ctrl` separated explicitly;
3. bridge sensor q/dq;
4. LowCmd (`q,dq,kp,kd,tau_ff`);
5. bridge-computed ctrl;
6. actual `mjData.ctrl` captured at `Begin()`;
7. contact metadata / bridge sequence metadata as supporting diagnostics;
8. `qacc0_after` from `End()`.

Then inspect the next record, but **do not** classify a difference as simulator-side solely because `state_raw` differs. First identify the differing state component and compare the next record's explicit fields. In particular, if the next-record difference is in the `ctrl` slice and the separately logged next-record `actual_ctrl` differs the same way, that is not evidence that `mj_step` itself generated the difference.

A simulator-side attribution is allowed only when the evidence establishes that identical relevant pre-step integration/plant state and identical applied inputs produced a different immediate simulator result, or when a differing next-record state component is proven to be modified only by the simulator step with no intervening writer path. Calibrate the label to the actual evidence.

## Required pairwise output

For L1-L2, L1-L3, and L2-L3, write a machine-readable table with at least:

- pair;
- earliest semantic divergence record/tick;
- state component, if any;
- field/index;
- value A / value B / delta where numerical;
- upstream fields known equal at that point;
- classification;
- evidence note explaining why the classification is causally valid.

Also write a small component-map artifact showing the established integration-state index ranges relevant to this incident, especially the `ctrl` range.

## Decision labels

Use exactly one top-level result label:

- `ORIGINAL_SIMULATOR_CLASSIFICATION_CONFIRMED` — the prior simulator attribution survives component-aware review with sufficient causal evidence.
- `ORIGINAL_CLASSIFICATION_OVERTURNED_CONTROLLER_OR_TRANSPORT` — the first supported difference is upstream of bridge application and the existing v2 evidence cannot distinguish controller from its input/transport.
- `ORIGINAL_CLASSIFICATION_OVERTURNED_BRIDGE` — LowCmd/upstream state remain equal but bridge-computed or actual applied control is first to differ.
- `ORIGINAL_CLASSIFICATION_OVERTURNED_PREEXISTING_STATE` — a genuine non-control plant/solver input state is already different before the candidate step.
- `UNRESOLVED_REQUIRES_POSTSTEP_CAPTURE` — existing v2 evidence cannot distinguish an intervening write from simulator evolution; a future checkpoint with an immediate full post-`mj_step` state snapshot is required.
- `UNRESOLVED_STATE_COMPONENT` — the state component containing the first differing scalar cannot be established.
- `PROTOCOL_FAILURE` — existing artifacts/provenance do not match the preregistered evidence.

Do not preserve `SIMULATOR_DIVERGENCE` merely for consistency with the old report; the purpose of this checkpoint is independent adjudication of that claim.

## Deliverables

Commit only derived review evidence and analysis code appropriate for the repository:

- `docs/validation/phase1_first_divergence_semantic_reaudit_20260914/RESULTS.md`
- `docs/validation/phase1_first_divergence_semantic_reaudit_20260914/first_divergence_semantic.csv`
- `docs/validation/phase1_first_divergence_semantic_reaudit_20260914/state_component_map.csv`
- corrected/new offline analyzer used for the review

Record the original raw capture SHA-256 values and prove they match the parent provenance. Do not commit the raw binaries.

## Stop rule

After the offline re-audit, commit and push the closeout to this branch, verify a clean worktree and remote SHA, then STOP.

Do not run a new simulator experiment, do not add post-step instrumentation yet, do not fix MuJoCo settings, do not run D4, and do not autonomously begin the next checkpoint. If immediate post-step state capture is required, recommend it as the one next step only.