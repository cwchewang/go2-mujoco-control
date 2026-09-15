# Phase2 checkpoint: edge-aware known-step swing planner V2

Date: 2026-09-15
Prepared branch: `research/phase2-known-step-edge-aware-v2-20260915`
Exact parent evidence: `2543901214e83fc1dad71110b6699e0dc8da48d3`

Read `docs/research/PHASE1_AGENT_CONTRACT.md`, the original 5 cm known-step task, the B-only task, and `docs/research/TASK_PHASE2_KNOWN_STEP_FIRST_SWING_FAILURE_AUDIT_20260915.md` before editing or running anything. This task is authoritative for the V2 checkpoint.

## 1. Question

Can a geometry-aware swing planner traverse the same fixed 5 cm up-step when it fixes the three failure modes identified by the frozen offline audit, while leaving speed, gait timing, WBC/MPC/ID, body references, contact scheduling, scene geometry, and D4 unchanged?

The parent audit classified V1 as `MIXED_CLEARANCE_TRACKING_PLACEMENT` and established:

- V1 endpoint-only adaptation was isolated and causal;
- first FR adapted swing had a geometrically high intended command at the edge but the actual foot entered low and showed force/contact evidence;
- FL1 and FR2 reconstructed intended commands entered the edge envelope below the conservative geometric center-clearance height;
- all final touchdown centers were beyond x=0.823, but FR1 had only about 2.5 mm margin;
- V1 delayed hard-posture versus A and advanced farther, so the mechanism was not inert;
- solver numerics remained healthy.

V2 must therefore change **planning geometry and timing only**, not actuator/control gains or approach speed.

## 2. Frozen environment and locomotion plant

Use only `unitree_robots/go2/scene_known_step_5cm.xml`:

- step edge `x_edge = 0.800 m`;
- step top `z_top = 0.050 m`;
- lateral half-width `1.00 m`.

Frozen Go2 collision geometry:

- foot sphere radius `r = 0.022 m`;
- MuJoCo default collision margin `m = 0.001 m`.

Frozen run arguments are in `example/cpp/scripts/run_phase2_known_step_edge_aware_v2.sh`:

- `--wall-clock-motion --cartesian-world --wbc-full --kernel raibert-trot`;
- period 0.60 s, duty 0.75, step length 0.091 m, base foot lift 0.028 m;
- Raibert gain 0.12, max adjustment 0.140 m;
- no world-feedback / no attitude-feedback;
- tau limit 35 Nm; preview horizon 4; max cycles 40;
- `FULL2_HOLD_CYCLES=999`;
- lockstep + paired HighState;
- D4, D90, PD pulse, reactive events, auto-environment all OFF.

Do not change any of those values.

## 3. Run matrix

Exactly one new live run is authorized:

- **C / DDS domain 233**: V2 enabled via `TROT_KNOWN_STEP_TRAVERSAL_V2=1`.

Do not rerun A or V1 B. Reuse their immutable captures only for comparison:

A:
`/home/che/dev/go2-workspace/phase2-known-step-wallclock-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`

V1 B:
`/home/che/dev/go2-workspace/phase2-known-step-b-only-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_b_only_20260915/B`

C output:
`example/cpp/experiments/_runs/phase2_known_step_edge_aware_v2_20260915/C`

No retry, replacement domain, second C, GUI replay, speed sweep, height sweep, parameter sweep, or follow-up live experiment.

## 4. V2 feature semantics

V2 is a separate opt-in path. `TROT_KNOWN_STEP_TRAVERSAL_V2=1` enables V2. The old `TROT_KNOWN_STEP_TRAVERSAL` V1 flag must be unset in C. V1 behavior must remain available and unchanged when its old flag is used; feature-off behavior must remain the historical path.

### 4.1 Fixed geometric constants

For this checkpoint define:

- edge-envelope entry: `x_entry = x_edge - r - m = 0.777 m`;
- edge-envelope exit / fully-beyond center: `x_exit = x_edge + r + m = 0.823 m`;
- conservative geometric center-clearance: `z_geom_clear = z_top + r + m = 0.073 m`;
- V2 landing minimum x: `x_land_min = max(0.850 m, x_edge + 2*r + m) = 0.850 m`.

