# RL capability-map formal science review r2 — 2026-09-24

Review exact target HEAD `de5e396331e01576a2bfd0fe1ccdf662835aa15a` only. Zero physics.

Context: first science review approved the prior formal target; execution review then found two execution-only identity defects. The target now restores the known-good five-field Praxis binding implementation already used successfully by formal #166 and updates the formal task to prospective r2 review paths.

Verify:
- protocol SHA-256 remains exactly `0eda1a046d4d9c456a3ee5a281cc183eaf188b0ff9db9fe0767bc5f6011dc803`;
- the nine-case matrix, case order, commands, scenes, metrics, thresholds, terrain goals, safety semantics, max_attempts=9, no-retry policy, progression and #166 sealed trace digest are scientifically unchanged from result `00d694dde213fb6862a161374e423261d13ab42b`;
- changes to task.py / identity.py / launch.py / preflight.py / test_launch.py are execution identity hardening only and do not change plant trajectory or evidence meaning;
- formal task references the r2 review locations prospectively and introduces no new scientific interpretation.

Do not run qualification, preparation, capture, simulation or plant physics. Static source inspection and non-plant unit tests are allowed if useful.

Commit exactly:
`docs/validation/rl_capability_map_formal_science_review_r2_20260924/review.json`

Fields: schema=1, role="science", target_head="de5e396331e01576a2bfd0fe1ccdf662835aa15a", nonempty reviewer, verdict APPROVED or VETO, summary, evidence array, concerns array.