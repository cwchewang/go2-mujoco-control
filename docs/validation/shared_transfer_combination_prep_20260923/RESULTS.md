# Shared transfer combination v1: exact-head preparation closeout

Date: 2026-09-23
Stage: exact-head readiness only; formal capture was not authorized.

## Independent reviews

Both reviews explicitly approve execution HEAD
`b882a5d775ffe01e2cfae6da13c68a040d1ed7b4`:

- Science: `gpt6-luna-max-science-review`, from
  `research/review-shared-transfer-science-20260923` at
  `fee495f253d90e7f1ae2fbe35e64987d88ae6e61`.
- Execution: `gpt6-luna-max-execution-review`, from
  `research/review-shared-transfer-execution-20260923` at
  `36dfee765654fb3d24575bc8c4b2a0aad6086f92`.

The reviewer identities differ. The ignored review input was constructed from
these closeouts at
`_runs/shared_transfer_combination_prep_20260923/review.json` and passed
`readiness.validate_review`.

## Clean-head qualification

Accepted qualification output:
`_runs/shared_transfer_combination_prep_20260923/qualification_sdkroot`.
Status: `ENGINEERING_ADMITTED`; `clean_head=true`; `development=false`;
`capability_status=NOT_RUN`. The independent substrate verifier returned
`VERIFIED` for this exact HEAD. All eight qualification checks returned zero:
controller configure/build/tests, substrate tests, preflight tests, tooling
tests, quality, and diff check.

Qualification fingerprint:
`dd156d40163e6f674ba34182f5cf83a8f791f09579fb12c3d990b74e36a802cd`.
Qualification manifest SHA-256:
`dd30ab0d4614194502fc39cd5284fe40acbf3039b8a159dc7fa453ed7779d674`.

Two earlier failed qualification bundles remain preserved under the same ignored
run root. The first stopped on the inherited `PYTHONPATH`; the second exposed
the missing default `simulate/mujoco` header path. For the accepted run,
`PYTHONPATH` was unset and the ignored controller build cache was configured to
use the existing MuJoCo 3.3.6 SDK at `~/.mujoco/mujoco-3.3.6`. Its library
SHA-256 (`b9173509d0c282a9b24b7f5825a40177a9967df0cd6395a9dc39522196e44495`)
matched the reliable venv's MuJoCo library. No source files were changed and
nothing was downloaded or installed.

## Zero-step preparation and verification

Preparation output:
`_runs/shared_transfer_combination_prep_20260923/prepared_clean`.
Status: `ENGINEERING_ADMITTED`; readiness: `READY_AWAITING_START`.
Prepared manifest SHA-256:
`f824877bbff984389089b31cbcc80d7a1be43c354f4b41c7dc6d14a801d6c49e`.
Protocol SHA-256:
`2d23131cb104be50aeb163737e3cfbf10f5a9291acf7726c2eda75e3fa5e9b32`.

Independent read-only verification accepted the evidence bundle, task and exact
HEAD identity, both reviews, and the qualification reference. It also confirmed
the protocol snapshot matches the task-bound protocol, the checkpoint snapshot
matches its declared hash, and the preparation manifest is intact. Both
combined-condition models loaded with physical fingerprint
`1c7ec61af1297fe1715e3d412481709bf4ad3ad42196e483c444d1a54db73e94`; policy
output validation completed during preparation.

Source and runtime identity:

- Pinned source: `wty-yy/go2_rl_gym`, commit
  `30e74dc507bec7a642a8c98be26081f2c6f0822d`.
- Checkpoint: `deploy/pre_train/go2/go2_moe_cts_high_slope_thre_164k_0.6715.pt`,
  SHA-256 `9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d`.
- Isolated runtime: CPython `3.10.12`, MuJoCo `3.3.6`, Torch `2.6.0+cpu`;
  `17,610` installed payload files verified against the locked runtime.
  Runtime lock SHA-256:
  `02f170cc1b64df7d21839a961bfb2f1b33ecaddd1755740272954df5e2d68d88`.

## Boundary

`physics_steps = 0`; `scientific_attempts = 0`; `live_runs = 0`;
`capability_status = NOT_RUN`. No locomotion PASS/FAIL is claimed. No capture,
training, tuning, or protocol change occurred.

The exact next boundary is explicit user `START_FORMAL_CAPTURE` authorization
for this prepared HEAD, protocol, and manifest. No authorization was created.

Veto: none. The required fetch was omitted because the worker instruction
prohibited Git metadata writes; `origin/main` and the named review branches were
read from their pre-existing local refs.
