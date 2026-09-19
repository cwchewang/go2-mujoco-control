# Praxis Control Plane v0.1 clean acceptance closeout

Date: `2026-09-20`

Task commit: `67ceb1c8ede41200294939fc3e7963718df966bf`

Candidate commit presented to the trusted host: `67ceb1c8ede41200294939fc3e7963718df966bf`

Mode: `infrastructure`

Proposed Luna classification: `CONTROL_PLANE_V01_CLEAN_ACCEPTED`

This closeout is an infrastructure acceptance record. It is not a new
scientific claim about locomotion repeatability or controller performance.

## CONTEXTPACK

The frozen ContextPack in the task document was checked against the candidate
tree and the existing `origin/main` ref:

- Project: `go2-mujoco-control`
- Repository: `cwchewang/go2-mujoco-control`
- Default branch SHA: `e01a3730da97dbfa0de0e3b0124a29a97f10b187`
- Project profile: `.atlas/project.json`
- Raw profile SHA-256: `aa8158ff9e7f267a4a89f8b73e3b81d702c8c12fe20428f140d9e43ff7d80f77`
- Canonical profile SHA-256: `4d42d51738b60efbf25584f03f27e1800f3f342fe026369ef3a47f9c20a1b258`
- `AGENTS.md` SHA-256: `0e5f638d56a9bf10fd1a1718a346e46c17cddcfdd3a7e82dc6985d495aecdcec`
- `docs/research/SOP.md` SHA-256: `fd3c9d1b2f29ee3924794e5984ead53a2e7de06cf87465eb38f3860439281e2b`
- Parent closeout SHA-256: `0aac77c9064dfe9079f70dc01cfd0f970c9e7d7b59e2f44ae9080c9768d6fd42`

The raw profile hash is SHA-256 over the file bytes. The canonical profile
hash is SHA-256 over `json.dumps(json.loads(profile), sort_keys=True,
separators=(",", ":"))` encoded as UTF-8, with no trailing newline. Both
values reproduce the frozen ContextPack exactly.

## APPROVAL RECEIPT

Source: `docs/research/evidence/atlas_host/67ceb1c8ede41200294939fc3e7963718df966bf.json`

The trusted record contains this approval receipt:

```json
{
  "schema_version": 1,
  "repository": "cwchewang/go2-mujoco-control",
  "issue_number": 127,
  "label": "praxis-approved",
  "event_id": 31455090148,
  "created_at": "2026-09-19T18:17:17Z",
  "actor": "cwchewang"
}
```

The receipt timestamp precedes the trusted host start timestamp
`2026-09-19T18:17:22.209399Z`.

## HOST EVIDENCE

### FACTS

The immutable trusted host record reports:

- `launched: true`
- `returncode: 0`
- `error: null`
- `timed_out: false`
- host record `schema_version: 1`
- `task_commit` and `candidate_commit` equal the exact task commit above
- `domain_id: 213`
- `run_dir: example/cpp/experiments/_runs/praxis_v01_clean_acceptance_20260920_r1`
- host timeout: `300 s`
- start: `2026-09-19T18:17:22.209399+00:00`
- finish: `2026-09-19T18:18:37.309456+00:00`
- frozen manifest SHA-256: `43317db71cf3afd32315099562acf1e8b72b9033da2546dd064a888926033663`

The host record's command is byte-for-byte equivalent as an argv list to the
single `ATLAS_HOST_EXPERIMENT` manifest in the task document. Its normalized
manifest hash was independently recomputed and matched the record.

The build provenance in the raw run reports a clean candidate worktree and
successful exact-source builds:

- simulator SHA-256: `47c3ddfb996ded32fbb70e86bac0863df0888f6046339c5b446c2a0f159a4bf3`
- controller SHA-256: `ee16b2763249e946df428829d79179669e531fdbf9de3bf035c91040213fc0c2`
- scene SHA-256: `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`
- MuJoCo version in simulator log: `3.3.6`
- DDS domain in runtime snapshots: `213`
- DDS interface: `lo`
- CycloneDDS version in runtime snapshots: `0.10.2`

The canonical raw-evidence index in the trusted record contains 18 files and
is non-empty. The following is the indexed snapshot; each hash is the raw file
SHA-256 recorded by the host:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `build_provenance.txt` | 4,126 | `2f2b00d23990d4ff4b4539d7f2cb39abeff86aa330fda9e2d2b8f18d756979d7` |
| `contact_ground_truth.csv` | 23,387,746 | `ddfa531a2b4bc29e8e7f7c74db6945b0a10112a55ecb2a0cfa791b5b83a43656` |
| `contact_ground_truth_analysis.txt` | 214 | `51629d972533b8f69a565473360548c7d6bfed3f9dcd8ae818b747a28e12ae40` |
| `contact_ground_truth_dynamics_analysis.txt` | 514 | `924ed8fc557f8b9e671839bb3eb0a0900ea5d08f806f1e3342ebddf6f0ffabf1` |
| `controller.log` | 4,477 | `eb1b817afe759c00001b3ee65ec6d756995bd1b6eba3b6716d915913555debc4` |
| `controller_build.log` | 1,592 | `42997b910b2af299cef097739ea70f29ae09fa9b4fefa62d546f4e375cf5029f` |
| `data.csv` | 15,907,710 | `0c3b7fa8b0ba7206bba670460f00f7a873e6f846382e8152a7fb3fbb33cf310f` |
| `dds_runtime/dds_base4000_preload.so` | 15,560 | `0631e8aa1b9826215ef268665049d154571d3ca332eeff478b8fa9d17691293f` |
| `dds_runtime/post_clean_state.txt` | 3,200 | `cd4ae03096d9ca0725537e0ced69a1c9973e7354ed02003c9fdc6844bf8bfa52` |
| `dds_runtime/post_state.txt` | 3,194 | `83142971318f01d61ee8293501910219deea16d0bde9020ee701b35802f0b516` |
| `dds_runtime/pre_state.txt` | 3,193 | `bc8a9a5667b74e4fbf45d828f40588c1613a997d44992ea8a484b9029137d9cb` |
| `dds_runtime/preparation_cleanup.txt` | 200 | `a9654ae9b452294b003d0208155c73981dffc9f559906646400ed5954da484a6` |
| `dds_runtime/runtime_metadata.txt` | 867 | `0b8d05c158084207f552f59cb061860847ca73d64710212b08eb9b38ffec8268` |
| `environment.txt` | 100 | `fcdd684a211809d5382bb92eba651a1e7d3e75b7672a6674616e469c32d53981` |
| `run_manifest.json` | 3,087 | `f88bea29fcc88c42d9ea4f8b1570e8bf783b40d30b5fbb626e835d08b159634b` |
| `run_metadata.txt` | 3,486 | `e96d3a99fdee70c942ea67e62f43526431e364856c935b6651b3f92246bd779e` |
| `simulator.log` | 4,078 | `6a1d36c1e8246d8f0dbc0c40473825db04ef65ea35352bd97314efd19f8a5c40` |
| `simulator_build.log` | 2,196 | `7f998f25bc1013301c84f8a0dc8b58472e5c13dbab02858e42a005b1b9f50ec3` |

