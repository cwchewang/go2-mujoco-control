# Phase2 checkpoint: known-step edge-aware V2 protocol repair

Date: 2026-09-15
Prepared branch: `research/phase2-known-step-edge-aware-v2-protocol-repair-20260915`
Exact parent closeout: `11e79eaba861d0e4fd26fdbaf4e9ec5f2caaacb6`
Failed V2 runtime HEAD recorded by parent: `be1e9acca1c6650be7d500e1e3fb63dcd5594826`

Read `docs/research/PHASE1_AGENT_CONTRACT.md`, `docs/research/TASK_PHASE2_KNOWN_STEP_EDGE_AWARE_V2_20260915.md`, and the parent V2 closeout before editing or running anything. This task is authoritative for this checkpoint.

## 1. Purpose

The previous V2 checkpoint did **not** produce a scientific controller result. Its only authorized C/domain 233 launch aborted before DDS bridge readiness, produced no controller `data.csv`, and was correctly closed as `PROTOCOL_FAILURE` without retry.

The observed root cause is protocol-only: `example/cpp/scripts/run_trot.sh` allowed DDS domain 233 even though CycloneDDS reported the resulting UDP port numbers out of range. The scientific V2 planner, controller, scene, gait, WBC/MPC/ID, body references, safety limits, and traversal criteria were therefore never evaluated by live data.

This checkpoint repairs only that protocol error and executes exactly one fresh V2 C capture in a new run directory.

## 2. Scientific intervention is frozen

The V2 scientific question, implementation semantics, diagnostics, geometry, classification precedence, and full-traversal criteria remain exactly those in `TASK_PHASE2_KNOWN_STEP_EDGE_AWARE_V2_20260915.md`.

The runtime-affecting controller/V2 implementation is frozen to the implementation used by the failed launch, whose metadata recorded git HEAD:

`be1e9acca1c6650be7d500e1e3fb63dcd5594826`

This checkpoint must not change any controller/C++/MuJoCo scene behavior relative to that V2 implementation. In particular, do not change:

- edge-aware latch logic;
- C1 corridor position or velocity math;
- touchdown x/y/z rules;
- V2 telemetry semantics;
- speed policy, period, duty, gait phase, step length, base foot lift;
- Raibert gains or max adjustment;
- WBC, SRBD MPC, ID-WBC, contact scheduling/merge logic;
- body-height/pitch/roll references;
- motor kp/kd/tau_ff policy or torque limit;
- D4/D90/PD pulse state;
- scene/collision geometry;
- safety thresholds;
- A/V1-B immutable raw captures;
- any V2 analysis threshold or classification criterion.

Allowed implementation changes are protocol/tooling only: DDS-domain validation, the protocol-repair runner, analyzer domain/path/text bookkeeping, protocol tests, task/results/provenance artifacts.

## 3. DDS protocol repair

The old runner used domain 233. The parent evidence shows this value passed `run_trot.sh` preflight but CycloneDDS aborted before DDS readiness with a port-out-of-range error.

For this checkpoint:

- use **DDS domain 230**;
- use only `example/cpp/scripts/run_phase2_known_step_edge_aware_v2_protocol_repair.sh` for the live launch;
- repair `example/cpp/scripts/run_trot.sh` so its accepted DDS-domain range ends at **232**, not 233;
- the error message must state the same `[0,232]` range;
- add/record a no-process preflight check showing 233 is rejected by the repaired validation before any simulator/controller launch;
- verify 230 is accepted by the repaired validation;
- update `analyze_phase2_known_step_edge_aware_v2.py` only as needed so the expected C domain is 230 and all machine-readable/text labels describe the actual protocol-repair C run rather than hard-coding domain 233.

Do not turn this into a generalized DDS refactor. The smallest auditable repair is preferred.

## 4. Run matrix

Frozen comparison captures, read-only:

A:
`/home/che/dev/go2-workspace/phase2-known-step-wallclock-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`

V1 B:
`/home/che/dev/go2-workspace/phase2-known-step-b-only-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_b_only_20260915/B`

