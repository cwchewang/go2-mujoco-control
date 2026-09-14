# Phase2 checkpoint: known-geometry 5 cm up-step traversal

Date: 2026-09-15
Prepared branch: `research/phase2-known-geometry-5cm-step-20260915`
Accepted parent evidence: `17c659635c7ee59d80947e10358366ea3477dba4`

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first. This task is authoritative over older terrain/reactive-event documents.

## 1. Question

Can the accepted deterministic D4-off locomotion stack traverse one fixed, full-width 5 cm up-step when the controller is given exact step geometry and is allowed to modify only swing-foot touchdown height and swing clearance?

This is the first terrain-conditioned locomotion checkpoint. It is deliberately **not** a perception experiment, not obstacle classification, not a scripted joint animation, and not a high-speed experiment.

The desired control form is:

`known terrain geometry + current gait/swing state -> online Cartesian swing target adaptation`

The existing WBC/MPC plant and gait remain continuously active.

## 2. Frozen scope

### Environment

Use only `unitree_robots/go2/scene_known_step_5cm.xml` prepared on this branch.

Geometry is frozen:

- leading edge: world `x = 0.80 m`;
- plateau height above floor: `0.05 m`;
- lateral half-width: `1.00 m`;
- plateau extends beyond the evaluation region.

Do not change the scene after a live run begins. Do not move, resize, bevel, soften, or lower the step.

### Baseline gait

Use `example/cpp/scripts/run_phase2_known_step_5cm_ab.sh` exactly. It intentionally uses the established `full2` Cartesian-world seed rather than the Phase1 2.3 m/s sprint:

- `--cartesian-world --wbc-full --kernel raibert-trot`
- period `0.60 s`, duty `0.75`, step length `0.091 m`, foot lift `0.028 m`;
- Raibert gain `0.12`, max adjustment `0.140 m`;
- tau limit `35 Nm`, preview horizon 4;
- no world-feedback or attitude-feedback overlays;
- `FULL2_HOLD_CYCLES=999` so this checkpoint does not turn into a speed-ramp experiment;
- `SIM_LOCKSTEP=1` and `TROT_LOCKSTEP_PAIRED_HIGHSTATE=1`;
- D4 and every prior diagnostic intervention OFF;
- `--auto-environment` and reactive obstacle events OFF. The old obstacle-turn-away path must not participate.

Do not change period, duty, step length, foot lift, Raibert gains, WBC/SRBD/ID weights, contact logic, body-height reference, torque limits, scene, or speed policy after preregistration.

## 3. Arms and run budget

Exactly two live process launches are authorized, in this order:

- **A**: same 5 cm step scene, known-step traversal adaptation OFF, DDS domain 229.
- **B**: identical runtime and scene, `TROT_KNOWN_STEP_TRAVERSAL=1`, DDS domain 230.

A may physically fail at the step; that does not by itself block B. B is allowed only if A passes the **pre-step A gate** below.

No retries, replacement domains, extra seeds, replicate runs, GUI replays, parameter sweeps, height sweeps, speed sweeps, or follow-on experiments. A process that never starts because a preflight detects a missing binary is not a live launch; document it exactly. Once a simulator/controller process starts for an arm, that arm is consumed.

## 4. Required implementation before any live run

Implement a small opt-in known-step geometry adapter. Keep it isolated and unit-testable; a pure helper header is preferred.

Environment controls:

- `TROT_KNOWN_STEP_TRAVERSAL=1` enables it;
- `TROT_KNOWN_STEP_EDGE_X_M=0.80`;
- `TROT_KNOWN_STEP_HEIGHT_M=0.05`;
- `TROT_KNOWN_STEP_HALF_WIDTH_Y_M=1.00`.

The helper must expose the terrain height for this one step:

- within lateral width and `x < edge`: `h = 0`;
- within lateral width and `x >= edge`: `h = step_height`;
- outside lateral width: `h = 0`.

For each leg while it is in swing, begin from the **unchanged nominal Cartesian-world Raibert touchdown x/y**. Let:

- `p0` = captured world swing-start foot point;
- `p1_nom` = ordinary nominal world touchdown from the existing planner;
- `h0 = terrain_height(p0.x, p0.y)`;
- `h1 = terrain_height(p1_nom.x, p1_nom.y)`;
- `rise = h1 - h0`.

When the feature is enabled, apply exactly:

`p1.z = p0.z + rise`

and use per-leg effective swing lift:

`lift_eff = max(base_foot_lift, max(0, rise) + 0.030 m)`.

