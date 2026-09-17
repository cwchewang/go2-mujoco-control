# Phase2 known-step V2 IK-map autonomous cycle

Mode: `confirmatory`  
SOP: `main/docs/research/SOP.md` v0.2  
Exact parent/base: `0f8a0109dc56a2dabad600aacee71c7d99bd6a46`  
Branch: `research/phase2-known-step-v2-ik-map-canary-20260917`

## Autonomous execution contract

This task is one complete research cycle, not a request for an intermediate audit.

After accepting the task, execute the full authorized decision tree without returning to the user or Sol for routine implementation choices:

`offline feasibility -> minimal target-map change if feasible -> focused tests/build/provenance/preflight -> exactly one live canary if authorized -> primary analysis -> bounded offline downstream localization when needed -> closeout`

Return early only at a task-defined/SOP-defined veto or when a genuinely new scientific decision outside this task is required. Do not request approval between the authorized stages above.

The Atlas trusted wrapper, not Luna, owns `git add`, `git commit`, and `git push`. Luna must leave only the intended tracked closeout/source changes in the task workspace and must not push.

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

## Bounded offline downstream localization

Run this section **only** if the primary classification is `MAPPING_FIXED_TRACKING_LIMITED`. It uses the single authorized canary already captured and authorizes no additional live run.

The purpose is to avoid another handoff whose only question would be “where downstream did the corrected command first stop being realized?” Localize the earliest post-mapping boundary using the captured canary plus frozen source.

Evaluate in causal order:

`IK joint target -> target shaping/rate limiting -> LowCmd q/dq/tau_ff -> actual joint q/dq -> FK(actual foot) -> contact`

Requirements:

1. Identify the earliest timestamp in the first FL crossing where the corrected mapped target still passes the 2 mm criterion but the next downstream representation materially fails to realize it.
2. Report target vs realized values at that boundary, including q/dq and any active configured rate/torque cap evidence available from source or logs.
3. Distinguish an explicit limiter/saturation from ordinary closed-loop tracking error; do not infer saturation merely from a large error.
4. Check whether contact occurs before or after the identified downstream divergence; do not relabel an already-existing tracking deficit as a contact-originated failure.
5. Name exactly one next intervention layer from:
   - `JOINT_TARGET_SHAPING_OR_RATE_LIMIT`
   - `LOWCMD_OR_TORQUE_APPLICATION`
   - `JOINT_CLOSED_LOOP_TRACKING`
   - `CONTACT_AFTER_TRACKING_DIVERGENCE`
   - `DOWNSTREAM_NOT_LOCALIZED`
6. Do not modify source, tune gains/limits, alter contact/planner logic, or run another experiment in this section.

The closeout must include this downstream localization when applicable so Sol can decide the next scientific task directly from GitHub without requesting a separate audit.

## Classification

Use exactly one primary classification:

- `DIRECT_V2_TARGET_INFEASIBLE` — no-live feasibility gate fails;
- `PROTOCOL_FAILURE` — provenance/preflight/evidence failure prevents interpretation;
- `DIRECT_MAP_GUARD_HIT` — runtime direct-valid guard fails and parent mapping fallback is used;
- `TARGET_MAPPING_NOT_FIXED` — guard remains direct-valid but mapping error exceeds the 2 mm criterion before edge entry;
- `MAPPING_FIXED_TRACKING_LIMITED` — mapping passes, but actual FL misses geometric clearance or the raised-platform contact condition;
- `MAPPING_FIXED_FIRST_FL_ESTABLISHED` — mapping passes and the first FL clears the edge envelope and establishes the retained raised-platform contact condition.

If and only if the primary classification is `MAPPING_FIXED_TRACKING_LIMITED`, also report exactly one `downstream_localization` value from the bounded list above.

Do not claim full-step traversal success from this canary; it isolates the first-FL execution chain only.

## Stop / continuation rules

- `DIRECT_V2_TARGET_INFEASIBLE`: close out with no runtime change/live run.
- `PROTOCOL_FAILURE`: close out; do not manufacture replacement evidence.
- `DIRECT_MAP_GUARD_HIT`: close out; no second run.
- `TARGET_MAPPING_NOT_FIXED`: close out with the earliest residual mapping mismatch; no second run.
- `MAPPING_FIXED_TRACKING_LIMITED`: complete the bounded offline downstream localization above, then close out; no second run.
- `MAPPING_FIXED_FIRST_FL_ESTABLISHED`: close out. Full-step/multi-leg continuation is a new scientific question and is intentionally outside this task.

## Closeout

Write the required tracked closeout artifacts:

- `docs/validation/phase2_known_step_v2_ik_map_canary_20260917/RESULTS.md`
- `docs/validation/phase2_known_step_v2_ik_map_canary_20260917/analysis.json`
- `docs/validation/phase2_known_step_v2_ik_map_canary_20260917/provenance.csv`

`RESULTS.md` must state the primary classification and, when applicable, `downstream_localization`, plus enough exact timestamps/numeric evidence to support them.

Preserve raw `_runs` byte-for-byte after capture begins. Do not stage, commit, or push; the trusted Atlas wrapper will validate and commit the intended tracked changes, then push them only if the remote branch is still at the exact task commit.