`0.850 m` is not a fitted value: it is the already-preregistered raised-platform contact x threshold from the original traversal success definition.

### 4.2 Early crossing latch at swing entry

The V1 defect was that the ordinary touchdown was recomputed through swing and adaptation could first become active mid-swing. V2 must decide/latch a crossing plan at **entering_swing**.

At entering_swing for each leg:

1. compute the ordinary nominal touchdown `p_nom` exactly as the historical Cartesian-world planner would, including all existing Raibert/lateral semantics;
2. create a **detection-only** copy of the same `WorldTouchdownInput`, set `swing_remaining_s = t_sw = max(0.05,(1-duty)*period)` regardless of the historical `predict_hip_at_td` flag, run the same `PlanWorldTouchdown`, and apply the same lateral offsets to obtain `p_probe`;
3. compute terrain height at swing start, `p_nom`, and `p_probe`;
4. latch V2 crossing for the entire swing iff the swing starts on the lower floor and either `p_nom` or `p_probe` lies on the raised plateau within the lateral step width.

The detection-only probe must never directly become the commanded touchdown. It exists only to decide the crossing before the foot reaches the edge.

If no crossing is latched, preserve the old non-crossing Cartesian-world behavior exactly, including ordinary touchdown recomputation.

Once crossing is latched, do not unlatch or recompute the final crossing target during that swing.

### 4.3 Latched crossing touchdown

For a latched floor-to-plateau crossing:

- keep nominal touchdown y unchanged;
- set `final_x = max(p_nom.x, x_land_min)`;
- set `final_y = p_nom.y`;
- set `rise = 0.050 m`;
- set `final_z = swing_start.z + rise`;
- retain the V1 effective lift definition only as an input to the corridor height calculation:
  `lift_eff = max(base_foot_lift, rise + 0.030)`, hence 0.080 m here.

The final target must be frozen for the rest of the swing.

Plateau-to-plateau and floor-to-floor swings must not accumulate height or receive a crossing x shift.

### 4.4 Edge-aware C1 swing corridor

For a valid latched +X crossing let `p0` be frozen swing start and `p1` be frozen final touchdown. Require:

`p0.x < x_entry < x_exit < p1.x`.

If this ordering is false, mark `planning_valid=false`, preserve a safe historical/non-V2 fallback for that swing, record the reason, and let the analyzer classify `PLANNING_GEOMETRY_FAILED`. Do not silently change thresholds or clamp to a different planner.

Define the corridor height:

`z_corridor = max(z_top + 2*r + m, 0.5*(p0.z + p1.z) + lift_eff)`.

For this geometry the first term is 0.095 m; the second term preserves at least the natural midpoint peak implied by the existing effective lift rather than lowering an already-high swing.

Use the historical horizontal progress:

`s = Quintic01(min(1, swing_phase/0.80))`.

Keep x/y interpolation exactly on that same historical horizontal quintic from `p0` to frozen `p1`.

Let:

`s_entry = (x_entry - p0.x)/(p1.x-p0.x)`

`s_exit = (x_exit - p0.x)/(p1.x-p0.x)`.

Command z as a piecewise C1 trajectory:

- `s <= s_entry`:
  `z = p0.z + (z_corridor-p0.z)*Quintic01(s/s_entry)`;
- `s_entry < s < s_exit`:
  `z = z_corridor`;
- `s >= s_exit`:
  `z = z_corridor + (p1.z-z_corridor)*Quintic01((s-s_exit)/(1-s_exit))`.

Implement the analytically consistent world velocity. The quintic has zero derivative at each segment boundary, so z and dz/dt must be continuous at `s_entry` and `s_exit` within numerical precision.

Do not add another free lift multiplier, waypoint height, phase shift, speed reduction, body pitch command, or gain.

## 5. Explicit prohibitions

V2 must not modify:

