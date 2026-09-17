# Phase 2 clean-baseline flat final closeout

Task: `docs/research/TASK_PHASE2_CLEAN_BASELINE_FLAT_FINAL_20260917.md`

Task commit: `42832a74b4115d8debc05fd42cec762989d5337b`

Exact parent: `2eb92bc62be6fba2dee26ac9229520d8835c6246`

Candidate presented to the trusted host: `0009b5fbd1e962e38135922da61245a99b522aab`

Trusted host record: `docs/research/evidence/atlas_host/42832a74b4115d8debc05fd42cec762989d5337b.json`

Raw run: `example/cpp/experiments/_runs/phase2_clean_baseline_flat_final_20260917/C`

## FACTS

- The trusted record reports `launched=true`, return code `0`, no host error,
  no timeout, DDS domain `220`, and elapsed host time `115.275903 s`. The
  frozen manifest SHA256 is
  `917e2b409a8d62239b6d88d61f103609c287136b98f86bb4214c2f54db053797`.
- The host record indexes 18 raw artifacts. Their recorded sizes and SHA256
  values were independently rechecked; every indexed artifact matched. The
  complete raw hash list is:

  ```text
  build_provenance.txt                                      1aa6218b602c0f5089e43d2e68dd02d06fd7f0b69ae6ed340f7a438dbfdf6f2e
  contact_ground_truth.csv                                  4d9ee3d2e8a2119afef0ae3358125e9f96c751e1c1913f73ede653b80cccebb7
  contact_ground_truth_analysis.txt                         a855696398d5b97504078fcd782b195d1709a02705af42c3b3d44d8744a6669a
  contact_ground_truth_dynamics_analysis.txt                8a79c9d6883bb29c3bb0e1d7e21dfad9819fbdfe938a71c1189f741caab3943b
  controller.log                                            6d28e2e3698c68c890c4b52a9826517fc2e4f29f8c0e36cf17a4d85dbac78ce2
  controller_build.log                                      01f4342cdae3c640ea21b3ef9b3283b25199f16bc2799a66689ab808137e1e17
  data.csv                                                  cfd4a5cf838cf491575156eb7b209bf726571a02c11748dde72382e914c97de9
  dds_runtime/dds_base4000_preload.so                      0631e8aa1b9826215ef268665049d154571d3ca332eeff478b8fa9d17691293f
  dds_runtime/post_clean_state.txt                         2e09a1b487e54cb1c208cc768a88202d41a85b944fffa48954c098332ee920ea
  dds_runtime/post_state.txt                               920d180c71faea79f70407a58fb89357cdc9ecc7b8334eddb61a56c6d7428340
  dds_runtime/pre_state.txt                                c5320d65590db871a86e1ce7af6ebe5782bd36714fd0f5ebedc7772df7f34b1a
  dds_runtime/preparation_cleanup.txt                      633a86080623548a9d9153a5e8c044ce1fb1d3ee2e63458333957fcd3ff8a8df
  dds_runtime/runtime_metadata.txt                         e43003d65b0c57a3244d6a16d4f9d8118cb485f381d15e85db78a78e99000e35
  environment.txt                                           fcdd684a211809d5382bb92eba651a1e7d3e75b7672a6674616e469c32d53981
  run_manifest.json                                         61141434be7e5398d1d3c8aec6dfd118f1a9c37c3e3e254a153e35312e0a8d0d
  run_metadata.txt                                          169300e8c14cfe67ca8caa3b97153a632e9004e09fe20e3390f2460606fcd4ac
  simulator.log                                            67038352310a338b1f6cceeb2583fa20877a613b15cdd39537692f772892ddec
  simulator_build.log                                      636d31b21716caf40689697a3297e93a2ff0b8a2fc3ed4e2ff798c7a9235a7b1
  ```

- The exact frozen command was launched once by the trusted wrapper:

  ```bash
  bash example/cpp/scripts/run_trot_exact_source.sh 90 _runs/phase2_clean_baseline_flat_final_20260917/C \
    --controller-duration 70 --task stand-walk-lie --kernel raibert-trot \
    --period 0.60 --duty 0.75 --step-length 0.091 --foot-lift 0.020 \
    --kp 63 --kd 2.8 --raibert-velocity-gain 0.05 \
    --raibert-max-adjustment 0.010 --world-feedback-max 0.060 \
    --world-feedback-slew 0.004 --clean-baseline --tau-limit 35 \
    --max-cycles 64 --headless --domain-id 220
  ```

