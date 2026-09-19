# Praxis Task px_1a0baa8b6d2_a6526efb44

Mode: `infrastructure`
Project: `go2-mujoco-control`
Repository: `cwchewang/go2-mujoco-control`
Capability: `go2-mujoco-live`
Approval boundary: `before_host`

## Objective

Validate Praxis Control Plane v0.1 cancel-before-host semantics at the Go2 trusted-host boundary. This is infrastructure acceptance only.

## Context paths

- docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md

## Instructions

- Inspect the frozen TaskSpec and Praxis ContextPack before acting.
- Do not alter controller, simulator, scene, gait, safety parameters, or the frozen host command.
- If a post-host closeout occurs, write only docs/validation/praxis_control_plane_v01_cancel_20260920/RESULTS.md.

## Constraints

- Exactly one trusted host invocation is permitted only after explicit approval.
- Do not substitute parameters, domain id, run directory, or launch command.
- This task is not locomotion science and makes no controller-quality claim.

## Allowed mutations

- docs/validation/praxis_control_plane_v01_cancel_20260920/

## Frozen parameters

```json
{
  "control_plane_version": "v0.1",
  "dogfood_kind": "cancel-before-host"
}
```

## Resource budget

```json
{
  "cpu_slots": null,
  "gpu_count": 0,
  "memory_gb": null,
  "wall_time_seconds": 1800
}
```

## Attempt policy

```json
{
  "max_scientific_attempts": 1,
  "retry_preflight": true,
  "scientific_boundary": "trusted Go2 host launch"
}
```

## Approval policy

```json
{
  "reason": "Explicitly authorize crossing the trusted host/scientific boundary.",
  "required_before": "before_host"
}
```

## Required evidence

- exact frozen task and candidate commit
- Praxis ContextPack default-branch SHA and instruction hashes
- approval or cancellation boundary
- trusted host record if and only if host execution was approved

## Stop rule

Stop without host execution if cancellation is requested before approval. Once host execution starts, preserve evidence and complete closeout.

## Closeout schema

- CONTROL PLANE FACTS
- CONTEXTPACK FACTS
- APPROVAL/CANCEL BOUNDARY
- HOST FACTS
- ACCEPTANCE

## Frozen TaskSpec

The following machine-readable block is the canonical task request.

```json
{
  "allowed_mutations": [
    "docs/validation/praxis_control_plane_v01_cancel_20260920/"
  ],
  "approval_policy": {
    "reason": "Explicitly authorize crossing the trusted host/scientific boundary.",
    "required_before": "before_host"
  },
  "attempt_policy": {
    "max_scientific_attempts": 1,
    "retry_preflight": true,
    "scientific_boundary": "trusted Go2 host launch"
  },
  "capability": "go2-mujoco-live",
  "capability_request": {
    "command": [
      "bash",
      "example/cpp/scripts/run_trot_exact_source.sh",
      "45",
      "example/cpp/experiments/_runs/praxis_v01_cancel_gate_20260920_r1",
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
      "216"
    ],
    "domain_id": 216,
    "environment": {},
    "run_dir": "example/cpp/experiments/_runs/praxis_v01_cancel_gate_20260920_r1",
    "schema_version": 1,
    "timeout_s": 300
  },
  "closeout_schema": [
    "CONTROL PLANE FACTS",
    "CONTEXTPACK FACTS",
    "APPROVAL/CANCEL BOUNDARY",
    "HOST FACTS",
    "ACCEPTANCE"
  ],
  "constraints": [
    "Exactly one trusted host invocation is permitted only after explicit approval.",
    "Do not substitute parameters, domain id, run directory, or launch command.",
    "This task is not locomotion science and makes no controller-quality claim."
  ],
  "context_paths": [
    "docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md"
  ],
  "frozen_parameters": {
    "control_plane_version": "v0.1",
    "dogfood_kind": "cancel-before-host"
  },
  "instructions": [
    "Inspect the frozen TaskSpec and Praxis ContextPack before acting.",
    "Do not alter controller, simulator, scene, gait, safety parameters, or the frozen host command.",
    "If a post-host closeout occurs, write only docs/validation/praxis_control_plane_v01_cancel_20260920/RESULTS.md."
  ],
  "mode": "infrastructure",
  "objective": "Validate Praxis Control Plane v0.1 cancel-before-host semantics at the Go2 trusted-host boundary. This is infrastructure acceptance only.",
  "project": {
    "profile_path": ".atlas/project.json",
    "project_id": "go2-mujoco-control",
    "repository": "cwchewang/go2-mujoco-control"
  },
  "required_evidence": [
    "exact frozen task and candidate commit",
    "Praxis ContextPack default-branch SHA and instruction hashes",
    "approval or cancellation boundary",
    "trusted host record if and only if host execution was approved"
  ],
  "resources": {
    "cpu_slots": null,
    "gpu_count": 0,
    "memory_gb": null,
    "wall_time_seconds": 1800
  },
  "schema_version": 1,
  "stop_rule": "Stop without host execution if cancellation is requested before approval. Once host execution starts, preserve evidence and complete closeout."
}
```

