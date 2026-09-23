# TASK — Design and implement the shared-transfer combination confirmation

Date: 2026-09-23
Worker intent: GPT-6 Luna at max reasoning effort
Stage: scientific design/implementation only
Formal capture: NOT authorized
Scientific attempts: 0 required
MuJoCo physics for the new campaign: NOT authorized

## Why this task exists

The sealed public CTS source baseline established:

- source-aligned 1.0 m/s flat locomotion passes and repeats deterministically;
- the shared FrozenPolicy adapter reproduces the source trajectory exactly under source conditions;
- source 0.15/0.30 m/s is weak;
- shared model alone at 1.0 m/s passes;
- shared home alone at 1.0 m/s passes;
- first-inference timing can materially change lateral drift;
- the historical shared-substrate 0.15 m/s campaign remains sealed FAIL and must never be retried.

The previous combined-preparation task (#145) correctly stopped because Praxis did not provision the canonical substrate resources and because implementation plus exact-head preparation were incorrectly coupled in one dirty pre-commit worktree. PR #146 and live acceptance #147 fixed resource provisioning and logical branch identity. This task intentionally performs only the implementation/freeze stage. Exact-head qualification and zero-step preparation will be a separate follow-up task after this task's result commit is trusted and pushed.

## Canonical context

Read first:

- docs/PROJECT_RECORD.md
- docs/TOPIC_AUDIT.md
- CURRENT.md
- docs/OPERATING_GUIDE.md
- docs/research/SOP.md
- docs/validation/rl_baseline_20260923/RESULTS.md
- docs/validation/governance_diagnosis_20260922/RESULTS.md
- tools/substrate/protocols/rl_source_v1.json
- tools/substrate/baseline.py
- tools/substrate/baseline_episode.py
- tools/substrate/baseline_verify.py

Infrastructure facts already live-accepted by #147:

- task worktree receives the canonical checkpoint with SHA-256
  9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d;
- all 50 pinned upstream source files pass rl_reference.lock.json;
- reliable Python imports Torch 2.6.0+cpu, MuJoCo 3.3.6, NumPy 2.2.6;
- MJPC admission binary is present;
- task worktree retains its frozen logical research/* branch;
- resources are ignored links into the persistent canonical cache, not tracked copies.

Do not spend this task re-solving those infrastructure problems.

## Scientific question

Does the COMPLETE shared deployment combination preserve the already-proven source-aligned 1.0 m/s flat capability when the following factors are applied together?

1. shared Go2 MuJoCo model;
2. shared home/reset pose;
3. source-aligned ten-PD-step startup before first policy inference;
4. shared FrozenPolicy observation/action adapter;
5. the same pinned public CTS checkpoint;
6. 1.0 m/s forward flat command.

This is an interaction/transfer-integrity test. Individually passing factors do not prove the combination passes.

## Required reasoning

Before editing, verify that this remains the minimal discriminating next experiment given the ten-case source baseline. If a strictly cleaner bounded formulation is needed to isolate the interaction without introducing a new confound, make that correction and explain it in the tracked closeout.

Explicitly state:

- what the existing single-factor results already prove;
- what interaction remains unproven;
- what a PASS would establish;
- what a FAIL would establish;
- what neither outcome can establish.

Do not turn this into a paper hypothesis or a broad terrain benchmark.

## Required implementation

Prospectively define a NEW campaign/protocol identity. Never modify, resume, or reuse the ledgers of:

- rl-flat-compatibility-v1;
- rl-source-baseline-v1.

Reuse existing source-baseline machinery instead of creating a parallel framework unless a concrete contract prevents reuse.

Freeze at minimum:

- exact scene/model choice;
- exact reset/home semantics;
- ten-PD-step startup semantics;
- policy adapter;
- checkpoint/source identity;
- 1.0 m/s command;
- duration and measurement window;
- longitudinal speed/MAE gates;
- lateral drift and yaw gates;
- safety/contact semantics;
- deterministic settings;
- prospective repeat budget and first-nonpass behavior;
- attempt accounting;
- offline verification requirements.

Prefer existing 1.0 m/s source-baseline gates when scientifically comparable. Any difference must be justified prospectively, not chosen to make the expected result pass.

Implement the smallest code/config/test changes needed so a later clean-HEAD task can:

1. run final qualification;
2. perform real model/checkpoint zero-step preparation;
3. stop at READY_AWAITING_START;
4. later accept a separate explicit formal-start authorization.

## Allowed work in this stage

Allowed:

- edit tracked protocol/config/runner/verifier/test/docs needed for this new campaign;
- inspect the provisioned canonical resources;
- import/load libraries for non-scientific engineering checks if needed;
- run unit/contract/static tests;
- run synthetic tests that do not integrate the new campaign's real MuJoCo plant;
- run repository quality checks;
- reason from sealed prior raw evidence without modifying it.

Not allowed:

- formal capture;
- any new campaign MuJoCo integration step;
- consuming any scientific attempt;
- training/fine-tuning;
- tuning thresholds from observed new outcomes;
- retrying any historical campaign;
- modifying sealed evidence/ledgers;
- expanding into terrain/MJPC/DIAL experiments.

Do NOT run final clean-HEAD qualification or final READY_AWAITING_START preparation in this task. Those belong to the follow-up task after this implementation result commit is frozen.

## Required tracked closeout

Create:

- a machine-readable new protocol/config;
- appropriate task/runner/verifier support;
- focused regression tests;
- a concise prospective protocol document if existing docs are insufficient;
- docs/validation/shared_transfer_combination_design_20260923/RESULTS.md.

The closeout must contain:

- exact scientific question and falsifier;
- exact factors changed together and factors held fixed;
- why the test is minimal;
- acceptance/safety criteria with rationale;
- implementation files changed;
- tests run and results;
- proof that no new campaign physics was integrated;
- scientific attempts consumed = 0;
- exact next task: clean-HEAD qualification + real zero-step preparation only;
- remaining uncertainty.

Do not update the canonical PROJECT_RECORD/CURRENT to claim readiness unless this task genuinely changes only the implementation frontier. It must not claim READY_AWAITING_START; that status is reserved for the follow-up exact-HEAD preparation.

## Closeout boundary

Finish with intended tracked changes only. The trusted Praxis wrapper owns the result commit/push.

If the design cannot be made prospective and unconfounded from current evidence, stop with a tracked veto closeout rather than inventing thresholds or running physics.
