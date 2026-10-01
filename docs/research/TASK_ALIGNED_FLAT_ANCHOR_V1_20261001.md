# Prospective aligned flat anchor v1 — preparation only — 2026-10-01

Goal: freeze the first short shared closed-loop integration anchor for the public
RL checkpoint and native MJPC comparator before any canonical physics is allowed.

This is not a controller ranking or performance experiment. It exists to test
whether both controller families can later be executed through the same canonical
TaskSpec, ScenarioSpec, action boundary, and CanonicalEvaluator while explicitly
recording their different information and timing regimes.

Frozen shared semantics:
- canonical scene: unitree_robots/go2/phase2_flat.xml;
- canonical physics dt: 0.002 s;
- reset: home key 0, zero qvel, zero ctrl;
- body-frame forward command target: [1.0, 0.0, 0.0];
- 50 zero-command ticks, 100 ramp ticks, 500 total ticks;
- measurement begins at tick 250;
- longitudinal metric: body_vx;
- world-x progress/world-y lateral gates are valid only because the frozen home
  key 0 has identity quaternion, so initial body forward/left align with world
  +x/+y; review preflight must fail closed if that reset geometry drifts;
- integration guardrails: progress >= 0.05 m, vx MAE <= 2.0 m/s,
  lateral <= 0.4 m, tilt <= 0.8 rad, height in [0.12, 0.55] m.

These thresholds are intentionally broad engineering guardrails. A future
PASS/FAIL under this anchor must not be interpreted as controller superiority or
a scientific bottleneck.

Controller regimes:
- RL: ProprioceptivePolicyAdapter over the frozen public CTS checkpoint;
  proprioceptive information only; no model access; 20 ms policy/feedback
  update; offline_unbounded compute semantics.
- MJPC: PositionTargetControllerAdapter over the source-pinned native iLQG
  bridge; WholeBodyState plus controller-private model access; 20 ms replanning,
  2 ms prospective shared feedback adaptation; offline_unbounded compute
  semantics.

The two controllers therefore do not receive identical information or timing.
The purpose of this first anchor is interface/evaluator alignment with those
differences made explicit, not equal-resource scientific comparison.

Hard authorization:
- physics_step_authorized = false;
- scientific_attempts_authorized = 0;
- requires_independent_review = true.

No execution task may reinterpret this preparation as permission to call
canonical mj_step. A separate reviewed task must freeze the exact capture commit,
attempt budget, evidence paths, and execution authorization first.
