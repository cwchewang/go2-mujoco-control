# Phase 1 HighState semantic re-audit — 2026-09-14

## Authority

Read and obey `docs/research/PHASE1_AGENT_CONTRACT.md` first.

This task starts from accepted boundary-instrumentation closeout SHA:

- parent evidence SHA: `859bb66f7d9dfe712bd7cd58186f99541ebc8e33`
- working branch: `research/phase1-highstate-semantic-reaudit-20260914`
- parent result: `docs/validation/phase1_lowstate_highstate_lowcmd_boundary_20260914/RESULTS.md`
- parent top-level label: `HIGHSTATE_PUBLICATION_PAIRING_DIVERGENCE`

This task is an **offline semantic re-audit only**. Reuse the existing local L1/L2/L3 boundary raw captures from the parent task. Do not start the simulator, controller, or any new live run. Do not modify the raw captures. Do not repair HighState publication, DDS, lockstep, controller logic, gait, WBC, D4, or any locomotion parameter.

## Why this re-audit is required

The parent analyzer currently scans each common tick and returns at the first difference. At the bridge HighState boundary it compares fields in this order:

`high_hash`, `high_source_generation`, `high_source_tick`, `high_skipped`.

At tick 11800, the parent result reports different `high_source_generation` values across all three pairs, but the bridge canonical HighState payload hashes at that same tick are equal, and the LowCmd hashes are still equal. Therefore the parent label correctly detects a publication-history/pairing difference, but it is not yet sufficient to claim that a **value-carrying controller input difference** caused the later LowCmd divergence.

The semantic re-audit must distinguish diagnostic metadata divergence from canonical payload divergence and must align the actual consumed HighState value lineage to the first LowCmd payload divergence.

## Research question

For each pair L1–L2, L1–L3, and L2–L3, what is the first **value-carrying** divergence in the causal path:

`bridge LowState/HighState canonical payload -> controller receipt payload -> exact consumed LowState+HighState tuple -> pre-publish LowCmd payload`?

Specifically:

1. Is the first `high_source_generation` difference at tick 11800 metadata-only, or does it correspond to a different HighState canonical value actually consumed by the controller?
2. What is the first tick at which the controller consumes a different HighState payload while LowState payload remains equal?
3. What is the first tick at which pre-publish LowCmd payload differs?
4. At that LowCmd-first-divergence tick, are the consumed LowState and HighState canonical payloads identical or different?
5. If consumed HighState differs, can it be traced to a different publication/receipt generation or freshness choice while the underlying bridge physical HighState at the same physics tick is equal?

## Semantic rules

### Metadata is not payload

Treat the following as diagnostic metadata, not by themselves causal physical input values:

- `high_source_generation`
- callback / receipt sequence numbers
- controller control sequence numbers
- publication skip counters
- raw row order or wall-clock timing metadata

A metadata difference may explain *why* a different payload was selected, but it is not itself sufficient to classify a value-carrying input divergence.

### Canonical payloads are authoritative

Use the canonical serialized payloads/hashes already defined by the parent instrumentation:

- LowState canonical payload: tick + active motor q/dq/tau_est + IMU + foot-force fields;
- HighState canonical payload: position + velocity;
- LowCmd canonical payload: q/dq/kp/kd/tau for 12 motors.

Do not hash raw C++ structs or DDS memory.

For every differing canonical hash, verify by payload bytes and decode the first differing semantic field/value. Hash inequality alone is not the final report.

### Alignment

Primary alignment is the controller control cycle / consumed LowState tick used by the parent traces, not wall-clock time.

Do not compare unrelated callback sequence numbers directly across independent process runs as if equal numeric sequence values implied equal freshness. Instead, within each run, trace each `controller_consumption` record to the actual `controller_receipt_high` record identified by `consumed_high_receipt_seq`, and trace that receipt to its canonical HighState payload and available bridge source-generation/source-tick evidence.

## Required pairwise audit

For each of L1–L2, L1–L3, L2–L3, compute and report all of the following independently rather than stopping at the first item:

1. earliest metadata-only HighState publication-history divergence;
2. earliest bridge canonical LowState payload divergence, if any;
3. earliest bridge canonical HighState payload divergence, if any;
4. earliest controller LowState receipt canonical payload divergence, if any;
5. earliest controller HighState receipt canonical payload divergence, if any;
6. earliest consumed LowState canonical payload divergence, if any;
7. earliest consumed HighState canonical payload divergence, if any;
8. earliest consumed LowState+HighState tuple value divergence;
9. earliest pre-publish LowCmd canonical payload divergence;
10. first semantic field/value difference for items 3, 5, 7, and 9 when they exist.

