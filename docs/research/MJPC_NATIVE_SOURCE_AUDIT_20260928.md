# Native MuJoCo MPC Go2 source audit — 2026-09-28

## Frozen upstream identity

The project already pins the exact author Go2 branch:

- repository: `https://github.com/johnzhang3/mujoco_mpc.git`
- commit: `e00c47a5adb9856af2e0f24231bb3a60d5be23c4`
- local Atlas clone: `.substrate/mjpc`, verified clean at that commit
- author deployment repository inspected at `johnzhang3/mujoco_mpc_deploy` main commit `ba86aa7d4c3f0efe7fee32c2b6d259d4a6d865df`

This means the next step does not need a new controller implementation or a different MJPC fork.

## Native control problem

The pinned `mjpc/tasks/quadruped/task_flat.xml` defines:

- planner index 2 = iLQG;
- planning horizon 0.35 s;
- planner discretization 0.01 s;
- Go2 quadruped modes including Walk;
- gait choices Stand / Walk / Trot / Canter / Gallop with automatic gait switching;
- task parameters including Walk speed and Walk turn;
- joint-reference actuators with gain 60 and derivative bias 5.

The task residual includes upright, height, moving position target, gait foot-height reference, balance, effort, posture, heading and angular-momentum terms. These are the upstream source semantics and must not be replaced by the project's current static admission cost.

## Deployment semantics

The author deployment interface feeds the latest Go2 state to the MJPC Agent and consumes joint-position-reference actions. The published system uses iLQR updates around 50 Hz, TV-LQR feedback around 300 Hz, and joint-level PD around 500 Hz. The paper states a default 0.35 s horizon with dynamics discretized at 100 Hz.

The Python API exposes `set_state`, `get_action(... nominal_action=False)`, `set_mode`, and `set_task_parameters`. The author's hardware path uses `ui_agent_server`, whose planner is asynchronous.

## Difference from current project admission

The current project MJPC admission is intentionally only a static home-state integration fixture with a ~40 ms horizon and no external plant advancement. It proves wiring, not locomotion capability. It must not be used as the strong MPC comparator.

## R1 decision

Before any aligned RL-vs-MPC benchmark, reproduce the native upstream Go2 closed-loop control problem with its own task, action parameterization, PD-in-model semantics, asynchronous planner and timing. Only after that source-condition anchor works may a later task adapt it to the shared evaluator.
