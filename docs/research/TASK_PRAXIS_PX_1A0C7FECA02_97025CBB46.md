# Praxis Task px_1a0c7feca02_97025cbb46

Mode: `scientific`
Project: `go2-mujoco-control`
Repository: `cwchewang/go2-mujoco-control`
Approval boundary: `none`

## Objective

Design and freeze the offline specification for Go2 Substrate Gate 0 benchmark v0, so MJPC and the published Go2 RL capability baseline can later be compared on one auditable MuJoCo protocol before any live capability runs.

## Context paths

- AGENTS.md
- CURRENT.md
- docs/research/SOP.md
- docs/ARCHITECTURE.md
- docs/CODE_GUIDE.md
- docs/validation/PHASE1_BENCHMARK_FREEZE_2026-08-24.md
- docs/research/TASK_CANONICAL_CLEAN_BASELINE_INTEGRATION_20260917.md
- docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md
- example/cpp/CMakeLists.txt
- example/cpp/scripts/README.md

## Instructions

- Offline benchmark-design checkpoint only; do not launch simulator/controller pairs or consume any scientific attempt.
- Start from protected-main ancestry b1cec66f446c34e850c9caeeac82de52805a3889 and follow AGENTS.md plus docs/research/SOP.md.
- Inventory existing Go2 model, terrain/scene assets, task/runner/analyzer surfaces, and existing flat/step/stairs/obstacle support. Distinguish reusable assets from missing adapters.
- Define benchmark v0 around shared Go2+MuJoCo model semantics, common task goals, terrain families, success/failure taxonomy, resource metrics, provenance fields, and deterministic run naming.
- Support later MJPC/iLQR smoke and published Go2 RL checkpoint smoke. DIAL/MPPI is only a later diagnostic challenger slot.
- Keep the sealed Raibert+SRBD+WBC clean baseline as legacy regression/reference only.
- Do not invent exact terrain geometry or thresholds unsupported by repository assets. Derive from source/scene geometry where possible; list unresolved values explicitly for Sol review.
- Produce a concise formal design/task document under docs/research/ and benchmark-v0 specification under docs/validation/ or established equivalent, with no-live validation.
- Do not change controller/planner behavior, scene geometry, scientific thresholds, runtime semantics, or GitHub workflows.

## Constraints

- No live MuJoCo/DDS locomotion execution.
- No controller/planner/runtime-semantic mutation.
- No tuning.
- No raw evidence deletion/renaming.
- No GitHub workflow changes.
- Ungrounded values must be marked unresolved for Sol.

## Allowed mutations

- docs/research/
- docs/validation/
- CURRENT.md

## Frozen parameters

```json
{
  "base_sha": "b1cec66f446c34e850c9caeeac82de52805a3889",
  "capability_baseline": "published Go2 RL checkpoint",
  "default_backend": "MJPC/iLQR whole-body MPC",
  "diagnostic_challenger": "DIAL/MPPI",
  "gate": "SUBSTRATE_GATE_0",
  "legacy_baseline_role": "regression/reference only",
  "live_authorized": false
}
```

## Resource budget

```json
{
  "cpu_slots": 2,
  "gpu_count": 0,
  "memory_gb": 8.0,
  "wall_time_seconds": 1200
}
```

## Attempt policy

```json
{
  "max_scientific_attempts": 0,
  "retry_preflight": true,
  "scientific_boundary": "No live scientific capture is authorized in this design task."
}
```

## Approval policy

```json
{
  "reason": null,
  "required_before": "none"
}
```

## Required evidence

- Source-derived inventory of reusable robot/terrain/task/analysis assets.
- Benchmark v0 protocol/spec with common goals, terrain families, success/failure semantics, resource/provenance fields, and backend adapter boundaries.
- Explicit unresolved decisions requiring Sol review.
- No-live validation proving only allowed documentation surfaces changed.
- Exact commit/branch and changed paths.

## Stop rule

Stop before any simulator/controller live run, controller/scene semantic edit, or unsupported threshold/geometry guess.

## Closeout schema

- FACTS
- BENCHMARK_V0
- ASSET_GAPS
- UNRESOLVED_FOR_SOL
- NO_LIVE_VALIDATION
- NEXT_GATE

## Frozen TaskSpec

The following machine-readable block is the canonical task request.

```json
{
  "allowed_mutations": [
    "docs/research/",
    "docs/validation/",
    "CURRENT.md"
  ],
  "approval_policy": {
    "reason": null,
    "required_before": "none"
  },
  "attempt_policy": {
    "max_scientific_attempts": 0,
    "retry_preflight": true,
    "scientific_boundary": "No live scientific capture is authorized in this design task."
  },
  "capability": null,
  "capability_request": null,
  "closeout_schema": [
    "FACTS",
    "BENCHMARK_V0",
    "ASSET_GAPS",
    "UNRESOLVED_FOR_SOL",
    "NO_LIVE_VALIDATION",
    "NEXT_GATE"
  ],
  "constraints": [
    "No live MuJoCo/DDS locomotion execution.",
    "No controller/planner/runtime-semantic mutation.",
    "No tuning.",
    "No raw evidence deletion/renaming.",
    "No GitHub workflow changes.",
    "Ungrounded values must be marked unresolved for Sol."
  ],
  "context_paths": [
    "AGENTS.md",
    "CURRENT.md",
    "docs/research/SOP.md",
    "docs/ARCHITECTURE.md",
    "docs/CODE_GUIDE.md",
    "docs/validation/PHASE1_BENCHMARK_FREEZE_2026-08-24.md",
    "docs/research/TASK_CANONICAL_CLEAN_BASELINE_INTEGRATION_20260917.md",
    "docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md",
    "example/cpp/CMakeLists.txt",
    "example/cpp/scripts/README.md"
  ],
  "frozen_parameters": {
    "base_sha": "b1cec66f446c34e850c9caeeac82de52805a3889",
    "capability_baseline": "published Go2 RL checkpoint",
    "default_backend": "MJPC/iLQR whole-body MPC",
    "diagnostic_challenger": "DIAL/MPPI",
    "gate": "SUBSTRATE_GATE_0",
    "legacy_baseline_role": "regression/reference only",
    "live_authorized": false
  },
  "instructions": [
    "Offline benchmark-design checkpoint only; do not launch simulator/controller pairs or consume any scientific attempt.",
    "Start from protected-main ancestry b1cec66f446c34e850c9caeeac82de52805a3889 and follow AGENTS.md plus docs/research/SOP.md.",
    "Inventory existing Go2 model, terrain/scene assets, task/runner/analyzer surfaces, and existing flat/step/stairs/obstacle support. Distinguish reusable assets from missing adapters.",
    "Define benchmark v0 around shared Go2+MuJoCo model semantics, common task goals, terrain families, success/failure taxonomy, resource metrics, provenance fields, and deterministic run naming.",
    "Support later MJPC/iLQR smoke and published Go2 RL checkpoint smoke. DIAL/MPPI is only a later diagnostic challenger slot.",
    "Keep the sealed Raibert+SRBD+WBC clean baseline as legacy regression/reference only.",
    "Do not invent exact terrain geometry or thresholds unsupported by repository assets. Derive from source/scene geometry where possible; list unresolved values explicitly for Sol review.",
    "Produce a concise formal design/task document under docs/research/ and benchmark-v0 specification under docs/validation/ or established equivalent, with no-live validation.",
    "Do not change controller/planner behavior, scene geometry, scientific thresholds, runtime semantics, or GitHub workflows."
  ],
  "mode": "scientific",
  "objective": "Design and freeze the offline specification for Go2 Substrate Gate 0 benchmark v0, so MJPC and the published Go2 RL capability baseline can later be compared on one auditable MuJoCo protocol before any live capability runs.",
  "project": {
    "profile_path": ".atlas/project.json",
    "project_id": "go2-mujoco-control",
    "repository": "cwchewang/go2-mujoco-control"
  },
  "required_evidence": [
    "Source-derived inventory of reusable robot/terrain/task/analysis assets.",
    "Benchmark v0 protocol/spec with common goals, terrain families, success/failure semantics, resource/provenance fields, and backend adapter boundaries.",
    "Explicit unresolved decisions requiring Sol review.",
    "No-live validation proving only allowed documentation surfaces changed.",
    "Exact commit/branch and changed paths."
  ],
  "resources": {
    "cpu_slots": 2,
    "gpu_count": 0,
    "memory_gb": 8.0,
    "wall_time_seconds": 1200
  },
  "schema_version": 1,
  "stop_rule": "Stop before any simulator/controller live run, controller/scene semantic edit, or unsupported threshold/geometry guess."
}
```

<!-- PRAXIS_TASK_SPEC
{"allowed_mutations":["docs/research/","docs/validation/","CURRENT.md"],"approval_policy":{"reason":null,"required_before":"none"},"attempt_policy":{"max_scientific_attempts":0,"retry_preflight":true,"scientific_boundary":"No live scientific capture is authorized in this design task."},"capability":null,"capability_request":null,"closeout_schema":["FACTS","BENCHMARK_V0","ASSET_GAPS","UNRESOLVED_FOR_SOL","NO_LIVE_VALIDATION","NEXT_GATE"],"constraints":["No live MuJoCo/DDS locomotion execution.","No controller/planner/runtime-semantic mutation.","No tuning.","No raw evidence deletion/renaming.","No GitHub workflow changes.","Ungrounded values must be marked unresolved for Sol."],"context_paths":["AGENTS.md","CURRENT.md","docs/research/SOP.md","docs/ARCHITECTURE.md","docs/CODE_GUIDE.md","docs/validation/PHASE1_BENCHMARK_FREEZE_2026-08-24.md","docs/research/TASK_CANONICAL_CLEAN_BASELINE_INTEGRATION_20260917.md","docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md","example/cpp/CMakeLists.txt","example/cpp/scripts/README.md"],"frozen_parameters":{"base_sha":"b1cec66f446c34e850c9caeeac82de52805a3889","capability_baseline":"published Go2 RL checkpoint","default_backend":"MJPC/iLQR whole-body MPC","diagnostic_challenger":"DIAL/MPPI","gate":"SUBSTRATE_GATE_0","legacy_baseline_role":"regression/reference only","live_authorized":false},"instructions":["Offline benchmark-design checkpoint only; do not launch simulator/controller pairs or consume any scientific attempt.","Start from protected-main ancestry b1cec66f446c34e850c9caeeac82de52805a3889 and follow AGENTS.md plus docs/research/SOP.md.","Inventory existing Go2 model, terrain/scene assets, task/runner/analyzer surfaces, and existing flat/step/stairs/obstacle support. Distinguish reusable assets from missing adapters.","Define benchmark v0 around shared Go2+MuJoCo model semantics, common task goals, terrain families, success/failure taxonomy, resource metrics, provenance fields, and deterministic run naming.","Support later MJPC/iLQR smoke and published Go2 RL checkpoint smoke. DIAL/MPPI is only a later diagnostic challenger slot.","Keep the sealed Raibert+SRBD+WBC clean baseline as legacy regression/reference only.","Do not invent exact terrain geometry or thresholds unsupported by repository assets. Derive from source/scene geometry where possible; list unresolved values explicitly for Sol review.","Produce a concise formal design/task document under docs/research/ and benchmark-v0 specification under docs/validation/ or established equivalent, with no-live validation.","Do not change controller/planner behavior, scene geometry, scientific thresholds, runtime semantics, or GitHub workflows."],"mode":"scientific","objective":"Design and freeze the offline specification for Go2 Substrate Gate 0 benchmark v0, so MJPC and the published Go2 RL capability baseline can later be compared on one auditable MuJoCo protocol before any live capability runs.","project":{"profile_path":".atlas/project.json","project_id":"go2-mujoco-control","repository":"cwchewang/go2-mujoco-control"},"required_evidence":["Source-derived inventory of reusable robot/terrain/task/analysis assets.","Benchmark v0 protocol/spec with common goals, terrain families, success/failure semantics, resource/provenance fields, and backend adapter boundaries.","Explicit unresolved decisions requiring Sol review.","No-live validation proving only allowed documentation surfaces changed.","Exact commit/branch and changed paths."],"resources":{"cpu_slots":2,"gpu_count":0,"memory_gb":8.0,"wall_time_seconds":1200},"schema_version":1,"stop_rule":"Stop before any simulator/controller live run, controller/scene semantic edit, or unsupported threshold/geometry guess."}
PRAXIS_TASK_SPEC -->

## Praxis ContextPack

Trusted dispatch-time context. Runtime facts may add to this; they must not silently replace these frozen repository facts.

- Project: `go2-mujoco-control`
- Repository: `cwchewang/go2-mujoco-control`
- Default branch: `main`
- Default branch SHA: `b1cec66f446c34e850c9caeeac82de52805a3889`
- Project profile raw-file SHA-256: `aa8158ff9e7f267a4a89f8b73e3b81d702c8c12fe20428f140d9e43ff7d80f77`
- Project profile canonical-JSON SHA-256: `4d42d51738b60efbf25584f03f27e1800f3f342fe026369ef3a47f9c20a1b258`

### Instruction: `AGENTS.md`

SHA-256: `0e5f638d56a9bf10fd1a1718a346e46c17cddcfdd3a7e82dc6985d495aecdcec`