For this 5 cm up-step, an actual crossing swing therefore uses `lift_eff = 0.080 m` because the baseline lift is 0.028 m.

When disabled, or when `rise == 0`, behavior must be exactly the existing nominal behavior.

### Explicit prohibitions

This checkpoint must **not**:

- change nominal touchdown x or y;
- snap footholds away from the edge;
- change gait phase, period, duty, speed command, or step length;
- change base-height reference or pitch/roll reference;
- change contact schedule or contact merge logic;
- change WBC, SRBD MPC, ID-WBC, gains, force references, torque limits, q/kp/kd/tau_ff logic, or D4;
- consume `environment_heightmap` or trigger `obstacle_left/right`;
- play a prerecorded joint trajectory or special per-leg animation;
- use knowledge of future A/B results to revise the formula.

The geometry adapter may affect joint commands only indirectly through the existing Cartesian swing target -> IK/WBC path.

## 5. Required diagnostics

Before any live run, add CSV telemetry sufficient to audit the intervention without inference. Use stable names and document them in the analyzer. At minimum record:

- feature enabled;
- edge x, height, half-width;
- per-leg scheduled stance/swing;
- per-leg swing-start world x/z;
- per-leg nominal touchdown world x/z before adaptation;
- per-leg terrain `h0`, `h1`, `rise`;
- per-leg effective lift;
- per-leg final commanded Cartesian target world x/z;
- per-leg actual world foot x/z;
- per-leg adaptation-active boolean.

Existing attitude, contacts, WBC/SRBD/ID, torque and world-base telemetry must remain available.

Do not repurpose D4 diagnostic columns for this feature.

## 6. Unit/source gates before runtime

Add focused tests covering at least:

1. feature disabled -> exact identity;
2. floor -> floor -> zero rise and baseline lift;
3. floor -> plateau -> `+0.05 m` touchdown z and `0.080 m` effective lift;
4. plateau -> plateau -> zero rise and baseline lift (no repeated +5 cm accumulation);
5. lateral point outside the step width -> floor height;
6. nominal x/y remain bitwise/equivalent unchanged by the adapter;
7. swing position and swing velocity use the same per-leg effective lift.

Run the normal build, `test_lockstep`, and full CTest. All tests must pass before A.

Perform a source audit proving the opt-in path does not modify any prohibited subsystem. Record changed files and the exact runtime implementation commit.

All runtime-affecting implementation and the analyzer must be committed before A. The worktree must be clean before A. After A begins, no runtime source, scene, runner, parameter, or acceptance threshold may change. Analysis-only repairs are allowed after capture only if documented and no runtime is rerun.

## 7. Pre-step A gate

After A, run the prepared analyzer in `--a-gate-only` mode. B is authorized only if all are true before the robot reaches `world_base_x_m = 0.65 m` (15 cm before the step):

- lockstep protocol passes;
- paired HighState has zero validation failures and zero async fallbacks;
- A adaptation is disabled and no adaptation-active sample exists;
- controller/safety/quality statuses remain zero;
- no hard-safety marker;
- gait reaches active locomotion and base advances forward to at least `x = 0.60 m`;
- WBC/SRBD/ID solver status is healthy;
- no source/provenance mismatch.

A is **not** required to traverse the step. A collision, stop, or failure after the pre-step region is valid baseline evidence and does not block B.

If this gate fails: classify `BASELINE_GATE_FAILED`, do not run B, close out and stop.

## 8. Exact pre-activation comparability

After B, compare A and B from the common deterministic handoff through the last row strictly before B's first `adaptation_active` sample.

Require identical row count/timestamps and exact equality for all available causal state/control fields, including:

- state/control clocks and gait phase/cycle;
- world/base pose and velocity;
- IMU;
- contacts;
- WBC/SRBD/ID outputs;
- nominal Cartesian swing targets;
- all 12 motor q/dq targets, kp, kd, tau_ff, q/dq state.

The enabled metadata flag itself may differ. Before activation, no final Cartesian target or motor-control field may differ.

Any causal difference before activation -> `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`. Do not relax to a tolerance and do not rerun.

## 9. B isolation gates

B must show all of the following:

- D4 remains off;
- adaptation is nonzero only on swing legs whose `h1 != h0`;
- nominal touchdown x/y are unchanged;
- final target z follows `p0.z + rise`;
- floor->plateau rise is exactly 0.05 m within float/log precision;
- crossing-swing effective lift is 0.080 m within float/log precision;
- plateau->plateau does not accumulate another 0.05 m;
- no base-height, gait timing, speed, WBC, contact-schedule, gain, torque-limit, or other intervention is activated.

