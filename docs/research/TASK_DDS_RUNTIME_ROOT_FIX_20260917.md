# DDS runtime root-fix

Mode: `infrastructure / non-locomotion / host-smoke`

Exact parent: `2f26b7ce9e74ec799cf600cf7db2ec2bd978fc3e`
Scientific clean-baseline parent: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`

## Why this task exists

The host-executed clean-baseline canary reached MuJoCo startup but CycloneDDS aborted before the controller started:

- interface `lo` was selected;
- MuJoCo data preparation completed;
- DDS then reported `Failed to find a free participant index for domain 220` and `Failed to create domain explicitly`;
- no controller `data.csv`, LowState/LowCmd handoff, or scientific sample was produced.

Historical repository evidence shows that successful Atlas/WSL campaigns already carried two DDS-specific mechanisms that are not part of the current generic `run_trot.sh` path:

1. cleanup of known `cdds*` / `cyclonedds*` / `iceoryx*` shared-memory objects at harness boundaries;
2. an optional repository source `example/cpp/scripts/dds_base4000_preload.c`, historically compiled to `/home/che/dds_base4000_preload.so` and injected by `GO2_DDS_PRELOAD` / `LD_PRELOAD` in some verified campaigns.

The purpose of this task is not to make one run pass by changing domain IDs. The purpose is to eliminate hidden machine-state and one-off DDS setup from the research workflow.

## Root-fix question

Can we replace the current implicit/fragmented DDS startup assumptions with one repository-owned, deterministic, self-checking runtime layer that:

- starts reliably on the existing frozen domain `220`;
- does not depend on an unexplained `/home/che/*.so` artifact or shell history;
- safely handles stale DDS shared-memory state and real port/process conflicts;
- records enough evidence to distinguish stale state, port collision, interface/configuration error, and application failure;
- succeeds on two consecutive boot cycles on the same domain;
- proves simulator-to-subscriber LowState delivery without publishing LowCmd or actuating the robot;
- is the canonical path used by maintained trot/Phase-2 launchers rather than another task-specific workaround.

## Scientific scope

This is NOT a locomotion experiment.

Frozen / forbidden:

- no planner, gait, MPC, WBC, IK/FK, gains, trajectory, scene, contact, safety, or locomotion parameter changes;
- no stand-up, walking, stepping, terrain traversal, or LowCmd publication;
- no domain switching to make the test pass;
- no controller-performance interpretation;
- no reuse of the 0.15 m/s canary as a smoke test.

The only authorized host activity is DDS boot/transport validation.

## Required investigation before implementation

Read and reconcile at minimum:

- `docs/validation/phase2_clean_baseline_flat_host_v4_20260917/RESULTS.md` and host record from the exact parent;
- `example/cpp/scripts/run_trot.sh`;
- `example/cpp/scripts/run_phase2_b0_pair.sh`;
- `example/cpp/scripts/run_phase2_b0_lockstep_pair.sh`;
- `example/cpp/scripts/dds_base4000_preload.c`;
- historical manifests/evidence that hash or use `/home/che/dds_base4000_preload.so` / `GO2_DDS_PRELOAD`;
- simulator/SDK interface/domain initialization code and current CycloneDDS version/configuration surface.

Do not assume the preload or shared-memory cleanup is the root cause just because it exists. Establish a source-grounded explanation for why it existed and what class of failure it addressed.

## Implementation requirements

Create one canonical DDS runtime/bootstrap layer under maintained repository paths. Exact file/API design is yours, but it must satisfy all of the following.

### 1. Repository-owned configuration

- Any preload/configuration mechanism needed for stable CycloneDDS startup must be generated from tracked repository source/configuration.
- Do not make `/home/che/dds_base4000_preload.so` or any other untracked machine artifact authoritative.
- If `dds_base4000_preload.c` remains the right mechanism, build/use an exact-source artifact deterministically and record its hash.
- If a cleaner CycloneDDS configuration mechanism is proven equivalent and sufficient, use it instead and explain why the historical preload is no longer needed.

### 2. Safe stale-state handling

- Detect relevant live simulator/controller/DDS processes before cleanup.
- Never kill unrelated processes and never delete unrelated `/dev/shm` entries.
- Clean only known DDS/iceoryx bookkeeping objects and only under a fail-safe condition that shows no active Go2 DDS run would be disrupted.
- Record pre-clean and post-clean state.

### 3. Port and participant diagnostics

Before launch, record enough information to answer:

- which interface is selected;
- which domain and effective CycloneDDS port policy are in force;
- which UDP ports relevant to the chosen configuration are already bound and by which PID/process when available;
- whether participant-index exhaustion is caused by actual port occupancy versus configuration/host behavior.

Do not solve a conflict by silently choosing another domain.

### 4. Canonical launcher integration

- `run_trot.sh` must use the canonical DDS preparation path so future scientific runs do not depend on hidden shell state.
- Maintained Phase-2/B0 runners that currently duplicate cleanup or optional preload behavior should delegate to the same mechanism or otherwise be made explicitly consistent with it.
- Avoid a new chain of per-experiment wrappers.

### 5. Read-only DDS probe

If no existing safe probe is suitable, add a minimal read-only Go2 DDS probe that:

- initializes the same interface/domain as the simulator;
- subscribes to `rt/lowstate` only;
- publishes no `LowCmd` and performs no actuation;
- exits success only after receiving a deterministic minimum number of valid LowState samples within a bounded timeout.

## Offline validation before host smoke

Run all practical checks for changed surfaces, including:

- shell/Python/C++ syntax as applicable;
- focused unit tests for any deterministic port/config/cleanup logic;
- build of repository-owned DDS support artifact(s), if used;
- build of the read-only probe, if added;
- existing relevant portable tests;
- `git diff --check`.

Do not launch MuJoCo/DDS yourself from the Luna sandbox.

## Trusted host smoke

The trusted host executor will run exactly one frozen host command. That command may internally perform the deterministic boot-only sequence below, but it must not publish LowCmd.

The host runner must capture its diagnostics and logs under the frozen run directory and perform:

1. pre-state snapshot: relevant processes, `lo` interface details, UDP bindings relevant to the effective DDS port policy, known DDS/iceoryx `/dev/shm` entries, and effective DDS configuration identity/hash;
2. safe canonical DDS preparation;
3. boot cycle A: start MuJoCo on domain `220`, require the DDS-ready condition, start the read-only LowState probe, require successful sample receipt, then terminate cleanly;
4. verify no Go2 simulator/probe process leaked;
5. boot cycle B: repeat the same domain/configuration again, with no manual human intervention or domain change, and require the same readiness + LowState result;
6. post-state snapshot and leak check.

Two successful consecutive cycles are required specifically to rule out a one-shot cleanup illusion.

## Root-fix pass criteria

Classify `DDS_RUNTIME_ROOT_FIXED` only if ALL are true:

1. a concrete root-cause account is supported by repository history plus host evidence;
2. the runtime no longer depends on the untracked historical preload artifact as authority;
3. domain `220` succeeds without domain switching;
4. two consecutive simulator DDS-ready boots succeed;
5. the read-only probe receives LowState in both cycles;
6. no LowCmd is published and no locomotion actuation occurs;
7. no relevant simulator/probe process leaks after either cycle;
8. cleanup/port diagnostics are fail-safe and explain conflicts instead of masking them;
9. `run_trot.sh` and maintained Phase-2 runners share the canonical DDS startup mechanism;
10. focused tests/build checks pass.

Otherwise use exactly one of:

- `DDS_ROOT_CAUSE_FOUND_FIX_INCOMPLETE` — root cause is evidenced but the canonical implementation does not yet satisfy the repeated smoke;
- `DDS_DIAGNOSIS_INCONCLUSIVE` — evidence does not identify a defensible root cause;
- `PROTOCOL_FAILURE` — task/host evidence is invalid or the host smoke cannot be interpreted.

## Closeout requirements

Write:

- `docs/validation/dds_runtime_root_fix_20260917/RESULTS.md`
- `docs/validation/dds_runtime_root_fix_20260917/analysis.json`
- `docs/validation/dds_runtime_root_fix_20260917/provenance.csv`

Structure the result explicitly as:

1. `FACTS` — source/history facts and immutable host facts;
2. `DERIVED DIAGNOSIS` — exact causal reasoning from those facts;
3. `IMPLEMENTATION` — what changed and why it is canonical rather than a workaround;
4. `LUNA INTERPRETATION` — proposed classification, clearly marked as reviewable by Sol.

Include exact hashes/paths for the effective DDS configuration/support artifact and both boot-cycle evidence sets.

<!-- ATLAS_HOST_EXPERIMENT
{"schema_version":1,"command":["bash","example/cpp/scripts/dds_runtime_root_smoke.sh","--domain-id","220","--run-dir","example/cpp/experiments/_runs/dds_runtime_root_fix_20260917/smoke"],"domain_id":220,"run_dir":"example/cpp/experiments/_runs/dds_runtime_root_fix_20260917/smoke","timeout_s":240,"environment":{"LD_LIBRARY_PATH":"/home/che/dev/go2-workspace/current/simulate/mujoco/lib"}}
ATLAS_HOST_EXPERIMENT -->
