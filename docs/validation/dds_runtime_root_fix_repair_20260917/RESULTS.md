# DDS runtime root-fix repair closeout

Date: 2026-09-17

Task: `docs/research/TASK_DDS_RUNTIME_ROOT_FIX_REPAIR_20260917.md`

Task commit: `73eb0bee3988e5aaf0b082c50140a959932ce51f`

Exact parent: `6e7f4198747529023073932fac95ac39c3b13a71`

Candidate commit presented to the trusted host:
`bb76042be8ab5c6b008e60c116ddff0128237826`

Trusted host record:
`docs/research/evidence/atlas_host/73eb0bee3988e5aaf0b082c50140a959932ce51f.json`

Raw run directory:
`example/cpp/experiments/_runs/dds_runtime_root_fix_repair_20260917/smoke`

Proposed Luna classification: `DDS_RUNTIME_ROOT_FIXED`

This is an infrastructure/runtime interpretation, not a locomotion result or
authoritative Sol verdict. Sol can recompute the facts and metrics from the
trusted record, the immutable raw files, the candidate commit, and the
provenance table, and can overturn this interpretation.

## FACTS — host/raw

- The trusted host record identifies candidate
  `bb76042be8ab5c6b008e60c116ddff0128237826`, task commit
  `73eb0bee3988e5aaf0b082c50140a959932ce51f`, the frozen command, domain
  `220`, `launched=true`, `returncode=0`, `error=null`, and
  `timed_out=false`.
- The host executed the frozen command once. Its recorded manifest hash is
  `3e60a844fb3aaae2dd9463cebb766251098695a59decc867c40bbdc1ae07bfdc`.
  Recorded host stdout and stderr hashes are respectively
  `5b49382b1530300ce09d67fa6d40fd927791394a48d56650c79d08a14bcaf98f` and
  `13fb34399560b92a4e4b40696ff8c50d53559e8884f30a4d03a476b0f2d19d36`.
- The host index contains 22 raw files. Every indexed path exists in the raw
  run directory and its bytes and size match the host-recorded SHA-256 and
  size fields. The exact hashes are listed in `provenance.csv`.
- `build_provenance.txt` records candidate SHA
  `bb76042be8ab5c6b008e60c116ddff0128237826`, candidate tree
  `85ce7419f04b6c9db945cadcfa0acc6a7652659b`, and a clean configure/build
  policy for both required executables. The simulator and probe were built
  from the candidate source directories. The only external MuJoCo root was
  `/home/che/dev/go2-workspace/current/simulate/mujoco`, resolving to
  `/home/che/.mujoco/mujoco-3.3.6`.
- The recorded exact-source executable hashes are:
  `simulate/build/unitree_mujoco` =
  `8c4ef43acc65938c231a73da6a9dbe7c6b1170d72733f757927316a15d130c1a` and
  `example/cpp/build/dds_lowstate_probe` =
  `153320393475d2b451fb73c869b6b45402b921cd04d2887edec238d545bc8ed3`.
- The effective DDS support source is the tracked
  `example/cpp/scripts/dds_base4000_preload.c`, hash
  `65100130add060af08f6404b03668f5018c9b039849bf62620cd99f362d38a3c`.
  The generated run-local artifact is
  `dds_runtime/dds_base4000_preload.so`, hash
  `0631e8aa1b9826215ef268665049d154571d3ca332eeff478b8fa9d17691293f`.
  `runtime_metadata.txt` has hash
  `2d5ea0f1225abf5da575f9e4971c372f11b879471f897b7783324b858dd6feea`.
  Its `original_ld_preload` field is empty and its effective preload points to
  the run-local generated artifact, not `/home/che/dds_base4000_preload.so`.
- All runtime snapshots record domain `220`, interface `lo`, CycloneDDS
  version `0.10.2`, base `4000`, participant gain `2`, and maximum automatic
  participant index `31`. The expected port range is `59000` through `59073`.
  The observed UDP listings contain no binding in that expected range.
- The preparation and between-cycle cleanup reports both contain an empty
  pre-clean inventory and an empty post-clean inventory. No stale-SHM object
  was present for the host run, so the host did not exercise deletion of a
  nonempty candidate. The fail-closed reference and inspection-gap paths are
  covered by the focused deterministic tests in the candidate.
- Cycle A's simulator log contains one `Unitree DDS bridge ready` marker and
  clean shutdown. Its read-only probe reports 10 valid samples, ticks 668 to
  688, on `rt/lowstate`.
- Cycle B's simulator log contains one `Unitree DDS bridge ready` marker and
  clean shutdown. Its read-only probe reports 10 valid samples, ticks 682 to
  700, on `rt/lowstate`.
- The cycle-A post-state, cycle-B post-state, and final post-state snapshots
  contain empty `active_go2_processes` sections. The smoke script also makes
  an explicit post-cycle leak check.
- The frozen smoke starts only `unitree_mujoco` and the read-only
  `dds_lowstate_probe`; it does not start `real_trot_go2` or another
  controller. The candidate probe source constructs a
  `ChannelSubscriber<LowState>` for `rt/lowstate` and has no
  `ChannelPublisher`, `LowCmd`, or publish call. Therefore the smoke has no
  LowCmd publication or locomotion-control path.

## DERIVED METRICS