<!-- PRAXIS_TASK_SPEC
{"allowed_mutations":["docs/validation/praxis_control_plane_v01_cancel_20260920/"],"approval_policy":{"reason":"Explicitly authorize crossing the trusted host/scientific boundary.","required_before":"before_host"},"attempt_policy":{"max_scientific_attempts":1,"retry_preflight":true,"scientific_boundary":"trusted Go2 host launch"},"capability":"go2-mujoco-live","capability_request":{"command":["bash","example/cpp/scripts/run_trot_exact_source.sh","45","example/cpp/experiments/_runs/praxis_v01_cancel_gate_20260920_r1","--controller-duration","15","--kernel","raibert-trot","--period","0.60","--duty","0.75","--step-length","0.091","--foot-lift","0.020","--kp","63","--kd","2.8","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--clean-baseline","--tau-limit","35","--max-cycles","6","--headless","--domain-id","216"],"domain_id":216,"environment":{},"run_dir":"example/cpp/experiments/_runs/praxis_v01_cancel_gate_20260920_r1","schema_version":1,"timeout_s":300},"closeout_schema":["CONTROL PLANE FACTS","CONTEXTPACK FACTS","APPROVAL/CANCEL BOUNDARY","HOST FACTS","ACCEPTANCE"],"constraints":["Exactly one trusted host invocation is permitted only after explicit approval.","Do not substitute parameters, domain id, run directory, or launch command.","This task is not locomotion science and makes no controller-quality claim."],"context_paths":["docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md"],"frozen_parameters":{"control_plane_version":"v0.1","dogfood_kind":"cancel-before-host"},"instructions":["Inspect the frozen TaskSpec and Praxis ContextPack before acting.","Do not alter controller, simulator, scene, gait, safety parameters, or the frozen host command.","If a post-host closeout occurs, write only docs/validation/praxis_control_plane_v01_cancel_20260920/RESULTS.md."],"mode":"infrastructure","objective":"Validate Praxis Control Plane v0.1 cancel-before-host semantics at the Go2 trusted-host boundary. This is infrastructure acceptance only.","project":{"profile_path":".atlas/project.json","project_id":"go2-mujoco-control","repository":"cwchewang/go2-mujoco-control"},"required_evidence":["exact frozen task and candidate commit","Praxis ContextPack default-branch SHA and instruction hashes","approval or cancellation boundary","trusted host record if and only if host execution was approved"],"resources":{"cpu_slots":null,"gpu_count":0,"memory_gb":null,"wall_time_seconds":1800},"schema_version":1,"stop_rule":"Stop without host execution if cancellation is requested before approval. Once host execution starts, preserve evidence and complete closeout."}
PRAXIS_TASK_SPEC -->