At the pair's first LowCmd payload divergence, emit a causal snapshot containing:

- control/LowState tick;
- LowState payload equality + hashes;
- HighState payload equality + hashes;
- consumed Low/High receipt sequence identifiers within each run;
- decoded HighState position/velocity values for both runs;
- decoded first differing LowCmd field and values;
- bridge HighState payload/hash at the same physics tick for both runs;
- bridge HighState source-generation/source-tick/skip metadata for context;
- whether the consumed HighState payload corresponds to the bridge payload from the same physics tick, an earlier available publication, or cannot be mapped unambiguously from existing traces.

Also report the most recent control tick *before* LowCmd divergence at which the entire consumed tuple and LowCmd payload are equal.

## Required classifications

Use exactly one top-level classification from this set, based on the earliest supported **value-carrying** cause of LowCmd divergence:

- `HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD` — bridge physical Low/High payload at aligned physics tick remains equal, but controller consumes a different HighState payload/freshness before or at the first LowCmd divergence, with LowState still equal.
- `HIGHSTATE_SOURCE_PAYLOAD_DIVERGENCE` — canonical bridge HighState payload itself differs before or at first LowCmd divergence while LowState source remains equal.
- `LOWSTATE_VALUE_DIVERGENCE` — canonical LowState payload differs first before or at LowCmd divergence.
- `TRANSPORT_OR_SUBSCRIBER_VALUE_DIVERGENCE` — bridge canonical payload is equal but the corresponding controller receipt canonical payload differs before consumption.
- `CONTROLLER_INTERNAL_DIVERGENCE` — at the first LowCmd payload divergence, the exact consumed LowState and HighState canonical payloads are identical, yet LowCmd canonical payload differs.
- `METADATA_ONLY_NOT_CAUSAL` — metadata/sequence/generation differs, but no value-carrying upstream divergence explains LowCmd within the audited window.
- `INSUFFICIENT_TRACE_TO_ATTRIBUTE` — existing traces cannot map the first LowCmd difference to a value-carrying upstream boundary without new instrumentation.
- `PROTOCOL_FAILURE` — provenance, hashes, trace consistency, or alignment is invalid.

Do not preserve the parent label merely because generation counters differ. Reclassify from semantic payload evidence.

## Window

Audit at least the entire parent captured comparison window `11800–12600` inclusive. If the first LowCmd payload divergence lies outside that range according to the raw traces, stop and classify `INSUFFICIENT_TRACE_TO_ATTRIBUTE`; do not run a new simulation in this task.

## No reruns / no substitutions

The valid input set is exactly the parent L1/L2/L3 raw captures. Verify their SHA-256 values against the parent provenance before analysis. If any file is missing or hash-mismatched, stop with `PROTOCOL_FAILURE`; do not regenerate or substitute a run.

## Deliverables

Create:

- `example/cpp/tools/analysis/analyze_phase1_highstate_semantic_reaudit.py`
- `docs/validation/phase1_highstate_semantic_reaudit_20260914/RESULTS.md`
- `docs/validation/phase1_highstate_semantic_reaudit_20260914/value_boundary.csv`
- `docs/validation/phase1_highstate_semantic_reaudit_20260914/lowcmd_causal_snapshot.csv`
- `docs/validation/phase1_highstate_semantic_reaudit_20260914/provenance.csv`
- optional compact JSON if useful for machine inspection

The analyzer must be offline-only, deterministic, stdlib-only if practical, and must never mutate raw captures.

`RESULTS.md` must explicitly state:

- the parent label and why it required semantic re-audit;
- the earliest metadata divergence versus earliest value-carrying divergence;
- the first LowCmd payload divergence per pair;
- whether consumed HighState value/freshness is causally upstream of it;
- the final single top-level classification;
- whether a live repair experiment is now justified.

## Stop condition

Stop once existing raw evidence either establishes or rejects HighState value/freshness pairing as the upstream cause of LowCmd divergence. Do not implement the repair in this branch.

If and only if the final classification is `HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD`, recommend a separate minimal-fix checkpoint that makes the controller consume a deterministically paired HighState for each LowState/control tick while preserving normal behavior when the diagnostic/fix mode is disabled.
