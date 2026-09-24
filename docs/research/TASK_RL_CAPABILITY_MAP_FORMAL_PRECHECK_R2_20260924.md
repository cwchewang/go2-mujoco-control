# Deterministic precheck r2 — RL capability-map formal fixture repair — 2026-09-24

This is a cheap owner precheck, NOT an independent reviewer and NOT a scientific run.

Exact formal target:
`0de58642d110067ba6622fa44287710cb170dd2d`

Base reviewed target:
`de5e396331e01576a2bfd0fe1ccdf662835aa15a`

Run only deterministic/static/zero-physics checks.

1. Verify the base-to-target tracked diff contains only:
   - `tools/research/test_preflight_integration.py`
   - `docs/research/TASK_RL_CAPABILITY_MAP_FORMAL_20260924.md`
2. Verify protocol SHA-256 remains
   `0eda1a046d4d9c456a3ee5a281cc183eaf188b0ff9db9fe0767bc5f6011dc803`.
3. Strict-load `tools/substrate/tasks/rl_capability_map_v1.json` and assert:
   branch=`research/rl-capability-map-formal-20260924`,
   issue_number=178,
   task_path=`docs/research/TASK_RL_CAPABILITY_MAP_FORMAL_20260924.md`,
   max_attempts=9,
   retry=`none`.
4. Run the full integration suite:
   `python3 -m unittest -v tools.research.test_preflight_integration`
   All tests must pass, including explicit wrong issue-number and wrong task-path rejection.
5. Run:
   `python3 -m unittest -v tools.substrate.test_launch.CurrentIdentityTests`
   All tests must pass.
6. Confirm no permanent campaign ledger exists for `rl-capability-map-v1`.
7. Record `physics_steps=0`, `scientific_attempts=0`.

Do not repair unrelated code. If all checks pass, create only:
`docs/validation/rl_capability_map_formal_precheck_r2_20260924/PRECHECK.md`
with a concise `PRECHECK PASS` and exact command/return-code evidence. Preserve raw logs in Praxis evidence.

If any check fails, write no PRECHECK.md and close out FAIL.
