# Phase2 known-step V2 IK-map canary

Mode: `confirmatory`  
SOP: `main/docs/research/SOP.md` v0.2  
Exact parent/base: `0f8a0109dc56a2dabad600aacee71c7d99bd6a46`  
Branch: `research/phase2-known-step-v2-ik-map-canary-20260917`

## Question

Does removing the parent audit's earliest execution-layer mismatch — the fixed body-frame workspace clamp changing an otherwise valid V2 swing target before IK — restore target fidelity for the first FL crossing, and if so is the remaining blocker downstream joint tracking/contact rather than target/IK mapping?

## Frozen parent evidence

The parent offline audit localized the earliest execution-layer boundary to:

`V2 world target -> WorldToBody -> ClampFootToHipWorkspace -> IK`

At the first valid FL latch (14.254 s), `FK(q_target)` already differed materially from the requested V2 world target before obstacle contact. The first crossing command itself was geometrically valid. Raw parent evidence remains immutable.

## No-live feasibility gate

Before modifying runtime code, use only the existing parent C capture and frozen source to reconstruct the requested, **unclamped** FL body-frame target for every sample from the first valid FL latch at 14.254 s through its first touchdown at 14.404 s.

For every reconstructed sample:

1. `LegInverseKinematics(FL, p_body_raw)` must succeed without modifying `p_body_raw`.
2. The resulting joint target must lie within the simulator's Go2 joint ranges from `unitree_robots/go2/go2.xml`:
   - abduction: `[-1.0472, 1.0472]` rad
   - front thigh: `[-1.5708, 3.4907]` rad
   - knee: `[-2.7227, -0.83776]` rad
3. Reapplying frozen FK to that IK result must reproduce `p_body_raw` to <= `1e-6 m` per axis.

If any sample fails this gate, **do not modify runtime code and do not launch a live run**. Close out as `DIRECT_V2_TARGET_INFEASIBLE`, report the earliest failing state time, requested body/world target, IK result/failure and violated joint range, then stop.

## Scientific change if the gate passes

Change only the target/IK mapping for a V2 swing sample where `crossing_latched && planning_valid`:

- compute `p_body_raw = WorldToBody(base, quaternion, target_world)`;
- if direct IK on `p_body_raw` succeeds and its three joints satisfy the simulator joint ranges above, use `p_body_raw` unchanged as the body-foot target reaching the existing IK/LowCmd path;
- do **not** apply `ClampFootToHipWorkspace` on that sample;
- if the direct-valid guard is not satisfied at runtime, fall back to the exact parent mapping for safety. Any such fallback makes the canary scientifically non-passing and must be reported as `DIRECT_MAP_GUARD_HIT`.

Do not invent another projection, relax a joint limit, or change the numeric parent workspace box.

All non-V2, non-latched, or planning-invalid samples keep the parent mapping exactly.

## Frozen variables

Do not change V2 planning geometry, `x_entry/x_exit/x_land_min`, rise/lift/corridor construction, swing timing, touchdown target, gait schedule, shaper, MPC, WBC/ID, gains, torque/rate limits, safety logic, scene geometry, contact model, controller duration, or scientific thresholds.

No planner-recovery change. No parameter sweep. No combined intervention.

## No-live tests before canary

Add the smallest tests needed to prove:

- ordinary/non-V2 mapping is bit-for-bit unchanged;
- planning-invalid V2 mapping is unchanged;
- a direct-valid V2 crossing target bypasses the rectangular clamp and round-trips IK->FK to the requested target;
- a direct-invalid or joint-range-invalid target takes the exact parent fallback path.

Run the existing Cartesian-world/IK tests affected by the change. Do not broaden the test campaign beyond what is needed to establish semantic isolation.

## Runner and run directory

Use the existing parent scientific launch semantics from `example/cpp/scripts/run_phase2_known_step_edge_aware_v2.sh` unchanged. A task-specific runner may differ only in fresh run directory and the free legal DDS domain selected by immediate preflight.

Fresh run directory:

`example/cpp/experiments/_runs/phase2_known_step_v2_ik_map_canary_20260917/C`

No new A is authorized.

## Live budget

If and only if the feasibility gate, tests, build, provenance and immediate SOP preflight all pass, authorize exactly **one** V2-on C canary. The attempt is consumed at the SOP capture boundary. No tuning or replacement C after capture begins.

## Primary analysis

Analyze only the first planning-valid FL crossing through its first touchdown before interpreting later events.

1. Verify no control-relevant plant/LowCmd divergence from the parent C occurs before the first V2 latch. Ignore wall-clock-only diagnostics already established as non-causal.
2. Reconstruct `FK(q_target)` in world coordinates over the first FL crossing and compare with the requested V2 world target.
   - mapping passes iff max absolute x and z error are each <= `0.002 m` before first edge-envelope entry;
3. For actual FL motion, retain the established geometric-clear threshold `z >= 0.073 m` while actual foot center x is in `[0.777, 0.823] m`.
4. Retain the established first-FL raised-platform contact condition: actual x >= `0.850 m` and actual z >= first-swing start z + `0.035 m` for >= `0.10 s`.
5. Report the first downstream joint target/actual q,dq and rate/torque-limit evidence only if mapping passes but actual clearance/contact fails.

## Classification

Use exactly one:

- `DIRECT_V2_TARGET_INFEASIBLE` — no-live feasibility gate fails;
- `PROTOCOL_FAILURE` — provenance/preflight/evidence failure prevents interpretation;
- `DIRECT_MAP_GUARD_HIT` — runtime direct-valid guard fails and parent mapping fallback is used;
- `TARGET_MAPPING_NOT_FIXED` — guard remains direct-valid but mapping error exceeds the 2 mm criterion before edge entry;
- `MAPPING_FIXED_TRACKING_LIMITED` — mapping passes, but actual FL misses geometric clearance or the raised-platform contact condition;
- `MAPPING_FIXED_FIRST_FL_ESTABLISHED` — mapping passes and the first FL clears the edge envelope and establishes the retained raised-platform contact condition.

Do not claim full-step traversal success from this canary; it isolates the first-FL execution chain only.

## Closeout

Write only:

- `docs/validation/phase2_known_step_v2_ik_map_canary_20260917/RESULTS.md`
- `docs/validation/phase2_known_step_v2_ik_map_canary_20260917/analysis.json`
- `docs/validation/phase2_known_step_v2_ik_map_canary_20260917/provenance.csv`

Preserve raw `_runs` byte-for-byte after capture begins. Commit and push the branch. Report only the resulting commit SHA to Sol.