The raw run's `run_metadata.txt` and `run_manifest.json` both report zero for
controller, safety, quality, analysis, ground-truth, dynamics, completion,
phase-1 quantitative, and terrain-analysis status fields. The runtime
snapshots report no active Go2 processes and no known shared-memory entries in
the pre, post, and post-clean snapshots.

### DERIVED METRICS

All metrics below were recomputed offline from the trusted record and raw run;
no raw file was rewritten. The evidence snapshot was reproduced by recursively
enumerating files under the frozen run directory, recording relative path,
type, byte size, and SHA-256, then comparing the resulting ordered list to the
record's `evidence` array. Result: exact match, 18 files, `39,345,540` bytes.

The time intervals were calculated by parsing the ISO-8601 timestamps and
subtracting datetimes:

- approval-to-host-start: `5.209399 s`
- trusted host elapsed time: `75.100057 s`
- elapsed time / host timeout: `75.100057 / 300 = 0.2503335`

The frozen manifest was parsed from the task marker and normalized with
`json.dumps(..., sort_keys=True, separators=(",", ":"))` plus one newline,
matching the host wrapper's manifest digest calculation. Result:

- recomputed manifest SHA-256: `43317db71cf3afd32315099562acf1e8b72b9033da2546dd064a888926033663`
- command, domain, and run directory: exact match to the host record

CSV metrics were computed with Python's standard-library `csv.DictReader`
without changing field order or numeric text:

- `data.csv`: 5,797 rows, 278 columns; `cmd_time_s` range `0.000–11.502 s`;
  `state_tick_s` range `1.684–13.278 s`; maximum `motion_dt_s` `0.004 s`;
  maximum `state_tick_gap_s` `0.018 s`; maximum wall motion interval
  `0.003813232 s`.
- `data.csv` motion-stage counts: stage `0` = 1,518, stage `1` = 658,
  stage `2` = 2,215, stage `3` = 1,406.
- `data.csv` consistency fields: terrain plan status, terrain planner
  rejections, terrain planner deadline misses, terrain safe-stop request,
  terrain plan failure, and reactive event activity remained zero in every
  row. Maximum `wbc_shadow_max_abs_tau` was `17.737528497`; maximum absolute
  joint `tau_est` was `22.55534935`; maximum absolute joint `q_error` was
  `0.228970289`.
- `contact_ground_truth.csv`: 6,658 rows, 264 columns; `step_index` range
  `0–6657`; time range `0.002–13.316 s`; span `13.314 s`; maximum
  `reactive_obstacle_contact_count` `0`; maximum
  `phase2_terrain_nonfoot_contact_count` `0`; total vertical contact-force
  column range `0–1358.06384789 N`.
- The raw contact-analysis report records 22,809 contact samples, zero
  negative vertical-contact-force samples, and `validation=PASS`.
- The raw dynamics-analysis report records p95 force-balance residual
  `0.390619638 N`, maximum residual norm `5.87906345 N`, tolerance `10 N`,
  and `force_balance_validation=PASS`.

The controller log records the frozen command values, clean-baseline mode,
WBC-full enabled, no Cartesian-world route, and the bounded return-to-stand
transition. These observations are retained as raw-run facts and consistency
checks; they are not used here to make a new scientific performance claim.

## ACCEPTANCE

### LUNA INTERPRETATION / classification

`CONTROL_PLANE_V01_CLEAN_ACCEPTED` is proposed for Sol review because all
task-specific infrastructure gates are satisfied:

1. The trusted record contains an explicit `praxis-approved` receipt, and its
   recorded creation time precedes host start by `5.209399 s`.
2. The trusted host launched exactly the frozen candidate/manifest, returned
   zero, did not time out, and reported no host error.
3. The exact frozen run directory is non-empty, and its 18-file raw snapshot
   is reproducibly identical to the trusted record's canonical evidence index.
4. The task ContextPack's raw and canonical project-profile hashes reproduce
   from the candidate tree, as do the frozen default-main and instruction
   hashes.
5. Runtime/build metadata and all recorded run status fields are internally
   consistent with a clean bounded host execution.

This interpretation is deliberately non-authoritative. Sol can independently
recompute the metrics from the trusted host record and raw files, and can
overturn this proposed infrastructure classification. No replacement run,
raw-evidence repair, source/runtime change, or live rerun was performed during
post-host analysis.
