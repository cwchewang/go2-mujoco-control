# Phase2 known-step V2 minimum-clearance path cycle

Mode: `confirmatory`  
SOP: `main/docs/research/SOP.md` v0.2  
Exact parent/base: `12238b768d8ac6f3d51032fc8ce19d443ca71966`  
Parent classification: `DIRECT_V2_TARGET_INFEASIBLE`  
Branch: `research/phase2-known-step-v2-min-clearance-path-20260917`

## Question

Can the first planning-valid FL V2 crossing be made kinematically feasible by removing the unnecessary high swing corridor while preserving the existing x/y progression, touchdown, gait and timing; and, if so, does passing that feasible V2 target unchanged to IK establish the first-FL 5 cm crossing?

This task tests one causal layer only: **V2 target construction plus faithful mapping of a target already proven feasible**. It does not authorize gait, WBC/MPC, gain, timing, touchdown, obstacle, contact or recovery changes.

## Frozen evidence

The exact parent closeout established:

- 75 planning-valid V2 FL samples from 14.254 s through 14.402 s;
- the raw V2 target is initially feasible, but at 14.310 s direct IK yields FL calf `-2.784049885 rad`, below the simulator lower bound `-2.7227 rad` by `0.061349885 rad`;
- direct IK first becomes geometrically unsolvable at 14.316 s (`leg_z_squared < 0`);
- therefore the mapping-only intervention was correctly vetoed and no live run occurred.

The frozen V2 source currently computes the valid-crossing corridor as the maximum of:

1. pure obstacle geometry clearance `geometry.height_m + foot_radius + margin`; and
2. `0.5 * (swing_start.z + final_touchdown.z) + effective_lift`.

For the first 5 cm FL crossing, the second term drives the command to about 0.130 m even though the geometric center-height requirement is about 0.073 m and the retained final touchdown center is about 0.075 m.

Parent raw evidence is read-only and must remain unchanged.

## Candidate scientific change

For a planning-valid, latched V2 crossing only, define the corridor deterministically as the **lowest geometry-consistent center height**:

```text
z_corridor_min = max(
    geometry.height_m + kKnownStepV2FootRadiusM + kKnownStepV2GeomMarginM,
    swing_start_world.z,
    final_touchdown_world.z)
```

Keep the existing horizontal progress, `s_entry`, `s_exit`, quintic ramps, world-Y interpolation, final touchdown and swing timing unchanged.

Do not tune this height and do not add a margin beyond the already frozen foot-radius plus 1 mm geometry margin.

The existing `effective_lift_m` value may remain for logging/fallback semantics, but it must not raise `z_corridor_m` for a planning-valid V2 crossing under this intervention.

## Mandatory no-live feasibility gate

Before changing runtime behavior, reconstruct the candidate minimum-clearance V2 FL world target over the exact parent C first crossing using the frozen parent base pose/quaternion and swing phase for every planning-valid V2 sample from 14.254 s through 14.402 s.

For every candidate sample:

1. preserve the parent x and y target exactly; change only z according to the deterministic minimum-clearance corridor above;
2. `LegInverseKinematics(FL, p_body_candidate)` must succeed;
3. resulting joints must satisfy the simulator ranges:
   - abduction `[-1.0472, 1.0472]`;
   - front thigh `[-1.5708, 3.4907]`;
   - knee `[-2.7227, -0.83776]`;
4. frozen FK of the IK result must reproduce `p_body_candidate` within `1e-6 m` per axis;
5. whenever candidate foot-center x is in `[x_entry, x_exit]`, candidate world z must be at least `geometry.height_m + foot_radius + margin`.

If any sample fails, do not modify runtime code and do not launch a live run. Classify `MIN_CLEARANCE_PATH_INFEASIBLE`, report the earliest failing sample and whether failure is IK geometry, joint range, FK round-trip or edge clearance, then stop.

No parameter sweep, alternative corridor, lateral detour, body-height change or timing change is authorized if this gate fails. Those would be new scientific questions.

## Runtime change if and only if the gate passes

Make only these coupled target-layer changes:

1. for a planning-valid latched V2 crossing, use the deterministic minimum-clearance `z_corridor_m` above;
2. after `WorldToBody`, if direct IK of that V2 target succeeds and all three joints satisfy the simulator ranges, pass that body target unchanged to the existing IK/LowCmd path and do not call `ClampFootToHipWorkspace` for that sample;
3. if the direct-valid runtime guard fails, fall back to the exact parent rectangular-clamp mapping for safety and mark the canary non-passing as `DIRECT_MAP_GUARD_HIT`.

All non-V2, non-latched or planning-invalid samples must keep the exact parent mapping and target construction.

