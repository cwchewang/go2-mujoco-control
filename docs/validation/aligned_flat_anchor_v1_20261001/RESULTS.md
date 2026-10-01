# Aligned flat anchor v1 — preparation closeout

Status: PREPARED / NOT_RUN.
Scientific attempts: 0.
Canonical physics steps: 0.

## Exact preparation identity

- preparation code commit:
  43f574044ecebdfcfffd68a88e4a93eb6399c1f2
- protocol:
  tools/substrate/protocols/aligned_flat_anchor_v1.json
- protocol SHA-256:
  0d0e0061c3552ae0faf3f9b64d006054d8205f26901398ab0b160cbb9b4d900b
- canonical scene:
  unitree_robots/go2/phase2_flat.xml
- compiled physical fingerprint:
  1c7ec61af1297fe1715e3d412481709bf4ad3ad42196e483c444d1a54db73e94
- canonical dt: 0.002 s
- physics_step_authorized: false
- scientific_attempts_authorized: 0
- independent review required: true

## Controller identities

RL:
- source commit:
  30e74dc507bec7a642a8c98be26081f2c6f0822d
- checkpoint SHA-256:
  9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d
- adapter: ProprioceptivePolicyAdapter
- information: proprioceptive, model_access=none
- timing: physics 2 ms, policy/feedback 20 ms, offline_unbounded

MJPC:
- source commit:
  e00c47a5adb9856af2e0f24231bb3a60d5be23c4
- verified local sealed binary SHA-256:
  9dd19fcff9f67d4bf0dc8638b31b9c35bf493a9b545f682d13d181c3c34e7a33
- process protocol: 3
- adapter: PositionTargetControllerAdapter
- compatibility correction: private_model_mjBIAS_AFFINE
- information: whole_body_state, model_access=controller_model
- timing: physics 2 ms, replanning 20 ms, prospective feedback 2 ms,
  offline_unbounded

The binary hash is preflight evidence for this Atlas preparation, not a portable
artifact identity. A future capture must re-verify the sealed binary against its
exact capture checkout.

## Frozen shared task

- id: aligned-flat-forward-integration-v1
- command: [1.0, 0.0, 0.0]
- command frame: body
- longitudinal metric: body_vx
- horizon: 500 ticks / 1.0 s
- zero command: 50 ticks
- ramp: 100 ticks
- measurement start: tick 250
- support semantics: traverse
- no scenario intervention

Guardrails are deliberately loose integration criteria and must not be used to
rank RL vs MJPC.

## Preflight performed

On the exact preparation commit:
- anchor JSON loaded through the fail-closed validator;
- compiled canonical model fingerprint and timestep matched;
- actual RL checkpoint bytes matched the frozen SHA;
- sealed MJPC binary identity and pinned source commit matched;
- authorization flags remained false / zero;
- Torch policy inference was not loaded;
- the native MJPC controller process was not started;
- no mjData was used for simulation and no mj_step was called.

Before the preparation commit:
- Ruff passed;
- 101 Python substrate/reliability/launch tests passed;
- 10 native MuJoCo no-step identity/boundary tests passed;
- compileall and git diff --check passed.

## Decision

The anchor is sufficiently specified for independent review, but execution is
NOT_RUN and unauthorized. The next action is review of task thresholds, frame
semantics, controller information/timing differences, and evidence requirements.
Only a later, separately authorized capture task may consume canonical physics
steps.

No locomotion result, performance comparison, real-time result, controller
ranking, cross-controller bottleneck, or paper gap follows from this preparation.
