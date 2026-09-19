# Praxis typed Go2 live canary closeout

Date: `2026-09-19`

Task commit: `7b3203303611562f682b1115e5cd99226c9a5d1e`

Candidate commit presented to the trusted host: `4decd75be91c2bb170f1c3041f27286215555647`

Mode: `infrastructure`

This closeout accepts the typed capability boundary only. It is not a
locomotion, gait-quality, or sim-to-real research result.

## TYPED REQUEST FACTS

- Capability: `go2-mujoco-live`.
- Dogfood kind: `typed-go2-capability-v0`.
- Expected transport marker: `ATLAS_HOST_EXPERIMENT`.
- Exactly one trusted host invocation was authorized and recorded.
- The frozen typed request, compiled legacy host block, and host record command
  all use domain `219`, host timeout `300 s`, wall-time argument `45 s`, and
  run directory
  `example/cpp/experiments/_runs/praxis_typed_go2_live_canary_20260919_r1`.
- The exact parent is commit `65824c293ce38100d3d7639d23c028b5b033b975`;
  its parent evidence is
  `docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md`.

## TRUSTED HOST FACTS

### HOST/RAW FACTS

- Trusted record:
  `docs/research/evidence/atlas_host/7b3203303611562f682b1115e5cd99226c9a5d1e.json`.
- Trusted record SHA256, recomputed offline:
  `bda16a031ec2f4ac777798220b742b37789fca44da31cc81fadd81a26d316960`.
- `launched=true`, `returncode=0`, `timed_out=false`, and `error=null`.
- Trusted host interval was `2026-09-19T13:21:47.029278+00:00` through
  `2026-09-19T13:23:01.533648+00:00` (`74.504 s`, calculated from the
  record timestamps).
- Raw run directory:
  `example/cpp/experiments/_runs/praxis_typed_go2_live_canary_20260919_r1`.
- Its 18-file trusted evidence snapshot matches an independent recursive
  SHA256/size snapshot exactly: `18/18`, `39,293,241` bytes.
- The raw `run_manifest.json` records candidate commit
  `4decd75be91c2bb170f1c3041f27286215555647` and `git_dirty=false`.
- The exact-source build provenance reports successful `unitree_mujoco` and
  `real_trot_go2` builds. It records simulator SHA256
  `47c3ddfb996ded32fbb70e86bac0863df0888f6046339c5b446c2a0f159a4bf3`,
  controller SHA256
  `c123659929a142d719e5169818bfb1e46963375225fbeab1181b27b060bd3ab8`,
  and scene SHA256
  `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.
- DDS runtime metadata records CycloneDDS `0.10.2`, interface `lo`, domain
  `219`, port base `4000`, and the expected runtime preload artifact.
  `simulator.log` contains `Unitree DDS bridge ready`.
- Controller handoff is evidenced by `Natural LowState settled`,
  `WBC-FULL: 18-DoF MJCF model loaded`, and `Starting diagonal trot:` in
  `controller.log`. The controller then records return-to-stand and the
  simulator records shutdown.
- The post-run DDS snapshot has no active Go2 processes and no known shared
  memory entries. The run manifest statuses are all zero:
  `controller`, `completion`, `analysis`, `dynamics`, `ground_truth`,
  `phase1_quantitative`, `quality`, `safety`, and `terrain_analysis`.

## TRANSPORT COMPILATION

- `PRAXIS_CAPABILITY_REQUEST` equals the frozen TaskSpec
  `capability_request`: `PASS`.
- `ATLAS_HOST_EXPERIMENT` equals the frozen TaskSpec `capability_request`:
  `PASS`.
- The trusted host command equals the compiled legacy command: `PASS`.
- Repository manifest validation passed without changing the manifest.
- Canonical validated-manifest SHA256, independently recomputed with the
  repository's sorted compact JSON plus newline rule:
  `6fe93ef680f7eeb80007007e6a99bd93a6be228e0e1089fe379289a0088ea3b5`.
- The host record carries the same manifest SHA256.

## DERIVED METRICS

All metrics below are offline derivations from the trusted record and immutable
raw files. Reproduction used the host record's evidence list, SHA256 over each
raw file, Python `csv.DictReader`, and the recorded analysis text; no raw file
was rewritten.

- `data.csv`: `5,790` rows, `278` columns, consistent row widths, command-time
  span `0.000` to `11.504 s`.
- `contact_ground_truth.csv`: `6,649` rows, `264` columns, consistent row
  widths, time span `0.002` to `13.298 s` (`13.296 s`).
- Contact analysis: `22,782` contact samples, zero negative vertical-GRF
  samples, validation `PASS`.
- Dynamics analysis: `6,648` balance samples; total mass constant at
  `15.206408 kg`; p95 force-balance residual `0.402770777 N`; maximum residual
  norm `5.87906345 N`, below the recorded `10 N` tolerance; validation `PASS`.
- Raw `run_manifest.json` and `run_metadata.txt` both report controller and
  completion status `0`; all other recorded status fields are also `0`.

## INFRASTRUCTURE ACCEPTANCE

### LUNA INTERPRETATION / CLASSIFICATION

`TYPED_GO2_CAPABILITY_ACCEPTED`.

The frozen typed request crossed the trusted Go2 MuJoCo/DDS host boundary in
the authorized single invocation: the manifest compiled exactly, the host
launched and returned `0` without timeout, DDS became ready, controller
handoff was recorded, all indexed raw evidence hashes were preserved, and the
run's infrastructure/status gates were zero.

This classification says only that the typed capability transport and trusted
host execution completed successfully. It makes no claim about locomotion
quality, scientific performance, or sim-to-real transfer, and Sol may
independently recompute or overturn it from the evidence above.

## LIMITATIONS

- Host stdout/stderr files were outside this workspace; their trusted hashes
  remain in the host record. The raw run evidence and its 18-entry snapshot
  were available locally and verified byte-for-byte.
- Final trusted result push is wrapper bookkeeping and is not inferred from
  the host return code; this Luna closeout leaves the intended tracked change
  uncommitted.
- No replacement live execution, rerun, source change, test change, launch
  script change, or raw-evidence modification was performed after host
  execution.
