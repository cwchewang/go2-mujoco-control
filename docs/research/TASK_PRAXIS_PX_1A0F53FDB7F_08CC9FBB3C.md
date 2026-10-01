# Praxis Task px_1a0f53fdb7f_08cc9fbb3c

Mode: `offline`
Project: `go2-mujoco-control`
Repository: `cwchewang/go2-mujoco-control`
Approval boundary: `none`

## Objective

Independently review PR #205 at exact head 86f3e65814b95ea69da983b8633e4d23578a4ad5 for correctness and scientific-interface integrity. Focus on the new PositionPDActuatorSpec, ControllerAdapter protocol, PositionTargetControllerAdapter, position_pd_actuator_spec extractor, tests, and ADR. Identify any bug, silent semantic mismatch, evidence-serialization issue, ordering issue, MuJoCo actuator-model mistake, or overclaim. Do not modify code.

## Context paths

- tools/substrate/contracts.py
- tools/substrate/model.py
- tools/substrate/test_substrate.py
- tools/substrate/test_native_boundary.py
- docs/adr/ADR-0001-mujoco-mjx-evaluation-substrate.md

## Instructions

- Review exact PR head only.
- Check MuJoCo affine actuator semantics against force = gain*ctrl + bias0 + bias1*length + bias2*velocity under unit joint transmission.
- Check joint-order mapping and clipping order.
- Check diagnostics are JSON-safe.
- Check tests actually falsify the missing-biastype bug.
- Separate blocking defects from optional follow-ups.

## Constraints

- Read-only review.
- No experiment.
- No source mutation.
- Do not approve based on prior chat claims; inspect code.

## Resource budget

```json
{
  "cpu_slots": 1,
  "gpu_count": 0,
  "memory_gb": null,
  "wall_time_seconds": 300
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
  "reason": null,
  "required_before": "none"
}
```

## Required evidence

- review verdict
- blocking findings
- nonblocking follow-ups
- exact reviewed commit

## Stop rule

Stop after review.

## Closeout schema

- commit
- verdict
- blocking_findings
- nonblocking_findings
- evidence

## Frozen TaskSpec

The following machine-readable block is the canonical task request.

```json
{
  "allowed_mutations": [],
  "approval_policy": {
    "reason": null,
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
    "commit",
    "verdict",
    "blocking_findings",
    "nonblocking_findings",
    "evidence"
  ],
  "constraints": [
    "Read-only review.",
    "No experiment.",
    "No source mutation.",
    "Do not approve based on prior chat claims; inspect code."
  ],
  "context_paths": [
    "tools/substrate/contracts.py",
    "tools/substrate/model.py",
    "tools/substrate/test_substrate.py",
    "tools/substrate/test_native_boundary.py",
    "docs/adr/ADR-0001-mujoco-mjx-evaluation-substrate.md"
  ],
  "frozen_parameters": {},
  "instructions": [
    "Review exact PR head only.",
    "Check MuJoCo affine actuator semantics against force = gain*ctrl + bias0 + bias1*length + bias2*velocity under unit joint transmission.",
    "Check joint-order mapping and clipping order.",
    "Check diagnostics are JSON-safe.",
    "Check tests actually falsify the missing-biastype bug.",
    "Separate blocking defects from optional follow-ups."
  ],
  "mode": "offline",
  "objective": "Independently review PR #205 at exact head 86f3e65814b95ea69da983b8633e4d23578a4ad5 for correctness and scientific-interface integrity. Focus on the new PositionPDActuatorSpec, ControllerAdapter protocol, PositionTargetControllerAdapter, position_pd_actuator_spec extractor, tests, and ADR. Identify any bug, silent semantic mismatch, evidence-serialization issue, ordering issue, MuJoCo actuator-model mistake, or overclaim. Do not modify code.",
  "project": {
    "profile_path": ".atlas/project.json",
    "project_id": "go2-mujoco-control",
    "repository": "cwchewang/go2-mujoco-control"
  },
  "required_evidence": [
    "review verdict",
    "blocking findings",
    "nonblocking follow-ups",
    "exact reviewed commit"
  ],
  "resources": {
    "cpu_slots": 1,
    "gpu_count": 0,
    "memory_gb": null,
    "wall_time_seconds": 300
  },
  "schema_version": 1,
  "stop_rule": "Stop after review."
}
```

<!-- PRAXIS_TASK_SPEC
{"allowed_mutations":[],"approval_policy":{"reason":null,"required_before":"none"},"attempt_policy":{"max_scientific_attempts":0,"retry_preflight":true,"scientific_boundary":null},"capability":null,"capability_request":null,"closeout_schema":["commit","verdict","blocking_findings","nonblocking_findings","evidence"],"constraints":["Read-only review.","No experiment.","No source mutation.","Do not approve based on prior chat claims; inspect code."],"context_paths":["tools/substrate/contracts.py","tools/substrate/model.py","tools/substrate/test_substrate.py","tools/substrate/test_native_boundary.py","docs/adr/ADR-0001-mujoco-mjx-evaluation-substrate.md"],"frozen_parameters":{},"instructions":["Review exact PR head only.","Check MuJoCo affine actuator semantics against force = gain*ctrl + bias0 + bias1*length + bias2*velocity under unit joint transmission.","Check joint-order mapping and clipping order.","Check diagnostics are JSON-safe.","Check tests actually falsify the missing-biastype bug.","Separate blocking defects from optional follow-ups."],"mode":"offline","objective":"Independently review PR #205 at exact head 86f3e65814b95ea69da983b8633e4d23578a4ad5 for correctness and scientific-interface integrity. Focus on the new PositionPDActuatorSpec, ControllerAdapter protocol, PositionTargetControllerAdapter, position_pd_actuator_spec extractor, tests, and ADR. Identify any bug, silent semantic mismatch, evidence-serialization issue, ordering issue, MuJoCo actuator-model mistake, or overclaim. Do not modify code.","project":{"profile_path":".atlas/project.json","project_id":"go2-mujoco-control","repository":"cwchewang/go2-mujoco-control"},"required_evidence":["review verdict","blocking findings","nonblocking follow-ups","exact reviewed commit"],"resources":{"cpu_slots":1,"gpu_count":0,"memory_gb":null,"wall_time_seconds":300},"schema_version":1,"stop_rule":"Stop after review."}
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

### Instruction: `tools/substrate/contracts.py`

SHA-256: `6eb689775fd77273f3de9f319157c41fa227a6523ba46c802dff3cdfa6ba2b44`

