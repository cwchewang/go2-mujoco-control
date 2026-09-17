# Phase2 clean baseline surgery P0

Mode: `engineering-correctness / no-live`

Exact base: `21633a76b8cc9c9e820c2399fb0bdbc4b864260a`
Branch: `research/phase2-clean-baseline-p0-20260917`

## Why this task exists

The current repository contains a legitimate dynamics/control core (Go2 rigid-body model, SRBD MPC, inverse-dynamics WBC), but the active locomotion path has accumulated historical experimental overlays, hidden target modification, and fallback behavior that make scientific interpretation difficult.

This task is not a performance task and is not a terrain-crossing task. It creates an explicit clean research baseline path whose semantics are easy to explain and whose outputs are not silently changed after planning/optimization.

No live MuJoCo canary is authorized in this task.

## Human-readable invariants

The clean path must satisfy four rules:

1. A foot target requested by the planner is either accepted unchanged or explicitly rejected. It must never be silently moved to another point.
2. A WBC QP result is used only when the complete constrained solve is accepted. Equality accuracy alone must not turn a failed constrained solve into success.
3. Once the clean WBC QP returns joint torque, no experimental propulsion/force/Cartesian torque overlay may modify that torque before the normal motor safety envelope.
4. Swing-foot acceleration tracking must use the full kinematic acceleration relation `J*qdd + Jdot*qdot = a_des`.

## Scope

Create the smallest opt-in clean-baseline path needed to enforce the invariants above while preserving the existing default behavior for historical experiments.

Do not delete historical V1/V2, FULL2, sprint, governor, or fallback code in this task. Isolate the clean path from it rather than performing a large repository rewrite.

Do not tune gains for performance.

## Required changes

### A. Swing task correctness

In the inverse-dynamics WBC swing-foot objective, include the current `Jdot*qdot` term so the optimized acceleration represents:

`J*qdd + Jdot*qdot ~= a_des`.

Keep the existing stance formulation semantically unchanged.

Add a focused unit test that would fail with the old swing formulation and pass with the corrected one.

### B. Strict constrained-solver acceptance

For the clean path, a failed `SolveDenseQpEq` / constrained WBC solve must not be accepted merely because the floating-base equality residual is small.

Prefer the simplest strict behavior: if the constrained solver does not report an accepted solution, clean WBC returns failure and the caller uses an explicit safe fallback/hold rather than treating the candidate as valid.

Add a deterministic test that constructs or injects a case where inequality/convergence acceptance fails while equality residual can remain small, and prove the clean path rejects it.

Do not weaken friction, unilateral-force, or torque constraints to make the test pass.

### C. No post-QP torque mutation in clean mode

Add an explicit opt-in clean-baseline mode or equivalent isolated code path.

In that clean mode, once ID-WBC produces an accepted torque vector, prohibit experimental post-QP torque modifications such as sprint direct-force bias, front/rear force-difference torque edits, Cartesian stance `J^T` PD torque overlays, or similar campaign-only additions.

Normal final motor safety limiting is allowed and must remain explicit.

Historical/default paths must remain available and behavior-compatible.

Add a focused test/probe proving that clean-mode torque sent toward `LowCmd` equals the accepted WBC torque up to the documented final safety envelope/ramp, with no hidden extra force term.

### D. No hidden foot-target rewriting in clean mode

For the clean path, do not use `ClampFootToHipWorkspace` or `AllLegInverseKinematicsClamped` as normal target-generation semantics.

For every commanded foot target in clean mode:

- run direct IK on the unchanged target;
- verify the resulting joint configuration is inside the authoritative Go2/MuJoCo joint ranges;
- if either check fails, return an explicit target-feasibility failure / safe hold instead of changing the target.

The planner-to-IK target must therefore have exact fidelity whenever accepted.

Do not invent a new planner, projection optimizer, or terrain trajectory in this task.

Add focused tests for:

- feasible target stays bit-for-bit / tolerance-equivalent unchanged through the target-to-IK boundary;
- unreachable target is rejected rather than moved;
- IK-solvable but joint-range-invalid target is rejected rather than moved.

## Preserve the current control core

Do not replace or redesign:

- `Go2RigidBody` model evaluation;
- SRBD state/control formulation;
- contact-force MPC objective/constraints except changes strictly needed for testability of clean acceptance;
- ID-WBC floating-base dynamics equality;
- friction cone / unilaterality / torque limits;
- 500 Hz LowCmd/LowState infrastructure;
- gait phase/schedule or Raibert foothold baseline.

Do not add terrain-aware swing planning yet.

## Historical-path compatibility

Existing default CLI behavior and historical experiment launch scripts must not silently switch to the clean path.

The clean path must be opt-in and clearly named. Add the smallest documentation needed to identify exactly how it differs from legacy/historical paths.

If an existing unit test depends on a historical hidden clamp/overlay, preserve that behavior outside clean mode rather than weakening the clean invariant.

## Validation

Run the smallest relevant unit tests first, then the full portable C++ test set that is practical on Atlas.

At minimum include evidence for:

- rigid-body model tests still pass;
- SRBD MPC tests still pass;
- inverse-dynamics WBC tests pass, including new `Jdot*qdot` coverage;
- clean constrained-solver rejection test passes;
- clean target-fidelity / IK-limit tests pass;
- clean no-post-QP-torque-mutation test passes;
- `git diff --check` passes.

No live simulator run is authorized. No performance claim is authorized.

## Decision at closeout

Classify exactly one:

- `CLEAN_BASELINE_P0_READY` — all four invariants are implemented in an opt-in path and required tests pass;
- `CORE_CORRECTNESS_BLOCKED` — a required invariant cannot be implemented without exposing a deeper core defect; report the earliest concrete blocker;
- `PROTOCOL_FAILURE` — build/test/evidence failure prevents interpretation.

If `CLEAN_BASELINE_P0_READY`, the next task will be a separate flat-ground reproduction of the low-speed ~0.15 m/s trot. That future live task is not authorized here.

## Closeout

Write:

- `docs/validation/phase2_clean_baseline_p0_20260917/RESULTS.md`
- `docs/validation/phase2_clean_baseline_p0_20260917/analysis.json`
- `docs/validation/phase2_clean_baseline_p0_20260917/provenance.csv`

Also update only the minimal clean-baseline documentation/tests/source required by this task.

Do not modify raw experiment `_runs` evidence. Do not push from the agent; leave intended changes for the trusted Atlas wrapper.
