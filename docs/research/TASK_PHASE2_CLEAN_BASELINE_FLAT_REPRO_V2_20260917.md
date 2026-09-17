# Phase2 clean baseline flat-ground reproduction v2

Mode: `confirmatory / execution-repair + one-live-canary`

Exact branch parent: `3ab920f916af5cb74fb0b2f9240a04a84005f09d`
Scientific baseline: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a` (`CLEAN_BASELINE_P0_READY`)
Prior protocol closeout: `3ab920f916af5cb74fb0b2f9240a04a84005f09d` (`PROTOCOL_FAILURE`, zero live attempts)
Branch: `research/phase2-clean-baseline-flat-repro-v2-20260917`

## Question

Can the unchanged clean baseline reproduce the established low-speed flat-ground Go2 trot once the three execution-only blockers from the prior protocol failure are repaired?

This is the same scientific question as the prior flat reproduction. The prior task launched no simulator/controller and consumed zero scientific attempts, so this task retains a budget of exactly one live canary.

## Frozen scientific/runtime semantics

No locomotion/control change is allowed before the live run. In particular, do not modify gait, planner, IK semantics, SRBD MPC, ID-WBC tasks/weights/constraints, gains, contact logic, scene/model, safety thresholds, or analysis thresholds.

Use exactly:

- `--clean-baseline`;
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
- default attitude feedback;
- torque limit `35 N m`;
- maximum `64` gait cycles;
- headless execution.

Do not enable `--cartesian-world`, known-step V1/V2, terrain actuation, sprint/high-speed overrides, impulse mode, direct-force overlays, or legacy comparison runs.

## Execution-only blockers to repair before live

The prior task found exactly three pre-live blockers:

1. Atlas trusted worktree is intentionally detached, while the old preflight required a symbolic branch name.
2. The runner-domain check could not infer the selected DDS domain from the runner source.
3. The exact checkout had no local MuJoCo headers/library, so it did not produce an exact-source `example/cpp/build/real_trot_go2`.

You may make the minimum execution-only changes needed to repair these blockers, provided they do not alter scientific/runtime controller semantics.

### A. Detached-worktree provenance

Do not weaken provenance. Teach the preflight/invocation to accept the trusted Atlas detached-worktree model by verifying the exact task SHA/ancestry plus the declared task branch identity, rather than requiring `git symbolic-ref` to succeed.

A detached checkout at the exact expected commit is acceptable; an unexpected SHA is not.

### B. Explicit DDS domain

Use a legal frozen manifest domain and make it explicit to both runner and preflight. Prefer baseline domain `220` if free immediately before launch. If it is not free, stop with `PROTOCOL_FAILURE`; do not select another domain after a failed live start.

The preflight must verify domain legality, lock availability, and absence of stale same-domain processes.

### C. Exact-source build with MuJoCo as a dependency only

Build `real_trot_go2` from the exact task worktree sources. It is allowed to consume the read-only MuJoCo SDK/header/library installation under `/home/che/dev/go2-workspace/current/simulate/mujoco` strictly as an external dependency/toolchain input, with its path and hashes recorded.

Do not substitute the reference tree's prebuilt `real_trot_go2` or other controller binary. The launched controller binary must be freshly built from this task worktree. If the simulator executable itself must come from the installed MuJoCo/Unitree runtime, record its provenance and ensure the exact task scene/model is used; never substitute controller code from another revision.

If exact-source build cannot be established cleanly, stop with `PROTOCOL_FAILURE`.

## Before live

1. Verify exact HEAD/ancestry and clean worktree.
2. Run focused clean-baseline, IK, dense-QP, SRBD-MPC, ID-WBC and CLI-route tests plus the practical portable suite.
3. Verify `--clean-baseline` remains incompatible with `--cartesian-world`.
4. Verify no scientific/runtime controller file differs from the scientific baseline except changes already present in the completed P0 result; execution-only build/preflight plumbing may differ and must be enumerated.
5. Build the exact-source controller binary against the allowed MuJoCo dependency.
6. Run fail-closed SOP preflight with explicit DDS domain `220` immediately before launch.

Any unresolved build/provenance/preflight failure => no live launch and `PROTOCOL_FAILURE`.

## Live budget

Exactly one clean-baseline flat-ground canary.

Fresh run directory:

`example/cpp/experiments/_runs/phase2_clean_baseline_flat_repro_v2_20260917/C`

No retry, replacement, tuning, comparison run, or terrain run once capture begins.

## Primary measurements

Report:

- stand -> gait -> return-to-stand completion;
- completed gait cycles;
- measured forward speed over `motion_stage==2` using the repository locomotion-progress analysis;
- commanded/nominal speed and tracking ratio;
- max/representative roll and pitch;
- any clean target-feasibility rejection;
- any strict ID-WBC constrained-solver rejection;
- any torque safety-envelope saturation;
- maximum joint target error / existing quality-gate values;
- any emergency/hard safety stop or abnormal contact failure.

## Passing criterion

Classify `CLEAN_BASELINE_FLAT_REPRODUCED` iff all hold:

1. 64 gait cycles complete and normal return to stand occurs;
2. no clean target-feasibility rejection during locomotion;
3. no strict WBC rejection is promoted to normal motion;
4. no emergency/hard safety stop;
5. measured forward speed is in `[0.11, 0.19] m/s`.

Otherwise identify the earliest causal boundary.

## Classification

Use exactly one:

- `CLEAN_BASELINE_FLAT_REPRODUCED`
- `CLEAN_BASELINE_TARGET_FEASIBILITY_FAIL`
- `CLEAN_BASELINE_WBC_STRICT_FAIL`
- `CLEAN_BASELINE_TRACKING_OR_STABILITY_FAIL`
- `PROTOCOL_FAILURE`

## Closeout

Write:

- `docs/validation/phase2_clean_baseline_flat_repro_v2_20260917/RESULTS.md`
- `docs/validation/phase2_clean_baseline_flat_repro_v2_20260917/analysis.json`
- `docs/validation/phase2_clean_baseline_flat_repro_v2_20260917/provenance.csv`

Preserve raw `_runs` evidence byte-for-byte after capture begins. Do not push from the agent; the trusted Atlas wrapper owns commit/push.