```text
"""Named boundaries; no simulator handles are exposed to proprioceptive policies."""

from dataclasses import dataclass
import numpy as np

POLICY_JOINTS = tuple(
    f"{leg}_{joint}_joint"
    for leg in ("FL", "FR", "RL", "RR")
    for joint in ("hip", "thigh", "calf")
)
MOTOR_JOINTS = tuple(
    f"{leg}_{joint}_joint"
    for leg in ("FR", "FL", "RR", "RL")
    for joint in ("hip", "thigh", "calf")
)


def vector(value, size, name):
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf":
        raise ValueError(f"{name}: expected numeric values, not booleans/strings")
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f"{name}: expected {size} finite values")
    return result.copy()


def reorder(values, source, target):
    source, target = tuple(source), tuple(target)
    if any(not isinstance(name, str) or not name for name in source + target):
        raise ValueError("joint names must be nonempty strings")
    if (
        len(set(source)) != len(source)
        or len(set(target)) != len(target)
        or set(source) != set(target)
    ):
        raise ValueError("joint names must be unique and describe the same joints")
    a = vector(values, len(source), "joint vector")
    return a[[source.index(name) for name in target]]


@dataclass(frozen=True)
class Proprioception:
    # MuJoCo free-joint rotational velocity is in the local body frame.
    joint_names: tuple
    position: np.ndarray
    velocity: np.ndarray
    quaternion_wxyz: np.ndarray
    angular_velocity_body: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "joint_names", tuple(self.joint_names))
        for name, size in (
            ("position", 12),
            ("velocity", 12),
            ("quaternion_wxyz", 4),
            ("angular_velocity_body", 3),
        ):
            value = vector(getattr(self, name), size, name)
            object.__setattr__(
                self, name, np.frombuffer(value.tobytes(), dtype=np.float64)
            )

    def validate(self):
        reorder(self.position, self.joint_names, POLICY_JOINTS)
        vector(self.velocity, 12, "joint velocity")
        q = vector(self.quaternion_wxyz, 4, "quaternion")
        if abs(np.linalg.norm(q) - 1) > 1e-6:
            raise ValueError("quaternion must be normalized")
        vector(self.angular_velocity_body, 3, "angular velocity")


@dataclass(frozen=True)
class TorqueCommand:
    joint_names: tuple
    feedforward: np.ndarray
    position_target: np.ndarray
    velocity_target: np.ndarray
    kp: np.ndarray
    kd: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "joint_names", tuple(self.joint_names))
        for name in ("feedforward", "position_target", "velocity_target", "kp", "kd"):
            value = vector(getattr(self, name), 12, name)
            object.__setattr__(
                self, name, np.frombuffer(value.tobytes(), dtype=np.float64)
            )

    def resolve(self, observation, lower, upper, target_names):
        observation.validate()
        ff, qref, dqref, kp, kd = [
            reorder(v, self.joint_names, target_names)
            for v in (
                self.feedforward,
                self.position_target,
                self.velocity_target,
                self.kp,
                self.kd,
            )
        ]
        if (kp < 0).any() or (kd < 0).any():
            raise ValueError("negative PD gain")
        q = reorder(observation.position, observation.joint_names, target_names)
        dq = reorder(observation.velocity, observation.joint_names, target_names)
        lo, hi = vector(lower, 12, "lower"), vector(upper, 12, "upper")
        if (lo >= hi).any():
            raise ValueError("invalid actuator range")
        pd = kp * (qref - q) + kd * (dqref - dq)
        total = vector(ff + pd, 12, "total torque")
        return {
            "feedforward": ff,
            "pd": pd,
            "total_unclipped": total,
            "ctrl": np.clip(total, lo, hi),
            "saturated": (total < lo) | (total > hi),
        }

```

### Instruction: `tools/substrate/model.py`

SHA-256: `3dfd63472e55bb9f89cde1975418a5225ad5a94049b6ef001e63d8ac0c130dbb`

```text
"""Conservative local MJCF dependency closure and compiled physical fingerprint."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np


from .integrity import digest


def dependency_manifest(scene, repository):
    root = Path(repository).resolve()
    scene = Path(scene).resolve()
    files, active = {}, set()
    compilers = []

    def confined(path):
        p = path.resolve()
        if not p.is_relative_to(root) or not p.is_file():
            raise ValueError(f"missing or out-of-root dependency: {p}")
        return p

    def visit(path, meshdir=None, texturedir=None):
        path = confined(path)
        if path in active:
            raise ValueError("cyclic MJCF include")
        active.add(path)
        tree = ET.parse(path).getroot()
        files[str(path.relative_to(root))] = digest(path)
        compiler = tree.find("compiler")
        if compiler is not None:
            compilers.append(path)
            if len(compilers) > 1 or path.parent != scene.parent:
                raise ValueError(
                    "unsupported multi-compiler or nested compiler asset semantics"
                )
            if compiler.get("strippath") not in (None, "false"):
                raise ValueError("strippath is unsupported")
            assetdir = compiler.get("assetdir", "")
            meshdir = path.parent / compiler.get("meshdir", assetdir)
            texturedir = path.parent / compiler.get("texturedir", assetdir)
        for node in tree.iter():
            if node.tag in ("plugin", "attach", "model") or any(
                k.startswith("file") and k != "file" for k in node.attrib
            ):
                raise ValueError("unsupported external/model/plugin asset declaration")
            name = node.get("file")
            if not name:
                continue
            if node.tag == "include":
                visit(path.parent / name, meshdir, texturedir)
            else:
                if node.tag not in ("mesh", "texture", "hfield"):
                    raise ValueError("unsupported file-bearing asset: " + node.tag)
                base = (
                    meshdir
                    if node.tag == "mesh"
                    else texturedir
                    if node.tag == "texture"
                    else path.parent
                )
                asset = confined((base or path.parent) / name)
                files[str(asset.relative_to(root))] = digest(asset)
        active.remove(path)

    visit(scene)
    entries = dict(sorted(files.items()))
    return {
        "files": entries,
        "sha256": hashlib.sha256(
            json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def physical_fingerprint(model):
    # Sensor/custom/task metadata deliberately excluded. Physical arrays are included
    # by prefix, including mesh vertices and collision geometry, not only XML text.
    prefixes = (
        "body_",
        "jnt_",
        "dof_",
        "geom_",
        "mesh_",
        "hfield_",
        "pair_",
        "exclude_",
        "eq_",
        "tendon_",
        "wrap_",
        "actuator_",
        "key_",
    )
    arrays = {}
    for name in dir(model):
        if name.startswith(prefixes):
            value = getattr(model, name)
            if isinstance(value, np.ndarray):
                arrays[name] = {
                    "shape": list(value.shape),
                    "dtype": str(value.dtype),
                    "hash": hashlib.sha256(value.tobytes()).hexdigest(),
                }
    # Addresses affect mechanics too; sensor insertion must not perturb these.
    for name in ("jnt_qposadr", "jnt_dofadr", "actuator_trnid", "dof_parentid"):
        arrays[name] = np.asarray(getattr(model, name)).tolist()
    options = {}
    for name in dir(model.opt):
        if name.startswith("_"):
            continue
        value = getattr(model.opt, name)
        if isinstance(value, np.ndarray):
            options[name] = value.tolist()
        elif isinstance(value, (float, int)):
            options[name] = value
    payload = {
        "arrays": arrays,
        "options": options,
        "nq": model.nq,
        "nv": model.nv,
        "nu": model.nu,
        "qpos0": model.qpos0.tolist(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def joint_layout(model):
    import mujoco
    from .contracts import POLICY_JOINTS

    names, qpos, dof = [], [], []
    for actuator in range(model.nu):
        if (
            model.actuator_trntype[actuator] != mujoco.mjtTrn.mjTRN_JOINT
            or model.actuator_gaintype[actuator] != mujoco.mjtGain.mjGAIN_FIXED
            or model.actuator_biastype[actuator] != mujoco.mjtBias.mjBIAS_NONE
            or model.actuator_dyntype[actuator] != mujoco.mjtDyn.mjDYN_NONE
            or model.actuator_gainprm[actuator, 0] != 1
            or not np.array_equal(model.actuator_gear[actuator], [1, 0, 0, 0, 0, 0])
            or not model.actuator_ctrllimited[actuator]
            or model.actuator_forcelimited[actuator]
        ):
            raise ValueError(
                "shared substrate requires finite-range direct torque motors"
            )
        joint = int(model.actuator_trnid[actuator, 0])
        if (
            model.jnt_type[joint] != mujoco.mjtJoint.mjJNT_HINGE
            or model.jnt_actfrclimited[joint]
        ):
            raise ValueError("unsupported joint transmission or secondary force limit")
        names.append(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint))
        qpos.append(int(model.jnt_qposadr[joint]))
        dof.append(int(model.jnt_dofadr[joint]))
    if len(names) != 12 or len(set(names)) != 12 or set(names) != set(POLICY_JOINTS):
        raise ValueError("unexpected actuated joint set")
    return tuple(names), qpos, dof


def decorate_mjpc(scene, destination):
    # Absolute include preserves the existing model/assets. Usersensors precede
    # ordinary sensors as required by MJPC. No actuator, inertia or contact edits.
    root = ET.Element("mujoco", model="Go2 shared substrate offline admission")
    sensors = ET.SubElement(root, "sensor")
    for name, dim, weight in (
        ("height", 1, 10),
        ("upright", 3, 2),
        ("velocity", 3, 1),
        ("posture", 12, 0.1),
        ("effort", 12, 0.001),
    ):
        ET.SubElement(
            sensors, "user", name=name, dim=str(dim), user=f"0 {weight} 0 100"
        )
    ET.SubElement(root, "include", file=str(Path(scene).resolve()))
    # A wrapper stored outside the scene directory changes MJCF relative asset
    # resolution. Keep the Go2 mesh source explicit; physical hash must match.
    ET.SubElement(
        root, "compiler", meshdir=str(Path(scene).resolve().parent / "assets")
    )
    custom = ET.SubElement(root, "custom")
    for name, value in (
        ("agent_planner", "2"),
        ("agent_horizon", "0.04"),
        ("agent_timestep", "0.002"),
    ):
        ET.SubElement(custom, "numeric", name=name, data=value)
    ET.ElementTree(root).write(destination, encoding="unicode")

```

