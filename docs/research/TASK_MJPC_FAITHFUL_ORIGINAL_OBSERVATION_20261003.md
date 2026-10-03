# Faithful original-only fixed-input observation

Parent: TASK_MJPC_CLOSED_TRACE_DIAGNOSIS_20261003.md; accepted diff-base 8915b0de1cc1dba661cc9e68fa50ddd021105a73.
Mode: bounded diagnostic, private optimizer observation, zero canonical integration.
Branch: research/mjpc-faithful-original-observation-20261003.
Authorization: direct user continuation instruction on 2026-10-03 requests two repeats / four solves / 16384 reserved private steps, no A/B rerun, no extra approval.

## Decision and causal boundary
Decide whether repairing the observer's live reset and named joint encoding closes the initial-solve mismatch, and identify remaining planner/worker mechanisms. Sealed A external inputs tick 0..10 are replayed without feeding observer controls back into a plant. All historical captures and thresholds remain immutable. The instrumented original optimizer binary is reused byte-for-byte; it is not the historical A binary, so matching does not establish full later trajectory reproduction.

## Frozen comparison
Two original-only fresh processes, each constructor then production live reset and ticks 0..10 with the production named-state encoder. Only tick0 and tick10 replan. Four workers; existing horizon36, dt0.01, derivative skip0, ten nominal rollouts; unchanged original duplicate t34 schedule. Binary92f7056463ae1f12cceea09b377712647716682254d3b911ce11d0e52bbe7f4b; MJPCe00c47a5adb9856af2e0f24231bb3a60d5be23c4. No fixed variant or new smoke optimizer. Bounds: four4096 reservations=16384; source-derived accounted upper four2501=10004; canonical0. Wall300s, native response30s. Report exact differences and original1e-9 comparison; do not widen thresholds.

## Qualification and readiness
New applicable no-optimizer-smoke qualification binds clean task HEAD, all tracked runtime/test/model inputs, Python executable, CPU, checkpoint/source lock, immutable native build provenance, sealed ELF loader/libraries/model dependency closure, and source A manifest/raw. Relevant changed reset/mapping/runtime/transport and observer tests rerun, native zero-integration checks and current quality rerun. The historical optimizer evidence is reused only for unchanged native implementation. No new calls are spent on qualification.
Owner deterministic PRECHECK precedes genuine independent science/execution review, both bind exact HEAD and packet hash. Execution holds experiment lock continuously across fresh identity/process/path/hash checks and entire pair.

## Outcomes and stopping
Output _runs/mjpc_faithful_original_observation_20261003, fresh and outside sealed bundles. Campaign reservation created exclusively before launch, per-call durable4096 reservations before request; existing output forbids duplicate execution. Identity/integrity/warning/budget/transport failure stops at first occurrence without retry/replacement. Numerical differences are retained observations; both predeclared repeats proceed if execution evidence remains valid.
If both match A within1e-9 and each other, observer defects explain the previous coarse mismatch but do not identify A/ref's2.68e-11 initial drift. If repeats differ at identical inputs, inspect FD Jacobian/policy/warmstart/event evidence for nondeterminism without claiming hidden A worker state. If stable repeats differ from A, remaining reset/configuration/instrumentation history is implicated, not canonical feedback. Deliver all11-tick control/cost comparisons, exact counters, sealed evidence, first drift and causal limits. Old A CLOSED_NO_RETRY; B NOT_RUN_REPRODUCTION_GATE_FAILED; R4/12s unchanged.