| Metric | Value | Reproducible basis |
|---|---:|---|
| Host elapsed time | `28.631046 s` | `finished_at - started_at` from the trusted record |
| Trusted wrapper invocations | `1` | host record `launched=true`, one execution interval |
| Host return code | `0` | trusted host record |
| Exact-source simulator build | `PASS` | build log ends with `Built target unitree_mujoco` |
| Exact-source probe build | `PASS` | build log ends with `Built target dds_lowstate_probe` |
| DDS-ready cycles | `2 / 2` | one marker in each simulator log |
| Successful LowState cycles | `2 / 2` | both probe evidence files report `probe_status=success` |
| Valid LowState samples | `20 / 20 required` | 10 reported in each probe evidence file |
| Monotonic tick checks | `2 / 2` | `688 > 668` and `700 > 682`; probe itself rejects non-increasing ticks |
| Frozen domain | `220` throughout | all runtime snapshots and both probe evidence files |
| Domain switches | `0` | command and all recorded runtime/probe domain fields |
| Expected DDS ports observed occupied | `0 / 66` | compare `ss -lunp` listings with ports `59000..59073` |
| Cleanup invocations | `2` | preparation and between-cycle cleanup reports |
| Host cleanup candidates | `0` | both cleanup reports have empty pre/post inventories |
| Host cleanup deletions | `0` | no per-object decision was needed because inventories were empty |
| Post-cycle Go2 process leaks | `0 / 2` | cycle A/B post-state sections are empty and script leak checks passed |
| Final Go2 process leaks | `0` | final `post_state.txt` active-process section is empty |
| LowCmd publication | `0 observed; path absent` | frozen smoke command plus read-only probe source |
| Raw evidence integrity | `22 / 22` | host-record SHA-256 and size comparison |

The host elapsed calculation is:

`2026-09-17T11:53:58.006612Z - 2026-09-17T11:53:29.375566Z = 28.631046 s`.

The port count is `2 + 2 * (31 + 1) = 66`; the expected values are generated
by the candidate runtime's `Base=4000`, domain gain `250`, participant gain
`2` policy for domain `220`. The host `ss` listings show unrelated bindings
on ports 53, 323, 48529, and 47191, but none of the 66 expected DDS ports.

## DERIVED DIAGNOSIS

The exact-parent evidence established the earlier execution failure boundary:
the prior root-fix host smoke reached MuJoCo but failed before DDS readiness
with participant-index exhaustion on domain 220. The immediate subsequent
parent attempt failed even earlier because a fresh task worktree lacked the
simulator binary. Those are historical execution facts, not measurements from
the current smoke.

The current evidence supports a workflow-level root-cause account: DDS startup
had depended on implicit, fragmented host state and an unavailable exact-source
simulator output. The candidate makes the simulator and probe available from
the candidate source, replaces ambient preload authority with a tracked source
and run-local generated artifact, fixes the effective participant/port policy,
and makes shared-memory cleanup refuse deletion when ownership/liveness cannot
be proven. On the same frozen domain and interface, the host then completed two
consecutive DDS-ready/LowState cycles.

The evidence does not isolate the historical participant-index failure to one
single mechanism between stale shared memory, participant-port allocation, and
the prior hidden preload path. In particular, the current host began with no
matching SHM candidate, so it demonstrates safe empty-state preparation rather
than a live deletion of a referenced or stale object. That limitation does not
invalidate the execution-repair classification because the deletion and
inspection decisions are covered by deterministic candidate tests, but it is
recorded so the result is not overstated.

## IMPLEMENTATION

- `example/cpp/scripts/dds_runtime_root_smoke.sh` now records candidate/build
  provenance, verifies the permitted external SDK, and clean-configures and
  builds `unitree_mujoco` and `dds_lowstate_probe` before DDS preparation.
- `simulate/CMakeLists.txt` accepts an explicit `MUJOCO_ROOT`, allowing the
  simulator sources to remain in the candidate tree while the permitted SDK
  supplies headers, libraries, and simulator support sources.
- `example/cpp/scripts/dds_runtime.sh` inventories exact matching paths,
  refuses known active Go2 DDS processes, checks `/proc` descriptors, memory
  mappings, cwd, and root references for every candidate, fails closed when
  required inspection is unavailable, and records pre-clean decisions and
  post-clean inventories.
- `example/cpp/tests/test_dds_runtime.sh` adds deterministic exact-path,
  deleted-mapping, referenced-object, incomplete-inspection, active-process,
  and unrelated-entry checks.
- `run_trot.sh` remains the maintained canonical DDS integration, and the
  maintained Phase-2/B0 launchers continue to delegate through it. No
  parallel DDS wrapper was introduced.

## LUNA INTERPRETATION

Proposed classification: `DDS_RUNTIME_ROOT_FIXED`.

The proposal is based on all required execution criteria: the exact-source
build succeeded; the tracked run-local DDS configuration was used; domain 220
was retained; both consecutive simulator boots reached DDS readiness; the
read-only probe received valid monotonic LowState samples in both cycles; no
controller or LowCmd publisher was launched; no simulator/probe leak remained;
and the cleanup implementation plus deterministic tests are fail-closed.

This classification makes no locomotion, controller-quality, hardware, or
sim-to-real claim. It is reviewable by Sol. The trusted host record and raw
files were not modified, no live run was repeated, and no Git metadata was
written in this post-host analysis. Only the three required closeout files are
intended tracked changes.
