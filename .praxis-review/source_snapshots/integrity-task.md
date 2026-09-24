# RL capability-map integrity review/repair r2 — 2026-09-24

Review and minimally repair the frozen capability-map design at exact parent `754ceb38e2bd8b1c60ff9c63db0f8326943b17f2`. Zero physics only.

## Trigger

The stage-owner review found one integrity gap: `flat_reference` reuses the exact shared deployment condition already proven deterministic in formal #166, but the new campaign currently only re-applies performance gates. The sealed #166 trace SHA-256 for both `combined_1` and `combined_2` is:

`1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484`

If the new schema/runner/environment silently changes the reference trajectory while still clearing performance thresholds, later terrain cases would be interpreted against a shifted reference.

## Required action

1. Independently verify from committed #166 RESULTS/evidence that the hash above is the authoritative deterministic qpos/qvel/target/applied trace for the exact shared model + shared_home + ten-step startup + adapter + 1.0 m/s flat condition.
2. Add the smallest prospective integrity binding so `flat_reference` must match that sealed trajectory digest exactly before dependent cases can run.
3. A mismatch must classify as `INTEGRITY_STOP` (not performance failure), consume only the already-started sentinel attempt, run no dependent cases, and preserve the observed digest/raw trace.
4. Do not add retries, loosen thresholds, change any other case, alter #166 evidence, or run MuJoCo plant integration.
5. Ensure offline verification independently checks the expected sealed digest rather than trusting only capture's classification.
6. Preserve schema-1 historical behavior.
7. Add focused tests for matching/mismatching sealed reference digest and stop semantics.
8. Re-run the relevant zero-physics/static test suite and self-review the full design for any related stale identity/path/hash issue. Repair minor issues autonomously.
9. Update the design/closeout/protocol hash/task config as needed and record `physics_steps=0`, `scientific_attempts=0`.

If this integrity binding cannot be made without changing the scientific question or invalidating the frozen matrix, VETO and explain why. Otherwise commit the repaired frozen design and closeout.