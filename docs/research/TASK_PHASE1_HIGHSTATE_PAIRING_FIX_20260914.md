# Phase 1 deterministic HighState pairing repair — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first.

## Handoff

- Parent evidence SHA: `d9b92581a302b27c3205e466fbbe48d3a412f2a5`
- Branch: `research/phase1-highstate-pairing-fix-20260914`
- Parent result: `docs/validation/phase1_highstate_semantic_reaudit_20260914/RESULTS.md`
- Accepted cause: `HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD`
- D4 and all other locomotion interventions: OFF.

This is the first authorized repair checkpoint. Do not tune gait, WBC, gains, solver settings, velocity semantics, or performance parameters.

## Established evidence

At the first LowCmd divergence, aligned bridge LowState and HighState physical payloads are still equal and consumed LowState is equal, but the controller consumes different HighState freshness: one run uses the current physics-tick HighState and another an earlier publication. Pairwise first LowCmd divergences are 12302 / 12304 / 12302 ms. Therefore the repair target is only the LowState/control-tick ↔ HighState association.

## Required repair invariant

In lockstep repair mode, the LowCmd generated for physics tick T must consume HighState position/velocity produced from the same locked MuJoCo state and the same tick T as the LowState that triggered that control cycle.

Do not solve this with sleeps, callback counters, polling delays, blocking HighState publication alone, or an assumption that two DDS topics preserve cross-topic ordering. The association must be carried atomically or be explicitly keyed by tick.

## Authorized implementation

Use the existing simulator-only LowState auxiliary transport pattern. Before editing, audit all uses of `motor_state[18]` and `[19]`. They must be unused by active control, safety, logging, and existing sidebands. Record the audit in `RESULTS.md`. If they are not free, stop as `IMPLEMENTATION_BLOCKER`; do not invent another protocol.

If free, implement a lockstep-only sideband gated by `TROT_LOCKSTEP_PAIRED_HIGHSTATE=1` and active only with `SIM_LOCKSTEP=1`:

- Bridge: while constructing LowState tick T from the locked `mj_data_`, encode the same-tick HighState `position[0:3]` and `velocity[0:3]` plus source tick/version marker into slots 18/19 before LowState publish.
- Do not change active motor slots 0..11 or the existing auxiliary slots 12..17.
- Keep the independent HighState DDS publication unchanged for normal/diagnostic consumers.
- Controller: in `SnapshotState()`, after copying `state_snapshot`, validate/decode the paired sideband and construct `high_state_snapshot` from it. In paired mode, control math must not use the asynchronous cached `high_state_`.
- Marker/version/tick mismatch must fail closed in paired mode; never silently fall back to asynchronous HighState.
- With paired mode disabled, historical behavior must remain unchanged.
- Boundary tracing must record the HighState actually consumed by control math, not the stale asynchronous cache.

A compact suggested encoding is documented by the implementation itself; preserve all six HighState floats exactly as float values and carry an exact source tick plus marker/version. Do not repurpose any field found to have an existing semantic use.

## Tests before live runs

Add focused tests proving:

1. pack/unpack preserves all six HighState float fields exactly;
2. decoded source tick must equal LowState tick;
3. invalid marker/version/tick fails closed in paired mode;
4. paired mode disabled preserves historical `SnapshotState()` behavior;
5. slots 0..17 are unchanged by the new sideband;
6. inherited lockstep writer/ack tests still pass.

Run the new focused tests, established controller lockstep tests, and `bash simulate/src/tests/run_lockstep_sim_tests.sh`. No live run before all pass.

## Prepared tools

Use only:

- `example/cpp/scripts/run_phase1_highstate_pairing_fix.sh`
- `example/cpp/tools/analysis/analyze_phase1_highstate_pairing_fix.py`

The runner enables paired mode, preserves the accepted varying-speed baseline, keeps D4/interventions off, records the 11800–12600 boundary window and the 7.999–13.0 MuJoCo snapshot window.

## Live matrix

After the implementation commit and tests, run exactly once each, sequentially:

```bash
bash example/cpp/scripts/run_phase1_highstate_pairing_fix.sh L1
bash example/cpp/scripts/run_phase1_highstate_pairing_fix.sh L2
bash example/cpp/scripts/run_phase1_highstate_pairing_fix.sh L3
```

No retries and no replacement run IDs. Preserve failed runs.

Then run:

```bash
python3 example/cpp/tools/analysis/analyze_phase1_highstate_pairing_fix.py \
  --runs-root example/cpp/experiments/_runs/phase1_highstate_pairing_fix_20260914 \
  --output-dir docs/validation/phase1_highstate_pairing_fix_20260914
```

Also run the existing `analyze_phase1_frozen_handoff_first_divergence.py` on the three new `mj_snapshot.bin` files and save its CSV in the validation directory. Interpret it component-semantically; its historical simulator label is not authoritative.

## Acceptance gates

Full validation requires all of the following:

1. L1–L3 lockstep protocol passes: constant 2 ms ticks, zero violations, exactly one command update per state tick, no fail-closed marker.
2. Every lockstep control cycle in paired mode validates marker/version/source-tick == consumed LowState tick; no asynchronous fallback.
3. In ticks 11800–12600, no pair has a value-carrying consumed HighState divergence and no pair has a pre-publish LowCmd divergence.
4. In the 7.999–13.0 s snapshot window, there is no component-aware value divergence across L1/L2/L3.
5. Across the full baseline run, all selected deterministic metrics used by `analyze_phase1_lockstep_baseline.py` have pairwise maximum absolute difference exactly 0, aligned row counts match, and terminal/status outcomes match.
6. All three runs reach the same terminal outcome without posture failure.
7. Build/runtime provenance matches except expected run/domain identifiers; raw artifacts are immutable and SHA-256 hashed.

Do not relax exact-zero thresholds after seeing results. If the HighState causal window is fixed but a later divergence remains, close as a partial repair; do not tune or add runs.

## Classification

Use exactly one:

- `FIX_VALIDATED_FULL_BASELINE_REPRODUCIBLE`
- `FIX_REMOVES_HIGHSTATE_CAUSE_BUT_OTHER_DIVERGENCE_REMAINS`
- `FIX_FAILED_HIGHSTATE_PAIRING_PERSISTS`
- `INSTRUMENTATION_OR_FIX_PERTURBATION`
- `PROTOCOL_FAILURE`
- `IMPLEMENTATION_BLOCKER`

Only `FIX_VALIDATED_FULL_BASELINE_REPRODUCIBLE` can justify a later return to D4. Do not run D4 here.

## Deliverables and stop

Commit/push implementation, tests, `docs/validation/phase1_highstate_pairing_fix_20260914/RESULTS.md`, boundary/full-run tables, snapshot first-divergence CSV, and provenance hashes. Record implementation commit SHA and final closeout SHA. Recommend one next checkpoint but do not execute it. Push this branch and STOP. No merge to main.