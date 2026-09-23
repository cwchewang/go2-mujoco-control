# Independent execution review — shared-transfer formal v2

Target execution HEAD: `bab5d56af48a23894c52982ad23b73f2a361e554`

## Role

Act only as the independent execution reviewer. Do not run MuJoCo physics, do
not start the campaign, do not create authorization, and do not alter the
experiment.

Inspect the exact target HEAD, especially:

- `docs/research/TASK_SHARED_TRANSFER_FORMAL_V2_20260923.md`
- `tools/substrate/tasks/rl_shared_transfer_combination_v1.json`
- `tools/substrate/protocols/rl_shared_transfer_combination_v1.json`
- `tools/research/identity.py`
- `tools/substrate/qualify.py`
- `tools/substrate/baseline.py`
- `tools/substrate/baseline_verify.py`
- `tools/substrate/readiness.py`

Verify specifically:

1. Praxis v2 detached execution binds exact repository/issue/branch/commit/path
   and clean HEAD before scientific work;
2. local resource provisioning is ignored/untracked and cannot silently replace
   the frozen source/checkpoint identities;
3. qualification and prepare are zero-physics gates before authorization;
4. authorization is created only after successful preparation and binds exact
   head/protocol/prepared manifest/max_attempts;
5. capture has one authoritative campaign ledger, max 2 attempts, no retry, and
   first-nonpass stop;
6. a crash/recovery after campaign claim cannot legally call capture again;
7. offline verification integrates zero physics and independently checks raw
   evidence/ledger/authorization;
8. evidence paths remain durable through Praxis v2 even after the task exits;
9. no v1 Control Plane/trusted-host wrapper is required.

Write exactly one tracked result file:

`docs/validation/shared_transfer_formal_v2_execution_20260923/review.json`

Schema:

{
  "schema": 1,
  "role": "execution",
  "target_head": "bab5d56af48a23894c52982ad23b73f2a361e554",
  "reviewer": "gpt6-luna-max-execution-review-v2",
  "verdict": "APPROVED" | "VETO",
  "summary": "...",
  "evidence": ["specific file/commit/check references"],
  "concerns": ["..."]
}

Use APPROVED only if this exact target HEAD can execute without weakening
scientific attempt accounting or evidence integrity. Preserve raw review
evidence under `$PRAXIS_EVIDENCE_DIR`, cite it in Praxis closeout, and commit
only review.json. Do not push; Praxis will publish it.
