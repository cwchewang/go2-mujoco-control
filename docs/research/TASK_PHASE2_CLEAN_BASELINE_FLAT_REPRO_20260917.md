# Phase2 clean baseline flat-ground reproduction

Mode: `confirmatory / one-live-canary`

Exact parent: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`
Parent classification: `CLEAN_BASELINE_P0_READY`
Branch: `research/phase2-clean-baseline-flat-repro-20260917`

## Question

After removing hidden target rewriting, permissive constrained-solver acceptance, post-QP torque overlays, and the missing swing `Jdot*qdot` term, can the opt-in clean baseline still reproduce the established low-speed flat-ground Go2 trot?

This is a baseline-viability test, not a terrain or performance-development task.

## Frozen control semantics

Use the clean path from the exact parent with no runtime/control changes:

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
- headless execution.

Do not enable `--cartesian-world`, known-step V1/V2, terrain actuation, sprint/high-speed campaign overrides, impulse mode, direct-force overlays, or other experimental interventions.

The historical indexed low-speed reference is the same nominal `0.091/0.60 = 0.151667 m/s` configuration, with later n=5 `--wbc-full` repeats reported around `0.116–0.147 m/s`. This reference is contextual only; no new legacy A run is authorized.

## Before live

1. Verify branch ancestry and exact parent.
2. Run the focused clean-baseline/IK/dense-QP/ID-WBC/SRBD tests and the practical portable test set.
3. Verify the clean CLI rejects `--cartesian-world` coexistence.
4. Verify no scientific/runtime file differs from the exact parent before the run except execution-only run/analysis plumbing if strictly necessary.
5. Run the SOP preflight immediately before launch using a free legal DDS domain.

If build, tests, provenance, or preflight fail, do not launch. Classify `PROTOCOL_FAILURE`.

## Live budget

Exactly one clean-baseline flat-ground canary is authorized.

Fresh run directory:

`example/cpp/experiments/_runs/phase2_clean_baseline_flat_repro_20260917/C`

No retry, replacement run, parameter tuning, legacy comparison run, or terrain run after capture begins.

## Primary measurements

Analyze only the single canary.

Report:

- whether the normal stand -> gait -> return-to-stand sequence completes;
- completed gait cycles;
- measured forward speed using the repository's established locomotion-progress analysis over `motion_stage==2`;
- commanded/nominal speed reported by the controller and tracking ratio;
- max/representative roll and pitch;
- whether any clean target-feasibility rejection occurs;
- whether any strict ID-WBC constrained-solver rejection occurs;
- whether any torque safety envelope saturation occurs;
- maximum joint target error / relevant existing quality-gate values;
- any emergency stop, hard safety stop, or abnormal contact failure.

## Passing criterion

Classify `CLEAN_BASELINE_FLAT_REPRODUCED` iff all of the following hold:

1. the run reaches 64 completed gait cycles and returns to stand normally;
2. no clean target-feasibility rejection occurs during locomotion;
3. no strict constrained-WBC rejection is promoted to normal motion during locomotion;
4. no emergency/hard safety stop occurs;
5. measured forward speed is at least `0.11 m/s` and no more than `0.19 m/s` (a deliberately broad one-run reproduction window around the established low-speed baseline, not a new performance claim).

If the run does not pass, identify the earliest causal boundary from the available logs before classifying.

## Classification

Use exactly one primary classification:

- `CLEAN_BASELINE_FLAT_REPRODUCED` — pass criteria above are satisfied;
- `CLEAN_BASELINE_TARGET_FEASIBILITY_FAIL` — clean target-to-IK/joint-range gate is the earliest blocker;
- `CLEAN_BASELINE_WBC_STRICT_FAIL` — strict constrained WBC acceptance is the earliest blocker;
- `CLEAN_BASELINE_TRACKING_OR_STABILITY_FAIL` — targets and WBC remain valid but actual tracking/contact/posture prevents reproduction;
- `PROTOCOL_FAILURE` — build/provenance/preflight/evidence failure prevents interpretation.

Do not modify control logic based on the canary result in this task. A failure becomes the next scientific question.

## Closeout

Write only:

- `docs/validation/phase2_clean_baseline_flat_repro_20260917/RESULTS.md`
- `docs/validation/phase2_clean_baseline_flat_repro_20260917/analysis.json`
- `docs/validation/phase2_clean_baseline_flat_repro_20260917/provenance.csv`

Preserve raw `_runs` evidence byte-for-byte after capture begins. Do not push from the agent; leave tracked edits for the trusted Atlas wrapper.