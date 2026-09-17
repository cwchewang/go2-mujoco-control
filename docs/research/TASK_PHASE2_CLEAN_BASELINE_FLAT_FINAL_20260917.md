# Phase2 clean baseline flat reproduction — final host canary

Mode: `confirmatory / one-live-canary`

Exact parent: `2eb92bc62be6fba2dee26ac9229520d8835c6246`
Scientific clean-baseline parent: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`
DDS runtime status at parent: `DDS_RUNTIME_ROOT_FIXED`

## Question

Can the P0 clean baseline reproduce a low-speed flat-ground trot now that the live-execution and DDS runtime layers have been repaired?

This is the same scientific question as the earlier flat reproduction tasks. All earlier host attempts consumed zero scientific attempts because they failed before a valid controller handoff. Do not reinterpret those protocol failures as locomotion evidence.

## Frozen scientific semantics

Exactly one flat-ground live canary is authorized.

Use:
- clean baseline enabled;
- default flat Go2 scene `unitree_robots/go2/scene_leg_lift_demo.xml`;
- task `stand-walk-lie`;
- Raibert trot kernel;
- period `0.60 s`;
- duty `0.75`;
- step length `0.091 m`;
- foot lift `0.020 m`;
- `kp=63`;
- `kd=2.8`;
- Raibert velocity gain `0.05 s`;
- Raibert max adjustment `0.010 m`;
- world feedback max `0.060`;
- world feedback slew `0.004`;
- torque limit `35 Nm`;
- maximum `64` gait cycles;
- headless;
- DDS domain `220`;
- nominal commanded speed `0.091 / 0.60 = 0.1516666667 m/s`.

Forbidden scientific changes:
- no Cartesian-world path;
- no terrain planner/sensor mode;
- no sprint/high-speed options;
- no gait, MPC, WBC, IK/FK, gains, contact, scene, safety, timing, command, threshold, or locomotion tuning;
- no parameter sweep or comparison run;
- no retry/replacement live run after scientific capture begins.

## Execution preparation allowed before live

The task worktree is fresh and ignored build outputs are not authoritative. Before host live execution, Luna may implement or repair only the minimal exact-source launch plumbing needed so the frozen host command is self-sufficient.

The frozen host runner path is:
`example/cpp/scripts/run_trot_exact_source.sh`

If it does not yet exist, implement it as a thin maintained execution helper. It may only:
1. prove the current candidate SHA/worktree is clean for tracked source;
2. deterministically configure/build `simulate/build/unitree_mujoco` from the candidate simulator source, using the permitted read-only MuJoCo SDK/runtime under `/home/che/dev/go2-workspace/current/simulate/mujoco` as dependency only;
3. deterministically configure/build `example/cpp/build/real_trot_go2` from the same candidate source;
4. record build/source/dependency/binary hashes in the requested run directory before launch;
5. invoke the existing canonical `run_trot.sh` exactly once with the arguments passed through unchanged.

It must not alter scientific arguments, choose another domain, retry a failed run, substitute a controller/simulator binary from another checkout, or add post-hoc locomotion logic.

The canonical DDS runtime added by the exact parent must remain in force. Do not bypass or disable it.

Luna may run syntax/unit/build checks in the sandbox, but MUST NOT launch MuJoCo/DDS/live controller from the sandbox. The trusted host executor owns the single live invocation.

## Attempt boundary and budget

A scientific attempt begins only at the first valid post-handoff controller state/control sample after both simulator DDS readiness and controller LowState/LowCmd handoff are established.

- Prelaunch/build/DDS failure before that point is `PROTOCOL_FAILURE` and consumes zero scientific attempts.
- Once a valid post-handoff sample exists, the one scientific attempt is consumed.
- There is no second live run, automatic scientific retry, alternate domain, or tuning follow-up in this task.

## Measurements

From immutable raw evidence determine at minimum:
- whether controller handoff occurred and timestamp/sample boundary;
- completed gait cycles;
- stand → walk → return-to-stand lifecycle status;
- commanded and measured forward speed during the defined locomotion interval;
- clean target-feasibility rejections;
- strict ID-WBC/QP rejections promoted to motion failure;
- emergency/hard safety stop;
- torque-envelope saturation if exposed by the controller log/data;
- body stability/tracking evidence sufficient to distinguish a controller/tracking failure from protocol failure.

All metrics must be reproducible from raw logs/CSV with formulas or deterministic analysis code.

## Pass criteria

Classify `CLEAN_BASELINE_FLAT_REPRODUCED` only if all are true:
1. valid controller handoff occurs;
2. all 64 requested gait cycles complete;
3. the lifecycle returns normally to stand without a hard/emergency stop;
4. no clean target-feasibility rejection terminates/promotes into motion failure;
5. no strict WBC/QP rejection terminates/promotes into motion failure;
6. measured forward speed over the preregistered locomotion interval is in `[0.11, 0.19] m/s`;
7. no gross tracking/stability failure invalidates the run.

Otherwise use exactly one primary classification:
- `CLEAN_BASELINE_TARGET_FEASIBILITY_FAIL`
- `CLEAN_BASELINE_WBC_STRICT_FAIL`
- `CLEAN_BASELINE_TRACKING_OR_STABILITY_FAIL`
- `PROTOCOL_FAILURE`

Choose the earliest causal boundary supported by evidence. Do not attribute downstream symptoms to WBC if target feasibility failed first, and do not call a pre-handoff execution abort a locomotion failure.

## Closeout

Write:
- `docs/validation/phase2_clean_baseline_flat_final_20260917/RESULTS.md`
- `docs/validation/phase2_clean_baseline_flat_final_20260917/analysis.json`
- `docs/validation/phase2_clean_baseline_flat_final_20260917/provenance.csv`

Separate the closeout into:
1. `FACTS` — immutable host/raw facts;
2. `DERIVED METRICS` — reproducible calculations;
3. `LUNA INTERPRETATION` — proposed classification, explicitly reviewable/overturnable by Sol.

Include exact candidate/source SHA, simulator/controller hashes, DDS support/config hash, frozen command, handoff boundary, raw file hashes, and scientific-attempt-consumed status.

<!-- ATLAS_HOST_EXPERIMENT
{"schema_version":1,"command":["bash","example/cpp/scripts/run_trot_exact_source.sh","90","_runs/phase2_clean_baseline_flat_final_20260917/C","--controller-duration","70","--task","stand-walk-lie","--kernel","raibert-trot","--period","0.60","--duty","0.75","--step-length","0.091","--foot-lift","0.020","--kp","63","--kd","2.8","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--clean-baseline","--tau-limit","35","--max-cycles","64","--headless","--domain-id","220"],"domain_id":220,"run_dir":"example/cpp/experiments/_runs/phase2_clean_baseline_flat_final_20260917/C","timeout_s":600,"environment":{"LD_LIBRARY_PATH":"/home/che/dev/go2-workspace/current/simulate/mujoco/lib"}}
ATLAS_HOST_EXPERIMENT -->
