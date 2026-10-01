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


## Exact review identity and no-physics re-preflight

- review code commit: d988c6cf357dcc32123d7b199525b8bae10acd04
- anchor protocol SHA-256:
  0d0e0061c3552ae0faf3f9b64d006054d8205f26901398ab0b160cbb9b4d900b
- canonical physical fingerprint:
  1c7ec61af1297fe1715e3d412481709bf4ad3ad42196e483c444d1a54db73e94
- canonical home base pose:
  [0.0, 0.0, 0.27, 1.0, 0.0, 0.0, 0.0]
- RL checkpoint SHA-256:
  9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d
- MJPC source commit:
  e00c47a5adb9856af2e0f24231bb3a60d5be23c4
- sealed native MJPC binary SHA-256:
  9dd19fcff9f67d4bf0dc8638b31b9c35bf493a9b545f682d13d181c3c34e7a33
- physics_step_authorized: false
- scientific_attempts_authorized: 0

The exact-code re-preflight compiled the model but did not create a simulation
trajectory, load the Torch policy, start the MJPC controller process, or call
mj_step.
