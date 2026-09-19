# Praxis Go2 MuJoCo live canary R1 — 2026-09-19

Mode: infrastructure / one trusted host-live canary

## Objective

Verify that the already-passed central Praxis -> Go2 adapter path can cross the
trusted host boundary once and complete one short Go2 MuJoCo/DDS run from the
exact task candidate.

This is infrastructure acceptance, not a locomotion research result. Do not use
this run to claim controller quality, repeatability, terrain capability, or a
scientific comparison.

## Exact base

- main parent: `d2b6a8fb7a22961a5a8ae0aacbeabe4177d536bb`
- passed no-host adapter result:
  `d7630e403afebdd65bf6595e042d96fc4bed61c7`

## Frozen live command

Use the maintained exact-source wrapper and the canonical clean-baseline path.
The live command is frozen in the manifest below.

The short gait settings are deliberately low-speed and derived from the already
accepted flat clean-baseline regime. They are not a new scientific test.

Luna may, before host execution:

- inspect the exact task/base/SOP;
- verify the canonical Praxis anchor and explicit task/state paths;
- run syntax, unit, build, dependency, and other no-live readiness checks;
- inspect whether the standard per-user MuJoCo SDK expected by
  `run_trot_exact_source.sh` is present;
- veto live if any required dependency, binary build, DDS precondition, or
  provenance condition is not satisfied.

Luna must not launch MuJoCo, DDS, simulator/controller processes, or any live
capture from the sandbox. Do not alter controller/simulator/scientific source,
gait parameters, scene, safety limits, or the frozen host manifest.

## Attempt rule

The trusted host wrapper may invoke the frozen command at most once.

A build/dependency/launch failure before valid controller handoff is an
infrastructure/prelaunch failure. Do not replace it with another live command,
domain, or tuned parameter set in this task.

## Acceptance evidence

After the trusted host phase, determine from the trusted host record and sealed
run directory:

- exact candidate commit;
- whether the host command was launched;
- host return code / timeout / error;
- whether simulator DDS readiness and controller handoff occurred;
- whether the requested short run reached a controlled stop;
- hashes/provenance of the exact-source simulator/controller outputs and raw
  run evidence;
- whether any hard/emergency safety rejection occurred;
- whether the central Praxis -> Go2 adapter -> trusted host -> same Luna
  analysis -> trusted push chain completed.

Do not convert these checks into a locomotion performance claim.

## Closeout

Write only:

`docs/validation/praxis_go2_live_canary_r1_20260919/RESULTS.md`

Separate:

1. TRUSTED HOST FACTS
2. DERIVED EXECUTION CHECKS
3. INFRASTRUCTURE ACCEPTANCE
4. REMAINING LIMITATIONS

Use one infrastructure classification:

- `PRAXIS_GO2_LIVE_PATH_READY`
- `PRAXIS_GO2_PRELAUNCH_FAILURE`
- `PRAXIS_GO2_HOST_EXECUTION_FAILURE`

<!-- ATLAS_HOST_EXPERIMENT
{"schema_version":1,"command":["bash","example/cpp/scripts/run_trot_exact_source.sh","45","_runs/praxis_go2_live_canary_r1_20260919","--controller-duration","15","--kernel","raibert-trot","--period","0.60","--duty","0.75","--step-length","0.091","--foot-lift","0.020","--kp","63","--kd","2.8","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--clean-baseline","--tau-limit","35","--max-cycles","6","--headless","--domain-id","218"],"domain_id":218,"run_dir":"example/cpp/experiments/_runs/praxis_go2_live_canary_r1_20260919","timeout_s":300,"environment":{}}
ATLAS_HOST_EXPERIMENT -->
