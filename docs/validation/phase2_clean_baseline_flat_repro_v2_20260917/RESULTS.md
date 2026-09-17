# Phase2 clean baseline flat-ground reproduction v2 closeout

Date: 2026-09-17
Task commit: `c04d68a9e463e7697b8ae8b9b0a4c2334041ee7a`
Exact branch parent: `3ab920f916af5cb74fb0b2f9240a04a84005f09d`
Scientific baseline: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`
Primary classification: `PROTOCOL_FAILURE`

No scientific canary attempt was consumed. The exact-source controller built
successfully and all preflight checks passed, but the simulator failed before
the controller could start. The first launch failed because the permitted
external simulator could not locate `libmujoco.so.3.3.6`. The single SOP-
allowed automatic recovery preserved those artifacts, supplied the permitted
MuJoCo library path, and used the same frozen domain `220`; MuJoCo then
started, but CycloneDDS failed while enumerating UDP interfaces and aborted
before DDS readiness and controller startup.

The recovery simulator produced only simulator-side
`contact_ground_truth.csv`; no controller `data.csv`, LowState/LowCmd
handoff, or post-handoff scientific sample was created. Therefore the live
budget consumed zero scientific attempts, and no gait cycles, speed, tracking,
stability, target-feasibility, WBC, torque, or safety interpretation is
valid.

Pre-live validation passed:

- exact detached HEAD, declared branch identity, and parent ancestry;
- exact-source `real_trot_go2` build against the read-only MuJoCo SDK;
- focused clean-baseline, IK, dense-QP, SRBD-MPC, ID-WBC, and CLI-route tests: 6/6;
- practical CTest suite: 32/32, excluding only `test_lockstep_motion_clock_integration`;
- clean-baseline rejection of `--cartesian-world`;
- fail-closed preflight immediately before each launch, including domain legality,
  lock/process checks, fresh recovery directory, hashes, and exact provenance.

Raw boot artifacts under
`example/cpp/experiments/_runs/phase2_clean_baseline_flat_repro_v2_20260917/C`
and its `recovery-1` subdirectory were preserved byte-for-byte after capture.
No domain change, tuning, comparison run, terrain run, or further retry was
made after the recovery failure.
