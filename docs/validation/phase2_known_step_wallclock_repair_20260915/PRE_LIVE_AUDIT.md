# Phase2 known-step wall-clock repair pre-live audit

Date: 2026-09-15
Branch: research/phase2-known-step-wallclock-repair-20260915
Parent: 9a3611e5e64150c45241cee92514d38ea6732857

## Scope and source audit

- The branch descends directly from the parent closeout.
- Relative to the parent, only the repair task document and
  example/cpp/scripts/run_phase2_known_step_5cm_wallclock_repair_ab.sh
  are added before live execution.
- No runtime source, scene, terrain-adapter math, controller parameter,
  WBC/MPC, gait, threshold, or D4 file changed after the parent.
- The runner contains --wall-clock-motion exactly once. Its frozen
  control arguments match the prior runner; only the run root and domains
  are administrative changes. A is domain 231 and B is domain 232.
- The prior raw run root
  example/cpp/experiments/_runs/phase2_known_step_5cm_20260915
  remains untouched and is not reused.

## Pre-live verification

- Controller Release build: PASS.
- test_known_step_terrain_adapter: PASS.
