# Phase2 known-step V2 same-binary A/C

Mode: `confirmatory`

SOP: `docs/research/SOP.md` v0.2
Parent: `867a5668d355fe4c77ef0063c393349d3819459d`
Branch: `research/phase2-known-step-v2-same-binary-ac-20260915`

## Question

Does edge-aware known-step V2 enable the original 5 cm traversal outcome when compared against a fresh V2-off baseline produced by the **same controller/simulator binaries**?

## Delta from parent

The parent recovered the C evidence but classified it `INCONCLUSIVE_PREACTIVATION_DIVERGENCE` because the historical A and C came from different runtime binary lineages.

This checkpoint replaces only that comparator design. Run one fresh A followed, conditionally, by one fresh C from one build:

- A: V2 disabled.
- C: V2 enabled.
- Build once before A; do not rebuild or modify source between A and C.
- Controller binary SHA-256 and simulator binary SHA-256 must be identical across A and C.
- Domains and run directories may differ as execution metadata; choose valid free domains through preflight rather than hard-coding a scientific value.

No controller/planner/scene/gait/WBC/MPC/ID/safety/threshold change is authorized.

## Frozen scientific design

Use the original V2 intervention, scene, locomotion configuration, measurements, thresholds, traversal criteria, and classification precedence from:

`docs/research/TASK_PHASE2_KNOWN_STEP_EDGE_AWARE_V2_20260915.md`

unchanged.

Fresh A/C exact preactivation equality through the row strictly before first C V2 crossing latch remains mandatory. If it fails, classify `INCONCLUSIVE_PREACTIVATION_DIVERGENCE` and do not reinterpret the old C result.

A must complete the original required baseline/protocol health gates before C is launched. If A fails those gates, stop without C.

Run budget: at most one scientifically consumed A and one scientifically consumed C, subject to SOP v0.2 pre-capture recovery rules.

## Execution requirements

Before live:

- run `tools/research/preflight.py` on the exact prepared/reviewed HEAD;
- use `--diff-base 867a5668d355fe4c77ef0063c393349d3819459d`;
- run the existing no-live CSV schema regression and relevant build/unit tests;
- verify the current fixed logger emits a valid schema;
- independently inspect the actual runner/config diff against the accepted V2 configuration;
- record the one built controller/simulator hashes that both arms will use.

Luna may make minimal execution-only runner/tooling repairs under SOP v0.2. Any runtime-semantic or primary-evidence-semantic change requires veto and Sol review before live.

## Closeout

Default outputs only: `RESULTS.md`, `analysis.json`, `provenance.csv`; add another table only if it is necessary evidence.

Record A/C raw hashes, exact runtime HEAD, identical binary hashes, preactivation result, protocol/evidence gates, and the single original V2 scientific classification.

Commit/push and stop. Do not tune or launch a follow-up experiment.