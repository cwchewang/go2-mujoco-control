# R1 native Go2 MuJoCo MPC closed-loop reproduction — 2026-09-28

## Goal

Reproduce a real closed-loop Go2 locomotion anchor using the already pinned author MuJoCo MPC Go2 implementation. This is an engineering/source-condition reproduction, not a scientific comparison and not a new algorithm.

Base main: `83b3833f53f66f404cf5f428b9648860adb88323`.
Source audit: `docs/research/MJPC_NATIVE_SOURCE_AUDIT_20260928.md`.
Pinned MJPC: `johnzhang3/mujoco_mpc@e00c47a5adb9856af2e0f24231bb3a60d5be23c4`.

## Non-goals / prohibitions

- Do not compare against #189 or claim one controller is better.
- Do not run a formal capability campaign or create a scientific-attempt ledger.
- Do not modify #189 evidence, v1 protocol, thresholds or errata.
- Do not invent a new controller, gait generator, cost or contact planner.
- Do not replace the upstream task with the project's static MJPC admission fixture.
- Do not tune cost weights to obtain a prettier result.
- Do not promote a paper topic.

## Source-condition semantics to preserve

Use the pinned upstream `Quadruped Flat` task and Go2 model:
- planner = iLQG (planner index 2);
- horizon = 0.35 s;
- planner timestep = 0.01 s;
- upstream joint-position-reference action model / PD semantics;
- native residual and cost weights unchanged;
- native automatic gait switching;
- external plant state fed back to the Agent continuously;
- action queried with feedback enabled (`nominal_action=False`).

For the engineering anchor set only task intent:
- mode: `Walk`;
- `Walk speed = 0.5` m/s;
- `Walk turn = 0`;
- gait switch: `Automatic`.

These values define a reproducible source-condition smoke, not a scientific benchmark.

## Implementation

Add a small project-owned runner/adapter around the pinned upstream implementation. It should:

1. verify exact upstream git commit and clean source;
2. build/reuse the required upstream Python/gRPC and `ui_agent_server` artifacts without patching upstream source;
3. load the exact upstream `task_flat.xml` model as an external MuJoCo plant;
4. reset the upstream home keyframe;
5. start the asynchronous `ui_agent_server` Agent;
6. configure only the source task intent above;
7. at each external plant tick, send time/qpos/qvel/mocap state to Agent, query feedback action, write the 12 joint-reference controls to the upstream plant and advance the plant;
8. record raw time, qpos/qvel, ctrl/action, task parameters, model/source hashes, wall timing and basic contact/posture diagnostics;
9. shut down cleanly and leave no orphan server.

If `ui_agent_server` requires a display, use a deterministic headless display wrapper; do not silently switch to synchronous `agent_server`.

## Engineering smoke

Development runs are allowed; they are not scientific attempts. Final clean smoke:
- maximum 3.0 s simulated time;
- exact source condition above;
- no tuning after start;
- finite state and action throughout;
- no process/orphan failure;
- record actual plant timestep and wall-time statistics;
- demonstrate nontrivial forward locomotion (report displacement and mean velocity) without calling it a capability benchmark.

If the native source condition does not locomote, preserve the failure and diagnose the earliest source/deployment mismatch. Do not rescue it by changing costs or inventing gait logic.

## Tests

Add deterministic tests for:
- exact upstream identity;
- task defaults (planner/horizon/planner timestep);
- action dimension and joint-reference semantics;
- task intent configuration;
- cleanup of spawned server;
- runner trace schema.

Where possible, isolate these from live integration. The final engineering smoke may integrate MuJoCo physics but must not touch the scientific-attempt ledger.

## Closeout

Produce `docs/validation/mjpc_native_closed_loop_20260928/RESULTS.md` with:
- exact upstream/source/binary identity;
- whether native closed-loop reproduction succeeded;
- actual timing and motion summary;
- what remains different from #189 RL conditions;
- explicit statement that no cross-controller conclusion has been made.

Update canonical CURRENT/PROJECT_RECORD only if the executable state materially advances, and label it engineering reproduction rather than scientific verification.