- approach speed or speed policy;
- gait period, duty, gait phase, base step length, ordinary non-crossing swing semantics;
- WBC, SRBD MPC, ID-WBC, gains, weights, force references, contact schedule/merge logic;
- base-height, pitch or roll references;
- torque limits, motor kp/kd/tau_ff policy;
- D4/D90/PD pulse;
- scene or collision geometry;
- safety limits;
- lateral touchdown y;
- old V1 semantics when V1 alone is selected.

The only causal V2 changes on a latched crossing swing are: earlier crossing decision/latch, frozen crossing touchdown, minimum forward landing margin, and edge-aware z trajectory/velocity.

## 6. Required V2 diagnostics

Before live run add explicit CSV telemetry, not inferred post hoc. At minimum per leg record:

- V2 feature enabled;
- crossing latched;
- planning valid + stable failure code/reason;
- swing-start x/z;
- ordinary `p_nom` x/y/z at latch;
- detection-only `p_probe` x/y/z;
- terrain h0/h_nom/h_probe;
- x_entry, x_exit, x_land_min;
- frozen final touchdown x/y/z;
- x shift from ordinary nominal;
- lift_eff and z_corridor;
- s, s_entry, s_exit;
- instantaneous commanded world x/z and vx/vz from the V2 trajectory;
- actual world foot x/z;
- scheduled swing/stance.

Keep the existing V1 telemetry and ordinary gait/WBC/contact/motor telemetry. Do not repurpose D4 fields.

## 7. Pre-live tests and source audit

Before C, add focused tests that prove at least:

1. V2 flag off -> historical behavior unchanged;
2. old V1 flag alone -> V1 tests/semantics unchanged;
3. detection-only probe can latch a crossing at swing entry even when `p_nom.x < edge` but `p_probe` reaches the plateau;
4. non-crossing floor swing does not latch;
5. plateau-to-plateau does not latch/accumulate +5 cm;
6. latched crossing final y equals ordinary nominal y;
7. latched final x >=0.850 and final z=start.z+0.05;
8. latched target remains frozen when body/velocity inputs change later in the same swing;
9. valid crossing satisfies `0<s_entry<s_exit<1`;
10. commanded z is >= `z_corridor` for the complete x-envelope `[0.777,0.823]` within numerical tolerance;
11. position and velocity are continuous at the two corridor boundaries;
12. invalid ordering records planning-invalid and does not silently invent another target;
13. non-crossing legs retain historical target/velocity semantics.

Run focused tests, controller full CTest, motion-clock integration test, simulator `test_lockstep`, simulator full CTest. All must pass.

Source diff audit must prove no prohibited subsystem changed. Runtime-affecting code, tests, telemetry, analyzer, and runner must all be committed before C. Worktree clean before live.

## 8. Frozen-reference provenance

Before C verify:

- A raw hashes still match the accepted pre-contact readjudication provenance;
- V1 B raw hashes still match the B-only/failure-audit provenance;
- scene hash unchanged;
- exact current runtime HEAD recorded;
- rebuilt controller/simulator binaries are recorded; rebuilds due to authorized source/telemetry changes are allowed, but source diff must stay inside the allowlist.

## 9. Exact pre-activation comparison

C must be compared against frozen A from the common lockstep handoff through the final row strictly before C's first `v2_crossing_latched` sample.

Require identical row count/timestamps and exact equality on all common causal fields available in both captures, including state/control clocks, gait phase/cycle, pose/velocity, IMU, contacts, ordinary nominal gait outputs, WBC/SRBD/ID outputs, and all motor command/state fields.

Allowed differences before activation are only V2 metadata/telemetry fields and noncausal wall timing / measured compute-time diagnostics. No causal command/state difference is allowed.

Mismatch -> `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`; do not rerun.

## 10. Planning/isolation gates

C must show:

- old V1 flag OFF and V2 ON;
- D4/D90/PD pulse OFF;
- at least one front-leg crossing latched before the first geometry-risk event;
- every latched crossing was planning-valid;
- ordinary nominal y unchanged in frozen final target;
- final x >=0.850 for every floor-to-plateau latched crossing;
- final z = start.z+0.050;
- command z >= z_corridor throughout every sample whose commanded x lies in `[0.777,0.823]`;
- analytic command velocity finite and boundary-continuous;
- no non-crossing swing receives V2 x/z/corridor modification;
- no prohibited controller/gait/body/contact intervention enabled.

