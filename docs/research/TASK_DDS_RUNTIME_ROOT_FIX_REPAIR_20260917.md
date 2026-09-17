# DDS runtime root-fix execution repair

Mode: `infrastructure / execution-repair + host-smoke`

Exact parent: `6e7f4198747529023073932fac95ac39c3b13a71`
Parent classification: `PROTOCOL_FAILURE`
Parent reason: `HOST_PREFLIGHT_MISSING_SIMULATOR_BINARY`

This is the same DDS root-fix question as `TASK_DDS_RUNTIME_ROOT_FIX_20260917`. The prior trusted host smoke consumed zero DDS boot cycles and zero scientific attempts because the candidate worktree lacked `simulate/build/unitree_mujoco`. Preserve the candidate DDS architecture unless new evidence shows it is wrong.

## Objective

Complete the root-fix validation without changing locomotion science:

1. make the host smoke self-sufficient for exact-source simulator/probe availability;
2. strengthen shared-memory cleanup so unrelated CycloneDDS/iceoryx state can never be deleted merely because Go2 process names are absent;
3. run the same frozen domain `220` A/B boot smoke with read-only LowState reception;
4. close out with enough immutable evidence for Sol to accept, revise, or overturn Luna's diagnosis.

## Frozen scope

Forbidden:
- no planner, gait, IK/FK, MPC, WBC, gains, safety, scene semantics, contact, or locomotion parameter changes;
- no `LowCmd` publisher and no actuation;
- no domain switching;
- no manual retry after host execution starts;
- no use of an untracked prebuilt controller/simulator as scientific authority.

Allowed external dependency/toolchain:
- read-only MuJoCo SDK/runtime under `/home/che/dev/go2-workspace/current/simulate/mujoco`;
- ordinary compiler/CMake/Ninja/Make tools already present on Atlas;
- installed Unitree/CycloneDDS development dependencies already used by this repository.

## Repair A — exact-source host build

The canonical smoke must not assume ignored build outputs already exist in a fresh detached task worktree.

Before the first DDS preparation/boot, deterministically ensure these executables exist from the candidate worktree sources:
- `simulate/build/unitree_mujoco`;
- `example/cpp/build/dds_lowstate_probe`.

Requirements:
- build them from the exact candidate source tree used by the host smoke;
- using the permitted external MuJoCo SDK only as dependency/toolchain, never substituting a simulator binary from another revision;
- fail closed if the exact-source build cannot be established;
- record build commands, source/candidate SHA, dependency path/hash where practical, and resulting executable SHA-256 values under the raw smoke directory;
- repeated invocation may reuse a build only if provenance proves it belongs to the same candidate SHA; otherwise rebuild.

Do not require Luna's sandbox to provide the host runtime binary. The trusted host smoke itself must own this deterministic availability step.

## Repair B — fail-closed shared-memory cleanup

Review `dds_runtime_cleanup_stale()` critically. Name-prefix matching plus absence of Go2 process names is insufficient proof that a `cdds*`, `cyclonedds*`, or `iceoryx*` object is unused.

Implement a conservative ownership/liveness proof before deleting each candidate object.

Minimum requirements:
- inventory exact candidate paths first;
- inspect host process state for references to each candidate using reliable `/proc` evidence and/or equivalent tools available on Atlas (for example open file descriptors and memory mappings; use multiple surfaces where appropriate);
- if any process references a candidate, do not delete it and report PID/process/path;
- if the runner cannot establish that a candidate is unused because required process inspection is unavailable or incomplete, fail closed rather than deleting it;
- never delete a non-matching path;
- retain the existing explicit refusal when a known Go2 DDS process is active;
- record pre-clean inventory, per-object decision/reason, and post-clean inventory;
- add focused deterministic tests for parsing/decision logic where possible without host mutation.

The goal is not aggressive cleanup. The goal is: delete only state that is demonstrably stale.

## Preserve and review the candidate architecture

The exact parent already contains:
- `example/cpp/scripts/dds_runtime.sh`;
- `example/cpp/scripts/dds_runtime_root_smoke.sh`;
- repository-source deterministic `dds_base4000_preload` build;
- `dds_lowstate_probe` subscribing only to `rt/lowstate`;
- canonical `run_trot.sh` integration;
- Phase-2/B0 launcher integration.

Keep these as the default design if source/history analysis supports them. Do not create another parallel DDS wrapper stack.

## Offline validation before host smoke

Run all practical checks for changed surfaces, including:
- shell/Python/C++ syntax as applicable;
- focused DDS-runtime tests, including fail-closed cleanup decision tests;
- exact-source build recipe validation for simulator and probe;
- existing portable Atlas/repository checks relevant to touched files;
- `git diff --check`.

Do not start MuJoCo/DDS from inside the Luna sandbox.

## Trusted host smoke

The host executor runs exactly one frozen command below. That command may internally build exact-source executables and then perform the two boot cycles. It must publish no LowCmd.

Required sequence:
1. record candidate SHA and build/dependency provenance;
2. ensure exact-source simulator + read-only probe executables;
3. pre-state snapshot including interface, effective DDS config, relevant UDP bindings, known DDS/iceoryx shared-memory candidates, and their liveness/ownership decisions;
4. canonical fail-closed DDS preparation;
5. cycle A on domain `220`: require simulator DDS-ready, then at least 10 valid monotonic `LowState` samples via read-only probe; terminate cleanly;
6. prove no simulator/probe process leaked;
7. between-cycle snapshot + safe cleanup decision;
8. cycle B on the same domain/config: same DDS-ready + LowState requirements;
9. prove no process leak and record post-state.

No alternate domain and no second host invocation.

## Classification

Use `DDS_RUNTIME_ROOT_FIXED` only if ALL prior root-fix criteria remain satisfied, including two consecutive same-domain successful boots and LowState reception, and the strengthened cleanup is demonstrably fail-safe.

Otherwise use exactly one of:
- `DDS_ROOT_CAUSE_FOUND_FIX_INCOMPLETE`
- `DDS_DIAGNOSIS_INCONCLUSIVE`
- `PROTOCOL_FAILURE`

A host-build/preflight failure before DDS smoke is `PROTOCOL_FAILURE` and consumes zero DDS boot cycles.

## Closeout

Write:
- `docs/validation/dds_runtime_root_fix_repair_20260917/RESULTS.md`
- `docs/validation/dds_runtime_root_fix_repair_20260917/analysis.json`
- `docs/validation/dds_runtime_root_fix_repair_20260917/provenance.csv`

Separate:
1. `FACTS`
2. `DERIVED DIAGNOSIS`
3. `IMPLEMENTATION`
4. `LUNA INTERPRETATION`

Include exact hashes for candidate source, built simulator, probe, generated DDS support artifact, effective configuration, cycle A/B logs/evidence, and host liveness/cleanup decisions.

<!-- ATLAS_HOST_EXPERIMENT
{"schema_version":1,"command":["bash","example/cpp/scripts/dds_runtime_root_smoke.sh","--domain-id","220","--run-dir","example/cpp/experiments/_runs/dds_runtime_root_fix_repair_20260917/smoke"],"domain_id":220,"run_dir":"example/cpp/experiments/_runs/dds_runtime_root_fix_repair_20260917/smoke","timeout_s":480,"environment":{"LD_LIBRARY_PATH":"/home/che/dev/go2-workspace/current/simulate/mujoco/lib"}}
ATLAS_HOST_EXPERIMENT -->
