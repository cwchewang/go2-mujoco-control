# Canonical clean-baseline integration and legacy isolation

Mode: `engineering-correctness / no-live / canonicalization`

Exact main parent: `041c36c499ff24ab6c8edf74fa6283e0ba923db6`
Validated research result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`
Validated live candidate: `0009b5fbd1e962e38135922da61245a99b522aab`
Clean-baseline P0 source/reference: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`
DDS root-fix accepted result: `2eb92bc62be6fba2dee26ac9229520d8835c6246`

## Purpose

The validated research chain has now established two accepted facts:

1. the repository-owned DDS/exact-source host runtime can start deterministically on domain 220; and
2. the P0 clean baseline reproduced the frozen flat trot for 64/64 cycles at the preregistered low speed, with no clean-target rejection, strict WBC/QP rejection, hard/emergency stop, or gross tracking/stability failure.

However protected `main` is still on a divergent history and does not yet contain the validated clean baseline as the canonical foundation. The goal of this task is to make `main`-derived code structurally clean and ready to become the long-term research base without importing the entire exploratory research history.

This task authorizes NO live MuJoCo/DDS locomotion execution.

## Critical integration rule

Do **not** merge or cherry-pick the entire research branch/history onto main.

The research chain and current main diverged after an older merge base. Treat the accepted commits above as a **reference tree and evidence source**, not as history to transplant wholesale.

Starting from this task branch (which is based on current protected main), inspect the exact accepted implementation and port only the minimal coherent code, tests, launch/runtime support, and final accepted evidence needed for the canonical baseline.

Do not bring intermediate failed task documents, obsolete experiment patches, V1/V2 known-step logic as active architecture, or temporary closeout/recovery scaffolding into the canonical surface unless a file is independently required by current main.

## Canonical control invariants

The integrated clean baseline must make these rules true by construction and tests, not merely by convention:

1. **Planner/foot target identity:** a clean-mode requested foot target is either accepted exactly or rejected. No workspace clamp, iterative shrink, or downstream target mutation may silently replace it.
2. **Authoritative joint limits:** clean target acceptance uses the actual Go2/MuJoCo joint limits and direct IK feasibility.
3. **Strict optimizer acceptance:** clean ID-WBC motion accepts only a genuinely accepted constrained QP result. Equality residual alone may not promote a failed solver result to success.
4. **Correct swing acceleration:** swing task acceleration includes the `Jdot*qdot` term.
5. **No post-optimizer actuation overlays:** after the accepted clean WBC/QP result, legacy lean/force/direct-propulsion/Cartesian-stance or similar torque overlays must not alter the command. Only the explicit final torque safety envelope may remain.
6. **Final command identity:** the LowCmd emitted in clean mode must be traceable to the accepted clean result plus the explicit finite/ramp/torque safety envelope.
7. **Fail closed:** clean target or strict WBC failure must safe-hold/stop according to the existing clean design; it must not fall back to legacy clamp or legacy controller behavior.
8. **Cartesian-world incompatibility:** clean baseline and the old Cartesian-world path remain mutually exclusive and fail closed at CLI/config validation.

## Legacy isolation

The repository may retain historical/legacy code where removal would create unnecessary compatibility risk, but it must be structurally isolated from the canonical research path.

Required outcomes:

- The clean baseline execution path must not invoke `ClampFootToHipWorkspace`, `AllLegInverseKinematicsClamped`, or any equivalent silent target mutation.
- Legacy post-WBC torque overlays must be unreachable once the clean path has produced its final accepted command.
- Historical helpers should be clearly labeled/contained as legacy and must not be the default extension point for new Phase-2 work.
- Any future **terrain actuation/planner execution** path must be required to enter through the clean baseline contract. Existing sensor-only/shadow observation may remain observer-only if it cannot actuate.
- Add a fail-closed guard/test so new Phase-2 actuation cannot accidentally route through the legacy clamp/overlay stack.
- Do not simply delete useful historical code if a smaller explicit isolation boundary is clearer and safer.

## Canonical DDS and exact-source runtime

