# Shared-transfer formal capture v2 — frozen execution task

## Objective

Execute the already-reviewed prospective `rl-shared-transfer-combination-v1`
campaign under Praxis v2 without changing its protocol, thresholds, attempt
budget, retry policy, model, source checkpoint, reset, adapter, or interpretation.

This task is the first real MuJoCo/scientific workload on the Praxis v2 runtime.
Praxis provides isolated full-host execution and evidence; the Go2 repository
owns qualification, START authorization, scientific attempt accounting and
verification.

## Frozen scientific contract

Use only:

- task configuration: `tools/substrate/tasks/rl_shared_transfer_combination_v1.json`
- protocol: `tools/substrate/protocols/rl_shared_transfer_combination_v1.json`
- protocol SHA-256:
  `2d23131cb104be50aeb163737e3cfbf10f5a9291acf7726c2eda75e3fa5e9b32`
- checkpoint SHA-256:
  `9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d`
- source commit:
  `30e74dc507bec7a642a8c98be26081f2c6f0822d`
- maximum scientific attempts: 2
- retry: none
- progression: first non-pass stops the campaign

Do not tune, weaken, reinterpret or replace any gate after seeing a result.

## Required independent reviews

Before qualification or any physics, retrieve and validate both review results:

- science task branch:
  `review/shared-transfer-formal-v2-science-r3-20260924`
- science result:
  `docs/validation/shared_transfer_formal_v2_science_r3_20260924/review.json`
- execution task branch:
  `review/shared-transfer-formal-v2-execution-r3-20260924`
- execution result:
  `docs/validation/shared_transfer_formal_v2_execution_r3_20260924/review.json`

Each result must state `verdict=APPROVED`, must bind
`target_head == PRAXIS_TASK_COMMIT`, and must have a non-empty reviewer
identity. The reviewer identities must differ. Record the exact review branch
tip commits used. If either review is absent, stale, vetoed, ambiguous or shares
the same reviewer identity, stop BLOCKED before qualification and before
physics.

Construct the Go2 review input expected by
`tools.substrate.readiness.validate_review` from those two exact review
results. Do not invent or repair a review verdict.

## Local resource admission before qualification

No downloads and no package installation are allowed for the scientific
campaign. Reuse the already accepted Atlas resources.

Canonical substrate resource root:

`/home/che/dev/go2-workspace/current/.substrate`

Canonical MuJoCo SDK:

`/home/che/.mujoco/mujoco-3.3.6`

Before qualification:

1. verify the checkpoint hash against the frozen SHA above;
2. verify every upstream source file against
   `tools/substrate/rl_reference.lock.json`;
3. verify the reliable interpreter imports exactly the locked Torch 2.6.0,
   MuJoCo 3.3.6 and NumPy 2.2.6 environment required by the repository;
4. verify `headless-reliable/go2_mjpc_admit` exists;
5. verify the MuJoCo SDK header and shared library exist;
6. expose the canonical immutable resources in this task worktree under ignored
   `.substrate/` paths required by the substrate code. Do not modify the
   canonical resource cache;
7. create a task-local ignored `.substrate/controller-reliable` build and
   preconfigure it with
   `-DGO2_MUJOCO_ROOT=/home/che/.mujoco/mujoco-3.3.6`.

Any failure here is infrastructure/preflight only. Stop BLOCKED. It consumes no
scientific attempt.

## Qualification and zero-step preparation

Use the reliable venv Python with `PYTHONPATH` unset,
`PYTHONNOUSERSITE=1`, and `PYTHONDONTWRITEBYTECODE=1`.

Under `$PRAXIS_EVIDENCE_DIR/formal/`:

1. run a clean non-development `tools.substrate.qualify`;
2. preserve all qualification logs and manifest;
3. run
   `tools.substrate.baseline prepare` with the frozen task, the constructed
   independent-review JSON and the accepted qualification bundle;
4. verify preparation returns `READY_AWAITING_START`, `physics_steps=0`,
   and no campaign ledger exists;
5. preserve the prepared manifest SHA-256.

If qualification or preparation fails, stop BLOCKED. Do not run capture.

## Explicit user START authorization

The user has explicitly authorized this formal capture. After, and only after,
a successful zero-step preparation, write the authorization JSON required by
`validate_authorization`, binding the exact current frozen head, protocol hash,
prepared-manifest hash and max_attempts=2.

Record the actual user instruction exactly as:

`好，开吧`

with `authorized_by: "user"` and
`action: "START_FORMAL_CAPTURE"`.

Preparation itself is not authorization; do not create this record before
successful preparation.

## Formal capture boundary

Immediately before capture, confirm:

- Praxis issue identity is exactly `#166` and `PRAXIS_TASK_PATH` is exactly `docs/research/TASK_SHARED_TRANSFER_FORMAL_V2_20260923.md`, matching the tracked task binding;
- current HEAD is exactly `PRAXIS_TASK_COMMIT`;
- the complete five-field Praxis v2 identity binding is present and exact;
- the tracked worktree is clean;
- the review and qualification references still validate;
- the prepared snapshot still validates;
- the campaign ledger for `rl-shared-transfer-combination-v1` does not exist.

Then execute exactly one `tools.substrate.baseline capture` command.

The Go2 campaign ledger is authoritative for scientific-attempt consumption.
Once the campaign ledger exists, **never invoke capture again**, including
during Praxis recovery. If the task process is interrupted after the campaign
is claimed, recovery may only inspect the existing capture/ledger, run offline
verification if possible, and close out the existing result. There is no
replacement attempt.

The protocol itself decides whether the second case runs. If `combined_1` is
non-PASS, the second case remains NOT_RUN.

## Offline verification and closeout

After capture, run `tools.substrate.baseline verify` exactly on the captured
bundle and prepared bundle. Verification must integrate zero physics.

Copy the external campaign ledger into
`$PRAXIS_EVIDENCE_DIR/formal/ledger/` for durable review.

Preserve in Praxis evidence at minimum:

- exact resource-preflight commands/results;
- exact review branch tips and parsed review results;
- qualification bundle and logs;
- prepared bundle;
- authorization JSON;
- complete capture bundle/raw traces;
- verification bundle;
- copied campaign ledger;
- exact command log and return codes;
- a concise machine-readable formal summary.

Create one tracked result document:

`docs/validation/shared_transfer_combination_formal_v2_20260923/RESULTS.md`

It must report exact metrics/verdicts from the verified evidence and distinguish:

- PASS;
- PERFORMANCE_FAIL;
- SAFETY_STOP / INTEGRITY_STOP;
- infrastructure/preflight failure.

Do not infer a causal explanation from one outcome. Do not claim low-speed,
terrain, hardware or general robustness. The only scientific question is
whether the complete pinned shared deployment combination preserves the sealed
source 1.0 m/s flat capability under this frozen protocol.

## Git / Praxis rules

The Praxis v2 worktree may be detached. Do not create or switch branches.
Use the frozen `PRAXIS_*` identity. Commit only the intended tracked
`RESULTS.md` closeout. Do not push; Praxis performs review publication and the
final compare-and-swap push.

If no scientific capture occurred, say so explicitly and leave
`scientific_attempts=0`. If capture crossed the Go2 campaign claim boundary,
report the exact consumed count from the ledger and never retry.
