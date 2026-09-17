# Phase2 known-step FL execution-chain audit

Mode: `exploratory` offline evidence audit  
SOP: `main/docs/research/SOP.md` v0.2  
Exact parent/base: `e3fa66ce17c39db65010e68c0dc7a30743382484`  
Branch: `research/phase2-known-step-v2-c-continuation-20260915`

## Question

For the first planning-valid FL V2 crossing in the already-consumed C capture, where is the earliest execution-layer divergence between the commanded world-foot trajectory and the actual foot trajectory: target/IK mapping, joint tracking/actuation, WBC/feedforward interaction, or obstacle contact?

## Scope

Use only the existing immutable A/C evidence and source corresponding to the captured runtime. Do not run any live simulation, replay that changes evidence, retry A/C, modify runtime code, tune parameters, or change the existing checkpoint classification.

Analyze only the first planning-valid FL crossing, from its latch at state time 14.254 s through touchdown / before the next FL swing.

Reconstruct the source-grounded chain:

`V2 world target/velocity -> IK -> joint q/dq targets -> motor kp/kd/tau_ff -> actual q/dq/tau_est -> FK(actual) foot pose -> contact`.

## Required audit

1. Find the earliest timestamp where commanded-vs-actual FL foot tracking begins to diverge materially. Report command x/z and vx/vz, actual x/z, and foot force/contact.
2. At that point and around edge contact, report the three FL joints' target q/dq, actual q/dq, target error, kp/kd/tau_ff, tau_est/effective torque, and any position/velocity/torque/rate-limit state available in the capture.
3. Reconstruct FK from the recorded joint targets using the frozen runtime kinematics. Compare `FK(target)` with the V2 commanded world-foot target:
   - if FK(target) already disagrees, localize to target/IK/mapping;
   - if FK(target) agrees while FK(actual) diverges, localize downstream.
4. Inspect 20-40 ms before and after first obstacle-edge contact. Determine whether the actual foot was already substantially below command before contact, or tracked acceptably until contact and was then blocked.
5. Check whether WBC/feedforward logic actually changes the FL motor command over the decisive interval; distinguish diagnostics from commands that reach LowCmd.
6. Classify the execution-layer blocker using exactly one of:
   - `IK_OR_TARGET_MAPPING`
   - `JOINT_TRACKING_LIMIT`
   - `TORQUE_OR_RATE_LIMIT`
   - `CONTACT_BLOCKAGE`
   - `WBC_OR_FEEDFORWARD_INTERFERENCE`
   - `MULTI_FACTOR`
   - `INSUFFICIENT_EVIDENCE`

Do not infer a mechanism from label names alone; give the earliest source/evidence propagation chain.

## Decision boundary

This is a localization audit, not a new scientific run. The existing checkpoint primary classification remains `PLANNING_GEOMETRY_FAILED`.

End with one next-intervention layer only: target/IK, joint tracking/actuation, WBC/feedforward integration, or contact handling. Do not propose parameter values, sweeps, planner recovery changes, or a combined fix.

## Closeout

Append the audit to the existing checkpoint `RESULTS.md` and `analysis.json`; update `provenance.csv` only if new conclusion-critical source/artifact identities must be recorded. Preserve raw `_runs` byte-for-byte.

Commit and push the branch. Report only the commit SHA after push; Sol will read the closeout from GitHub.
