# Canonical clean-baseline repeatability — R2 of 3

Mode: `confirmatory / independent-repeat / one-live-canary`

Canonical protected-main baseline: `e30782ad916ef1614a877d7a3c122f62682c8f19`
Accepted predecessor flat result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`
Suite ID: `canonical_clean_baseline_repeatability_20260917`
Replicate: `R2 / 3`

## Purpose

This is the second of three preregistered, independent fresh-worktree reproductions used to seal the canonical clean locomotion foundation. R1, R2, and R3 are defined from the same canonical main SHA before any repeat result is inspected. Their controller/simulator/scientific parameters are identical; only the replicate label and raw run directory differ.

The suite passes only if all three independently satisfy the frozen flat-baseline criteria. Do not tune or rewrite this replicate in response to R1.

## Source freeze

No controller, simulator, gait, WBC/MPC, kinematics, DDS-runtime, scene, safety, test threshold, or launcher implementation change is authorized before live execution.

Before host execution, prove `example/cpp/`, `simulate/`, and `unitree_robots/` are byte-for-byte unchanged from canonical main `e30782ad916ef1614a877d7a3c122f62682c8f19`. The task document itself may differ. If a source/runtime repair is required, classify `PROTOCOL_FAILURE` and stop; do not repair it inside this replicate.

Luna may run read-only/static/build checks but MUST NOT launch MuJoCo, DDS, or controller. The trusted host executor owns the sole live invocation.

## Frozen scientific semantics

Exactly one flat-ground live attempt:

- `--clean-baseline`
- scene `unitree_robots/go2/scene_leg_lift_demo.xml`
- task `stand-walk-lie`
- kernel `raibert-trot`
- period `0.60 s`, duty `0.75`, step `0.091 m`, lift `0.020 m`
- `kp=63`, `kd=2.8`
- Raibert gain `0.05 s`, max adjustment `0.010 m`
- world feedback max `0.060`, slew `0.004`
- torque limit `35 Nm`
- maximum `64` cycles
- headless, DDS domain `220`
- nominal speed `0.1516666667 m/s`

Forbidden: any parameter change, alternate domain, Cartesian-world, terrain, sprint, tuning/recovery/comparison run, or replacement live attempt.

## Attempt boundary

Attempt starts at first valid post-handoff state/control sample. Pre-handoff execution failure is `PROTOCOL_FAILURE` with no scientific attempt consumed. Once handoff occurs, R2 is consumed; no retry.

## Required measurements

Record exact source identity against canonical main, simulator/controller/DDS hashes, handoff, lifecycle and 64 cycles, stage-2 OLS speed, target/WBC/safety rejection counts, roll/pitch, joint/foot error, support/contact quality, estimated torque, and all raw evidence hashes. Analysis must be deterministic; no live rerun.

## Pass criteria

`CLEAN_BASELINE_FLAT_REPRODUCED` requires all seven frozen gates: valid handoff; 64/64 cycles; normal lifecycle/no hard-emergency stop; no clean target failure; no strict WBC/QP failure; OLS speed in `[0.11,0.19] m/s`; no gross tracking/stability failure.

Otherwise use one earliest-causal class: `CLEAN_BASELINE_TARGET_FEASIBILITY_FAIL`, `CLEAN_BASELINE_WBC_STRICT_FAIL`, `CLEAN_BASELINE_TRACKING_OR_STABILITY_FAIL`, or `PROTOCOL_FAILURE`.

## Closeout

Write `docs/validation/canonical_clean_baseline_repeat_r2_20260917/{RESULTS.md,analysis.json,provenance.csv}` with `FACTS`, `DERIVED METRICS`, `LUNA INTERPRETATION`. Sol may overturn Luna from immutable evidence.

<!-- ATLAS_HOST_EXPERIMENT
{"schema_version":1,"command":["bash","example/cpp/scripts/run_trot_exact_source.sh","90","_runs/canonical_clean_baseline_repeatability_20260917/R2","--controller-duration","70","--task","stand-walk-lie","--kernel","raibert-trot","--period","0.60","--duty","0.75","--step-length","0.091","--foot-lift","0.020","--kp","63","--kd","2.8","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--clean-baseline","--tau-limit","35","--max-cycles","64","--headless","--domain-id","220"],"domain_id":220,"run_dir":"example/cpp/experiments/_runs/canonical_clean_baseline_repeatability_20260917/R2","timeout_s":600,"environment":{"MUJOCO_ROOT":"/home/che/.mujoco/mujoco-3.3.6","LD_LIBRARY_PATH":"/home/che/.mujoco/mujoco-3.3.6/lib"}}
ATLAS_HOST_EXPERIMENT -->