- The host build provenance records candidate tree
  `fc89cdb3f110f3846466090e60249f69f731afca`, a clean tracked worktree,
  simulator SHA256
  `8c4ef43acc65938c231a73da6a9dbe7c6b1170d72733f757927316a15d130c1a`, and
  controller SHA256
  `ad4aed86d2562a77c7a1aaf46690f3aedccb22938e7659015ff7ce7e75cb83c5`.
  The frozen scene SHA256 is
  `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.
- DDS support was the recorded `dds_base4000_preload.c` source, SHA256
  `65100130add060af08f6404b03668f5018c9b039849bf62620cd99f362d38a3c`, with
  generated preload SHA256
  `0631e8aa1b9826215ef268665049d154571d3ca332eeff478b8fa9d17691293f`.
  The runtime metadata records CycloneDDS `0.10.2`, loopback interface, port
  base `4000`, domain `220`, and maximum automatic participant index `31`.
- `simulator.log` contains the DDS-ready marker and shutdown marker.
  `controller.log` contains the 18-DoF model load, settled `LowState`, and
  start-of-trot markers. The first CSV data row has `has_state=1`,
  `motion_stage=0`, `cycle_index=-1`, `cmd_time_s=0`, and
  `state_tick_s=1.746`; therefore the scientific attempt was consumed.
- The raw lifecycle records include the pre-motion health record at cycle 0,
  requested cycles 1 through 64, cycle 65 as the pre-stop brake/return
  transition, `LOCOMOTION -> RETURN_TO_STAND`, `RETURN_TO_STAND -> LIE_DOWN`,
  and `Task completed: stand-walk-lie`. There are no raw log markers for a
  target-feasibility rejection, strict WBC/QP rejection, hard safety stop, or
  emergency stop.
- The data CSV has 25,059 rows and all rows have `has_state=1`. Its motion
  stage counts are `0:1500`, `1:650`, `2:19606`, `3:1402`, `4:1499`, and
  `5:402`. The requested 64-cycle data interval is present. All recorded
  controller/status fields in `run_metadata.txt` are zero-status, and the
  pre/post DDS snapshots report empty Go2 process and known-shm inventories.
- The host-produced contact ground-truth and dynamics validation artifacts
  both report `PASS`; their raw validation inputs and outputs are included in
  the indexed hash list above. No raw run file or trusted host record was
  modified during this closeout.

## DERIVED METRICS

The deterministic analysis is implemented in
`example/cpp/tools/analysis/analyze_clean_baseline_flat_final.py`. It reads
only the trusted host record and indexed raw files. Its output is
`analysis.json`; the full input/tool/source hash ledger is
`provenance.csv`.

- Nominal speed is `0.091 / 0.60 = 0.15166666666666667 m/s`.
- Primary locomotion interval: CSV rows satisfying
  `motion_stage == 2 and cycle_index >= 0`. There are 19,606 samples over
  `39.260 s`, with `6.002663668 m` endpoint displacement. Ordinary least
  squares of `world_base_x_m` against `state_tick_s` gives
  `0.15380595762132146 m/s`; endpoint speed is
  `0.15289515201222617 m/s`, a nominal ratio of `1.014105215085636`.
- Requested-cycle diagnostic interval: CSV rows satisfying
  `motion_stage == 2 and 1 <= cycle_index <= 64`. There are 19,204 samples
  over `38.442 s`; OLS speed is `0.15381904325269138 m/s`, endpoint speed is
  `0.15383399518755528 m/s`, and the ratio to nominal is
  `1.0141914939737893`.
- The requested-cycle measured-velocity field has count `19,204`, minimum
  `0.124527540`, p05 `0.143945393`, median `0.152893408`, mean
  `0.15376908687294313`, p95 `0.16575295425`, and maximum `0.181423873 m/s`.
  Ground-truth world-x base velocity over the controller stage-2 interval has
  median `0.153515967849`, p05 `0.127449622366`, p95 `0.171652885194`, and
  mean `0.15289089317209495 m/s`.
- Lifecycle counting gives `64/64` requested cycles complete. The controller
  health records for cycles 1 through 64 have maximum absolute roll
  `0.966123 deg`, pitch `1.20646 deg`, support drift `5.24979 mm`, joint error
  `0.075396 rad`, foot error `0.0351327 m`, and estimated torque `15.2658 Nm`.
  Minimum support is two contacts and support fraction is `1.0`; low-support
  samples and touchdown x/y errors above the recorded guards are zero.
- Requested-cycle CSV flags are success-valued for every one of the 19,204
  rows: `has_state`, footstep-plan-valid, full SRBD WBC, full ID WBC, shadow
  solver/mapping/task/wrench/constraint checks are all `1`. Terrain is disabled
  throughout, with zero terrain failure/rejection flags. Exact rejection and
  safety-marker counts are zero for clean target infeasible, strict WBC/QP,
  cycle-quality guard, hard safety, and emergency-stop markers. Torque-over-
  limit samples and consecutive counts are also zero.
- Contact validation covers 26,004 rows, 84,624 contact samples, no negative
  vertical contact GRF samples, and maximum vertical GRF `429.144246 N`.
  Dynamics validation covers 26,003 balance samples with p95 residual
  `0.505693963 N`, maximum residual norm `5.87906345 N`, and the recorded
  `10 N` tolerance.

The formulas and all source/raw/tool hashes are machine-readable in
`analysis.json` and `provenance.csv`; Sol can reproduce these values without
launching another experiment.

## LUNA INTERPRETATION

The proposed Luna classification is
`CLEAN_BASELINE_FLAT_REPRODUCED`. This is an interpretation, not an
authoritative result. It is based on all seven frozen gates: valid handoff,
64 completed cycles, normal task completion without a hard/emergency stop, no
clean target-feasibility rejection, no strict WBC/QP rejection, forward speed
inside `[0.11, 0.19] m/s`, and no gross tracking/stability failure.

The earliest supported boundary is scientific capture: the host established
DDS readiness and controller handoff, then produced a complete bounded
flat-ground canary. The prior infrastructure status and the parent
`DDS_RUNTIME_ROOT_FIXED` evidence are retained as provenance, not reclassified
as locomotion evidence. The single scientific attempt is consumed; no retry,
comparison run, or live follow-up is authorized by this closeout.

Sol should independently recompute `analysis.json` from the indexed raw files
and may overturn this proposed classification. The trusted host record and raw
evidence remain the authority for host facts; this document records Luna's
reviewable interpretation only.
