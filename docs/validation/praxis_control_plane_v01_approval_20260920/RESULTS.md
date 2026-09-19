# Praxis Control Plane v0.1 approval-gate closeout

Date: `2026-09-20`

Task: `px_1a0bab35091_6ebd645e97`

Task commit and candidate presented to host:
`d09310796445a3ea1baf517ad6c674e6ee4fba35`

Mode: `infrastructure`

## CONTROL PLANE FACTS

- The frozen control-plane request is `v0.1`, dogfood kind
  `approve-before-host`, with approval boundary `before_host`.
- The trusted host record is
  `docs/research/evidence/atlas_host/d09310796445a3ea1baf517ad6c674e6ee4fba35.json`.
  Its SHA-256 is
  `89a57e6c46aed9582708eb5f15b59c645a571c9dbc1487b28f7436f033b0b83a`.
- The host record reports `launched=true`, `returncode=0`, `error=null`, and
  `timed_out=false`. Its recorded interval is
  `2026-09-19T17:33:08.811858+00:00` to
  `2026-09-19T17:34:23.120639+00:00` (74.308781 seconds).
- The host command, domain `217`, run argument, and all frozen controller
  arguments match the TaskSpec. The canonical manifest SHA-256 is
  `a1bcea6bf358dff068774ff209192d3834f855e7a6c82f9a3f577de8cb21705c`.
- No second host invocation was made during this analysis phase. No runtime,
  controller, simulator, test, launch script, host record, or raw evidence was
  modified after host execution.

## CONTEXTPACK FACTS

- Default branch/SHA: `main` /
  `ce53d212d08bb8d1d737bb03b46c352c6afdefd2`.
- Frozen instruction hashes:
  - `AGENTS.md`:
    `0e5f638d56a9bf10fd1a1718a346e46c17cddcfdd3a7e82dc6985d495aecdcec`;
  - `docs/research/SOP.md`:
    `fd3c9d1b2f29ee3924794e5984ead53a2e7de06cf87465eb38f3860439281e2b`;
  - parent closeout:
    `0aac77c9064dfe9079f70dc01cfd0f970c9e7d7b59e2f44ae9080c9768d6fd42`.
- The frozen project-profile hash is
  `4d42d51738b60efbf25584f03f27e1800f3f342fe026369ef3a47f9c20a1b258`.
  The observed `.atlas/project.json` hash is
  `aa8158ff9e7f267a4a89f8b73e3b81d702c8c12fe20428f140d9e43ff7d80f77`; this
  pre-existing ContextPack/profile mismatch is recorded, not repaired.
- The exact task-file SHA-256 is
  `296b575f800a29358c852f6a5d85b02fb47646456539e7f245891b3ee83cba5b`.

## APPROVAL/CANCEL BOUNDARY

- The task required explicit approval before the trusted Go2 host boundary.
  The trusted worker reached the post-host `analyzing` state, and the host
  record proves that exactly one permitted host invocation crossed the launch
  boundary. No cancellation was recorded before launch.
- The host JSON does not contain an approval-event identifier or approval
  timestamp. Therefore the approval ordering is a trusted-control-plane fact,
  not something independently reconstructed from the host JSON alone. This
  closeout does not claim stronger approval evidence than the supplied worker
  and host records provide.

## HOST FACTS

- Frozen host manifest run directory:
  `example/cpp/experiments/_runs/praxis_v01_approval_gate_20260920_r1`.
  That path is absent in this analysis worktree, and the host record has
  `evidence=[]`.
- The immutable raw artifacts are present at the host-created nested path:
  `example/cpp/experiments/_runs/example/cpp/experiments/_runs/`
  `praxis_v01_approval_gate_20260920_r1`.
  This is a path/indexing anomaly, not a moved or repaired run. The raw tree
  was left in place.
- `run_manifest.json` reports candidate commit
  `d09310796445a3ea1baf517ad6c674e6ee4fba35`, `git_dirty=false`, domain `217`,
  controller duration `15` seconds, wall timeout `45` seconds, and all nine
  completion/controller/analysis/safety/quality/ground-truth/dynamics status
  fields equal to `0`.
- The raw run's build provenance matches the recorded simulator, controller,
  scene, canonical runner, exact-source wrapper, and DDS preload hashes.
- Pre/post DDS snapshots report domain `217`, loopback interface `lo`, expected
  ports `58250` through `58323`, no active Go2 processes, and no known DDS SHM
  artifacts after cleanup.

Primary raw hashes (actual nested path):

| Artifact | Size | SHA-256 |
|---|---:|---|
| `data.csv` | 15,801,724 bytes | `3ded27c5363bb7744a652f0126e9633c1d09938b8a31e87a3fc8f6044cc33481` |
| `contact_ground_truth.csv` | 23,389,975 bytes | `0d9cb76df842b4e0785f3a9113e5cc2078d1ed42551eb31792977670d6d024a1` |
| `run_manifest.json` | 3,084 bytes | `caed60b632757842cd69af7996e3df27c18ebec622fe65a2b753657185504af5` |
| `run_metadata.txt` | 3,675 bytes | `ab31f5d9c48aae8bd04f197b43bac1d133e82470d81116a5260c537b37958095` |
| `build_provenance.txt` | 4,174 bytes | `96f3109e4bddcea763568fa75ba3420e188ce166fd6dc495b326b374a378f7d5` |
| `controller.log` | 4,482 bytes | `9092a59382e02ef80c2a9e6924fa6534cbd131799f313de0089f820fbd6f6bfa` |
| `simulator.log` | 4,078 bytes | `62a3c4e39f186d138e42303f94429de25c1001ecb5a3181fe359a080dad9950c` |

