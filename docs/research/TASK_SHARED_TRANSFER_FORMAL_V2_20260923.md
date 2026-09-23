# TASK — Shared transfer combination v1 formal capture on Praxis v2

## Objective

Execute the already-frozen confirmatory protocol
`tools/substrate/protocols/rl_shared_transfer_combination_v1.json` exactly once
under the current Go2 scientific gates, using Praxis v2 only as the execution,
evidence, recovery and publication runtime.

This task does not authorize protocol edits, threshold changes, tuning, training,
replacement attempts, or alternate campaigns.

## Frozen scientific contract

The protocol is `rl-shared-transfer-combination-v1` and remains unchanged:

- mode: confirmatory;
- max scientific attempts: 2;
- physics period: 0.002 s;
- control decimation: 10;
- command: 1.0 m/s forward;
- two cases: `combined_1`, then exact repeat `combined_2` only if the first passes;
- first inference tick: 10;
- horizon: 6000 physics ticks = 12 s;
- measurement delay: 1000 ticks = measure [2 s, 12 s);
- forward mean gate >= 0.8 m/s;
- forward MAE <= max(0.05, 0.2 * command);
- lateral drift <= 0.3 m;
- yaw <= 0.3 rad;
- existing safety/integrity gates remain authoritative;
- progression: `first_nonpass_stop`;
- retry: none.

Pinned source identity remains:

- source repository state: `wty-yy/go2_rl_gym` commit
  `30e74dc507bec7a642a8c98be26081f2c6f0822d`;
- checkpoint:
  `deploy/pre_train/go2/go2_moe_cts_high_slope_thre_164k_0.6715.pt`;
- checkpoint SHA-256:
  `9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d`.

## Exact execution identity

Praxis v2 may present a detached worktree. That is expected.

Before any qualification or preparation:

1. Require the complete five-value Praxis identity environment:
   `PRAXIS_REPOSITORY`, `PRAXIS_ISSUE_NUMBER`, `PRAXIS_TASK_BRANCH`,
   `PRAXIS_TASK_COMMIT`, `PRAXIS_TASK_PATH`.
2. Require `PRAXIS_REPOSITORY=cwchewang/go2-mujoco-control`.
3. Require `PRAXIS_TASK_BRANCH=research/shared-transfer-formal-v2-20260923`.
4. Require current `HEAD == PRAXIS_TASK_COMMIT`.
5. Require the tracked worktree clean.
6. Do not create/switch/track a named local branch. Detached HEAD is normal.

The task configuration is
`tools/substrate/tasks/rl_shared_transfer_combination_v1.json`; it must bind the
same logical branch and unchanged protocol SHA-256.

## Independent reviews

Formal capture is forbidden until two independent Praxis v2 review tasks have
completed:

- science review branch:
  `research/review-shared-transfer-science-v2-20260923`
- science review output:
  `docs/validation/shared_transfer_formal_v2_20260923/science_review.json`
- execution review branch:
  `research/review-shared-transfer-execution-v2-20260923`
- execution review output:
  `docs/validation/shared_transfer_formal_v2_20260923/execution_review.json`

Before qualification, fetch only those two review branches. Read their JSON
outputs from their current remote tips and require:

- schema = 1;
- target_head == current `PRAXIS_TASK_COMMIT`;
- verdict == `APPROVED`;
- science role == `science`;
- execution role == `execution`;
- reviewer strings are non-empty and differ.

Construct an ignored local review input with the exact schema required by
`tools.substrate.readiness.validate_review`:

```json
{
  "head": "<PRAXIS_TASK_COMMIT>",
  "science": {
    "verdict": "APPROVED",
    "reviewer": "<science reviewer>",
    "evidence": "<science branch>@<review result commit>:<review path>"
  },
  "execution": {
    "verdict": "APPROVED",
    "reviewer": "<execution reviewer>",
    "evidence": "<execution branch>@<review result commit>:<review path>"
  }
}
```

If either review is missing, mismatched, VETO, malformed or non-independent,
stop before qualification and report BLOCKED. Do not substitute the historical
b882 review.

## Reproducible local resources

Praxis v2 intentionally does not own project resource provisioning. Before
qualification, bind the existing verified Atlas resources into this isolated
task worktree without changing tracked files.

Canonical substrate root:
`/home/che/dev/go2-workspace/current/.substrate`.

Verify before linking:

1. `rl/policy.pt` matches the pinned checkpoint SHA-256 above.
2. Every file in `tools/substrate/rl_reference.lock.json` exists and hash
   matches under `upstream-go2-30e74dc5`.
3. `venv-reliable/bin/python` imports:
   - Torch 2.6.0+cpu,
   - MuJoCo 3.3.6,
   - NumPy 2.2.6.
4. `headless-reliable/go2_mjpc_admit` exists.
5. Existing MuJoCo SDK
   `$HOME/.mujoco/mujoco-3.3.6` contains
   `include/mujoco/mujoco.h` and `lib/libmujoco.so`.

Create only ignored task-local links under `.substrate/` for:

- `.substrate/rl/policy.pt`
- `.substrate/upstream-go2-30e74dc5`
- `.substrate/venv-reliable`
- `.substrate/headless-reliable`

Do not download, install, replace, or mutate these canonical resources.

Unset inherited `PYTHONPATH`; use
`.substrate/venv-reliable/bin/python` for substrate commands.

Before qualification, configure the ignored controller build cache once with:

```bash
cmake -S example/cpp -B .substrate/controller-reliable \
  -DCMAKE_BUILD_TYPE=Release \
  -DGO2_MUJOCO_ROOT="$HOME/.mujoco/mujoco-3.3.6"
```

