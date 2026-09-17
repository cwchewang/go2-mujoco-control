# Phase2 clean baseline flat-ground reproduction via trusted host executor

Mode: `confirmatory / one-host-live-canary`

Exact branch parent: `b986a24c423e71bfdf5017e3eebdedad6d7e9d6e`
Scientific clean-baseline parent: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`
Parent live status: zero scientific attempts consumed; prior failures were execution-layer only.

## Question

Can the opt-in clean baseline reproduce the established low-speed flat-ground Go2 trot when the live MuJoCo/CycloneDDS process is launched by the trusted Atlas host executor rather than from inside the Luna sandbox?

This is the same scientific question as the prior flat reproduction attempts. No controller tuning, terrain intervention, or scientific parameter change is authorized.

## Scientific semantics frozen

Use the clean path with:

- `--clean-baseline` enabled;
- flat default Go2 scene;
- Raibert trot kernel;
- period `0.60 s`;
- duty `0.75`;
- step length `0.091 m`;
- foot lift `0.020 m`;
- `kp=63`, `kd=2.8`;
- Raibert velocity gain `0.05 s`;
- Raibert max adjustment `0.010 m`;
- world feedback max `0.060 m`, slew `0.004 m`;
- default attitude feedback retained;
- torque limit `35 N m`;
- maximum `64` gait cycles;
- normal `stand-walk-lie` lifecycle;
- headless execution.

Do not enable `--cartesian-world`, known-step V1/V2, terrain actuation, sprint/high-speed overrides, impulse mode, direct-force overlays, or any alternative controller behavior.

The historical indexed low-speed reference is the same nominal `0.091/0.60 = 0.151667 m/s` configuration. This is contextual only; no legacy comparison run is authorized.

## Luna preparation phase

Before the host phase, Luna may autonomously perform all execution-only preparation inside its workspace sandbox:

1. verify the exact branch ancestry and that scientific/runtime source relative to the clean-baseline parent is unchanged;
2. build the exact-source `real_trot_go2` controller against the canonical read-only MuJoCo SDK available on Atlas;
3. prepare an executable simulator at `simulate/build/unitree_mujoco`, preferring an exact-source build against the same SDK; if only a canonical reference runtime can be used, record its hash/source provenance and do not claim simulator-source identity unless verified;
4. run the focused clean-baseline/IK/dense-QP/SRBD-MPC/ID-WBC/CLI tests and the practical portable test set;
5. verify `--clean-baseline` rejects coexistence with `--cartesian-world`;
6. verify the frozen host command prerequisites exist.

Luna MUST NOT launch MuJoCo, CycloneDDS, the controller/simulator pair, or any live capture itself. The trusted host executor owns that action.

No scientific source or parameter change is permitted in preparation. Execution-only build products are allowed and need not be tracked.

## Frozen trusted-host manifest

The block below is machine-readable and frozen by the exact task commit. Luna must not modify or replace it.

<!-- ATLAS_HOST_EXPERIMENT
{
  "schema_version": 1,
  "command": [
    "bash",
    "example/cpp/scripts/run_trot.sh",
    "90",
    "_runs/phase2_clean_baseline_flat_host_v4_20260917/C",
    "--controller-duration",
    "70",
    "--task",
    "stand-walk-lie",
    "--kernel",
    "raibert-trot",
    "--period",
    "0.60",
    "--duty",
    "0.75",
    "--step-length",
    "0.091",
    "--foot-lift",
    "0.020",
    "--kp",
    "63",
    "--kd",
    "2.8",
    "--raibert-velocity-gain",
    "0.05",
    "--raibert-max-adjustment",
    "0.010",
    "--world-feedback-max",
    "0.060",
    "--world-feedback-slew",
    "0.004",
    "--clean-baseline",
    "--tau-limit",
    "35",
    "--max-cycles",
    "64",
    "--headless",
    "--domain-id",
    "220"
  ],
  "domain_id": 220,
  "run_dir": "example/cpp/experiments/_runs/phase2_clean_baseline_flat_host_v4_20260917/C",
  "timeout_s": 120,
  "environment": {
    "LD_LIBRARY_PATH": "/home/che/dev/go2-workspace/current/simulate/mujoco/lib"
  }
}
ATLAS_HOST_EXPERIMENT -->

## Host execution authority

The trusted host executor may launch exactly the frozen command above once. It must record the actual candidate commit, argv, domain, timestamps, return code, host stdout/stderr hashes, and hashes of every raw file in the run directory.

The host record and raw run evidence are facts, not Luna interpretation. After host execution they are immutable for this task.

No automatic scientific retry, domain substitution, parameter change, comparison run, or terrain run is authorized.

## Post-host analysis

The same Luna thread resumes after host execution and must analyze only the trusted record plus the raw evidence it indexes.

Closeout artifacts must clearly separate:

1. `FACTS` — directly recorded host/raw evidence;
2. `DERIVED METRICS` — deterministic calculations, with source columns/formulas or analysis code sufficient for Sol to recompute;
3. `LUNA INTERPRETATION` — mechanism judgment and primary classification, explicitly reviewable/overturnable by Sol.

Report at minimum:

- whether simulator and controller started and LowState/LowCmd handoff occurred;
- whether normal stand -> gait -> return-to-stand completed;
- completed gait cycles;
- measured forward speed over `motion_stage==2` using the repository's established progress method;
- commanded/nominal speed and tracking ratio;
- max/representative roll and pitch;
- any clean target-feasibility rejection;
- any strict ID-WBC constrained-solver rejection;
- torque safety-envelope saturation, if logged;
- maximum relevant joint/foot tracking error available in existing logs;
- emergency/hard safety stop or abnormal contact failure;
- actual source/binary/scene provenance recorded by the host/runner.

## Passing criterion

Classify `CLEAN_BASELINE_FLAT_REPRODUCED` iff all hold:

1. the run reaches 64 completed gait cycles and returns to stand normally;
2. no clean target-feasibility rejection occurs during locomotion;
3. no strict constrained-WBC rejection is promoted to normal motion during locomotion;
4. no emergency/hard safety stop occurs;
5. measured forward speed is at least `0.11 m/s` and no more than `0.19 m/s`.

If the run does not pass, identify the earliest causal boundary from the immutable evidence before classifying.

## Classification

Use exactly one Luna primary classification:

- `CLEAN_BASELINE_FLAT_REPRODUCED`
- `CLEAN_BASELINE_TARGET_FEASIBILITY_FAIL`
- `CLEAN_BASELINE_WBC_STRICT_FAIL`
- `CLEAN_BASELINE_TRACKING_OR_STABILITY_FAIL`
- `PROTOCOL_FAILURE`

Luna's classification is a proposal, not the final scientific verdict; Sol may revise or overturn it from the evidence.

## Closeout

Write:

- `docs/validation/phase2_clean_baseline_flat_host_v4_20260917/RESULTS.md`
- `docs/validation/phase2_clean_baseline_flat_host_v4_20260917/analysis.json`
- `docs/validation/phase2_clean_baseline_flat_host_v4_20260917/provenance.csv`

Do not modify raw `_runs` evidence or the trusted host execution record after host execution. Do not run another live experiment from Luna.