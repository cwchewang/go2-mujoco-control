# Phase2 clean baseline flat-ground reproduction closeout

Date: 2026-09-17
Task commit: `74acc1926cd4b59e9dd83b1ee35695cb45dc0bb2`
Exact parent: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`
Primary classification: `PROTOCOL_FAILURE`

No live canary was launched. The SOP preflight failed before launch, so no
scientific attempt was consumed and no raw `_runs` evidence was created or
modified.

Pre-live checks that passed:

- Exact parent ancestry and exact `HEAD` verification.
- CMake configure for the exact checkout.
- Focused clean-baseline, IK, dense-QP, SRBD-MPC, and CLI-route tests: 5/5.
- Available portable CTest set: 29/29 passed, excluding the lockstep
  integration test.
- Exact-source reference-backed Go2 rigid-body and inverse-dynamics WBC tests.
- Runner Bash syntax and locomotion analyzer Python syntax.
- The clean CLI incompatibility guard rejected `--clean-baseline` with
  `--cartesian-world`.

The aggregate local build could not produce `real_trot_go2` because this
checkout has no local MuJoCo headers/library. The read-only reference tree has
simulator/controller binaries from a different research revision; they were
not substituted for the exact task build.

The mandated fail-closed preflight reported these hard failures:

- the worker checkout is detached, so the required branch name was not
  verifiable;
- the runner-domain check could not infer a domain from the runner source;
- the exact checkout's `example/cpp/build/real_trot_go2` is missing.

Because the task requires `PROTOCOL_FAILURE` on build or preflight failure,
there is no locomotion classification or performance interpretation.
