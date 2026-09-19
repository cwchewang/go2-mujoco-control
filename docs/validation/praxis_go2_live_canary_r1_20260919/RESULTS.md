# Praxis Go2 MuJoCo live canary R1 closeout

Date: `2026-09-19`

Mode: `infrastructure / one trusted host-live canary`

Candidate presented to the host: `4b7a2bd2593a298d08bd244e21ffea143a217b1a`

## 1. TRUSTED HOST FACTS

Sources used here are the trusted host record
`docs/research/evidence/atlas_host/4b7a2bd2593a298d08bd244e21ffea143a217b1a.json`
and its sealed run directory
`example/cpp/experiments/_runs/praxis_go2_live_canary_r1_20260919/`.
The raw directory contains exactly the 18 files indexed by the host record;
recorded path, byte size, and SHA-256 all match the current files.

- The host record has `launched=true`, `returncode=0`, `timed_out=false`, and
  `error=null`. Its host timeout was 300 s; the recorded host elapsed time was
  75.655047 s.
- The normalized frozen manifest hash is
  `9243032a07c2c52ade97be948c53c6ad82e6c40e07d745afbd4633ad68d004e7`, matching
  the task manifest. The recorded command, run directory, domain `218`, and
  empty environment match the task exactly.
- `build_provenance.txt` records the same candidate commit and tree
  `910ecf058499df2cbb99f12fb8099a0f60441e38`, a clean tracked worktree, and
  exact-source simulator/controller outputs. The recorded hashes are:
  simulator `47c3ddfb996ded32fbb70e86bac0863df0888f6046339c5b446c2a0f159a4bf3`;
  controller `3271859612e739e3671ee6ec38b3ca3970614d21aff880553168a833c5ced701`;
  scene `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.
- `simulator.log` contains `Unitree DDS bridge ready`. `controller.log`
  contains `Natural LowState settled`, `WBC-FULL: 18-DoF MJCF model loaded`,
  and the diagonal-trot start sequence.
- The controller log records seven health lines for cycle IDs 0 through 6,
  then pre-stop braking, `LOCOMOTION -> RETURN_TO_STAND`, and
  `Trot stopping; returning to stand`. The simulator log records
  `SIGNAL: shutdown requested`.
- `run_metadata.txt` and `run_manifest.json` report zero for controller,
  safety, quality, analysis, ground-truth, dynamics, completion, and other
  generated status fields. The post DDS snapshot reports no active Go2
  processes and no known shared-memory objects.

## 2. DERIVED METRICS

No raw file was rewritten. The contact metrics were recomputed with the exact
analyzers named and hashed in `run_manifest.json`:

- `analyze_contact_ground_truth.py` SHA-256:
  `a5426a8f6af8dbb15202c48eb6411afd936456a2a34d5d5ba678ebe7b771886f`.
- `analyze_contact_dynamics.py` SHA-256:
  `ba17187dd7d979e2dbdfd288c96f7193e496b7cf51c2b96cbcc1461a2f7bcd37`.

The reproducible analyzer commands were run against the sealed
`contact_ground_truth.csv` with their default 5 N touch threshold and the
recorded 10 N dynamics tolerance. Both returned `validation=PASS` with these
values:

- 6,653 ground-truth rows, 264 columns, time span 13.304 s, median sample
  interval 0.002 s.
- 22,967 contact samples; contact GRF z range 5.00293895 to 429.144246 N;
  maximum contact GRF norm 526.466334 N; negative contact GRF z samples: 0.
- Total mass remained 15.206408 kg and gravity was `(0, 0, -9.81)` m/s² with
  zero measured gravity drift.
- Force-balance p95 residual was 0.380452885 N, RMS residual 0.237695513 N,
  maximum component residual 5.8481883 N, and maximum residual norm
  5.87906345 N. The p95 value is below the 10 N tolerance.

An independent standard-library CSV scan of `data.csv` found 5,776 rows and
278 columns, with command-log time from 0 to 11.502 s and median interval
0.002 s. Every row had `has_state=1`; observed contact count was 2 through 4;
`terrain_safe_stop_requested` was always 0; and terrain contact rejections
were always 0. Across the recorded telemetry, maximum absolute estimated
joint torque was 22.591836929 and maximum absolute shadow torque was
17.714613256, while the controller health lines reported zero torque-over
samples, minimum support contacts 2, zero low-support samples, and support
contact fraction 1.0 for every health line.

These are execution/evidence checks only. They are not locomotion quality
metrics or a scientific comparison.

## 3. LUNA INTERPRETATION / INFRASTRUCTURE ACCEPTANCE

Classification: **`PRAXIS_GO2_LIVE_PATH_READY`**

The exact candidate crossed the trusted host boundary once, built and launched
the exact-source simulator/controller pair, reached DDS readiness and valid
controller handoff, produced sealed outputs with matching provenance, passed
the deterministic contact and dynamics checks, reported no hard safety or
quality rejection, and reached the runner’s controlled-stop condition with
return code 0.

The earlier no-host adapter acceptance is the parent evidence for the central
Praxis -> Go2 adapter segment. This closeout independently covers the host
execution and Luna analysis segments. No trusted push was performed or
asserted: this closeout is intentionally left uncommitted, as required.

## 4. REMAINING LIMITATIONS

- This is one infrastructure canary, not evidence of controller quality,
  repeatability, terrain capability, or a scientific comparison.
- The requested controller duration was 15 s, but `data.csv` spans 11.502 s
  and the ground-truth capture spans 13.304 s. The evidence supports a clean
  bounded stop, not a claim that the full requested duration was sustained.
- Host stdout/stderr are outside this workspace; their hashes are recorded in
  the trusted host record. The indexed run artifacts are the locally auditable
  evidence.
- No additional live run, retry, parameter change, source change, raw-data
  repair, Git commit, or push was performed.
