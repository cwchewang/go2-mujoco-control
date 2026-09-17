# DDS runtime root-fix closeout

Date: 2026-09-17

Task: `docs/research/TASK_DDS_RUNTIME_ROOT_FIX_20260917.md`

Task commit: `305e5734b21cd70d3ce158a25bf2686b9cf7534c`

Candidate commit presented to the trusted host: `5cc56557a3d6a7affd6400f0b3bc8434d91bc6cd`

Trusted host record: `docs/research/evidence/atlas_host/305e5734b21cd70d3ce158a25bf2686b9cf7534c.json`

Proposed Luna classification: `PROTOCOL_FAILURE`

Earliest causal boundary: `execution`

Reason code: `HOST_PREFLIGHT_MISSING_SIMULATOR_BINARY`

No live DDS boot cycle or scientific capture was reached. No scientific attempt
was consumed. This is a reviewable Luna interpretation, not an authoritative
Sol verdict.

## FACTS — host/raw

- The trusted host record reports the frozen smoke command, domain `220`, the
  required `LD_LIBRARY_PATH`, `launched=true`, `returncode=2`,
  `timed_out=false`, `error=null`, and `evidence=[]`.
- The host record identifies candidate commit
  `5cc56557a3d6a7affd6400f0b3bc8434d91bc6cd`; the task commit recorded in the
  same record is `305e5734b21cd70d3ce158a25bf2686b9cf7534c`.
- The recorded host stdout is empty. The recorded stderr contains exactly:
  `missing simulator: /home/che/dev/go2-agent/tasks/305e5734b21cd70d/simulate/build/unitree_mujoco`.
  Its SHA-256 is
  `5bbc4211da098eb420b6019285a3d1fea339a5492088f02bdc939aba280dcd73`.
- The candidate smoke script checks that simulator path at line 47 and exits
  with status 2 before sourcing the runtime layer at line 51, creating the run
  directory at line 52, or preparing DDS at line 53. Its first simulator launch
  is later in the script, after those guards.
- The requested raw run directory does not exist. Therefore neither
  `cycle_A` nor `cycle_B`, the runtime snapshots, the simulator logs, the
  read-only probe evidence, nor a generated support artifact exists for this
  host attempt.
- The trusted host record's `manifest_sha256` is
  `37bb5a6c47b091a71d0fa23d61bba6788a4b8a4fc974c431b236576f56830cdc`.
  The immutable host record itself has SHA-256
  `330acd106feb73c9b9d0387ec838413a9593ee77295cbf0960d87bd5af9627b3`.
- The exact parent closeout documents an earlier, different host attempt that
  reached MuJoCo startup and then failed creating CycloneDDS domain 220 with
  participant-index exhaustion. That historical fact is not evidence that this
  task's candidate reached DDS; the present host attempt stopped earlier at the
  missing-binary guard.

## DERIVED METRICS

| Metric | Value | Reproducible basis |
|---|---:|---|
| Host-record elapsed time | `0.007822 s` | Difference between recorded `started_at` and `finished_at` |
| Host return code | `2` | Trusted host record |
| Host timeout | `false` | Trusted host record |
| Host wrapper invocation | `1` | `launched=true` in trusted host record |
| MuJoCo simulator launch attempts | `0 observed` | Missing-binary guard precedes the first `&` launch in the smoke script |
| DDS preparation calls | `0 observed` | `dds_runtime_prepare` is after the failed guard |
| DDS-ready markers | `0` | No simulator log or raw run directory |
| LowState probe launches | `0 observed` | Probe launch is after the DDS-ready wait |
| Successful LowState cycles | `0 / 2` | Neither cycle directory exists |
| LowCmd publication | `not reached` | No simulator or probe process was launched by this attempt |
| Raw evidence files | `0` | Requested run directory is absent and host `evidence` is empty |
| Generated effective support artifact | `not created` | Runtime preparation was not reached |
| Domain changes | `0 observed` | The only requested domain was frozen domain `220` |
| Scientific capture started | `false` | No controller, probe, or DDS cycle was reached |

The host elapsed time is calculated as:
`2026-09-17T11:26:40.376098Z - 2026-09-17T11:26:40.368276Z = 0.007822 s`.
The host stdout has 0 bytes and the host stderr has 96 bytes; both byte counts
and hashes are recorded in `provenance.csv`.

### Derived diagnosis

The observed failure is a host-side executable-availability failure, not a
CycloneDDS participant, shared-memory, port, interface, or application failure.
The smoke script's control flow and the exact stderr message place the boundary
before runtime preparation. Consequently, the host evidence cannot test the
root-fix criteria requiring two DDS-ready boots, LowState delivery, leak checks,
or effective port diagnostics.

The repository-owned configuration source exists at
`example/cpp/scripts/dds_base4000_preload.c` with SHA-256
`65100130add060af08f6404b03668f5018c9b039849bf62620cd99f362d38a3c` in the
candidate tree. The expected generated artifact
`example/cpp/experiments/_runs/dds_runtime_root_fix_20260917/smoke/dds_runtime/dds_base4000_preload.so`
was not created, so it has no host artifact hash. The same applies to both
cycle evidence sets: the expected `cycle_A` and `cycle_B` paths are absent.

## IMPLEMENTATION

The candidate commit contains the repository-owned runtime layer, deterministic
support-artifact build and hashing, fail-safe known-DDS shared-memory cleanup,
port/process snapshots, canonical `run_trot.sh` and Phase-2 launcher
integration, a read-only `rt/lowstate` probe, and focused offline tests. Exact
candidate file hashes are recorded in `provenance.csv`.

These implementation facts are candidate-source facts only. Because the trusted
host stopped before the smoke script reached them, this closeout makes no claim
that the runtime fixed the historical DDS participant-index failure.

## LUNA INTERPRETATION

The proposed classification is `PROTOCOL_FAILURE` at the `execution` boundary,
with reason code `HOST_PREFLIGHT_MISSING_SIMULATOR_BINARY`. The trusted host did
invoke the frozen command, but the required simulator executable was absent at
the candidate path, so the smoke did not enter MuJoCo, DDS, the probe, or either
boot cycle.

This is not a scientific pass/fail result and does not establish or refute the
DDS runtime root fix. Sol may independently recompute the metrics from the
trusted record, host logs, candidate script, and provenance table, and may
overturn this proposed classification.

## Scope controls

- Trusted host record: not modified.
- Raw run directory/evidence: not modified; it was absent.
- Runtime source, controller source, tests, and launch scripts: not modified
  after the host run.
- Live experiment: not rerun.
- Git metadata: not written or pushed.
- Only the three task-required analysis closeout files are added in this
  post-host phase.
