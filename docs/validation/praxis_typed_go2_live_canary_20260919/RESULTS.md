# Praxis typed Go2 live canary preparation

Date: `2026-09-19`

Task commit: `7b3203303611562f682b1115e5cd99226c9a5d1e`

Candidate commit: `pending trusted wrapper commit`

Mode: `infrastructure`

This is a preparation record only. It does not claim a live run, locomotion
result, DDS handoff, host return code, or final infrastructure classification.

## TYPED REQUEST FACTS

- Capability: `go2-mujoco-live`.
- Dogfood kind: `typed-go2-capability-v0`.
- Expected transport marker: `ATLAS_HOST_EXPERIMENT`.
- Exactly one trusted host invocation is authorized; no replacement, tuning,
  domain change, or retry after launch is authorized.
- The exact parent is commit `65824c293ce38100d3d7639d23c028b5b033b975`.
  Its parent evidence is
  `docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md`.
- The typed request in the frozen TaskSpec is the following normalized manifest
  (36 argv elements, domain `219`, timeout `300 s`):

```json
{
  "command": [
    "bash",
    "example/cpp/scripts/run_trot_exact_source.sh",
    "45",
    "_runs/praxis_typed_go2_live_canary_20260919_r1",
    "--controller-duration",
    "15",
    "--kernel",
    "raibert-trot",
    "--period",
    "0.60",
    "--duty",
    "0.75",
    "--step-length",
    "0.091",
    "--foot-lift",
    "0.020",
    "--kp",
    "63",
    "--kd",
    "2.8",
    "--raibert-velocity-gain",
    "0.05",
    "--raibert-max-adjustment",
    "0.010",
    "--world-feedback-max",
    "0.060",
    "--world-feedback-slew",
    "0.004",
    "--clean-baseline",
    "--tau-limit",
    "35",
    "--max-cycles",
    "6",
    "--headless",
    "--domain-id",
    "219"
  ],
  "domain_id": 219,
  "environment": {},
  "run_dir": "example/cpp/experiments/_runs/praxis_typed_go2_live_canary_20260919_r1",
  "schema_version": 1,
  "timeout_s": 300
}
```

## TRUSTED HOST FACTS

- Luna did not launch MuJoCo, DDS, the controller/simulator pair, or any live
  scientific capture.
- No trusted host record, raw run evidence, DDS-readiness record, controller
  handoff, host return code, timeout result, or result push exists in this
  preparation phase.
- Historical raw evidence under the read-only reference tree
  `/home/che/dev/go2-workspace/praxis-anchor` was not modified.
- Candidate commit assignment remains the trusted wrapper's responsibility;
  Luna did not write Git metadata.

## TRANSPORT COMPILATION

- `PRAXIS_CAPABILITY_REQUEST` equals the frozen TaskSpec
  `capability_request`: `PASS`.
- `ATLAS_HOST_EXPERIMENT` equals the frozen TaskSpec `capability_request`:
  `PASS`.
- Typed request equals the compiled legacy host manifest byte-for-byte after
  JSON parsing: `PASS`.
- Repository validator `atlas_host_experiment.validate_manifest`: `PASS`.
- Canonical validated-manifest SHA256:
  `6fe93ef680f7eeb80007007e6a99bd93a6be228e0e1089fe379289a0088ea3b5`.
- Frozen runner exists at
  `example/cpp/scripts/run_trot_exact_source.sh`; `bash -n` passed.
- The requested run directory was absent before host execution, so it is
  fresh for the trusted wrapper: `PASS`.

## INFRASTRUCTURE ACCEPTANCE

Preparation gate: `READY_FOR_TRUSTED_HOST_EXECUTION`.

This is not final acceptance. The trusted wrapper may now present the exact
frozen manifest for its single host invocation. Final acceptance requires the
trusted host record, immutable evidence hashes, DDS/controller handoff facts,
return/timeout facts, and the final trusted result push.

No-live checks completed in this phase:

- `python3 -m unittest tools/tests/test_atlas_host_experiment.py` — `7/7 OK`.
- `python3 -m unittest tools/tests/test_atlas_research_worker.py tools/tests/test_atlas_dispatch_vnext.py` — `15/15 OK`.
- `bash -n example/cpp/scripts/run_trot_exact_source.sh` — `PASS`.
- `git diff --check` — `PASS`.

The sandbox has no existing `example/cpp/build` or `simulate/build` tree,
and the exact-source wrapper requires host-only MuJoCo and Unitree SDK roots;
those host builds remain deferred to the trusted wrapper. No scientific or
runtime source was changed.

## LIMITATIONS

- The required `git fetch origin --prune` was attempted but could not update
  this linked worktree's shared `FETCH_HEAD` because the Git metadata is
  read-only. The supplied refs were inspected read-only: `HEAD` and
  `origin/research/praxis-px_1a0b9cf9785_937e1b19d0` both resolve to the exact
  task commit, and `origin/main` resolves to the exact parent commit.
- `tools/research/preflight.py` is not present in this task tree. Host-side
  readiness and the trusted wrapper's launch checks remain authoritative.
- No live result or final classification is inferred from these preparation
  facts.
