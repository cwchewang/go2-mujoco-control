# TASK — Independent science review for shared transfer formal v2

## Role

Act as an independent science reviewer for the frozen shared-transfer formal
experiment. This task is review-only and zero-physics.

Reviewer identity to record exactly:

`gpt6-luna-max-science-review-v2-20260923`

The scientific execution HEAD being reviewed is exactly the frozen starting
commit exposed as `PRAXIS_TASK_COMMIT`. Do not review your eventual result
commit as the target.

## Inspect

Read at least:

- `tools/substrate/protocols/rl_shared_transfer_combination_v1.json`
- `tools/substrate/tasks/rl_shared_transfer_combination_v1.json`
- `docs/research/TASK_SHARED_TRANSFER_FORMAL_V2_20260923.md`
- the sealed source baseline/history needed to understand what is already proven;
- implementation paths used by `tools.substrate.baseline` and its analyzer.

No MuJoCo stepping, policy inference, qualification, capture, training or
scientific attempt is allowed.

## Review questions

Decide only whether the frozen experiment is scientifically valid to run:

1. Is the combined model + shared home + adapter interaction the minimal
   unresolved 1.0 m/s flat question given prior evidence?
2. Are thresholds and stop rules prospective rather than selected from this new
   outcome?
3. Is the two-case repeat requirement appropriate and bounded?
4. Are PASS/FAIL/safety/integrity interpretations stated narrowly enough?
5. Is any important scientific confound severe enough to veto execution?

Do not rank alternatives or redesign the study unless a veto requires a concrete
reason.

## Output

Write exactly:

`docs/validation/shared_transfer_formal_v2_20260923/science_review.json`

with:

```json
{
  "schema": 1,
  "role": "science",
  "reviewer": "gpt6-luna-max-science-review-v2-20260923",
  "target_head": "<exact PRAXIS_TASK_COMMIT>",
  "verdict": "APPROVED or VETO",
  "summary": "<bounded rationale>",
  "checks": ["<specific check>", "..."],
  "limitations": ["<what this experiment cannot establish>", "..."]
}
```

Do not modify protocol, task configuration, runtime code or thresholds.
Commit the review JSON and any strictly necessary review note, then produce the
normal Praxis evidence closeout citing the inspected evidence.