<!-- PRAXIS_CAPABILITY_REQUEST
{"command":["bash","example/cpp/scripts/run_trot_exact_source.sh","45","example/cpp/experiments/_runs/praxis_v01_cancel_gate_20260920_r1","--controller-duration","15","--kernel","raibert-trot","--period","0.60","--duty","0.75","--step-length","0.091","--foot-lift","0.020","--kp","63","--kd","2.8","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--clean-baseline","--tau-limit","35","--max-cycles","6","--headless","--domain-id","216"],"domain_id":216,"environment":{},"run_dir":"example/cpp/experiments/_runs/praxis_v01_cancel_gate_20260920_r1","schema_version":1,"timeout_s":300}
PRAXIS_CAPABILITY_REQUEST -->

## Praxis ContextPack

Trusted dispatch-time context. Runtime facts may add to this; they must not silently replace these frozen repository facts.

- Project: `go2-mujoco-control`
- Repository: `cwchewang/go2-mujoco-control`
- Default branch: `main`
- Default branch SHA: `ce53d212d08bb8d1d737bb03b46c352c6afdefd2`
- Project profile SHA-256: `4d42d51738b60efbf25584f03f27e1800f3f342fe026369ef3a47f9c20a1b258`

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

<!-- PRAXIS_CONTEXT_PACK
{"default_branch":"main","default_branch_sha":"ce53d212d08bb8d1d737bb03b46c352c6afdefd2","instructions":[{"chars":2186,"excerpt":"# Go2 repository rules\n\n`main` is the stable code line and long-term route. The active research\nfrontier may live on a separate `research/*` branch. This file contains\nrepository guardrails; it is not a scientific plan or current-status report.\n\n## Task discovery bootstrap\n\nBefore accepting, declining, or executing any task from a local worktree, first\nrefresh the remote source of truth:\n\n1. run `git fetch origin --prune`;\n2. read `origin/main:CURRENT.md` (for example with\n   `git show origin/main:CURRENT.md`) to discover the active research branch;\n3. compare the local active branch/worktree with `origin/<active-branch>` and\n   fast-forward only when safe; never reset, discard, or delete local commits,\n   untracked files, or raw evidence to make it match;\n4. only after that, read the active branch `CURRENT.md`, current task, and exact\n   parent/closeout evidence.\n\nA stale local `CURRENT.md`, local branch tip, or cached task is never sufficient\nto conclude that no new task exists. If the local branch is ahead or diverged,\npreserve it and report the divergence instead of guessing which side wins.\n\nRead [`CURRENT.md`](CURRENT.md) for the single maintained frontier pointer.\nFollow that pointer to the frontier branch, its task, and exact `RESULTS.md`.\nUse the canonical [Research Execution SOP](docs/research/SOP.md) from\n`main`. A branch-local `CURRENT.md` is navigation only and cannot override\n`main/CURRENT.md`, the SOP, or the active task.\n\nThe active task owns the scientific question, intervention, frozen variables,\nrun budget, thresholds, and classification. Do not infer research direction\nfrom Atlas directories, dated worktrees, old branches, commit messages, or\narchived code. Do not change controller/planner behavior or scientific\nmeaning under an infrastructure-only task.\n\nNo live experiment is authorized by this file alone. Before any live run,\nfollow the task and SOP, verify the exact branch/HEAD and clean worktree, and\npreserve raw evidence. Everything below\n`example/cpp/experiments/_runs/` is ignored local evidence: never commit,\ndelete, overwrite, rename, or treat it as instruction. Curated evidence\nrequires its own manifest and provenance.\n","path":"AGENTS.md","sha256":"0e5f638d56a9bf10fd1a1718a346e46c17cddcfdd3a7e82dc6985d495aecdcec","truncated":false},{"chars":8306,"excerpt":"# Research Execution SOP v0.2\n\nStatus: active for new research checkpoints after adoption. Historical checkpoints keep the rules frozen with them.\n\nThis SOP is intentionally small. The normal path should feel like: **short task → preflight → run → closeout**.\n\n## 1. Core rule\n\n**Scientific variables are strict; execution engineering is flexible before live; after scientific capture begins, results may not be selected or retried opportunistically.**\n\n- **Sol** owns the scientific question and final scientific judgment.\n- **Luna** independently owns execution readiness and has unconditional live veto.\n\nA task is not permission to bypass a verified infrastructure constraint.\n\n## 2. What a task contains\n\nA task describes the **delta from its exact parent**, not the whole project.\n\nFor a live checkpoint it needs only:\n\n- mode: `infrastructure`, `exploratory`, or `confirmatory`;\n- question;\n- exact parent/base;\n- scientific change;\n- variables that must remain frozen;\n- run budget;\n- primary measurements / classification rule;\n- runner and run directory;\n- genuinely task-specific preflight requirements, if any.\n\nDo not restate SOP rules, parent results, unchanged thresholds, or long historical narratives. Read the current task, this SOP, and the exact parent `RESULTS.md`; consult older tasks only when evidence actually requires them.\n\n## 3. Scientific authority\n\nFor confirmatory work, Sol freezes the intervention, baseline, run budget, primary metrics, thresholds/classification, and scientific stop conditions.\n\nLuna must not autonomously change anything that could alter the post-handoff state/control trajectory or the scientific meaning of the primary evidence. This includes speed policy, gait timing, planner mathematics, WBC/MPC/ID behavior, controller gains, scene geometry, safety limits, scientific thresholds, seed/run count, or follow-up experiments.\n\nIf uncertain whether a change is execution-only or scientific/runtime-semantic, treat it as scientific and veto live.\n\n## 4. Luna autonomy and veto\n\nBefore scientific capture, Luna may independently inspect and minimally repair execution-only issues such as:\n\n- DDS/domain choice, locks and port conflicts;\n- paths, run-directory bookkeeping and executable bits;\n- runner shell plumbing that is proven trajectory-neutral;\n- logger/schema bookkeeping;\n- analyzer/tooling plumbing that does not change primary evidence meaning;\n- provenance collection, stale process cleanup, and no-live tests.\n\nLuna may add no-live tests without asking.\n\nIf the task conflicts with verified source semantics, geometry, protocol limits, accepted evidence, or preflight, Luna must veto rather than weaken an existing guard to obey the task.\n\n## 5. Preflight\n\nEvery live run must pass `tools/research/preflight.py` immediately before launch.\n\nAlways check:\n\n- exact branch/HEAD and clean worktree;\n- runner existence/syntax and actual DDS domain;\n- DDS/RTPS port legality, selected safe policy and free lock;\n- fresh run directory;\n- no stale simulator/controller/runner process;\n- task-required files/hashes/tests.\n\nUse `--diff-base <accepted-ref>` whenever an accepted parent/baseline exists. Preflight auto-detects changed execution surfaces from Git diff; `--changed-surface` is only an override/addition.\n\nChange-triggered checks:\n\n- runtime/schema/scene change → at least one relevant no-live/build test;\n- schema change → schema regression test;\n- primary analyzer semantics change → parser/fixture test;\n- runner change → record a baseline runner diff summary and inspect the actual Git diff;\n- geometry-dependent scientific gate change → re-derive it from source/scene geometry.\n\n### Sol review gate\n\nSecond Sol review is required only when the committed change can alter either:\n\n1. the post-handoff state/control trajectory; or\n2. the meaning/mapping/classification of primary evidence.\n\nRuntime, scene and schema changes trigger this automatically. A runner or analyzer change triggers it only when its actual semantics meet one of those two conditions; Luna must pass `--requires-sol-review` in that case.\n\nPure paths, output locations, report rendering, bookkeeping, or presentation-only analysis changes do not require redundant Sol review.\n\nWhen review is required, the exact reviewed SHA must equal the live HEAD via `--approved-head`.\n\n## 6. Attempt boundary and retry\n\nA scientific attempt is consumed at the first valid **post-handoff state/control sample** used by the experiment.\n\n- **Prelaunch failure:** no attempt consumed; Luna may fix execution-only issues and rerun preflight.\n- **Boot failure before that sample:** no scientific attempt consumed. One automatic recovery launch is allowed only if the cause is proven execution-only, failed artifacts are preserved, scientific/runtime semantics are unchanged, and preflight passes again.\n- **Scientific capture started:** run budget is consumed. No autonomous retry, replacement run, domain change, or tuning.\n\nScientific gate failures stop; infrastructure gate failures before capture may be repaired in the same checkpoint.\n\n## 7. Evidence\n\nOnce capture starts, raw artifacts are immutable. Do not overwrite, normalize, or hand-edit raw evidence.\n\nPrefer deterministic offline salvage over rerunning. A repair is scientifically usable only when:\n\n- raw bytes remain unchanged;\n- the mapping/repair is unique;\n- it follows from frozen runtime source/protocol rather than outcome preference;\n- independent semantic invariants validate it;\n- derivation and provenance are recorded.\n\nDo not preregister a guessed bug shape when uniqueness/source-grounded recoverability is the real requirement.\n\nHistorical conclusions are append-only; a later correction may supersede an interpretation without erasing it.\n\n## 8. Failure triage\n\nAfter a failed run, identify the earliest failed boundary before designing another experiment:\n\n1. `execution`\n2. `evidence`\n3. `causal`\n4. `scientific`\n\nDo not invent a new generic classification label for every infrastructure failure. Record the boundary plus a specific `reason_code`; scientific labels remain task-specific.\n\n## 9. Exploratory vs confirmatory\n\n- `infrastructure`: tooling/repair only; no scientific claim.\n- `exploratory`: bounded search/debugging authorized in advance; useful for design, not confirmatory evidence.\n- `confirmatory`: intervention, run budget, thresholds and classification frozen before live.\n\nDo not force tuning into repeated fake one-run confirmatory checkpoints. Explore first when necessary, then freeze and validate.\n\n## 10. Branches and outputs\n\nCreate a new research branch for a new scientific question, new live attempt, or runtime-semantic change.\n\nPure offline correction, evidence salvage, analyzer repair, or additional derived analysis may continue on the same research branch when raw evidence and scientific design are unchanged. Append a new commit/closeout and mark supersession when needed.\n\nDefault closeout artifacts are only:\n\n- `RESULTS.md`\n- `analysis.json`\n- `provenance.csv`\n\nCreate extra CSV/tables only when they are actual evidence needed to audit that checkpoint.\n\nProvenance should hash what matters to the conclusion: raw evidence, scene/model/config where relevant, and exact runtime/source/binary identity. Do not hash every derived report by ritual.\n\n## 11. Lessons already encoded\n\nThis SOP specifically addresses failures already seen in this project:\n\n- DDS domain 233 → actual RTPS/domain preflight + Luna veto;\n- missing `--wall-clock-motion` → runner comparison against accepted baseline;\n- invalid `base x < 0.65` pre-step gate → source/scene-derived geometry review;\n- 780/776 CSV mismatch → schema regression test before live;\n- guessed empty-token recovery rule → general uniqueness/source-invariant evidence recovery;\n- unnecessary branch/checkpoint churn → execution repair before capture and same-branch offline corrections.\n\n## 12. Authority and version\n\nFor checkpoints adopting this SOP:\n\n1. frozen scientific delta in the current task;\n2. this SOP for execution/veto/retry/evidence rules;\n3. exact parent/baseline evidence;\n4. older history as needed.\n\n`PHASE1_AGENT_CONTRACT.md` remains historical authority only for checkpoints created under it.\n\nCurrent version: **v0.2**. Git history is the changelog; no separate release ceremony is required.\n","path":"docs/research/SOP.md","sha256":"fd3c9d1b2f29ee3924794e5984ead53a2e7de06cf87465eb38f3860439281e2b","truncated":false},{"chars":6965,"excerpt":"# Canonical clean-baseline integration closeout\n\nDate: `2026-09-17`\n\nTask commit: `7ab6fbf6e08e57d0d6d1b536ab7870887ac602e7`\n\nExact main parent: `041c36c499ff24ab6c8edf74fa6283e0ba923db6`\n\nMode: `engineering-correctness / no-live / canonicalization`\n\nProposed Luna classification: `CANONICAL_CLEAN_BASELINE_READY`\n\n## FACTS\n\n- No simulator/controller pair or locomotion run was launched. Raw `_runs`\n  evidence was not modified.\n- The accepted reference commits were inspected as trees and evidence sources,\n  not merged or cherry-picked as history:\n  - P0 clean-baseline source/reference: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`;\n  - accepted DDS root-fix result: `2eb92bc62be6fba2dee26ac9229520d8835c6246`;\n  - validated flat result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`;\n  - exact validated live candidate/wrapper source: `0009b5fbd1e962e38135922da61245a99b522aab`.\n- The port is limited to the clean controller seams, focused tests, tracked DDS\n  runtime/probe/exact-source plumbing, build-root portability, and canonical\n  documentation. Historical task documents, intermediate recovery scaffolds,\n  and full historical analysis were not imported.\n- Clean controller implementation is in:\n  `example/cpp/wbc/clean_baseline.h`,\n  `example/cpp/kinematics/go2_inverse_kinematics.h`,\n  `example/cpp/wbc/inverse_dynamics_wbc.h`,\n  `example/cpp/trot/trot_experiment_gait.cpp`,\n  `example/cpp/trot/trot_experiment_wbc.cpp`, and\n  `example/cpp/trot/trot_experiment_control.cpp`.\n- Canonical runtime implementation is in\n  `example/cpp/scripts/dds_runtime.sh`, `run_trot.sh`,\n  `run_trot_exact_source.sh`, `dds_runtime_root_smoke.sh`, and the read-only\n  `apps/dds_lowstate_probe.cpp`; `example/cpp/CMakeLists.txt` and\n  `simulate/CMakeLists.txt` accept explicit SDK roots.\n- Accepted flat evidence remains externally auditable at the referenced\n  closeout and host-record paths. Its frozen command and core result are\n  preserved: `64/64` cycles, nominal `0.1516666667 m/s`, measured OLS speed\n  about `0.153806 m/s`, and zero primary rejection/safety counts.\n- Validation completed without live execution: full controller CTest `34/34`,\n  including `test_dds_runtime`, `test_clean_baseline`,\n  `test_go2_inverse_kinematics`, `test_inverse_dynamics_wbc`,\n  `test_terrain_interfaces`, and `test_lean_route_guard`; the simulator\n  `test_lockstep` unit test also passed. The simulator-launch integration CTest\n  was excluded by the no-live task boundary.\n- `bash -n` passed for all canonical shell scripts and `git diff --check`\n  passed. The required remote refresh was attempted but the linked worktree’s\n  Git metadata rejected `FETCH_HEAD` writes as read-only; the supplied exact\n  task ref, `HEAD`, `origin/main`, and accepted reference refs were verified\n  read-only without changing Git metadata.\n\n## INVARIANT AUDIT\n\n1. **Planner/foot target identity — PASS.** Clean gait target construction\n   calls `ResolveFootTargetsToJointPositions` with the requested targets and\n   does not call the legacy clamped solver. The direct-IK rejection and\n   non-mutation cases pass in `test_go2_inverse_kinematics` and\n   `test_clean_baseline`.\n2. **Authoritative joint limits — PASS.** Clean acceptance checks the Go2\n   ranges represented in `unitree_robots/go2/go2.xml`, including distinct front\n   and rear thigh ranges, after direct IK. The joint-range-invalid fixture is\n   rejected without projection.\n3. **Strict optimizer acceptance — PASS.** `require_qp_acceptance` rejects a\n   failed constrained solve before its iterate can become output. The dense-QP\n   rejection fixture and strict ID-WBC test pass; clean runtime failure clears\n   solver/mapping acceptance and cannot reuse a stale result.\n4. **Correct swing acceleration — PASS.** `AddSwingFootAccelerationTask`\n   includes `Jdot*qdot` in the acceleration residual. The focused swing test\n   checks both the gradient term and Hessian.\n5. **No post-optimizer actuation overlays — PASS.** Clean\n   `WriteMotorCommands` returns through the accepted torque plus the explicit\n   final finite/ramp/absolute envelope. Legacy force, lean, Cartesian, and\n   sprint overlays are enclosed by `!params_.clean_baseline`.\n6. **Final command identity — PASS.** Clean LowCmd torque is sourced from the\n   mapped accepted ID-WBC torque and passed only to\n   `ApplyFinalTorqueSafetyEnvelope`; failed WBC uses a zero-feedforward safe\n   hold rather than a legacy command path.\n7. **Fail closed — PASS.** Direct target failure requests the existing stop\n   sequence, strict WBC failure disables primary output, and clean command\n   writing emits a zero-feedforward hold instead of falling back to legacy\n   torque/position overlays. The route and contract tests cover these seams.\n8. **Cartesian-world incompatibility — PASS.** CLI validation rejects\n   `--clean-baseline --cartesian-world`, and `test_lean_route_guard` passes.\n\n## LEGACY ISOLATION\n\n- `AllLegInverseKinematicsClamped` and `ClampFootToHipWorkspace` remain only\n  for compatibility and are explicitly labeled legacy. The clean target branch\n  precedes both legacy paths and uses a const requested-target boundary.\n- Cartesian-world is a separate CLI route and is fail-closed against clean\n  mode. Its post-WBC behavior cannot be reached after clean mode is selected.\n- Terrain observation remains sensor-only in the maintained runtime. The\n  `TerrainPlannerConfig` actuation boundary now rejects any actuation-capable\n  planner unless `clean_baseline_contract` is explicitly enabled; its focused\n  test proves the rejection and the opt-in contract path.\n- The legacy helpers were not deleted because existing compatibility callers\n  and historical tests still depend on them. They are not the clean extension\n  seam or default Phase-2 route.\n\n## CANONICAL SURFACE\n\nFuture Phase-2 work should start from `CURRENT.md`, use the tracked DDS layer\nthrough `example/cpp/scripts/run_trot.sh`, and extend only this contract:\n\n`gait/foothold + predicted body/hip state -> clean swing planner -> exact foot targets -> direct IK feasibility -> strict WBC -> final safety envelope`\n\nThe clean controller entry is `real_trot_go2 ... --clean-baseline`; Cartesian\nworld and legacy terrain-actuation options remain separate or retired. Exact\nsource builds use `simulate/CMakeLists.txt` with `-DMUJOCO_ROOT` and\n`example/cpp/CMakeLists.txt` with `-DGO2_MUJOCO_ROOT`. The read-only DDS probe\nis `dds_lowstate_probe --domain-id N --interface lo`.\n\n## LUNA INTERPRETATION\n\n`CANONICAL_CLEAN_BASELINE_READY` is proposed because the minimal accepted clean\nimplementation is coherently integrated on current-main ancestry, all eight\ncontrol invariants have source and focused-test evidence, the accepted flat and\nDDS records remain referenced with hashes, and legacy clamp/overlay entry is\nexplicitly isolated. This is an offline integration result. It does not claim\nnew repeatability or authorize a live run; repeatability remains a later task\nafter protected-main integration.\n","path":"docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md","sha256":"0aac77c9064dfe9079f70dc01cfd0f970c9e7d7b59e2f44ae9080c9768d6fd42","truncated":false}],"project_id":"go2-mujoco-control","project_profile_sha256":"4d42d51738b60efbf25584f03f27e1800f3f342fe026369ef3a47f9c20a1b258","repository":"cwchewang/go2-mujoco-control","schema_version":1}
PRAXIS_CONTEXT_PACK -->

<!-- ATLAS_HOST_EXPERIMENT
{"command":["bash","example/cpp/scripts/run_trot_exact_source.sh","45","example/cpp/experiments/_runs/praxis_v01_cancel_gate_20260920_r1","--controller-duration","15","--kernel","raibert-trot","--period","0.60","--duty","0.75","--step-length","0.091","--foot-lift","0.020","--kp","63","--kd","2.8","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--clean-baseline","--tau-limit","35","--max-cycles","6","--headless","--domain-id","216"],"domain_id":216,"environment":{},"run_dir":"example/cpp/experiments/_runs/praxis_v01_cancel_gate_20260920_r1","schema_version":1,"timeout_s":300}
ATLAS_HOST_EXPERIMENT -->
