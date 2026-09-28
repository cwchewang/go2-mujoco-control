# R1 native whole-body MPC source reproduction — 2026-09-28

## Goal

Establish one genuinely strong closed-loop model-based baseline before any cross-controller scientific comparison. Reproduce the author-provided Go2 MuJoCo MPC control problem in its own source semantics first; do not weaken it to fit the current RL benchmark.

Base: `83b3833f53f66f404cf5f428b9648860adb88323`.

## Upstream identities

- MuJoCo MPC Go2 fork: `johnzhang3/mujoco_mpc@e00c47a5adb9856af2e0f24231bb3a60d5be23c4`.
- This commit is the current `go2` branch tip at task freeze and is already pinned in `tools/substrate/sources.lock.json`.
- Deployment/interface reference: `johnzhang3/mujoco_mpc_deploy@ba86aa7d4c3f0efe7fee32c2b6d259d4a6d865df`.
- Paper: Whole-Body Model-Predictive Control of Legged Robots with MuJoCo, arXiv 2503.04613 (current paper revision to be recorded in audit).

## Source facts to preserve unless disproven by exact-source audit

The pinned Go2 `task_flat.xml` declares a 0.35 s agent horizon and 0.01 s agent timestep, exposes Stand/Walk/Trot/Canter/Gallop plus Walk speed/turn parameters, and uses the fork's native quadruped residual/task machinery. The deploy reference sends the agent current state and reads a joint-position action, then applies it through Go2 low-level PD. Do not replace these source semantics with the repository's 40 ms static-admission fixture.

## Stage R1A — exact source audit

Document with source references:
1. planner ID and exact iLQG configuration used by the paper/fork;
2. optimized action parameterization and actuator semantics;
3. planner update / feedback / plant frequencies and horizon;
4. task mode, gait, speed and turn parameters required for ordinary quadruped locomotion;
5. reset/keyframe and model identity;
6. state information available to the planner;
7. how PD is represented in prediction versus deployment;
8. what `mujoco_mpc_deploy` contributes versus the solver/task fork;
9. which paper/demo capability can actually be reproduced without hardware, mocap, ROS or Unitree SDK.

If the pinned fork differs materially from the latest paper revision, record the difference rather than silently updating it.

## Stage R1B — source-condition closed-loop engineering reproduction

Build the minimum headless simulation path that preserves the upstream Go2 task and action semantics. It may wrap the upstream Agent/native solver, but must not reimplement iLQG or invent a new gait/controller.

Required first target: stable quadruped locomotion on the author's own flat Go2 task under one documented ordinary locomotion configuration.

This is an engineering/source reproduction, not a scientific benchmark:
- physics integration is allowed;
- no #189 protocol or scientific ledger is used;
- no comparison to RL is made;
- no capability claim beyond the exact source-condition smoke;
- log state, native action, actually applied actuator command, task parameters, solver timing and termination;
- preserve upstream model/task separately from the canonical evaluator.

Before live integration, owner-side deterministic checks must establish exact source/model/task identities and headless runner semantics. Do not run an expensive reviewer.

## Stage R1C — minimal adapter boundary proposal

Only after R1B succeeds, document the smallest adapter needed to expose this controller to the future shared evaluator:
- reset;
- observation/state input;
- step/action output;
- diagnostics/timing;
- controller internal state/warm-start handling.

Do not implement TaskSpec/ScenarioSpec/InformationSpec/TimingSpec as a universal SDK in this task. Do not force MPC internal cost/action representation to match RL.

## Stop conditions

Stop and report rather than redesign the controller if:
- the pinned source does not expose a reproducible headless closed-loop configuration;
- missing upstream assets/dependencies make faithful reproduction materially ambiguous;
- achieving locomotion requires changing task residuals, action semantics or planner internals;
- only a custom controller substantially different from the author implementation can walk.

A stop is useful evidence and should trigger a source/version decision, not ad-hoc tuning.

## Acceptance

Deliver:
- `docs/research/R1_NATIVE_MPC_SOURCE_AUDIT_20260928.md`;
- exact reproduction command/config;
- deterministic engineering smoke evidence if source-faithful execution is possible;
- CPU wall-time / planner timing record;
- source/model/task hashes;
- proposed minimal ControllerAdapter boundary;
- explicit list of what is still NOT verified.

No formal cross-controller experiment and no paper-topic promotion in R1.
