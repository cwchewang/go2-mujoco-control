# Canonical clean-baseline repeatability — R3 closeout

Task: `docs/research/TASK_CANONICAL_CLEAN_BASELINE_REPEAT_R3_20260917.md`

Task/candidate commit: `ba4d7ff8a865bd31f826e972b48105876ffa0640`

Canonical protected-main baseline: `e30782ad916ef1614a877d7a3c122f62682c8f19`

Accepted predecessor flat result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`

Trusted host record: `docs/research/evidence/atlas_host/ba4d7ff8a865bd31f826e972b48105876ffa0640.json`

Raw run: `example/cpp/experiments/_runs/canonical_clean_baseline_repeatability_20260917/R3`

The trusted host record and indexed raw files are authoritative. The
classification below is Luna's reproducible interpretation only.

## FACTS

- The trusted host reports `launched=true`, return code `0`, no host error,
  `timed_out=false`, and host elapsed time `114.872562 s`. Its manifest SHA256
  is `94b6c3d9b21179ea7791f31bdeb043f6f541a5c1b147824378e4e1355199eef2`.
  The host command exactly matches the frozen task manifest: one bounded,
  headless `stand-walk-lie` / `raibert-trot` run at DDS domain `220`, with
  period `0.60`, duty `0.75`, step `0.091`, lift `0.020`, `kp=63`, `kd=2.8`,
  Raibert gain/max adjustment `0.05`/`0.010`, world feedback max/slew
  `0.060`/`0.004`, `--clean-baseline`, torque limit `35`, and `64` cycles.
- The candidate presented to the host is the exact task commit above. The host
  build provenance records candidate tree
  `8e5b649885c4af38062a8d9e9dd5a04fdb886847` and a clean tracked worktree.
  The pre-host source audit found `example/cpp/`, `simulate/`, and
  `unitree_robots/` unchanged from canonical main. The only post-host code
  addition is the analysis-only helper
  `example/cpp/tools/analysis/analyze_canonical_clean_baseline_repeat_r3.py`;
  runtime/controller/scene/test/launch files were not modified.
- Host build identities are: simulator
  `47c3ddfb996ded32fbb70e86bac0863df0888f6046339c5b446c2a0f159a4bf3`,
  controller
  `f1d2f26d1f9a5fcaad94d3874252697a1caf77638cf325ef67aa7d2167684140`, and
  scene `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.
  The recorded MuJoCo library/header hashes are
  `b9173509d0c282a9b24b7f5825a40177a9967df0cd6395a9dc39522196e44495` and
  `3190fd17711cf25b6b7605802df353571e4329ca3849485e56643e49925208cd`.
- DDS runtime facts are domain `220`, loopback interface, CycloneDDS `0.10.2`,
  port base `4000`, participant index maximum `31`, and support preload hash
  `0631e8aa1b9826215ef268665049d154571d3ca332eeff478b8fa9d17691293f`.
  Pre/post snapshots contain no active Go2 processes or known shared-memory
  objects. The simulator log contains the DDS-ready and shutdown markers; the
  controller log contains natural LowState settle, 18-DoF MJCF load, and
  normal `stand-walk-lie` completion.
- The raw `data.csv` contains 25,073 rows and 278 columns; every row has
  `has_state=1`. Run metadata status fields are all zero. The stage counts are
  `0:1503`, `1:650`, `2:19618`, `3:1401`, `4:1499`, and `5:402`.
- The indexed raw evidence has 18 files. Every recorded size and SHA256
  matches the trusted host record, with no extra raw files. The complete raw
  hash ledger is in `analysis.json` and `provenance.csv`; key hashes include:

  ```text
  build_provenance.txt                                      975051f98041047784585a31a021f2c005916994a4b6c8e023f544bd6c7555b9
  contact_ground_truth.csv                                  9e17228a6e2e05d10bc5b07f6eec4677122dc3df9cf7d99e1d2933d2b96084be
  contact_ground_truth_analysis.txt                         85dcd28cbc3fb804db237f5dcb7f29146852a6acc77d91eb7f596042eb110725
  contact_ground_truth_dynamics_analysis.txt                12c6a8b7b3b1385855a22f8a9d7f2dfe564b5689e1e47d034f532659de20547d
  controller.log                                            ef12be1a11e4e888ea8c873f231512bfa970616377895e75c1a06c703c8bbe00
  controller_build.log                                      b9bf9e7492b215b8d25fd71cda2597ed4e2b55eedff3419594db18a6383aadb3
  data.csv                                                  9111969c2899ceee43ececc7779750969bddd25a01e07c59f93a914cf99abcdc
  dds_runtime/dds_base4000_preload.so                      0631e8aa1b9826215ef268665049d154571d3ca332eeff478b8fa9d17691293f
  dds_runtime/post_clean_state.txt                         94810cf1f47ef07179c4d0478b8fb0ff24c39da0fd0952d20a5934ce8930bacd
  dds_runtime/post_state.txt                               5f2098a21d9e647608b1729465441782b511173c1acb61a940b4669ca8021058
  dds_runtime/pre_state.txt                                a5e4f4452df9f6944b378c82120893f33e6e92cd9ee81bb8b84cf90c0f31c4f3
  dds_runtime/preparation_cleanup.txt                      cb71b8509c4ef4bd9a686357153298b346b8d34ab2278fd6ea412556073a6ebf
  dds_runtime/runtime_metadata.txt                         c4fc7b71dcd06d7988ea21c57414074112f2a1b002540d215515824774c56040
  environment.txt                                           fcdd684a211809d5382bb92eba651a1e7d3e75b7672a6674616e469c32d53981
  run_manifest.json                                         ae0614df705b7a53fa0d3a0805929d0cb88587ef79f6416dc269d8fda13239ec
  run_metadata.txt                                          655b5f7afb01ad303c4a98bbac77dc388ef83cfd32c455c2678cbe697b93d845
  simulator.log                                            ef7a7030cc7d5dbfc540b8f3ff5e1c986c003c6e37512e75ec5645a158b22c02
  simulator_build.log                                      c51dd8f2d129a79b47ab3203bae5d54996ff48b55044dbb7311c34f1f312cd57
  ```