A failure in those geometry/isolation requirements -> `PLANNING_GEOMETRY_FAILED` unless preactivation or protocol takes precedence.

## 11. Actual tracking diagnostics

For every front-leg latched crossing report:

- first commanded and actual edge-envelope entry;
- commanded/actual z there;
- min commanded z and min actual z while each trajectory is in the edge envelope;
- max/median actual-minus-commanded z error;
- foot force/contact around envelope entry;
- touchdown actual x/z and command x/z;
- joint q target/state error, dq, tau_est/effective torque if available;
- whether actual center entered the envelope below `z_geom_clear=0.073`;
- whether the leg obtained >=0.10 s physical raised-platform contact using the original x>=0.85 and z>=z0+0.035 criterion.

Do not use a post-hoc tracking threshold to change the live run. These are classification diagnostics.

## 12. Full traversal success remains unchanged

C is a successful full traversal only if the original preregistered criteria are all satisfied:

1. base x reaches >=1.45 m;
2. after first reaching 1.45, base does not fall below 1.35 for >=0.50 s state time;
3. all four legs each obtain >=0.10 s cumulative physical contact with actual x>=0.85 and actual z>=z0+0.035;
4. no hard safety marker and final statuses zero;
5. max |roll| and |pitch| in the step/traversal window <=0.25 rad;
6. WBC/SRBD/ID valid rows all succeed and residual p95 <=1e-3;
7. no persistent commanded/actual dragging artifact.

Do not weaken these criteria.

## 13. Classification

Use exactly one primary label, precedence in this order:

1. `PROTOCOL_FAILURE`: run order/provenance/lockstep/paired-state/evidence-schema violation.
2. `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`: causal exact equality fails before first V2 latch.
3. `PLANNING_GEOMETRY_FAILED`: V2 latch/target/corridor/isolation invariant fails.
4. `SUPPORTED_ENABLES_TRAVERSAL_V2`: all protocol/planning gates pass and full traversal succeeds.
5. `TRACKING_LIMITED`: planning gates pass, full traversal fails, and at least one critical front crossing actual foot enters the edge envelope below 0.073 m and/or shows material contact/blockage while the commanded V2 corridor is geometrically clear.
6. `FRONT_PAIR_ESTABLISHED_BUT_COORDINATION_FAILED`: planning gates pass, both front legs satisfy the original raised-platform contact criterion, but full traversal still fails before all four legs/whole body complete the step.
7. `OTHER_CONTROL_LIMIT_IDENTIFIED`: planning passes and failure does not fit the two preceding mechanisms; identify the directly evidenced mechanism.
8. `INSUFFICIENT_EVIDENCE`: otherwise.

Do not invent a new label after seeing data.

Historical A and V1 B timing (`A risk->hard ~0.340 s`, `V1 B ~0.606 s`) may be reported as secondary context only; they are not V2 pass thresholds.

## 14. Analyzer and required outputs

Before C, create `example/cpp/tools/analysis/analyze_phase2_known_step_edge_aware_v2.py`.

It must consume frozen A, frozen V1 B for secondary comparison, and C. It must implement:

- provenance and launch-budget checks;
- exact A/C preactivation comparison;
- V2 geometry/isolation gates;
- original traversal success calculation;
- per-leg edge/corridor tracking analysis;
- body/contact/solver chronology;
- frozen classification precedence above.

Write under `docs/validation/phase2_known_step_edge_aware_v2_20260915/` at least:

- `RESULTS.md`;
- `analysis.json`;
- `preactivation_exact.csv`;
- `planning_isolation.csv`;
- `front_crossing_summary.csv`;
- `edge_tracking_timeline.csv`;
- `touchdown_summary.csv`;
- `protocol_gates.csv`;
- `provenance.csv`.

## 15. Stop

After one C live run, analysis, closeout commit and push, stop.

Do not tune V2, alter the corridor or x margin, slow the robot, change body posture, add foothold search, run 10 cm, add perception, or execute any other live experiment in this checkpoint.
