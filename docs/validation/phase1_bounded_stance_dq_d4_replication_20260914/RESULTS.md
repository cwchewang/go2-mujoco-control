# Phase1 bounded stance-dq D4 live replication — 2026-09-14

## Outcome

Result: **INCONCLUSIVE**. The replication stopped after the first authorized launch because A failed the required baseline gate. B was not launched, as required by the task.

This task authorized exactly two launches, A then B, with no retry or third launch. A used the unchanged prior D4-live implementation with `TROT_BOUNDED_STANCE_DQ_D4_AB=0`. It reached only active-relative `29.020011491 s`, stopped on a hard posture limit at approximately `-179.88 deg` roll, and never reached the required `[32,33)` 2.3 m/s gate window. Therefore there is no valid A/B causal comparison and no DID endpoint.

## Contract and fixed implementation

`PHASE1_AGENT_CONTRACT.md` and this replication task were read completely before action. The worktree is native WSL and the source is the existing D4 implementation from prior checkpoint `e65c8830905c2c744c85d82ec08c3e4b7f6989c4`, with only the replication task document added on top. No controller behavior, thresholds, gains, gait parameters, model, scene, profile, logging semantics, or acceptance behavior was changed.

The fixed intervention remains the cached default-off `TROT_BOUNDED_STANCE_DQ_D4_AB` flag. The previous D4 implementation applies the full 3×3 repository Jacobian SVD correction only to controller/WBC stance-leg dq during active-relative `[32.10,39.90)`, using `delta=dq_ss-dq_base`, `s=min(1,2/max|delta|,4/max|kd*delta|)`, and baseline fallback for invalid solves. It was not exercised in this replication because B was forbidden after the A failure.

## Provenance and exact run command

Target branch: `research/phase1-bounded-stance-dq-d4-replication-20260914`.

Run source commit: `30074fccb53fc6d274bb4a08ed780efc1247aa14` (`research: preregister D4 live replication`), clean tree. The controller implementation is inherited unchanged from `e65c8830905c2c744c85d82ec08c3e4b7f6989c4`.

Only launched run: A `varying_20260914_105519`.

```text
TROT_CPU_AUTOPIN=1 TROT_DIAG_ID_CLOSURE=1 TROT_BOUNDED_STANCE_DQ_D4_AB=0 GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv bash example/cpp/scripts/run_phase1_velocity_benchmark.sh varying _runs/phase1_bounded_stance_dq_d4_replication_20260914/A 232
```

No explicit seed was used. B was not launched.

Controller SHA256: `508e782f32ade286b03dd381fcffc238586109cc0450c85179490e4ca3a0835b`.

Simulator SHA256: `23a5f6d7f5938acc69421c8d913bb29c1e01982ced9214c5e36745eaaafa3534`.

Scene SHA256: `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.

Profile SHA256: `9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74`.

Implementation source file SHA256:

```text
example/cpp/trot/trot_experiment.h                 288ae92b7e3b51c96ffb3c1801125f902c48b17aed7c8df21074aed6597ee275
example/cpp/trot/trot_experiment_control.cpp        d3ccdd95e4f4629b8f25322fc6f120bbe5d0aa3e57d5a93a03cb6eacaf103397
example/cpp/trot/trot_experiment_diagnostics.cpp    4e91581455c3bf9ca18c49acb3dbd233dc684dc006144210ff5729dddee764b1
example/cpp/trot/trot_experiment_lifecycle.cpp      02f0f1600f9895280225b4edfab827870dcc2612372b3bb6bfbfa327204a08cb
```

## A baseline gate

The wrapper metadata records `controller_status=0`, `quality_status=0`, `analysis_status=0`, `ground_truth_status=0`, and `dynamics_status=0`, but `safety_status=1` and `completion_status=1`. The strict velocity analyzer returned `strict_pass=false`.

A produced `18,062` total rows and `15,912` continuous-trot active rows. The active prefix ended at `29.020011491 s`; it did not reach active-relative `[32,33)`, so the required gate row count and medians are unavailable. For reference, the last observed active prefix `[24,29.020011491)` had `3,912` rows, median measured `1.672011400 m/s`, median applied `1.839987620 m/s`, and did not represent the required 2.3 m/s endpoint.

The A controller log repeatedly records `Trot hard posture limit: roll=-179.88... deg` followed by `Trot hard safety limit reached; stopping`. The maximum recorded absolute roll was `179.9992810188 deg`, maximum absolute pitch `76.7852735218 deg`, and the analyzer reported a minimum base height of `0.057491793 m`. The simulator log contains normal startup and shutdown, while ground-truth and dynamics validation both report `validation=PASS`. This is an observed physical baseline failure, not a logging or simulator-infrastructure failure.

## Why B was not launched

The A gate requires active-relative `≥40 s` without hard safety stop, continuous trot, and the `[32,33)` residual-overspeed/braking-demand measurements: median measured-applied in `[+0.15,+0.35] m/s`, plus negative WBC desired ax, SRBD ax, and ID qdd-x medians. A stopped at `29.020011491 s` with `safety_status=1` before the gate window. The task explicitly says to stop rather than improvise when A fails; consequently B, isolation checks, pre-window comparability, DID, tracking support, and stability trade-off comparison are all unavailable.

## Raw evidence hashes

Only A was launched: `varying_20260914_105519`.

```text
data.csv                    040bf63af3c7464541e0551ef90a19ab902110fb0fec2b982cb94e27ef101292
data.csv.id_closure.csv     2628ea3ea003472e1fa3ea02ac01eef83d051c01e0729abac3ac6cb65180cf14
controller.log              305330ac10cdca12abae36d1ec7427f0098958fb154bfed9af8d5908921711cb
simulator.log               7e65773f85cbd85325f9bc285deaacc58ada03b8e1fb522381ff933bb954f603
run_metadata.txt            7cb4ef6332920f945293ef278a046bf12425602a9cbc151e3162d795bfea8b74
run_manifest.json           384b1faaaf806000a688777adab276859ae0dd8d2047a723f6cef2d14b907c80
environment.txt             28633acc2968fd589e005dea595d297b2b0a54243c7620aff27c67fe1ccf62f9
contact_ground_truth.csv    a5f43e59b1d135c0d7d95c9eb3a9e910b0d497da3c99577163595111d5ae6c88
```

## Recommendation

Retain this `INCONCLUSIVE` replication checkpoint and stop. Do not rerun A, launch B, or alter the D4 intervention without explicit authorization for a new task.