### Instruction: `tools/substrate/test_substrate.py`

SHA-256: `dace5f4e061962429a46684e5f65bac0fcc77ef57f7eb71b90d94019f8ab5d55`

```text
import tempfile
import unittest
from pathlib import Path
import numpy as np
from .contracts import (
    POLICY_JOINTS as P,
    MOTOR_JOINTS as M,
    Proprioception,
    TorqueCommand,
    reorder,
)
from .rl import DEFAULT, observation45
from .model import dependency_manifest
from .evidence import summarize_frames, validate_capture_contract


class Boundaries(unittest.TestCase):
    def obs(self):
        return Proprioception(
            P, DEFAULT.copy(), np.zeros(12), np.array([1.0, 0.0, 0.0, 0.0]), np.zeros(3)
        )

    def test_named_permutation_roundtrip(self):
        a = np.arange(12.0)
        np.testing.assert_array_equal(reorder(reorder(a, P, M), M, P), a)
        self.assertEqual(reorder(a, P, M)[0], 3)

    def test_duplicate_missing_nonfinite_rejected(self):
        for source, values in (
            (P[:-1] + (P[0],), np.zeros(12)),
            (P[:-1], np.zeros(11)),
            (P, np.full(12, np.nan)),
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                reorder(values, source, M)

    def test_torque_pd_sum_before_model_limit(self):
        o = self.obs()
        cmd = TorqueCommand(
            P,
            np.full(12, 30),
            DEFAULT.astype(np.float64) + 1,
            np.zeros(12),
            np.full(12, 20),
            np.full(12, 0.5),
        )
        r = cmd.resolve(o, np.full(12, -40), np.full(12, 40), M)
        np.testing.assert_array_equal(r["total_unclipped"], np.full(12, 50))
        np.testing.assert_array_equal(r["ctrl"], np.full(12, 40))
        self.assertTrue(r["saturated"].all())

    def test_invalid_gain_and_range(self):
        cmd = TorqueCommand(
            P, np.zeros(12), DEFAULT, np.zeros(12), np.full(12, -1), np.zeros(12)
        )
        with self.assertRaises(ValueError):
            cmd.resolve(self.obs(), np.full(12, -40), np.full(12, 40), M)
        cmd = TorqueCommand(
            P, np.zeros(12), DEFAULT, np.zeros(12), np.zeros(12), np.zeros(12)
        )
        with self.assertRaises(ValueError):
            cmd.resolve(self.obs(), np.ones(12), np.zeros(12), M)

    def test_policy_observation_golden(self):
        o = self.obs()
        o = Proprioception(
            M,
            reorder(o.position, P, M) + np.arange(12) / 10,
            reorder(np.arange(12), P, M),
            np.array([np.cos(0.2), np.sin(0.2), 0.0, 0.0]),
            np.array([1.0, 2.0, 3.0]),
        )
        actual = observation45(o, [0.2, -0.1, 0.3], np.arange(12) / 20)
        expected = np.concatenate(
            (
                [0.25, 0.5, 0.75],
                [0, -np.sin(0.4), -np.cos(0.4)],
                [0.4, -0.2, 0.075],
                reorder(o.position, M, P) - DEFAULT,
                np.arange(12) * 0.05,
                np.arange(12) / 20,
            )
        ).astype(np.float32)
        np.testing.assert_allclose(actual, expected, atol=1e-7)
        self.assertEqual(actual.shape, (45,))
        self.assertEqual(actual.dtype, np.float32)

    def test_policy_rejects_bad_quaternion_command(self):
        o = self.obs()
        with self.assertRaises(ValueError):
            observation45(o, [3, 0, 0], np.zeros(12))
        o = Proprioception(P, DEFAULT, np.zeros(12), np.zeros(4), np.zeros(3))
        with self.assertRaises(ValueError):
            observation45(o, [0, 0, 0], np.zeros(12))

    def test_asset_closure_detects_included_mesh_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            (p / "assets").mkdir()
            (p / "assets/a.obj").write_text("mesh one")
            (p / "robot.xml").write_text(
                '<mujoco><compiler meshdir="assets"/><asset><mesh file="a.obj"/></asset></mujoco>'
            )
            (p / "scene.xml").write_text('<mujoco><include file="robot.xml"/></mujoco>')
            a = dependency_manifest(p / "scene.xml", p)
            self.assertEqual(len(a["files"]), 3)
            (p / "assets/a.obj").write_text("mesh two")
            self.assertNotEqual(
                a["sha256"], dependency_manifest(p / "scene.xml", p)["sha256"]
            )

    def test_include_cycle_and_missing_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            f = p / "a.xml"
            for target in ("a.xml", "missing.xml", "../outside.xml"):
                f.write_text(f'<mujoco><include file="{target}"/></mujoco>')
                with self.assertRaises(ValueError):
                    dependency_manifest(f, p)

    def test_earliest_failure_preserved(self):
        rows = [
            dict(sequence=0, sim_time_s=0, failure="solver_nonfinite"),
            dict(sequence=1, sim_time_s=0.02, terminal_reason="task_incomplete"),
        ]
        r = summarize_frames(rows, 0.02)
        self.assertEqual(r["first_failure"]["reason"], "solver_nonfinite")
        self.assertEqual(r["terminal_reason"], "task_incomplete")
        self.assertFalse(r["task_complete"])

    def test_jump_traverse_vs_mandatory_support(self):
        rows = [dict(sequence=0, sim_time_s=0, task_complete=True, supports=[])]
        self.assertTrue(
            summarize_frames(rows, 0.02, "traverse", ["top"])["task_complete"]
        )
        self.assertFalse(
            summarize_frames(rows, 0.02, "mandatory_support", ["top"])["task_complete"]
        )

    def test_duplicate_or_gap_rejected(self):
        for seq, t in ((0, 0.02), (2, 0.02), (1, 0), (1, 0.04), (1, float("nan"))):
            rows = [dict(sequence=0, sim_time_s=0), dict(sequence=seq, sim_time_s=t)]
            with self.subTest(seq=seq, t=t), self.assertRaises(ValueError):
                summarize_frames(rows, 0.02)

    def test_unreviewed_capture_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unfrozen capture"):
            validate_capture_contract({})


if __name__ == "__main__":
    unittest.main()

```

