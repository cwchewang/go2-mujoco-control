# Canonical clean-baseline repeatability — R1 of 3

Mode: `confirmatory / independent-repeat / one-live-canary`

Canonical protected-main baseline: `e30782ad916ef1614a877d7a3c122f62682c8f19`
Accepted predecessor flat result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`
Suite ID: `canonical_clean_baseline_repeatability_20260917`
Replicate: `R1 / 3`

## Purpose

This is the first of three preregistered, independent fresh-worktree reproductions used to seal the canonical clean locomotion foundation. R1, R2, and R3 are defined from the same canonical main SHA before any repeat result is inspected. Their controller/simulator/scientific parameters are identical; only the replicate label and raw run directory differ.

The suite passes only if all three independently satisfy the frozen flat-baseline criteria. Do not tune or rewrite later replicates in response to this result.

## Source freeze

No controller, simulator, gait, WBC/MPC, kinematics, DDS-runtime, scene, safety, test threshold, or launcher implementation change is authorized before live execution.

Before host execution, prove that these source surfaces are byte-for-byte unchanged from canonical main `e30782ad916ef1614a877d7a3c122f62682c8f19`:

- `example/cpp/`
- `simulate/`
- `unitree_robots/`

The task document itself may differ. If a source/runtime repair would be required, classify `PROTOCOL_FAILURE` and stop; do not repair it inside this repeatability replicate.

Luna may run read-only/static/build checks but MUST NOT launch MuJoCo, DDS, or the controller. The trusted host executor owns the sole live invocation.

## Frozen scientific semantics

Exactly one flat-ground live attempt is authorized, with:

- `--clean-baseline`
- scene `unitree_robots/go2/scene_leg_lift_demo.xml`
- task `stand-walk-lie`
- kernel `raibert-trot`
- period `0.60 s`
- duty `0.75`
- step length `0.091 m`
- foot lift `0.020 m`
- `kp=63`
- `kd=2.8`
- Raibert velocity gain `0.05 s`
- Raibert max adjustment `0.010 m`
- world feedback max `0.060`
- world feedback slew `0.004`
- torque limit `35 Nm`
- maximum `64` gait cycles
- headless
- DDS domain `220`
- nominal commanded speed `0.091 / 0.60 = 0.1516666667 m/s`

Forbidden: parameter changes, alternate domain, Cartesian-world, terrain mode, sprint/high-speed options, recovery/tuning, comparison run, or replacement live attempt.

## Attempt boundary

A scientific attempt begins at the first valid post-handoff controller state/control sample after simulator DDS readiness and LowState/LowCmd handoff.

- Build/DDS/pre-handoff failure: `PROTOCOL_FAILURE`, scientific attempt not consumed.
- Once a valid post-handoff sample exists: R1 is consumed, no retry.

## Required measurements

From immutable raw evidence determine:

- exact candidate/source SHA and source-identity check against canonical main;
- exact-source simulator/controller hashes and DDS support hash;
- valid handoff boundary;
- 64-cycle completion and stand -> walk -> return-stand -> lie lifecycle;
- measured forward speed using the same stage-2 OLS method as the accepted predecessor;
- clean target-feasibility rejections;
- strict WBC/QP rejections;
- hard/emergency stop;
- roll/pitch, joint error, foot error, support/contact quality, and estimated torque;
- raw evidence hashes.

All derived metrics must be deterministic and source-grounded. Offline analysis after the run is allowed; no live rerun is allowed.

## Pass criteria

Classify `CLEAN_BASELINE_FLAT_REPRODUCED` only if all are true:

1. valid controller handoff;
2. all 64 requested gait cycles complete;
3. normal return-to-stand/lifecycle completion with no hard/emergency stop;
4. no clean target-feasibility rejection promoted to motion failure;
5. no strict WBC/QP rejection promoted to motion failure;
6. preregistered locomotion-interval forward speed is in `[0.11, 0.19] m/s`;
7. no gross tracking/stability failure invalidates the run.

Otherwise use exactly one earliest-causal classification:

- `CLEAN_BASELINE_TARGET_FEASIBILITY_FAIL`
- `CLEAN_BASELINE_WBC_STRICT_FAIL`
- `CLEAN_BASELINE_TRACKING_OR_STABILITY_FAIL`
- `PROTOCOL_FAILURE`

## Closeout

Write:

- `docs/validation/canonical_clean_baseline_repeat_r1_20260917/RESULTS.md`
- `docs/validation/canonical_clean_baseline_repeat_r1_20260917/analysis.json`
- `docs/validation/canonical_clean_baseline_repeat_r1_20260917/provenance.csv`

Separate `FACTS`, `DERIVED METRICS`, and `LUNA INTERPRETATION`. Luna's classification is a proposal; Sol may overturn it from immutable evidence without rerunning.

<!-- ATLAS_HOST_EXPERIMENT
{"schema_version":1,"command":["bash","example/cpp/scripts/run_trot_exact_source.sh","90","_runs/canonical_clean_baseline_repeatability_20260917/R1","--controller-duration","70","--task","stand-walk-lie","--kernel","raibert-trot","--period","0.60","--duty","0.75","--step-length","0.091","--foot-lift","0.020","--kp","63","--kd","2.8","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--clean-baseline","--tau-limit","35","--max-cycles","64","--headless","--domain-id","220"],"domain_id":220,"run_dir":"example/cpp/experiments/_runs/canonical_clean_baseline_repeatability_20260917/R1","timeout_s":600,"environment":{"MUJOCO_ROOT":"/home/che/.mujoco/mujoco-3.3.6","LD_LIBRARY_PATH":"/home/che/.mujoco/mujoco-3.3.6/lib"}}
ATLAS_HOST_EXPERIMENT -->
