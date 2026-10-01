# R1 MJPC planning / feedback cadence — engineering closeout

Status: ENGINEERING PASS / SCIENTIFIC ATTEMPTS 0.

## Exact identity

- code commit: 3e1d4bae3c7d09c0a0c5b23fe075f6822967a28b
- pinned MJPC source: e00c47a5adb9856af2e0f24231bb3a60d5be23c4
- sealed native controller SHA-256:
  9dd19fcff9f67d4bf0dc8638b31b9c35bf493a9b545f682d13d181c3c34e7a33
- canonical plant steps: 0
- canonical plant time: 0.0 s

## Implemented timing semantics

TimingSpec now distinguishes:
- physics period: 0.002 s;
- slow control/planning period: 0.020 s;
- feedback period: 0.002 s for this prospective shared adaptation;
- compute semantics: offline_unbounded.

The native bridge replans only on planning ticks. Between replans it updates the
current WholeBodyState and evaluates the existing iLQG policy with
ActionFromPolicy(current_state, current_time). Command is sampled only on a
replan tick; requested command changes between replans are recorded but do not
silently mutate the planner task.

The author's audited deployment writes joint PD LowCmd at 2 ms while the MJPC
action is produced by a separate asynchronous loop. Consequently this 2 ms
feedback configuration is a shared-evaluator adaptation, not a source-timing
reproduction and not evidence of 500 Hz native MJPC feedback.

## Exact-code zero-canonical-step smoke

The smoke deliberately did not call canonical plant.step().

At t=0:
- requested command: [1.0, 0.0, 0.0];
- sampled command: [1.0, 0.0, 0.0];
- replanned: true;
- planning compute: 0.027854 s;
- action compute: 0.000001 s;
- iLQG reported latest plan cost: 0.08976081533117637;
- q_des range: [-1.800463694591259, 0.9012494598107356];
- max absolute resolved canonical torque: 0.10329455263302645 Nm;
- saturated motors: 0.

At synthetic controller time t=0.002 s, with the canonical state unchanged:
- requested command: [0.5, 0.0, 0.1];
- sampled command: [1.0, 0.0, 0.0];
- replanned: false;
- planning compute: 0.0 s;
- action compute: 0.000001 s;
- q_des range: [-1.800413813559474, 0.90124540571057];
- max absolute resolved canonical torque: 0.1034009670528091 Nm;
- saturated motors: 0.

This second call is a protocol/feedback engineering check, not a physical
trajectory sample: time was advanced for controller-policy evaluation while the
canonical plant was intentionally not stepped.

## Regression

Before the exact-code smoke:
- Ruff passed;
- 98 Python contract/reliability/launch tests passed;
- 9 native MuJoCo scenario/boundary tests passed;
- compileall and git diff --check passed.

Focused cadence tests also cover:
- 20 ms replan / 2 ms feedback tick arithmetic;
- missing, duplicated, reordered, and off-clock feedback ticks;
- command sampling/hold between replans;
- zero planning compute metadata on feedback-only ticks;
- fail-closed requirement for an existing policy before feedback-only action.

## Interpretation

This closes an engineering timing ambiguity in the shared MJPC adapter. It does
not establish real-time feasibility: the observed 27.854 ms planning call exceeds
the prospective 20 ms planning period, and the current anchor therefore remains
offline_unbounded. It also does not establish locomotion performance,
superiority to RL, a cross-controller bottleneck, or a paper contribution.

The next step remains a separate prospective aligned closed-loop anchor with
frozen TaskSpec, ScenarioSpec, per-controller InformationSpec/TimingSpec,
ControllerAdapter identities, and CanonicalEvaluator. No canonical physics step
is authorized by this closeout.
