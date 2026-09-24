# RL capability-map integrity r2 closeout — 2026-09-24

## Result

**PASS.** The frozen capability-map design now binds its `flat_reference`
sentinel to the exact sealed #166 qpos/qvel/target/applied trace digest. The
change is prospective and leaves the nine-case matrix, thresholds, retry
policy, and all #166 artifacts unchanged. No MuJoCo plant integration or
scientific campaign was run: `physics_steps=0`, `scientific_attempts=0`. [E1, E3, E4]

The Praxis task identity is issue **#177**, branch
`research/rl-capability-map-integrity-r2-20260924`, starting HEAD
`42e92806f1b5b96057298d98b30b2611e470ddc4`. The task config now binds this
branch, the updated protocol hash
`0eda1a046d4d9c456a3ee5a281cc183eaf188b0ff9db9fe0767bc5f6011dc803`, and the
frozen parent `754ceb38e2bd8b1c60ff9c63db0f8326943b17f2`. [E5]

## Sealed reference audit

The committed #166 `RESULTS.md` and publication evidence identify both
`combined_1` and `combined_2` as PASS with the same digest. Independent
recomputation from both preserved 6,001-row raw traces, using the exact
historical schema-1 canonicalization over only `qpos`, `qvel`, `target`, and
`applied`, returns
`1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484` for each.
The four streams also match row-by-row. The capture protocol binds the flat
scene, shared-home reset, adapter, tick-10 first inference, `[1.0, 0.0, 0.0]`
command, source commit and checkpoint hash. The qualification evidence records
the shared `go2.xml` and `phase2_flat.xml` hashes and physical model fingerprint.
The offline #166 closeout reports `VERIFIED`, two consumed attempts, and zero
physics steps. [E1, E2]

## Repair and stop behavior

The schema-2 `flat_reference` case now declares the sealed digest. Protocol
validation requires exactly one well-formed binding on the first case. Capture
compares its recomputed trajectory digest after writing and syncing the raw
trace; mismatch records the expected and observed digests, classifies the case
as `INTEGRITY_STOP`, preserves the started sentinel attempt, and exits before
any dependent case. The offline verifier independently recomputes the raw
trajectory and applies the same expected-digest check before comparing the
stored result. Schema-1 cases without the binding remain on their historical
path. [E3]

Focused tests cover protocol binding validation, matching and mismatching
digests, mismatch precedence over performance failure, one started sentinel
claim, dependent-case suppression, and schema-1 no-binding behavior. The
relevant static/zero-physics suite passed: 65 tests ran, with three native
source-asset tests skipped because their required native source assets were
unavailable. The selected-scene parser tests ran with the zero-step guard.
[E4]

## Scope

No scientific attempts were made. The immutable #166 results, raw capture,
ledger, and source artifacts were copied into the Praxis evidence package for
this review; the source artifacts were not modified. No retry, threshold
change, case change, or MuJoCo integration was introduced. [E1, E5]