This is preparation only and must not run MuJoCo physics.

## Phase A — clean qualification

Run exactly one clean, non-development qualification:

```bash
.substrate/venv-reliable/bin/python -m tools.substrate.qualify \
  --output _runs/shared_transfer_formal_v2_20260923/qualification
```

Require `ENGINEERING_ADMITTED`, `clean_head=true`, all required checks zero,
and a sealed manifest. If qualification fails, stop before preparation/capture.
Fixing tracked code in this task is forbidden.

## Phase B — zero-step preparation

Run:

```bash
.substrate/venv-reliable/bin/python -m tools.substrate.baseline prepare \
  --task tools/substrate/tasks/rl_shared_transfer_combination_v1.json \
  --review _runs/shared_transfer_formal_v2_20260923/review.json \
  --qualification _runs/shared_transfer_formal_v2_20260923/qualification \
  --output _runs/shared_transfer_formal_v2_20260923/prepared
```

Require:

- `READY_AWAITING_START`;
- `physics_steps = 0`;
- campaign ledger
  `_runs/substrate_attempts/rl-shared-transfer-combination-v1` still absent;
- exact current HEAD unchanged;
- protocol hash unchanged.

Preparation is not authorization.

## User START authorization

The user already explicitly authorized formal capture in the controlling ChatGPT
conversation with the exact instruction:

`好，开吧`

This authorization is valid only after both exact-head reviews approve and the
zero-step preparation above is READY.

After preparation, create exactly one ignored authorization JSON binding the
actual prepared checkpoint:

```json
{
  "action": "START_FORMAL_CAPTURE",
  "head": "<current exact PRAXIS_TASK_COMMIT>",
  "protocol_sha256": "<actual frozen protocol SHA-256>",
  "prepared_manifest_sha256": "<actual prepared manifest SHA-256>",
  "max_attempts": 2,
  "authorized_by": "user",
  "user_instruction": "好，开吧"
}
```

Do not invent a new user instruction and do not broaden the attempt budget.

## Phase C — formal capture

Invoke the formal capture command exactly once:

```bash
.substrate/venv-reliable/bin/python -m tools.substrate.baseline capture \
  --task tools/substrate/tasks/rl_shared_transfer_combination_v1.json \
  --prepared _runs/shared_transfer_formal_v2_20260923/prepared \
  --authorization _runs/shared_transfer_formal_v2_20260923/authorization.json \
  --output _runs/shared_transfer_formal_v2_20260923/capture
```

Hard rules:

- Never invoke `capture` a second time in this task, regardless of outcome.
- Never delete or reset the campaign ledger.
- Never replace a failed/safety/integrity outcome with another run.
- Never tune thresholds, reset state, command, model, adapter, inference timing,
  horizon or analysis after seeing evidence.
- If `combined_1` is non-PASS, preserve the prescribed stop behavior.
- A safety/integrity stop is a bounded experiment outcome, not permission to retry.
- If the process errors after the campaign is claimed, preserve all evidence and
  close out the task without another capture.

## Phase D — offline verification

If the capture command produced a sealed `CAPTURE_COMPLETE` bundle, run exactly
one offline verification:

```bash
.substrate/venv-reliable/bin/python -m tools.substrate.baseline verify \
  --capture _runs/shared_transfer_formal_v2_20260923/capture \
  --prepared _runs/shared_transfer_formal_v2_20260923/prepared \
  --output _runs/shared_transfer_formal_v2_20260923/verification
```

Verification must consume zero physics steps and independently audit the attempt
ledger, authorization, trace, analysis and repeat semantics.

## Interpretation boundary

Report only what this frozen experiment establishes.

If both cases PASS with an exact repeat trace, the allowed conclusion is:

> the exact pinned full shared deployment combination (shared model + shared
> home + adapter + 10-step first inference) preserves the source 1.0 m/s flat
> gate under this deterministic MuJoCo setup.

If the first case fails frozen performance gates, the allowed conclusion is:

> the full pinned combination fails the frozen 1.0 m/s flat gate in this setup.

Safety/integrity stops must be reported as such.

No outcome establishes causal attribution, low-speed capability, terrain
robustness, hardware transfer, general robustness or a paper claim.

## Tracked closeout

After capture/verification are finished, and only then, write tracked closeout
artifacts under:

`docs/validation/shared_transfer_formal_v2_20260923/`

At minimum:

- `RESULTS.md`
- `RESULT.json`

Record:

- exact frozen HEAD;
- protocol SHA;
- qualification/prepared/capture/verification manifest SHA-256 values;
- exact user instruction;
- campaign ledger contents;
- attempt statuses;
- for every executed case: mean forward speed, MAE, lateral drift, yaw,
  safety/integrity outcome and trace SHA-256;
- repeat equality result;
- final bounded interpretation;
- what was not established.

Do not modify scientific/runtime source after capture. Commit only intended
tracked closeout artifacts. Leave raw scientific evidence in the ignored
`_runs` tree and also copy or reference the decisive raw files into
`$PRAXIS_EVIDENCE_DIR` so the Praxis closeout can cite falsifiable evidence.

## Praxis closeout

Write the required `$PRAXIS_EVIDENCE_DIR/closeout.json`.

A scientifically valid PERFORMANCE_FAIL, SAFETY_STOP or INTEGRITY_STOP is not a
Praxis execution failure if the frozen campaign completed as specified and its
evidence verifies. Distinguish scientific outcome from runtime/task failure.

Every material observation/inference/conclusion must cite preserved evidence.