Parent failed V2 C, evidence only and never overwritten:
`/home/che/dev/go2-workspace/phase2-known-step-edge-aware-v2-20260915/example/cpp/experiments/_runs/phase2_known_step_edge_aware_v2_20260915/C`

Exactly one new live run is authorized in this checkpoint:

C:
`example/cpp/experiments/_runs/phase2_known_step_edge_aware_v2_protocol_repair_20260915/C`

DDS domain: `230`.

The parent failed launch does not authorize an in-place retry and its directory must remain immutable. This task creates a new checkpoint/run directory. Within this checkpoint there is exactly one C launch. No retry, replacement domain, second C, A rerun, V1-B rerun, GUI replay, sweep, or follow-up live experiment is authorized.

## 5. Pre-live gates

Before C:

1. verify exact branch and clean worktree;
2. verify the parent failed C evidence and SHA are present and unchanged;
3. prove the scientific V2/controller source diff versus the failed runtime implementation is empty; only the protocol/tooling allowlist may differ;
4. repair and test DDS-domain validation: 233 rejected without process launch, 230 accepted;
5. run syntax/help checks for the analyzer and runner;
6. run the focused V2 tests from the original task;
7. run controller full CTest;
8. run motion-clock integration test;
9. run simulator `test_lockstep` and simulator full CTest;
10. verify A and V1-B frozen raw hashes still match accepted provenance;
11. verify scene hash is unchanged;
12. commit all protocol/tooling changes and record the exact pre-run HEAD;
13. working tree must be clean before C.

Any failed pre-live gate stops the checkpoint. Do not launch C after a gate failure.

## 6. Live C protocol

Run exactly once using:

`example/cpp/scripts/run_phase2_known_step_edge_aware_v2_protocol_repair.sh`

The runner is frozen to the original V2 plant/scene/arguments and only changes the output directory and DDS domain to 230.

Required runtime protocol remains:

- `SIM_LOCKSTEP=1`;
- paired HighState enabled;
- bridge atomic record enabled;
- V2 ON;
- V1 OFF;
- D4/D90/PD pulse OFF;
- same 5 cm scene and frozen controller arguments;
- no live manual intervention.

If C aborts before usable capture or a protocol gate fails, classify `PROTOCOL_FAILURE` and stop. No retry.

## 7. Analysis

Use the existing V2 analyzer with only protocol-repair bookkeeping changes. Preserve all original V2 logic:

- exact A/C preactivation equality;
- V2 planning/isolation gates;
- C1 corridor and analytic velocity checks;
- command-vs-actual front-leg tracking diagnostics;
- original raised-platform contact definition;
- original full-traversal criteria;
- original classification precedence.

Do not change thresholds after seeing C.

Primary labels remain exactly:

1. `PROTOCOL_FAILURE`
2. `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`
3. `PLANNING_GEOMETRY_FAILED`
4. `SUPPORTED_ENABLES_TRAVERSAL_V2`
5. `TRACKING_LIMITED`
6. `FRONT_PAIR_ESTABLISHED_BUT_COORDINATION_FAILED`
7. `OTHER_CONTROL_LIMIT_IDENTIFIED`
8. `INSUFFICIENT_EVIDENCE`

## 8. Required closeout

Write results under:

`docs/validation/phase2_known_step_edge_aware_v2_protocol_repair_20260915/`

At minimum preserve the original V2 output set:

- `RESULTS.md`
- `analysis.json`
- `preactivation_exact.csv`
- `planning_isolation.csv`
- `front_crossing_summary.csv`
- `edge_tracking_timeline.csv`
- `touchdown_summary.csv`
- `protocol_gates.csv`
- `body_contact_chronology.csv`
- `provenance.csv`

Also record pre-live test results and the DDS validation repair evidence, including proof that domain 233 is rejected before launch and domain 230 is the only authorized live domain.

Commit and push the closeout, then stop. Do not merge, tune V2, change speed/gait/control, or start another experiment.
