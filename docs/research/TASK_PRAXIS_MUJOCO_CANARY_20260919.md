# Praxis central-runtime MuJoCo canary — 2026-09-19

Mode: infrastructure

## Question

Can the Go2 repository, after migration to the central Praxis runtime, complete
one real trusted MuJoCo/DDS host execution through the existing project adapter,
with Luna preparation/analysis separated from the live launch and the result
pushed back through the trusted closeout path?

## Exact parent/base

- `main@1b2cbfe39d95464cea4d9b5eaf8a7627e8ac290a`
- No controller, simulator, scene, threshold, or scientific-policy change is authorized.
- This run is infrastructure evidence only and must not be interpreted as a
  locomotion research result.

## Frozen execution

Use the existing low-stress straight-trot path. Luna may perform deterministic
offline inspection/build/readiness checks but must not launch MuJoCo or DDS.
Do not modify the frozen manifest.

<!-- ATLAS_HOST_EXPERIMENT
{"schema_version":1,"command":["bash","example/cpp/scripts/run_trot.sh","60","_runs/praxis_mujoco_canary_20260919_r1","--controller-duration","20","--period","0.60","--duty","0.75","--foot-lift","0.020","--kp","63","--kd","2.8","--kernel","raibert-trot","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--wbc-primary","--step-length","0.050","--max-cycles","6","--headless","--domain-id","212"],"domain_id":212,"run_dir":"example/cpp/experiments/_runs/praxis_mujoco_canary_20260919_r1","timeout_s":90,"environment":{}}
ATLAS_HOST_EXPERIMENT -->

## Acceptance

After trusted host execution, write only
`docs/validation/praxis_mujoco_canary_20260919/RESULTS.md` with:

- whether the central Praxis dispatcher reached the project adapter;
- candidate commit presented to the host;
- whether the host launch occurred;
- host return code;
- whether the declared run directory contains immutable evidence;
- whether the MuJoCo/controller run completed without runner-level failure;
- whether this validates Go2 as usable through the central Praxis runtime.

Keep FACTS, derived checks, and interpretation separate. Do not rerun the host
experiment after scientific/live capture starts.
