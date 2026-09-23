# Shared transfer combination v1

## Decision and question

This campaign decides whether the already source-aligned 1.0 m/s flat capability
survives deployment with Praxis's shared Go2 model, shared home pose, ten-step
startup, and shared `FrozenPolicy` adapter together. The sealed ten-case source
baseline is the comparison: its source reference and adapter trajectories match,
and its model-only and home-only cases each pass, but no case has tested their
full combination. Repeating the source arm would spend an attempt without
isolating the untested interaction.

The falsifier is a performance failure, safety stop, or repeat-integrity failure
in either of the two predeclared combined-condition episodes. A performance
failure means this deployment combination misses the frozen 1.0 m/s flat gates.
A safety stop means the task cannot receive a performance verdict under its
safety semantics. A repeat-integrity failure means the two episodes did not
reproduce the same recorded control/state trace.

## Frozen condition

The machine-readable definition is
[`rl_shared_transfer_combination_v1.json`](../../tools/substrate/protocols/rl_shared_transfer_combination_v1.json).
Both episodes use:

- Scene `unitree_robots/go2/phase2_flat.xml`.
- Shared home qpos: base `[0, 0, 0.27]`, identity quaternion, and each leg
  `[0, 0.9, -1.8]`; MjData-default zero velocity, with no active-state
  `mj_forward` before stepping.
- Existing ten-step startup: 10 MuJoCo steps at 0.002 s with the baseline
  runner's fixed PD hold target `[0.1, 0.8, -1.5, -0.1, 0.8, -1.5, 0.1, 1.0,
  -1.5, -0.1, 1.0, -1.5]`; first policy inference at tick 10, then every 10
  physics ticks.
- The existing shared `FrozenPolicy` observation/action adapter and the pinned
  CTS source commit `30e74dc507bec7a642a8c98be26081f2c6f0822d`; checkpoint
  `go2_moe_cts_high_slope_thre_164k_0.6715.pt`, SHA-256
  `9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d`.
- Constant `[1.0, 0.0, 0.0]` m/s forward command for 6000 physics ticks (12 s).
  Measure body-forward speed over ticks `[1000, 6000)`; lateral drift and yaw
  use the whole episode.
- Two fresh episodes with the same condition and seed 0. The second depends on
  the first passing and must match its qpos, qvel, target, and applied-control
  trace hash exactly. Budget is two attempts; stop at the first non-pass and do
  not retry. An initial safety stop before the first control sample creates no
  consumed attempt, following the existing runner's accounting boundary.

The acceptance gates reuse the sealed 1.0 m/s flat source gates: mean body-forward
speed at least 0.8 m/s, MAE at most 0.2 m/s (`max(0.05, 0.2 × command)`), maximum
lateral drift at most 0.3 m, and maximum absolute yaw change at most 0.3 rad.
These are the existing reference gates, not thresholds selected from a new
outcome. CPU inference uses one Torch intra-op and inter-op thread,
deterministic Torch algorithms, evaluation/inference mode, and seed 0; the
baseline qualification binds the remaining runtime and native dependencies.

Either missing-data safety condition (nonfinite state/control, invalid
orientation, physics warning, base-terrain contact, tilt above 1.2 rad, base
clearance below 0.06 m, or lateral position beyond 1.5 m) stops the episode.
Foot-ground contacts are expected and recorded; base-terrain contact is a safety
stop, not a performance failure or a claim of falling.

## Interpretation boundary

A PASS establishes that this complete, pinned deployment combination met the
source 1.0 m/s flat gates in two identical deterministic episodes. It does not
estimate a success probability. A performance FAIL establishes that this
combination failed at least one frozen gate in this setup; a safety stop or
integrity stop limits the claim as described above. Neither PASS nor FAIL
identifies which combined factor caused the outcome, establishes low-speed or
terrain capability, generalizes to other checkpoints or hardware, or explains
the sealed 0.15 m/s failure. Repeated identical traces establish repeatability,
not independent statistical evidence.

Preparation and formal capture are separate. A later exact-HEAD qualification
and real zero-step preparation may produce `READY_AWAITING_START`; only a
separate explicit authorization may start this campaign. This document grants
no capture permission.
