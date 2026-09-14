# Phase2 checkpoint repair: known-geometry 5 cm step with validated pre-handoff wall-clock motion

Date: 2026-09-15
Prepared branch: `research/phase2-known-step-wallclock-repair-20260915`
Parent closeout: `9a3611e5e64150c45241cee92514d38ea6732857`
Previous failed checkpoint: `BASELINE_GATE_FAILED`; A only, B not run.

Read `docs/research/PHASE1_AGENT_CONTRACT.md` and `docs/research/TASK_PHASE2_KNOWN_GEOMETRY_5CM_STEP_20260915.md` first. This repair task overrides only the startup-clock/runtime-launch details listed below. All terrain geometry, adapter mathematics, A/B semantics, gates, thresholds, success criteria, and prohibitions from the original task remain frozen.

## 1. Why this is a new checkpoint

The previous A/domain 229 completed the lockstep transport protocol (4879 rows, 2 ms, zero protocol violations) and paired HighState validation (4879 cycles, zero validation failures, zero async fallbacks), but it triggered hard safety before any `motion_stage==2` active locomotion row. The known-step adapter was disabled and never active, so the terrain hypothesis was not tested.

Source audit identified a protocol mismatch relative to the accepted deterministic locomotion setup: the failed runner omitted `--wall-clock-motion`.

Production `MotionClockStep()` semantics are already covered by `test_lockstep_motion_clock_integration`: before the lockstep writer handoff, `wall_clock_motion=true` keeps the real LowCmdWrite path on wall-clock motion; after the handoff, the established lockstep motion clock takes over and advances exactly once per accepted simulator tick. This checkpoint repairs only that omitted startup condition.

Do not reinterpret the prior A as a terrain failure.

## 2. Frozen runtime change

Use only:

`example/cpp/scripts/run_phase2_known_step_5cm_wallclock_repair_ab.sh`

Relative to the failed checkpoint's runner, the only control/runtime semantic change is:

- add `--wall-clock-motion`.

Administrative isolation changes that do not alter controller physics:

- new run root: `_runs/phase2_known_step_5cm_wallclock_repair_20260915`;
- A DDS domain 231;
- B DDS domain 232.

Everything else remains exactly frozen from the original task:

- same `scene_known_step_5cm.xml` geometry: edge x=0.80 m, height=0.05 m, half-width=1.00 m;
- same `--cartesian-world --wbc-full --kernel raibert-trot`;
- period 0.60, duty 0.75, step length 0.091, base foot lift 0.028;
- Raibert gain 0.12, max adjustment 0.140;
- tau limit 35, preview horizon 4;
- no world-feedback / no attitude-feedback overlays;
- `FULL2_HOLD_CYCLES=999`;
- `SIM_LOCKSTEP=1`, `TROT_LOCKSTEP_PAIRED_HIGHSTATE=1`;
- D4, PD pulse, D90, reactive obstacle / auto-environment paths OFF;
- same known-step adapter formula and telemetry;
- same body-height, contact, WBC/SRBD/ID, gain, torque and speed policy.

No terrain/controller source change is authorized in this checkpoint unless a preflight compile failure is caused solely by branch bookkeeping. Do not tune or repair full2 behavior after a live launch.

## 3. Pre-live gates

Before any live process:

1. confirm branch descends from `9a3611e5e64150c45241cee92514d38ea6732857`;
2. worktree clean;
3. source diff audit proves no runtime source/scene/terrain-adapter math changed after the parent; only the new task/runner (and analysis-only closeout files later) are added;
4. run `test_lockstep_motion_clock_integration` and require PASS;
5. run `test_known_step_terrain_adapter` and require PASS;
6. run controller CTest and simulator `test_lockstep`; all required tests PASS;
7. verify new runner contains `--wall-clock-motion` exactly once and otherwise matches the prior runner's physics/control arguments;
8. verify old raw run directory is not deleted, overwritten, renamed, or reused.

Commit all pre-live bookkeeping before A and record that exact HEAD as the runtime HEAD.

## 4. Run budget and authorization

Exactly two live process launches are authorized, in order:

- A/domain 231: known-step traversal adaptation OFF;
- B/domain 232: adaptation ON.

Run A once. Analyze A with the existing prepared analyzer using:

- `--runs-root example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915`
- a new output directory `docs/validation/phase2_known_step_5cm_wallclock_repair_20260915`
- `--a-gate-only`
- `--expected-head <exact pre-live runtime HEAD>`.

B is authorized only if every original pre-step A gate passes. If A fails, classify `BASELINE_GATE_FAILED`, do not run B, close out and stop.

If A passes, run B exactly once, then run full analysis with the same analyzer, run root, output directory, and expected runtime HEAD.

No retry, replacement domain, extra seed, flat-floor probe, GUI replay, parameter sweep, speed sweep, threshold change, or additional live experiment is allowed.

## 5. Original evidence gates remain authoritative

If B is run, the following sections of `TASK_PHASE2_KNOWN_GEOMETRY_5CM_STEP_20260915.md` remain unchanged and authoritative:

- exact pre-activation comparability;
- B intervention isolation;
- traversal success definition;
- secondary metrics;
- top-level classification labels.

In particular, do not relax exact A/B equality before first B adaptation-active sample.

## 6. Additional repair audit

Closeout must additionally record:

- previous failed A runtime HEAD `89658121e002c9f95f47ee8d09ec83cd41f17845`;
- previous failure: no active locomotion rows, hard safety before step, B not run;
- proof that `--wall-clock-motion` is present in both new A/B argv;
- pre-handoff motion-clock telemetry sufficient to show the repaired run is wall-clock-driven before writer handoff and state-synchronous after handoff;
- lockstep and paired HighState summaries;
- exact runtime HEAD and clean worktree status;
- launch count and domains;
- simulator/controller/scene hashes.

Do not claim the wall-clock omission was causally proven to be the previous failure mechanism merely because the repaired A passes; phrase it as the isolated protocol repair that restored or failed to restore a healthy baseline.

## 7. Stop conditions

After final closeout push, stop. Do not run 10 cm, height-map perception, D4, a speed increase, or any other terrain checkpoint.