Violation -> `PROTOCOL_FAILURE` unless the violation is specifically a pre-activation causal divergence.

## 10. Traversal success definition

Derive each leg's floor-contact foot-center reference `z0_leg` from healthy pre-step A/B contact samples before `x=0.60 m`; A/B references must agree.

An arm is a **successful full traversal** only if all are true:

1. world base x reaches at least `edge + 0.65 = 1.45 m`;
2. after first reaching 1.45 m it does not fall back below `edge + 0.55 = 1.35 m` for at least 0.50 s of state time;
3. each of FR/FL/RR/RL obtains at least 0.10 s cumulative physical-contact time after the edge with actual foot `x >= 0.85 m` and actual foot `z >= z0_leg + 0.035 m`, demonstrating all four feet have genuinely occupied the raised platform;
4. no hard-safety marker and all final statuses are zero;
5. max absolute roll and pitch from base x=0.60 through the 0.50 s post-crossing hold are each <= `0.25 rad`;
6. WBC/SRBD/ID solver success remains 100% where those diagnostics are valid and WBC equation residual p95 <= `1e-3`;
7. there is no persistent command/actual-foot divergence indicating the robot was merely dragged over the edge.

If a raw channel required for a criterion is unavailable, add the preregistered telemetry before runtime; do not weaken the criterion after the run.

## 11. Secondary metrics (report, do not gate unless above says so)

For A and B report:

- whether full traversal succeeded;
- first base crossing time for x=0.80 and 1.45 m;
- each leg's first raised-platform touchdown and cumulative raised-platform contact time;
- max/p95 signed and absolute roll/pitch in the step window;
- peak/p95 absolute world-base vertical velocity;
- physical contact-count distribution and touchdown intervals;
- commanded vs actual foot z around each first raised touchdown;
- max Cartesian foot tracking error if available;
- effective torque RMS/p95/max and saturation evidence;
- WBC/SRBD/ID solver and residual statistics;
- number/timing of adapted swings and their rise/lift values.

Do not invent a slip conclusion if support-foot kinematics are unavailable.

## 12. Classification

Use exactly one top-level label:

- `SUPPORTED_ENABLES_TRAVERSAL`: all protocol/isolation/comparability gates pass, A is not a successful full traversal, and B is.
- `SUPPORTED_SAFE_TRAVERSAL_BASELINE_ALSO_PASSES`: all gates pass and both A and B are successful full traversals. This validates the terrain-conditioned mechanism but does **not** claim it was necessary at 5 cm.
- `ADAPTATION_FAILED`: pre-step A gate passes, comparability/isolation/protocol pass, but B does not satisfy full traversal success.
- `ADAPTATION_HARMFUL`: A succeeds, B fails while protocol/isolation/comparability pass.
- `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`: exact pre-activation causal equality fails.
- `BASELINE_GATE_FAILED`: A is unhealthy before the step.
- `PROTOCOL_FAILURE`: run-order, lockstep, paired-state, provenance, isolation, unauthorized-change, or evidence-schema failure.

Do not change these labels or thresholds after seeing data.

## 13. Required analyzer and artifacts

Before A, create `example/cpp/tools/analysis/analyze_phase2_known_step_5cm.py` with:

- `--a-gate-only` mode;
- full A/B mode;
- exact pre-activation comparison;
- isolation checks;
- traversal-success calculation;
- secondary metrics;
- provenance hashes.

Full analysis must write at least:

- `docs/validation/phase2_known_step_5cm_20260915/RESULTS.md`;
- `analysis.json`;
- `arm_summary.csv`;
- `preactivation_exact.csv`;
- `adaptation_isolation.csv`;
- `touchdown_summary.csv`;
- `protocol_gates.csv`;
- `provenance.csv`.

If useful, add plots for base x/z, signed roll/pitch, per-leg foot x/z, and adapted target z/lift; plots are supporting evidence, not substitutes for machine-readable gates.

## 14. Closeout

Record:

- prepared parent SHA;
- runtime implementation HEAD;
- final closeout HEAD;
- clean pre-run worktree status;
- exact A/B domains and launch count;
- simulator/controller/scene SHA-256;
- relevant environment and argv;
- all test results;
- A-gate decision before B;
- final classification and every gate/metric needed to reproduce it.

Commit and push the closeout to this branch, then stop. Do not run a 10 cm step, speed sweep, perception experiment, height-map version, D4 variant, or any other follow-up in this checkpoint.
