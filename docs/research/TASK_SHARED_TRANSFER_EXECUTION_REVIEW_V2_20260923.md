# TASK — Independent execution review for shared transfer formal v2

## Role

Act as an independent execution/integrity reviewer for the frozen shared-transfer
formal experiment. This task is review-only and zero-physics.

Reviewer identity to record exactly:

`gpt6-luna-max-execution-review-v2-20260923`

The execution HEAD being reviewed is exactly the frozen starting commit exposed
as `PRAXIS_TASK_COMMIT`. Do not review your eventual result commit as the
target.

## Inspect

Read at least:

- `docs/research/TASK_SHARED_TRANSFER_FORMAL_V2_20260923.md`
- `tools/substrate/tasks/rl_shared_transfer_combination_v1.json`
- `tools/substrate/protocols/rl_shared_transfer_combination_v1.json`
- `tools/substrate/baseline.py`
- `tools/substrate/baseline_verify.py`
- `tools/substrate/readiness.py`
- `tools/substrate/qualification.py`
- `tools/research/preflight.py`
- `tools/research/identity.py`
- integrity/guard/watchdog/ledger code that materially controls the formal run.

No MuJoCo stepping, policy inference, qualification, capture, training or
scientific attempt is allowed.

## Review questions

Decide whether this exact HEAD and task procedure are safe and auditable to run:

1. Does detached Praxis v2 identity fail closed on repo/branch/commit/cleanliness?
2. Are canonical source/checkpoint/runtime resources verified before use?
3. Does qualification remain clean and zero-science?
4. Does prepare consume zero physics and bind exact inputs/reviews?
5. Is user START authorization bound to exact HEAD/protocol/prepared manifest and
   max_attempts=2?
6. Is capture single-invocation/no-retry with durable external attempt claims?
7. Do first-nonpass and exact-repeat semantics match the protocol?
8. Are watchdog/safety/integrity/evidence paths sufficient to prevent a silent
   unbounded or replacement run?
9. Does offline verification independently audit the decisive claims?
10. Can tracked closeout be written only after the scientific run without
    invalidating the frozen capture identity?

VETO any issue that could consume attempts incorrectly, permit a replacement
run, change the frozen scientific condition, or make the result unauditable.

## Output

Write exactly:

`docs/validation/shared_transfer_formal_v2_20260923/execution_review.json`

with:

```json
{
  "schema": 1,
  "role": "execution",
  "reviewer": "gpt6-luna-max-execution-review-v2-20260923",
  "target_head": "<exact PRAXIS_TASK_COMMIT>",
  "verdict": "APPROVED or VETO",
  "summary": "<bounded rationale>",
  "checks": ["<specific check>", "..."],
  "limitations": ["<remaining non-veto caveat>", "..."]
}
```

Do not modify protocol, task configuration, runtime code or thresholds.
Commit the review JSON and any strictly necessary review note, then produce the
normal Praxis evidence closeout citing the inspected evidence.
