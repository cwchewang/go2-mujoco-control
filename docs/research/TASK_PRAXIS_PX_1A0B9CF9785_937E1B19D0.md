# Praxis Task px_1a0b9cf9785_937e1b19d0

Mode: `infrastructure`
Project: `go2-mujoco-control`
Repository: `cwchewang/go2-mujoco-control`
Capability: `go2-mujoco-live`

## Objective

Verify that one typed go2-mujoco-live capability request submitted through the Praxis Control Plane crosses the existing trusted Go2 MuJoCo/DDS host boundary and closes out successfully.

## Instructions

- Treat this only as typed-capability infrastructure acceptance, not a locomotion research result.
- Inspect the frozen TaskSpec and the compiled legacy host block before host execution.
- Do not modify controller, simulator, gait, scene, host command, or scientific parameters.
- Write only docs/validation/praxis_typed_go2_live_canary_20260919/RESULTS.md during analysis.

## Constraints

- Exactly one trusted host invocation is authorized.
- No parameter sweep, tuning retry, alternate domain, or replacement live run.
- Do not modify .github/ or tools/atlas_*.
- Do not rewrite sealed raw evidence or trusted host facts.

## Allowed mutations

- docs/validation/praxis_typed_go2_live_canary_20260919/

## Frozen parameters

```json
{
  "dogfood_kind": "typed-go2-capability-v0",
  "expected_capability": "go2-mujoco-live",
  "expected_legacy_marker": "ATLAS_HOST_EXPERIMENT"
}
```

## Resource budget

```json
{
  "cpu_slots": 1,
  "gpu_count": 0,
  "memory_gb": null,
  "wall_time_seconds": 1200
}
```

## Attempt policy

```json
{
  "max_scientific_attempts": 1,
  "retry_preflight": true,
  "scientific_boundary": "first trusted host launch recorded by the Go2 adapter"
}
```

## Required evidence

- exact frozen task commit and candidate commit
- compiled ATLAS_HOST_EXPERIMENT manifest matching the typed capability_request
- trusted host record and immutable run evidence hashes
- DDS readiness and controller handoff
- host return code and timeout status
- final trusted result push

## Stop rule

Stop without replacement live execution if the typed request cannot be compiled exactly, preflight fails, or the one trusted host invocation completes or fails after launch.

## Closeout schema

- TYPED REQUEST FACTS
- TRUSTED HOST FACTS
- TRANSPORT COMPILATION
- INFRASTRUCTURE ACCEPTANCE
- LIMITATIONS

## Frozen TaskSpec

The following machine-readable block is the canonical task request.

