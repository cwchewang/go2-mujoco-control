# Aligned flat anchor v1 — first bounded capture — 2026-10-01

Goal: execute the reviewed 1 s shared engineering anchor once for the frozen RL
controller and once for the pinned native MJPC controller through the same
canonical MuJoCo plant, TaskSpec, action resolution and CanonicalEvaluator.

Authorization for this task only:
- physics_step_authorized = true;
- engineering attempts: RL = 1, MJPC = 1;
- scientific attempts = 0;
- retry = none;
- controller order = RL then MJPC;
- maximum 500 physics steps per controller;
- exact capture commit must be supplied by the execution task and match clean HEAD.

Evidence requirements:
- create a fresh ignored run directory; never overwrite;
- persist started metadata before execution;
- persist an attempt ledger entry before the first plant step of each controller;
- append every raw row to JSONL before advancing to the next physics step;
- save controller diagnostics, target and resolved torque evidence;
- replay each raw JSONL independently through CanonicalEvaluator;
- save result and SHA-256 for each raw member;
- report failures as captured results; never tune or retry.

Interpretation:
This is the first shared closed-loop engineering integration capture. Its broad
1 s guardrails are not the sealed #189 performance task and cannot rank RL vs
MJPC. Different information and timing regimes remain explicit. No real-time,
scientific bottleneck or paper claim follows from this capture.