## DERIVED METRICS

The deterministic calculation is implemented in
`example/cpp/tools/analysis/analyze_canonical_clean_baseline_repeat_r3.py`.
It reads only the trusted record and indexed raw files. The machine-readable
output is `analysis.json`; the input/source/hash ledger is `provenance.csv`.

- Handoff: the first valid state/control row is CSV row `2`, with
  `cmd_time_s=0`, `state_tick_s=1.688`, `has_state=1`, stage `0`, and cycle
  `-1`. The first locomotion row is CSV row `2155`, at `cmd_time_s=4.3`,
  `state_tick_s=6.022`, stage `2`, cycle `0`. The scientific attempt was
  consumed.
- Lifecycle: controller health and start records cover requested cycles `1`
  through `64`; cycle `65` is the return transition. The task completed through
  `RETURN_TO_STAND -> LIE_DOWN` without hard-safety or emergency markers.
- Nominal speed is `0.091 / 0.60 = 0.15166666666666667 m/s`. For the primary
  window `motion_stage == 2 and cycle_index >= 0`, there are 19,618 samples
  over `39.286 s`, with endpoint displacement `6.014039582 m`. OLS of
  `world_base_x_m` against `state_tick_s` is
  `0.15387870609711238 m/s`; endpoint speed is `0.15308353057068677 m/s`,
  ratio `1.0145848753655762`.
- For the requested-cycle diagnostic window
  `motion_stage == 2 and 1 <= cycle_index <= 64`, there are 19,215 samples
  over `38.482 s`; OLS speed is `0.1539100800512008 m/s`, endpoint speed is
  `0.1539848186684684 m/s`, and nominal ratio is `1.014791736601324`.
- Requested-cycle measured-velocity statistics are count `19,215`, minimum
  `0.12536092`, p05 `0.1428249709`, median `0.152981706`, mean
  `0.1539435460627114`, p95 `0.1668953279`, and maximum `0.183093798 m/s`.
  Ground-truth world-x velocity over the primary stage-2 interval has mean
  `0.15307862413845386`, median `0.154750643774`, p05 `0.12934951202775`,
  and p95 `0.17090115388605 m/s`.
- Requested-cycle controller health maxima/minima are roll `0.907105 deg`,
  pitch `0.980239 deg`, support drift `5.03174 mm`, joint error `0.0616535
  rad`, foot error `0.0272088 m`, estimated torque `16.44 Nm`, minimum support
  contacts `2`, support-contact fraction `1.0`, and zero low-support samples.
  Touchdown absolute errors peak at `0.00500592 m` x and `0.00680105 m` y;
  torque-over-limit samples and consecutive counts are both zero.
- Every requested-cycle row has success-valued `has_state`, footstep-plan,
  full SRBD WBC, full ID WBC, and shadow solver/mapping/task/wrench/constraint
  flags. Terrain is disabled throughout. Controller-log rejection counts are
  zero for clean target infeasible, strict WBC/QP, cycle-quality guard, hard
  safety, and emergency stop.
- Contact validation covers 25,975 rows and 84,955 contact samples, with no
  negative vertical contact GRF samples and maximum vertical GRF `429.144246
  N`. Dynamics validation covers 25,974 balance samples; p95 residual is
  `0.532305526 N`, maximum residual norm is `5.87906345 N`, and the recorded
  tolerance is `10 N`. Both raw validations report `PASS`.
- The gross tracking/stability gate uses the accepted predecessor's
  deterministic operationalization: max absolute roll/pitch below `16 deg`,
  max joint error below `0.80 rad`, minimum support fraction at least `0.35`,
  and `quality_status=0`. All are satisfied by the values above.

The seven computed gates are all true:

```text
valid_controller_handoff                 True
all_64_requested_gait_cycles_complete   True
normal_return_to_stand_without_hard_stop True
no_clean_target_feasibility_rejection   True
no_strict_wbc_qp_rejection               True
measured_forward_speed_in_0_11_to_0_19  True
no_gross_tracking_or_stability_failure  True
```

## LUNA INTERPRETATION

Luna's proposed classification is `CLEAN_BASELINE_FLAT_REPRODUCED`.

The earliest supported boundary is scientific capture: the host established
DDS readiness and controller handoff, then completed the single bounded
flat-ground canary with all 64 requested gait cycles and normal task
completion. The R3 attempt is consumed. No retry, replacement run, tuning,
comparison run, or live follow-up is authorized by this closeout.

This is not an authoritative scientific judgment. Sol must independently
recompute the facts and metrics from the immutable trusted host record and raw
hash-indexed files, and may overturn this interpretation without rerunning the
experiment.