Do not invent a new projection or optimizer in this task.

## Frozen variables

Do not change:

- `x_entry`, `x_exit`, `x_land_min`;
- final touchdown x/y/z;
- V2 latch condition or edge ordering;
- swing phase, period, duty factor or gait schedule;
- horizontal x/y interpolation;
- planner recovery;
- body command or base-height target;
- MPC, WBC/ID, gains, torque/rate limits, safety logic;
- scene geometry, foot radius, geometry margin or contact model;
- controller duration or scientific thresholds.

No parameter sweep. No replacement run after capture begins.

## No-live tests before canary

Add the smallest tests needed to prove:

- ordinary/non-V2 target construction and mapping are bit-for-bit unchanged;
- planning-invalid V2 behavior is unchanged;
- planning-valid V2 uses the deterministic minimum-clearance corridor;
- the edge corridor satisfies the frozen geometric-clearance requirement;
- a direct-valid V2 candidate bypasses the rectangular clamp and IK->FK round-trips to the requested target;
- a direct-invalid or joint-range-invalid V2 candidate takes the exact parent fallback;
- the frozen first-FL parent-pose candidate passes the complete no-live feasibility gate.

Run only the smallest affected Cartesian-world/IK tests, then the required build/provenance checks and immediate SOP preflight.

## Runner and live budget

Use the existing scientific launch semantics from `example/cpp/scripts/run_phase2_known_step_edge_aware_v2.sh`, differing only where required for the fresh run directory and an immediately preflighted free legal DDS domain.

Fresh run directory:

`example/cpp/experiments/_runs/phase2_known_step_v2_min_clearance_path_20260917/C`

If and only if the feasibility gate, tests, build, provenance and immediate preflight all pass, authorize exactly **one** V2-on C canary.

No new A is authorized. No tuning, retry or replacement C after the SOP capture boundary.

## Primary analysis

Analyze the first planning-valid FL crossing through first touchdown before interpreting any later event.

1. Verify no control-relevant divergence from the exact parent before first V2 latch.
2. Reconstruct requested V2 target and `FK(q_target)` in world coordinates.
   - mapping passes iff max absolute x and z errors are each `<= 0.002 m` before first edge-envelope entry;
3. actual FL geometric clearance passes iff actual foot-center `z >= 0.073 m` while actual x is in `[0.777, 0.823] m`;
4. retained first-FL raised-platform contact passes iff actual x `>= 0.850 m` and actual z `>= first-swing-start-z + 0.035 m` for `>= 0.10 s`;
5. report whether the runtime direct-valid guard ever falls back.

## Mandatory offline downstream localization if mapping passes but actual motion fails

If mapping passes but actual geometric clearance or retained raised-platform contact fails, do not stop at the label `tracking-limited`.

Using the single canary capture only, continue offline and identify the earliest downstream execution boundary among:

`q_target -> dq_target/rate shaping -> torque command/limit -> actual q/dq -> contact`

At minimum report:

- first time and joint where target-vs-actual q error becomes large enough to explain the foot miss;
- whether target dq is rate-limited first;
- whether commanded/estimated torque reaches the frozen limit first;
- whether a contact event precedes or follows the established tracking error;
- the one earliest downstream layer supported by the data.

This localization authorizes no second live intervention or run. It exists so Sol can issue the next task without another intermediate audit cycle.

## Classification

Use exactly one primary classification:

- `MIN_CLEARANCE_PATH_INFEASIBLE` — mandatory offline candidate gate fails;
- `PROTOCOL_FAILURE` — build/provenance/preflight/evidence failure prevents interpretation;
- `DIRECT_MAP_GUARD_HIT` — runtime feasibility guard falls back to parent mapping;
- `TARGET_MAPPING_NOT_FIXED` — direct-valid path remains active but mapping exceeds the 2 mm criterion;
- `MAPPING_FIXED_TRACKING_LIMITED` — mapping passes but actual first-FL clearance/contact fails; include the mandatory earliest downstream localization;
- `MAPPING_FIXED_FIRST_FL_ESTABLISHED` — mapping passes and actual first FL clears the edge envelope and establishes retained raised-platform contact.

Do not claim full-step or full-traversal success from this task.

## Closeout

Write only:

- `docs/validation/phase2_known_step_v2_min_clearance_path_20260917/RESULTS.md`
- `docs/validation/phase2_known_step_v2_min_clearance_path_20260917/analysis.json`
- `docs/validation/phase2_known_step_v2_min_clearance_path_20260917/provenance.csv`

Preserve all raw `_runs` byte-for-byte after capture begins. Do not push from the agent; leave the intended tracked edits for the trusted Atlas closeout/push wrapper.