### Instruction: `tools/substrate/test_native_boundary.py`

SHA-256: `40477510795bfe86bbe6c26324fa9044e811968c20628aeec3c2adf621b44b0a`

```text
"""Native model checks, run separately from dependency-light hosted CI."""

import tempfile
import unittest
from pathlib import Path
import mujoco
import numpy as np
from .contracts import MOTOR_JOINTS
from .model import physical_fingerprint, joint_layout, decorate_mjpc

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "unitree_robots/go2/phase2_flat.xml"


class NativeBoundary(unittest.TestCase):
    def test_named_joints_and_model_limits(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        names, qadr, vadr = joint_layout(model)
        self.assertEqual(names, MOTOR_JOINTS)
        self.assertEqual(qadr[:3], [10, 11, 12])
        self.assertEqual(vadr[:3], [9, 10, 11])
        np.testing.assert_allclose(model.actuator_ctrlrange[:3, 1], [40.0, 40.0, 45.43])

    def test_decorated_physics_identical(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "task.xml"
            decorate_mjpc(SCENE, f)
            decorated = mujoco.MjModel.from_xml_path(str(f))
            self.assertEqual(
                physical_fingerprint(model), physical_fingerprint(decorated)
            )
            self.assertEqual(
                int(decorated.sensor_type[0]), int(mujoco.mjtSensor.mjSENS_USER)
            )
            self.assertEqual(sum(decorated.sensor_dim[:5]), 31)

    def test_friction_or_actuator_drift_detected(self):
        model = mujoco.MjModel.from_xml_path(str(SCENE))
        original = physical_fingerprint(model)
        model.geom_friction[0, 0] *= 0.5
        self.assertNotEqual(original, physical_fingerprint(model))
        model.actuator_gainprm[0, 0] = 2
        with self.assertRaises(ValueError):
            joint_layout(model)
        model.actuator_gainprm[0, 0] = 1
        model.actuator_forcelimited[0] = True
        with self.assertRaises(ValueError):
            joint_layout(model)


if __name__ == "__main__":
    unittest.main()

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

<!-- PRAXIS_CONTEXT_PACK
{"default_branch":"main","default_branch_sha":"83b3833f53f66f404cf5f428b9648860adb88323","instructions":[{"chars":3844,"excerpt":"# Go2 repository rules\n\n`main` is the stable code line and long-term route. The active research\nfrontier may live on a separate `research/*` branch. This file contains\nrepository guardrails; it is not a scientific plan or current-status report.\n\n## Research handoff\n\nUse [OPERATING_GUIDE](docs/OPERATING_GUIDE.md) to turn the current objective into\na bounded task that a human or any model can execute. State the decision it\nserves before choosing a method, checkpoint, parameter or pass threshold.\nUpstream defaults are candidate choices, not validated research requirements.\nDo not silently invent missing scientific decisions; resolve the specific gap\nwhile continuing independent authorized work. Keep routine execution autonomous.\n\nBefore choosing research direction, read `docs/PROJECT_RECORD.md` and then `docs/TOPIC_AUDIT.md`. They are the repo-native canonical scientific state and topic audit. `CURRENT.md` remains the canonical execution-frontier pointer. Chat history, Memory, screenshots, and old Library copies cannot override these repo records.\n\n## Task discovery bootstrap\n\nAt session entry or when resuming a stale task, refresh the remote source of\ntruth once. Repeat when new upstream work could affect the task, not before\nevery small edit:\n\n1. run `git fetch origin --prune`;\n2. read `origin/main:CURRENT.md` (for example with\n   `git show origin/main:CURRENT.md`) to discover the active research branch;\n3. compare the local active branch/worktree with `origin/<active-branch>` and\n   fast-forward only when safe; never reset, discard, or delete local commits,\n   untracked files, or raw evidence to make it match;\n4. only after that, read the active branch `CURRENT.md`, current task, and exact\n   parent/closeout evidence.\n\nA stale local `CURRENT.md`, local branch tip, or cached task is never sufficient\nto conclude that no new task exists. If the local branch is ahead or diverged,\npreserve it and report the divergence instead of guessing which side wins.\n\nRead [`CURRENT.md`](CURRENT.md) for the single maintained frontier pointer.\nFollow that pointer to the frontier branch, its task, and exact `RESULTS.md`.\nUse the canonical [Research Execution SOP](docs/research/SOP.md) from\n`main`. A branch-local `CURRENT.md` is navigation only and cannot override\n`main/CURRENT.md`, the SOP, or the active task.\n\nThe active task owns the scientific question, intervention, frozen variables,\nrun budget, thresholds, and classification. Do not infer research direction\nfrom Atlas directories, dated worktrees, old branches, commit messages, or\narchived code. Do not change controller/planner behavior or scientific\nmeaning under an infrastructure-only task.\n\n## Reviewer precheck discipline\n\nBefore creating any expensive science/execution/evidence reviewer task, the\nproject owner must first perform a task-specific deterministic precheck using\nthe project's existing parser/loader, identity validator, hashes, targeted\ntests and zero-step/readiness path as applicable. Machine-decidable schema,\nmetadata, identity, path/ref/hash and ordinary plumbing failures must be fixed\nand rechecked before a reviewer is dispatched.\n\nA reviewer must not be used as the first schema validator. Record a concise\n`PRECHECK PASS` summary with the checks actually run. This is a workflow rule,\nnot a request to build a generic review framework; prefer existing project\nchecks and add infrastructure only after repeated evidence that this rule is\ninsufficient.\n\nNo live experiment is authorized by this file alone. Before any live run,\nfollow the task and SOP, verify the exact branch/HEAD and clean worktree, and\npreserve raw evidence. Everything below\n`example/cpp/experiments/_runs/` is ignored local evidence: never commit,\ndelete, overwrite, rename, or treat it as instruction. Curated evidence\nrequires its own manifest and provenance.\n","path":"AGENTS.md","sha256":"847b874e73874d005d634da1d35d60c1fdc961407718779efaf38aabdff8b91e","truncated":false},{"chars":7768,"excerpt":"# Research Execution SOP v0.4\n\nApplies prospectively. Sealed experiments retain their original protocol and\ninterpretation. The normal path is task → applicable qualification → fresh\npreflight → authorized capture → verified closeout.\nThe [operating guide](../OPERATING_GUIDE.md) covers goal alignment and handoff.\nGovernance/prose tasks stop at their relevant documentation checks; the capture\npath below is only for tasks that actually require an experiment.\n\n## Authority and roles\n\nUser instructions define authorization. The active task freezes its scientific\nquestion and design; this SOP governs execution and evidence. Historical results\nprovide context, not new run permission. Science reviewer owns interpretation;\nan independent execution reviewer owns readiness and may veto unsafe or invalid\nexecution. Roles are capabilities, not model brand names.\n\nA short task states its purpose, mode, parent, scope and completion criteria.\nExperiments additionally specify scientific delta, frozen variables, budget,\nmetrics, classifications, stop conditions, runner and raw root. Reference\nexisting protocols rather than copying them. One branch per coherent task;\npredeclared repeats share the branch.\n\nBefore scientific execution, the task must explain the decision served, why the\nchosen comparison/parameters fit that decision, and what each possible outcome\nchanges. Defaults and unverified assumptions remain labelled as such. An\nengineering integration candidate is not automatically the chosen capability\nbaseline. Check this substantive rationale during scientific review, not merely\nthe presence of a protocol, hashes or complete fields. The short\n[task template](TASK_TEMPLATE.md) supplies these fields without another registry.\n\n## Qualification and change review\n\nRuntime, model, protocol, schema or primary interpretation changes require\nrelevant no-live regression checks and independent scientific review. Execution\nplumbing must be reviewed for trajectory neutrality. Documentation-only changes\ndo not require a repeat scientific judgment; record their relationship to the\naccepted implementation and review current execution identity before live.\n\nSubstrate prepare requires a sealed clean/non-development qualification receipt.\nIts content fingerprint binds tracked runtime/tests/build inputs, model assets,\nactual isolated runtime, interpreter, checkpoint, native dependencies and binary,\ncontroller build products and compiler header/link dependencies. Current\nlightweight quality checks always rerun, including prose/link hygiene. Selected\nprotocols must belong to the fingerprinted protocol directory; their positive\ninteger budget is bound to preparation and explicit authorization.\nChanged inputs invalidate reuse; matching inputs may reuse offline tests across\ndocumentation or merge commits. Producer HEAD is retained, never rewritten.\nCurrent task, review, exact execution HEAD and user authorization are not cached.\n\n## Fresh preflight\n\nThe Go2 Praxis dispatcher requires a canonical TaskSpec resource manifest on\nnew queued tasks. Declare the `substrate` root for the CTS checkpoint with the\nSHA-256 from `tools/substrate/sources.lock.json`, and declare the runtime modules\nand exact distribution versions required by that task. The host binds\n`substrate` to its trusted `.substrate` directory and probes those modules with\nthe reliable substrate Python. A missing or mismatched declared resource stops\nbefore Luna starts and consumes no scientific attempt. The worker's own\nprovisioning and the scientific preparation checks still verify the complete\nsource lock, model loading, and execution semantics. Older task documents\nwithout a manifest must be reissued under the new contract before dispatch;\ndo not silently relax this gate to replay them.\n\nBefore capture, the runner continuously holds the experiment lock through\npreflight and the whole campaign. Check exact HEAD, expected logical branch\nidentity, and clean worktree. A named expected branch remains valid for manual\nexecution; a detached Praxis v2 worktree requires the complete matching Praxis\nbinding and exact frozen commit. Also check current inputs, fresh output, no\nstale runtime processes, and transport-specific constraints. DDS uses actual\ndomain/port checks; reviewed in-process runners have no fictitious DDS\nrequirement. Never run a real runner as a preflight test.\n\nUse the accepted parent as diff-base. Automatically classify changed runtime,\nrunner, schema, scene and analyzer files; explicit surfaces add to this set.\nAny runner change records its actual diff, including explicit runner declarations.\nVerified applicable qualification replaces duplicate offline tests; it never\nreplaces fresh lock/process/input checks. Unknown executable substrate files\nare conservatively runtime changes. Failed prerequisites prevent launch.\n\n## Attempts, exploration and stopping\n\nThe first valid post-handoff state/control sample consumes an attempt, reserved\ndurably before logging. Prelaunch execution-only faults may be repaired while\npreserving failed artifacts. A proven execution-only boot fault may receive one\nrecovery only if the task permits it. A stricter frozen task overrides this default.\n\nNo opportunistic retry, replacement, threshold change or sample selection after\ncapture. Safety failures and broken execution/evidence stop. A task may predeclare\nan exploratory matrix whose expected performance failures are retained outcomes\nand whose remaining cases continue; that permission must exist before results.\nConfirmatory designs freeze intervention, comparisons, sample plan and stopping.\nThe sealed rl-flat-compatibility-v1 campaign remains first-nonpass-stop, no retry.\n\n## Evidence and interpretation\n\nRaw evidence is append-only across runs and immutable within a sealed run.\nRecord source/inputs, environment, command, attempt ledger and terminal status.\nVerify capture independently; local verification includes the external ledger.\nPortable verification must explicitly say the external ledger was not checked.\nShared runtime formulas are supplemented by independent algebraic checks;\nmodel contact reconstruction is a separate zero-integration audit, not replayed\ndynamics or proof of causal attribution.\n\nDeterministic offline salvage is allowed only with unchanged raw bytes, unique\nsource-grounded mapping and independent invariants. Corrections are new artifacts\nand superseding interpretation, never rewriting history. Distinguish execution,\nevidence, causal inference and scientific performance boundaries.\n\nRepeated deterministic traces test repeatability, not statistical success rates.\nCapability comparisons need a prospective task/terrain/seed or perturbation plan,\ninformation and compute conditions, uncertainty reporting and declared exclusions.\nCheck pretrained-policy deployment semantics before attributing transfer failure\nto policy quality. Same robot name is not equal physics or equal task distribution.\n\n## Closeout and navigation\n\nFor experiments, the usual tracked artifacts are RESULTS.md, analysis.json and\nprovenance.csv. Routine engineering and documentation work use only the records\nneeded to support their actual claims; do not manufacture empty data artifacts.\nArchive source-bound raw evidence, including failed outcomes and the ledger,\nverify archive members, then regenerate the workspace catalog. Do not duplicate\nprotocol text or state records across manually maintained status pages.\n\ndocs/research/current.json owns execution navigation; CURRENT.md and START_HERE\nare generated views. PROJECT_RECORD owns research conclusions; TOPIC_AUDIT changes\nonly when topic judgment changes. Historical branch/worktree cleanup is a separate\nowned maintenance action, never implicit deletion during an experiment.\n","path":"docs/research/SOP.md","sha256":"8e52478bea6fd2b686ac1fdaeef4a8ad8f4a46b0c05cc16986867c0d59f333dc","truncated":false},{"chars":4147,"excerpt":"\"\"\"Named boundaries; no simulator handles are exposed to proprioceptive policies.\"\"\"\n\nfrom dataclasses import dataclass\nimport numpy as np\n\nPOLICY_JOINTS = tuple(\n    f\"{leg}_{joint}_joint\"\n    for leg in (\"FL\", \"FR\", \"RL\", \"RR\")\n    for joint in (\"hip\", \"thigh\", \"calf\")\n)\nMOTOR_JOINTS = tuple(\n    f\"{leg}_{joint}_joint\"\n    for leg in (\"FR\", \"FL\", \"RR\", \"RL\")\n    for joint in (\"hip\", \"thigh\", \"calf\")\n)\n\n\ndef vector(value, size, name):\n    raw = np.asarray(value)\n    if raw.dtype.kind not in \"iuf\":\n        raise ValueError(f\"{name}: expected numeric values, not booleans/strings\")\n    result = np.asarray(value, dtype=np.float64)\n    if result.shape != (size,) or not np.isfinite(result).all():\n        raise ValueError(f\"{name}: expected {size} finite values\")\n    return result.copy()\n\n\ndef reorder(values, source, target):\n    source, target = tuple(source), tuple(target)\n    if any(not isinstance(name, str) or not name for name in source + target):\n        raise ValueError(\"joint names must be nonempty strings\")\n    if (\n        len(set(source)) != len(source)\n        or len(set(target)) != len(target)\n        or set(source) != set(target)\n    ):\n        raise ValueError(\"joint names must be unique and describe the same joints\")\n    a = vector(values, len(source), \"joint vector\")\n    return a[[source.index(name) for name in target]]\n\n\n@dataclass(frozen=True)\nclass Proprioception:\n    # MuJoCo free-joint rotational velocity is in the local body frame.\n    joint_names: tuple\n    position: np.ndarray\n    velocity: np.ndarray\n    quaternion_wxyz: np.ndarray\n    angular_velocity_body: np.ndarray\n\n    def __post_init__(self):\n        object.__setattr__(self, \"joint_names\", tuple(self.joint_names))\n        for name, size in (\n            (\"position\", 12),\n            (\"velocity\", 12),\n            (\"quaternion_wxyz\", 4),\n            (\"angular_velocity_body\", 3),\n        ):\n            value = vector(getattr(self, name), size, name)\n            object.__setattr__(\n                self, name, np.frombuffer(value.tobytes(), dtype=np.float64)\n            )\n\n    def validate(self):\n        reorder(self.position, self.joint_names, POLICY_JOINTS)\n        vector(self.velocity, 12, \"joint velocity\")\n        q = vector(self.quaternion_wxyz, 4, \"quaternion\")\n        if abs(np.linalg.norm(q) - 1) > 1e-6:\n            raise ValueError(\"quaternion must be normalized\")\n        vector(self.angular_velocity_body, 3, \"angular velocity\")\n\n\n@dataclass(frozen=True)\nclass TorqueCommand:\n    joint_names: tuple\n    feedforward: np.ndarray\n    position_target: np.ndarray\n    velocity_target: np.ndarray\n    kp: np.ndarray\n    kd: np.ndarray\n\n    def __post_init__(self):\n        object.__setattr__(self, \"joint_names\", tuple(self.joint_names))\n        for name in (\"feedforward\", \"position_target\", \"velocity_target\", \"kp\", \"kd\"):\n            value = vector(getattr(self, name), 12, name)\n            object.__setattr__(\n                self, name, np.frombuffer(value.tobytes(), dtype=np.float64)\n            )\n\n    def resolve(self, observation, lower, upper, target_names):\n        observation.validate()\n        ff, qref, dqref, kp, kd = [\n            reorder(v, self.joint_names, target_names)\n            for v in (\n                self.feedforward,\n                self.position_target,\n                self.velocity_target,\n                self.kp,\n                self.kd,\n            )\n        ]\n        if (kp < 0).any() or (kd < 0).any():\n            raise ValueError(\"negative PD gain\")\n        q = reorder(observation.position, observation.joint_names, target_names)\n        dq = reorder(observation.velocity, observation.joint_names, target_names)\n        lo, hi = vector(lower, 12, \"lower\"), vector(upper, 12, \"upper\")\n        if (lo >= hi).any():\n            raise ValueError(\"invalid actuator range\")\n        pd = kp * (qref - q) + kd * (dqref - dq)\n        total = vector(ff + pd, 12, \"total torque\")\n        return {\n            \"feedforward\": ff,\n            \"pd\": pd,\n            \"total_unclipped\": total,\n            \"ctrl\": np.clip(total, lo, hi),\n            \"saturated\": (total < lo) | (total > hi),\n        }\n","path":"tools/substrate/contracts.py","sha256":"6eb689775fd77273f3de9f319157c41fa227a6523ba46c802dff3cdfa6ba2b44","truncated":false},{"chars":7178,"excerpt":"\"\"\"Conservative local MJCF dependency closure and compiled physical fingerprint.\"\"\"\n\nimport hashlib\nimport json\nfrom pathlib import Path\nimport xml.etree.ElementTree as ET\nimport numpy as np\n\n\nfrom .integrity import digest\n\n\ndef dependency_manifest(scene, repository):\n    root = Path(repository).resolve()\n    scene = Path(scene).resolve()\n    files, active = {}, set()\n    compilers = []\n\n    def confined(path):\n        p = path.resolve()\n        if not p.is_relative_to(root) or not p.is_file():\n            raise ValueError(f\"missing or out-of-root dependency: {p}\")\n        return p\n\n    def visit(path, meshdir=None, texturedir=None):\n        path = confined(path)\n        if path in active:\n            raise ValueError(\"cyclic MJCF include\")\n        active.add(path)\n        tree = ET.parse(path).getroot()\n        files[str(path.relative_to(root))] = digest(path)\n        compiler = tree.find(\"compiler\")\n        if compiler is not None:\n            compilers.append(path)\n            if len(compilers) > 1 or path.parent != scene.parent:\n                raise ValueError(\n                    \"unsupported multi-compiler or nested compiler asset semantics\"\n                )\n            if compiler.get(\"strippath\") not in (None, \"false\"):\n                raise ValueError(\"strippath is unsupported\")\n            assetdir = compiler.get(\"assetdir\", \"\")\n            meshdir = path.parent / compiler.get(\"meshdir\", assetdir)\n            texturedir = path.parent / compiler.get(\"texturedir\", assetdir)\n        for node in tree.iter():\n            if node.tag in (\"plugin\", \"attach\", \"model\") or any(\n                k.startswith(\"file\") and k != \"file\" for k in node.attrib\n            ):\n                raise ValueError(\"unsupported external/model/plugin asset declaration\")\n            name = node.get(\"file\")\n            if not name:\n                continue\n            if node.tag == \"include\":\n                visit(path.parent / name, meshdir, texturedir)\n            else:\n                if node.tag not in (\"mesh\", \"texture\", \"hfield\"):\n                    raise ValueError(\"unsupported file-bearing asset: \" + node.tag)\n                base = (\n                    meshdir\n                    if node.tag == \"mesh\"\n                    else texturedir\n                    if node.tag == \"texture\"\n                    else path.parent\n                )\n                asset = confined((base or path.parent) / name)\n                files[str(asset.relative_to(root))] = digest(asset)\n        active.remove(path)\n\n    visit(scene)\n    entries = dict(sorted(files.items()))\n    return {\n        \"files\": entries,\n        \"sha256\": hashlib.sha256(\n            json.dumps(entries, sort_keys=True, separators=(\",\", \":\")).encode()\n        ).hexdigest(),\n    }\n\n\ndef physical_fingerprint(model):\n    # Sensor/custom/task metadata deliberately excluded. Physical arrays are included\n    # by prefix, including mesh vertices and collision geometry, not only XML text.\n    prefixes = (\n        \"body_\",\n        \"jnt_\",\n        \"dof_\",\n        \"geom_\",\n        \"mesh_\",\n        \"hfield_\",\n        \"pair_\",\n        \"exclude_\",\n        \"eq_\",\n        \"tendon_\",\n        \"wrap_\",\n        \"actuator_\",\n        \"key_\",\n    )\n    arrays = {}\n    for name in dir(model):\n        if name.startswith(prefixes):\n            value = getattr(model, name)\n            if isinstance(value, np.ndarray):\n                arrays[name] = {\n                    \"shape\": list(value.shape),\n                    \"dtype\": str(value.dtype),\n                    \"hash\": hashlib.sha256(value.tobytes()).hexdigest(),\n                }\n    # Addresses affect mechanics too; sensor insertion must not perturb these.\n    for name in (\"jnt_qposadr\", \"jnt_dofadr\", \"actuator_trnid\", \"dof_parentid\"):\n        arrays[name] = np.asarray(getattr(model, name)).tolist()\n    options = {}\n    for name in dir(model.opt):\n        if name.startswith(\"_\"):\n            continue\n        value = getattr(model.opt, name)\n        if isinstance(value, np.ndarray):\n            options[name] = value.tolist()\n        elif isinstance(value, (float, int)):\n            options[name] = value\n    payload = {\n        \"arrays\": arrays,\n        \"options\": options,\n        \"nq\": model.nq,\n        \"nv\": model.nv,\n        \"nu\": model.nu,\n        \"qpos0\": model.qpos0.tolist(),\n    }\n    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()\n\n\ndef joint_layout(model):\n    import mujoco\n    from .contracts import POLICY_JOINTS\n\n    names, qpos, dof = [], [], []\n    for actuator in range(model.nu):\n        if (\n            model.actuator_trntype[actuator] != mujoco.mjtTrn.mjTRN_JOINT\n            or model.actuator_gaintype[actuator] != mujoco.mjtGain.mjGAIN_FIXED\n            or model.actuator_biastype[actuator] != mujoco.mjtBias.mjBIAS_NONE\n            or model.actuator_dyntype[actuator] != mujoco.mjtDyn.mjDYN_NONE\n            or model.actuator_gainprm[actuator, 0] != 1\n            or not np.array_equal(model.actuator_gear[actuator], [1, 0, 0, 0, 0, 0])\n            or not model.actuator_ctrllimited[actuator]\n            or model.actuator_forcelimited[actuator]\n        ):\n            raise ValueError(\n                \"shared substrate requires finite-range direct torque motors\"\n            )\n        joint = int(model.actuator_trnid[actuator, 0])\n        if (\n            model.jnt_type[joint] != mujoco.mjtJoint.mjJNT_HINGE\n            or model.jnt_actfrclimited[joint]\n        ):\n            raise ValueError(\"unsupported joint transmission or secondary force limit\")\n        names.append(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint))\n        qpos.append(int(model.jnt_qposadr[joint]))\n        dof.append(int(model.jnt_dofadr[joint]))\n    if len(names) != 12 or len(set(names)) != 12 or set(names) != set(POLICY_JOINTS):\n        raise ValueError(\"unexpected actuated joint set\")\n    return tuple(names), qpos, dof\n\n\ndef decorate_mjpc(scene, destination):\n    # Absolute include preserves the existing model/assets. Usersensors precede\n    # ordinary sensors as required by MJPC. No actuator, inertia or contact edits.\n    root = ET.Element(\"mujoco\", model=\"Go2 shared substrate offline admission\")\n    sensors = ET.SubElement(root, \"sensor\")\n    for name, dim, weight in (\n        (\"height\", 1, 10),\n        (\"upright\", 3, 2),\n        (\"velocity\", 3, 1),\n        (\"posture\", 12, 0.1),\n        (\"effort\", 12, 0.001),\n    ):\n        ET.SubElement(\n            sensors, \"user\", name=name, dim=str(dim), user=f\"0 {weight} 0 100\"\n        )\n    ET.SubElement(root, \"include\", file=str(Path(scene).resolve()))\n    # A wrapper stored outside the scene directory changes MJCF relative asset\n    # resolution. Keep the Go2 mesh source explicit; physical hash must match.\n    ET.SubElement(\n        root, \"compiler\", meshdir=str(Path(scene).resolve().parent / \"assets\")\n    )\n    custom = ET.SubElement(root, \"custom\")\n    for name, value in (\n        (\"agent_planner\", \"2\"),\n        (\"agent_horizon\", \"0.04\"),\n        (\"agent_timestep\", \"0.002\"),\n    ):\n        ET.SubElement(custom, \"numeric\", name=name, data=value)\n    ET.ElementTree(root).write(destination, encoding=\"unicode\")\n","path":"tools/substrate/model.py","sha256":"3dfd63472e55bb9f89cde1975418a5225ad5a94049b6ef001e63d8ac0c130dbb","truncated":false},{"chars":5926,"excerpt":"import tempfile\nimport unittest\nfrom pathlib import Path\nimport numpy as np\nfrom .contracts import (\n    POLICY_JOINTS as P,\n    MOTOR_JOINTS as M,\n    Proprioception,\n    TorqueCommand,\n    reorder,\n)\nfrom .rl import DEFAULT, observation45\nfrom .model import dependency_manifest\nfrom .evidence import summarize_frames, validate_capture_contract\n\n\nclass Boundaries(unittest.TestCase):\n    def obs(self):\n        return Proprioception(\n            P, DEFAULT.copy(), np.zeros(12), np.array([1.0, 0.0, 0.0, 0.0]), np.zeros(3)\n        )\n\n    def test_named_permutation_roundtrip(self):\n        a = np.arange(12.0)\n        np.testing.assert_array_equal(reorder(reorder(a, P, M), M, P), a)\n        self.assertEqual(reorder(a, P, M)[0], 3)\n\n    def test_duplicate_missing_nonfinite_rejected(self):\n        for source, values in (\n            (P[:-1] + (P[0],), np.zeros(12)),\n            (P[:-1], np.zeros(11)),\n            (P, np.full(12, np.nan)),\n        ):\n            with self.subTest(source=source), self.assertRaises(ValueError):\n                reorder(values, source, M)\n\n    def test_torque_pd_sum_before_model_limit(self):\n        o = self.obs()\n        cmd = TorqueCommand(\n            P,\n            np.full(12, 30),\n            DEFAULT.astype(np.float64) + 1,\n            np.zeros(12),\n            np.full(12, 20),\n            np.full(12, 0.5),\n        )\n        r = cmd.resolve(o, np.full(12, -40), np.full(12, 40), M)\n        np.testing.assert_array_equal(r[\"total_unclipped\"], np.full(12, 50))\n        np.testing.assert_array_equal(r[\"ctrl\"], np.full(12, 40))\n        self.assertTrue(r[\"saturated\"].all())\n\n    def test_invalid_gain_and_range(self):\n        cmd = TorqueCommand(\n            P, np.zeros(12), DEFAULT, np.zeros(12), np.full(12, -1), np.zeros(12)\n        )\n        with self.assertRaises(ValueError):\n            cmd.resolve(self.obs(), np.full(12, -40), np.full(12, 40), M)\n        cmd = TorqueCommand(\n            P, np.zeros(12), DEFAULT, np.zeros(12), np.zeros(12), np.zeros(12)\n        )\n        with self.assertRaises(ValueError):\n            cmd.resolve(self.obs(), np.ones(12), np.zeros(12), M)\n\n    def test_policy_observation_golden(self):\n        o = self.obs()\n        o = Proprioception(\n            M,\n            reorder(o.position, P, M) + np.arange(12) / 10,\n            reorder(np.arange(12), P, M),\n            np.array([np.cos(0.2), np.sin(0.2), 0.0, 0.0]),\n            np.array([1.0, 2.0, 3.0]),\n        )\n        actual = observation45(o, [0.2, -0.1, 0.3], np.arange(12) / 20)\n        expected = np.concatenate(\n            (\n                [0.25, 0.5, 0.75],\n                [0, -np.sin(0.4), -np.cos(0.4)],\n                [0.4, -0.2, 0.075],\n                reorder(o.position, M, P) - DEFAULT,\n                np.arange(12) * 0.05,\n                np.arange(12) / 20,\n            )\n        ).astype(np.float32)\n        np.testing.assert_allclose(actual, expected, atol=1e-7)\n        self.assertEqual(actual.shape, (45,))\n        self.assertEqual(actual.dtype, np.float32)\n\n    def test_policy_rejects_bad_quaternion_command(self):\n        o = self.obs()\n        with self.assertRaises(ValueError):\n            observation45(o, [3, 0, 0], np.zeros(12))\n        o = Proprioception(P, DEFAULT, np.zeros(12), np.zeros(4), np.zeros(3))\n        with self.assertRaises(ValueError):\n            observation45(o, [0, 0, 0], np.zeros(12))\n\n    def test_asset_closure_detects_included_mesh_mutation(self):\n        with tempfile.TemporaryDirectory() as t:\n            p = Path(t)\n            (p / \"assets\").mkdir()\n            (p / \"assets/a.obj\").write_text(\"mesh one\")\n            (p / \"robot.xml\").write_text(\n                '<mujoco><compiler meshdir=\"assets\"/><asset><mesh file=\"a.obj\"/></asset></mujoco>'\n            )\n            (p / \"scene.xml\").write_text('<mujoco><include file=\"robot.xml\"/></mujoco>')\n            a = dependency_manifest(p / \"scene.xml\", p)\n            self.assertEqual(len(a[\"files\"]), 3)\n            (p / \"assets/a.obj\").write_text(\"mesh two\")\n            self.assertNotEqual(\n                a[\"sha256\"], dependency_manifest(p / \"scene.xml\", p)[\"sha256\"]\n            )\n\n    def test_include_cycle_and_missing_rejected(self):\n        with tempfile.TemporaryDirectory() as t:\n            p = Path(t)\n            f = p / \"a.xml\"\n            for target in (\"a.xml\", \"missing.xml\", \"../outside.xml\"):\n                f.write_text(f'<mujoco><include file=\"{target}\"/></mujoco>')\n                with self.assertRaises(ValueError):\n                    dependency_manifest(f, p)\n\n    def test_earliest_failure_preserved(self):\n        rows = [\n            dict(sequence=0, sim_time_s=0, failure=\"solver_nonfinite\"),\n            dict(sequence=1, sim_time_s=0.02, terminal_reason=\"task_incomplete\"),\n        ]\n        r = summarize_frames(rows, 0.02)\n        self.assertEqual(r[\"first_failure\"][\"reason\"], \"solver_nonfinite\")\n        self.assertEqual(r[\"terminal_reason\"], \"task_incomplete\")\n        self.assertFalse(r[\"task_complete\"])\n\n    def test_jump_traverse_vs_mandatory_support(self):\n        rows = [dict(sequence=0, sim_time_s=0, task_complete=True, supports=[])]\n        self.assertTrue(\n            summarize_frames(rows, 0.02, \"traverse\", [\"top\"])[\"task_complete\"]\n        )\n        self.assertFalse(\n            summarize_frames(rows, 0.02, \"mandatory_support\", [\"top\"])[\"task_complete\"]\n        )\n\n    def test_duplicate_or_gap_rejected(self):\n        for seq, t in ((0, 0.02), (2, 0.02), (1, 0), (1, 0.04), (1, float(\"nan\"))):\n            rows = [dict(sequence=0, sim_time_s=0), dict(sequence=seq, sim_time_s=t)]\n            with self.subTest(seq=seq, t=t), self.assertRaises(ValueError):\n                summarize_frames(rows, 0.02)\n\n    def test_unreviewed_capture_fail_closed(self):\n        with self.assertRaisesRegex(ValueError, \"unfrozen capture\"):\n            validate_capture_contract({})\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n","path":"tools/substrate/test_substrate.py","sha256":"dace5f4e061962429a46684e5f65bac0fcc77ef57f7eb71b90d94019f8ab5d55","truncated":false},{"chars":1994,"excerpt":"\"\"\"Native model checks, run separately from dependency-light hosted CI.\"\"\"\n\nimport tempfile\nimport unittest\nfrom pathlib import Path\nimport mujoco\nimport numpy as np\nfrom .contracts import MOTOR_JOINTS\nfrom .model import physical_fingerprint, joint_layout, decorate_mjpc\n\nROOT = Path(__file__).resolve().parents[2]\nSCENE = ROOT / \"unitree_robots/go2/phase2_flat.xml\"\n\n\nclass NativeBoundary(unittest.TestCase):\n    def test_named_joints_and_model_limits(self):\n        model = mujoco.MjModel.from_xml_path(str(SCENE))\n        names, qadr, vadr = joint_layout(model)\n        self.assertEqual(names, MOTOR_JOINTS)\n        self.assertEqual(qadr[:3], [10, 11, 12])\n        self.assertEqual(vadr[:3], [9, 10, 11])\n        np.testing.assert_allclose(model.actuator_ctrlrange[:3, 1], [40.0, 40.0, 45.43])\n\n    def test_decorated_physics_identical(self):\n        model = mujoco.MjModel.from_xml_path(str(SCENE))\n        with tempfile.TemporaryDirectory() as t:\n            f = Path(t) / \"task.xml\"\n            decorate_mjpc(SCENE, f)\n            decorated = mujoco.MjModel.from_xml_path(str(f))\n            self.assertEqual(\n                physical_fingerprint(model), physical_fingerprint(decorated)\n            )\n            self.assertEqual(\n                int(decorated.sensor_type[0]), int(mujoco.mjtSensor.mjSENS_USER)\n            )\n            self.assertEqual(sum(decorated.sensor_dim[:5]), 31)\n\n    def test_friction_or_actuator_drift_detected(self):\n        model = mujoco.MjModel.from_xml_path(str(SCENE))\n        original = physical_fingerprint(model)\n        model.geom_friction[0, 0] *= 0.5\n        self.assertNotEqual(original, physical_fingerprint(model))\n        model.actuator_gainprm[0, 0] = 2\n        with self.assertRaises(ValueError):\n            joint_layout(model)\n        model.actuator_gainprm[0, 0] = 1\n        model.actuator_forcelimited[0] = True\n        with self.assertRaises(ValueError):\n            joint_layout(model)\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n","path":"tools/substrate/test_native_boundary.py","sha256":"40477510795bfe86bbe6c26324fa9044e811968c20628aeec3c2adf621b44b0a","truncated":false},{"chars":2290,"excerpt":"# ADR-0001: MuJoCo/MJX evaluation substrate and controller ownership\n\n- **Date:** 2026-09-28\n- **Status:** Accepted as the project architecture direction; implementation is\n  partial.\n- **Decision served:** establish a reusable evaluation foundation that lets\n  evidence, rather than an assumed controller default, identify which\n  locomotion failures merit new mechanisms.\n\n## Decision\n\nMuJoCo is the canonical evaluation physics for the current project. MuJoCo/MJX\nis the intended scalable substrate direction; the shared interfaces and\nscalable execution path are not yet fully implemented.\n\nGo2 is the first testbed, not the project identity. MJPC/iLQR is a strong\ngradient-based comparator, not a privileged default or source of truth.\nSampling/search, learning, and contact-implicit methods remain available when\nthe task and observed failure structure justify them.\n\nReuse mature simulator, solver, and controller infrastructure where it fits.\nScientific ownership resides in task, information, timing, and intervention\ndefinitions; diagnostics; fair comparisons; and any new mechanism that the\nevidence shows is needed. Reimplementing a mature controller from scratch is\nnot a contribution by itself.\n\n## Planned boundary\n\nThe next minimal contract direction is `TaskSpec`, `ScenarioSpec`,\n`InformationSpec`, `TimingSpec`, `ControllerAdapter`, and a canonical\n`Evaluator` / physical-oracle boundary. The evaluator owns common physical\nexecution and canonical outcome evidence; the information contract states what\neach controller may observe. This is a direction for later implementation,\nnot a universal SDK or a claim that a generic multi-controller platform\nalready exists.\n\n## Current and verified state\n\nThe repository has task-specific MuJoCo Go2 assets, a reviewed schema-2 public\nRL execution/analyzer/verifier path, and static MJPC/iLQG admission utilities.\nThese are executable components, not yet the shared multi-controller contract\nabove. In particular, static MJPC admission is not a closed-loop locomotion\ncomparison.\n\nThe verified #189 conclusions and their semantic corrections are recorded in\nthe [versioned erratum](../validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md).\nThey do not yet establish a cross-controller bottleneck or a paper topic.\n","path":"docs/adr/ADR-0001-mujoco-mjx-evaluation-substrate.md","sha256":"5d9a573cd596acd22c580389c14425a22a8ab85602345ea2068a2001df0ce761","truncated":false}],"project_id":"go2-mujoco-control","project_profile_canonical_sha256":"6148b57f23e8d0f297143dd661125abdc981e4b210ca8e6850a2b3f767941ad2","project_profile_raw_sha256":"022c7317a228337555d344b6894ba24fe4c628fd0db7fbbcaca8aeaf4a5fbcaa","repository":"cwchewang/go2-mujoco-control","schema_version":1}
PRAXIS_CONTEXT_PACK -->
