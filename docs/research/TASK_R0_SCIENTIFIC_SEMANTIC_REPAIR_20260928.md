# R0 scientific-semantic repair — 2026-09-28

## Scope

Repair the scientific semantics and recoverability exposed by the 2026-09-28 independent audit. This is engineering/documentation repair only. Do **not** run a new scientific campaign or reinterpret unchanged raw evidence as a new experiment.

Base: `0a143ebbed6a5ad1b5fb7a7c1bf2f618243b8790`.
Historical capture source: `e40b0933572345f23b37e3bb06350518fde63e76`.
Archive ref: `archive/rl-capability-map-v1-20260924`.

## Frozen prohibitions

- Do not edit or replace the sealed #189 raw evidence.
- Do not change `rl_capability_map_v1.json` thresholds, cases, commands or attempt budget.
- Do not edit the historical `scene_low_friction_patch.xml`; add a versioned successor if needed.
- Do not invoke formal capture, `mj_step`, `mj_step1` or `mj_step2`.
- Do not rerun #189 or consume a scientific attempt.
- Do not create a new method or promote a paper topic.
- Do not rewrite Git history.

## Required repairs

### R0.1 — #189 semantic errata

Create a versioned erratum for #189 and link it prominently from the existing RESULTS document.

Record, without changing the original raw evidence:
1. The original `low_friction_cross` PASS is only a geometric/task-goal pass under the frozen scene. It is **not evidence of low-friction robustness** because the compiled foot geoms have priority 1 while the patch has priority 0, so the effective foot–patch contact uses the foot friction rather than the intended patch friction.
2. Preserve the terrain 5 cm / 10 cm / repeated-step conclusions; this low-friction issue does not invalidate them.
3. The schema-2 angular-velocity analyzer incorrectly rotates MuJoCo free-joint angular velocity a second time. Correct the implementation and verifier.
4. Preserve an explicit offline recomputation record from the existing #189 raw trajectory: command `wz=0.5`; corrected body-local qvel-z mean approximately `0.1038956543`, MAE approximately `0.3961043457`; therefore the frozen yaw probe remains PERFORMANCE_FAIL under tolerance 0.1. This is a zero-physics reanalysis, not a new campaign.

### R0.2 — Permanent semantic regression tests

Add tests that fail if:
- free-joint angular velocity is incorrectly rotated as if world-frame;
- the independent verifier repeats that error;
- a versioned low-friction scene does not actually produce the intended runtime `mjContact` friction/condim for foot–patch support;
- a foot is simultaneously supported by the normal floor while it is meant to be supported by the low-friction patch in the representative semantic fixture.

The low-friction test must inspect compiled/runtime MuJoCo contact semantics, not merely XML strings. It may use `mj_forward`, but must not integrate physics.

### R0.3 — Recover schema-2 maintenance surface

Recover the reviewed #189 schema-2 execution/analyzer/verifier surface onto this branch from the historical capture source, while preserving current main identity/preflight changes. The minimum known delta includes:
- `tools/substrate/baseline.py`
- `tools/substrate/baseline_episode.py`
- `tools/substrate/baseline_verify.py`
- `tools/substrate/test_baseline.py`
- `tools/substrate/protocols/rl_capability_map_v1.json`
- `tools/substrate/tasks/rl_capability_map_successor_v1.json`
- `tools/substrate/tasks/rl_capability_map_v1.json`

Do not blindly cherry-pick the full historical branch. Verify imports and tests from a fresh checkout.

### R0.4 — Versioned corrected low-friction semantic fixture

Add a new scene/version rather than modifying v1. Ensure the intended patch is the actual supporting surface and its effective contact friction/condim is observable and tested. Do not run a capability experiment on it in this task.

### R0.5 — Architecture decision and canonical state

Integrate the substance of PR #193 into one coherent canonical update rather than leaving TOPIC_AUDIT alone.

Add a short ADR recording:
- MuJoCo is the canonical evaluation physics for the current project;
- MuJoCo/MJX is the intended scalable substrate direction, not yet fully implemented;
- Go2 is the first testbed, not the project identity;
- MJPC/iLQR is a strong comparator, not a privileged default truth;
- mature solver/controller infrastructure should be reused; scientific ownership lives in task/information/timing/intervention definitions, diagnostics, comparisons and evidence-driven new mechanisms.

Synchronize `docs/PROJECT_RECORD.md`, `docs/research/current.json`, generated `CURRENT.md`, and `docs/TOPIC_AUDIT.md`. Distinguish explicitly:
- planned architecture;
- currently executable capabilities;
- scientifically verified results.

Do not claim that a generic multi-controller platform already exists.

### R0.6 — Minimal substrate contract direction

Do **not** build a universal SDK here. Document the next minimal interfaces only: TaskSpec, ScenarioSpec, InformationSpec, TimingSpec, ControllerAdapter, canonical Evaluator/physical-oracle boundary. Implementation comes after R0 passes.

## Deterministic acceptance

Run without scientific integration:
- `git diff --check`;
- relevant portable/unit tests;
- exact tests for body angular-velocity semantics;
- runtime contact-semantic test on the new low-friction fixture using `mj_forward`;
- repository hygiene;
- import/loader checks for restored schema-2 protocol/task surface.

Produce a concise closeout stating exactly which old conclusions were retained, corrected, or withdrawn.

No reviewer is required for ordinary plumbing. Do not run qualification/prepare/capture.