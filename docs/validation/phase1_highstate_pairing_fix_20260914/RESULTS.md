# Phase 1 HighState pairing fix validation

Top-level classification: `FIX_VALIDATED_FULL_BASELINE_REPRODUCIBLE`

Runtime HEAD: `9bf71c41349dbe0dde8dcbb7b9c76f396c87974e`

- Lockstep protocol: PASS
- Paired HighState runtime validation: PASS
- 11800–12600 consumed-HighState/LowCmd window: CLEAR
- 7.999–13.0 snapshot window: CLEAR (NO_DIVERGENCE_IN_WINDOW)
- Full-run exact selected-metric repeatability: PASS
- Binary/source provenance: PASS

Pairwise boundary table is in `pairwise_boundary.csv`; full-run differences are in `full_run_pairwise.csv`; protocol and paired-runtime gates have dedicated CSVs. Raw artifacts are hashed in `provenance.csv`.

## Closeout

- Parent evidence SHA: `d9b92581a302b27c3205e466fbbe48d3a412f2a5`.
- Implementation commit SHA: `9bf71c41349dbe0dde8dcbb7b9c76f396c87974e`.
- Final closeout SHA: recorded by the pushed closeout commit.
- Authorized runner: `bash example/cpp/scripts/run_phase1_highstate_pairing_fix.sh L1|L2|L3`; each run was executed exactly once with domains 211/212/213.
- Analyzer: `python3 example/cpp/tools/analysis/analyze_phase1_highstate_pairing_fix.py --runs-root example/cpp/experiments/_runs/phase1_highstate_pairing_fix_20260914 --output-dir docs/validation/phase1_highstate_pairing_fix_20260914`.
- D4 and all other locomotion interventions remained off; no tuning, retry, replacement run, or follow-on repair was performed.

## motor_state[18]/[19] audit

The pre-edit audit searched active simulator/controller code, safety paths, logging, and existing auxiliary transport. Motor slots 0..11 are the active Go2 sensor/control fields. The existing dynamics auxiliary writer covers only motors 12..17: 42 fields are packed as the 6x6 mass matrix and six base bias values. No active reference or writer uses motor_state[18] or motor_state[19], so both slots were free for the authorized simulator-only sideband.

The repair writes only slots 18/19 when both `SIM_LOCKSTEP=1` and `TROT_LOCKSTEP_PAIRED_HIGHSTATE=1`; slots 0..17 and the independent HighState DDS publication are unchanged. The sideband stores the six same-tick HighState floats plus an exact marker, version, source tick, and tick complement. Controller SnapshotState decodes and validates it, uses no asynchronous HighState in paired mode, and fails closed on invalid metadata without fallback. Flag-off selection remains the historical asynchronous-cache path.

Raw run artifacts are immutable and SHA-256 recorded in `provenance.csv`; all three metadata files report the implementation HEAD above, matching simulator/controller/scene hashes, zero status failures, and matching terminal outcomes. Recommend one later checkpoint only if the planner reopens D4; D4 was not executed here.
