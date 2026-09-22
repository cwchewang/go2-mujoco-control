# SUBSTRATE_GATE_0 benchmark v0 design closeout

Task: `px_1a0c7feca02_97025cbb46`

Task commit: `d650147127eda95a6caeb9e4e7c3a457fc091c5c`

Exact parent/base: `b1cec66f446c34e850c9caeeac82de52805a3889`

Dispatch branch: `research/praxis-px_1a0c7feca02_97025cbb46`

Working-tree state: detached `HEAD` at the exact task commit; the existing
read-only `origin/<dispatch branch>` ref matched `HEAD`.

Proposed status: `OFFLINE_SPECIFICATION_COMPLETE_PENDING_SOL_REVIEW`

## FACTS

- The exact canonical parent evidence was read from
  `docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md`.
- `origin/main` and the exact task parent both resolve to
  `b1cec66f446c34e850c9caeeac82de52805a3889`.
- The source inventory covers the unchanged Go2 model, checked-in flat/step/
  repeated-step scenes, holdout candidates, legacy composite/generated terrain,
  current runner/analyzer surfaces, and absent future backend adapters.
- The formal design is in
  `docs/research/TASK_SUBSTRATE_GATE_0_BENCHMARK_V0_20260922.md`.
- The field-level benchmark specification is in `SPEC.md` in this directory.
- Source hashes used for the inventory are in `provenance.csv`.
- The clean Raibert+SRBD+WBC baseline remains reference-only; no new capability
  or terrain result is claimed.

## BENCHMARK_V0

The design freezes the comparison shape: one unchanged `go2.xml` model,
immutable hashed scenario assets, common task goals, a backend-neutral
observation/action boundary, harness-only ground truth, common terminal
taxonomy, resource metrics, required provenance, and deterministic run IDs.

It registers flat, 5 cm, 10 cm, repeated-step, and existing holdout assets as
source-backed candidates. Stairs/rough/hfield assets remain adapter- or
generation-manifest-dependent. Reactive obstacle and low-friction assets are
diagnostic/excluded from the geometry-focused Gate 0 registry.

## ASSET_GAPS

- There is no Gate 0 manifest loader or backend-neutral analyzer.
- MJPC/iLQR and DIAL/MPPI implementations are absent from this repository.
- The published RL checkpoint identity and action/observation adapter are
  absent; no external checkpoint was downloaded or executed.
- Existing terrain scenes lack uniform semantic goal metadata, and generated
  terrain lacks a frozen recipe/seed/output manifest.

## UNRESOLVED_FOR_SOL

Final case membership, goal planes, start states, horizon/stability window,
repeats/seeds, all numerical gates, control cadence/action scaling, backend
versions/adapters, checkpoint provenance, resource normalization, and generated
terrain admission remain explicitly unresolved. Existing Phase-2 thresholds
were not copied into Gate 0.

## NO_LIVE_VALIDATION

- No simulator/controller pair, DDS process, MJPC, DIAL/MPPI, or RL policy was
  launched.
- No scientific attempt was consumed and no raw `_runs` evidence was read for
  mutation, renamed, deleted, or overwritten.
- Only the allowed documentation surfaces were changed: `docs/research/` and
  `docs/validation/`.
- Read-only checks completed: exact HEAD/parent/ref comparison, source/hash
  inventory, documentation references, and post-edit `git diff --check`.
- The explicit worker guardrail forbids commands that write Git metadata, so the
  AGENTS.md `git fetch origin --prune` refresh was not attempted. Existing
  `origin/main` and dispatch refs were used read-only and matched the supplied
  exact task/base facts.

## NEXT_GATE

Sol reviews and resolves the listed fields. A separate task must then add and
validate adapters/manifests offline before any task may authorize a live Gate 0
run. This zero-attempt design task does not authorize that run.

Changed paths intended by this closeout:

- `docs/research/TASK_SUBSTRATE_GATE_0_BENCHMARK_V0_20260922.md`
- `docs/validation/substrate_gate_0_benchmark_v0/SPEC.md`
- `docs/validation/substrate_gate_0_benchmark_v0/RESULTS.md`
- `docs/validation/substrate_gate_0_benchmark_v0/provenance.csv`
