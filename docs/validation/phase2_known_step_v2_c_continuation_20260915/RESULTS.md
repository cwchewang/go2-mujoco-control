# Phase2 known-step V2 C continuation closeout

Date: 2026-09-16
Primary classification: `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`
Earliest informative failure boundary: `causal` — strict A/C preactivation equality failed immediately after the common handoff.

Exactly one authorized C capture was consumed after the required immediate preflight passed. No retry, replacement run, tuning, A rerun, or follow-up live run was made. C produced 5,005 data rows and 5,005 paired HighState cycles with 2 ms lockstep and zero trace violations. The captured runtime stopped on the existing hard safety/posture path (`safety_status=1`, `completion_status=1`); this is preserved as an outcome, not repaired or reclassified.

Provenance passed: A runtime HEAD=`4834baea49f5aac9430dbdeaf8e3d93fe6124b2d`, C runtime HEAD=`3f6f12b62d1131eb0aed5d0eb65a6132f804f701`, both clean; controller SHA-256=`fe7339d50346e53069d81a27504ae4de4217baab29a6695cdd5073d1898b1fd2`; simulator SHA-256=`29caa74aa8e5cf1988190ecb8978d2fe15ce6a21146182c66e5efc91121c022b`; scene SHA-256=`8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc`. A/C binary identity, frozen V1 B hashes, V2-on/V1-off isolation, DDS/domain, lockstep, and launch-budget gates passed.

The common handoff was state tick 8.000 s. A/C were compared for 3,127 rows through the row strictly before C's first V2 crossing latch at 14.254 s (FL, base x=0.511724145); 770 causal fields were compared and 1,000 mismatches were recorded (capped). The first mismatch was row 0 at 8.000 s (`wbc_shadow_within_budget`, A=`0`, C=`1`); the next row also contains small WBC full-ID numeric/status differences. The C V2 feature flag first became active at 12.302 s (row 2,151). Therefore the required exact preactivation gate fails before any valid A/C V2 causal attribution, and the original precedence selects `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`.

The existing V2 analysis was still applied descriptively. The first FL command entered the edge at 14.332 s with x=0.778435267 m, z=0.130230552 m, while the actual foot entered at 14.394 s with x=0.777368072 m, z=0.042044500 m, contact=true and force=100 N. Its actual-commanded z absolute max/p95 were 0.113197807/0.111193878 m; commanded touchdown was x/z=0.850000000/0.075230552 m versus actual x/z=0.785232410/0.046628094 m. FR first entered at 15.154 s with actual x/z=0.778506104/0.023192198 m, contact=true and force=82 N. Planning gates recorded the first latch before first plausible contact risk (14.396 s) but failed later latch-validity/final-x/effective-lift and FL/FR zero-segment boundary checks.

No qualified raised-platform contact was established for any leg. Body progression reached max x=0.883443139 m and first x=0.80 m at 15.744 s, never x=1.45 m. Contact chronology began with 2 contacts at handoff, reached 4 at 8.118 s, then became intermittent from 12.476 s; the first posture threshold crossing was 15.208 s. In the analyzed post-contact window, WBC had 1,539 valid rows, SRBD success=1.0, ID success=1.0, and equality-residual p95=1.352373e-4; runtime safety/completion and traversal gates remained failed.

Detailed raw hashes, metadata, protocol gates, exact preactivation mismatches, planning, tracking, contact chronology, and WBC/SRBD/ID metrics are in `analysis.json` and `provenance.csv`. Raw `_runs` artifacts are unchanged.

## Superseding offline causal audit (2026-09-16)

