# Canonical clean-baseline repeatability R1 closeout

Task: `docs/research/TASK_CANONICAL_CLEAN_BASELINE_REPEAT_R1_20260917.md`

Task/candidate commit: `28f883496bd2d64d610ce0d023f2daf7ceea393d`

Canonical protected-main baseline: `e30782ad916ef1614a877d7a3c122f62682c8f19`

Accepted predecessor flat result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`

Trusted host record: `docs/research/evidence/atlas_host/28f883496bd2d64d610ce0d023f2daf7ceea393d.json`

Raw run: `example/cpp/experiments/_runs/canonical_clean_baseline_repeatability_20260917/R1`

Replicate: `R1 / 3`

Proposed Luna classification: `CLEAN_BASELINE_FLAT_REPRODUCED`

## FACTS

- The trusted record reports `launched=true`, return code `0`, no host error,
  no timeout, DDS domain `220`, and elapsed host time `113.924698 s`. The
  frozen manifest SHA256 is
  `06dddb76b0dad0b183a402c18406e181471263b429ed5a13ca0cc13f8f3ebee1`.
- The host record indexes 18 raw artifacts. Every indexed size and SHA256 was
  independently recomputed and matched. The complete per-file ledger is in
  `analysis.json` and `provenance.csv`; raw evidence was not modified.
- Build provenance records candidate tree
  `32dbd9a7bc582d61fafc4e6bf1b9809a9b6176f8`, a clean tracked worktree,
  simulator SHA256
  `47c3ddfb996ded32fbb70e86bac0863df0888f6046339c5b446c2a0f159a4bf3`, and
  controller SHA256
  `896336842bb0e8f344c4f14605819051669d66881eefd7ca79b85bbc9128f080`.
  The frozen scene SHA256 is
  `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.
- The source-identity check is empty for each frozen surface:
  `example/cpp/`, `simulate/`, and `unitree_robots/` are byte-for-byte
  unchanged between canonical main and the candidate commit.
- DDS support is the tracked `dds_base4000_preload.c` source with SHA256
  `65100130add060af08f6404b03668f5018c9b039849bf62620cd99f362d38a3c` and
  host-produced preload SHA256
  `0631e8aa1b9826215ef268665049d154571d3ca332eeff478b8fa9d17691293f`.
  Runtime metadata records CycloneDDS `0.10.2`, loopback interface, port base
  `4000`, domain `220`, and maximum automatic participant index `31`; expected
  RTPS ports are `59000` through `59073`.
- `simulator.log` contains the DDS-ready marker and shutdown marker.
  `controller.log` contains settled `LowState`, start-of-trot, pre-stop brake,
  return-to-stand, lie-down, and task-completed markers. The first CSV sample
  is row 2 with `has_state=1`, `motion_stage=0`, `cycle_index=-1`,
  `cmd_time_s=0`, and `state_tick_s=1.69`; the scientific attempt was
  consumed.
- The raw lifecycle has requested cycles 1 through 64, then the normal
  `LOCOMOTION -> RETURN_TO_STAND -> LIE_DOWN` sequence and
  `Task completed: stand-walk-lie`. All recorded controller/status fields in
  `run_metadata.txt` are zero. No raw log marker reports clean target
  infeasibility, strict WBC/QP rejection, hard safety stop, or emergency stop.
- Host-produced contact ground-truth and dynamics validation both report
  `PASS`. Contact validation covers 25,932 rows and 84,524 contact samples,
  with no negative vertical contact GRF samples and maximum vertical GRF
  `429.144246 N`. Dynamics validation covers 25,931 balance samples with p95
  residual `0.530579758 N`, maximum residual norm `5.87906345 N`, and `10 N`
  tolerance.

## DERIVED METRICS

The deterministic analysis is implemented by
`example/cpp/tools/analysis/analyze_clean_baseline_repeat_r1.py`. It reads
only the trusted record, indexed raw files, the frozen task, and Git object
metadata. `analysis.json` contains the full machine-readable calculation and
gate ledger; `provenance.csv` hashes the task, host record, parent evidence,
analyzer, source identities, raw artifacts, and host-built binaries.

- `data.csv` contains 25,070 data rows and 278 columns. Motion-stage counts
  are `0:1500`, `1:650`, `2:19611`, `3:1402`, `4:1506`, and `5:401`.
  The requested-cycle window contains 19,208 samples; all 25,070 rows have
  `has_state=1`.
- Using the accepted predecessor's stage-2 method—ordinary least-squares
  slope of `world_base_x_m` versus `state_tick_s`, with rows satisfying
  `motion_stage == 2 and cycle_index >= 0`—the locomotion interval is
  `5.99` to `45.21 s`, with `5.963743650 m` displacement and OLS speed
  `0.15330369123472856 m/s`. Endpoint speed is
  `0.15205873661397248 m/s`, or `1.0107935685806277` times nominal.
- The requested cycles 1 through 64 give OLS speed
  `0.15333238872231142 m/s` and endpoint speed
  `0.15322041195918154 m/s`. Nominal speed is
  `0.091 / 0.60 = 0.15166666666666667 m/s`.
- Requested-cycle measured-velocity statistics are count `19,208`, minimum
  `0.124463613`, p05 `0.1419638143`, median `0.152600303`, mean
  `0.15316969349463763`, p95 `0.1665212384`, and maximum `0.177045471 m/s`.
- Controller health over cycles 1 through 64 has maximum absolute roll
  `0.73356 deg`, pitch `0.84654 deg`, support drift `5.17807 mm`, joint error
  `0.061647 rad`, foot error `0.0283063 m`, and estimated torque
  `13.9116 Nm`. Minimum support is two contacts and support-contact fraction
  is `1.0`; torque-over-limit samples and consecutive counts are zero.
  Maximum touchdown errors are `0.00427299 m` in x and `0.00659012 m` in y.
- Every requested-cycle clean target/WBC success flag is `1`; terrain is
  disabled and terrain failure/contact-rejection flags are zero. The exact
  log rejection counts for clean target infeasible, strict WBC/QP, cycle
  quality, hard safety, and emergency stop are all zero.
- All frozen classification gates evaluate true in `analysis.json`: valid
  handoff, 64 completed cycles, normal lifecycle, no target-feasibility or
  strict-WBC rejection, forward speed in `[0.11, 0.19] m/s`, and no gross
  tracking/stability failure.

## LUNA INTERPRETATION

Luna proposes `CLEAN_BASELINE_FLAT_REPRODUCED` for R1. The host established a
valid post-handoff sample, consumed the single scientific attempt, completed
all 64 requested cycles, returned normally through stand to lie-down, and
met the preregistered speed and stability gates without target-feasibility,
strict-WBC/QP, hard-stop, or emergency-stop evidence.

This is only the R1 result of a preregistered three-replicate suite. It does
not seal the suite, authorize tuning, or alter the frozen design for R2/R3.
The classification is a reviewable Luna interpretation, not an authoritative
scientific judgment. Sol may independently recompute `analysis.json` from the
indexed immutable raw files and overturn this proposal without rerunning R1.
