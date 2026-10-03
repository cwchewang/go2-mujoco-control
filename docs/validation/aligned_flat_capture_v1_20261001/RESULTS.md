# Aligned flat capture v1 — closeout

Status: CAPTURE FAILED / INFRASTRUCTURE STOP.
Engineering attempts consumed: RL 1/1, MJPC 1/1. Retry: none.
Scientific attempts: 0.

## Exact identity

- capture HEAD: 2411c4af1f8ab95e50f7e07e672466b5c0abb406
- raw run: example/cpp/experiments/_runs/aligned_flat_capture_v1/run_001
- sealed run manifest SHA-256:
  12e6dba7b06dd6eda8caa667c017fa09faf247eb894612bfaca61eaa593c026c
- anchor SHA-256:
  0d0e0061c3552ae0faf3f9b64d006054d8205f26901398ab0b160cbb9b4d900b
- both immutable ledger claims exist at the first post-handoff state/control sample.

## RL arm

RL completed the full 500 canonical physics steps / 501 frames and independent
CanonicalEvaluator replay returned PASS under the broad 1 s engineering anchor:
progress 0.6125663634 m, body-vx MAE 0.1523337194 m/s, 50 controller updates,
no physical failure, terminal reason horizon.

This is not the sealed #189 flat-reference task and is not a controller-ranking
result.

## MJPC arm

The MJPC arm consumed its single attempt and produced 140 raw frames (ticks
0..139), corresponding to 140 canonical physics steps before the tick-140
controller update failed. The last preserved canonical state at t=0.278 s had
x=-0.003654 m, y=0.002433 m, height=0.337926 m and tilt=0.135614 rad; no physical
failure had been classified. Fourteen replans had completed successfully;
planning p50 was 0.028089 s and max was 0.038878 s. Nine per-motor torque
saturation events were recorded descriptively.

At the tick-140 replan the Python IPC layer raised:
ValueError: native MJPC emitted invalid JSON

The adjacent host MuJoCo log, preserved unchanged here, records:
ERROR: no group 0 geom detected by raycast

Its SHA-256 is:
58f730a745d4d2ae46c7fdc4c5bfca3e68c6c2f9d69a4c6627245ae62420d602

Pinned source shows mjpc::Ground emits this MuJoCo error only when its downward
raycast finds no group-0 geometry. The source task does contain a group-0 infinite
floor. Therefore the direct runtime evidence supports an internal MJPC
planning-model/rollout failure during replan, while the strict stdout JSON channel
also converted native diagnostic/error text into an IPC parse failure. The exact
non-JSON stdout line was not persisted, so the closeout does not claim its exact
text.

This is not classified as an MJPC locomotion PERFORMANCE_FAIL: the arm did not
reach a canonical terminal verdict and stopped at an infrastructure/planning
boundary.

## Decision

The first shared closed-loop physics has now genuinely executed. RL has one
complete broad-anchor PASS. MJPC has one consumed partial capture ending in an
infrastructure/planning stop. The cross-controller integration comparison is
INCOMPLETE and supports no ranking, bottleneck or paper claim.

v1 is permanently closed; neither arm may be retried. Next work is offline/zero-
physics diagnosis and IPC/planner-boundary hardening, followed by a separately
versioned v2 preparation. Any v2 live physics requires a new exact-head review
and a new explicit user START authorization.
