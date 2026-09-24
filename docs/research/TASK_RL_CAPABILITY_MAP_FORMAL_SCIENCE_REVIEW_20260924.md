# RL capability-map formal science review — 2026-09-24

Review exact target HEAD `6bd0485f25f848d9286ae986ed4f2f7d805a5090` only. Zero physics.

Verify that the target is scientifically equivalent to the already frozen and repaired capability-map design:
- design result `754ceb38e2bd8b1c60ff9c63db0f8326943b17f2`
- integrity result `00d694dde213fb6862a161374e423261d13ab42b`
- protocol SHA-256 `0eda1a046d4d9c456a3ee5a281cc183eaf188b0ff9db9fe0767bc5f6011dc803`.

Check that the only prospective changes after the repaired design are formal execution identity/task binding, not the scientific matrix or interpretation. Confirm:
- same 9 cases, commands, scenes, thresholds, terrain goals, safety semantics, progression and max_attempts=9;
- no retries;
- exact #166 flat-reference digest binding remains unchanged;
- lateral/yaw probes remain bounded engineering probes;
- excluded scenes and scope limitations remain unchanged;
- no paper-gap claim is introduced.

Do not run qualification, preparation, capture, simulation, or plant physics.

Commit exactly one file:
`docs/validation/rl_capability_map_formal_science_review_20260924/review.json`

JSON fields: schema=1, role="science", target_head="6bd0485f25f848d9286ae986ed4f2f7d805a5090", nonempty reviewer, verdict APPROVED or VETO, summary, evidence array, concerns array.