# TASK — Shared transfer combination confirmation preparation (GPT-6 Luna max)

Date: 2026-09-23
Project: Go2 Substrate Gate 0
Mode: scientific preparation / zero-step only
Formal scientific execution: NOT authorized in this task

## Trigger

The public CTS source-aligned baseline is now sealed at main. Evidence establishes:
- source 1.0 m/s flat reference passes and repeats deterministically;
- the shared FrozenPolicy interface reproduces the source trajectory exactly at source conditions;
- source low-speed 0.15/0.30 m/s is weak;
- shared model alone at 1.0 m/s passes;
- shared home alone at 1.0 m/s passes;
- first-inference timing materially affects lateral drift;
- the first historical shared-substrate 0.15 m/s capture remains a sealed FAIL and MUST NOT be retried.

Canonical inputs:
- docs/PROJECT_RECORD.md
- docs/TOPIC_AUDIT.md
- CURRENT.md
- docs/validation/rl_baseline_20260923/RESULTS.md
- docs/validation/governance_diagnosis_20260922/RESULTS.md
- docs/research/SOP.md

## Objective

Prepare the next prospective experiment that tests the complete combination actually intended for subsequent shared-substrate capability mapping:

1. shared Go2 MuJoCo model;
2. shared home/reset pose;
3. upstream-aligned ten-PD-step startup before first policy inference;
4. shared FrozenPolicy / observation-action adapter;
5. the same pinned public CTS checkpoint;
6. a source-proven 1.0 m/s flat command condition.

The purpose is to determine whether the COMPLETE transferred stack preserves the already-proven source 1.0 m/s capability. This is a substrate-validity check, not a terrain capability claim and not a paper result by itself.

## Scientific reasoning requirements

Before implementing anything, audit whether this combination test is still the minimal discriminating next experiment given the sealed ten-case baseline. If a strictly smaller or logically cleaner prospective test is required to avoid a confound, explain it and implement that bounded correction. Do not broaden into a new research direction.

Explicitly separate:
- what is already proven by single-factor tests;
- what remains unproven because interaction effects are possible;
- what this combination test can falsify;
- what it cannot establish even if it passes.

Do NOT infer that individually passing factors imply the combination passes.

## Protocol constraints

Prospectively freeze a new protocol/campaign identity. Do not modify or resume:
- rl-flat-compatibility-v1;
- rl-source-baseline-v1;
- any prior attempt ledger or raw evidence.

Use the same pinned checkpoint/source provenance unless a hard integrity mismatch vetoes the task.

Default design intent:
- flat environment;
- 1.0 m/s forward command;
- shared model + shared home + ten-step startup + shared adapter together;
- sufficient duration to compare with the established 1.0 m/s reference;
- deterministic execution;
- repeat budget chosen prospectively and justified;
- predeclared longitudinal, lateral, yaw, safety, contact, and integrity criteria;
- no post-outcome threshold tuning.

Reuse existing source-baseline acceptance definitions when scientifically appropriate. If a threshold must differ, justify it prospectively from the measurement question, not from expected outcomes.

## Required engineering work

1. Reuse existing substrate machinery where possible; do not create a parallel runner without need.
2. Add/modify only the minimum protocol/runner/verifier code required for this combination confirmation.
3. Ensure raw evidence, attempt accounting, exact-head preparation, review binding, deterministic settings, timeout handling, and independent offline verification remain at least as strong as the latest accepted substrate workflow.
4. Add focused regression tests for the combined configuration and any new protocol semantics.
5. Run all proportionate repository/portable/native checks required by SOP for the changed dependency set.
6. Perform REAL model/checkpoint loading and zero-step preparation only.
7. Confirm zero scientific attempts and zero MuJoCo integration steps at task closeout.

## Hard execution boundary

STOP at READY_AWAITING_START.

Do not create a START_FORMAL_CAPTURE authorization.
Do not call the formal capture path.
Do not consume a scientific attempt.
Do not integrate physics for this new campaign.
Do not tune the policy/model/controller.
Do not train or fine-tune.
Do not start terrain/MJPC/DIAL work.
Do not retry or modify historical campaigns.

A later explicit user instruction is required to cross the formal-start boundary.

## Worker/runtime check

This task is intended to be the first research task after the project worker switch to:
- model: gpt-6-luna
- reasoning effort: max

Verify the task worktree's trusted worker configuration is consistent with that intended selection. If the checked-in configuration is not consistent, stop and record an infrastructure veto instead of silently running under another declared configuration.

## Required tracked closeout

Create:
- docs/research/TASK_SHARED_TRANSFER_COMBINATION_20260923.md (this task remains immutable except trusted mechanical normalization);
- a prospective protocol document or update to the appropriate existing protocol documentation;
- machine-readable protocol/config;
- focused tests;
- docs/validation/shared_transfer_combination_prep_20260923/RESULTS.md;
- update docs/PROJECT_RECORD.md and CURRENT.md only if the preparation genuinely changes the canonical frontier.

The closeout must state:
- exact question/falsifier;
- exact frozen factors;
- explicit unchanged factors;
- acceptance/safety criteria and rationale;
- test/qualification results;
- exact zero-step preparation result;
- attempt count = 0;
- physics steps = 0;
- next explicit START action if preparation is accepted;
- any veto/remaining uncertainty.

## Stop conditions

Stop without formal execution if:
- current source baseline evidence contradicts the proposed test logic;
- checkpoint/model/source integrity cannot be verified;
- worker configuration does not reflect GPT-6 Luna max as intended;
- required independent preparation/review or verification cannot be made reproducible;
- the change would require modifying sealed historical evidence;
- a prerequisite scientific decision is genuinely unresolved.

Do not ask the user about routine implementation choices already determined by the canonical project record and this task.