Port the accepted repository-owned runtime from the validated reference if not already present on main:

- deterministic tracked-source DDS support artifact generation;
- fail-closed DDS shared-memory cleanup/inspection behavior;
- canonical `run_trot.sh` DDS integration;
- exact-source host build wrapper for simulator/controller;
- read-only LowState probe and relevant focused tests where they are part of the accepted runtime;
- removal of ambient `/home/che/dds_base4000_preload.so` or hidden shell state as authority.

Preserve current main's newer Atlas worker/dispatcher infrastructure. Do not regress or replace it with older research-branch copies.

## Evidence canonicalization

Bring into the main-derived integration only the small, final accepted evidence needed to support the baseline claim. At minimum preserve or recreate canonical records that identify:

- accepted DDS root-fix result `2eb92bc62be6fba2dee26ac9229520d8835c6246`;
- accepted flat reproduction result `8b189c1bd7dab761c014f1db98e1223f3d73120d`;
- exact validated live candidate `0009b5fbd1e962e38135922da61245a99b522aab`;
- frozen command/parameters;
- core measured result: 64/64 cycles, nominal 0.1516666667 m/s, measured regression speed about 0.153806 m/s, and zero primary rejection/safety counts;
- provenance pointers/hashes sufficient to locate and audit the original accepted evidence.

Prefer copying the final accepted closeout/provenance/host-record files or writing one concise canonical evidence record over importing every intermediate task and protocol-failure document.

Update `CURRENT.md`, `docs/ARCHITECTURE.md`, `docs/CODE_GUIDE.md`, or the smallest appropriate canonical docs so future work clearly starts from the clean baseline rather than V1/V2 patch history.

## Canonical extension seam for terrain research

Create or document one obvious extension boundary for the next kinematics-aware terrain swing planner:

`gait/foothold + predicted body/hip state -> clean swing planner -> exact foot targets -> direct IK feasibility -> strict WBC -> final safety envelope`

Do not implement the new terrain planner in this task. The objective is to make it difficult to extend the wrong legacy seam.

## Validation

No live run is authorized.

Perform all practical static/offline/build validation, including at minimum:

- portable repository checks;
- focused clean-baseline unit/contract tests;
- direct-IK/joint-limit tests;
- strict ID-WBC tests including solver rejection and swing `Jdot*qdot` behavior;
- clean CLI incompatibility checks;
- tests proving clean mode bypasses legacy clamp and post-WBC overlays;
- DDS runtime focused tests, including fail-closed cleanup behavior;
- exact-source wrapper syntax/contract checks;
- practical CTest set and MuJoCo-backed rigid-body/ID-WBC tests when available without launching a live simulator/controller pair;
- `git diff --check`.

If a historical test conflicts with the accepted clean invariants, determine whether the test is legacy-specific and isolate it rather than weakening the invariant.

## Required closeout

Write:

- `docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md`
- `docs/validation/canonical_clean_baseline_integration_20260917/provenance.csv`

The result must separate:

1. `FACTS` — exact main parent, accepted reference commits, actual ported files and tests;
2. `INVARIANT AUDIT` — each of the eight canonical control invariants with source/test evidence;
3. `LEGACY ISOLATION` — what remains and why it cannot mutate the canonical path;
4. `CANONICAL SURFACE` — exact commands/files future Phase-2 work should use;
5. `LUNA INTERPRETATION` — proposed classification, reviewable by Sol.

Use one primary classification:

- `CANONICAL_CLEAN_BASELINE_READY` — minimal validated implementation is coherently integrated on current-main ancestry, invariants/tests pass, accepted evidence is preserved, and legacy cannot silently enter the clean path;
- `CANONICAL_INTEGRATION_INCOMPLETE` — the accepted implementation cannot yet be ported without unresolved conflict or an invariant remains unproven;
- `PROTOCOL_FAILURE` — task execution/evidence is invalid.

Do not perform a live experiment and do not claim repeatability beyond the already accepted single formal flat reproduction. Repeatability will be tested only after this integration is merged to protected main.
