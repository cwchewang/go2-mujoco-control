# Phase1 D4 deterministic live A/B closeout

Top-level classification: `SUPPORTED`.

## Preregistration and scope

- Task branch: `research/phase1-bounded-stance-dq-d4-deterministic-ab-20260914`.
- Accepted base evidence: `6970d3c9406a4297cb67a4a397e8b84335732d25`.
- Pre-run HEAD and runtime HEAD: `c5fb8c0271e3caaf77b6debcaae4610d39e05814`.
- Prerequisite: `FIX_VALIDATED_FULL_BASELINE_REPRODUCIBLE`.
- Exactly one actual runtime capture was completed for A and one for B. A used DDS domain 221; B used 222. B was launched only after the prepared A gate returned `A_GATE_PASS`. No retry, replacement ID, extra replicate, tuning, D4-math change, or follow-on experiment was performed.
- The initial runner preflight found the newly created worktree lacked the simulator binary and exited before starting either process. The simulator was then built using the repository's documented build, and the runner-created empty A directory was removed after verifying it contained no artifacts. The subsequent A and B process launches each completed once; no raw capture was overwritten.

## Source audit and pre-run tests

The base-to-HEAD tracked delta contains only the named task, runner, and analyzer. The inherited D4 implementation was audited in `example/cpp/trot/trot_experiment_control.cpp` and `trot_experiment_lifecycle.cpp`: A leaves `TROT_BOUNDED_STANCE_DQ_D4_AB` unset; B alone enables it; the gate is active-relative [32.10,39.90), requires controller/WBC stance and valid paired state, solves the existing stationary-support Jacobian target, falls back on invalid solves, and applies the inherited whole-leg scalar with the preregistered 2 rad/s and 4 Nm caps. No q/kp/kd/tau_ff, WBC/SRBD/ID, gait, velocity profile, solver, model, scene, safety limit, or HighState pairing code was changed.

Pre-run validation passed:

- `cmake -S simulate -B simulate/build && cmake --build simulate/build -j$(nproc)`: simulator built.
- `cmake -S example/cpp -B example/cpp/build && cmake --build example/cpp/build -j$(nproc)`: controller and analysis/test targets built.
- `./simulate/build/test_lockstep`: all tests passed, including its intentional fail-closed counterexamples.
- `ctest --test-dir example/cpp/build --output-on-failure`: 30/30 passed, including writer-gate, motion-clock, HighState-pairing, integration, WBC, and dynamics tests.

## Runtime protocol and A gate

Both runs used `SIM_LOCKSTEP=1`, `TROT_LOCKSTEP_PAIRED_HIGHSTATE=1`, `TROT_DIAG_ID_CLOSURE=1`, and `TROT_BRIDGE_ATOMIC_RECORD=1`. Each trace has 43,554 rows at 2 ms, all protocol gates pass, and the consumed-HighState summary is 43,554 cycles with zero validation failures and zero async fallbacks. All seven status codes are zero for both runs.

The prepared analyzer command was run with `--a-gate-only` after A. A passed: active-relative max 82.804 s; motion stage 2 throughout [32,40); median measured-minus-applied in [32,33) was +0.250740602 m/s; median WBC/SRBD/ID longitudinal values were respectively -2.507406018, -1.507218024, and -2.3285093135; no hard-safety marker.

## A/B result

`prewindow_exact.csv` reports exact equality for row count/timestamps and every preregistered causal field in [31.90,32.10): clocks, motion/velocity fields, body/world velocity, IMU, WBC/SRBD/ID quantities, contacts, and all 12 motors' q/dq targets, gains, feedforward, and q/dq state.

`isolation.csv` passes: 22,380 changed joint events, maximum |delta dq|=1.474688416 rad/s, maximum |kd*delta dq|=4.0 Nm, zero invalid solves and zero fallbacks. Changes were confined to the active gate and selected stance legs; A had no correction.

The primary statistic is:

```text
DID_excess=(B_full-B_pre)-(A_full-A_pre)=-0.242994545 m/s
```

A/B settling times are 29.81 s and 1.19 s from the 1.4-to-2.3 m/s transition; B is not worse. B has no hard-safety or status failure. Therefore all gates pass, B is safe, DID is below the preregistered -0.02 m/s threshold, and the result is `SUPPORTED`.

## Provenance and deliverables

Raw captures remain local and immutable under `example/cpp/experiments/_runs/phase1_d4_deterministic_ab_20260914/{A,B}`. `provenance.csv` records SHA-256 for every required raw artifact. Both runs use simulator SHA-256 `23a38f92cc0c0ec0dcfe3ce6cb217262ebd9bd9ba1baaf7825b548923ad46db7`, controller SHA-256 `a12c9e8690a7469b14ffdd24df9a425431a5dd8a17d858f0fe05cd5ee43e4dc4`, and scene SHA-256 `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`. B's run metadata marks the worktree dirty only because the required A-gate derived directory existed before B; source HEAD and binary hashes are identical, and no tracked source changed.

Required machine-readable outputs are present: `ab.csv`, `prewindow_exact.csv`, `isolation.csv`, `protocol_gates.csv`, and `provenance.csv`; `a_gate.csv` and `analysis.json` preserve the staged gate and final decision. The prepared full analyzer command was:

```text
python3 example/cpp/tools/analysis/analyze_phase1_d4_deterministic_ab.py \
  --runs-root example/cpp/experiments/_runs/phase1_d4_deterministic_ab_20260914 \
  --output-dir docs/validation/phase1_d4_deterministic_ab_20260914
```

Closeout is complete on this branch. No repair or later experiment was executed.
