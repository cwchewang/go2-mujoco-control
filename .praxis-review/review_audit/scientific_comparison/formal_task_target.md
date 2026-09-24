# RL capability-map formal capture — 2026-09-24

## Objective

Execute the frozen schema-2 `rl-capability-map-v1` campaign exactly once under Praxis v2. This is the formal RL capability screen for the current Substrate Gate 0.

Scientific design source:
- design result: `754ceb38e2bd8b1c60ff9c63db0f8326943b17f2`
- integrity repair result: `00d694dde213fb6862a161374e423261d13ab42b`
- protocol: `tools/substrate/protocols/rl_capability_map_v1.json`
- protocol SHA-256: `0eda1a046d4d9c456a3ee5a281cc183eaf188b0ff9db9fe0767bc5f6011dc803`
- Praxis issue identity: **#178**
- logical branch: `research/rl-capability-map-formal-20260924`

Do not change protocol, thresholds, case order, retry policy, source checkpoint, model, reset, adapter, command magnitudes, scene contracts, or interpretation after seeing any result.

## Frozen campaign

Nine deterministic cases, maximum one scientific attempt each, maximum **9 total attempts**, **no retry**:

1. `flat_reference`: [1.0, 0, 0], exact sealed #166 trace digest required.
2. `flat_half_speed`: [0.5, 0, 0].
3. `flat_reverse_probe`: [-0.5, 0, 0].
4. `flat_lateral_probe`: [0, 0.25, 0].
5. `flat_yaw_probe`: [0, 0, 0.5].
6. `step_5cm_cross`: +X 1.0 m/s.
7. `step_10cm_cross`: +X 1.0 m/s.
8. `repeated_steps_cross`: +X 1.0 m/s on 5/15/5 cm profile.
9. `low_friction_cross`: +X 1.0 m/s on the declared low-friction patch.

The exact case definitions, scene geom contracts, terrain goals, metric windows, tracking tolerances, safety gates and progression are authoritative only from the frozen protocol JSON.

## Reference integrity

Before interpreting any dependent result, `flat_reference` must:
- pass its ordinary frozen performance gates; and
- reproduce exactly the sealed #166 qpos/qvel/target/applied trace digest:
  `1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484`.

Any digest mismatch is `INTEGRITY_STOP`, consumes only the already-started sentinel attempt, preserves the observed raw trace/digest, and leaves all dependent cases `NOT_RUN`. Never reinterpret it as a performance failure.

## Required exact-head reviews

Before qualification or plant physics, retrieve and validate:

Science review branch:
`review/rl-capability-map-formal-science-r2-20260924`
Result:
`docs/validation/rl_capability_map_formal_science_review_r2_20260924/review.json`

Execution review branch:
`review/rl-capability-map-formal-execution-r2-20260924`
Result:
`docs/validation/rl_capability_map_formal_execution_review_r2_20260924/review.json`

Each must be `APPROVED`, bind `target_head == PRAXIS_TASK_COMMIT`, contain a nonempty reviewer identity and evidence, and have different reviewer identities. If either is absent/stale/vetoed/ambiguous, stop before qualification and before physics.

## Preflight / preparation

Use only locked host assets/runtime. No downloads, package installation, training, fine-tuning, checkpoint substitution or scene editing during the formal campaign.

Perform the normal clean non-development qualification and schema-2 zero-step preparation. Preparation must:
- validate protocol/task/source/checkpoint hashes;
- validate exact selected-scene world collision geom contracts;
- validate the complete three-axis command shapes and probe envelope;
- leave live `MjData` and time unchanged;
- return ready status with `physics_steps=0`;
- find no pre-existing campaign ledger.

Any unsupported scene / qualification / preparation failure is infrastructure/preflight only and consumes no scientific attempt.

## Start authorization

The user has already instructed the project owner to continue this staged workflow after being told that the next passed stage would proceed directly into the formal capability experiment.

After successful zero-step preparation, create the required start authorization bound to:
- exact current frozen HEAD;
- protocol hash;
- prepared-manifest hash;
- max_attempts=9.

Record the user instruction exactly as:
`好，继续`

with `authorized_by: "user"` and `action: "START_FORMAL_CAPTURE"`.

Do not create authorization before preparation succeeds.

## Capture boundary

Immediately before capture verify:
- Praxis issue is exactly #178;
- `PRAXIS_TASK_PATH` is exactly `docs/research/TASK_RL_CAPABILITY_MAP_FORMAL_20260924.md`;
- all five Praxis identity fields are exact;
- current HEAD is exactly `PRAXIS_TASK_COMMIT`;
- tracked worktree is clean;
- reviews, qualification, preparation and authorization still validate;
- protocol hash is unchanged;
- no permanent campaign ledger exists.

Then execute exactly one `tools.substrate.baseline capture` command.

Once the permanent campaign ledger exists, never invoke capture again, including during recovery. Recovery after claim may only inspect the existing ledger/capture, perform offline verification if possible, and close out that same result.

## Progression

- Expected complete `TRACKING_FAILURE` / `TASK_GOAL_FAILURE`: record and continue to later independent cases.
- `SAFETY_STOP` or `INTEGRITY_STOP`: stop the campaign immediately.
- A failed `flat_reference` makes every dependent case `NOT_RUN`.
- Preflight/unsupported-scene failures consume zero attempts and stop before capture.
- No retry under any classification.

## Verification / closeout

Run the independent offline verifier on the existing prepared/capture bundles only; verification integrates zero physics and must independently recompute the sealed reference digest from raw rows.

Preserve:
- review tips/results;
- resource and scene-contract preflight;
- qualification receipt/logs;
- prepared bundle;
- authorization;
- complete raw traces/results;
- authoritative campaign ledger and copy;
- verification bundle;
- exact commands/return codes;
- concise machine-readable summary.

Commit exactly one tracked formal closeout:
`docs/validation/rl_capability_map_formal_20260924/RESULTS.md`

Report each case individually with exact metrics and classification. Do not convert the nine deterministic cases into a success-rate statistic. Do not claim hardware, randomized robustness, lateral/turning terrain traversal, universal terrain ceilings, causal slip mechanics, or a paper gap.

## Worker autonomy

Minor execution problems may be repaired autonomously only before scientific capture if they do not change the frozen protocol/question/threshold meaning/budget/evidence semantics. Re-run zero-step validation after repair.

After any scientific attempt is consumed, do not modify the frozen execution code or protocol to obtain a better result. Preserve the evidence and close out the campaign as run.
