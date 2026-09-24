# Deterministic precheck — RL capability-map formal fixture repair — 2026-09-24

This is a cheap owner precheck, NOT an independent reviewer and NOT a scientific run.

Exact formal target to precheck:
`ccff21f7c3e6a2d55023fd0ec80bdf4edfc3f5b5`

Base reviewed target:
`de5e396331e01576a2bfd0fe1ccdf662835aa15a`

## Required checks

Run only deterministic/static/zero-physics checks. Do not run qualification capture,
MuJoCo plant integration, training, or any scientific capability episode.

1. Verify `git diff --name-only de5e396... ccff21f7c3e6a2d55023fd0ec80bdf4edfc3f5b5` contains exactly:
   - `tools/research/test_preflight_integration.py`
   - `docs/research/TASK_RL_CAPABILITY_MAP_FORMAL_20260924.md`
2. Verify `tools/substrate/protocols/rl_capability_map_v1.json` SHA-256 remains:
   `0eda1a046d4d9c456a3ee5a281cc183eaf188b0ff9db9fe0767bc5f6011dc803`.
3. Verify the formal task config still loads with the real strict loader and retains:
   branch `research/rl-capability-map-formal-20260924`, issue 178, formal task path,
   max_attempts=9, retry=none.
4. Run the complete preflight integration fixture suite:
   `python3 -m unittest -v tools.research.test_preflight_integration`
   It must be fully green; specifically the detached exact five-field binding success
   fixture must now PASS.
5. Run:
   `python3 -m unittest -v tools.substrate.test_launch.CurrentIdentityTests`
   and confirm wrong repository/branch/commit/issue/path or incomplete binding remains
   fail-closed as covered by the suite.
6. Confirm no permanent campaign ledger exists for `rl-capability-map-v1`.
7. Record `physics_steps=0`, `scientific_attempts=0`.

If any check fails, do not repair unrelated code and do not dispatch reviewers. Report FAIL.

If all pass, write:
`docs/validation/rl_capability_map_formal_precheck_20260924/PRECHECK.md`
with a concise `PRECHECK PASS` summary, exact commands/return codes, exact target/head,
diff paths, protocol hash, ledger status, and zero-attempt statement.

Commit only that PRECHECK.md. Preserve raw command output in Praxis evidence and cite it
from closeout.json.
