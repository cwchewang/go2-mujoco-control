# R1B2 upstream Agent reproduction — 2026-09-29

Purpose: diagnose #197 without tuning. #197 forced special Walk mode + manual Walk gait at t=0 in a custom external loop; this is not yet equivalent to the paper/source ordinary quadruped goal-following path.

Pinned source: johnzhang3/mujoco_mpc@e00c47a5adb9856af2e0f24231bb3a60d5be23c4.

Frozen rules:
- use upstream Agent/agent_server semantics, not a new iLQG implementation;
- preserve upstream model, costs, PD (Kp 60/Kd 5), horizon 0.35 s, planner timestep 0.01 s;
- no RL comparison, #189 use, cost tuning, parameter sweep or paper-topic claim.

D1: audit exact differences among synchronous agent_server, async ui_agent_server, and #197 custom runner: task Transition, state/mocap propagation, planner warm-start, feedback policy, update timing and physics stepping.

D2: source-native standing anchor. Start with default Quadruped mode and Automatic gait switching. Use server-owned/supported physics path. Record state, selected task parameters, actions, timing and trunk height. If it cannot remain upright, stop.

D3 only if D2 passes: move only the upstream goal mocap modestly in +X. Keep Quadruped + Automatic. Record actual gait selection and progress. Do not force Walk mode or gait.

D4 only if D3 passes: after a stable phase, enter special Walk mode to diagnose whether #197 failed because it entered Walk at t=0.

Before each live engineering smoke, run deterministic source/model/config checks with zero physics steps. These are engineering reproductions, not scientific attempts.

Deliver a concise diagnosis document and preserved smoke evidence. If D3 passes, propose only the minimal ControllerAdapter boundary; do not build a universal evaluator.