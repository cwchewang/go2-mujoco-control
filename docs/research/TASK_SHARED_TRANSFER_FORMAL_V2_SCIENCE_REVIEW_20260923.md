# Independent science review — shared-transfer formal v2

Target execution HEAD: `bab5d56af48a23894c52982ad23b73f2a361e554`

## Role

Act only as the independent science reviewer. Do not run MuJoCo physics, do not
start the campaign, do not create authorization, and do not change the target
experiment.

Inspect the target HEAD and the sealed source-baseline evidence/history needed
to judge the scientific design.

Review at least:

- `tools/substrate/protocols/rl_shared_transfer_combination_v1.json`
- `tools/substrate/tasks/rl_shared_transfer_combination_v1.json`
- `docs/research/TASK_SHARED_TRANSFER_FORMAL_V2_20260923.md`
- the established source 1.0 m/s baseline and prior shared-home/shared-model/
  shared-adapter evidence already tracked in the repository.

Verify specifically:

1. protocol SHA remains
   `2d23131cb104be50aeb163737e3cfbf10f5a9291acf7726c2eda75e3fa5e9b32`;
2. the prospective thresholds were not changed after prior results;
3. the complete shared combination is still the minimal unresolved interaction
   question;
4. two-case repeat semantics and first-nonpass stop are scientifically coherent;
5. PASS/FAIL interpretation is bounded to this exact flat 1.0 m/s setup;
6. no result can legitimately imply low-speed, terrain, hardware, or general
   robustness, or identify a causal factor.

Write exactly one tracked result file:

`docs/validation/shared_transfer_formal_v2_science_20260923/review.json`

Schema:

{
  "schema": 1,
  "role": "science",
  "target_head": "bab5d56af48a23894c52982ad23b73f2a361e554",
  "reviewer": "gpt6-luna-max-science-review-v2",
  "verdict": "APPROVED" | "VETO",
  "summary": "...",
  "evidence": ["specific file/commit/check references"],
  "concerns": ["..."]
}

Use APPROVED only if this exact target HEAD is scientifically suitable for the
frozen formal campaign. A concern that does not invalidate execution may remain
in concerns. If any material prospective-design problem exists, use VETO.

Run only read-only/static checks required to support the review. Preserve raw
review evidence under `$PRAXIS_EVIDENCE_DIR`, cite it in Praxis closeout, and
commit only the review.json result. Do not push; Praxis will publish it.
