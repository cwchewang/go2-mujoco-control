# RL capability-map prospective successor — 2026-09-24

## Objective

Run a new prospective nine-case `rl-capability-map-v1` campaign after the incomplete #178 campaign. This is a **new campaign**, not a retry or continuation of #178's permanent ledger.

Issue identity: **#189**  
Logical branch: `research/rl-capability-map-successor-20260924`  
Task path: `docs/research/TASK_RL_CAPABILITY_MAP_SUCCESSOR_20260924.md`

Scientific protocol is unchanged:
- `tools/substrate/protocols/rl_capability_map_v1.json`
- SHA-256 `0eda1a046d4d9c456a3ee5a281cc183eaf188b0ff9db9fe0767bc5f6011dc803`
- 9 cases, max_attempts=9, retry=`none`
- sealed flat-reference trace SHA-256 `1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484`

Do not change protocol bytes, thresholds, case order, source checkpoint, model, reset, adapter, commands, scene contracts, progression, or interpretation after seeing results.

## Why this successor exists

#178 invoked the frozen campaign exactly once. Its first `flat_reference` attempt completed all 6000 physics ticks and its raw trace independently replayed as PASS with the exact sealed #166 digest, but capture finalization failed because `flat_cross_axis_pass` became a NumPy boolean and could not be JSON serialized. The permanent #178 ledger therefore remains authoritative: one attempt consumed; remaining eight cases NOT_RUN; no recapture.

The repair is intentionally mechanical:
- #178 closeout commit: `6d620c68b37c9642aa0086efa88db85eee7c5492`
- analyzer repair: `9be79465403c1d47fea5c238d6b3df5b0fc3f6dd`
- regression-test HEAD before this task metadata: `096bb6150d9bb0bd0481b1b5a5f45ce37ee098b9`
- runtime change: normalize `flat_cross_axis_pass` to native Python `bool`
- regression: capability analysis result must be JSON serializable.

Owner Hostbridge precheck `go2-json-bool-repair-precheck-096bb615-r2-20260924` proved on `096bb615...`:
- exact repair diff only touched analyzer + regression test;
- frozen protocol hash unchanged;
- targeted tests PASS;
- replaying #178 raw sentinel still gives PASS, exact sealed digest, mean vx `0.885882509707172`, progress `10.486111570522883`;
- repaired result field is native `bool` and serializes successfully.

## Frozen campaign

Run exactly these protocol-defined cases, at most once each:
1. `flat_reference`
2. `flat_half_speed`
3. `flat_reverse_probe`
4. `flat_lateral_probe`
5. `flat_yaw_probe`
6. `step_5cm_cross`
7. `step_10cm_cross`
8. `repeated_steps_cross`
9. `low_friction_cross`

Performance failures may continue according to the frozen protocol. `SAFETY_STOP` and `INTEGRITY_STOP` stop the campaign. No retry.

## Review carry-forward and owner precheck

The original r2 science/execution reviews approved the unchanged scientific design at `de5e396331e01576a2bfd0fe1ccdf662835aa15a`. No new expensive reviewer is required only if the project-owner deterministic precheck on the **final exact launch HEAD** proves all of the following:

1. Relative to #178 closeout `6d620c68...`, tracked execution changes are only the one-line native-bool normalization, its regression test, this successor task file, and its task-config file.
2. Protocol bytes/hash remain unchanged.
3. Strict task loader accepts the successor task config with exact repository/issue/branch/commit/task-path identity.
4. Complete preflight integration and CurrentIdentity tests pass; wrong issue/path/incomplete bindings fail closed.
5. The repaired analyzer JSON-serializes the preserved #178 raw trace without changing its digest or frozen metrics.
6. Locked host assets/runtime are staged only into ignored task-local paths; no downloads/install/training.
7. Clean non-development qualification passes on the final HEAD.
8. Zero-step preparation passes with `physics_steps=0`, no campaign ledger, and no scientific attempt consumed.

Runtime review bundle for preparation/capture:
- science: APPROVED, reviewer `OpenAI Codex science r2 — inherited semantic approval`, evidence cites the original r2 science review plus owner proof that protocol/scientific semantics are unchanged;
- execution: APPROVED, reviewer `ChatGPT project owner deterministic precheck`, evidence cites the final exact-head Hostbridge PRECHECK PASS.

If any condition fails, do not start capture.

## Locked host runtime

Use only the already-verified Atlas assets. Do not download or install anything.

Task-local ignored `.substrate` should mirror the successful #178 qualification layout:
- `rl` -> `/home/che/dev/go2-workspace/current/.substrate/rl`
- `upstream-go2-30e74dc5` -> `/home/che/dev/go2-workspace/current/.substrate/upstream-go2-30e74dc5`
- `headless-reliable` -> `/home/che/dev/go2-workspace/current/.substrate/headless-reliable`
- `controller-reliable` is task-local build output.

Use locked interpreter:
`/home/che/dev/go2-workspace/current/.substrate/venv-reliable/bin/python`

## Qualification and zero-step preparation

Before any capture:
- run clean `tools.substrate.qualify`;
- construct the exact-head runtime review bundle described above;
- run `tools.substrate.baseline prepare` with this successor task config;
- preparation must return `READY_AWAITING_START`, `physics_steps=0`;
- confirm no `_runs/substrate_attempts/rl-capability-map-v1` ledger exists in this fresh task worktree.

Preparation is not scientific execution.

## Start authorization

The user approved the staged route “close out #178 → fix serialization → owner precheck → new prospective campaign” with the instruction:

`好`

Only after the final exact-head owner precheck and zero-step preparation PASS, create authorization:
- `action: START_FORMAL_CAPTURE`
- `authorized_by: user`
- `user_instruction: 好`
- exact HEAD
- exact protocol hash
- exact prepared-manifest hash
- max_attempts=9.

## Capture boundary

Immediately before capture verify:
- repository `cwchewang/go2-mujoco-control`
- issue exactly #189
- branch exactly `research/rl-capability-map-successor-20260924`
- task path exactly `docs/research/TASK_RL_CAPABILITY_MAP_SUCCESSOR_20260924.md`
- current HEAD exactly `PRAXIS_TASK_COMMIT`
- clean tracked worktree
- protocol hash unchanged
- review/qualification/preparation/authorization all validate
- no permanent campaign ledger exists.

Then invoke exactly one `tools.substrate.baseline capture` command.

Once the new campaign ledger exists, never invoke capture again. Recovery may only inspect/verify/close out that same result.

## Verification and closeout

Run the independent offline verifier only against the existing prepared/capture bundles; it must integrate zero physics and independently recompute the sealed reference digest.

Commit exactly one tracked result:
`docs/validation/rl_capability_map_successor_20260924/RESULTS.md`

Report all nine cases individually with exact metrics/classifications. Do not convert them into a success-rate statistic and do not claim hardware/general robustness/paper novelty beyond the frozen evidence.