The historical primary classification above is preserved. A source-grounded audit of the consumed raw A/C evidence supersedes its preactivation-divergence interpretation: the old 629-field-style equality gate was over-inclusive for this run. The raw A/C comparison through rows 0..3126 (state ticks 8.000000..14.252000 s, immediately before C's first V2 latch) has 73 differing fields and 21,635 differing cells:

- Wall-clock/runtime diagnostics: `motion_clock_wall_dt_s`, `wbc_shadow_elapsed_us`, and `wbc_shadow_within_budget`.
- External/configuration input: `known_step_v2_feature_enabled`, which is the intentional A-off/C-on V2 mode input starting at state tick 12.302000 s.
- Trajectory-driving controller state/plan: `wbc_full_id_ok`, plus the four-leg `known_step_v2_*` plan families `planning_failure_code`, `planning_failure_reason`, `swing_start_x_m`, `swing_start_z_m`, `ordinary_nominal_touchdown_{x,y,z}_m`, `probe_touchdown_{x,y,z}_m`, `x_entry_m`, `x_exit_m`, `final_touchdown_{x,y,z}_m`, and `effective_lift_m`. These are theoretically trajectory-driving, but before a valid latch the command path remains on the ordinary target branch.
- Derived/logging-only WBC fields: `wbc_shadow_min_contact_normal_force_n`, `wbc_shadow_max_abs_tau`, `wbc_full_id_qdd_x_mps2`, and `wbc_full_id_contact_force_x_n`. No final LowCmd field differs in the pre-latch interval.
- No differing external simulator state field and no differing actual LowCmd `q/dq/kp/kd/tau` field were found before the first V2 latch.

The WBC budget propagation is non-causal in this run. At row 0, `wbc_shadow_elapsed_us` was A=`1001.604000000`, C=`993.763000000`, giving `within_budget` A=`0`, C=`1`. The existing argv omitted both feedforward options, so `params_.wbc_torque_feedforward` was false. `EvaluateWbcFeedforwardGate` therefore returned `disabled` at its first `requested` check; A and C both had gate code `0`, `ready=0`, and no budget-dependent feedforward branch. The budget value was not read by `WriteMotorCommands`; all published LowCmd command fields were exact-equal through row 3126. The row-1 ID solver status/cache transient (`wbc_full_id_ok` A=`0`, C=`1`) was followed by successful equal output at row 2 and did not alter a command or plant-state field.

The source call graph is: `MotionClockStep` wall delta -> lockstep state-tick rebase -> actual `motion_dt`; `UpdateWbcShadow` steady-clock elapsed -> `within_budget` -> feedforward gate. The gate is short-circuited by `requested=false`. The V2 path is `known_step_geometry.v2_enabled` -> `PlanKnownStepV2Crossing` -> `crossing_latched && planning_valid` -> `KnownStepV2SwingTarget/Velocity` -> `target_world` -> IK joint targets -> `WriteMotorCommands`/published LowCmd. The first control-relevant A/C divergence is therefore the intended V2 boundary at row 3127, state tick 14.254000 s: C FL `crossing_latched=1`, `final_touchdown_x=0.850000000`, `effective_lift=0.080000000`; A remains V2-off, and the first LowCmd differences occur on that row. No control-relevant divergence precedes it.

Using the existing classification precedence, the source-grounded offline readjudication is `PLANNING_GEOMETRY_FAILED`; no new scientific label is introduced. This does not alter the captured C outcome, thresholds, V2 semantics, or any raw evidence.

## Final TASK §§10–13 classification

The historical `INCONCLUSIVE_PREACTIVATION_DIVERGENCE` remains recorded above, but is superseded for the final classification by the source-grounded offline causal audit. The §10 gates are:

| §10 gate | Result | Earliest evidence |
|---|---|---|
| V2 ON; old V1 OFF/unset | PASS | C V2 flag active=`1`; old V1 value=`0`; old V1 environment flag absent |
| D4/D90/PD OFF | PASS | D4 enabled/gate-active=`0`; D90 enabled/gate-active=`0`; `PD_PULSE` absent |
| Front-leg latch before first geometry risk | PASS | FL latch row 3127, state tick 14.254 s; first risk row 3198, 14.396 s |
| Every latched crossing `planning_valid` | **FAIL** | FL second swing row 3427, 14.854 s: `planning_valid=0`, code=`2`, reason=`invalid_edge_ordering`, `s_entry=s_exit=0` |
| Final y equals ordinary nominal y | PASS | maximum absolute error=`0.0 m`; first FL latch both y=`0.078051928 m` |
| Final x >= 0.850 m | **FAIL** | same FL swing: final x=`0.790137099 m`, margin=`-0.059862901 m` |
| Final z = start.z + 0.050 m | **FAIL** | same FL swing: start/final z=`0.046628094 m`; expected=`0.096628094 m`; error=`0.050000000 m` |
| Floor-to-plateau rise=`0.050 m` | PASS | maximum formula error=`0.0 m` |
| Floor-to-plateau effective lift=`0.080 m` | **FAIL** | same FL swing: effective lift=`0.028 m`, error=`0.052 m` |
| Commanded z >= corridor for x in [0.777, 0.823] | PASS | 1,510 samples; minimum margin=`0.0 m` at FL row 3166, 14.332 s (`z=corridor=0.130230552 m`) |
| Analytic velocity finite | PASS | no missing/non-finite vx/vz in 1,578 latched samples |
| Analytic boundary-continuous | **FAIL** | earliest is FL second swing at 14.854 s with zero segment (`s_entry=s_exit=0`); FR later fails at 15.154 s |
| Non-crossing swing unchanged | PASS | no non-crossing isolation failures |
| No prohibited controller/gait/body/contact intervention | PASS | V2-only mode; old V1, D4, D90, PD and other intervention inputs were off/unset |

The earliest failure mechanism is the FL second-swing invalid edge ordering at 14.854 s. The runtime records the invalid ordering rather than silently inventing a V2 target; it falls back to the ordinary touchdown (`final_x=0.790137099`, `final_z=start.z`, `effective_lift=0.028`) and produces the zero-length analytic corridor segment. Because a §10 planning/isolation gate fails, the final primary classification under §13 is **`PLANNING_GEOMETRY_FAILED`**.

This is not `INCONCLUSIVE_PREACTIVATION_DIVERGENCE` because the prior source-grounded audit established exact control-relevant A/C state and LowCmd trajectory through the pre-latch row; not `TRACKING_LIMITED`, `FRONT_PAIR_ESTABLISHED_BUT_COORDINATION_FAILED`, or `OTHER_CONTROL_LIMIT_IDENTIFIED` because §13 gives the planning failure precedence and the front-pair raised-contact criterion was not established; not `SUPPORTED_ENABLES_TRAVERSAL_V2` because planning and full traversal criteria failed; and not `PROTOCOL_FAILURE` or `INSUFFICIENT_EVIDENCE` because provenance/lockstep/evidence gates passed and the planning failure is directly observed.

## Offline mechanism-separation audit: first FL crossing to second FL ordering failure (2026-09-16)

This is an offline interpretation of the unique C raw capture. The existing primary classification remains `PLANNING_GEOMETRY_FAILED`; no raw evidence or runtime semantics changed.

Timeline and front-leg state:

- At 14.254 s (raw row 3127), FL latched V2 with a valid plan. At the same instant FR was still non-latched (`crossing_latched=0`); there was no established front pair.
- At 14.332 s, the FL command entered the edge envelope at x=0.778435267 m and z=0.130230552 m, exactly at the commanded corridor. At 14.394 s, the actual FL entered at x=0.777368072 m and z=0.042044500 m, below the 0.073 m geometric-clear level, with contact=true and 100 N.
- At 14.404 s, FL touchdown was commanded at x/z=0.850000000/0.075230552 m but actual x/z was 0.785232410/0.046628094 m. It did not satisfy the raised-platform contact criterion (actual x >= 0.850 m and actual z >= start.z+0.035 m for >=0.10 s).
- At 14.854 s (raw row 3427), the next FL swing latched the crossing condition but failed `planning_valid`; FR remained non-latched and ordinary. The actual first-FL touchdown x/z above became the next FL p0 exactly.
- The first FR crossing did not latch until 15.154 s, after the FL invalid-ordering event. FR was already invalid at latch: its command/actual first edge entries were x/z=0.777150774/0.026995857 m and 0.778506104/0.023192198 m, respectively, with contact=true and 82 N. Its min command/actual z in the observed envelope was 0.026995857/0.023192198 m; no actual touchdown or qualified raised-platform contact was recorded before the raw capture ended.

First-crossing command versus actual evidence:

| leg | frozen start p0 (x/z m) | valid/final commanded touchdown (x/z m) | first edge command (x/z m) | first edge actual (x/z m) | envelope min command/actual z (m) | touchdown actual (x/z m) | raised contact |
|---|---:|---:|---:|---:|---:|---:|---|
| FL | 0.509015097 / 0.025230552 | 0.850000000 / 0.075230552 | 0.778435267 / 0.130230552 | 0.777368072 / 0.042044500 | 0.130230552 / 0.042044500 | 0.785232410 / 0.046628094 | No |
| FR | 0.777146087 / 0.026927914 | fallback 0.880977774 / 0.026927914 (invalid plan) | 0.777150774 / 0.026995857 | 0.778506104 / 0.023192198 | 0.026995857 / 0.023192198 | Not recorded before capture end | No |

The first FL plan had x_entry=0.777 m, x_exit=0.823 m, and z_corridor=0.130230552 m. Its command was therefore geometrically valid and clear, while the actual foot showed an unambiguous execution blockage signature: actual z entered below the clear level with contact/force and landed 0.064767590 m short in x. This evidence identifies tracking/contact blockage for the crossing, without isolating a lower-level friction or actuator subcause.

Second FL `invalid_edge_ordering` at 14.854 s:

- `p0=(0.785232410, 0.046628094)`. `p_nom=(0.790137099, 0.042764916, 0.046628094)`. `p_probe=(0.818490387, 0.045511083, 0.046628094)`.
- Before validity rejection, the proposed frozen `p1` was `(0.850000000, 0.042764916, 0.096628094)` with effective lift 0.080 m.
- In source evaluation order, `p0.x < x_entry` was the first failed inequality: `0.785232410 < 0.777000000` is false. `x_entry < x_exit` passed (`0.777 < 0.823`), and `x_exit < p1.x` passed (`0.823 < 0.850`). The normalized checks also failed because `s_entry=-0.127106937` and `s_exit=0.583124831`, so `0 < s_entry < s_exit < 1` was false.
- The crossing latch still held because V2 was enabled, h0=0.000 m, and the probe height was h_probe=0.050 m: the latch condition is evaluated before `planning_valid`, and `0 < 0.050` with raised height above h0 is true. Validity rejection then reset the target to ordinary `p_nom`, rise=0, lift=0.028 m, and corridor=0.
- `p0` came from actual tracking/contact, not from the preceding planned target: the source captures the stance anchor from actual world-foot state, and the preceding FL actual touchdown is the exact same `(x,z)`. The preceding plan had commanded `(0.850000000, 0.075230552)` but actual touchdown was `(0.785232410, 0.046628094)`.

Causal judgment: `PRIMARY_TRACKING_CONTACT_DEFECT_WITH_PLANNER_RECOVERY_GAP`. The first crossing command was valid, but the actual FL foot failed to execute it; that miss placed the next FL start beyond the edge-entry boundary while still on the floor, and the V2 planner had no recovery path for that state and fell back to the ordinary target. This is not `PRIMARY_PLANNING_DEFECT`, because the observed second-swing invalid ordering is conditional on the preceding actual miss rather than inevitable under successful first-crossing tracking. The single next intervention target is **tracking/contact/control integration** for execution of the already-valid first FL crossing; planner geometry/recovery is not changed in that intervention.
