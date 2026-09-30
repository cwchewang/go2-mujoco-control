# Praxis Task px_1a0f264f667_fe755912dd

Mode: `infrastructure`
Project: `go2-mujoco-control`
Repository: `cwchewang/go2-mujoco-control`
Approval boundary: `none`

## Objective

Implement and document a reproducible source-conditioned MJPC Go2 comparator engineering admission based on the already pinned johnzhang3/mujoco_mpc commit e00c47a5adb9856af2e0f24231bb3a60d5be23c4. This closes the mature-controller audit stage without claiming a scientific capability comparison. The admission must use the upstream Agent + QuadrupedFlat closed-loop call sequence headlessly, encode the two compatibility conditions discovered on Atlas, produce bounded engineering evidence, and advance the repo's NEXT status to prospective aligned multi-controller comparison.

## Context paths

- docs/PROJECT_RECORD.md
- docs/TOPIC_AUDIT.md
- docs/adr/ADR-0001-mujoco-mjx-evaluation-substrate.md
- tools/substrate/sources.lock.json
- tools/substrate/native/CMakeLists.txt
- tools/substrate/native/admit.cc
- tools/substrate/README.md
- docs/research/SOP.md

## Instructions

- Start from current main HEAD 83b3833f53f66f404cf5f428b9648860adb88323 and require a clean checkout. Create a dedicated task branch/worktree following repo conventions.
- Do not change the pinned MJPC commit or edit the upstream .substrate/mjpc tracked source checkout.
- Add a source-bound, GUI-free engineering comparator admission using the upstream Agent + QuadrupedFlat semantics rather than the previous direct iLQG-only static admission.
- Make the GCC Release strict-aliasing workaround explicit and auditable. The pinned upstream utilities use reinterpret-based double/int selection storage; compile the relevant comparator target with -fno-strict-aliasing or an equivalently explicit build-level compatibility condition without rewriting upstream source. Record compiler flags in evidence.
- Make the actuator semantic correction explicit and fail-closed. The pinned task_flat includes go2.xml where gainprm=60 and biasprm='0 -60 -5' are present but biastype is not affine, causing constant-force rather than intended PD semantics under MuJoCo 3.3.6. For this source-conditioned comparator admission only, correct the internal comparator model to mjBIAS_AFFINE after validating the exact expected source semantics. Do not silently change the canonical evaluation plant and do not switch to go2_identified.xml because that changes additional armature/friction parameters.
- The engineering probe should initialize upstream task state, then command Walk mode, Manual gait switch, Trot, Walk speed 1.0 m/s, Walk turn 0, and run a bounded headless closed loop. It must clearly label output as engineering/source-conditioned admission, not aligned benchmark evidence.
- Include a plant-only home-hold semantic check demonstrating that the corrected affine actuator behavior is stable enough to distinguish the source bug from MPC behavior.
- Add tests that fail if upstream source semantics/pin change, if compatibility corrections are not declared, or if output metadata omits source commit/compiler/task/model/compatibility details.
- Run only infrastructure/engineering validation, with max_scientific_attempts=0. No terrain capability map, no paper-gap claim, no threshold tuning.
- Create a concise validation closeout under docs/validation/ with exact commands/results. Preserve informal /tmp observations only as motivation; authoritative evidence must come from this prospective task.
- Update PROJECT_RECORD and TOPIC_AUDIT only to the bounded conclusion: the mature Go2 MJPC implementation is reusable as a comparator after explicit source-compatibility handling; generic TaskSpec/ScenarioSpec/InformationSpec/TimingSpec/ControllerAdapter/Evaluator remains unimplemented; next step is a prospective aligned comparison task sharing canonical evaluation semantics.
- Update CURRENT/current.json if repo conventions require it so handoff points to the new engineering frontier. Do not claim Gate 0 complete.
- Commit changes on the dedicated branch. Push the branch if normal repo task convention permits; do not merge to main.

## Constraints

- No scientific attempts or formal capability conclusions.
- No mutation of sealed #189 evidence or historical raw runs.
- No change to MJPC/RL source pins.
- No GUI/GLFW dependency requirement.
- No hardware/DDS execution.
- Do not implement the full generic multi-controller contract in this task.
- Do not modify main directly or force-update refs.

## Allowed mutations

- repository branch/worktree files
- ignored build artifacts
- new validation evidence
- git commit
- git push dedicated branch

## Frozen parameters

```json
{
  "base_head": "83b3833f53f66f404cf5f428b9648860adb88323",
  "command_mode": "Walk",
  "gait": "Trot",
  "gait_switch": "Manual",
  "mjpc_commit": "e00c47a5adb9856af2e0f24231bb3a60d5be23c4",
  "mujoco_version": "3.3.6",
  "scientific_attempts": 0,
  "walk_speed_mps": 1,
  "walk_turn_radps": 0
}
```

## Resource budget

```json
{
  "cpu_slots": 8,
  "gpu_count": 0,
  "memory_gb": 12.0,
  "wall_time_seconds": 1200
}
```

## Attempt policy

```json
{
  "max_scientific_attempts": 0,
  "retry_preflight": true,
  "scientific_boundary": null
}
```

## Approval policy

```json
{
  "reason": "User approved continuing the Go2 project; infrastructure-only task with no scientific attempt.",
  "required_before": "none"
}
```

## Required evidence

- exact base/source identity
- headless upstream Agent comparator build
- declared strict-aliasing compatibility flag
- validated actuator biastype correction
- plant home-hold engineering result
- bounded Walk/Trot engineering result
- tests
- git diff/status
- validation closeout
- commit SHA

## Stop rule

Stop without broadening scope if exact pinned upstream semantics differ from the predeclared assumptions, if the headless comparator cannot build without GUI dependencies, or if engineering validation is unstable. Report the blocker rather than altering scientific semantics.

## Closeout schema

- identity
- implementation
- compatibility
- tests
- engineering_evidence
- documentation
- git

## Frozen TaskSpec

The following machine-readable block is the canonical task request.

```json
{
  "allowed_mutations": [
    "repository branch/worktree files",
    "ignored build artifacts",
    "new validation evidence",
    "git commit",
    "git push dedicated branch"
  ],
  "approval_policy": {
    "reason": "User approved continuing the Go2 project; infrastructure-only task with no scientific attempt.",
    "required_before": "none"
  },
  "attempt_policy": {
    "max_scientific_attempts": 0,
    "retry_preflight": true,
    "scientific_boundary": null
  },
  "capability": null,
  "capability_request": null,
  "closeout_schema": [
    "identity",
    "implementation",
    "compatibility",
    "tests",
    "engineering_evidence",
    "documentation",
    "git"
  ],
  "constraints": [
    "No scientific attempts or formal capability conclusions.",
    "No mutation of sealed #189 evidence or historical raw runs.",
    "No change to MJPC/RL source pins.",
    "No GUI/GLFW dependency requirement.",
    "No hardware/DDS execution.",
    "Do not implement the full generic multi-controller contract in this task.",
    "Do not modify main directly or force-update refs."
  ],
  "context_paths": [
    "docs/PROJECT_RECORD.md",
    "docs/TOPIC_AUDIT.md",
    "docs/adr/ADR-0001-mujoco-mjx-evaluation-substrate.md",
    "tools/substrate/sources.lock.json",
    "tools/substrate/native/CMakeLists.txt",
    "tools/substrate/native/admit.cc",
    "tools/substrate/README.md",
    "docs/research/SOP.md"
  ],
  "frozen_parameters": {
    "base_head": "83b3833f53f66f404cf5f428b9648860adb88323",
    "command_mode": "Walk",
    "gait": "Trot",
    "gait_switch": "Manual",
    "mjpc_commit": "e00c47a5adb9856af2e0f24231bb3a60d5be23c4",
    "mujoco_version": "3.3.6",
    "scientific_attempts": 0,
    "walk_speed_mps": 1,
    "walk_turn_radps": 0
  },
  "instructions": [
    "Start from current main HEAD 83b3833f53f66f404cf5f428b9648860adb88323 and require a clean checkout. Create a dedicated task branch/worktree following repo conventions.",
    "Do not change the pinned MJPC commit or edit the upstream .substrate/mjpc tracked source checkout.",
    "Add a source-bound, GUI-free engineering comparator admission using the upstream Agent + QuadrupedFlat semantics rather than the previous direct iLQG-only static admission.",
    "Make the GCC Release strict-aliasing workaround explicit and auditable. The pinned upstream utilities use reinterpret-based double/int selection storage; compile the relevant comparator target with -fno-strict-aliasing or an equivalently explicit build-level compatibility condition without rewriting upstream source. Record compiler flags in evidence.",
    "Make the actuator semantic correction explicit and fail-closed. The pinned task_flat includes go2.xml where gainprm=60 and biasprm='0 -60 -5' are present but biastype is not affine, causing constant-force rather than intended PD semantics under MuJoCo 3.3.6. For this source-conditioned comparator admission only, correct the internal comparator model to mjBIAS_AFFINE after validating the exact expected source semantics. Do not silently change the canonical evaluation plant and do not switch to go2_identified.xml because that changes additional armature/friction parameters.",
    "The engineering probe should initialize upstream task state, then command Walk mode, Manual gait switch, Trot, Walk speed 1.0 m/s, Walk turn 0, and run a bounded headless closed loop. It must clearly label output as engineering/source-conditioned admission, not aligned benchmark evidence.",
    "Include a plant-only home-hold semantic check demonstrating that the corrected affine actuator behavior is stable enough to distinguish the source bug from MPC behavior.",
    "Add tests that fail if upstream source semantics/pin change, if compatibility corrections are not declared, or if output metadata omits source commit/compiler/task/model/compatibility details.",
    "Run only infrastructure/engineering validation, with max_scientific_attempts=0. No terrain capability map, no paper-gap claim, no threshold tuning.",
    "Create a concise validation closeout under docs/validation/ with exact commands/results. Preserve informal /tmp observations only as motivation; authoritative evidence must come from this prospective task.",
    "Update PROJECT_RECORD and TOPIC_AUDIT only to the bounded conclusion: the mature Go2 MJPC implementation is reusable as a comparator after explicit source-compatibility handling; generic TaskSpec/ScenarioSpec/InformationSpec/TimingSpec/ControllerAdapter/Evaluator remains unimplemented; next step is a prospective aligned comparison task sharing canonical evaluation semantics.",
    "Update CURRENT/current.json if repo conventions require it so handoff points to the new engineering frontier. Do not claim Gate 0 complete.",
    "Commit changes on the dedicated branch. Push the branch if normal repo task convention permits; do not merge to main."
  ],
  "mode": "infrastructure",
  "objective": "Implement and document a reproducible source-conditioned MJPC Go2 comparator engineering admission based on the already pinned johnzhang3/mujoco_mpc commit e00c47a5adb9856af2e0f24231bb3a60d5be23c4. This closes the mature-controller audit stage without claiming a scientific capability comparison. The admission must use the upstream Agent + QuadrupedFlat closed-loop call sequence headlessly, encode the two compatibility conditions discovered on Atlas, produce bounded engineering evidence, and advance the repo's NEXT status to prospective aligned multi-controller comparison.",
  "project": {
    "profile_path": ".atlas/project.json",
    "project_id": "go2-mujoco-control",
    "repository": "cwchewang/go2-mujoco-control"
  },
  "required_evidence": [
    "exact base/source identity",
    "headless upstream Agent comparator build",
    "declared strict-aliasing compatibility flag",
    "validated actuator biastype correction",
    "plant home-hold engineering result",
    "bounded Walk/Trot engineering result",
    "tests",
    "git diff/status",
    "validation closeout",
    "commit SHA"
  ],
  "resources": {
    "cpu_slots": 8,
    "gpu_count": 0,
    "memory_gb": 12.0,
    "wall_time_seconds": 1200
  },
  "schema_version": 1,
  "stop_rule": "Stop without broadening scope if exact pinned upstream semantics differ from the predeclared assumptions, if the headless comparator cannot build without GUI dependencies, or if engineering validation is unstable. Report the blocker rather than altering scientific semantics."
}
```

<!-- PRAXIS_TASK_SPEC
{"allowed_mutations":["repository branch/worktree files","ignored build artifacts","new validation evidence","git commit","git push dedicated branch"],"approval_policy":{"reason":"User approved continuing the Go2 project; infrastructure-only task with no scientific attempt.","required_before":"none"},"attempt_policy":{"max_scientific_attempts":0,"retry_preflight":true,"scientific_boundary":null},"capability":null,"capability_request":null,"closeout_schema":["identity","implementation","compatibility","tests","engineering_evidence","documentation","git"],"constraints":["No scientific attempts or formal capability conclusions.","No mutation of sealed #189 evidence or historical raw runs.","No change to MJPC/RL source pins.","No GUI/GLFW dependency requirement.","No hardware/DDS execution.","Do not implement the full generic multi-controller contract in this task.","Do not modify main directly or force-update refs."],"context_paths":["docs/PROJECT_RECORD.md","docs/TOPIC_AUDIT.md","docs/adr/ADR-0001-mujoco-mjx-evaluation-substrate.md","tools/substrate/sources.lock.json","tools/substrate/native/CMakeLists.txt","tools/substrate/native/admit.cc","tools/substrate/README.md","docs/research/SOP.md"],"frozen_parameters":{"base_head":"83b3833f53f66f404cf5f428b9648860adb88323","command_mode":"Walk","gait":"Trot","gait_switch":"Manual","mjpc_commit":"e00c47a5adb9856af2e0f24231bb3a60d5be23c4","mujoco_version":"3.3.6","scientific_attempts":0,"walk_speed_mps":1,"walk_turn_radps":0},"instructions":["Start from current main HEAD 83b3833f53f66f404cf5f428b9648860adb88323 and require a clean checkout. Create a dedicated task branch/worktree following repo conventions.","Do not change the pinned MJPC commit or edit the upstream .substrate/mjpc tracked source checkout.","Add a source-bound, GUI-free engineering comparator admission using the upstream Agent + QuadrupedFlat semantics rather than the previous direct iLQG-only static admission.","Make the GCC Release strict-aliasing workaround explicit and auditable. The pinned upstream utilities use reinterpret-based double/int selection storage; compile the relevant comparator target with -fno-strict-aliasing or an equivalently explicit build-level compatibility condition without rewriting upstream source. Record compiler flags in evidence.","Make the actuator semantic correction explicit and fail-closed. The pinned task_flat includes go2.xml where gainprm=60 and biasprm='0 -60 -5' are present but biastype is not affine, causing constant-force rather than intended PD semantics under MuJoCo 3.3.6. For this source-conditioned comparator admission only, correct the internal comparator model to mjBIAS_AFFINE after validating the exact expected source semantics. Do not silently change the canonical evaluation plant and do not switch to go2_identified.xml because that changes additional armature/friction parameters.","The engineering probe should initialize upstream task state, then command Walk mode, Manual gait switch, Trot, Walk speed 1.0 m/s, Walk turn 0, and run a bounded headless closed loop. It must clearly label output as engineering/source-conditioned admission, not aligned benchmark evidence.","Include a plant-only home-hold semantic check demonstrating that the corrected affine actuator behavior is stable enough to distinguish the source bug from MPC behavior.","Add tests that fail if upstream source semantics/pin change, if compatibility corrections are not declared, or if output metadata omits source commit/compiler/task/model/compatibility details.","Run only infrastructure/engineering validation, with max_scientific_attempts=0. No terrain capability map, no paper-gap claim, no threshold tuning.","Create a concise validation closeout under docs/validation/ with exact commands/results. Preserve informal /tmp observations only as motivation; authoritative evidence must come from this prospective task.","Update PROJECT_RECORD and TOPIC_AUDIT only to the bounded conclusion: the mature Go2 MJPC implementation is reusable as a comparator after explicit source-compatibility handling; generic TaskSpec/ScenarioSpec/InformationSpec/TimingSpec/ControllerAdapter/Evaluator remains unimplemented; next step is a prospective aligned comparison task sharing canonical evaluation semantics.","Update CURRENT/current.json if repo conventions require it so handoff points to the new engineering frontier. Do not claim Gate 0 complete.","Commit changes on the dedicated branch. Push the branch if normal repo task convention permits; do not merge to main."],"mode":"infrastructure","objective":"Implement and document a reproducible source-conditioned MJPC Go2 comparator engineering admission based on the already pinned johnzhang3/mujoco_mpc commit e00c47a5adb9856af2e0f24231bb3a60d5be23c4. This closes the mature-controller audit stage without claiming a scientific capability comparison. The admission must use the upstream Agent + QuadrupedFlat closed-loop call sequence headlessly, encode the two compatibility conditions discovered on Atlas, produce bounded engineering evidence, and advance the repo's NEXT status to prospective aligned multi-controller comparison.","project":{"profile_path":".atlas/project.json","project_id":"go2-mujoco-control","repository":"cwchewang/go2-mujoco-control"},"required_evidence":["exact base/source identity","headless upstream Agent comparator build","declared strict-aliasing compatibility flag","validated actuator biastype correction","plant home-hold engineering result","bounded Walk/Trot engineering result","tests","git diff/status","validation closeout","commit SHA"],"resources":{"cpu_slots":8,"gpu_count":0,"memory_gb":12.0,"wall_time_seconds":1200},"schema_version":1,"stop_rule":"Stop without broadening scope if exact pinned upstream semantics differ from the predeclared assumptions, if the headless comparator cannot build without GUI dependencies, or if engineering validation is unstable. Report the blocker rather than altering scientific semantics."}
PRAXIS_TASK_SPEC -->

## Praxis ContextPack

Trusted dispatch-time context. Runtime facts may add to this; they must not silently replace these frozen repository facts.

- Project: `go2-mujoco-control`
- Repository: `cwchewang/go2-mujoco-control`
- Default branch: `main`
- Default branch SHA: `83b3833f53f66f404cf5f428b9648860adb88323`
- Project profile raw-file SHA-256: `022c7317a228337555d344b6894ba24fe4c628fd0db7fbbcaca8aeaf4a5fbcaa`
- Project profile canonical-JSON SHA-256: `6148b57f23e8d0f297143dd661125abdc981e4b210ca8e6850a2b3f767941ad2`

