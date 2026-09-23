# TASK — Exact-head qualification and zero-step preparation for shared transfer combination v1

Date: 2026-09-23
Stage: exact-head readiness only
Formal capture: NOT authorized
Scientific attempts: 0 required
Physics steps: 0 required

## Parent

Implementation result:
`90588fbfd53a65c42af6cdc237ec7bfd8f823d81`.

Protocol:
`tools/substrate/protocols/rl_shared_transfer_combination_v1.json`.

Task configuration:
`tools/substrate/tasks/rl_shared_transfer_combination_v1.json`.

The complete combination and its prospective gates were already designed and implemented by GPT-6 Luna max in #148. Do not redesign them here.

## Objective

On this exact clean HEAD, after two independent exact-target reviews exist:

1. verify the science and execution reviews both approve this exact HEAD;
2. run the required clean/non-development substrate qualification with the reliable substrate interpreter;
3. perform REAL model/checkpoint loading and zero-step preparation for the new campaign;
4. independently verify the prepared bundle;
5. stop at `READY_AWAITING_START`.

No formal capture is authorized.

## Independent review inputs

Before doing qualification or preparation, read the final review closeouts from these review branches:

- `research/review-shared-transfer-science-20260923`
- `research/review-shared-transfer-execution-20260923`

Each review must explicitly bind and approve this exact execution HEAD. Reviewer identities must differ. If either review is missing, vetoes, binds another HEAD, or is ambiguous, STOP without qualification/preparation.

Construct the ignored review JSON required by `tools.substrate.readiness.validate_review` from those accepted review closeouts. Do not fabricate approval.

## Required execution

Use the provisioned canonical resources under `.substrate/`; do not download/install.

Use the reliable interpreter:
`.substrate/venv-reliable/bin/python`.

Run a fresh clean qualification into a new ignored evidence path under:
`_runs/shared_transfer_combination_prep_20260923/`.

Then run:
`python -m tools.substrate.baseline prepare`
with:
- `--task tools/substrate/tasks/rl_shared_transfer_combination_v1.json`;
- the exact independent review JSON;
- the fresh accepted qualification receipt;
- a fresh preparation output.

Verify the prepared bundle using the existing independent baseline verifier/readiness machinery as applicable without integrating physics.

## Hard boundaries

- No `capture`.
- No START_FORMAL_CAPTURE authorization.
- No MuJoCo integration step for this campaign.
- No scientific attempt consumption.
- No training/tuning.
- No threshold/protocol changes.
- No historical campaign mutation/retry.
- No network downloads/installs.
- Do not alter protocol/runtime code in this task. If code changes are needed, stop and report a veto; they require a new reviewed implementation HEAD.

## Required closeout

Create only:
`docs/validation/shared_transfer_combination_prep_20260923/RESULTS.md`

Record:
- exact execution HEAD;
- science/execution reviewer identities and bound HEAD;
- qualification path/status/fingerprint;
- preparation path/status/manifest;
- checkpoint/source/runtime verification;
- readiness verdict;
- physics_steps = 0;
- scientific_attempts = 0;
- exact next boundary: explicit user START_FORMAL_CAPTURE authorization;
- any veto.

Do not claim PASS/FAIL for locomotion; no locomotion experiment occurs here.