## DERIVED METRICS

All metrics below were recomputed read-only from the actual nested raw path.
They are descriptive evidence checks, not a locomotion-quality claim.

- CSV integrity: `data.csv` has 5,760 rows and 278 columns; every row has the
  expected width; `cmd_time_s` is monotonic over `0.000..11.502` seconds and
  `state_tick_s` is monotonic over `1.688..13.264` seconds. Every row has
  `has_state=1`.
- Motion-stage counts are `{0: 1503, 1: 649, 2: 2203, 3: 1405}`. The
  `cycle_index` counts are `{-1: 2152, 0: 301, 1: 300, 2: 301, 3: 300,
  4: 301, 5: 298, 6: 301, 7: 1506}`. Every row reports
  `wbc_full_srbd_ok=1` and `wbc_full_id_ok=1`; the maximum absolute recorded
  `wbc_full_eq_residual` is `0.000004283`.
- The standard `analyze_locomotion_progress.py` calculation, using
  `--target-speed 0.15166666666666667 --min-cycle 1`, yields 1,902 walking
  rows, 3.810000 seconds, 0.562794 m distance, OLS speed `0.151886 m/s`,
  endpoint speed `0.147715 m/s`, and maximum lateral drift `0.005518 m`.
  This descriptive calculation is not used to accept the infrastructure task.
- `contact_ground_truth.csv` has 6,659 rows and 264 columns, strictly
  increasing contiguous steps, and time span `13.316` seconds at median
  `0.002` seconds. The standard ground-truth analyzer reports 22,833 contact
  samples, minimum contact vertical GRF `5.07148218 N`, maximum contact
  vertical GRF `429.144246 N`, maximum contact GRF norm `526.466334 N`, zero
  negative vertical-GRF samples, and `validation=PASS`.
- The standard dynamics analyzer with `--balance-tolerance-n 10` reports
  constant mass `15.206408 kg`, gravity `(0,0,-9.81) m/s^2`, p95 force-balance
  residual `0.375124275 N`, RMS `0.248879277 N`, maximum component residual
  `5.8481883 N`, maximum residual norm `5.87906345 N`, and
  `force_balance_validation=PASS`.

Reproducibility/provenance for the analyzer metrics:

```text
python3 example/cpp/tools/analysis/analyze_contact_ground_truth.py \
  example/cpp/experiments/_runs/example/cpp/experiments/_runs/\
  praxis_v01_approval_gate_20260920_r1/contact_ground_truth.csv
python3 example/cpp/tools/analysis/analyze_contact_dynamics.py \
  example/cpp/experiments/_runs/example/cpp/experiments/_runs/\
  praxis_v01_approval_gate_20260920_r1/contact_ground_truth.csv \
  --balance-tolerance-n 10
python3 example/cpp/tools/analysis/analyze_locomotion_progress.py \
  example/cpp/experiments/_runs/example/cpp/experiments/_runs/\
  praxis_v01_approval_gate_20260920_r1/data.csv \
  --target-speed 0.15166666666666667 --min-cycle 1
```

Analyzer SHA-256 values were respectively:

- `analyze_contact_ground_truth.py`:
  `a5426a8f6af8dbb15202c48eb6411afd936456a2a34d5d5ba678ebe7b771886f`;
- `analyze_contact_dynamics.py`:
  `ba17187dd7d979e2dbdfd288c96f7193e496b7cf51c2b96cbcc1461a2f7bcd37`;
- `analyze_locomotion_progress.py`:
  `32dd989a5ba48beaf2a2fba83e3e3e81fc5ba1b9ca7c799e6e43ac21eee564e6`.

The row counts, stage/cycle counters, monotonicity checks, and hash table were
computed with Python standard-library `csv.DictReader`, `Counter`, and
`hashlib.sha256` in a read-only one-off scan; no helper file was added.

## LUNA INTERPRETATION

The trusted control-plane path completed one frozen invocation after the
before-host gate, with the exact candidate and command, return code zero, and
no retry. On that narrow infrastructure question, Luna interprets the
approve-before-host behavior as having passed.

The conclusion is conditional because the host record does not index the raw
artifacts it produced: the manifest path is absent, while the actual run is
under a duplicated path prefix and `evidence=[]`. The frozen ContextPack also
has a project-profile hash mismatch, and the host JSON does not preserve an
approval-event token. These are provenance/audit limitations, not grounds to
move, normalize, or overwrite raw evidence after capture.

### LUNA CLASSIFICATION

`PRAXIS_APPROVE_BEFORE_HOST_ACCEPTED_WITH_RAW_PATH_ANOMALY`

This is an infrastructure/control-plane classification only. It is not a
scientific or controller-quality classification. Sol may independently
recompute the metrics above and overturn this interpretation.

## ACCEPTANCE

- Control-plane acceptance: `PASS`, conditional on the trusted wrapper's
  approval sequencing.
- Host execution: exactly one launch, successful return, no timeout/error.
- Raw evidence: preserved and analyzable at the observed nested path, but not
  correctly indexed by the supplied host record; evidence-integrity status is
  `ANOMALY`.
- No live rerun, source/runtime mutation, Git metadata write, or push was
  performed during closeout.
