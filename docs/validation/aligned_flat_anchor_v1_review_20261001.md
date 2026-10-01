# Aligned flat anchor v1 — independent semantic review

Status: REVIEW PASS WITH EXPLICIT BOUNDS / NOT_RUN.
Canonical physics steps: 0. Scientific attempts: 0.

The 500-tick anchor is suitable as a first interface/evaluator integration run,
not as a performance comparison. Its broad guardrails are intentionally different
from the sealed #189 flat_reference criteria and must not be compared to #189
PASS/FAIL as though they were the same task.

Review findings:
- body-frame command/body_vx is coherent with the canonical reset because frozen
  home key 0 has identity quaternion: initial forward/left are world +x/+y.
  Validation now checks this explicitly, so the world-x progress and world-y
  lateral guardrails cannot silently become frame-inconsistent;
- canonical model validation also re-runs the direct-torque joint/actuator
  boundary rather than relying only on the physical fingerprint;
- RL and MJPC intentionally retain different information budgets and feedback
  rates. This is acceptable for an integration anchor, but cannot support a fair
  controller ranking;
- both remain offline_unbounded; observed MJPC planning time already rules out
  interpreting this anchor as a 20 ms real-time result;
- authorization remains fail-closed: the prepared anchor itself authorizes zero
  physics steps and zero scientific attempts.

The review does not authorize capture. A separate exact-commit capture task must
still define one bounded attempt per controller, raw evidence paths, controller
diagnostics, independent CanonicalEvaluator replay, and explicit physics-step
authorization before mj_step may be called.