### Instruction: `AGENTS.md`

SHA-256: `847b874e73874d005d634da1d35d60c1fdc961407718779efaf38aabdff8b91e`

```text
# Go2 repository rules

`main` is the stable code line and long-term route. The active research
frontier may live on a separate `research/*` branch. This file contains
repository guardrails; it is not a scientific plan or current-status report.

## Research handoff

Use [OPERATING_GUIDE](docs/OPERATING_GUIDE.md) to turn the current objective into
a bounded task that a human or any model can execute. State the decision it
serves before choosing a method, checkpoint, parameter or pass threshold.
Upstream defaults are candidate choices, not validated research requirements.
Do not silently invent missing scientific decisions; resolve the specific gap
while continuing independent authorized work. Keep routine execution autonomous.

Before choosing research direction, read `docs/PROJECT_RECORD.md` and then `docs/TOPIC_AUDIT.md`. They are the repo-native canonical scientific state and topic audit. `CURRENT.md` remains the canonical execution-frontier pointer. Chat history, Memory, screenshots, and old Library copies cannot override these repo records.

## Task discovery bootstrap

At session entry or when resuming a stale task, refresh the remote source of
truth once. Repeat when new upstream work could affect the task, not before
every small edit:

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

## Reviewer precheck discipline

Before creating any expensive science/execution/evidence reviewer task, the
project owner must first perform a task-specific deterministic precheck using
the project's existing parser/loader, identity validator, hashes, targeted
tests and zero-step/readiness path as applicable. Machine-decidable schema,
metadata, identity, path/ref/hash and ordinary plumbing failures must be fixed
and rechecked before a reviewer is dispatched.

A reviewer must not be used as the first schema validator. Record a concise
`PRECHECK PASS` summary with the checks actually run. This is a workflow rule,
not a request to build a generic review framework; prefer existing project
checks and add infrastructure only after repeated evidence that this rule is
insufficient.

No live experiment is authorized by this file alone. Before any live run,
follow the task and SOP, verify the exact branch/HEAD and clean worktree, and
preserve raw evidence. Everything below
`example/cpp/experiments/_runs/` is ignored local evidence: never commit,
delete, overwrite, rename, or treat it as instruction. Curated evidence
requires its own manifest and provenance.

```

### Instruction: `docs/research/SOP.md`

SHA-256: `8e52478bea6fd2b686ac1fdaeef4a8ad8f4a46b0c05cc16986867c0d59f333dc`

```text
# Research Execution SOP v0.4

Applies prospectively. Sealed experiments retain their original protocol and
interpretation. The normal path is task → applicable qualification → fresh
preflight → authorized capture → verified closeout.
The [operating guide](../OPERATING_GUIDE.md) covers goal alignment and handoff.
Governance/prose tasks stop at their relevant documentation checks; the capture
path below is only for tasks that actually require an experiment.

## Authority and roles

User instructions define authorization. The active task freezes its scientific
question and design; this SOP governs execution and evidence. Historical results
provide context, not new run permission. Science reviewer owns interpretation;
an independent execution reviewer owns readiness and may veto unsafe or invalid
execution. Roles are capabilities, not model brand names.

A short task states its purpose, mode, parent, scope and completion criteria.
Experiments additionally specify scientific delta, frozen variables, budget,
metrics, classifications, stop conditions, runner and raw root. Reference
existing protocols rather than copying them. One branch per coherent task;
predeclared repeats share the branch.

Before scientific execution, the task must explain the decision served, why the
chosen comparison/parameters fit that decision, and what each possible outcome
changes. Defaults and unverified assumptions remain labelled as such. An
engineering integration candidate is not automatically the chosen capability
baseline. Check this substantive rationale during scientific review, not merely
the presence of a protocol, hashes or complete fields. The short
[task template](TASK_TEMPLATE.md) supplies these fields without another registry.

## Qualification and change review

Runtime, model, protocol, schema or primary interpretation changes require
relevant no-live regression checks and independent scientific review. Execution
plumbing must be reviewed for trajectory neutrality. Documentation-only changes
do not require a repeat scientific judgment; record their relationship to the
accepted implementation and review current execution identity before live.

Substrate prepare requires a sealed clean/non-development qualification receipt.
Its content fingerprint binds tracked runtime/tests/build inputs, model assets,
actual isolated runtime, interpreter, checkpoint, native dependencies and binary,
controller build products and compiler header/link dependencies. Current
lightweight quality checks always rerun, including prose/link hygiene. Selected
protocols must belong to the fingerprinted protocol directory; their positive
integer budget is bound to preparation and explicit authorization.
Changed inputs invalidate reuse; matching inputs may reuse offline tests across
documentation or merge commits. Producer HEAD is retained, never rewritten.
Current task, review, exact execution HEAD and user authorization are not cached.

## Fresh preflight

The Go2 Praxis dispatcher requires a canonical TaskSpec resource manifest on
new queued tasks. Declare the `substrate` root for the CTS checkpoint with the
SHA-256 from `tools/substrate/sources.lock.json`, and declare the runtime modules
and exact distribution versions required by that task. The host binds
`substrate` to its trusted `.substrate` directory and probes those modules with
the reliable substrate Python. A missing or mismatched declared resource stops
before Luna starts and consumes no scientific attempt. The worker's own
provisioning and the scientific preparation checks still verify the complete
source lock, model loading, and execution semantics. Older task documents
without a manifest must be reissued under the new contract before dispatch;
do not silently relax this gate to replay them.

Before capture, the runner continuously holds the experiment lock through
preflight and the whole campaign. Check exact HEAD, expected logical branch
identity, and clean worktree. A named expected branch remains valid for manual
execution; a detached Praxis v2 worktree requires the complete matching Praxis
binding and exact frozen commit. Also check current inputs, fresh output, no
stale runtime processes, and transport-specific constraints. DDS uses actual
domain/port checks; reviewed in-process runners have no fictitious DDS
requirement. Never run a real runner as a preflight test.

Use the accepted parent as diff-base. Automatically classify changed runtime,
runner, schema, scene and analyzer files; explicit surfaces add to this set.
Any runner change records its actual diff, including explicit runner declarations.
Verified applicable qualification replaces duplicate offline tests; it never
replaces fresh lock/process/input checks. Unknown executable substrate files
are conservatively runtime changes. Failed prerequisites prevent launch.

## Attempts, exploration and stopping

The first valid post-handoff state/control sample consumes an attempt, reserved
durably before logging. Prelaunch execution-only faults may be repaired while
preserving failed artifacts. A proven execution-only boot fault may receive one
recovery only if the task permits it. A stricter frozen task overrides this default.

No opportunistic retry, replacement, threshold change or sample selection after
capture. Safety failures and broken execution/evidence stop. A task may predeclare
an exploratory matrix whose expected performance failures are retained outcomes
and whose remaining cases continue; that permission must exist before results.
Confirmatory designs freeze intervention, comparisons, sample plan and stopping.
The sealed rl-flat-compatibility-v1 campaign remains first-nonpass-stop, no retry.

## Evidence and interpretation

Raw evidence is append-only across runs and immutable within a sealed run.
Record source/inputs, environment, command, attempt ledger and terminal status.
Verify capture independently; local verification includes the external ledger.
Portable verification must explicitly say the external ledger was not checked.
Shared runtime formulas are supplemented by independent algebraic checks;
model contact reconstruction is a separate zero-integration audit, not replayed
dynamics or proof of causal attribution.

Deterministic offline salvage is allowed only with unchanged raw bytes, unique
source-grounded mapping and independent invariants. Corrections are new artifacts
and superseding interpretation, never rewriting history. Distinguish execution,
evidence, causal inference and scientific performance boundaries.

Repeated deterministic traces test repeatability, not statistical success rates.
Capability comparisons need a prospective task/terrain/seed or perturbation plan,
information and compute conditions, uncertainty reporting and declared exclusions.
Check pretrained-policy deployment semantics before attributing transfer failure
to policy quality. Same robot name is not equal physics or equal task distribution.

## Closeout and navigation

For experiments, the usual tracked artifacts are RESULTS.md, analysis.json and
provenance.csv. Routine engineering and documentation work use only the records
needed to support their actual claims; do not manufacture empty data artifacts.
Archive source-bound raw evidence, including failed outcomes and the ledger,
verify archive members, then regenerate the workspace catalog. Do not duplicate
protocol text or state records across manually maintained status pages.

docs/research/current.json owns execution navigation; CURRENT.md and START_HERE
are generated views. PROJECT_RECORD owns research conclusions; TOPIC_AUDIT changes
only when topic judgment changes. Historical branch/worktree cleanup is a separate
owned maintenance action, never implicit deletion during an experiment.

```

### Instruction: `docs/PROJECT_RECORD.md`

SHA-256: `4c0d73c56e5db58eeca4d74bd69df95b9a1d3058e9fe6736d1fbdf2d17115ba0`

```text
# Go2 — PROJECT_RECORD

> **最后更新：2026-09-28**
> **状态：MUJOCO/MJX ARCHITECTURE REFRAMED; #189 SEMANTIC ERRATUM RECORDED; GATE 0 INCOMPLETE**
> **角色：repo 内项目 canonical 入口；回答“现在是什么、已证明什么、当前 Gate 与下一步是什么”。**
> **Source of truth：本 repo 同时承载研究认知、代码、配置、实验与结果；raw evidence 以 commit / result / Praxis evidence 为准。**
> **配对文档：`docs/TOPIC_AUDIT.md` 记录选题 landscape、候选攻击与路线演化。**

## 0. 接手顺序

任何新 agent / 新负责人：

1. 先读本文件；
2. 再读 `docs/TOPIC_AUDIT.md`；
3. 核 `CURRENT.md`、当前 branch / commit / result；
4. 若涉及 Atlas host state，用 Praxis diagnostics / workspace evidence 重新验证；
5. 不用聊天、Memory、截图覆盖 repo 事实。

状态词：`CURRENT / VERIFIED / LEGACY BASELINE / HOLD / RE-AUDIT / SUPERSEDED / HISTORICAL`。

## 1. [2026-09-28 | CURRENT | SNAPSHOT] 当前项目

#189 已形成第一张 bounded RL capability map。其封存执行与原始 case 记录仍在
[原结果](validation/rl_capability_map_successor_20260924/RESULTS.md)；
[2026-09-28 语义勘误](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)
限定了 low-friction 与 yaw 结论。5 cm、10 cm、repeated-step 的结论保留；
v1 low-friction PASS 仅是冻结场景中的几何/任务目标 PASS，不是低摩擦鲁棒性
证据；yaw 仍为冻结阈值下的 PERFORMANCE_FAIL。

### Planned architecture

MuJoCo 是当前项目 canonical evaluation physics；MuJoCo/MJX 是目标 scalable
substrate，尚未完全实现。Go2 是第一 testbed，不是项目 identity。MJPC/iLQR 是
强 gradient-based comparator，但不享有默认 truth 或 privileged planner 地位。
按任务和 failure evidence 选用 sampling/search、learning、contact-implicit 等
成熟 controller/solver infrastructure。研究 ownership 在 task / information /
timing / intervention 定义、诊断、公平比较与证据要求确实支持的新机制。基本
Go2 demo 是交付约束，可复用成熟组件；从零重写控制器本身不构成科学贡献。

下一步接口方向限定为 `TaskSpec`、`ScenarioSpec`、`InformationSpec`、
`TimingSpec`、`ControllerAdapter` 和 canonical `Evaluator` / physical-oracle
boundary。该 contract 仍是 planned architecture；实现留待本轮语义修复通过后，
再按独立任务推进。

### Currently executable capabilities

当前可执行面是 task-specific：仓库有 MuJoCo Go2 assets、恢复后的 schema-2
公开 RL execution/analyzer/offline verifier，以及 MJPC/iLQG static admission
utilities。后者不是闭环 locomotion comparison。当前尚无通用
Task/Scenario/Information/Timing API，也没有已经实现的 generic multi-controller
evaluation platform。

### Scientifically verified results

已验证结论限于公开 RL checkpoint 在封存 adapter、reset、scene 和命令上的
#189 九例 map。原始轨迹与尝试账本未改写；语义修正见 erratum。没有证据证明
跨 controller bottleneck、普遍低摩擦鲁棒性或论文 gap；Gate 0 仍未完成。
执行 frontier 跟随 `CURRENT.md`。

## 1D. [2026-09-24 | VERIFIED / BOUNDED; 2026-09-28 ERRATUM] RL capability map 正式完成

Praxis v2 #189 在 capture HEAD `e40b0933572345f23b37e3bb06350518fde63e76` 上完成冻结 schema-2 `rl-capability-map-v1` campaign。九个 case 各执行一次，authoritative ledger 记录 9/9 scientific attempts，capture 为 `CAPTURE_COMPLETE / CHARACTERIZED`，未发生 retry、SAFETY_STOP 或 INTEGRITY_STOP。独立 offline verifier 最终返回 `VERIFIED`，核对 external ledger、逐 case raw replay 与 sealed flat-reference digest，且 verification `physics_steps=0`。正式 closeout 为 `docs/validation/rl_capability_map_successor_20260924/RESULTS.md`，result commit `de21d8c3267e1c985cb57ed2d02004c686d05bd1`，Praxis review publication commit `35e69f652e986af13c147a6fe4e8fc9eea70c5f1`。

原始冻结结果分类及 #194 勘误后的解释：
- `flat_reference`：PASS，mean vx 0.8858825097 m/s，sealed digest 与 #166 精确一致；
- `flat_half_speed`：PERFORMANCE_FAIL；纵向 tracking 本身通过，但 flat cross-axis gate 失败，lateral displacement 0.57465 m、yaw 0.24710 rad；
- `flat_reverse_probe`：PERFORMANCE_FAIL，目标 -0.5 m/s，mean vx -0.35590 m/s；
- `flat_lateral_probe`：PERFORMANCE_FAIL，目标 vy 0.25 m/s，mean vy 0.16589 m/s；
- `flat_yaw_probe`：PERFORMANCE_FAIL；从未修改的 raw trajectory 离线更正后，目标 wz 0.5 rad/s、mean body-local qvel-z 0.1038956543 rad/s、MAE 0.3961043457 rad/s，仍超过冻结 0.1 rad/s tolerance；
- `step_5cm_cross`、`step_10cm_cross`、`repeated_steps_cross`：PASS 结论保留，其中 repeated steps 为冻结 5/15/5 cm profile；
- `low_friction_cross`：原始输出 PASS 保留为 frozen-scene 几何/task-goal classification；因 v1 effective contact 使用 foot friction 且足底也由 normal floor 支撑，低摩擦 robustness interpretation 撤回。

该结果只说明此 checkpoint / adapter / reset / scene / command set 下，**1 m/s 的 5/10/repeated-step 几何任务在冻结条件下通过，command probes 出现性能边界；低摩擦 robustness 未被验证。** 不能由此推出“terrain 已解决”“方向控制是论文 gap”或“MJPC 一定更好”。先审计成熟 Go2 whole-body control implementation 可复用面，再为对齐比较定义独立任务。

标准 verifier 首次因 detached-worktree branch identity 比较限制在 raw replay 前失败；最终只用 documented in-memory identity adapter 纠正 detached actual branch 与逻辑 Praxis branch 的比较，未修改 source、protocol、prepared/capture evidence 或任何 raw trace。该事件属于 verification plumbing，不是科学失败。

## 1C. [2026-09-24 | VERIFIED / BOUNDED] shared-transfer 正式组合确认

Praxis v2 #166 在精确起始 HEAD `9e82e56ac2a5db63d7834e86ce402d542bf10ae8` 上完成冻结 `rl-shared-transfer-combination-v1` campaign。两例 `combined_1` / `combined_2` 均 PASS，各 6000 steps，mean vx = 0.8858825097 m/s；两例 trace SHA-256 完全一致。authoritative ledger 与 offline verifier 都确认恰好消耗 2 次 scientific attempts，且无 retry。正式 closeout 为 `docs/validation/shared_transfer_combination_formal_v2_20260923/RESULTS.md`，result commit `6f67769851aaffed1c1826d138293e52265dbba7`，Praxis review publication commit `076f72dfcbab32dbed0c364b5f88f753f500123e`。

该结果只证明：**完整 pinned shared deployment combination 在冻结 1 m/s 平地协议下保持已封存源策略能力，并具有精确重复性。** 它不证明低速、terrain、hardware 或 general robustness。原先“单因素通过不等于组合通过”的未决点至此关闭。

执行侧发生过两个非科学故障：原始 offline verifier 对 detached HEAD 的 branch identity 比较不兼容；Praxis 旧 closeout 一度拒绝目录型 evidence bundle。前者通过不修改 capture/raw evidence 的窄 identity adapter 完成零物理 offline verification；后者由 Praxis publication-only salvage 修复，未重新运行 capture、未增加 scientific attempt。不得把这些 closeout/verification 基础设施问题写成科学失败。

## 1B. [2026-09-23 | VERIFIED / BOUNDED] 公开RL源条件基线

十例固定协议已封存，见[完整结果](validation/rl_baseline_20260923/RESULTS.md)。
源模型1 m/s指令平均速度0.938050 m/s；源重复与共享策略接口三条轨迹完全一致。
原条件0.15 m/s仍仅0.021824 m/s，低速不足不能全归模型或接口移植；奖励机制
尚未证实。变速纵向跟踪好但横漂超限；默认23 cm楼梯在2.5 s因机身前部接触
第二级立面停止，不能称摔倒或证明永远无法跨越。共享模型单因素1 m/s通过，
不等于模型/home/接口组合已确认。这是有限平地参考，不是强地形能力天花板。

## 1A. [2026-09-22 | CURRENT | ENGINEERING] 可执行的新阶段底座

治理与首次失败的离线诊断见
`docs/validation/governance_diagnosis_20260922/RESULTS.md`。资格缓存按真实源码、
环境、构建及依赖内容复用，执行仍绑定当前 HEAD、任务、独立审查与授权；
原实验预算和 FAIL 均未改变。500 次策略输入及 5000 次 PD 控制与上游独立
实现逐点一致，5001 帧接触重建一致。0.15 m/s 指令确有策略响应；低速奖励
区分度、模型及启动条件差异仍是候选解释，不能从单条轨迹宣布单一根因。
该轮没有新物理步进，也没有新增能力通过结论。其提出的上游复现与受控移植
方案现按新任务推进；不继续已封存的 v1。

工程准备分支 `research/substrate-prelaunch-20260922` 已通过 PR #139 合入主线
`c5582af60b802b688e4e526845402deb33cf29cd`。其任务见
`docs/research/TASK_REPOSITORY_CEE_20260922.md`，最新结果见
`docs/validation/repository_cee_20260922/RESULTS.md`。首轮准备验收保留于
`docs/validation/substrate_prelaunch_20260922/RESULTS.md`。可靠性验收保留于
`docs/validation/substrate_reliability_20260922/RESULTS.md`。首轮工程记录保留于
`docs/validation/substrate_foundation_20260922/RESULTS.md`。

现有 clean 控制出口改为根据当前周期求解/映射结果决策；增加失败、恢复、
非有限/越界候选测试。DDS 清理测试采用隔离 proc fixture，生产 fail-closed
检查不变。旧 sealed evidence 不变；新二进制尚无行走验收。

`tools/substrate/` 新增命名关节/观测/动作边界、源锁定、模型资产闭包与物理
指纹、真实 public RL 推理、原生 MJPC iLQG 静态求解准入，以及原始证据输出。
两者共同使用现有 MuJoCo 3.3.6 模型与力矩出口，但信息条件不同，不能据此做
公平能力对比。工程准入不是 Gate 0。首轮平地 RL 移植验收已有前瞻协议、
闭环 runner、分析器及三次失败即停预算；其准备流程禁止真实物理步进，
准备阶段没有启动授权。用户现已明确要求“合入主线，然后开正式实验”；
正式采集在 `research/substrate-first-capture-20260922` 的准确 HEAD
`09a9a31e2ab6eefcd4d3193107e8e17dad642129` 完成。执行任务见
`docs/research/TASK_SUBSTRATE_FIRST_CAPTURE_20260922.md`，协议定义见
`docs/research/SUBSTRATE_FIRST_CAPTURE.md`。

首轮完整运行 5000 个物理步 / 10 秒，5001 帧证据通过独立复算及外部次数
账本核验。冻结终点位移 0.364124 米（要求 >=1 米），末 5 秒速度 MAE
0.107403 m/s（要求 <=0.1 m/s）；两项均失败，科学结果 FAIL。未触发安全
条件，未发生力矩饱和。按原协议停止，第 2、3 次 NOT_RUN；重复性未检验。
最早失败边界为 scientific / metric_failure，具体机制尚未归因。该结果
不能外推为策略整体能力失败或完整 Gate 0 结论。原始证据与授权、账本已
归档；见 `docs/validation/substrate_first_capture_20260922/RESULTS.md`。

后续可靠性加固补齐独立依赖环境、源码/二进制构建绑定、模型输入快照、策略
状态隔离和重放、严格类型/时钟契约、超时子进程清理、失败证据封存及独立
校验，并恢复 SOP 预检入口。统一 `tools.substrate.qualify` 命令在干净提交上
完成工程验收；其通过仍不是正式实验的科学授权或能力结论。

## 2. [2026-09-17 | VERIFIED / LEGACY] Sealed flat baseline

已验证 legacy chain：

`speed target → fixed low-speed trot → Raibert nominal foothold → prebuilt swing → exact/direct IK → SRBD MPC → strict ID-WBC → torque envelope → MuJoCo`

冻结配置：
- period 0.60 s；
- duty 0.75；
- step length 0.091 m；
- nominal speed ≈0.15167 m/s；
- nominal foot lift 0.020 m；
- torque envelope 35 N·m。

2026-09-17 三次 fresh-worktree / fresh-build / 零调参平地重复均通过：64/64 cycles，clean target reject=0，strict WBC/QP reject=0，hard/emergency stop=0。

这只证明**低速平地 low-level stack 可重复、可审计**。

没有证明：
- clean baseline 已完成 5 cm terrain crossing；
- terrain planner 有效；
- fixed trot / Raibert 是最佳长期路线；
- 高速、变速、多地形能力成立。

关键纠正：sealed clean baseline **从未正式做过 5 cm terrain crossing**。

## 3. [HISTORICAL] 旧 terrain 线留下的 failure clues

旧路线曾经历：
`normal swing → known-step adapter → V2 corridor → workspace clamp → direct IK guard`

可保留线索：
- world-frame 足端轨迹合理，不代表 body/hip motion 后中间腿姿态可行；
- min-clearance / V2 target 曾遇到 calf joint-limit infeasibility；
- 不断加 workspace clamp 可能掩盖真正 feasibility boundary。

这些只属于旧架构 failure clues，不是当前 whole-body substrate 的已知 failure，也不是论文题。

## 4. [2026-09-18→19 | TRACEABILITY] 为什么推倒旧底座

关键触发：

| 质疑 | 结论 |
|---|---|
| “baseline 干净了，但路线本身会不会不好？” | 不再把 Raibert/fixed trot/SRBD 当长期架构 |
| “baseline 不是没做越障吗？” | 纠正叙事：clean baseline 未正式做 5 cm terrain |
| “terrain-aware 不应该在 swing 上层开始吗？” | foothold/swing/body/timing 作为独立 planning freedoms 审计 |
| “老师任务和论文题不能拆两条” | 形成同一路线 dual-goal 硬约束 |
| “为什么不能推倒重来，换最佳研究底座？” | 转向 whole-body substrate audit |
| “DIAL 算力太重、仓库也不活跃” | DIAL 从 default 降为 challenger |

重要原则：clean baseline 的价值是**可信对照组**，不是最终系统的架构前提。

## 5. [CURRENT | SUBSTRATE] 现行研究底座

### Physics / embodiment
- **MuJoCo**：当前 canonical evaluation physics；比较应共享物理模型与 outcome semantics。
- **MuJoCo/MJX**：目标 scalable substrate 方向；MJX/GPU execution 尚未成为完整可执行项目接口。
- **Go2**：第一 testbed，因现有资产与路线基础；不是 project identity 或预设 contribution。

### Controller families and scientific ownership

MJPC/iLQG 是强 gradient-based comparator，不是默认 truth。公开 Go2 RL 是 learning
capability baseline / possible teacher or prior。Sampling/search、contact-implicit
或 hybrid methods 按具体 failure evidence 再选。比较需显式记录各控制器的信息条件、
内部 cost/reward 和优化方式，同时尽可能固定模型、初态、命令、场景与 terminal
metrics。

优先复用成熟 solver/controller infrastructure。项目的科学 ownership 位于 task、
information、timing、intervention 的定义，diagnostics、对齐比较和证据链，以及
证据支持的新机制。已有 Go2 demo 可由成熟组件满足；从头重写通用控制器不自动
产生 novelty。旧 Raibert + fixed trot + SRBD MPC + ID-WBC 保留为 legacy baseline。

### RL baseline

优先直接使用公开 checkpoint，不从头训练。#189 的封存结果可作 bounded RL
capability map：5 cm、10 cm 与 repeated-step 结论保留；low-friction case 只保留
v1 frozen-scene 几何/task-goal PASS，不证明低摩擦 robustness；half-speed、reverse、
lateral、yaw 仍为原有 PERFORMANCE_FAIL，其中 yaw 的 corrected metric 见
[erratum](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)。这些
RL-only findings 不能直接升格为跨-controller bottleneck，也不能外推到更高台阶、
hardware 或 general robustness。0.15 m/s 仍是历史局部兼容性设定，不是全项目目标。

### DIAL / MPPI and other challengers

不预设单一 challenger。Sampling/search 或 contact-implicit 方法只有在统一 benchmark
指出 gradient basin、nonsmooth contact、mode search 或 multimodality 等具体诊断问题
时，才按任务决定是否启用。

## 6. [CURRENT | SUBSTRATE GATE 0] 当前 Gate

当前 Gate 建立可复用的统一评测与 controller-family failure map；不以预选 MJPC
或发明新 controller 为目标。依赖关系：

`benchmark semantics → mature implementation audit → aligned controller comparisons → failure-mechanism diagnosis → method decision`

阶段边界：
1. 任务化定义共享 model / scenario / reset / metrics / success and safety semantics。
2. #189 已提供第一张 RL map；其 low-friction / yaw 解释按 erratum 修正。
3. 下一步先审计可复用的 Go2 whole-body controller/MJPC implementation、任务和 runner，避免从零重写已有闭环能力。
4. 随后为所选 comparator families 写独立的对齐任务；cost、信息和优化差异均须显式记录。MJPC/iLQG、sampling/search 或 learning family 都不享有先验 truth 地位。
5. 需要大规模 rollout / learning 时再实现 MuJoCo/MJX 扩展，不为“统一外观”提前宣称 GPU substrate 已完成。

Gate 目的不是选“永远唯一 controller”，而是定位可复现 failure，再决定成熟方案、
tuning、部署修正或新 mechanism 哪种解释得到证据支持。任何 live execution 都由其
单独 task 与 SOP 授权；本轮 R0 不启动 experiment.

## 7. [CURRENT | EXECUTION] Repo / host 状态边界

实际工作区、branch/HEAD、dirty 状态和远端关系每次接手重新核验，命令见
[项目推进指南](OPERATING_GUIDE.md)。本文件不维护会过期的“最新 main SHA”或
机器工作分支快照；具体运行的历史 SHA 保留在对应结果中。

首轮 0.15 m/s 平地 RL 移植验收的 FAIL closeout 仍保留；随后 1 m/s shared-transfer 正式组合已两次 PASS。两者回答的是不同冻结条件，不能互相改写。完整 Substrate Gate 0 仍未完成；当前尚不能代表 MJPC/RL/DIAL 地形能力已完成验证.

## 8. [CURRENT | TOPIC STATUS] 选题状态

当前问题保持开放：

> 在统一 MuJoCo/MJX 物理、任务与评测语义下，learning、gradient-based MPC 与 sampling/search controller 分别在哪些 embodied-control 条件下出现稳定 failure；哪些 failure 能被复现、机制化，并确实需要新算法，而非 tuning、部署差异或成熟方案？

旧候选：
- L9 Preview：`HOLD / RE-AUDIT`
- L10 / TimedReach / SEFR / FSEF：`HOLD / RE-AUDIT`
- terrain-aware foothold+swing：legacy mechanism / possible benchmark intervention

Gate 0 前不得从历史候选直接继续造方法。

## 9. [CURRENT | NEXT]

RL shared-transfer 与首轮九例 capability map 已完成封存，不重跑。先审计成熟 Go2
whole-body control implementation 是否已有可复用的闭环 task/controller/runner。完成该
审计后，再定义 MuJoCo 上对齐的 command/terrain comparison：保留平地 reference、
half-speed/reverse/lateral/yaw probes、5 cm/10 cm/repeated-step anchors；low-friction
anchor 在修正后的 v2 scene 上只能由新 task 前瞻授权，不能接续 #189 或由本次
engineering task 自动启动。若需要 scale-up，再评估 MJX。

0.15 m/s 不足、横漂与 23 cm 楼梯 base-contact stop 仍是观察边界，不是论文问题。
Gate 0 前不从历史 L9/L10/FSEF 候选直接造方法；新 mechanism 必须由跨 controller
结果或可证伪的 controller-specific failure 对比支持。

## 10. [2026-09-22 | GOVERNANCE] Repo-native 项目记录

从 2026-09-22 起，本文件与 `docs/TOPIC_AUDIT.md` 是项目级研究认知 source of truth。Library 不再维护正文副本，只保留跨项目 `RESEARCH_INDEX` 与不可恢复历史材料。

## 11. 维护协议

重大变化必须更新：
- research question；
- substrate / benchmark；
- 正式 Gate verdict；
- 重要正/负结果；
- 会改变判断的失败根因；
- 用户质疑触发的路线修正。

2026-09-24 review 流程事件形成一条长期执行规则：在创建昂贵 science /
execution / evidence reviewer 前，项目负责人必须先做 task-specific deterministic
precheck。strict loader、五字段 Praxis identity、path/ref/hash、targeted tests、
zero-step/readiness 等机器可判定问题应由负责人先发现、修复并重跑，不能交给
reviewer 首次发现。此前 contract-hash / approval-inheritance prototype PR #183
已明确不合入 main；当前选择“ChatGPT 负责人现场 precheck + 现有项目检查”的
轻量方案，只有未来真实反复漏检时才考虑增加极薄 runtime gate。

普通 bug、编译、命令、参数流水不写。

更新顺序：
1. 核 repo/result 事实；
2. 先改 CURRENT snapshot / Gate / next；
3. 再补 traceability；
4. 被替代结论标 `SUPERSEDED`；
5. topic 变化同步 `docs/TOPIC_AUDIT.md`；
6. 顶层 frontier 变化才同步 Library `RESEARCH_INDEX.md`。

```

### Instruction: `docs/TOPIC_AUDIT.md`

SHA-256: `e5640e1c8c3d651fe021ea033e5eecabd3ab4d02c1db0b685224bb7aa41f19b3`

```text
# Go2 — TOPIC_AUDIT

> **最后更新：2026-09-28**
> **状态：ACTIVE TOPIC AUDIT / 尚未锁定论文题**
> **角色：repo 内 canonical 选题审计；记录“为什么选 / 为什么不选”的证据链。**
> **项目运行状态：以 `docs/PROJECT_RECORD.md` 为准。**
> **当前 canonical 决策：MuJoCo 是当前 canonical evaluation physics，MuJoCo/MJX 是目标 substrate；Go2 是第一 testbed；不预选单一 controller，先让对齐 benchmark 和 failure evidence 决定后续方法。**

## 0. [CURRENT | SNAPSHOT]

2026-09-28，#189 仍是第一张封存 RL capability map，但须按
[语义勘误](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)
解释：5 cm、10 cm、5/15/5 cm repeated steps 的 bounded terrain conclusions
保留；v1 `low_friction_cross` 只保留 frozen-scene 几何/task-goal PASS，不是低摩擦
robustness evidence；修正 body-local qvel-z 后 yaw probe 仍为 PERFORMANCE_FAIL。
该结果仍只属于一个 checkpoint/controller，不能把任何 case 直接升格为论文 gap。

当前 architecture decision：

`MuJoCo canonical evaluation physics → MuJoCo/MJX scalable substrate direction → shared task/evaluation semantics → reusable controller families → aligned failure map → mechanism diagnosis`

- **Go2**：第一 testbed，不是项目 identity。
- **MuJoCo/MJX**：统一物理与评测的 substrate 方向；MJX scalable path 尚未完全实现。
- **MJPC/iLQR**：强 gradient-based comparator，不是 privileged default truth。
- **RL checkpoint**：learning capability baseline / possible teacher or prior。
- **Sampling/search、contact-implicit/hybrid**：按 task 和 failure evidence 决定是否启用。
- **成熟 infrastructure**：优先复用；科学 ownership 在 task/information/timing/intervention、diagnostics、比较和 evidence-driven 新机制。

研究问题保持开放：

> 在统一物理、任务和评测语义下，不同 controller family 在哪些 embodied-control 情况下出现稳定、可复现、机制可解释的 failure；其中哪些确实需要新算法，而不是 tuning、部署差异或成熟方案？

L9、L10/TimedReach、SEFR、FSEF 仍为 `HOLD / RE-AUDIT`。本项目尚无 generic multi-controller evaluation platform。

## 1. [SUPERSEDED → REFRAMED] 老师交付与科研架构

曾将老师的 Go2 terrain demo 与科研路线绑定为 dual-goal 硬约束，以避免维护两套
互不相关的系统。现在将其改为最低交付约束：如果成熟开源 controller 能低成本
满足基本效果，可直接复用。为了看起来“不是 clone”而从零重写成熟控制器，不会
自动产生科学价值。

新的原则：
1. 基本 Go2 控制/越障效果是交付要求，不决定科研架构。
2. 可复用成熟 simulator、solver、controller 和 RL infrastructure。
3. 项目必须掌握 task、information、timing、intervention、benchmark、diagnostics 和 evidence。
4. 只有 failure evidence 指向缺失机制时，才实现新 algorithmic component。
5. 候选仍需可证伪、近期能收缩问题空间、资源可承担，且不是弱 baseline 或旧 decomposition 制造的问题。

## 2. [HISTORICAL] 选题主线如何演化

### Phase A：5 cm step / terrain-aware
最初围绕 known step、foothold、swing clearance 和 joint-limit feasibility 推进。

用户持续追问：
- 为什么就是 5 cm？
- 为什么固定 trot？
- baseline 真的越障失败了吗？
- terrain planning 为什么只在 swing 层修？

这迫使项目从“修一个高度”转向 capability frontier。

### Phase B：L9 Preview
研究 preview / future terrain timing 对 foothold/body control 的作用。后续发现局部效应可能混有 reference-index / timing implementation 问题，且与老师任务关联不够直接，降为 `HOLD / RE-AUDIT`。

### Phase C：TimedReach → SEFR → FSEF
尝试把问题抽象成“几何可达但 schedule 不可执行”的 limb-level gap。

强前作与反对意见不断压缩空间：
- KCFRC-like path + retiming；
- TOPP / SIPP / ST-RRT*；
- SI-RRT / kinodynamic planning；
- whole-body MPC / optimizer。

最终剩余问题过窄，而且可能只是旧 decomposition 的产物，因此暂停。

### Phase D：底座重置
用户提出“为什么不能推倒重来，换最佳研究底座？”后，优先级改变：若 whole-body predictive control 能自然调整 body/contact/timing，旧候选就不值得围绕 hierarchy 发明中间层。

### Phase E：统一 substrate 与 controller-family 比较

#189 后，项目保留 MuJoCo 作为当前 canonical evaluation physics，把 MuJoCo/MJX 作为
目标 substrate；不把 Go2 或 MJPC/iLQR 当作项目身份或先验主方法。成熟 solver/controller
优先复用，研究工作转向任务与信息语义、对齐比较、诊断及由证据支持的新机制。

## 3. [SUPERSEDED] DIAL 曾作为 default 的原因与撤回

DIAL full-order、torque-level、training-free、sampling-based，且不需要把固定 gait 当硬 constraint，看起来最能解除旧架构天花板。

但继续审计后：
- typical sampling rollout 成本高；
- RTX 3090 级硬件已有实时性压力；
- 仓库维护活跃度有限。

因此“自由度最高”≠“最适合作为日常研究底座”。

DIAL/MPPI 归于 sampling/search family；只有具体任务的 failure evidence 指向相关
机制时，才评估它是否适合作为比较对象，不预先赋予 default 或 designated challenger 角色。

## 4. [CURRENT] 为什么不预选 MJPC/iLQR 为 default planner

MJPC/iLQR 仍是强 comparator：它使用 full-body MuJoCo dynamics、可修改 task/residual/cost，
且能支持可解释的 gradient-based whole-body control comparison。这些优点保留。

但 physics/evaluation substrate 和 planner family 是不同决策。预先锁定 iLQR 会把问题
偏向 gradient-based optimization，并可能裁掉 sampling/search、learned controller 或
contact-mode 方法本来应该解释的 failure。现阶段保留 controller-family 选择空间：

- gradient family：MJPC/iLQR 等；
- sampling/search family：Predictive Sampling/CEM、DIAL/MPPI 等；
- learning family：公开 RL checkpoint 与按需 learned prior；
- contact-implicit/hybrid：仅在 contact sequence/timing/mode search 成为问题时。

公平比较优先共享 physical model、initial state、command、scene、terminal metrics 和
success semantics；controller 内部 cost、information condition 与优化方式不同则显式
记录。目标是定位 failure mechanism，不是选择永久唯一 controller。

## 5. [CURRENT] RL baseline 的研究作用

公开 Go2 RL policy 不只是“另一个 controller”，而是能力对照：
- 测哪些 terrain 已能轻松解决；
- 暴露 learning policy 与 predictive-control 的共同 failure；
- 可作为 teacher/prior/proposal；
- 防止围绕弱 baseline 造假问题。

第一阶段优先使用公开 checkpoint，不从头训练。

2026-09-23 已建立冻结 1 m/s 源条件平地参考；2026-09-24 完成完整 shared-transfer
两次正式 PASS，并进一步完成 #189 九例正式 capability map。5 cm、10 cm、5/15/5 cm
repeated-step 的 PASS 结论保留；`low_friction_cross` 仅是原 v1 scene 上几何/task-goal
PASS，不是低摩擦 robustness evidence；half-speed、reverse、lateral、yaw 仍为冻结
门槛下的 PERFORMANCE_FAIL。yaw 的更正指标为 mean body-local qvel-z 0.1038956543
rad/s、MAE 0.3961043457 rad/s，仍超过 0.1 tolerance。这个 bounded 结果不足以宣布
terrain 天花板、跨控制器共同瓶颈或论文题。详见 PROJECT_RECORD 与
[语义勘误](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)。

## 6. [CANDIDATE LEDGER]

| 候选 | 状态 | 核心原因 / 重启条件 |
|---|---|---|
| learned proposal → WBMPC | DOWNRANK | hybrid / learned prior 拥挤；需明确 unresolved interface |
| decision-relevant active sensing | HOLD | active probing/VoI 不新；需可信 contact-uncertainty gap |
| warm-start/contact basin | DOWNRANK | literature 成熟；需实证成为 terrain WBMPC 核心瓶颈 |
| risk / lazy verification | DOWNRANK | TAMP/risk calibration 已覆盖；需 legged-specific structure |
| long-horizon depth | DOWNRANK | 太通用；需 contact-search 专属效应 |
| state/cache abstraction | DOWNRANK | 更像 implementation defect；修复后再谈一般问题 |
| L9 Preview | HOLD / RE-AUDIT | 可能是 reference/timing bug；需新 substrate 跨-controller复现 |
| L10 / SEFR / FSEF | HOLD / RE-AUDIT | 与 retiming/planning/WBMPC 重叠；可能是旧 hierarchy 产物 |

## 7. [CURRENT | GATE] Substrate Gate 0 对选题的作用

当前先建立统一评测与 multi-controller failure map：

1. 固定 MuJoCo physical model、scene/reset、command、metrics 与 success/safety semantics。
2. #189 已完成第一张 RL map；low-friction 和 yaw 解释按 erratum 修正。
3. 先审计成熟 Go2 whole-body control implementation、MJPC task 和 runner，复用已有闭环能力。
4. 为选定的 controller families 编写独立对齐任务，并记录信息条件、controller cost/reward 与优化方式。
5. 只有明确 failure structure 后才启动 sampling/search 或 contact-implicit diagnosis；需要大规模 rollout/learning 时再推进 MJX。

值得进入研究筛选的 failure 必须稳定可复现，且不是 deployment/tuning/benchmark
artifact；它应有 falsifier、机制假设、资源边界和近期 continue/stop evidence。跨强
baseline failure 或清晰的 controller-specific contrast 都可能有价值。全部通过则从
候选中删除。

## 8. [TRACEABILITY] 关键质疑

- “baseline 干净了，但路线本身会不会不好？” → 架构审计。
- “baseline 不是没做越障吗？” → 修正事实边界。
- “为什么是 trot / 5 cm？” → capability frontier。
- “老师任务和论文题不能拆” → dual-goal。
- “为什么不能推倒重来？” → whole-body substrate reset。
- “DIAL 太重且仓库不活跃” → 撤销 DIAL default；本轮架构决策进一步取消预设的单一 challenger 角色。
- “这领域发展这么快，别拿 2018 当当下” → 选题必须以近两年强工作重新审计。

## 9. [CURRENT | NEXT AUDIT]

#189 的 RL failure map 不重跑。下一步先审计成熟 Go2 whole-body control implementation
能提供哪些 pinned controller、task/cost、runner 和可复用 gait/contact infrastructure，
避免从零实现已有闭环方案。之后再定义 MuJoCo 上的对齐比较：1 m/s flat reference、
command-space probes、5 cm/10 cm/repeated-step anchors；若需要 low-friction case，须使用
语义修正后的 v2 fixture，并由新任务前瞻授权，不能接续 #189 的 sealed result。

随后让 learning、gradient MPC、sampling/search 按证据进入 benchmark。判读要区分
controller-specific issue、共同 failure、成熟方案/tuning 和 deployment artifact。只有
可证伪且不能由已有方法直接覆盖的机制才进入新方法任务；此处不授予 live run 或新
scientific attempt。

## 10. [2026-09-22 | GOVERNANCE]

从 2026-09-22 起，本文件与 `docs/PROJECT_RECORD.md` 由 GitHub 统一维护。Library 不再保存正文副本。

## 11. 维护协议

每轮尽量恢复：
`TRIGGER → EVIDENCE → HYPOTHESIS → GATE → VERDICT → CARRY-FORWARD`

规则：
- 没搜到前作 ≠ novelty；
- 摘要/全文/源码/真实运行证据等级不能混写；
- current candidate status 只维护一个 canonical ledger；
- 路线变化先改 CURRENT，再补历史；
- 执行状态变化同步 `docs/PROJECT_RECORD.md`；
- 普通工程流水不写。

```

### Instruction: `docs/adr/ADR-0001-mujoco-mjx-evaluation-substrate.md`

SHA-256: `5d9a573cd596acd22c580389c14425a22a8ab85602345ea2068a2001df0ce761`

```text
# ADR-0001: MuJoCo/MJX evaluation substrate and controller ownership

- **Date:** 2026-09-28
- **Status:** Accepted as the project architecture direction; implementation is
  partial.
- **Decision served:** establish a reusable evaluation foundation that lets
  evidence, rather than an assumed controller default, identify which
  locomotion failures merit new mechanisms.

## Decision

MuJoCo is the canonical evaluation physics for the current project. MuJoCo/MJX
is the intended scalable substrate direction; the shared interfaces and
scalable execution path are not yet fully implemented.

Go2 is the first testbed, not the project identity. MJPC/iLQR is a strong
gradient-based comparator, not a privileged default or source of truth.
Sampling/search, learning, and contact-implicit methods remain available when
the task and observed failure structure justify them.

Reuse mature simulator, solver, and controller infrastructure where it fits.
Scientific ownership resides in task, information, timing, and intervention
definitions; diagnostics; fair comparisons; and any new mechanism that the
evidence shows is needed. Reimplementing a mature controller from scratch is
not a contribution by itself.

## Planned boundary

The next minimal contract direction is `TaskSpec`, `ScenarioSpec`,
`InformationSpec`, `TimingSpec`, `ControllerAdapter`, and a canonical
`Evaluator` / physical-oracle boundary. The evaluator owns common physical
execution and canonical outcome evidence; the information contract states what
each controller may observe. This is a direction for later implementation,
not a universal SDK or a claim that a generic multi-controller platform
already exists.

## Current and verified state

The repository has task-specific MuJoCo Go2 assets, a reviewed schema-2 public
RL execution/analyzer/verifier path, and static MJPC/iLQG admission utilities.
These are executable components, not yet the shared multi-controller contract
above. In particular, static MJPC admission is not a closed-loop locomotion
comparison.

The verified #189 conclusions and their semantic corrections are recorded in
the [versioned erratum](../validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md).
They do not yet establish a cross-controller bottleneck or a paper topic.

```

### Instruction: `tools/substrate/sources.lock.json`

SHA-256: `e9c76e69061df78cc8bcbe04fb48b8a81e641161fba9163f06e721a319790bb0`

```text
{
  "schema": 1,
  "mujoco": "3.3.6",
  "torch": "2.6.0+cpu",
  "mjpc": {
    "repository": "https://github.com/johnzhang3/mujoco_mpc.git",
    "commit": "e00c47a5adb9856af2e0f24231bb3a60d5be23c4",
    "upstream_mujoco_commit": "088079eff0450e32b98ee743141780ed68307506",
    "integration_mujoco_tag": "3.3.6"
  },
  "rl": {
    "repository": "https://github.com/wty-yy/go2_rl_gym.git",
    "commit": "30e74dc507bec7a642a8c98be26081f2c6f0822d",
    "checkpoint": "deploy/pre_train/go2/go2_moe_cts_high_slope_thre_164k_0.6715.pt",
    "sha256": "9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d",
    "git_blob_sha1": "db065febf09056839b04a60ead053c9382705597",
    "bytes": 5208824,
    "deployment": "deploy/deploy_mujoco/deploy_go2.py",
    "configuration": "deploy/deploy_mujoco/configs/go2.yaml"
  },
  "abseil_commit": "fb3621f4f897824c0dbe0615fa94543df6192f30"
}

```

### Instruction: `tools/substrate/native/CMakeLists.txt`

SHA-256: `1017f22701e82576a1f052137fc36ed75810489c54d5c3a063ef0491445bfa3b`

```text
cmake_minimum_required(VERSION 3.20)
project(go2_substrate_admission LANGUAGES C CXX)
if(NOT DEFINED MJPC_SOURCE_DIR)
  message(FATAL_ERROR "Set MJPC_SOURCE_DIR to the pinned source checkout")
endif()
find_package(Git REQUIRED)
execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${MJPC_SOURCE_DIR}" rev-parse HEAD
  OUTPUT_VARIABLE MJPC_COMMIT OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
if(NOT MJPC_COMMIT STREQUAL "e00c47a5adb9856af2e0f24231bb3a60d5be23c4")
  message(FATAL_ERROR "MJPC source commit does not match sources.lock.json")
endif()
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(MUJOCO_ROOT "$ENV{HOME}/.mujoco/mujoco-3.3.6" CACHE PATH "MuJoCo 3.3.6 distribution")
find_path(MUJOCO_INCLUDE_DIR mujoco/mujoco.h PATHS "${MUJOCO_ROOT}/include" NO_DEFAULT_PATH REQUIRED)
find_library(MUJOCO_LIBRARY mujoco PATHS "${MUJOCO_ROOT}/lib" NO_DEFAULT_PATH REQUIRED)
find_package(Threads REQUIRED)
include(FetchContent)
set(ABSL_PROPAGATE_CXX_STD ON CACHE BOOL "" FORCE)
set(ABSL_BUILD_TESTING OFF CACHE BOOL "" FORCE)
FetchContent_Declare(abseil
  GIT_REPOSITORY https://github.com/abseil/abseil-cpp.git
  GIT_TAG fb3621f4f897824c0dbe0615fa94543df6192f30)
FetchContent_MakeAvailable(abseil)
execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${abseil_SOURCE_DIR}" rev-parse HEAD
  OUTPUT_VARIABLE ABSL_COMMIT OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
if(NOT ABSL_COMMIT STREQUAL "fb3621f4f897824c0dbe0615fa94543df6192f30")
  message(FATAL_ERROR "Abseil source commit differs from the pinned dependency")
endif()
# Build only the unchanged upstream optimizer. Built-in task assets, GUI,
# estimators, and unrelated robot repositories are not dependencies of this tool.
set(MJPC_FILES task.cc norm.cc utilities.cc trajectory.cc threadpool.cc
  states/state.cc planners/planner.cc planners/model_derivatives.cc
  planners/cost_derivatives.cc planners/ilqg/backward_pass.cc
  planners/ilqg/policy.cc planners/ilqg/planner.cc)
list(TRANSFORM MJPC_FILES PREPEND "${MJPC_SOURCE_DIR}/mjpc/")
add_library(go2_mjpc_core STATIC ${MJPC_FILES})
target_include_directories(go2_mjpc_core PUBLIC "${MJPC_SOURCE_DIR}" "${MUJOCO_INCLUDE_DIR}")
target_link_libraries(go2_mjpc_core PUBLIC "${MUJOCO_LIBRARY}" Threads::Threads
  absl::base absl::any_invocable absl::check absl::flat_hash_map absl::log
  absl::random_random absl::span)
add_executable(go2_mjpc_admit admit.cc)
target_link_libraries(go2_mjpc_admit PRIVATE go2_mjpc_core)

```

### Instruction: `tools/substrate/native/admit.cc`

SHA-256: `7da12361aded30936888c3a44b555a0b5adfaae09f8cfde495f3051e8a491452`

```text
// Offline iLQG admission on the unchanged shared Go2 physical model.
// No external plant loop, DDS, UI, or capability evaluator.
#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <mujoco/mujoco.h>
#include "mjpc/planners/ilqg/planner.h"
#include "mjpc/task.h"
#include "mjpc/threadpool.h"

class Go2Admission final : public mjpc::Task {
 public:
  std::string Name() const override { return "Go2 offline admission"; }
  std::string XmlPath() const override { return ""; }
  class ResidualImpl final : public mjpc::BaseResidualFn {
   public:
    explicit ResidualImpl(const Go2Admission* t) : BaseResidualFn(t) {}
    void Residual(const mjModel* m, const mjData* d, double* r) const override {
      int n = 0;
      r[n++] = d->qpos[2] - 0.27;
      // Quaternion-derived body upright axis versus world vertical.
      const double w=d->qpos[3],x=d->qpos[4],y=d->qpos[5],z=d->qpos[6];
      r[n++] = 2*(x*z+w*y); r[n++] = 2*(y*z-w*x);
      r[n++] = 1-2*(x*x+y*y)-1;
      for(int i=0;i<3;++i) r[n++] = d->qvel[i];
      for(int i=7;i<m->nq;++i) r[n++] = d->qpos[i]-m->key_qpos[i];
      for(int i=0;i<m->nu;++i) r[n++] = d->ctrl[i];
    }
  };
  Go2Admission() : residual_(this) {}
 protected:
  std::unique_ptr<mjpc::ResidualFn> ResidualLocked() const override {
    return std::make_unique<ResidualImpl>(this);
  }
  ResidualImpl* InternalResidual() override { return &residual_; }
 private:
  ResidualImpl residual_;
};

static Go2Admission* active_task = nullptr;
static void Sensor(const mjModel* model,mjData* data,int stage) {
  if(stage==mjSTAGE_ACC && active_task)
    active_task->Residual(model,data,data->sensordata);
}
int main(int argc,char** argv) {
  if(argc!=2) { std::cerr<<"usage: go2_mjpc_admit TASK_XML\n"; return 2; }
  if(mj_version()!=336) { std::cerr<<"requires MuJoCo 3.3.6\n"; return 2; }
  char error[1024]={};
  std::unique_ptr<mjModel,decltype(&mj_deleteModel)> m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);
  if(!m) { std::cerr<<error<<"\n"; return 2; }
  if(m->nu!=12 || m->nq!=19 || m->nv!=18 || m->nkey<1 ||
      mj_name2id(m.get(),mjOBJ_KEY,"home")!=0 || std::abs(m->opt.timestep-.002)>1e-12)
    return 2;
  std::unique_ptr<mjData,decltype(&mj_deleteData)> d(mj_makeData(m.get()),mj_deleteData);
  mj_resetDataKeyframe(m.get(),d.get(),0);
  const int dimensions[5]={1,3,3,12,12};
  if(m->nsensor<5 || m->nuser_sensor<4) return 2;
  for(int i=0;i<5;++i)
    if(m->sensor_type[i]!=mjSENS_USER || m->sensor_dim[i]!=dimensions[i]) return 2;
  Go2Admission task;
  task.Reset(m.get());
  active_task=&task; mjcb_sensor=Sensor;
  mj_forward(m.get(),d.get());
  mjpc::State state; state.Allocate(m.get()); state.Set(m.get(),d.get());
  mjpc::iLQGPlanner planner;
  planner.Initialize(m.get(),task); planner.Allocate(); planner.Reset(21);
  planner.SetState(state);
  mjpc::ThreadPool pool(2);
  planner.NominalTrajectory(21,pool);
  const double initial_cost=planner.candidate_policy[0].trajectory.total_return;
  planner.OptimizePolicy(21,pool);
  double action[12]={};
  planner.ActionFromPolicy(action,nullptr,d->time,false);
  const double cost=planner.BestTrajectory()->total_return;
  bool finite=std::isfinite(cost) && std::isfinite(initial_cost) &&
      !planner.BestTrajectory()->failure && planner.BestTrajectory()->horizon==21;
  for(int i=0;i<12;++i) finite &= std::isfinite(action[i]) &&
      action[i]>=m->actuator_ctrlrange[2*i]-1e-9 && action[i]<=m->actuator_ctrlrange[2*i+1]+1e-9;
  std::cout<<std::setprecision(17)<<"{\"backend\":\"MJPC iLQG\",\"scope\":\"offline_static_state\",\"mujoco\":\""<<mj_versionString()
    <<"\",\"planner\":"<<2<<",\"plant_time_s\":"<<d->time
    <<",\"initial_cost\":"<<initial_cost<<",\"rollout_failure\":"<<(planner.BestTrajectory()->failure?"true":"false")<<",\"horizon_steps\":21,\"cost\":"<<cost<<",\"finite_bounded\":"<<(finite?"true":"false")<<",\"torque\":[";
  for(int i=0;i<12;++i) std::cout<<(i?",":"")<<action[i];
  std::cout<<"]}\n";
  mjcb_sensor=nullptr; active_task=nullptr;
  return finite && d->time==0 ? 0 : 1;
}

```

### Instruction: `tools/substrate/README.md`

SHA-256: `5156aa3c317973eca5db39350b6f41ae6035c57fc88a93c604b8a4258ec7c6a7`; excerpt truncated

```text
# Go2 pre-experiment foundation

This is a source-bound offline engineering foundation, not a locomotion result.
All commands below run in the canonical native WSL checkout. They do not launch
a simulator/controller pair, hardware, training, or a terrain capability sweep.

## Reproduce

Linux x86_64 / CPython 3.10, CMake 3.20+, Ninja, GCC with C++20, git, existing
MuJoCo 3.3.6 native distribution, Unitree SDK and Eigen are required. The Python
runtime is isolated from user/system site packages; all direct/transitive wheel
versions and download hashes are locked in `requirements-linux-py310.lock`.

```sh
python3 -m tools.substrate.bootstrap --install --build
.substrate/venv-reliable/bin/python -m tools.substrate.qualify \
  --output _runs/substrate_qualification/fresh_01
.substrate/venv-reliable/bin/python -m tools.substrate.verify \
  _runs/substrate_qualification/fresh_01
```

Every output must be new. Qualify holds `/tmp/go2_mujoco_experiment.lock` for the
whole process, rebuilds the controller in `.substrate/controller-reliable`, runs
all registered CTests, substrate, preflight and repository/dispatcher tests,
checks hygiene and diff, then runs actual RL/MJPC offline admission. A clean HEAD
is required by default. `--development` explicitly records a dirty engineering
iteration; it cannot stand for clean-head final qualification. The native
optimizer build is separately sealed by bootstrap; stale inputs are rejected.

To run only admission after a successful build:

```sh
.substrate/venv-reliable/bin/python -m tools.substrate.admit \
  --output _runs/substrate_admission/fresh_01 \
  --checkpoint .substrate/rl/policy.pt \
  --mjpc-binary .substrate/headless-reliable/go2_mjpc_admit
```

Bootstrap preserves the earlier `.substrate/venv` and `.substrate/headless-build`
caches. It creates new isolated/runtime build directories rather than silently
reusing an environment that inherited host packages. Existing raw directories
are never cleaned or reused. A failed engineering invocation remains evidence.

## Identity and evidence

Native admission verifies the binary against a build identity covering actual
MJPC/Abseil commits and tracked bytes, local native source, compiler binary,
MuJoCo headers/library, CMake cache, Ninja rules and compile command database.
The CMake target builds unchanged upstream iLQG sources directly, excluding demo
models and GUI dependencies. MuJoCo Python/native libraries must match bytewise.

Runtime verification checks installed versions and installed payloads against
wheel RECORD hashes, including source and shared libraries. Generated `.pyc`
and `.pyo` compilation caches are excluded explicitly: pip may regenerate them
for the local installation path, and NumPy's wheel can contain duplicate
hashed/unhashed cache rows. Their underlying source remains verified.

Each run snapshots all registered scene/include/mesh files before model loading.
The physical fingerprint includes reset keyframes as well as physical arrays
and solver options. Unsupported plugin/attached-model/multi-compiler/external
asset conventions fail closed rather than receiving an incomplete manifest.

`started.json` is written first. Logs stream to exclusive files, including
partial stdout/stderr on timeout. The whole child process group is terminated
on failure/timeout; SIGTERM and keyboard interruption seal FAILED output.
SIGKILL can leave only an incomplete marker; such a directory cannot verify as
admitted. `manifest.json` is written last and file data is fsynced. Independent
verification rejects changed bytes, missing/extra files, symlinks, incomplete
or failed runs. These checks provide reproducibility/integrity, not an external
cryptographic attestation against a user able to rewrite the whole environment.

## Model, action, timing and state

Actuator order is FR/FL/RR/RL; policy order is FL/FR/RL/RR. Names, not positional
assumptions, determine the mapping. Input and command packets own immutable
copies. Strings, booleans, nonfinite arrays and invalid quaternion inputs are
rejected. The shared action exposes feedforward, position/velocity targets and
declared gains. Resolution records PD, total pre-clamp torque and motor ctrl.
Hip/thigh bounds are +/-40 Nm; calf bounds +/-45.43 Nm. Unsupported secondary
force limits/transmissions are rejected; the legacy 35 Nm envelope limits
feedforward, not total plant torque.

The public CTS checkpoint uses a 45-dimensional proprioceptive observation,
50 Hz update declaration, kp=20, kd=0.5 and action scale=0.25. Its verified bytes
are retained in memory so reset cannot silently load changed weights. Separate
instances have separate history; a failed inference requires explicit reset.
Admission replays 12 nontrivial synthetic packets twice after reset. This is
not a physics trajectory or a claim of achieved 50 Hz real-time control.

`ControlClock` represents 50 Hz at 500 Hz as exactly one update per 
```

<!-- PRAXIS_CONTEXT_PACK
{"default_branch":"main","default_branch_sha":"83b3833f53f66f404cf5f428b9648860adb88323","instructions":[{"chars":3844,"excerpt":"# Go2 repository rules\n\n`main` is the stable code line and long-term route. The active research\nfrontier may live on a separate `research/*` branch. This file contains\nrepository guardrails; it is not a scientific plan or current-status report.\n\n## Research handoff\n\nUse [OPERATING_GUIDE](docs/OPERATING_GUIDE.md) to turn the current objective into\na bounded task that a human or any model can execute. State the decision it\nserves before choosing a method, checkpoint, parameter or pass threshold.\nUpstream defaults are candidate choices, not validated research requirements.\nDo not silently invent missing scientific decisions; resolve the specific gap\nwhile continuing independent authorized work. Keep routine execution autonomous.\n\nBefore choosing research direction, read `docs/PROJECT_RECORD.md` and then `docs/TOPIC_AUDIT.md`. They are the repo-native canonical scientific state and topic audit. `CURRENT.md` remains the canonical execution-frontier pointer. Chat history, Memory, screenshots, and old Library copies cannot override these repo records.\n\n## Task discovery bootstrap\n\nAt session entry or when resuming a stale task, refresh the remote source of\ntruth once. Repeat when new upstream work could affect the task, not before\nevery small edit:\n\n1. run `git fetch origin --prune`;\n2. read `origin/main:CURRENT.md` (for example with\n   `git show origin/main:CURRENT.md`) to discover the active research branch;\n3. compare the local active branch/worktree with `origin/<active-branch>` and\n   fast-forward only when safe; never reset, discard, or delete local commits,\n   untracked files, or raw evidence to make it match;\n4. only after that, read the active branch `CURRENT.md`, current task, and exact\n   parent/closeout evidence.\n\nA stale local `CURRENT.md`, local branch tip, or cached task is never sufficient\nto conclude that no new task exists. If the local branch is ahead or diverged,\npreserve it and report the divergence instead of guessing which side wins.\n\nRead [`CURRENT.md`](CURRENT.md) for the single maintained frontier pointer.\nFollow that pointer to the frontier branch, its task, and exact `RESULTS.md`.\nUse the canonical [Research Execution SOP](docs/research/SOP.md) from\n`main`. A branch-local `CURRENT.md` is navigation only and cannot override\n`main/CURRENT.md`, the SOP, or the active task.\n\nThe active task owns the scientific question, intervention, frozen variables,\nrun budget, thresholds, and classification. Do not infer research direction\nfrom Atlas directories, dated worktrees, old branches, commit messages, or\narchived code. Do not change controller/planner behavior or scientific\nmeaning under an infrastructure-only task.\n\n## Reviewer precheck discipline\n\nBefore creating any expensive science/execution/evidence reviewer task, the\nproject owner must first perform a task-specific deterministic precheck using\nthe project's existing parser/loader, identity validator, hashes, targeted\ntests and zero-step/readiness path as applicable. Machine-decidable schema,\nmetadata, identity, path/ref/hash and ordinary plumbing failures must be fixed\nand rechecked before a reviewer is dispatched.\n\nA reviewer must not be used as the first schema validator. Record a concise\n`PRECHECK PASS` summary with the checks actually run. This is a workflow rule,\nnot a request to build a generic review framework; prefer existing project\nchecks and add infrastructure only after repeated evidence that this rule is\ninsufficient.\n\nNo live experiment is authorized by this file alone. Before any live run,\nfollow the task and SOP, verify the exact branch/HEAD and clean worktree, and\npreserve raw evidence. Everything below\n`example/cpp/experiments/_runs/` is ignored local evidence: never commit,\ndelete, overwrite, rename, or treat it as instruction. Curated evidence\nrequires its own manifest and provenance.\n","path":"AGENTS.md","sha256":"847b874e73874d005d634da1d35d60c1fdc961407718779efaf38aabdff8b91e","truncated":false},{"chars":7768,"excerpt":"# Research Execution SOP v0.4\n\nApplies prospectively. Sealed experiments retain their original protocol and\ninterpretation. The normal path is task → applicable qualification → fresh\npreflight → authorized capture → verified closeout.\nThe [operating guide](../OPERATING_GUIDE.md) covers goal alignment and handoff.\nGovernance/prose tasks stop at their relevant documentation checks; the capture\npath below is only for tasks that actually require an experiment.\n\n## Authority and roles\n\nUser instructions define authorization. The active task freezes its scientific\nquestion and design; this SOP governs execution and evidence. Historical results\nprovide context, not new run permission. Science reviewer owns interpretation;\nan independent execution reviewer owns readiness and may veto unsafe or invalid\nexecution. Roles are capabilities, not model brand names.\n\nA short task states its purpose, mode, parent, scope and completion criteria.\nExperiments additionally specify scientific delta, frozen variables, budget,\nmetrics, classifications, stop conditions, runner and raw root. Reference\nexisting protocols rather than copying them. One branch per coherent task;\npredeclared repeats share the branch.\n\nBefore scientific execution, the task must explain the decision served, why the\nchosen comparison/parameters fit that decision, and what each possible outcome\nchanges. Defaults and unverified assumptions remain labelled as such. An\nengineering integration candidate is not automatically the chosen capability\nbaseline. Check this substantive rationale during scientific review, not merely\nthe presence of a protocol, hashes or complete fields. The short\n[task template](TASK_TEMPLATE.md) supplies these fields without another registry.\n\n## Qualification and change review\n\nRuntime, model, protocol, schema or primary interpretation changes require\nrelevant no-live regression checks and independent scientific review. Execution\nplumbing must be reviewed for trajectory neutrality. Documentation-only changes\ndo not require a repeat scientific judgment; record their relationship to the\naccepted implementation and review current execution identity before live.\n\nSubstrate prepare requires a sealed clean/non-development qualification receipt.\nIts content fingerprint binds tracked runtime/tests/build inputs, model assets,\nactual isolated runtime, interpreter, checkpoint, native dependencies and binary,\ncontroller build products and compiler header/link dependencies. Current\nlightweight quality checks always rerun, including prose/link hygiene. Selected\nprotocols must belong to the fingerprinted protocol directory; their positive\ninteger budget is bound to preparation and explicit authorization.\nChanged inputs invalidate reuse; matching inputs may reuse offline tests across\ndocumentation or merge commits. Producer HEAD is retained, never rewritten.\nCurrent task, review, exact execution HEAD and user authorization are not cached.\n\n## Fresh preflight\n\nThe Go2 Praxis dispatcher requires a canonical TaskSpec resource manifest on\nnew queued tasks. Declare the `substrate` root for the CTS checkpoint with the\nSHA-256 from `tools/substrate/sources.lock.json`, and declare the runtime modules\nand exact distribution versions required by that task. The host binds\n`substrate` to its trusted `.substrate` directory and probes those modules with\nthe reliable substrate Python. A missing or mismatched declared resource stops\nbefore Luna starts and consumes no scientific attempt. The worker's own\nprovisioning and the scientific preparation checks still verify the complete\nsource lock, model loading, and execution semantics. Older task documents\nwithout a manifest must be reissued under the new contract before dispatch;\ndo not silently relax this gate to replay them.\n\nBefore capture, the runner continuously holds the experiment lock through\npreflight and the whole campaign. Check exact HEAD, expected logical branch\nidentity, and clean worktree. A named expected branch remains valid for manual\nexecution; a detached Praxis v2 worktree requires the complete matching Praxis\nbinding and exact frozen commit. Also check current inputs, fresh output, no\nstale runtime processes, and transport-specific constraints. DDS uses actual\ndomain/port checks; reviewed in-process runners have no fictitious DDS\nrequirement. Never run a real runner as a preflight test.\n\nUse the accepted parent as diff-base. Automatically classify changed runtime,\nrunner, schema, scene and analyzer files; explicit surfaces add to this set.\nAny runner change records its actual diff, including explicit runner declarations.\nVerified applicable qualification replaces duplicate offline tests; it never\nreplaces fresh lock/process/input checks. Unknown executable substrate files\nare conservatively runtime changes. Failed prerequisites prevent launch.\n\n## Attempts, exploration and stopping\n\nThe first valid post-handoff state/control sample consumes an attempt, reserved\ndurably before logging. Prelaunch execution-only faults may be repaired while\npreserving failed artifacts. A proven execution-only boot fault may receive one\nrecovery only if the task permits it. A stricter frozen task overrides this default.\n\nNo opportunistic retry, replacement, threshold change or sample selection after\ncapture. Safety failures and broken execution/evidence stop. A task may predeclare\nan exploratory matrix whose expected performance failures are retained outcomes\nand whose remaining cases continue; that permission must exist before results.\nConfirmatory designs freeze intervention, comparisons, sample plan and stopping.\nThe sealed rl-flat-compatibility-v1 campaign remains first-nonpass-stop, no retry.\n\n## Evidence and interpretation\n\nRaw evidence is append-only across runs and immutable within a sealed run.\nRecord source/inputs, environment, command, attempt ledger and terminal status.\nVerify capture independently; local verification includes the external ledger.\nPortable verification must explicitly say the external ledger was not checked.\nShared runtime formulas are supplemented by independent algebraic checks;\nmodel contact reconstruction is a separate zero-integration audit, not replayed\ndynamics or proof of causal attribution.\n\nDeterministic offline salvage is allowed only with unchanged raw bytes, unique\nsource-grounded mapping and independent invariants. Corrections are new artifacts\nand superseding interpretation, never rewriting history. Distinguish execution,\nevidence, causal inference and scientific performance boundaries.\n\nRepeated deterministic traces test repeatability, not statistical success rates.\nCapability comparisons need a prospective task/terrain/seed or perturbation plan,\ninformation and compute conditions, uncertainty reporting and declared exclusions.\nCheck pretrained-policy deployment semantics before attributing transfer failure\nto policy quality. Same robot name is not equal physics or equal task distribution.\n\n## Closeout and navigation\n\nFor experiments, the usual tracked artifacts are RESULTS.md, analysis.json and\nprovenance.csv. Routine engineering and documentation work use only the records\nneeded to support their actual claims; do not manufacture empty data artifacts.\nArchive source-bound raw evidence, including failed outcomes and the ledger,\nverify archive members, then regenerate the workspace catalog. Do not duplicate\nprotocol text or state records across manually maintained status pages.\n\ndocs/research/current.json owns execution navigation; CURRENT.md and START_HERE\nare generated views. PROJECT_RECORD owns research conclusions; TOPIC_AUDIT changes\nonly when topic judgment changes. Historical branch/worktree cleanup is a separate\nowned maintenance action, never implicit deletion during an experiment.\n","path":"docs/research/SOP.md","sha256":"8e52478bea6fd2b686ac1fdaeef4a8ad8f4a46b0c05cc16986867c0d59f333dc","truncated":false},{"chars":13808,"excerpt":"# Go2 — PROJECT_RECORD\n\n> **最后更新：2026-09-28**\n> **状态：MUJOCO/MJX ARCHITECTURE REFRAMED; #189 SEMANTIC ERRATUM RECORDED; GATE 0 INCOMPLETE**\n> **角色：repo 内项目 canonical 入口；回答“现在是什么、已证明什么、当前 Gate 与下一步是什么”。**\n> **Source of truth：本 repo 同时承载研究认知、代码、配置、实验与结果；raw evidence 以 commit / result / Praxis evidence 为准。**\n> **配对文档：`docs/TOPIC_AUDIT.md` 记录选题 landscape、候选攻击与路线演化。**\n\n## 0. 接手顺序\n\n任何新 agent / 新负责人：\n\n1. 先读本文件；\n2. 再读 `docs/TOPIC_AUDIT.md`；\n3. 核 `CURRENT.md`、当前 branch / commit / result；\n4. 若涉及 Atlas host state，用 Praxis diagnostics / workspace evidence 重新验证；\n5. 不用聊天、Memory、截图覆盖 repo 事实。\n\n状态词：`CURRENT / VERIFIED / LEGACY BASELINE / HOLD / RE-AUDIT / SUPERSEDED / HISTORICAL`。\n\n## 1. [2026-09-28 | CURRENT | SNAPSHOT] 当前项目\n\n#189 已形成第一张 bounded RL capability map。其封存执行与原始 case 记录仍在\n[原结果](validation/rl_capability_map_successor_20260924/RESULTS.md)；\n[2026-09-28 语义勘误](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)\n限定了 low-friction 与 yaw 结论。5 cm、10 cm、repeated-step 的结论保留；\nv1 low-friction PASS 仅是冻结场景中的几何/任务目标 PASS，不是低摩擦鲁棒性\n证据；yaw 仍为冻结阈值下的 PERFORMANCE_FAIL。\n\n### Planned architecture\n\nMuJoCo 是当前项目 canonical evaluation physics；MuJoCo/MJX 是目标 scalable\nsubstrate，尚未完全实现。Go2 是第一 testbed，不是项目 identity。MJPC/iLQR 是\n强 gradient-based comparator，但不享有默认 truth 或 privileged planner 地位。\n按任务和 failure evidence 选用 sampling/search、learning、contact-implicit 等\n成熟 controller/solver infrastructure。研究 ownership 在 task / information /\ntiming / intervention 定义、诊断、公平比较与证据要求确实支持的新机制。基本\nGo2 demo 是交付约束，可复用成熟组件；从零重写控制器本身不构成科学贡献。\n\n下一步接口方向限定为 `TaskSpec`、`ScenarioSpec`、`InformationSpec`、\n`TimingSpec`、`ControllerAdapter` 和 canonical `Evaluator` / physical-oracle\nboundary。该 contract 仍是 planned architecture；实现留待本轮语义修复通过后，\n再按独立任务推进。\n\n### Currently executable capabilities\n\n当前可执行面是 task-specific：仓库有 MuJoCo Go2 assets、恢复后的 schema-2\n公开 RL execution/analyzer/offline verifier，以及 MJPC/iLQG static admission\nutilities。后者不是闭环 locomotion comparison。当前尚无通用\nTask/Scenario/Information/Timing API，也没有已经实现的 generic multi-controller\nevaluation platform。\n\n### Scientifically verified results\n\n已验证结论限于公开 RL checkpoint 在封存 adapter、reset、scene 和命令上的\n#189 九例 map。原始轨迹与尝试账本未改写；语义修正见 erratum。没有证据证明\n跨 controller bottleneck、普遍低摩擦鲁棒性或论文 gap；Gate 0 仍未完成。\n执行 frontier 跟随 `CURRENT.md`。\n\n## 1D. [2026-09-24 | VERIFIED / BOUNDED; 2026-09-28 ERRATUM] RL capability map 正式完成\n\nPraxis v2 #189 在 capture HEAD `e40b0933572345f23b37e3bb06350518fde63e76` 上完成冻结 schema-2 `rl-capability-map-v1` campaign。九个 case 各执行一次，authoritative ledger 记录 9/9 scientific attempts，capture 为 `CAPTURE_COMPLETE / CHARACTERIZED`，未发生 retry、SAFETY_STOP 或 INTEGRITY_STOP。独立 offline verifier 最终返回 `VERIFIED`，核对 external ledger、逐 case raw replay 与 sealed flat-reference digest，且 verification `physics_steps=0`。正式 closeout 为 `docs/validation/rl_capability_map_successor_20260924/RESULTS.md`，result commit `de21d8c3267e1c985cb57ed2d02004c686d05bd1`，Praxis review publication commit `35e69f652e986af13c147a6fe4e8fc9eea70c5f1`。\n\n原始冻结结果分类及 #194 勘误后的解释：\n- `flat_reference`：PASS，mean vx 0.8858825097 m/s，sealed digest 与 #166 精确一致；\n- `flat_half_speed`：PERFORMANCE_FAIL；纵向 tracking 本身通过，但 flat cross-axis gate 失败，lateral displacement 0.57465 m、yaw 0.24710 rad；\n- `flat_reverse_probe`：PERFORMANCE_FAIL，目标 -0.5 m/s，mean vx -0.35590 m/s；\n- `flat_lateral_probe`：PERFORMANCE_FAIL，目标 vy 0.25 m/s，mean vy 0.16589 m/s；\n- `flat_yaw_probe`：PERFORMANCE_FAIL；从未修改的 raw trajectory 离线更正后，目标 wz 0.5 rad/s、mean body-local qvel-z 0.1038956543 rad/s、MAE 0.3961043457 rad/s，仍超过冻结 0.1 rad/s tolerance；\n- `step_5cm_cross`、`step_10cm_cross`、`repeated_steps_cross`：PASS 结论保留，其中 repeated steps 为冻结 5/15/5 cm profile；\n- `low_friction_cross`：原始输出 PASS 保留为 frozen-scene 几何/task-goal classification；因 v1 effective contact 使用 foot friction 且足底也由 normal floor 支撑，低摩擦 robustness interpretation 撤回。\n\n该结果只说明此 checkpoint / adapter / reset / scene / command set 下，**1 m/s 的 5/10/repeated-step 几何任务在冻结条件下通过，command probes 出现性能边界；低摩擦 robustness 未被验证。** 不能由此推出“terrain 已解决”“方向控制是论文 gap”或“MJPC 一定更好”。先审计成熟 Go2 whole-body control implementation 可复用面，再为对齐比较定义独立任务。\n\n标准 verifier 首次因 detached-worktree branch identity 比较限制在 raw replay 前失败；最终只用 documented in-memory identity adapter 纠正 detached actual branch 与逻辑 Praxis branch 的比较，未修改 source、protocol、prepared/capture evidence 或任何 raw trace。该事件属于 verification plumbing，不是科学失败。\n\n## 1C. [2026-09-24 | VERIFIED / BOUNDED] shared-transfer 正式组合确认\n\nPraxis v2 #166 在精确起始 HEAD `9e82e56ac2a5db63d7834e86ce402d542bf10ae8` 上完成冻结 `rl-shared-transfer-combination-v1` campaign。两例 `combined_1` / `combined_2` 均 PASS，各 6000 steps，mean vx = 0.8858825097 m/s；两例 trace SHA-256 完全一致。authoritative ledger 与 offline verifier 都确认恰好消耗 2 次 scientific attempts，且无 retry。正式 closeout 为 `docs/validation/shared_transfer_combination_formal_v2_20260923/RESULTS.md`，result commit `6f67769851aaffed1c1826d138293e52265dbba7`，Praxis review publication commit `076f72dfcbab32dbed0c364b5f88f753f500123e`。\n\n该结果只证明：**完整 pinned shared deployment combination 在冻结 1 m/s 平地协议下保持已封存源策略能力，并具有精确重复性。** 它不证明低速、terrain、hardware 或 general robustness。原先“单因素通过不等于组合通过”的未决点至此关闭。\n\n执行侧发生过两个非科学故障：原始 offline verifier 对 detached HEAD 的 branch identity 比较不兼容；Praxis 旧 closeout 一度拒绝目录型 evidence bundle。前者通过不修改 capture/raw evidence 的窄 identity adapter 完成零物理 offline verification；后者由 Praxis publication-only salvage 修复，未重新运行 capture、未增加 scientific attempt。不得把这些 closeout/verification 基础设施问题写成科学失败。\n\n## 1B. [2026-09-23 | VERIFIED / BOUNDED] 公开RL源条件基线\n\n十例固定协议已封存，见[完整结果](validation/rl_baseline_20260923/RESULTS.md)。\n源模型1 m/s指令平均速度0.938050 m/s；源重复与共享策略接口三条轨迹完全一致。\n原条件0.15 m/s仍仅0.021824 m/s，低速不足不能全归模型或接口移植；奖励机制\n尚未证实。变速纵向跟踪好但横漂超限；默认23 cm楼梯在2.5 s因机身前部接触\n第二级立面停止，不能称摔倒或证明永远无法跨越。共享模型单因素1 m/s通过，\n不等于模型/home/接口组合已确认。这是有限平地参考，不是强地形能力天花板。\n\n## 1A. [2026-09-22 | CURRENT | ENGINEERING] 可执行的新阶段底座\n\n治理与首次失败的离线诊断见\n`docs/validation/governance_diagnosis_20260922/RESULTS.md`。资格缓存按真实源码、\n环境、构建及依赖内容复用，执行仍绑定当前 HEAD、任务、独立审查与授权；\n原实验预算和 FAIL 均未改变。500 次策略输入及 5000 次 PD 控制与上游独立\n实现逐点一致，5001 帧接触重建一致。0.15 m/s 指令确有策略响应；低速奖励\n区分度、模型及启动条件差异仍是候选解释，不能从单条轨迹宣布单一根因。\n该轮没有新物理步进，也没有新增能力通过结论。其提出的上游复现与受控移植\n方案现按新任务推进；不继续已封存的 v1。\n\n工程准备分支 `research/substrate-prelaunch-20260922` 已通过 PR #139 合入主线\n`c5582af60b802b688e4e526845402deb33cf29cd`。其任务见\n`docs/research/TASK_REPOSITORY_CEE_20260922.md`，最新结果见\n`docs/validation/repository_cee_20260922/RESULTS.md`。首轮准备验收保留于\n`docs/validation/substrate_prelaunch_20260922/RESULTS.md`。可靠性验收保留于\n`docs/validation/substrate_reliability_20260922/RESULTS.md`。首轮工程记录保留于\n`docs/validation/substrate_foundation_20260922/RESULTS.md`。\n\n现有 clean 控制出口改为根据当前周期求解/映射结果决策；增加失败、恢复、\n非有限/越界候选测试。DDS 清理测试采用隔离 proc fixture，生产 fail-closed\n检查不变。旧 sealed evidence 不变；新二进制尚无行走验收。\n\n`tools/substrate/` 新增命名关节/观测/动作边界、源锁定、模型资产闭包与物理\n指纹、真实 public RL 推理、原生 MJPC iLQG 静态求解准入，以及原始证据输出。\n两者共同使用现有 MuJoCo 3.3.6 模型与力矩出口，但信息条件不同，不能据此做\n公平能力对比。工程准入不是 Gate 0。首轮平地 RL 移植验收已有前瞻协议、\n闭环 runner、分析器及三次失败即停预算；其准备流程禁止真实物理步进，\n准备阶段没有启动授权。用户现已明确要求“合入主线，然后开正式实验”；\n正式采集在 `research/substrate-first-capture-20260922` 的准确 HEAD\n`09a9a31e2ab6eefcd4d3193107e8e17dad642129` 完成。执行任务见\n`docs/research/TASK_SUBSTRATE_FIRST_CAPTURE_20260922.md`，协议定义见\n`docs/research/SUBSTRATE_FIRST_CAPTURE.md`。\n\n首轮完整运行 5000 个物理步 / 10 秒，5001 帧证据通过独立复算及外部次数\n账本核验。冻结终点位移 0.364124 米（要求 >=1 米），末 5 秒速度 MAE\n0.107403 m/s（要求 <=0.1 m/s）；两项均失败，科学结果 FAIL。未触发安全\n条件，未发生力矩饱和。按原协议停止，第 2、3 次 NOT_RUN；重复性未检验。\n最早失败边界为 scientific / metric_failure，具体机制尚未归因。该结果\n不能外推为策略整体能力失败或完整 Gate 0 结论。原始证据与授权、账本已\n归档；见 `docs/validation/substrate_first_capture_20260922/RESULTS.md`。\n\n后续可靠性加固补齐独立依赖环境、源码/二进制构建绑定、模型输入快照、策略\n状态隔离和重放、严格类型/时钟契约、超时子进程清理、失败证据封存及独立\n校验，并恢复 SOP 预检入口。统一 `tools.substrate.qualify` 命令在干净提交上\n完成工程验收；其通过仍不是正式实验的科学授权或能力结论。\n\n## 2. [2026-09-17 | VERIFIED / LEGACY] Sealed flat baseline\n\n已验证 legacy chain：\n\n`speed target → fixed low-speed trot → Raibert nominal foothold → prebuilt swing → exact/direct IK → SRBD MPC → strict ID-WBC → torque envelope → MuJoCo`\n\n冻结配置：\n- period 0.60 s；\n- duty 0.75；\n- step length 0.091 m；\n- nominal speed ≈0.15167 m/s；\n- nominal foot lift 0.020 m；\n- torque envelope 35 N·m。\n\n2026-09-17 三次 fresh-worktree / fresh-build / 零调参平地重复均通过：64/64 cycles，clean target reject=0，strict WBC/QP reject=0，hard/emergency stop=0。\n\n这只证明**低速平地 low-level stack 可重复、可审计**。\n\n没有证明：\n- clean baseline 已完成 5 cm terrain crossing；\n- terrain planner 有效；\n- fixed trot / Raibert 是最佳长期路线；\n- 高速、变速、多地形能力成立。\n\n关键纠正：sealed clean baseline **从未正式做过 5 cm terrain crossing**。\n\n## 3. [HISTORICAL] 旧 terrain 线留下的 failure clues\n\n旧路线曾经历：\n`normal swing → known-step adapter → V2 corridor → workspace clamp → direct IK guard`\n\n可保留线索：\n- world-frame 足端轨迹合理，不代表 body/hip motion 后中间腿姿态可行；\n- min-clearance / V2 target 曾遇到 calf joint-limit infeasibility；\n- 不断加 workspace clamp 可能掩盖真正 feasibility boundary。\n\n这些只属于旧架构 failure clues，不是当前 whole-body substrate 的已知 failure，也不是论文题。\n\n## 4. [2026-09-18→19 | TRACEABILITY] 为什么推倒旧底座\n\n关键触发：\n\n| 质疑 | 结论 |\n|---|---|\n| “baseline 干净了，但路线本身会不会不好？” | 不再把 Raibert/fixed trot/SRBD 当长期架构 |\n| “baseline 不是没做越障吗？” | 纠正叙事：clean baseline 未正式做 5 cm terrain |\n| “terrain-aware 不应该在 swing 上层开始吗？” | foothold/swing/body/timing 作为独立 planning freedoms 审计 |\n| “老师任务和论文题不能拆两条” | 形成同一路线 dual-goal 硬约束 |\n| “为什么不能推倒重来，换最佳研究底座？” | 转向 whole-body substrate audit |\n| “DIAL 算力太重、仓库也不活跃” | DIAL 从 default 降为 challenger |\n\n重要原则：clean baseline 的价值是**可信对照组**，不是最终系统的架构前提。\n\n## 5. [CURRENT | SUBSTRATE] 现行研究底座\n\n### Physics / embodiment\n- **MuJoCo**：当前 canonical evaluation physics；比较应共享物理模型与 outcome semantics。\n- **MuJoCo/MJX**：目标 scalable substrate 方向；MJX/GPU execution 尚未成为完整可执行项目接口。\n- **Go2**：第一 testbed，因现有资产与路线基础；不是 project identity 或预设 contribution。\n\n### Controller families and scientific ownership\n\nMJPC/iLQG 是强 gradient-based comparator，不是默认 truth。公开 Go2 RL 是 learning\ncapability baseline / possible teacher or prior。Sampling/search、contact-implicit\n或 hybrid methods 按具体 failure evidence 再选。比较需显式记录各控制器的信息条件、\n内部 cost/reward 和优化方式，同时尽可能固定模型、初态、命令、场景与 terminal\nmetrics。\n\n优先复用成熟 solver/controller infrastructure。项目的科学 ownership 位于 task、\ninformation、timing、intervention 的定义，diagnostics、对齐比较和证据链，以及\n证据支持的新机制。已有 Go2 demo 可由成熟组件满足；从头重写通用控制器不自动\n产生 novelty。旧 Raibert + fixed trot + SRBD MPC + ID-WBC 保留为 legacy baseline。\n\n### RL baseline\n\n优先直接使用公开 checkpoint，不从头训练。#189 的封存结果可作 bounded RL\ncapability map：5 cm、10 cm 与 repeated-step 结论保留；low-friction case 只保留\nv1 frozen-scene 几何/task-goal PASS，不证明低摩擦 robustness；half-speed、reverse、\nlateral、yaw 仍为原有 PERFORMANCE_FAIL，其中 yaw 的 corrected metric 见\n[erratum](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)。这些\nRL-only findings 不能直接升格为跨-controller bottleneck，也不能外推到更高台阶、\nhardware 或 general robustness。0.15 m/s 仍是历史局部兼容性设定，不是全项目目标。\n\n### DIAL / MPPI and other challengers\n\n不预设单一 challenger。Sampling/search 或 contact-implicit 方法只有在统一 benchmark\n指出 gradient basin、nonsmooth contact、mode search 或 multimodality 等具体诊断问题\n时，才按任务决定是否启用。\n\n## 6. [CURRENT | SUBSTRATE GATE 0] 当前 Gate\n\n当前 Gate 建立可复用的统一评测与 controller-family failure map；不以预选 MJPC\n或发明新 controller 为目标。依赖关系：\n\n`benchmark semantics → mature implementation audit → aligned controller comparisons → failure-mechanism diagnosis → method decision`\n\n阶段边界：\n1. 任务化定义共享 model / scenario / reset / metrics / success and safety semantics。\n2. #189 已提供第一张 RL map；其 low-friction / yaw 解释按 erratum 修正。\n3. 下一步先审计可复用的 Go2 whole-body controller/MJPC implementation、任务和 runner，避免从零重写已有闭环能力。\n4. 随后为所选 comparator families 写独立的对齐任务；cost、信息和优化差异均须显式记录。MJPC/iLQG、sampling/search 或 learning family 都不享有先验 truth 地位。\n5. 需要大规模 rollout / learning 时再实现 MuJoCo/MJX 扩展，不为“统一外观”提前宣称 GPU substrate 已完成。\n\nGate 目的不是选“永远唯一 controller”，而是定位可复现 failure，再决定成熟方案、\ntuning、部署修正或新 mechanism 哪种解释得到证据支持。任何 live execution 都由其\n单独 task 与 SOP 授权；本轮 R0 不启动 experiment.\n\n## 7. [CURRENT | EXECUTION] Repo / host 状态边界\n\n实际工作区、branch/HEAD、dirty 状态和远端关系每次接手重新核验，命令见\n[项目推进指南](OPERATING_GUIDE.md)。本文件不维护会过期的“最新 main SHA”或\n机器工作分支快照；具体运行的历史 SHA 保留在对应结果中。\n\n首轮 0.15 m/s 平地 RL 移植验收的 FAIL closeout 仍保留；随后 1 m/s shared-transfer 正式组合已两次 PASS。两者回答的是不同冻结条件，不能互相改写。完整 Substrate Gate 0 仍未完成；当前尚不能代表 MJPC/RL/DIAL 地形能力已完成验证.\n\n## 8. [CURRENT | TOPIC STATUS] 选题状态\n\n当前问题保持开放：\n\n> 在统一 MuJoCo/MJX 物理、任务与评测语义下，learning、gradient-based MPC 与 sampling/search controller 分别在哪些 embodied-control 条件下出现稳定 failure；哪些 failure 能被复现、机制化，并确实需要新算法，而非 tuning、部署差异或成熟方案？\n\n旧候选：\n- L9 Preview：`HOLD / RE-AUDIT`\n- L10 / TimedReach / SEFR / FSEF：`HOLD / RE-AUDIT`\n- terrain-aware foothold+swing：legacy mechanism / possible benchmark intervention\n\nGate 0 前不得从历史候选直接继续造方法。\n\n## 9. [CURRENT | NEXT]\n\nRL shared-transfer 与首轮九例 capability map 已完成封存，不重跑。先审计成熟 Go2\nwhole-body control implementation 是否已有可复用的闭环 task/controller/runner。完成该\n审计后，再定义 MuJoCo 上对齐的 command/terrain comparison：保留平地 reference、\nhalf-speed/reverse/lateral/yaw probes、5 cm/10 cm/repeated-step anchors；low-friction\nanchor 在修正后的 v2 scene 上只能由新 task 前瞻授权，不能接续 #189 或由本次\nengineering task 自动启动。若需要 scale-up，再评估 MJX。\n\n0.15 m/s 不足、横漂与 23 cm 楼梯 base-contact stop 仍是观察边界，不是论文问题。\nGate 0 前不从历史 L9/L10/FSEF 候选直接造方法；新 mechanism 必须由跨 controller\n结果或可证伪的 controller-specific failure 对比支持。\n\n## 10. [2026-09-22 | GOVERNANCE] Repo-native 项目记录\n\n从 2026-09-22 起，本文件与 `docs/TOPIC_AUDIT.md` 是项目级研究认知 source of truth。Library 不再维护正文副本，只保留跨项目 `RESEARCH_INDEX` 与不可恢复历史材料。\n\n## 11. 维护协议\n\n重大变化必须更新：\n- research question；\n- substrate / benchmark；\n- 正式 Gate verdict；\n- 重要正/负结果；\n- 会改变判断的失败根因；\n- 用户质疑触发的路线修正。\n\n2026-09-24 review 流程事件形成一条长期执行规则：在创建昂贵 science /\nexecution / evidence reviewer 前，项目负责人必须先做 task-specific deterministic\nprecheck。strict loader、五字段 Praxis identity、path/ref/hash、targeted tests、\nzero-step/readiness 等机器可判定问题应由负责人先发现、修复并重跑，不能交给\nreviewer 首次发现。此前 contract-hash / approval-inheritance prototype PR #183\n已明确不合入 main；当前选择“ChatGPT 负责人现场 precheck + 现有项目检查”的\n轻量方案，只有未来真实反复漏检时才考虑增加极薄 runtime gate。\n\n普通 bug、编译、命令、参数流水不写。\n\n更新顺序：\n1. 核 repo/result 事实；\n2. 先改 CURRENT snapshot / Gate / next；\n3. 再补 traceability；\n4. 被替代结论标 `SUPERSEDED`；\n5. topic 变化同步 `docs/TOPIC_AUDIT.md`；\n6. 顶层 frontier 变化才同步 Library `RESEARCH_INDEX.md`。\n","path":"docs/PROJECT_RECORD.md","sha256":"4c0d73c56e5db58eeca4d74bd69df95b9a1d3058e9fe6736d1fbdf2d17115ba0","truncated":false},{"chars":7881,"excerpt":"# Go2 — TOPIC_AUDIT\n\n> **最后更新：2026-09-28**\n> **状态：ACTIVE TOPIC AUDIT / 尚未锁定论文题**\n> **角色：repo 内 canonical 选题审计；记录“为什么选 / 为什么不选”的证据链。**\n> **项目运行状态：以 `docs/PROJECT_RECORD.md` 为准。**\n> **当前 canonical 决策：MuJoCo 是当前 canonical evaluation physics，MuJoCo/MJX 是目标 substrate；Go2 是第一 testbed；不预选单一 controller，先让对齐 benchmark 和 failure evidence 决定后续方法。**\n\n## 0. [CURRENT | SNAPSHOT]\n\n2026-09-28，#189 仍是第一张封存 RL capability map，但须按\n[语义勘误](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)\n解释：5 cm、10 cm、5/15/5 cm repeated steps 的 bounded terrain conclusions\n保留；v1 `low_friction_cross` 只保留 frozen-scene 几何/task-goal PASS，不是低摩擦\nrobustness evidence；修正 body-local qvel-z 后 yaw probe 仍为 PERFORMANCE_FAIL。\n该结果仍只属于一个 checkpoint/controller，不能把任何 case 直接升格为论文 gap。\n\n当前 architecture decision：\n\n`MuJoCo canonical evaluation physics → MuJoCo/MJX scalable substrate direction → shared task/evaluation semantics → reusable controller families → aligned failure map → mechanism diagnosis`\n\n- **Go2**：第一 testbed，不是项目 identity。\n- **MuJoCo/MJX**：统一物理与评测的 substrate 方向；MJX scalable path 尚未完全实现。\n- **MJPC/iLQR**：强 gradient-based comparator，不是 privileged default truth。\n- **RL checkpoint**：learning capability baseline / possible teacher or prior。\n- **Sampling/search、contact-implicit/hybrid**：按 task 和 failure evidence 决定是否启用。\n- **成熟 infrastructure**：优先复用；科学 ownership 在 task/information/timing/intervention、diagnostics、比较和 evidence-driven 新机制。\n\n研究问题保持开放：\n\n> 在统一物理、任务和评测语义下，不同 controller family 在哪些 embodied-control 情况下出现稳定、可复现、机制可解释的 failure；其中哪些确实需要新算法，而不是 tuning、部署差异或成熟方案？\n\nL9、L10/TimedReach、SEFR、FSEF 仍为 `HOLD / RE-AUDIT`。本项目尚无 generic multi-controller evaluation platform。\n\n## 1. [SUPERSEDED → REFRAMED] 老师交付与科研架构\n\n曾将老师的 Go2 terrain demo 与科研路线绑定为 dual-goal 硬约束，以避免维护两套\n互不相关的系统。现在将其改为最低交付约束：如果成熟开源 controller 能低成本\n满足基本效果，可直接复用。为了看起来“不是 clone”而从零重写成熟控制器，不会\n自动产生科学价值。\n\n新的原则：\n1. 基本 Go2 控制/越障效果是交付要求，不决定科研架构。\n2. 可复用成熟 simulator、solver、controller 和 RL infrastructure。\n3. 项目必须掌握 task、information、timing、intervention、benchmark、diagnostics 和 evidence。\n4. 只有 failure evidence 指向缺失机制时，才实现新 algorithmic component。\n5. 候选仍需可证伪、近期能收缩问题空间、资源可承担，且不是弱 baseline 或旧 decomposition 制造的问题。\n\n## 2. [HISTORICAL] 选题主线如何演化\n\n### Phase A：5 cm step / terrain-aware\n最初围绕 known step、foothold、swing clearance 和 joint-limit feasibility 推进。\n\n用户持续追问：\n- 为什么就是 5 cm？\n- 为什么固定 trot？\n- baseline 真的越障失败了吗？\n- terrain planning 为什么只在 swing 层修？\n\n这迫使项目从“修一个高度”转向 capability frontier。\n\n### Phase B：L9 Preview\n研究 preview / future terrain timing 对 foothold/body control 的作用。后续发现局部效应可能混有 reference-index / timing implementation 问题，且与老师任务关联不够直接，降为 `HOLD / RE-AUDIT`。\n\n### Phase C：TimedReach → SEFR → FSEF\n尝试把问题抽象成“几何可达但 schedule 不可执行”的 limb-level gap。\n\n强前作与反对意见不断压缩空间：\n- KCFRC-like path + retiming；\n- TOPP / SIPP / ST-RRT*；\n- SI-RRT / kinodynamic planning；\n- whole-body MPC / optimizer。\n\n最终剩余问题过窄，而且可能只是旧 decomposition 的产物，因此暂停。\n\n### Phase D：底座重置\n用户提出“为什么不能推倒重来，换最佳研究底座？”后，优先级改变：若 whole-body predictive control 能自然调整 body/contact/timing，旧候选就不值得围绕 hierarchy 发明中间层。\n\n### Phase E：统一 substrate 与 controller-family 比较\n\n#189 后，项目保留 MuJoCo 作为当前 canonical evaluation physics，把 MuJoCo/MJX 作为\n目标 substrate；不把 Go2 或 MJPC/iLQR 当作项目身份或先验主方法。成熟 solver/controller\n优先复用，研究工作转向任务与信息语义、对齐比较、诊断及由证据支持的新机制。\n\n## 3. [SUPERSEDED] DIAL 曾作为 default 的原因与撤回\n\nDIAL full-order、torque-level、training-free、sampling-based，且不需要把固定 gait 当硬 constraint，看起来最能解除旧架构天花板。\n\n但继续审计后：\n- typical sampling rollout 成本高；\n- RTX 3090 级硬件已有实时性压力；\n- 仓库维护活跃度有限。\n\n因此“自由度最高”≠“最适合作为日常研究底座”。\n\nDIAL/MPPI 归于 sampling/search family；只有具体任务的 failure evidence 指向相关\n机制时，才评估它是否适合作为比较对象，不预先赋予 default 或 designated challenger 角色。\n\n## 4. [CURRENT] 为什么不预选 MJPC/iLQR 为 default planner\n\nMJPC/iLQR 仍是强 comparator：它使用 full-body MuJoCo dynamics、可修改 task/residual/cost，\n且能支持可解释的 gradient-based whole-body control comparison。这些优点保留。\n\n但 physics/evaluation substrate 和 planner family 是不同决策。预先锁定 iLQR 会把问题\n偏向 gradient-based optimization，并可能裁掉 sampling/search、learned controller 或\ncontact-mode 方法本来应该解释的 failure。现阶段保留 controller-family 选择空间：\n\n- gradient family：MJPC/iLQR 等；\n- sampling/search family：Predictive Sampling/CEM、DIAL/MPPI 等；\n- learning family：公开 RL checkpoint 与按需 learned prior；\n- contact-implicit/hybrid：仅在 contact sequence/timing/mode search 成为问题时。\n\n公平比较优先共享 physical model、initial state、command、scene、terminal metrics 和\nsuccess semantics；controller 内部 cost、information condition 与优化方式不同则显式\n记录。目标是定位 failure mechanism，不是选择永久唯一 controller。\n\n## 5. [CURRENT] RL baseline 的研究作用\n\n公开 Go2 RL policy 不只是“另一个 controller”，而是能力对照：\n- 测哪些 terrain 已能轻松解决；\n- 暴露 learning policy 与 predictive-control 的共同 failure；\n- 可作为 teacher/prior/proposal；\n- 防止围绕弱 baseline 造假问题。\n\n第一阶段优先使用公开 checkpoint，不从头训练。\n\n2026-09-23 已建立冻结 1 m/s 源条件平地参考；2026-09-24 完成完整 shared-transfer\n两次正式 PASS，并进一步完成 #189 九例正式 capability map。5 cm、10 cm、5/15/5 cm\nrepeated-step 的 PASS 结论保留；`low_friction_cross` 仅是原 v1 scene 上几何/task-goal\nPASS，不是低摩擦 robustness evidence；half-speed、reverse、lateral、yaw 仍为冻结\n门槛下的 PERFORMANCE_FAIL。yaw 的更正指标为 mean body-local qvel-z 0.1038956543\nrad/s、MAE 0.3961043457 rad/s，仍超过 0.1 tolerance。这个 bounded 结果不足以宣布\nterrain 天花板、跨控制器共同瓶颈或论文题。详见 PROJECT_RECORD 与\n[语义勘误](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)。\n\n## 6. [CANDIDATE LEDGER]\n\n| 候选 | 状态 | 核心原因 / 重启条件 |\n|---|---|---|\n| learned proposal → WBMPC | DOWNRANK | hybrid / learned prior 拥挤；需明确 unresolved interface |\n| decision-relevant active sensing | HOLD | active probing/VoI 不新；需可信 contact-uncertainty gap |\n| warm-start/contact basin | DOWNRANK | literature 成熟；需实证成为 terrain WBMPC 核心瓶颈 |\n| risk / lazy verification | DOWNRANK | TAMP/risk calibration 已覆盖；需 legged-specific structure |\n| long-horizon depth | DOWNRANK | 太通用；需 contact-search 专属效应 |\n| state/cache abstraction | DOWNRANK | 更像 implementation defect；修复后再谈一般问题 |\n| L9 Preview | HOLD / RE-AUDIT | 可能是 reference/timing bug；需新 substrate 跨-controller复现 |\n| L10 / SEFR / FSEF | HOLD / RE-AUDIT | 与 retiming/planning/WBMPC 重叠；可能是旧 hierarchy 产物 |\n\n## 7. [CURRENT | GATE] Substrate Gate 0 对选题的作用\n\n当前先建立统一评测与 multi-controller failure map：\n\n1. 固定 MuJoCo physical model、scene/reset、command、metrics 与 success/safety semantics。\n2. #189 已完成第一张 RL map；low-friction 和 yaw 解释按 erratum 修正。\n3. 先审计成熟 Go2 whole-body control implementation、MJPC task 和 runner，复用已有闭环能力。\n4. 为选定的 controller families 编写独立对齐任务，并记录信息条件、controller cost/reward 与优化方式。\n5. 只有明确 failure structure 后才启动 sampling/search 或 contact-implicit diagnosis；需要大规模 rollout/learning 时再推进 MJX。\n\n值得进入研究筛选的 failure 必须稳定可复现，且不是 deployment/tuning/benchmark\nartifact；它应有 falsifier、机制假设、资源边界和近期 continue/stop evidence。跨强\nbaseline failure 或清晰的 controller-specific contrast 都可能有价值。全部通过则从\n候选中删除。\n\n## 8. [TRACEABILITY] 关键质疑\n\n- “baseline 干净了，但路线本身会不会不好？” → 架构审计。\n- “baseline 不是没做越障吗？” → 修正事实边界。\n- “为什么是 trot / 5 cm？” → capability frontier。\n- “老师任务和论文题不能拆” → dual-goal。\n- “为什么不能推倒重来？” → whole-body substrate reset。\n- “DIAL 太重且仓库不活跃” → 撤销 DIAL default；本轮架构决策进一步取消预设的单一 challenger 角色。\n- “这领域发展这么快，别拿 2018 当当下” → 选题必须以近两年强工作重新审计。\n\n## 9. [CURRENT | NEXT AUDIT]\n\n#189 的 RL failure map 不重跑。下一步先审计成熟 Go2 whole-body control implementation\n能提供哪些 pinned controller、task/cost、runner 和可复用 gait/contact infrastructure，\n避免从零实现已有闭环方案。之后再定义 MuJoCo 上的对齐比较：1 m/s flat reference、\ncommand-space probes、5 cm/10 cm/repeated-step anchors；若需要 low-friction case，须使用\n语义修正后的 v2 fixture，并由新任务前瞻授权，不能接续 #189 的 sealed result。\n\n随后让 learning、gradient MPC、sampling/search 按证据进入 benchmark。判读要区分\ncontroller-specific issue、共同 failure、成熟方案/tuning 和 deployment artifact。只有\n可证伪且不能由已有方法直接覆盖的机制才进入新方法任务；此处不授予 live run 或新\nscientific attempt。\n\n## 10. [2026-09-22 | GOVERNANCE]\n\n从 2026-09-22 起，本文件与 `docs/PROJECT_RECORD.md` 由 GitHub 统一维护。Library 不再保存正文副本。\n\n## 11. 维护协议\n\n每轮尽量恢复：\n`TRIGGER → EVIDENCE → HYPOTHESIS → GATE → VERDICT → CARRY-FORWARD`\n\n规则：\n- 没搜到前作 ≠ novelty；\n- 摘要/全文/源码/真实运行证据等级不能混写；\n- current candidate status 只维护一个 canonical ledger；\n- 路线变化先改 CURRENT，再补历史；\n- 执行状态变化同步 `docs/PROJECT_RECORD.md`；\n- 普通工程流水不写。\n","path":"docs/TOPIC_AUDIT.md","sha256":"e5640e1c8c3d651fe021ea033e5eecabd3ab4d02c1db0b685224bb7aa41f19b3","truncated":false},{"chars":2290,"excerpt":"# ADR-0001: MuJoCo/MJX evaluation substrate and controller ownership\n\n- **Date:** 2026-09-28\n- **Status:** Accepted as the project architecture direction; implementation is\n  partial.\n- **Decision served:** establish a reusable evaluation foundation that lets\n  evidence, rather than an assumed controller default, identify which\n  locomotion failures merit new mechanisms.\n\n## Decision\n\nMuJoCo is the canonical evaluation physics for the current project. MuJoCo/MJX\nis the intended scalable substrate direction; the shared interfaces and\nscalable execution path are not yet fully implemented.\n\nGo2 is the first testbed, not the project identity. MJPC/iLQR is a strong\ngradient-based comparator, not a privileged default or source of truth.\nSampling/search, learning, and contact-implicit methods remain available when\nthe task and observed failure structure justify them.\n\nReuse mature simulator, solver, and controller infrastructure where it fits.\nScientific ownership resides in task, information, timing, and intervention\ndefinitions; diagnostics; fair comparisons; and any new mechanism that the\nevidence shows is needed. Reimplementing a mature controller from scratch is\nnot a contribution by itself.\n\n## Planned boundary\n\nThe next minimal contract direction is `TaskSpec`, `ScenarioSpec`,\n`InformationSpec`, `TimingSpec`, `ControllerAdapter`, and a canonical\n`Evaluator` / physical-oracle boundary. The evaluator owns common physical\nexecution and canonical outcome evidence; the information contract states what\neach controller may observe. This is a direction for later implementation,\nnot a universal SDK or a claim that a generic multi-controller platform\nalready exists.\n\n## Current and verified state\n\nThe repository has task-specific MuJoCo Go2 assets, a reviewed schema-2 public\nRL execution/analyzer/verifier path, and static MJPC/iLQG admission utilities.\nThese are executable components, not yet the shared multi-controller contract\nabove. In particular, static MJPC admission is not a closed-loop locomotion\ncomparison.\n\nThe verified #189 conclusions and their semantic corrections are recorded in\nthe [versioned erratum](../validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md).\nThey do not yet establish a cross-controller bottleneck or a paper topic.\n","path":"docs/adr/ADR-0001-mujoco-mjx-evaluation-substrate.md","sha256":"5d9a573cd596acd22c580389c14425a22a8ab85602345ea2068a2001df0ce761","truncated":false},{"chars":885,"excerpt":"{\n  \"schema\": 1,\n  \"mujoco\": \"3.3.6\",\n  \"torch\": \"2.6.0+cpu\",\n  \"mjpc\": {\n    \"repository\": \"https://github.com/johnzhang3/mujoco_mpc.git\",\n    \"commit\": \"e00c47a5adb9856af2e0f24231bb3a60d5be23c4\",\n    \"upstream_mujoco_commit\": \"088079eff0450e32b98ee743141780ed68307506\",\n    \"integration_mujoco_tag\": \"3.3.6\"\n  },\n  \"rl\": {\n    \"repository\": \"https://github.com/wty-yy/go2_rl_gym.git\",\n    \"commit\": \"30e74dc507bec7a642a8c98be26081f2c6f0822d\",\n    \"checkpoint\": \"deploy/pre_train/go2/go2_moe_cts_high_slope_thre_164k_0.6715.pt\",\n    \"sha256\": \"9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d\",\n    \"git_blob_sha1\": \"db065febf09056839b04a60ead053c9382705597\",\n    \"bytes\": 5208824,\n    \"deployment\": \"deploy/deploy_mujoco/deploy_go2.py\",\n    \"configuration\": \"deploy/deploy_mujoco/configs/go2.yaml\"\n  },\n  \"abseil_commit\": \"fb3621f4f897824c0dbe0615fa94543df6192f30\"\n}\n","path":"tools/substrate/sources.lock.json","sha256":"e9c76e69061df78cc8bcbe04fb48b8a81e641161fba9163f06e721a319790bb0","truncated":false},{"chars":2505,"excerpt":"cmake_minimum_required(VERSION 3.20)\nproject(go2_substrate_admission LANGUAGES C CXX)\nif(NOT DEFINED MJPC_SOURCE_DIR)\n  message(FATAL_ERROR \"Set MJPC_SOURCE_DIR to the pinned source checkout\")\nendif()\nfind_package(Git REQUIRED)\nexecute_process(COMMAND \"${GIT_EXECUTABLE}\" -C \"${MJPC_SOURCE_DIR}\" rev-parse HEAD\n  OUTPUT_VARIABLE MJPC_COMMIT OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)\nif(NOT MJPC_COMMIT STREQUAL \"e00c47a5adb9856af2e0f24231bb3a60d5be23c4\")\n  message(FATAL_ERROR \"MJPC source commit does not match sources.lock.json\")\nendif()\nset(CMAKE_EXPORT_COMPILE_COMMANDS ON)\nset(CMAKE_CXX_STANDARD 20)\nset(CMAKE_CXX_STANDARD_REQUIRED ON)\nset(MUJOCO_ROOT \"$ENV{HOME}/.mujoco/mujoco-3.3.6\" CACHE PATH \"MuJoCo 3.3.6 distribution\")\nfind_path(MUJOCO_INCLUDE_DIR mujoco/mujoco.h PATHS \"${MUJOCO_ROOT}/include\" NO_DEFAULT_PATH REQUIRED)\nfind_library(MUJOCO_LIBRARY mujoco PATHS \"${MUJOCO_ROOT}/lib\" NO_DEFAULT_PATH REQUIRED)\nfind_package(Threads REQUIRED)\ninclude(FetchContent)\nset(ABSL_PROPAGATE_CXX_STD ON CACHE BOOL \"\" FORCE)\nset(ABSL_BUILD_TESTING OFF CACHE BOOL \"\" FORCE)\nFetchContent_Declare(abseil\n  GIT_REPOSITORY https://github.com/abseil/abseil-cpp.git\n  GIT_TAG fb3621f4f897824c0dbe0615fa94543df6192f30)\nFetchContent_MakeAvailable(abseil)\nexecute_process(COMMAND \"${GIT_EXECUTABLE}\" -C \"${abseil_SOURCE_DIR}\" rev-parse HEAD\n  OUTPUT_VARIABLE ABSL_COMMIT OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)\nif(NOT ABSL_COMMIT STREQUAL \"fb3621f4f897824c0dbe0615fa94543df6192f30\")\n  message(FATAL_ERROR \"Abseil source commit differs from the pinned dependency\")\nendif()\n# Build only the unchanged upstream optimizer. Built-in task assets, GUI,\n# estimators, and unrelated robot repositories are not dependencies of this tool.\nset(MJPC_FILES task.cc norm.cc utilities.cc trajectory.cc threadpool.cc\n  states/state.cc planners/planner.cc planners/model_derivatives.cc\n  planners/cost_derivatives.cc planners/ilqg/backward_pass.cc\n  planners/ilqg/policy.cc planners/ilqg/planner.cc)\nlist(TRANSFORM MJPC_FILES PREPEND \"${MJPC_SOURCE_DIR}/mjpc/\")\nadd_library(go2_mjpc_core STATIC ${MJPC_FILES})\ntarget_include_directories(go2_mjpc_core PUBLIC \"${MJPC_SOURCE_DIR}\" \"${MUJOCO_INCLUDE_DIR}\")\ntarget_link_libraries(go2_mjpc_core PUBLIC \"${MUJOCO_LIBRARY}\" Threads::Threads\n  absl::base absl::any_invocable absl::check absl::flat_hash_map absl::log\n  absl::random_random absl::span)\nadd_executable(go2_mjpc_admit admit.cc)\ntarget_link_libraries(go2_mjpc_admit PRIVATE go2_mjpc_core)\n","path":"tools/substrate/native/CMakeLists.txt","sha256":"1017f22701e82576a1f052137fc36ed75810489c54d5c3a063ef0491445bfa3b","truncated":false},{"chars":4092,"excerpt":"// Offline iLQG admission on the unchanged shared Go2 physical model.\n// No external plant loop, DDS, UI, or capability evaluator.\n#include <cmath>\n#include <iomanip>\n#include <iostream>\n#include <memory>\n#include <stdexcept>\n#include <mujoco/mujoco.h>\n#include \"mjpc/planners/ilqg/planner.h\"\n#include \"mjpc/task.h\"\n#include \"mjpc/threadpool.h\"\n\nclass Go2Admission final : public mjpc::Task {\n public:\n  std::string Name() const override { return \"Go2 offline admission\"; }\n  std::string XmlPath() const override { return \"\"; }\n  class ResidualImpl final : public mjpc::BaseResidualFn {\n   public:\n    explicit ResidualImpl(const Go2Admission* t) : BaseResidualFn(t) {}\n    void Residual(const mjModel* m, const mjData* d, double* r) const override {\n      int n = 0;\n      r[n++] = d->qpos[2] - 0.27;\n      // Quaternion-derived body upright axis versus world vertical.\n      const double w=d->qpos[3],x=d->qpos[4],y=d->qpos[5],z=d->qpos[6];\n      r[n++] = 2*(x*z+w*y); r[n++] = 2*(y*z-w*x);\n      r[n++] = 1-2*(x*x+y*y)-1;\n      for(int i=0;i<3;++i) r[n++] = d->qvel[i];\n      for(int i=7;i<m->nq;++i) r[n++] = d->qpos[i]-m->key_qpos[i];\n      for(int i=0;i<m->nu;++i) r[n++] = d->ctrl[i];\n    }\n  };\n  Go2Admission() : residual_(this) {}\n protected:\n  std::unique_ptr<mjpc::ResidualFn> ResidualLocked() const override {\n    return std::make_unique<ResidualImpl>(this);\n  }\n  ResidualImpl* InternalResidual() override { return &residual_; }\n private:\n  ResidualImpl residual_;\n};\n\nstatic Go2Admission* active_task = nullptr;\nstatic void Sensor(const mjModel* model,mjData* data,int stage) {\n  if(stage==mjSTAGE_ACC && active_task)\n    active_task->Residual(model,data,data->sensordata);\n}\nint main(int argc,char** argv) {\n  if(argc!=2) { std::cerr<<\"usage: go2_mjpc_admit TASK_XML\\n\"; return 2; }\n  if(mj_version()!=336) { std::cerr<<\"requires MuJoCo 3.3.6\\n\"; return 2; }\n  char error[1024]={};\n  std::unique_ptr<mjModel,decltype(&mj_deleteModel)> m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);\n  if(!m) { std::cerr<<error<<\"\\n\"; return 2; }\n  if(m->nu!=12 || m->nq!=19 || m->nv!=18 || m->nkey<1 ||\n      mj_name2id(m.get(),mjOBJ_KEY,\"home\")!=0 || std::abs(m->opt.timestep-.002)>1e-12)\n    return 2;\n  std::unique_ptr<mjData,decltype(&mj_deleteData)> d(mj_makeData(m.get()),mj_deleteData);\n  mj_resetDataKeyframe(m.get(),d.get(),0);\n  const int dimensions[5]={1,3,3,12,12};\n  if(m->nsensor<5 || m->nuser_sensor<4) return 2;\n  for(int i=0;i<5;++i)\n    if(m->sensor_type[i]!=mjSENS_USER || m->sensor_dim[i]!=dimensions[i]) return 2;\n  Go2Admission task;\n  task.Reset(m.get());\n  active_task=&task; mjcb_sensor=Sensor;\n  mj_forward(m.get(),d.get());\n  mjpc::State state; state.Allocate(m.get()); state.Set(m.get(),d.get());\n  mjpc::iLQGPlanner planner;\n  planner.Initialize(m.get(),task); planner.Allocate(); planner.Reset(21);\n  planner.SetState(state);\n  mjpc::ThreadPool pool(2);\n  planner.NominalTrajectory(21,pool);\n  const double initial_cost=planner.candidate_policy[0].trajectory.total_return;\n  planner.OptimizePolicy(21,pool);\n  double action[12]={};\n  planner.ActionFromPolicy(action,nullptr,d->time,false);\n  const double cost=planner.BestTrajectory()->total_return;\n  bool finite=std::isfinite(cost) && std::isfinite(initial_cost) &&\n      !planner.BestTrajectory()->failure && planner.BestTrajectory()->horizon==21;\n  for(int i=0;i<12;++i) finite &= std::isfinite(action[i]) &&\n      action[i]>=m->actuator_ctrlrange[2*i]-1e-9 && action[i]<=m->actuator_ctrlrange[2*i+1]+1e-9;\n  std::cout<<std::setprecision(17)<<\"{\\\"backend\\\":\\\"MJPC iLQG\\\",\\\"scope\\\":\\\"offline_static_state\\\",\\\"mujoco\\\":\\\"\"<<mj_versionString()\n    <<\"\\\",\\\"planner\\\":\"<<2<<\",\\\"plant_time_s\\\":\"<<d->time\n    <<\",\\\"initial_cost\\\":\"<<initial_cost<<\",\\\"rollout_failure\\\":\"<<(planner.BestTrajectory()->failure?\"true\":\"false\")<<\",\\\"horizon_steps\\\":21,\\\"cost\\\":\"<<cost<<\",\\\"finite_bounded\\\":\"<<(finite?\"true\":\"false\")<<\",\\\"torque\\\":[\";\n  for(int i=0;i<12;++i) std::cout<<(i?\",\":\"\")<<action[i];\n  std::cout<<\"]}\\n\";\n  mjcb_sensor=nullptr; active_task=nullptr;\n  return finite && d->time==0 ? 0 : 1;\n}\n","path":"tools/substrate/native/admit.cc","sha256":"7da12361aded30936888c3a44b555a0b5adfaae09f8cfde495f3051e8a491452","truncated":false},{"chars":11343,"excerpt":"# Go2 pre-experiment foundation\n\nThis is a source-bound offline engineering foundation, not a locomotion result.\nAll commands below run in the canonical native WSL checkout. They do not launch\na simulator/controller pair, hardware, training, or a terrain capability sweep.\n\n## Reproduce\n\nLinux x86_64 / CPython 3.10, CMake 3.20+, Ninja, GCC with C++20, git, existing\nMuJoCo 3.3.6 native distribution, Unitree SDK and Eigen are required. The Python\nruntime is isolated from user/system site packages; all direct/transitive wheel\nversions and download hashes are locked in `requirements-linux-py310.lock`.\n\n```sh\npython3 -m tools.substrate.bootstrap --install --build\n.substrate/venv-reliable/bin/python -m tools.substrate.qualify \\\n  --output _runs/substrate_qualification/fresh_01\n.substrate/venv-reliable/bin/python -m tools.substrate.verify \\\n  _runs/substrate_qualification/fresh_01\n```\n\nEvery output must be new. Qualify holds `/tmp/go2_mujoco_experiment.lock` for the\nwhole process, rebuilds the controller in `.substrate/controller-reliable`, runs\nall registered CTests, substrate, preflight and repository/dispatcher tests,\nchecks hygiene and diff, then runs actual RL/MJPC offline admission. A clean HEAD\nis required by default. `--development` explicitly records a dirty engineering\niteration; it cannot stand for clean-head final qualification. The native\noptimizer build is separately sealed by bootstrap; stale inputs are rejected.\n\nTo run only admission after a successful build:\n\n```sh\n.substrate/venv-reliable/bin/python -m tools.substrate.admit \\\n  --output _runs/substrate_admission/fresh_01 \\\n  --checkpoint .substrate/rl/policy.pt \\\n  --mjpc-binary .substrate/headless-reliable/go2_mjpc_admit\n```\n\nBootstrap preserves the earlier `.substrate/venv` and `.substrate/headless-build`\ncaches. It creates new isolated/runtime build directories rather than silently\nreusing an environment that inherited host packages. Existing raw directories\nare never cleaned or reused. A failed engineering invocation remains evidence.\n\n## Identity and evidence\n\nNative admission verifies the binary against a build identity covering actual\nMJPC/Abseil commits and tracked bytes, local native source, compiler binary,\nMuJoCo headers/library, CMake cache, Ninja rules and compile command database.\nThe CMake target builds unchanged upstream iLQG sources directly, excluding demo\nmodels and GUI dependencies. MuJoCo Python/native libraries must match bytewise.\n\nRuntime verification checks installed versions and installed payloads against\nwheel RECORD hashes, including source and shared libraries. Generated `.pyc`\nand `.pyo` compilation caches are excluded explicitly: pip may regenerate them\nfor the local installation path, and NumPy's wheel can contain duplicate\nhashed/unhashed cache rows. Their underlying source remains verified.\n\nEach run snapshots all registered scene/include/mesh files before model loading.\nThe physical fingerprint includes reset keyframes as well as physical arrays\nand solver options. Unsupported plugin/attached-model/multi-compiler/external\nasset conventions fail closed rather than receiving an incomplete manifest.\n\n`started.json` is written first. Logs stream to exclusive files, including\npartial stdout/stderr on timeout. The whole child process group is terminated\non failure/timeout; SIGTERM and keyboard interruption seal FAILED output.\nSIGKILL can leave only an incomplete marker; such a directory cannot verify as\nadmitted. `manifest.json` is written last and file data is fsynced. Independent\nverification rejects changed bytes, missing/extra files, symlinks, incomplete\nor failed runs. These checks provide reproducibility/integrity, not an external\ncryptographic attestation against a user able to rewrite the whole environment.\n\n## Model, action, timing and state\n\nActuator order is FR/FL/RR/RL; policy order is FL/FR/RL/RR. Names, not positional\nassumptions, determine the mapping. Input and command packets own immutable\ncopies. Strings, booleans, nonfinite arrays and invalid quaternion inputs are\nrejected. The shared action exposes feedforward, position/velocity targets and\ndeclared gains. Resolution records PD, total pre-clamp torque and motor ctrl.\nHip/thigh bounds are +/-40 Nm; calf bounds +/-45.43 Nm. Unsupported secondary\nforce limits/transmissions are rejected; the legacy 35 Nm envelope limits\nfeedforward, not total plant torque.\n\nThe public CTS checkpoint uses a 45-dimensional proprioceptive observation,\n50 Hz update declaration, kp=20, kd=0.5 and action scale=0.25. Its verified bytes\nare retained in memory so reset cannot silently load changed weights. Separate\ninstances have separate history; a failed inference requires explicit reset.\nAdmission replays 12 nontrivial synthetic packets twice after reset. This is\nnot a physics trajectory or a claim of achieved 50 Hz real-time control.\n\n`ControlClock` represents 50 Hz at 500 Hz as exactly one update per ","path":"tools/substrate/README.md","sha256":"5156aa3c317973eca5db39350b6f41ae6035c57fc88a93c604b8a4258ec7c6a7","truncated":true}],"project_id":"go2-mujoco-control","project_profile_canonical_sha256":"6148b57f23e8d0f297143dd661125abdc981e4b210ca8e6850a2b3f767941ad2","project_profile_raw_sha256":"022c7317a228337555d344b6894ba24fe4c628fd0db7fbbcaca8aeaf4a5fbcaa","repository":"cwchewang/go2-mujoco-control","schema_version":1}
PRAXIS_CONTEXT_PACK -->