```json
{
  "allowed_mutations": [
    "docs/validation/praxis_typed_go2_live_canary_20260919/"
  ],
  "attempt_policy": {
    "max_scientific_attempts": 1,
    "retry_preflight": true,
    "scientific_boundary": "first trusted host launch recorded by the Go2 adapter"
  },
  "capability": "go2-mujoco-live",
  "capability_request": {
    "command": [
      "bash",
      "example/cpp/scripts/run_trot_exact_source.sh",
      "45",
      "_runs/praxis_typed_go2_live_canary_20260919_r1",
      "--controller-duration",
      "15",
      "--kernel",
      "raibert-trot",
      "--period",
      "0.60",
      "--duty",
      "0.75",
      "--step-length",
      "0.091",
      "--foot-lift",
      "0.020",
      "--kp",
      "63",
      "--kd",
      "2.8",
      "--raibert-velocity-gain",
      "0.05",
      "--raibert-max-adjustment",
      "0.010",
      "--world-feedback-max",
      "0.060",
      "--world-feedback-slew",
      "0.004",
      "--clean-baseline",
      "--tau-limit",
      "35",
      "--max-cycles",
      "6",
      "--headless",
      "--domain-id",
      "219"
    ],
    "domain_id": 219,
    "environment": {},
    "run_dir": "example/cpp/experiments/_runs/praxis_typed_go2_live_canary_20260919_r1",
    "schema_version": 1,
    "timeout_s": 300
  },
  "closeout_schema": [
    "TYPED REQUEST FACTS",
    "TRUSTED HOST FACTS",
    "TRANSPORT COMPILATION",
    "INFRASTRUCTURE ACCEPTANCE",
    "LIMITATIONS"
  ],
  "constraints": [
    "Exactly one trusted host invocation is authorized.",
    "No parameter sweep, tuning retry, alternate domain, or replacement live run.",
    "Do not modify .github/ or tools/atlas_*.",
    "Do not rewrite sealed raw evidence or trusted host facts."
  ],
  "frozen_parameters": {
    "dogfood_kind": "typed-go2-capability-v0",
    "expected_capability": "go2-mujoco-live",
    "expected_legacy_marker": "ATLAS_HOST_EXPERIMENT"
  },
  "instructions": [
    "Treat this only as typed-capability infrastructure acceptance, not a locomotion research result.",
    "Inspect the frozen TaskSpec and the compiled legacy host block before host execution.",
    "Do not modify controller, simulator, gait, scene, host command, or scientific parameters.",
    "Write only docs/validation/praxis_typed_go2_live_canary_20260919/RESULTS.md during analysis."
  ],
  "mode": "infrastructure",
  "objective": "Verify that one typed go2-mujoco-live capability request submitted through the Praxis Control Plane crosses the existing trusted Go2 MuJoCo/DDS host boundary and closes out successfully.",
  "project": {
    "profile_path": ".atlas/project.json",
    "project_id": "go2-mujoco-control",
    "repository": "cwchewang/go2-mujoco-control"
  },
  "required_evidence": [
    "exact frozen task commit and candidate commit",
    "compiled ATLAS_HOST_EXPERIMENT manifest matching the typed capability_request",
    "trusted host record and immutable run evidence hashes",
    "DDS readiness and controller handoff",
    "host return code and timeout status",
    "final trusted result push"
  ],
  "resources": {
    "cpu_slots": 1,
    "gpu_count": 0,
    "memory_gb": null,
    "wall_time_seconds": 1200
  },
  "schema_version": 1,
  "stop_rule": "Stop without replacement live execution if the typed request cannot be compiled exactly, preflight fails, or the one trusted host invocation completes or fails after launch."
}
```

<!-- PRAXIS_CAPABILITY_REQUEST
{"command":["bash","example/cpp/scripts/run_trot_exact_source.sh","45","_runs/praxis_typed_go2_live_canary_20260919_r1","--controller-duration","15","--kernel","raibert-trot","--period","0.60","--duty","0.75","--step-length","0.091","--foot-lift","0.020","--kp","63","--kd","2.8","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--clean-baseline","--tau-limit","35","--max-cycles","6","--headless","--domain-id","219"],"domain_id":219,"environment":{},"run_dir":"example/cpp/experiments/_runs/praxis_typed_go2_live_canary_20260919_r1","schema_version":1,"timeout_s":300}
PRAXIS_CAPABILITY_REQUEST -->

<!-- ATLAS_HOST_EXPERIMENT
{"command":["bash","example/cpp/scripts/run_trot_exact_source.sh","45","_runs/praxis_typed_go2_live_canary_20260919_r1","--controller-duration","15","--kernel","raibert-trot","--period","0.60","--duty","0.75","--step-length","0.091","--foot-lift","0.020","--kp","63","--kd","2.8","--raibert-velocity-gain","0.05","--raibert-max-adjustment","0.010","--world-feedback-max","0.060","--world-feedback-slew","0.004","--clean-baseline","--tau-limit","35","--max-cycles","6","--headless","--domain-id","219"],"domain_id":219,"environment":{},"run_dir":"example/cpp/experiments/_runs/praxis_typed_go2_live_canary_20260919_r1","schema_version":1,"timeout_s":300}
ATLAS_HOST_EXPERIMENT -->