```text
# Go2 repository rules

`main` is the stable code line and long-term route. The active research
frontier may live on a separate `research/*` branch. This file contains
repository guardrails; it is not a scientific plan or current-status report.

## Task discovery bootstrap

Before accepting, declining, or executing any task from a local worktree, first
refresh the remote source of truth:

1. run `git fetch origin --prune`;
2. read `origin/main:CURRENT.md` (for example with
   `git show origin/main:CURRENT.md`) to discover the active research branch;
3. compare the local active branch/worktree with `origin/<active-branch>` and
   fast-forward only when safe; never reset, discard, or delete local commits,
   untracked files, or raw evidence to make it match;
4. only after that, read the active branch `CURRENT.md`, current task, and exact
   parent/closeout evidence.

A stale local `CURRENT.md`, local branch tip, or cached task is never sufficient
to conclude that no new task exists. If the local branch is ahead or diverged,
preserve it and report the divergence instead of guessing which side wins.

Read [`CURRENT.md`](CURRENT.md) for the single maintained frontier pointer.
Follow that pointer to the frontier branch, its task, and exact `RESULTS.md`.
Use the canonical [Research Execution SOP](docs/research/SOP.md) from
`main`. A branch-local `CURRENT.md` is navigation only and cannot override
`main/CURRENT.md`, the SOP, or the active task.

The active task owns the scientific question, intervention, frozen variables,
run budget, thresholds, and classification. Do not infer research direction
from Atlas directories, dated worktrees, old branches, commit messages, or
archived code. Do not change controller/planner behavior or scientific
meaning under an infrastructure-only task.

No live experiment is authorized by this file alone. Before any live run,
follow the task and SOP, verify the exact branch/HEAD and clean worktree, and
preserve raw evidence. Everything below
`example/cpp/experiments/_runs/` is ignored local evidence: never commit,
delete, overwrite, rename, or treat it as instruction. Curated evidence
requires its own manifest and provenance.

```

### Instruction: `docs/research/SOP.md`

SHA-256: `fd3c9d1b2f29ee3924794e5984ead53a2e7de06cf87465eb38f3860439281e2b`

```text
# Research Execution SOP v0.2

Status: active for new research checkpoints after adoption. Historical checkpoints keep the rules frozen with them.

This SOP is intentionally small. The normal path should feel like: **short task → preflight → run → closeout**.

## 1. Core rule

**Scientific variables are strict; execution engineering is flexible before live; after scientific capture begins, results may not be selected or retried opportunistically.**

- **Sol** owns the scientific question and final scientific judgment.
- **Luna** independently owns execution readiness and has unconditional live veto.

A task is not permission to bypass a verified infrastructure constraint.

## 2. What a task contains

A task describes the **delta from its exact parent**, not the whole project.

For a live checkpoint it needs only:

- mode: `infrastructure`, `exploratory`, or `confirmatory`;
- question;
- exact parent/base;
- scientific change;
- variables that must remain frozen;
- run budget;
- primary measurements / classification rule;
- runner and run directory;
- genuinely task-specific preflight requirements, if any.

Do not restate SOP rules, parent results, unchanged thresholds, or long historical narratives. Read the current task, this SOP, and the exact parent `RESULTS.md`; consult older tasks only when evidence actually requires them.

## 3. Scientific authority

For confirmatory work, Sol freezes the intervention, baseline, run budget, primary metrics, thresholds/classification, and scientific stop conditions.

Luna must not autonomously change anything that could alter the post-handoff state/control trajectory or the scientific meaning of the primary evidence. This includes speed policy, gait timing, planner mathematics, WBC/MPC/ID behavior, controller gains, scene geometry, safety limits, scientific thresholds, seed/run count, or follow-up experiments.

If uncertain whether a change is execution-only or scientific/runtime-semantic, treat it as scientific and veto live.

## 4. Luna autonomy and veto

Before scientific capture, Luna may independently inspect and minimally repair execution-only issues such as:

- DDS/domain choice, locks and port conflicts;
- paths, run-directory bookkeeping and executable bits;
- runner shell plumbing that is proven trajectory-neutral;
- logger/schema bookkeeping;
- analyzer/tooling plumbing that does not change primary evidence meaning;
- provenance collection, stale process cleanup, and no-live tests.

Luna may add no-live tests without asking.

If the task conflicts with verified source semantics, geometry, protocol limits, accepted evidence, or preflight, Luna must veto rather than weaken an existing guard to obey the task.

## 5. Preflight

Every live run must pass `tools/research/preflight.py` immediately before launch.

Always check:

- exact branch/HEAD and clean worktree;
- runner existence/syntax and actual DDS domain;
- DDS/RTPS port legality, selected safe policy and free lock;
- fresh run directory;
- no stale simulator/controller/runner process;
- task-required files/hashes/tests.

Use `--diff-base <accepted-ref>` whenever an accepted parent/baseline exists. Preflight auto-detects changed execution surfaces from Git diff; `--changed-surface` is only an override/addition.

Change-triggered checks:

- runtime/schema/scene change → at least one relevant no-live/build test;
- schema change → schema regression test;
- primary analyzer semantics change → parser/fixture test;
- runner change → record a baseline runner diff summary and inspect the actual Git diff;
- geometry-dependent scientific gate change → re-derive it from source/scene geometry.

### Sol review gate

Second Sol review is required only when the committed change can alter either:

1. the post-handoff state/control trajectory; or
2. the meaning/mapping/classification of primary evidence.

Runtime, scene and schema changes trigger this automatically. A runner or analyzer change triggers it only when its actual semantics meet one of those two conditions; Luna must pass `--requires-sol-review` in that case.

Pure paths, output locations, report rendering, bookkeeping, or presentation-only analysis changes do not require redundant Sol review.

When review is required, the exact reviewed SHA must equal the live HEAD via `--approved-head`.

## 6. Attempt boundary and retry

A scientific attempt is consumed at the first valid **post-handoff state/control sample** used by the experiment.

- **Prelaunch failure:** no attempt consumed; Luna may fix execution-only issues and rerun preflight.
- **Boot failure before that sample:** no scientific attempt consumed. One automatic recovery launch is allowed only if the cause is proven execution-only, failed artifacts are preserved, scientific/runtime semantics are unchanged, and preflight passes again.
- **Scientific capture started:** run budget is consumed. No autonomous retry, replacement run, domain change, or tuning.

Scientific gate failures stop; infrastructure gate failures before capture may be repaired in the same checkpoint.

## 7. Evidence

Once capture starts, raw artifacts are immutable. Do not overwrite, normalize, or hand-edit raw evidence.

Prefer deterministic offline salvage over rerunning. A repair is scientifically usable only when:

- raw bytes remain unchanged;
- the mapping/repair is unique;
- it follows from frozen runtime source/protocol rather than outcome preference;
- independent semantic invariants validate it;
- derivation and provenance are recorded.

Do not preregister a guessed bug shape when uniqueness/source-grounded recoverability is the real requirement.

Historical conclusions are append-only; a later correction may supersede an interpretation without erasing it.

## 8. Failure triage

After a failed run, identify the earliest failed boundary before designing another experiment:

1. `execution`
2. `evidence`
3. `causal`
4. `scientific`

Do not invent a new generic classification label for every infrastructure failure. Record the boundary plus a specific `reason_code`; scientific labels remain task-specific.

## 9. Exploratory vs confirmatory

- `infrastructure`: tooling/repair only; no scientific claim.
- `exploratory`: bounded search/debugging authorized in advance; useful for design, not confirmatory evidence.
- `confirmatory`: intervention, run budget, thresholds and classification frozen before live.

Do not force tuning into repeated fake one-run confirmatory checkpoints. Explore first when necessary, then freeze and validate.

## 10. Branches and outputs

Create a new research branch for a new scientific question, new live attempt, or runtime-semantic change.

Pure offline correction, evidence salvage, analyzer repair, or additional derived analysis may continue on the same research branch when raw evidence and scientific design are unchanged. Append a new commit/closeout and mark supersession when needed.

Default closeout artifacts are only:

- `RESULTS.md`
- `analysis.json`
- `provenance.csv`

Create extra CSV/tables only when they are actual evidence needed to audit that checkpoint.

Provenance should hash what matters to the conclusion: raw evidence, scene/model/config where relevant, and exact runtime/source/binary identity. Do not hash every derived report by ritual.

## 11. Lessons already encoded

This SOP specifically addresses failures already seen in this project:

- DDS domain 233 → actual RTPS/domain preflight + Luna veto;
- missing `--wall-clock-motion` → runner comparison against accepted baseline;
- invalid `base x < 0.65` pre-step gate → source/scene-derived geometry review;
- 780/776 CSV mismatch → schema regression test before live;
- guessed empty-token recovery rule → general uniqueness/source-invariant evidence recovery;
- unnecessary branch/checkpoint churn → execution repair before capture and same-branch offline corrections.

## 12. Authority and version

For checkpoints adopting this SOP:

1. frozen scientific delta in the current task;
2. this SOP for execution/veto/retry/evidence rules;
3. exact parent/baseline evidence;
4. older history as needed.

`PHASE1_AGENT_CONTRACT.md` remains historical authority only for checkpoints created under it.

Current version: **v0.2**. Git history is the changelog; no separate release ceremony is required.

```

### Instruction: `CURRENT.md`

SHA-256: `aa8a33c4ded00a3d79c609f448be89a260952ada27f53baef12b1dfbbd1429dd`

```text
# Go2 repository bootstrap

`main` is the stable code line and long-term route. The active research
frontier may live on a separate `research/*` branch and is not implied by
the code or history on `main`.

This file is the only maintained repository-level frontier pointer. It is not
a scientific plan. The active task owns the research question and design; the
canonical execution rules live in [`docs/research/SOP.md`](docs/research/SOP.md).

## Active research frontier

Update only this block when the frontier changes. The dated branch/task below
are a pointer value, not a permanent architecture decision.

- Branch: [`research/canonical-clean-baseline-integration-20260917`](https://github.com/kairoi-k/go2-mujoco-control/tree/research/canonical-clean-baseline-integration-20260917)
- Branch navigation: [`CURRENT.md`](https://github.com/kairoi-k/go2-mujoco-control/blob/research/canonical-clean-baseline-integration-20260917/CURRENT.md)
- Task: [`TASK_CANONICAL_CLEAN_BASELINE_INTEGRATION_20260917.md`](https://github.com/kairoi-k/go2-mujoco-control/blob/research/canonical-clean-baseline-integration-20260917/docs/research/TASK_CANONICAL_CLEAN_BASELINE_INTEGRATION_20260917.md)
- Expected closeout: [`RESULTS.md`](https://github.com/kairoi-k/go2-mujoco-control/blob/research/canonical-clean-baseline-integration-20260917/docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md)

```

### Instruction: `docs/ARCHITECTURE.md`

SHA-256: `09057f74352dc251fd6feecf7cada2c70a469175c8c668c2d79369217580c6ca`

```text
# Architecture

This document maps the code; it does not define research status or the next
task. For Phase 2, read [`CURRENT.md`](../CURRENT.md) first.

## Runtime data flow

The MuJoCo process and 500 Hz C++ controller communicate through the Unitree
SDK2 DDS interface.

```text
MuJoCo -> LowState / lidar -> state snapshot and filtering
                                  |
requested velocity -> Phase 1 shaper -> gait/foothold targets
                                           |
                         clean target contract + direct IK feasibility
                                           |
                                        SRBD MPC
                                           |
                              strict 18-DoF ID-WBC acceptance
                                           |
                              final finite/ramp/torque envelope
                                           |
                                      LowCmd -> MuJoCo
```

The sensor-only terrain path derives a terrain model, feasibility results, and
a plan from lidar. On the current line it may be logged and analyzed, but it
does not alter gait, MPC, WBC, contact policy, or velocity. There is no
production terrain-actuation path.

## Active modules

| Area | Primary files | Responsibility |
|---|---|---|
| CLI and lifecycle | `example/cpp/trot/trot_cli.*`, `trot_experiment_lifecycle.cpp` | configuration, DDS, startup, shutdown |
| Control loop | `example/cpp/trot/trot_experiment_control.cpp` | state snapshot, phase execution, command publication |
| Gait | `example/cpp/trot/trot_experiment_gait.cpp`, `example/cpp/gait/*` | running-trot phase, footholds, velocity targets |
| Terrain interfaces | `example/cpp/terrain/*` | sensor-derived model, feasibility, immutable plan interface |
| MPC and WBC | `example/cpp/trot/trot_experiment_wbc.cpp`, `example/cpp/wbc/*` | SRBD preview and inverse-dynamics control |
| Kinematics | `example/cpp/kinematics/*` | FK, IK, Jacobians, rigid-body model |
| Contact | `example/cpp/contact/*` | measured-contact filtering, wrench allocation, torque mapping |
| Timing | `example/cpp/trot/lockstep_*` | lockstep clock/writer diagnostics; not a realtime acceptance claim |
| Diagnostics | `example/cpp/trot/trot_experiment_diagnostics.cpp`, `trot_types.h` | limits, status, structured logs |
| Clean baseline contract | `example/cpp/wbc/clean_baseline.h`, `go2_inverse_kinematics.h`, `inverse_dynamics_wbc.h` | exact targets, authoritative limits, strict solver result, final command envelope |
| Canonical DDS runtime | `example/cpp/scripts/dds_runtime.sh`, `run_trot.sh`, `run_trot_exact_source.sh` | tracked support artifact, fail-closed cleanup, exact-source launch plumbing |
| Tests and analysis | `example/cpp/tests/`, `example/cpp/tools/` | unit/integration checks and protocol analyzers |

## Target Phase 2 planner

The active Stage C target adds `TerrainBelief` for estimated state, measured
contact, terrain freshness, and uncertainty. `TerrainFeasibility` remains the
hard-filter/candidate layer. A receding-horizon `TerrainPlanner` then jointly
optimizes future footholds, body/CoM references, touchdown/contact timing, and
swing duration. Its complete output is one atomic `TerrainExecutionState`
consumed by gait, SRBD-MPC, and ID-WBC.

The first implementation stays in running-trot topology and runs in
shadow/replay before actuation. The existing per-leg scorer is not the target
planner, and archived Stage-C code is not a design source. `CURRENT.md` owns
the ordered implementation and acceptance sequence.

## Phase 2 invariants

The Phase 1 shaper remains the only velocity authority. Planned contact and
force-supported measured contact remain separate. A future terrain execution
path must publish one immutable, time-indexed snapshot shared by gait, SRBD-MPC,
and ID-WBC; no consumer may invent its own timing, contact, or recovery state.
Any actuation-capable terrain planner must explicitly enable the clean baseline
contract and enter through `exact foot targets -> direct IK feasibility ->
strict WBC -> final safety envelope`. Sensor-only terrain remains observer-only.
The Cartesian-world and legacy clamp/overlay path is incompatible with
`--clean-baseline`.

The retained `example/cpp/leg_lift/` executable and multi-step configurations
are historical experiments. They are not a Phase 2 route or design source.
Removed crawl/three-contact code and Git history are not fallback
implementations.

## Repository boundaries

`simulate/` and `unitree_robots/go2/` remain close to the upstream Unitree
simulator. Research-specific model control lives in `example/cpp/`. Isaac Lab
RL and Kine2Go imitation live only in their companion repositories and are not
runtime dependencies here.

See [`CODE_GUIDE.md`](CODE_GUIDE.md) for source navigation,
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) for execution rules, and
[`../UPSTREAM_AND_CONTRIBUTIONS.md`](../UPSTREAM_AND_CONTRIBUTIONS.md) for
provenance.

```

### Instruction: `docs/CODE_GUIDE.md`

SHA-256: `b4fdc0e7c300f9278c47d406bb6e6783417c255c98973de15210b4ac4df447c8`

```text
# Code guide

This guide points contributors to the smallest relevant source area for common changes. The primary research implementation is under `example/cpp/`.
For current Phase 2 work, read [`../CURRENT.md`](../CURRENT.md) first; this file
only maps code and cannot define the route.

## Entry points

| Task | Start here |
|---|---|
| Read current Phase 2 route/status | `CURRENT.md`, then `AGENTS.md` and `docs/research/PHASE2_ACCEPTANCE.md` |
| Understand the runtime/control data flow | `docs/ARCHITECTURE.md` |
| Build or run the C++ stack | `example/cpp/README.md` |
| Change command-line configuration | `example/cpp/trot/trot_cli.*` |
| Change the canonical clean baseline | `example/cpp/wbc/clean_baseline.h`, `example/cpp/kinematics/go2_inverse_kinematics.h`, `example/cpp/wbc/inverse_dynamics_wbc.h`, `example/cpp/trot/trot_experiment_gait.cpp`, `trot_experiment_wbc.cpp`, `trot_experiment_control.cpp` |
| Change stand / walk / stop sequencing | `example/cpp/trot/trot_task.*`, `example/cpp/trot/trot_experiment_control.cpp` |
| Change gait phase or foot targets | `example/cpp/trot/trot_experiment_gait.cpp`, `example/cpp/gait/raibert_trot_kernel.h` |
| Change Raibert landing adjustment | `example/cpp/gait/raibert_footstep_planner.h` |
| Change contact-force allocation | `example/cpp/contact/contact_wrench_*` |
| Change centroidal wrench / foothold preview | `example/cpp/wbc/centroidal_wbc.h`, `example/cpp/gait/preview_footstep_horizon.h`, `example/cpp/contact/contact_wrench_qp.h`, `example/cpp/gait/footstep_mpc.h` |
| Change `--wbc-full` ID-WBC / SRBD MPC | `example/cpp/kinematics/go2_rigid_body.h`, `example/cpp/wbc/srbd_mpc.h`, `example/cpp/wbc/inverse_dynamics_wbc.h`, `example/cpp/wbc/dense_qp.h`, `example/cpp/trot/trot_experiment_wbc.cpp` |
| Change dynamics-informed feedforward | `example/cpp/trot/trot_experiment_wbc.cpp`, `example/cpp/trot/trot_true_dynamics.h` |
| Change safety gates / diagnostics | `example/cpp/trot/trot_experiment_diagnostics.cpp` |
| Change sensor-only terrain interfaces | `example/cpp/terrain/*`, `example/cpp/trot/trot_experiment_gait.cpp` |
| Change timing/lockstep diagnostics | `example/cpp/trot/lockstep_*`, `example/cpp/tests/test_lockstep_*` |
| Change canonical DDS/build plumbing | `example/cpp/scripts/dds_runtime.sh`, `run_trot.sh`, `run_trot_exact_source.sh`, `simulate/CMakeLists.txt`, `example/cpp/CMakeLists.txt` |
| Run Phase 2 B0 development checks | `example/cpp/scripts/run_phase2_b0_pair.sh`, `run_phase2_b0_fixed_pair.sh`; domains come from the holdout manifest |
| Inspect historical leg-lift / multi-step code | `example/cpp/leg_lift/*`; never use it as a Phase 2 route or design source |
| Inspect retained experiment evidence | `example/cpp/experiments/`, `example/cpp/experiments/CATALOG.md` |

## Trot controller

`real_trot_go2.cpp` is the executable entry point. Sequencing lives in `TrotTask`; the remaining `TrotExperiment` modules own DDS, gait, WBC, and diagnostics:

- `trot/trot_task.*` — stand / walk / stand / lie sequencer;
- `trot/trot_experiment_lifecycle.cpp` — initialization, DDS, shutdown;
- `trot/trot_experiment_gait.cpp` — velocity estimation and gait targets;
- `trot/trot_experiment_wbc.cpp` — contact-force / dynamics-informed feedforward;
- `trot/trot_experiment_diagnostics.cpp` — limits, quality gates, logging;
- `trot/trot_experiment_control.cpp` — 500 Hz control loop;
- `trot/trot_types.h` — shared configuration and diagnostic structures.

## Leg-lift controller

This standalone historical experiment is not a Phase 2 route or design source.
Its action-sequence implementation is split into:

- `leg_lift_cli.*` — CLI parsing;
- `leg_lift_lifecycle.cpp` — setup and lifecycle;
- `leg_lift_world.cpp` — world-frame feedback;
- `leg_lift_diagnostics.cpp` — logging and acceptance diagnostics;
- `leg_lift_control.cpp` — control phases and command publication;
- `leg_lift_types.h` — sequence types and constants.

## Supporting headers

- Kinematics: `example/cpp/kinematics/go2_forward_kinematics.h`, `go2_inverse_kinematics.h`, `go2_leg_jacobian.h`
- Gait: `example/cpp/gait/locomotion_kernel.h`, `raibert_trot_kernel.h`, `raibert_footstep_planner.h`, `preview_footstep_horizon.h`, `footstep_mpc.h`
- Contact / WBC: `example/cpp/contact/contact_*.h`, `contact_wrench_qp.h`, `example/cpp/wbc/dense_qp.h`, `wbc_runtime_gate.h`, `example/cpp/contact/go2_contact_torque_mapping.h`
- Terrain: `example/cpp/terrain/terrain_model.h`, `terrain_feasibility.h`, `terrain_motion_plan.h`, `terrain_planner.h`, `terrain_control_interface.h`
- Timing: `example/cpp/trot/lockstep_motion_clock.h`, `lockstep_writer_gate.h`
- Filtering / frames: `example/cpp/util/velocity_filter.h`, `motion_frame_utils.h`, `example/cpp/contact/contact_state_filter.h`

When a change can alter research semantics, record the affected configuration/evidence and follow [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

```

### Instruction: `docs/validation/PHASE1_BENCHMARK_FREEZE_2026-08-24.md`

SHA-256: `3ab47ab6921796678d3fc1416f797621509f5e4ac74548910aa79a0a2d8ba338`

```text
# Phase1 benchmark freeze

This is the frozen Phase1 reference for the terrain worktree. It is a
simulation-only result and does not claim hardware or sim-to-real performance.

- Source: `1b4d9b8fcf3dcfb63cee144c9871a235101713c9`
- Branch: `terrain/phase2-20260824T150934Z`
- Build: MuJoCo 3.3.6, simulator and C++ controller built in Ubuntu-22.04/WSL
- Tests: `ctest --test-dir example/cpp/build --output-on-failure` - 25/25
- Profile: `bash example/cpp/scripts/run_sustained_running.sh --headless`
- Analyzer: `python3 example/cpp/tools/analysis/analyze_sustained_running.py <run>`

| run | median m/s | good window s | roll/pitch P95 deg | aerial | pair sync min | stop P95 m/s |
|---|---:|---:|---:|---:|---:|---:|
| `phase1_freeze_running_r1_20260824` | 3.242725 | 61.402 | 2.821/2.288 | 0.293086 | 0.817057 | 0.004574 |
| `phase1_freeze_running_r2_20260824` | 3.227325 | 61.442 | 3.166/2.541 | 0.283184 | 0.799286 | 0.003563 |
| `phase1_freeze_running_r3_20260824` | 3.234687 | 61.422 | 2.778/2.308 | 0.291980 | 0.810059 | 0.003980 |

All three runs passed the unchanged strict analyzer. Terrain changes must
retain this reference as a separate flat-ground regression.

```

### Instruction: `docs/research/TASK_CANONICAL_CLEAN_BASELINE_INTEGRATION_20260917.md`

SHA-256: `7517923c1df410c54f51dab9626d5e8fc3a3b97f6b9b87c70c7a4a5b6f16bf9f`

```text
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

```

### Instruction: `docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md`

SHA-256: `0aac77c9064dfe9079f70dc01cfd0f970c9e7d7b59e2f44ae9080c9768d6fd42`

```text
# Canonical clean-baseline integration closeout

Date: `2026-09-17`

Task commit: `7ab6fbf6e08e57d0d6d1b536ab7870887ac602e7`

Exact main parent: `041c36c499ff24ab6c8edf74fa6283e0ba923db6`

Mode: `engineering-correctness / no-live / canonicalization`

Proposed Luna classification: `CANONICAL_CLEAN_BASELINE_READY`

## FACTS

- No simulator/controller pair or locomotion run was launched. Raw `_runs`
  evidence was not modified.
- The accepted reference commits were inspected as trees and evidence sources,
  not merged or cherry-picked as history:
  - P0 clean-baseline source/reference: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`;
  - accepted DDS root-fix result: `2eb92bc62be6fba2dee26ac9229520d8835c6246`;
  - validated flat result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`;
  - exact validated live candidate/wrapper source: `0009b5fbd1e962e38135922da61245a99b522aab`.
- The port is limited to the clean controller seams, focused tests, tracked DDS
  runtime/probe/exact-source plumbing, build-root portability, and canonical
  documentation. Historical task documents, intermediate recovery scaffolds,
  and full historical analysis were not imported.
- Clean controller implementation is in:
  `example/cpp/wbc/clean_baseline.h`,
  `example/cpp/kinematics/go2_inverse_kinematics.h`,
  `example/cpp/wbc/inverse_dynamics_wbc.h`,
  `example/cpp/trot/trot_experiment_gait.cpp`,
  `example/cpp/trot/trot_experiment_wbc.cpp`, and
  `example/cpp/trot/trot_experiment_control.cpp`.
- Canonical runtime implementation is in
  `example/cpp/scripts/dds_runtime.sh`, `run_trot.sh`,
  `run_trot_exact_source.sh`, `dds_runtime_root_smoke.sh`, and the read-only
  `apps/dds_lowstate_probe.cpp`; `example/cpp/CMakeLists.txt` and
  `simulate/CMakeLists.txt` accept explicit SDK roots.
- Accepted flat evidence remains externally auditable at the referenced
  closeout and host-record paths. Its frozen command and core result are
  preserved: `64/64` cycles, nominal `0.1516666667 m/s`, measured OLS speed
  about `0.153806 m/s`, and zero primary rejection/safety counts.
- Validation completed without live execution: full controller CTest `34/34`,
  including `test_dds_runtime`, `test_clean_baseline`,
  `test_go2_inverse_kinematics`, `test_inverse_dynamics_wbc`,
  `test_terrain_interfaces`, and `test_lean_route_guard`; the simulator
  `test_lockstep` unit test also passed. The simulator-launch integration CTest
  was excluded by the no-live task boundary.
- `bash -n` passed for all canonical shell scripts and `git diff --check`
  passed. The required remote refresh was attempted but the linked worktree’s
  Git metadata rejected `FETCH_HEAD` writes as read-only; the supplied exact
  task ref, `HEAD`, `origin/main`, and accepted reference refs were verified
  read-only without changing Git metadata.

## INVARIANT AUDIT

1. **Planner/foot target identity — PASS.** Clean gait target construction
   calls `ResolveFootTargetsToJointPositions` with the requested targets and
   does not call the legacy clamped solver. The direct-IK rejection and
   non-mutation cases pass in `test_go2_inverse_kinematics` and
   `test_clean_baseline`.
2. **Authoritative joint limits — PASS.** Clean acceptance checks the Go2
   ranges represented in `unitree_robots/go2/go2.xml`, including distinct front
   and rear thigh ranges, after direct IK. The joint-range-invalid fixture is
   rejected without projection.
3. **Strict optimizer acceptance — PASS.** `require_qp_acceptance` rejects a
   failed constrained solve before its iterate can become output. The dense-QP
   rejection fixture and strict ID-WBC test pass; clean runtime failure clears
   solver/mapping acceptance and cannot reuse a stale result.
4. **Correct swing acceleration — PASS.** `AddSwingFootAccelerationTask`
   includes `Jdot*qdot` in the acceleration residual. The focused swing test
   checks both the gradient term and Hessian.
5. **No post-optimizer actuation overlays — PASS.** Clean
   `WriteMotorCommands` returns through the accepted torque plus the explicit
   final finite/ramp/absolute envelope. Legacy force, lean, Cartesian, and
   sprint overlays are enclosed by `!params_.clean_baseline`.
6. **Final command identity — PASS.** Clean LowCmd torque is sourced from the
   mapped accepted ID-WBC torque and passed only to
   `ApplyFinalTorqueSafetyEnvelope`; failed WBC uses a zero-feedforward safe
   hold rather than a legacy command path.
7. **Fail closed — PASS.** Direct target failure requests the existing stop
   sequence, strict WBC failure disables primary output, and clean command
   writing emits a zero-feedforward hold instead of falling back to legacy
   torque/position overlays. The route and contract tests cover these seams.
8. **Cartesian-world incompatibility — PASS.** CLI validation rejects
   `--clean-baseline --cartesian-world`, and `test_lean_route_guard` passes.

## LEGACY ISOLATION

- `AllLegInverseKinematicsClamped` and `ClampFootToHipWorkspace` remain only
  for compatibility and are explicitly labeled legacy. The clean target branch
  precedes both legacy paths and uses a const requested-target boundary.
- Cartesian-world is a separate CLI route and is fail-closed against clean
  mode. Its post-WBC behavior cannot be reached after clean mode is selected.
- Terrain observation remains sensor-only in the maintained runtime. The
  `TerrainPlannerConfig` actuation boundary now rejects any actuation-capable
  planner unless `clean_baseline_contract` is explicitly enabled; its focused
  test proves the rejection and the opt-in contract path.
- The legacy helpers were not deleted because existing compatibility callers
  and historical tests still depend on them. They are not the clean extension
  seam or default Phase-2 route.

## CANONICAL SURFACE

Future Phase-2 work should start from `CURRENT.md`, use the tracked DDS layer
through `example/cpp/scripts/run_trot.sh`, and extend only this contract:

`gait/foothold + predicted body/hip state -> clean swing planner -> exact foot targets -> direct IK feasibility -> strict WBC -> final safety envelope`

The clean controller entry is `real_trot_go2 ... --clean-baseline`; Cartesian
world and legacy terrain-actuation options remain separate or retired. Exact
source builds use `simulate/CMakeLists.txt` with `-DMUJOCO_ROOT` and
`example/cpp/CMakeLists.txt` with `-DGO2_MUJOCO_ROOT`. The read-only DDS probe
is `dds_lowstate_probe --domain-id N --interface lo`.

## LUNA INTERPRETATION

`CANONICAL_CLEAN_BASELINE_READY` is proposed because the minimal accepted clean
implementation is coherently integrated on current-main ancestry, all eight
control invariants have source and focused-test evidence, the accepted flat and
DDS records remain referenced with hashes, and legacy clamp/overlay entry is
explicitly isolated. This is an offline integration result. It does not claim
new repeatability or authorize a live run; repeatability remains a later task
after protected-main integration.

```

### Instruction: `example/cpp/CMakeLists.txt`

SHA-256: `6f9d85ffba28b9176b5b2b66ccf69c37605b793dbfe73128f0333ba444a944a4`; excerpt truncated

```text
cmake_minimum_required(VERSION 3.16)
project(stand_go2)
enable_testing()

list(APPEND CMAKE_PREFIX_PATH "/opt/unitree_robotics/lib/cmake")
find_package(unitree_sdk2 REQUIRED)
find_package(Eigen3 REQUIRED)

set(GO2_CPP_INCLUDE_DIRS
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/apps
    ${CMAKE_CURRENT_SOURCE_DIR}/trot
    ${CMAKE_CURRENT_SOURCE_DIR}/gait
    ${CMAKE_CURRENT_SOURCE_DIR}/kinematics
    ${CMAKE_CURRENT_SOURCE_DIR}/contact
    ${CMAKE_CURRENT_SOURCE_DIR}/wbc
    ${CMAKE_CURRENT_SOURCE_DIR}/util
    ${CMAKE_CURRENT_SOURCE_DIR}/leg_lift
    ${CMAKE_CURRENT_SOURCE_DIR}/terrain
)
include_directories(${GO2_CPP_INCLUDE_DIRS})

add_executable(stand_go2 apps/stand_go2.cpp)
target_link_libraries(stand_go2 unitree_sdk2)

add_executable(hold_pose_go2 apps/hold_pose_go2.cpp)
target_link_libraries(hold_pose_go2 unitree_sdk2)

add_executable(track_lowcmd_lowstate_go2 apps/track_lowcmd_lowstate_go2.cpp)
target_link_libraries(track_lowcmd_lowstate_go2 unitree_sdk2)

# Boot-only DDS transport probe.  It subscribes to rt/lowstate and never
# constructs a LowCmd publisher; the trusted host smoke uses it after the
# simulator's DDS-ready marker.
add_executable(dds_lowstate_probe apps/dds_lowstate_probe.cpp)
target_link_libraries(dds_lowstate_probe unitree_sdk2)

add_executable(single_leg_lift_go2 apps/single_leg_lift_go2.cpp)
target_link_libraries(single_leg_lift_go2 unitree_sdk2)

add_executable(real_leg_lift_go2
    leg_lift/real_leg_lift_go2.cpp
    leg_lift/leg_lift_cli.cpp
    leg_lift/leg_lift_lifecycle.cpp
    leg_lift/leg_lift_world.cpp
    leg_lift/leg_lift_diagnostics.cpp
    leg_lift/leg_lift_control.cpp
)
target_link_libraries(real_leg_lift_go2 unitree_sdk2)

add_executable(real_trot_go2
    trot/real_trot_go2.cpp
    trot/trot_cli.cpp
    trot/trot_task.cpp
    trot/trot_experiment_lifecycle.cpp
    trot/trot_experiment_gait.cpp
    trot/trot_experiment_wbc.cpp
    trot/trot_experiment_diagnostics.cpp
    trot/trot_experiment_control.cpp
)
target_link_libraries(real_trot_go2 unitree_sdk2 Eigen3::Eigen)

set(GO2_MUJOCO_ROOT
    "${CMAKE_CURRENT_SOURCE_DIR}/../../simulate/mujoco" CACHE PATH
    "MuJoCo SDK/runtime root used for the controller build")
set(_go2_mujoco_lib "${GO2_MUJOCO_ROOT}/lib/libmujoco.so")
set(_go2_mujoco_inc "${GO2_MUJOCO_ROOT}/include")
set(_go2_model_path
    "${CMAKE_CURRENT_SOURCE_DIR}/../../unitree_robots/go2/go2.xml")
if(EXISTS "${_go2_mujoco_lib}")
    target_include_directories(real_trot_go2 PRIVATE "${_go2_mujoco_inc}")
    target_link_libraries(real_trot_go2 "${_go2_mujoco_lib}")
    target_compile_definitions(
        real_trot_go2 PRIVATE GO2_MODEL_PATH="${_go2_model_path}")
    set_target_properties(
        real_trot_go2 PROPERTIES
        BUILD_RPATH "${GO2_MUJOCO_ROOT}/lib")
endif()

function(go2_add_ctest name)
    add_test(NAME ${name} COMMAND ${name})
endfunction()

add_test(
    NAME test_dds_runtime
    COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_dds_runtime.sh
            ${CMAKE_CURRENT_SOURCE_DIR}/../..)

if(EXISTS "${_go2_mujoco_lib}")
    add_executable(test_go2_forward_kinematics tests/test_go2_forward_kinematics.cpp)
    target_include_directories(
        test_go2_forward_kinematics
        PRIVATE "${_go2_mujoco_inc}")
    target_link_libraries(
        test_go2_forward_kinematics
        "${_go2_mujoco_lib}")
    target_compile_definitions(
        test_go2_forward_kinematics
        PRIVATE GO2_MODEL_PATH="${CMAKE_CURRENT_SOURCE_DIR}/../../unitree_robots/go2/go2.xml")
    go2_add_ctest(test_go2_forward_kinematics)
endif()

add_executable(test_go2_inverse_kinematics tests/test_go2_inverse_kinematics.cpp)

add_executable(test_raibert_footstep_planner tests/test_raibert_footstep_planner.cpp)

add_executable(test_raibert_trot_kernel tests/test_raibert_trot_kernel.cpp)
target_link_libraries(test_raibert_trot_kernel Eigen3::Eigen)

add_executable(test_cartesian_world_trot tests/test_cartesian_world_trot.cpp)
go2_add_ctest(test_cartesian_world_trot)

add_executable(test_motion_frame_utils tests/test_motion_frame_utils.cpp)

add_executable(test_velocity_filter tests/test_velocity_filter.cpp)
add_executable(test_velocity_command tests/test_velocity_command.cpp)
go2_add_ctest(test_velocity_command)

add_executable(test_trot_task tests/test_trot_task.cpp trot/trot_task.cpp)

add_executable(test_lean_route_guard
    tests/test_lean_route_guard.cpp
    trot/trot_cli.cpp
    trot/trot_task.cpp)
target_link_libraries(test_lean_route_guard unitree_sdk2 Eigen3::Eigen)
go2_add_ctest(test_lean_route_guard)

add_executable(test_contact_state_filter tests/test_contact_state_filter.cpp)
add_executable(test_contact_fusion_fault_harness tests/test_contact_fusion_fault_harness.cpp)
go2_add_ctest(test_contact_fusion_fault_harness)

set(CMAKE_BUILD_TYPE Release)

add_executable(test_contact_wrench_allocator tests/test_contact_wrench_allocator.cpp)
target_link_libraries(test_contact_wrench_allocator Eigen3::Eigen)

add_executable(test_go2_leg_jacobian tests/test_go2_leg_jacobian.cpp)
target_link_libraries(test_go2_leg_jacobian Eigen3::Eigen)

add_executable(test_contact_wrench_constraints tests/test_contact_wrench_constraints.cpp)
target_link_libraries(test_contact_wrench_constraints Eigen3::Eigen)

add_executable(test_contact_torque_mapping tests/test_contact_torque_mapping.cpp)
target_link_libraries(test_contact_torque_mapping Eigen3::Eigen)

add_executable(test_projected_contact_wrench_allocator tests/test_projected_contact_wrench_allocator.cpp)
target_link_libraries(test_projected_contact_wrench_allocator Eigen3::Eigen)

add_executable(test_contact_wrench_lexicographic_allocator tests/test_contact_wrench_lexicographic_allocator.cpp)
target_link_libraries(test_contact_wrench_lexicographic_allocator Eigen3::Eigen)

add_executable(test_dynamic_acceleration_target tests/test_dynamic_acceleration_target.cpp)

add_executable(test_motion_event_response tests/test_motion_event_response.cpp)

add_executable(test_wbc_runtime_gate tests/test_wbc_runtime_gate.cpp)

# Order-108 verification-only controller-side lockstep writer tick gate
# (DDS-free; header-only in trot/lockstep_writer_gate.h).
add_executable(test_lockstep_writer_gate tests/test_lockstep_writer_gate.cpp)
go2_add_ctest(test_lockstep_writer_gate)

# Order-109 verification-only state-synchronous motion clock (DDS-free).
add_executable(test_lockstep_motion_clock tests/test_lockstep_motion_clock.cpp)
go2_add_ctest(test_lockstep_motion_clock)

# Order-109b production call-chain integration test. The controller sources
# are compiled unchanged except for a test-only publish suppression and
# observability seam; the test drives TrotExperiment::LowCmdWrite itself.
add_executable(test_lockstep_motion_clock_integration
    tests/test_lockstep_motion_clock_integration.cpp
    trot/trot_task.cpp
    trot/trot_experiment_lifecycle.cpp
    trot/trot_experiment_gait.cpp
    trot/trot_experiment_wbc.cpp
    trot/trot_experiment_diagnostics.cpp
    trot/trot_experiment_control.cpp
)
target_compile_definitions(test_lockstep_motion_clock_integration
    PRIVATE GO2_TROT_TESTING=1)
target_link_libraries(test_lockstep_motion_clock_integration
    unitree_sdk2 Eigen3::Eigen)
if(EXISTS "${_go2_mujoco_lib}")
    target_include_directories(test_lockstep_motion_clock_integration
        PRIVATE "${_go2_mujoco_inc}")
    target_link_libraries(test_lockstep_motion_clock_integration
        "${_go2_mujoco_lib}")
    target_compile_definitions(test_lockstep_motion_clock_integration
        PRIVATE GO2_MODEL_PATH="${_go2_model_path}")
    set_target_properties(test_lockstep_motion_clock_integration PROPERTIES
        BUILD_RPATH "${GO2_MUJOCO_ROOT}/lib")
endif()
go2_add_ctest(test_lockstep_motion_clock_integration)

add_executable(test_centroidal_wbc tests/test_centroidal_wbc.cpp)

add_executable(test_preview_footstep_horizon tests/test_preview_footstep_horizon.cpp)
target_link_libraries(test_preview_footstep_horizon Eigen3::Eigen)

add_executable(test_dense_qp tests/test_dense_qp.cpp)
target_link_libraries(test_dense_qp Eigen3::Eigen)

add_executable(test_clean_baseline tests/test_clean_baseline.cpp)

add_executable(test_contact_wrench_qp tests/test_contact_wrench_qp.cpp)
target_link_libraries(test_contact_wrench_qp Eigen3::Eigen)

if(EXISTS "${_go2_mujoco_lib}")
    add_executable(test_go2_rigid_body tests/test_go2_rigid_body.cpp)
    target_include_directories(test_go2_rigid_body PRIVATE "${_go2_mujoco_inc}")
    target_link_libraries(test_go2_rigid_body "${_go2_mujoco_lib}" Eigen3::Eigen)
    target_compile_definitions(
        test_go2_rigid_body PRIVATE GO2_MODEL_PATH="${_go2_model_path}")
    set_target_properties(
        test_go2_rigid_body PROPERTIES
        BUILD_RPATH "${GO2_MUJOCO_ROOT}/lib")
    go2_add_ctest(test_go2_rigid_body)

    add_executable(test_inverse_dynamics_wbc tests/test_inverse_dynamics_wbc.cpp)
    target_include_directories(
        test_inverse_dynamics_wbc PRIVATE "${_go2_mujoco_inc}")
    target_link_libraries(
        test_inverse_dynamics_wb
```

### Instruction: `example/cpp/scripts/README.md`

SHA-256: `7bf90f21c5d9ccf1c6686029dc4c158555b97f4123d016eb3304aaf039a3dee1`; excerpt truncated

```text

```

<!-- PRAXIS_CONTEXT_PACK
{"default_branch":"main","default_branch_sha":"b1cec66f446c34e850c9caeeac82de52805a3889","instructions":[{"chars":2186,"excerpt":"# Go2 repository rules\n\n`main` is the stable code line and long-term route. The active research\nfrontier may live on a separate `research/*` branch. This file contains\nrepository guardrails; it is not a scientific plan or current-status report.\n\n## Task discovery bootstrap\n\nBefore accepting, declining, or executing any task from a local worktree, first\nrefresh the remote source of truth:\n\n1. run `git fetch origin --prune`;\n2. read `origin/main:CURRENT.md` (for example with\n   `git show origin/main:CURRENT.md`) to discover the active research branch;\n3. compare the local active branch/worktree with `origin/<active-branch>` and\n   fast-forward only when safe; never reset, discard, or delete local commits,\n   untracked files, or raw evidence to make it match;\n4. only after that, read the active branch `CURRENT.md`, current task, and exact\n   parent/closeout evidence.\n\nA stale local `CURRENT.md`, local branch tip, or cached task is never sufficient\nto conclude that no new task exists. If the local branch is ahead or diverged,\npreserve it and report the divergence instead of guessing which side wins.\n\nRead [`CURRENT.md`](CURRENT.md) for the single maintained frontier pointer.\nFollow that pointer to the frontier branch, its task, and exact `RESULTS.md`.\nUse the canonical [Research Execution SOP](docs/research/SOP.md) from\n`main`. A branch-local `CURRENT.md` is navigation only and cannot override\n`main/CURRENT.md`, the SOP, or the active task.\n\nThe active task owns the scientific question, intervention, frozen variables,\nrun budget, thresholds, and classification. Do not infer research direction\nfrom Atlas directories, dated worktrees, old branches, commit messages, or\narchived code. Do not change controller/planner behavior or scientific\nmeaning under an infrastructure-only task.\n\nNo live experiment is authorized by this file alone. Before any live run,\nfollow the task and SOP, verify the exact branch/HEAD and clean worktree, and\npreserve raw evidence. Everything below\n`example/cpp/experiments/_runs/` is ignored local evidence: never commit,\ndelete, overwrite, rename, or treat it as instruction. Curated evidence\nrequires its own manifest and provenance.\n","path":"AGENTS.md","sha256":"0e5f638d56a9bf10fd1a1718a346e46c17cddcfdd3a7e82dc6985d495aecdcec","truncated":false},{"chars":8306,"excerpt":"# Research Execution SOP v0.2\n\nStatus: active for new research checkpoints after adoption. Historical checkpoints keep the rules frozen with them.\n\nThis SOP is intentionally small. The normal path should feel like: **short task → preflight → run → closeout**.\n\n## 1. Core rule\n\n**Scientific variables are strict; execution engineering is flexible before live; after scientific capture begins, results may not be selected or retried opportunistically.**\n\n- **Sol** owns the scientific question and final scientific judgment.\n- **Luna** independently owns execution readiness and has unconditional live veto.\n\nA task is not permission to bypass a verified infrastructure constraint.\n\n## 2. What a task contains\n\nA task describes the **delta from its exact parent**, not the whole project.\n\nFor a live checkpoint it needs only:\n\n- mode: `infrastructure`, `exploratory`, or `confirmatory`;\n- question;\n- exact parent/base;\n- scientific change;\n- variables that must remain frozen;\n- run budget;\n- primary measurements / classification rule;\n- runner and run directory;\n- genuinely task-specific preflight requirements, if any.\n\nDo not restate SOP rules, parent results, unchanged thresholds, or long historical narratives. Read the current task, this SOP, and the exact parent `RESULTS.md`; consult older tasks only when evidence actually requires them.\n\n## 3. Scientific authority\n\nFor confirmatory work, Sol freezes the intervention, baseline, run budget, primary metrics, thresholds/classification, and scientific stop conditions.\n\nLuna must not autonomously change anything that could alter the post-handoff state/control trajectory or the scientific meaning of the primary evidence. This includes speed policy, gait timing, planner mathematics, WBC/MPC/ID behavior, controller gains, scene geometry, safety limits, scientific thresholds, seed/run count, or follow-up experiments.\n\nIf uncertain whether a change is execution-only or scientific/runtime-semantic, treat it as scientific and veto live.\n\n## 4. Luna autonomy and veto\n\nBefore scientific capture, Luna may independently inspect and minimally repair execution-only issues such as:\n\n- DDS/domain choice, locks and port conflicts;\n- paths, run-directory bookkeeping and executable bits;\n- runner shell plumbing that is proven trajectory-neutral;\n- logger/schema bookkeeping;\n- analyzer/tooling plumbing that does not change primary evidence meaning;\n- provenance collection, stale process cleanup, and no-live tests.\n\nLuna may add no-live tests without asking.\n\nIf the task conflicts with verified source semantics, geometry, protocol limits, accepted evidence, or preflight, Luna must veto rather than weaken an existing guard to obey the task.\n\n## 5. Preflight\n\nEvery live run must pass `tools/research/preflight.py` immediately before launch.\n\nAlways check:\n\n- exact branch/HEAD and clean worktree;\n- runner existence/syntax and actual DDS domain;\n- DDS/RTPS port legality, selected safe policy and free lock;\n- fresh run directory;\n- no stale simulator/controller/runner process;\n- task-required files/hashes/tests.\n\nUse `--diff-base <accepted-ref>` whenever an accepted parent/baseline exists. Preflight auto-detects changed execution surfaces from Git diff; `--changed-surface` is only an override/addition.\n\nChange-triggered checks:\n\n- runtime/schema/scene change → at least one relevant no-live/build test;\n- schema change → schema regression test;\n- primary analyzer semantics change → parser/fixture test;\n- runner change → record a baseline runner diff summary and inspect the actual Git diff;\n- geometry-dependent scientific gate change → re-derive it from source/scene geometry.\n\n### Sol review gate\n\nSecond Sol review is required only when the committed change can alter either:\n\n1. the post-handoff state/control trajectory; or\n2. the meaning/mapping/classification of primary evidence.\n\nRuntime, scene and schema changes trigger this automatically. A runner or analyzer change triggers it only when its actual semantics meet one of those two conditions; Luna must pass `--requires-sol-review` in that case.\n\nPure paths, output locations, report rendering, bookkeeping, or presentation-only analysis changes do not require redundant Sol review.\n\nWhen review is required, the exact reviewed SHA must equal the live HEAD via `--approved-head`.\n\n## 6. Attempt boundary and retry\n\nA scientific attempt is consumed at the first valid **post-handoff state/control sample** used by the experiment.\n\n- **Prelaunch failure:** no attempt consumed; Luna may fix execution-only issues and rerun preflight.\n- **Boot failure before that sample:** no scientific attempt consumed. One automatic recovery launch is allowed only if the cause is proven execution-only, failed artifacts are preserved, scientific/runtime semantics are unchanged, and preflight passes again.\n- **Scientific capture started:** run budget is consumed. No autonomous retry, replacement run, domain change, or tuning.\n\nScientific gate failures stop; infrastructure gate failures before capture may be repaired in the same checkpoint.\n\n## 7. Evidence\n\nOnce capture starts, raw artifacts are immutable. Do not overwrite, normalize, or hand-edit raw evidence.\n\nPrefer deterministic offline salvage over rerunning. A repair is scientifically usable only when:\n\n- raw bytes remain unchanged;\n- the mapping/repair is unique;\n- it follows from frozen runtime source/protocol rather than outcome preference;\n- independent semantic invariants validate it;\n- derivation and provenance are recorded.\n\nDo not preregister a guessed bug shape when uniqueness/source-grounded recoverability is the real requirement.\n\nHistorical conclusions are append-only; a later correction may supersede an interpretation without erasing it.\n\n## 8. Failure triage\n\nAfter a failed run, identify the earliest failed boundary before designing another experiment:\n\n1. `execution`\n2. `evidence`\n3. `causal`\n4. `scientific`\n\nDo not invent a new generic classification label for every infrastructure failure. Record the boundary plus a specific `reason_code`; scientific labels remain task-specific.\n\n## 9. Exploratory vs confirmatory\n\n- `infrastructure`: tooling/repair only; no scientific claim.\n- `exploratory`: bounded search/debugging authorized in advance; useful for design, not confirmatory evidence.\n- `confirmatory`: intervention, run budget, thresholds and classification frozen before live.\n\nDo not force tuning into repeated fake one-run confirmatory checkpoints. Explore first when necessary, then freeze and validate.\n\n## 10. Branches and outputs\n\nCreate a new research branch for a new scientific question, new live attempt, or runtime-semantic change.\n\nPure offline correction, evidence salvage, analyzer repair, or additional derived analysis may continue on the same research branch when raw evidence and scientific design are unchanged. Append a new commit/closeout and mark supersession when needed.\n\nDefault closeout artifacts are only:\n\n- `RESULTS.md`\n- `analysis.json`\n- `provenance.csv`\n\nCreate extra CSV/tables only when they are actual evidence needed to audit that checkpoint.\n\nProvenance should hash what matters to the conclusion: raw evidence, scene/model/config where relevant, and exact runtime/source/binary identity. Do not hash every derived report by ritual.\n\n## 11. Lessons already encoded\n\nThis SOP specifically addresses failures already seen in this project:\n\n- DDS domain 233 → actual RTPS/domain preflight + Luna veto;\n- missing `--wall-clock-motion` → runner comparison against accepted baseline;\n- invalid `base x < 0.65` pre-step gate → source/scene-derived geometry review;\n- 780/776 CSV mismatch → schema regression test before live;\n- guessed empty-token recovery rule → general uniqueness/source-invariant evidence recovery;\n- unnecessary branch/checkpoint churn → execution repair before capture and same-branch offline corrections.\n\n## 12. Authority and version\n\nFor checkpoints adopting this SOP:\n\n1. frozen scientific delta in the current task;\n2. this SOP for execution/veto/retry/evidence rules;\n3. exact parent/baseline evidence;\n4. older history as needed.\n\n`PHASE1_AGENT_CONTRACT.md` remains historical authority only for checkpoints created under it.\n\nCurrent version: **v0.2**. Git history is the changelog; no separate release ceremony is required.\n","path":"docs/research/SOP.md","sha256":"fd3c9d1b2f29ee3924794e5984ead53a2e7de06cf87465eb38f3860439281e2b","truncated":false},{"chars":1404,"excerpt":"# Go2 repository bootstrap\n\n`main` is the stable code line and long-term route. The active research\nfrontier may live on a separate `research/*` branch and is not implied by\nthe code or history on `main`.\n\nThis file is the only maintained repository-level frontier pointer. It is not\na scientific plan. The active task owns the research question and design; the\ncanonical execution rules live in [`docs/research/SOP.md`](docs/research/SOP.md).\n\n## Active research frontier\n\nUpdate only this block when the frontier changes. The dated branch/task below\nare a pointer value, not a permanent architecture decision.\n\n- Branch: [`research/canonical-clean-baseline-integration-20260917`](https://github.com/kairoi-k/go2-mujoco-control/tree/research/canonical-clean-baseline-integration-20260917)\n- Branch navigation: [`CURRENT.md`](https://github.com/kairoi-k/go2-mujoco-control/blob/research/canonical-clean-baseline-integration-20260917/CURRENT.md)\n- Task: [`TASK_CANONICAL_CLEAN_BASELINE_INTEGRATION_20260917.md`](https://github.com/kairoi-k/go2-mujoco-control/blob/research/canonical-clean-baseline-integration-20260917/docs/research/TASK_CANONICAL_CLEAN_BASELINE_INTEGRATION_20260917.md)\n- Expected closeout: [`RESULTS.md`](https://github.com/kairoi-k/go2-mujoco-control/blob/research/canonical-clean-baseline-integration-20260917/docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md)\n","path":"CURRENT.md","sha256":"aa8a33c4ded00a3d79c609f448be89a260952ada27f53baef12b1dfbbd1429dd","truncated":false},{"chars":4975,"excerpt":"# Architecture\n\nThis document maps the code; it does not define research status or the next\ntask. For Phase 2, read [`CURRENT.md`](../CURRENT.md) first.\n\n## Runtime data flow\n\nThe MuJoCo process and 500 Hz C++ controller communicate through the Unitree\nSDK2 DDS interface.\n\n```text\nMuJoCo -> LowState / lidar -> state snapshot and filtering\n                                  |\nrequested velocity -> Phase 1 shaper -> gait/foothold targets\n                                           |\n                         clean target contract + direct IK feasibility\n                                           |\n                                        SRBD MPC\n                                           |\n                              strict 18-DoF ID-WBC acceptance\n                                           |\n                              final finite/ramp/torque envelope\n                                           |\n                                      LowCmd -> MuJoCo\n```\n\nThe sensor-only terrain path derives a terrain model, feasibility results, and\na plan from lidar. On the current line it may be logged and analyzed, but it\ndoes not alter gait, MPC, WBC, contact policy, or velocity. There is no\nproduction terrain-actuation path.\n\n## Active modules\n\n| Area | Primary files | Responsibility |\n|---|---|---|\n| CLI and lifecycle | `example/cpp/trot/trot_cli.*`, `trot_experiment_lifecycle.cpp` | configuration, DDS, startup, shutdown |\n| Control loop | `example/cpp/trot/trot_experiment_control.cpp` | state snapshot, phase execution, command publication |\n| Gait | `example/cpp/trot/trot_experiment_gait.cpp`, `example/cpp/gait/*` | running-trot phase, footholds, velocity targets |\n| Terrain interfaces | `example/cpp/terrain/*` | sensor-derived model, feasibility, immutable plan interface |\n| MPC and WBC | `example/cpp/trot/trot_experiment_wbc.cpp`, `example/cpp/wbc/*` | SRBD preview and inverse-dynamics control |\n| Kinematics | `example/cpp/kinematics/*` | FK, IK, Jacobians, rigid-body model |\n| Contact | `example/cpp/contact/*` | measured-contact filtering, wrench allocation, torque mapping |\n| Timing | `example/cpp/trot/lockstep_*` | lockstep clock/writer diagnostics; not a realtime acceptance claim |\n| Diagnostics | `example/cpp/trot/trot_experiment_diagnostics.cpp`, `trot_types.h` | limits, status, structured logs |\n| Clean baseline contract | `example/cpp/wbc/clean_baseline.h`, `go2_inverse_kinematics.h`, `inverse_dynamics_wbc.h` | exact targets, authoritative limits, strict solver result, final command envelope |\n| Canonical DDS runtime | `example/cpp/scripts/dds_runtime.sh`, `run_trot.sh`, `run_trot_exact_source.sh` | tracked support artifact, fail-closed cleanup, exact-source launch plumbing |\n| Tests and analysis | `example/cpp/tests/`, `example/cpp/tools/` | unit/integration checks and protocol analyzers |\n\n## Target Phase 2 planner\n\nThe active Stage C target adds `TerrainBelief` for estimated state, measured\ncontact, terrain freshness, and uncertainty. `TerrainFeasibility` remains the\nhard-filter/candidate layer. A receding-horizon `TerrainPlanner` then jointly\noptimizes future footholds, body/CoM references, touchdown/contact timing, and\nswing duration. Its complete output is one atomic `TerrainExecutionState`\nconsumed by gait, SRBD-MPC, and ID-WBC.\n\nThe first implementation stays in running-trot topology and runs in\nshadow/replay before actuation. The existing per-leg scorer is not the target\nplanner, and archived Stage-C code is not a design source. `CURRENT.md` owns\nthe ordered implementation and acceptance sequence.\n\n## Phase 2 invariants\n\nThe Phase 1 shaper remains the only velocity authority. Planned contact and\nforce-supported measured contact remain separate. A future terrain execution\npath must publish one immutable, time-indexed snapshot shared by gait, SRBD-MPC,\nand ID-WBC; no consumer may invent its own timing, contact, or recovery state.\nAny actuation-capable terrain planner must explicitly enable the clean baseline\ncontract and enter through `exact foot targets -> direct IK feasibility ->\nstrict WBC -> final safety envelope`. Sensor-only terrain remains observer-only.\nThe Cartesian-world and legacy clamp/overlay path is incompatible with\n`--clean-baseline`.\n\nThe retained `example/cpp/leg_lift/` executable and multi-step configurations\nare historical experiments. They are not a Phase 2 route or design source.\nRemoved crawl/three-contact code and Git history are not fallback\nimplementations.\n\n## Repository boundaries\n\n`simulate/` and `unitree_robots/go2/` remain close to the upstream Unitree\nsimulator. Research-specific model control lives in `example/cpp/`. Isaac Lab\nRL and Kine2Go imitation live only in their companion repositories and are not\nruntime dependencies here.\n\nSee [`CODE_GUIDE.md`](CODE_GUIDE.md) for source navigation,\n[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) for execution rules, and\n[`../UPSTREAM_AND_CONTRIBUTIONS.md`](../UPSTREAM_AND_CONTRIBUTIONS.md) for\nprovenance.\n","path":"docs/ARCHITECTURE.md","sha256":"09057f74352dc251fd6feecf7cada2c70a469175c8c668c2d79369217580c6ca","truncated":false},{"chars":4900,"excerpt":"# Code guide\n\nThis guide points contributors to the smallest relevant source area for common changes. The primary research implementation is under `example/cpp/`.\nFor current Phase 2 work, read [`../CURRENT.md`](../CURRENT.md) first; this file\nonly maps code and cannot define the route.\n\n## Entry points\n\n| Task | Start here |\n|---|---|\n| Read current Phase 2 route/status | `CURRENT.md`, then `AGENTS.md` and `docs/research/PHASE2_ACCEPTANCE.md` |\n| Understand the runtime/control data flow | `docs/ARCHITECTURE.md` |\n| Build or run the C++ stack | `example/cpp/README.md` |\n| Change command-line configuration | `example/cpp/trot/trot_cli.*` |\n| Change the canonical clean baseline | `example/cpp/wbc/clean_baseline.h`, `example/cpp/kinematics/go2_inverse_kinematics.h`, `example/cpp/wbc/inverse_dynamics_wbc.h`, `example/cpp/trot/trot_experiment_gait.cpp`, `trot_experiment_wbc.cpp`, `trot_experiment_control.cpp` |\n| Change stand / walk / stop sequencing | `example/cpp/trot/trot_task.*`, `example/cpp/trot/trot_experiment_control.cpp` |\n| Change gait phase or foot targets | `example/cpp/trot/trot_experiment_gait.cpp`, `example/cpp/gait/raibert_trot_kernel.h` |\n| Change Raibert landing adjustment | `example/cpp/gait/raibert_footstep_planner.h` |\n| Change contact-force allocation | `example/cpp/contact/contact_wrench_*` |\n| Change centroidal wrench / foothold preview | `example/cpp/wbc/centroidal_wbc.h`, `example/cpp/gait/preview_footstep_horizon.h`, `example/cpp/contact/contact_wrench_qp.h`, `example/cpp/gait/footstep_mpc.h` |\n| Change `--wbc-full` ID-WBC / SRBD MPC | `example/cpp/kinematics/go2_rigid_body.h`, `example/cpp/wbc/srbd_mpc.h`, `example/cpp/wbc/inverse_dynamics_wbc.h`, `example/cpp/wbc/dense_qp.h`, `example/cpp/trot/trot_experiment_wbc.cpp` |\n| Change dynamics-informed feedforward | `example/cpp/trot/trot_experiment_wbc.cpp`, `example/cpp/trot/trot_true_dynamics.h` |\n| Change safety gates / diagnostics | `example/cpp/trot/trot_experiment_diagnostics.cpp` |\n| Change sensor-only terrain interfaces | `example/cpp/terrain/*`, `example/cpp/trot/trot_experiment_gait.cpp` |\n| Change timing/lockstep diagnostics | `example/cpp/trot/lockstep_*`, `example/cpp/tests/test_lockstep_*` |\n| Change canonical DDS/build plumbing | `example/cpp/scripts/dds_runtime.sh`, `run_trot.sh`, `run_trot_exact_source.sh`, `simulate/CMakeLists.txt`, `example/cpp/CMakeLists.txt` |\n| Run Phase 2 B0 development checks | `example/cpp/scripts/run_phase2_b0_pair.sh`, `run_phase2_b0_fixed_pair.sh`; domains come from the holdout manifest |\n| Inspect historical leg-lift / multi-step code | `example/cpp/leg_lift/*`; never use it as a Phase 2 route or design source |\n| Inspect retained experiment evidence | `example/cpp/experiments/`, `example/cpp/experiments/CATALOG.md` |\n\n## Trot controller\n\n`real_trot_go2.cpp` is the executable entry point. Sequencing lives in `TrotTask`; the remaining `TrotExperiment` modules own DDS, gait, WBC, and diagnostics:\n\n- `trot/trot_task.*` — stand / walk / stand / lie sequencer;\n- `trot/trot_experiment_lifecycle.cpp` — initialization, DDS, shutdown;\n- `trot/trot_experiment_gait.cpp` — velocity estimation and gait targets;\n- `trot/trot_experiment_wbc.cpp` — contact-force / dynamics-informed feedforward;\n- `trot/trot_experiment_diagnostics.cpp` — limits, quality gates, logging;\n- `trot/trot_experiment_control.cpp` — 500 Hz control loop;\n- `trot/trot_types.h` — shared configuration and diagnostic structures.\n\n## Leg-lift controller\n\nThis standalone historical experiment is not a Phase 2 route or design source.\nIts action-sequence implementation is split into:\n\n- `leg_lift_cli.*` — CLI parsing;\n- `leg_lift_lifecycle.cpp` — setup and lifecycle;\n- `leg_lift_world.cpp` — world-frame feedback;\n- `leg_lift_diagnostics.cpp` — logging and acceptance diagnostics;\n- `leg_lift_control.cpp` — control phases and command publication;\n- `leg_lift_types.h` — sequence types and constants.\n\n## Supporting headers\n\n- Kinematics: `example/cpp/kinematics/go2_forward_kinematics.h`, `go2_inverse_kinematics.h`, `go2_leg_jacobian.h`\n- Gait: `example/cpp/gait/locomotion_kernel.h`, `raibert_trot_kernel.h`, `raibert_footstep_planner.h`, `preview_footstep_horizon.h`, `footstep_mpc.h`\n- Contact / WBC: `example/cpp/contact/contact_*.h`, `contact_wrench_qp.h`, `example/cpp/wbc/dense_qp.h`, `wbc_runtime_gate.h`, `example/cpp/contact/go2_contact_torque_mapping.h`\n- Terrain: `example/cpp/terrain/terrain_model.h`, `terrain_feasibility.h`, `terrain_motion_plan.h`, `terrain_planner.h`, `terrain_control_interface.h`\n- Timing: `example/cpp/trot/lockstep_motion_clock.h`, `lockstep_writer_gate.h`\n- Filtering / frames: `example/cpp/util/velocity_filter.h`, `motion_frame_utils.h`, `example/cpp/contact/contact_state_filter.h`\n\nWhen a change can alter research semantics, record the affected configuration/evidence and follow [`../CONTRIBUTING.md`](../CONTRIBUTING.md).\n","path":"docs/CODE_GUIDE.md","sha256":"b4fdc0e7c300f9278c47d406bb6e6783417c255c98973de15210b4ac4df447c8","truncated":false},{"chars":1175,"excerpt":"# Phase1 benchmark freeze\n\nThis is the frozen Phase1 reference for the terrain worktree. It is a\nsimulation-only result and does not claim hardware or sim-to-real performance.\n\n- Source: `1b4d9b8fcf3dcfb63cee144c9871a235101713c9`\n- Branch: `terrain/phase2-20260824T150934Z`\n- Build: MuJoCo 3.3.6, simulator and C++ controller built in Ubuntu-22.04/WSL\n- Tests: `ctest --test-dir example/cpp/build --output-on-failure` - 25/25\n- Profile: `bash example/cpp/scripts/run_sustained_running.sh --headless`\n- Analyzer: `python3 example/cpp/tools/analysis/analyze_sustained_running.py <run>`\n\n| run | median m/s | good window s | roll/pitch P95 deg | aerial | pair sync min | stop P95 m/s |\n|---|---:|---:|---:|---:|---:|---:|\n| `phase1_freeze_running_r1_20260824` | 3.242725 | 61.402 | 2.821/2.288 | 0.293086 | 0.817057 | 0.004574 |\n| `phase1_freeze_running_r2_20260824` | 3.227325 | 61.442 | 3.166/2.541 | 0.283184 | 0.799286 | 0.003563 |\n| `phase1_freeze_running_r3_20260824` | 3.234687 | 61.422 | 2.778/2.308 | 0.291980 | 0.810059 | 0.003980 |\n\nAll three runs passed the unchanged strict analyzer. Terrain changes must\nretain this reference as a separate flat-ground regression.\n","path":"docs/validation/PHASE1_BENCHMARK_FREEZE_2026-08-24.md","sha256":"3ab47ab6921796678d3fc1416f797621509f5e4ac74548910aa79a0a2d8ba338","truncated":false},{"chars":9062,"excerpt":"# Canonical clean-baseline integration and legacy isolation\n\nMode: `engineering-correctness / no-live / canonicalization`\n\nExact main parent: `041c36c499ff24ab6c8edf74fa6283e0ba923db6`\nValidated research result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`\nValidated live candidate: `0009b5fbd1e962e38135922da61245a99b522aab`\nClean-baseline P0 source/reference: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`\nDDS root-fix accepted result: `2eb92bc62be6fba2dee26ac9229520d8835c6246`\n\n## Purpose\n\nThe validated research chain has now established two accepted facts:\n\n1. the repository-owned DDS/exact-source host runtime can start deterministically on domain 220; and\n2. the P0 clean baseline reproduced the frozen flat trot for 64/64 cycles at the preregistered low speed, with no clean-target rejection, strict WBC/QP rejection, hard/emergency stop, or gross tracking/stability failure.\n\nHowever protected `main` is still on a divergent history and does not yet contain the validated clean baseline as the canonical foundation. The goal of this task is to make `main`-derived code structurally clean and ready to become the long-term research base without importing the entire exploratory research history.\n\nThis task authorizes NO live MuJoCo/DDS locomotion execution.\n\n## Critical integration rule\n\nDo **not** merge or cherry-pick the entire research branch/history onto main.\n\nThe research chain and current main diverged after an older merge base. Treat the accepted commits above as a **reference tree and evidence source**, not as history to transplant wholesale.\n\nStarting from this task branch (which is based on current protected main), inspect the exact accepted implementation and port only the minimal coherent code, tests, launch/runtime support, and final accepted evidence needed for the canonical baseline.\n\nDo not bring intermediate failed task documents, obsolete experiment patches, V1/V2 known-step logic as active architecture, or temporary closeout/recovery scaffolding into the canonical surface unless a file is independently required by current main.\n\n## Canonical control invariants\n\nThe integrated clean baseline must make these rules true by construction and tests, not merely by convention:\n\n1. **Planner/foot target identity:** a clean-mode requested foot target is either accepted exactly or rejected. No workspace clamp, iterative shrink, or downstream target mutation may silently replace it.\n2. **Authoritative joint limits:** clean target acceptance uses the actual Go2/MuJoCo joint limits and direct IK feasibility.\n3. **Strict optimizer acceptance:** clean ID-WBC motion accepts only a genuinely accepted constrained QP result. Equality residual alone may not promote a failed solver result to success.\n4. **Correct swing acceleration:** swing task acceleration includes the `Jdot*qdot` term.\n5. **No post-optimizer actuation overlays:** after the accepted clean WBC/QP result, legacy lean/force/direct-propulsion/Cartesian-stance or similar torque overlays must not alter the command. Only the explicit final torque safety envelope may remain.\n6. **Final command identity:** the LowCmd emitted in clean mode must be traceable to the accepted clean result plus the explicit finite/ramp/torque safety envelope.\n7. **Fail closed:** clean target or strict WBC failure must safe-hold/stop according to the existing clean design; it must not fall back to legacy clamp or legacy controller behavior.\n8. **Cartesian-world incompatibility:** clean baseline and the old Cartesian-world path remain mutually exclusive and fail closed at CLI/config validation.\n\n## Legacy isolation\n\nThe repository may retain historical/legacy code where removal would create unnecessary compatibility risk, but it must be structurally isolated from the canonical research path.\n\nRequired outcomes:\n\n- The clean baseline execution path must not invoke `ClampFootToHipWorkspace`, `AllLegInverseKinematicsClamped`, or any equivalent silent target mutation.\n- Legacy post-WBC torque overlays must be unreachable once the clean path has produced its final accepted command.\n- Historical helpers should be clearly labeled/contained as legacy and must not be the default extension point for new Phase-2 work.\n- Any future **terrain actuation/planner execution** path must be required to enter through the clean baseline contract. Existing sensor-only/shadow observation may remain observer-only if it cannot actuate.\n- Add a fail-closed guard/test so new Phase-2 actuation cannot accidentally route through the legacy clamp/overlay stack.\n- Do not simply delete useful historical code if a smaller explicit isolation boundary is clearer and safer.\n\n## Canonical DDS and exact-source runtime\n\nPort the accepted repository-owned runtime from the validated reference if not already present on main:\n\n- deterministic tracked-source DDS support artifact generation;\n- fail-closed DDS shared-memory cleanup/inspection behavior;\n- canonical `run_trot.sh` DDS integration;\n- exact-source host build wrapper for simulator/controller;\n- read-only LowState probe and relevant focused tests where they are part of the accepted runtime;\n- removal of ambient `/home/che/dds_base4000_preload.so` or hidden shell state as authority.\n\nPreserve current main's newer Atlas worker/dispatcher infrastructure. Do not regress or replace it with older research-branch copies.\n\n## Evidence canonicalization\n\nBring into the main-derived integration only the small, final accepted evidence needed to support the baseline claim. At minimum preserve or recreate canonical records that identify:\n\n- accepted DDS root-fix result `2eb92bc62be6fba2dee26ac9229520d8835c6246`;\n- accepted flat reproduction result `8b189c1bd7dab761c014f1db98e1223f3d73120d`;\n- exact validated live candidate `0009b5fbd1e962e38135922da61245a99b522aab`;\n- frozen command/parameters;\n- core measured result: 64/64 cycles, nominal 0.1516666667 m/s, measured regression speed about 0.153806 m/s, and zero primary rejection/safety counts;\n- provenance pointers/hashes sufficient to locate and audit the original accepted evidence.\n\nPrefer copying the final accepted closeout/provenance/host-record files or writing one concise canonical evidence record over importing every intermediate task and protocol-failure document.\n\nUpdate `CURRENT.md`, `docs/ARCHITECTURE.md`, `docs/CODE_GUIDE.md`, or the smallest appropriate canonical docs so future work clearly starts from the clean baseline rather than V1/V2 patch history.\n\n## Canonical extension seam for terrain research\n\nCreate or document one obvious extension boundary for the next kinematics-aware terrain swing planner:\n\n`gait/foothold + predicted body/hip state -> clean swing planner -> exact foot targets -> direct IK feasibility -> strict WBC -> final safety envelope`\n\nDo not implement the new terrain planner in this task. The objective is to make it difficult to extend the wrong legacy seam.\n\n## Validation\n\nNo live run is authorized.\n\nPerform all practical static/offline/build validation, including at minimum:\n\n- portable repository checks;\n- focused clean-baseline unit/contract tests;\n- direct-IK/joint-limit tests;\n- strict ID-WBC tests including solver rejection and swing `Jdot*qdot` behavior;\n- clean CLI incompatibility checks;\n- tests proving clean mode bypasses legacy clamp and post-WBC overlays;\n- DDS runtime focused tests, including fail-closed cleanup behavior;\n- exact-source wrapper syntax/contract checks;\n- practical CTest set and MuJoCo-backed rigid-body/ID-WBC tests when available without launching a live simulator/controller pair;\n- `git diff --check`.\n\nIf a historical test conflicts with the accepted clean invariants, determine whether the test is legacy-specific and isolate it rather than weakening the invariant.\n\n## Required closeout\n\nWrite:\n\n- `docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md`\n- `docs/validation/canonical_clean_baseline_integration_20260917/provenance.csv`\n\nThe result must separate:\n\n1. `FACTS` — exact main parent, accepted reference commits, actual ported files and tests;\n2. `INVARIANT AUDIT` — each of the eight canonical control invariants with source/test evidence;\n3. `LEGACY ISOLATION` — what remains and why it cannot mutate the canonical path;\n4. `CANONICAL SURFACE` — exact commands/files future Phase-2 work should use;\n5. `LUNA INTERPRETATION` — proposed classification, reviewable by Sol.\n\nUse one primary classification:\n\n- `CANONICAL_CLEAN_BASELINE_READY` — minimal validated implementation is coherently integrated on current-main ancestry, invariants/tests pass, accepted evidence is preserved, and legacy cannot silently enter the clean path;\n- `CANONICAL_INTEGRATION_INCOMPLETE` — the accepted implementation cannot yet be ported without unresolved conflict or an invariant remains unproven;\n- `PROTOCOL_FAILURE` — task execution/evidence is invalid.\n\nDo not perform a live experiment and do not claim repeatability beyond the already accepted single formal flat reproduction. Repeatability will be tested only after this integration is merged to protected main.\n","path":"docs/research/TASK_CANONICAL_CLEAN_BASELINE_INTEGRATION_20260917.md","sha256":"7517923c1df410c54f51dab9626d5e8fc3a3b97f6b9b87c70c7a4a5b6f16bf9f","truncated":false},{"chars":6965,"excerpt":"# Canonical clean-baseline integration closeout\n\nDate: `2026-09-17`\n\nTask commit: `7ab6fbf6e08e57d0d6d1b536ab7870887ac602e7`\n\nExact main parent: `041c36c499ff24ab6c8edf74fa6283e0ba923db6`\n\nMode: `engineering-correctness / no-live / canonicalization`\n\nProposed Luna classification: `CANONICAL_CLEAN_BASELINE_READY`\n\n## FACTS\n\n- No simulator/controller pair or locomotion run was launched. Raw `_runs`\n  evidence was not modified.\n- The accepted reference commits were inspected as trees and evidence sources,\n  not merged or cherry-picked as history:\n  - P0 clean-baseline source/reference: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`;\n  - accepted DDS root-fix result: `2eb92bc62be6fba2dee26ac9229520d8835c6246`;\n  - validated flat result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`;\n  - exact validated live candidate/wrapper source: `0009b5fbd1e962e38135922da61245a99b522aab`.\n- The port is limited to the clean controller seams, focused tests, tracked DDS\n  runtime/probe/exact-source plumbing, build-root portability, and canonical\n  documentation. Historical task documents, intermediate recovery scaffolds,\n  and full historical analysis were not imported.\n- Clean controller implementation is in:\n  `example/cpp/wbc/clean_baseline.h`,\n  `example/cpp/kinematics/go2_inverse_kinematics.h`,\n  `example/cpp/wbc/inverse_dynamics_wbc.h`,\n  `example/cpp/trot/trot_experiment_gait.cpp`,\n  `example/cpp/trot/trot_experiment_wbc.cpp`, and\n  `example/cpp/trot/trot_experiment_control.cpp`.\n- Canonical runtime implementation is in\n  `example/cpp/scripts/dds_runtime.sh`, `run_trot.sh`,\n  `run_trot_exact_source.sh`, `dds_runtime_root_smoke.sh`, and the read-only\n  `apps/dds_lowstate_probe.cpp`; `example/cpp/CMakeLists.txt` and\n  `simulate/CMakeLists.txt` accept explicit SDK roots.\n- Accepted flat evidence remains externally auditable at the referenced\n  closeout and host-record paths. Its frozen command and core result are\n  preserved: `64/64` cycles, nominal `0.1516666667 m/s`, measured OLS speed\n  about `0.153806 m/s`, and zero primary rejection/safety counts.\n- Validation completed without live execution: full controller CTest `34/34`,\n  including `test_dds_runtime`, `test_clean_baseline`,\n  `test_go2_inverse_kinematics`, `test_inverse_dynamics_wbc`,\n  `test_terrain_interfaces`, and `test_lean_route_guard`; the simulator\n  `test_lockstep` unit test also passed. The simulator-launch integration CTest\n  was excluded by the no-live task boundary.\n- `bash -n` passed for all canonical shell scripts and `git diff --check`\n  passed. The required remote refresh was attempted but the linked worktree’s\n  Git metadata rejected `FETCH_HEAD` writes as read-only; the supplied exact\n  task ref, `HEAD`, `origin/main`, and accepted reference refs were verified\n  read-only without changing Git metadata.\n\n## INVARIANT AUDIT\n\n1. **Planner/foot target identity — PASS.** Clean gait target construction\n   calls `ResolveFootTargetsToJointPositions` with the requested targets and\n   does not call the legacy clamped solver. The direct-IK rejection and\n   non-mutation cases pass in `test_go2_inverse_kinematics` and\n   `test_clean_baseline`.\n2. **Authoritative joint limits — PASS.** Clean acceptance checks the Go2\n   ranges represented in `unitree_robots/go2/go2.xml`, including distinct front\n   and rear thigh ranges, after direct IK. The joint-range-invalid fixture is\n   rejected without projection.\n3. **Strict optimizer acceptance — PASS.** `require_qp_acceptance` rejects a\n   failed constrained solve before its iterate can become output. The dense-QP\n   rejection fixture and strict ID-WBC test pass; clean runtime failure clears\n   solver/mapping acceptance and cannot reuse a stale result.\n4. **Correct swing acceleration — PASS.** `AddSwingFootAccelerationTask`\n   includes `Jdot*qdot` in the acceleration residual. The focused swing test\n   checks both the gradient term and Hessian.\n5. **No post-optimizer actuation overlays — PASS.** Clean\n   `WriteMotorCommands` returns through the accepted torque plus the explicit\n   final finite/ramp/absolute envelope. Legacy force, lean, Cartesian, and\n   sprint overlays are enclosed by `!params_.clean_baseline`.\n6. **Final command identity — PASS.** Clean LowCmd torque is sourced from the\n   mapped accepted ID-WBC torque and passed only to\n   `ApplyFinalTorqueSafetyEnvelope`; failed WBC uses a zero-feedforward safe\n   hold rather than a legacy command path.\n7. **Fail closed — PASS.** Direct target failure requests the existing stop\n   sequence, strict WBC failure disables primary output, and clean command\n   writing emits a zero-feedforward hold instead of falling back to legacy\n   torque/position overlays. The route and contract tests cover these seams.\n8. **Cartesian-world incompatibility — PASS.** CLI validation rejects\n   `--clean-baseline --cartesian-world`, and `test_lean_route_guard` passes.\n\n## LEGACY ISOLATION\n\n- `AllLegInverseKinematicsClamped` and `ClampFootToHipWorkspace` remain only\n  for compatibility and are explicitly labeled legacy. The clean target branch\n  precedes both legacy paths and uses a const requested-target boundary.\n- Cartesian-world is a separate CLI route and is fail-closed against clean\n  mode. Its post-WBC behavior cannot be reached after clean mode is selected.\n- Terrain observation remains sensor-only in the maintained runtime. The\n  `TerrainPlannerConfig` actuation boundary now rejects any actuation-capable\n  planner unless `clean_baseline_contract` is explicitly enabled; its focused\n  test proves the rejection and the opt-in contract path.\n- The legacy helpers were not deleted because existing compatibility callers\n  and historical tests still depend on them. They are not the clean extension\n  seam or default Phase-2 route.\n\n## CANONICAL SURFACE\n\nFuture Phase-2 work should start from `CURRENT.md`, use the tracked DDS layer\nthrough `example/cpp/scripts/run_trot.sh`, and extend only this contract:\n\n`gait/foothold + predicted body/hip state -> clean swing planner -> exact foot targets -> direct IK feasibility -> strict WBC -> final safety envelope`\n\nThe clean controller entry is `real_trot_go2 ... --clean-baseline`; Cartesian\nworld and legacy terrain-actuation options remain separate or retired. Exact\nsource builds use `simulate/CMakeLists.txt` with `-DMUJOCO_ROOT` and\n`example/cpp/CMakeLists.txt` with `-DGO2_MUJOCO_ROOT`. The read-only DDS probe\nis `dds_lowstate_probe --domain-id N --interface lo`.\n\n## LUNA INTERPRETATION\n\n`CANONICAL_CLEAN_BASELINE_READY` is proposed because the minimal accepted clean\nimplementation is coherently integrated on current-main ancestry, all eight\ncontrol invariants have source and focused-test evidence, the accepted flat and\nDDS records remain referenced with hashes, and legacy clamp/overlay entry is\nexplicitly isolated. This is an offline integration result. It does not claim\nnew repeatability or authorize a live run; repeatability remains a later task\nafter protected-main integration.\n","path":"docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md","sha256":"0aac77c9064dfe9079f70dc01cfd0f970c9e7d7b59e2f44ae9080c9768d6fd42","truncated":false},{"chars":10779,"excerpt":"cmake_minimum_required(VERSION 3.16)\nproject(stand_go2)\nenable_testing()\n\nlist(APPEND CMAKE_PREFIX_PATH \"/opt/unitree_robotics/lib/cmake\")\nfind_package(unitree_sdk2 REQUIRED)\nfind_package(Eigen3 REQUIRED)\n\nset(GO2_CPP_INCLUDE_DIRS\n    ${CMAKE_CURRENT_SOURCE_DIR}\n    ${CMAKE_CURRENT_SOURCE_DIR}/apps\n    ${CMAKE_CURRENT_SOURCE_DIR}/trot\n    ${CMAKE_CURRENT_SOURCE_DIR}/gait\n    ${CMAKE_CURRENT_SOURCE_DIR}/kinematics\n    ${CMAKE_CURRENT_SOURCE_DIR}/contact\n    ${CMAKE_CURRENT_SOURCE_DIR}/wbc\n    ${CMAKE_CURRENT_SOURCE_DIR}/util\n    ${CMAKE_CURRENT_SOURCE_DIR}/leg_lift\n    ${CMAKE_CURRENT_SOURCE_DIR}/terrain\n)\ninclude_directories(${GO2_CPP_INCLUDE_DIRS})\n\nadd_executable(stand_go2 apps/stand_go2.cpp)\ntarget_link_libraries(stand_go2 unitree_sdk2)\n\nadd_executable(hold_pose_go2 apps/hold_pose_go2.cpp)\ntarget_link_libraries(hold_pose_go2 unitree_sdk2)\n\nadd_executable(track_lowcmd_lowstate_go2 apps/track_lowcmd_lowstate_go2.cpp)\ntarget_link_libraries(track_lowcmd_lowstate_go2 unitree_sdk2)\n\n# Boot-only DDS transport probe.  It subscribes to rt/lowstate and never\n# constructs a LowCmd publisher; the trusted host smoke uses it after the\n# simulator's DDS-ready marker.\nadd_executable(dds_lowstate_probe apps/dds_lowstate_probe.cpp)\ntarget_link_libraries(dds_lowstate_probe unitree_sdk2)\n\nadd_executable(single_leg_lift_go2 apps/single_leg_lift_go2.cpp)\ntarget_link_libraries(single_leg_lift_go2 unitree_sdk2)\n\nadd_executable(real_leg_lift_go2\n    leg_lift/real_leg_lift_go2.cpp\n    leg_lift/leg_lift_cli.cpp\n    leg_lift/leg_lift_lifecycle.cpp\n    leg_lift/leg_lift_world.cpp\n    leg_lift/leg_lift_diagnostics.cpp\n    leg_lift/leg_lift_control.cpp\n)\ntarget_link_libraries(real_leg_lift_go2 unitree_sdk2)\n\nadd_executable(real_trot_go2\n    trot/real_trot_go2.cpp\n    trot/trot_cli.cpp\n    trot/trot_task.cpp\n    trot/trot_experiment_lifecycle.cpp\n    trot/trot_experiment_gait.cpp\n    trot/trot_experiment_wbc.cpp\n    trot/trot_experiment_diagnostics.cpp\n    trot/trot_experiment_control.cpp\n)\ntarget_link_libraries(real_trot_go2 unitree_sdk2 Eigen3::Eigen)\n\nset(GO2_MUJOCO_ROOT\n    \"${CMAKE_CURRENT_SOURCE_DIR}/../../simulate/mujoco\" CACHE PATH\n    \"MuJoCo SDK/runtime root used for the controller build\")\nset(_go2_mujoco_lib \"${GO2_MUJOCO_ROOT}/lib/libmujoco.so\")\nset(_go2_mujoco_inc \"${GO2_MUJOCO_ROOT}/include\")\nset(_go2_model_path\n    \"${CMAKE_CURRENT_SOURCE_DIR}/../../unitree_robots/go2/go2.xml\")\nif(EXISTS \"${_go2_mujoco_lib}\")\n    target_include_directories(real_trot_go2 PRIVATE \"${_go2_mujoco_inc}\")\n    target_link_libraries(real_trot_go2 \"${_go2_mujoco_lib}\")\n    target_compile_definitions(\n        real_trot_go2 PRIVATE GO2_MODEL_PATH=\"${_go2_model_path}\")\n    set_target_properties(\n        real_trot_go2 PROPERTIES\n        BUILD_RPATH \"${GO2_MUJOCO_ROOT}/lib\")\nendif()\n\nfunction(go2_add_ctest name)\n    add_test(NAME ${name} COMMAND ${name})\nendfunction()\n\nadd_test(\n    NAME test_dds_runtime\n    COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_dds_runtime.sh\n            ${CMAKE_CURRENT_SOURCE_DIR}/../..)\n\nif(EXISTS \"${_go2_mujoco_lib}\")\n    add_executable(test_go2_forward_kinematics tests/test_go2_forward_kinematics.cpp)\n    target_include_directories(\n        test_go2_forward_kinematics\n        PRIVATE \"${_go2_mujoco_inc}\")\n    target_link_libraries(\n        test_go2_forward_kinematics\n        \"${_go2_mujoco_lib}\")\n    target_compile_definitions(\n        test_go2_forward_kinematics\n        PRIVATE GO2_MODEL_PATH=\"${CMAKE_CURRENT_SOURCE_DIR}/../../unitree_robots/go2/go2.xml\")\n    go2_add_ctest(test_go2_forward_kinematics)\nendif()\n\nadd_executable(test_go2_inverse_kinematics tests/test_go2_inverse_kinematics.cpp)\n\nadd_executable(test_raibert_footstep_planner tests/test_raibert_footstep_planner.cpp)\n\nadd_executable(test_raibert_trot_kernel tests/test_raibert_trot_kernel.cpp)\ntarget_link_libraries(test_raibert_trot_kernel Eigen3::Eigen)\n\nadd_executable(test_cartesian_world_trot tests/test_cartesian_world_trot.cpp)\ngo2_add_ctest(test_cartesian_world_trot)\n\nadd_executable(test_motion_frame_utils tests/test_motion_frame_utils.cpp)\n\nadd_executable(test_velocity_filter tests/test_velocity_filter.cpp)\nadd_executable(test_velocity_command tests/test_velocity_command.cpp)\ngo2_add_ctest(test_velocity_command)\n\nadd_executable(test_trot_task tests/test_trot_task.cpp trot/trot_task.cpp)\n\nadd_executable(test_lean_route_guard\n    tests/test_lean_route_guard.cpp\n    trot/trot_cli.cpp\n    trot/trot_task.cpp)\ntarget_link_libraries(test_lean_route_guard unitree_sdk2 Eigen3::Eigen)\ngo2_add_ctest(test_lean_route_guard)\n\nadd_executable(test_contact_state_filter tests/test_contact_state_filter.cpp)\nadd_executable(test_contact_fusion_fault_harness tests/test_contact_fusion_fault_harness.cpp)\ngo2_add_ctest(test_contact_fusion_fault_harness)\n\nset(CMAKE_BUILD_TYPE Release)\n\nadd_executable(test_contact_wrench_allocator tests/test_contact_wrench_allocator.cpp)\ntarget_link_libraries(test_contact_wrench_allocator Eigen3::Eigen)\n\nadd_executable(test_go2_leg_jacobian tests/test_go2_leg_jacobian.cpp)\ntarget_link_libraries(test_go2_leg_jacobian Eigen3::Eigen)\n\nadd_executable(test_contact_wrench_constraints tests/test_contact_wrench_constraints.cpp)\ntarget_link_libraries(test_contact_wrench_constraints Eigen3::Eigen)\n\nadd_executable(test_contact_torque_mapping tests/test_contact_torque_mapping.cpp)\ntarget_link_libraries(test_contact_torque_mapping Eigen3::Eigen)\n\nadd_executable(test_projected_contact_wrench_allocator tests/test_projected_contact_wrench_allocator.cpp)\ntarget_link_libraries(test_projected_contact_wrench_allocator Eigen3::Eigen)\n\nadd_executable(test_contact_wrench_lexicographic_allocator tests/test_contact_wrench_lexicographic_allocator.cpp)\ntarget_link_libraries(test_contact_wrench_lexicographic_allocator Eigen3::Eigen)\n\nadd_executable(test_dynamic_acceleration_target tests/test_dynamic_acceleration_target.cpp)\n\nadd_executable(test_motion_event_response tests/test_motion_event_response.cpp)\n\nadd_executable(test_wbc_runtime_gate tests/test_wbc_runtime_gate.cpp)\n\n# Order-108 verification-only controller-side lockstep writer tick gate\n# (DDS-free; header-only in trot/lockstep_writer_gate.h).\nadd_executable(test_lockstep_writer_gate tests/test_lockstep_writer_gate.cpp)\ngo2_add_ctest(test_lockstep_writer_gate)\n\n# Order-109 verification-only state-synchronous motion clock (DDS-free).\nadd_executable(test_lockstep_motion_clock tests/test_lockstep_motion_clock.cpp)\ngo2_add_ctest(test_lockstep_motion_clock)\n\n# Order-109b production call-chain integration test. The controller sources\n# are compiled unchanged except for a test-only publish suppression and\n# observability seam; the test drives TrotExperiment::LowCmdWrite itself.\nadd_executable(test_lockstep_motion_clock_integration\n    tests/test_lockstep_motion_clock_integration.cpp\n    trot/trot_task.cpp\n    trot/trot_experiment_lifecycle.cpp\n    trot/trot_experiment_gait.cpp\n    trot/trot_experiment_wbc.cpp\n    trot/trot_experiment_diagnostics.cpp\n    trot/trot_experiment_control.cpp\n)\ntarget_compile_definitions(test_lockstep_motion_clock_integration\n    PRIVATE GO2_TROT_TESTING=1)\ntarget_link_libraries(test_lockstep_motion_clock_integration\n    unitree_sdk2 Eigen3::Eigen)\nif(EXISTS \"${_go2_mujoco_lib}\")\n    target_include_directories(test_lockstep_motion_clock_integration\n        PRIVATE \"${_go2_mujoco_inc}\")\n    target_link_libraries(test_lockstep_motion_clock_integration\n        \"${_go2_mujoco_lib}\")\n    target_compile_definitions(test_lockstep_motion_clock_integration\n        PRIVATE GO2_MODEL_PATH=\"${_go2_model_path}\")\n    set_target_properties(test_lockstep_motion_clock_integration PROPERTIES\n        BUILD_RPATH \"${GO2_MUJOCO_ROOT}/lib\")\nendif()\ngo2_add_ctest(test_lockstep_motion_clock_integration)\n\nadd_executable(test_centroidal_wbc tests/test_centroidal_wbc.cpp)\n\nadd_executable(test_preview_footstep_horizon tests/test_preview_footstep_horizon.cpp)\ntarget_link_libraries(test_preview_footstep_horizon Eigen3::Eigen)\n\nadd_executable(test_dense_qp tests/test_dense_qp.cpp)\ntarget_link_libraries(test_dense_qp Eigen3::Eigen)\n\nadd_executable(test_clean_baseline tests/test_clean_baseline.cpp)\n\nadd_executable(test_contact_wrench_qp tests/test_contact_wrench_qp.cpp)\ntarget_link_libraries(test_contact_wrench_qp Eigen3::Eigen)\n\nif(EXISTS \"${_go2_mujoco_lib}\")\n    add_executable(test_go2_rigid_body tests/test_go2_rigid_body.cpp)\n    target_include_directories(test_go2_rigid_body PRIVATE \"${_go2_mujoco_inc}\")\n    target_link_libraries(test_go2_rigid_body \"${_go2_mujoco_lib}\" Eigen3::Eigen)\n    target_compile_definitions(\n        test_go2_rigid_body PRIVATE GO2_MODEL_PATH=\"${_go2_model_path}\")\n    set_target_properties(\n        test_go2_rigid_body PROPERTIES\n        BUILD_RPATH \"${GO2_MUJOCO_ROOT}/lib\")\n    go2_add_ctest(test_go2_rigid_body)\n\n    add_executable(test_inverse_dynamics_wbc tests/test_inverse_dynamics_wbc.cpp)\n    target_include_directories(\n        test_inverse_dynamics_wbc PRIVATE \"${_go2_mujoco_inc}\")\n    target_link_libraries(\n        test_inverse_dynamics_wb","path":"example/cpp/CMakeLists.txt","sha256":"6f9d85ffba28b9176b5b2b66ccf69c37605b793dbfe73128f0333ba444a944a4","truncated":true},{"chars":2124,"excerpt":"","path":"example/cpp/scripts/README.md","sha256":"7bf90f21c5d9ccf1c6686029dc4c158555b97f4123d016eb3304aaf039a3dee1","truncated":true}],"project_id":"go2-mujoco-control","project_profile_canonical_sha256":"4d42d51738b60efbf25584f03f27e1800f3f342fe026369ef3a47f9c20a1b258","project_profile_raw_sha256":"aa8158ff9e7f267a4a89f8b73e3b81d702c8c12fe20428f140d9e43ff7d80f77","repository":"cwchewang/go2-mujoco-control","schema_version":1}
PRAXIS_CONTEXT_PACK -->
