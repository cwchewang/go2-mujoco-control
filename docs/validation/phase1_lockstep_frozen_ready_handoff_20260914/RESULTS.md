Phase1 frozen-state READY handoff, 2026-09-14

Base checkpoint: e7c7c88edd4e461c7b819397d5038b7d8786e9b6.
Decision: FROZEN_HANDOFF_STILL_NONDETERMINISTIC.

Stage 0 audit preceded behavior edits. The inherited deterministic 4000-step zero-control routine serializes the handoff state at tick 8000. The old BarrierComplete-only condition left a wall-clock mj_step path active, advancing the state to observed ticks 9090-9496 before the first gated publish. The old bridge had no immutable 8000 repetition or READY. The controller settled, captured joints/world reference, prepared the gate and clock, then started its writer without READY.

Stage 1 adds verification metadata only: the simulator freezes at 8000 and republishes it, accepts exact READY 8000, then requires the exact first LowCmd/ack pair before one step to 8002. READY alone cannot step and pre-READY LowCmd arrivals fail closed. The controller sends READY after capture and before the gated writer. Flag-off behavior is unchanged.

Frozen handoff evidence is in handoff_states.csv, protocol_gates.csv, and run_summary.csv. Handoff numeric equality uses the required <=1e-12 gate and binary equality is reported by SHA256.

|run|freeze|capture|READY|first gated|ack|first post|steps before exact|LowCmd before READY|frozen publishes|protocol|physical|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
|L1|8000|8000|8000|8000|8000,1|8002|0|0|992|PASS|PASS|
|L2|8000|8000|8000|8000|8000,1|8002|0|0|982|PASS|PASS|
|L3|8000|8000|8000|8000|8000,1|8002|0|0|976|PASS|PASS|

The physical gate is the inherited active-duration/status/continuous-trot/excess and negative WBC-SRBD-ID acceleration gate. Pairwise.csv uses the preregistered 10 ms active-relative grid, 10 ms join tolerance, and 10-consecutive-point divergence definition.
All protocol PASS=true; all physical PASS=true; excess-median range=0.011175902 m/s (<=0.010=false); no sustained divergence before 40 s=false.

Exactly L1, L2, and L3 ran sequentially with the varying-profile WBC-full running-trot baseline, D4 and other A/B flags OFF, fixed affinity, and DDS domains 231/232/230. No fourth run was launched.
The exact source HEAD, binary hashes, scene/profile hashes, protocol deltas, and raw artifact locations are recorded in run_metadata.txt and run_summary.csv. Source SHA256 values:
simulate/src/lockstep.h 5ed0d3206dadaf2cd5e0137570f4e8e8179a1c4943c1b4f15fda29003a90065a
simulate/src/main.cc 1801249d3e9b589875b053b4bbefb72b9450ca5dabbc263920c4c03c3d715742
simulate/src/unitree_sdk2_bridge.h 03166f41f72487f4eda178708aac06c50c6147f5cf2ee969bc2358b7b9424fbd
simulate/src/tests/test_lockstep.cpp 602990de6263f19c7db83cb1d86e3bc435bc945e038e4d877270a274b174a536
example/cpp/trot/trot_experiment.h 5a0ec8196a88f0ef56b11c68556e022c15de7a8c6729407eb5283d8bb126a3d3
example/cpp/trot/trot_experiment_lifecycle.cpp 59b60d67e421e8ddc7e424f71e4cd3ab77a99404268f6edb01a0d9f3cf12b02a
example/cpp/trot/trot_experiment_control.cpp 31fe8a91c78cd9bf3ebfc81ff25c2711747c6d03fab67ac5def9a614679df364
example/cpp/tests/test_lockstep_motion_clock_integration.cpp 54a443f2e32cb62069ed0d5af5aaf49fa68824049a159fe76b0b2eda7012d6e3
example/cpp/trot/lockstep_writer_gate.h f96c7ce9c088f56f5105c9718d3bc63e61fa77458733977eb4c219d61a8f9bab
example/cpp/trot/lockstep_motion_clock.h 704a352e39164d22fe74457f4cb9a6fb57f94e7222dfca6dd707ac135603add8
example/cpp/scripts/run_trot.sh f566b7285687e5ce4746778f0aaf6bf0ce0b7663cbe52963cc683f34be52ffc2
example/cpp/configs/phase1_velocity_varying.csv 9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74
unitree_robots/go2/scene_leg_lift_demo.xml 12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8

Checkpoint complete: Stage 0 audit, Stage 1 handshake, Stage 2 tests, and exactly three authorized Stage 3 launches are complete.
Recommended next step: resolve reproducibility in a separately authorized checkpoint; not executed here.
