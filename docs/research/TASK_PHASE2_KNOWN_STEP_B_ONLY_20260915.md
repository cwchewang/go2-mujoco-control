# Phase2 checkpoint: B-only known-geometry 5 cm up-step traversal

Date: 2026-09-15
Prepared branch: `research/phase2-known-step-b-only-20260915`
Accepted readjudication: `9b782101d2fad1d3c64a80213cd741b8bd2e3179`
Accepted A runtime HEAD: `df5d7663adc9e96d153107e071d7b49676bcdad6`

Read `docs/research/PHASE1_AGENT_CONTRACT.md`, `docs/research/TASK_PHASE2_KNOWN_GEOMETRY_5CM_STEP_20260915.md`, and `docs/research/TASK_PHASE2_KNOWN_STEP_PRECONTACT_READJUDICATION_20260915.md` first. This task authorizes one B-only live run and freezes the interpretation below.

## 1. Why A is not rerun

The immutable A capture from the wall-clock-repair checkpoint was re-adjudicated offline with a geometry-valid pre-contact mask. Result: `PRECONTACT_BASELINE_HEALTHY_CONTACT_CONFOUNDED`.

Accepted A evidence:

- corrected active predicate: `motion_stage == 2` (the old `velocity_command_active` predicate was inapplicable because this full2 run did not use runtime velocity command);
- clean pre-contact mask: `motion_stage == 2`, `world_base_x_m <= 0.40 m`, every actual foot-center x `< 0.75 m`;
- 870 rows / 1.738 s clean pre-contact evidence;
- max |roll| = 0.034321602 rad;
- max |pitch| = 0.086687908 rad;
- SRBD success = 100%, ID success = 100%;
- WBC equality residual p95 = 6.4272e-06;
- adaptation enabled/active samples = 0;
- lockstep and paired HighState passed;
- first plausible step-contact risk = 14.616 s (FR foot center x=0.782261435 m, z=0.040634785 m);
- first 22-degree hard-posture crossing = 14.956 s;
- risk precedes hard posture by 0.340 s.

This checkpoint therefore treats A as the frozen negative-control arm. Do not rerun A.

Frozen A raw root on Atlas:

`example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`

The old A bytes must remain immutable.

## 2. Question

With the same deterministic locomotion runtime and the same fixed 5 cm full-width step, does enabling only the preregistered known-step swing touchdown-height / clearance adapter allow full traversal where the accepted A entered the step-interaction region and subsequently failed hard posture?

This is still a known-geometry locomotion experiment, not perception.

## 3. Exactly one live launch

Only one live launch is authorized:

- **B only**, DDS domain 232.

Use only:

`example/cpp/scripts/run_phase2_known_step_5cm_b_only.sh`

No A launch. No retry. No replacement domain. No extra seed. No GUI replay. No flat-floor control. No 10 cm run. No speed sweep. No parameter tuning.

If preflight fails before simulator/controller processes start, repair only the preflight/bookkeeping problem and document it. Once B simulator/controller starts, the single live budget is consumed.

## 4. Frozen runtime semantics

The B-only runner must remain semantically identical to the accepted wall-clock A except for:

- `TROT_KNOWN_STEP_TRAVERSAL=1`;
- administrative run root;
- DDS domain 232.

Frozen runtime arguments/environment:

- `SIM_LOCKSTEP=1`;
- `TROT_LOCKSTEP_PAIRED_HIGHSTATE=1`;
- `TROT_BRIDGE_ATOMIC_RECORD=1`;
- `TROT_DYNAMICS_TOLERANCE_N=20`;
- `FULL2_HOLD_CYCLES=999`;
- `TROT_KNOWN_STEP_EDGE_X_M=0.80`;
- `TROT_KNOWN_STEP_HEIGHT_M=0.05`;
- `TROT_KNOWN_STEP_HALF_WIDTH_Y_M=1.00`;
- D4 / PD pulse / D90 OFF;
- reactive obstacle / auto-environment OFF;
- `--headless --wall-clock-motion --controller-duration 34`;
- scene `unitree_robots/go2/scene_known_step_5cm.xml`;
- `--cartesian-world --wbc-full --kernel raibert-trot`;
- period 0.60 s, duty 0.75, step 0.091 m, base lift 0.028 m;
- Raibert gain 0.12, max adjustment 0.140 m;
- no world-feedback, no attitude-feedback;
- tau limit 35 Nm, preview horizon 4, max cycles 40.

Known-step adapter mathematics remain frozen exactly as previously implemented:

- nominal touchdown x/y unchanged;
- `rise = terrain_height(p1_nom) - terrain_height(p0)`;
- `p1.z = p0.z + rise`;
- `lift_eff = max(base_foot_lift, max(0,rise)+0.030)`;
- for floor->5 cm plateau crossing, rise=0.05 m and lift_eff=0.080 m;
- plateau->plateau must not accumulate another 5 cm.

No runtime source, scene, controller, WBC/MPC/ID, contact logic, gait timing, body-height reference, gains, safety thresholds, or adapter formula may be changed.

## 5. Pre-live source/binary provenance gate

Before B starts:

1. worktree clean;
2. diff audit from accepted A runtime HEAD `df5d7663...` to the pre-live B HEAD proves runtime-affecting source and scene are unchanged; only research docs, analysis-only files, and the dedicated B-only runner may differ;
3. run focused known-step adapter test, lockstep motion-clock integration test, controller CTest, simulator test_lockstep / CTest; all pass;
4. verify B-only runner contains exactly the frozen arguments above and cannot launch A;
5. verify frozen A raw files still match the readjudication/provenance hashes;
6. if the existing binaries are reused, require the hashes to match the accepted A capture:
   - controller SHA-256 `80c05a7750ef6782ff24955f7952dd391afce4c5406a15182bc712b36ef49ab3`;
   - simulator SHA-256 `b9f9e44a40d9b08cd6dce6632038819fab5ec0099e1628078c07185d5a808c9d`;
   - scene SHA-256 `8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc`.

If a rebuild is unavoidable, source/compile provenance must prove no runtime source changed; record both old and new binary hashes. Do not change code merely to recover the old hash.

## 6. Required analyzer before B

Before the live run, create and commit a B-only analyzer, preferably:

`example/cpp/tools/analysis/analyze_phase2_known_step_5cm_b_only.py`

It must read:

- frozen A from `example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`;
- new B from `example/cpp/experiments/_runs/phase2_known_step_5cm_b_only_20260915/B`.

Do not use `velocity_command_active` to define activity for either arm. For full2, locomotion activity is `motion_stage == 2`.

The analyzer and all thresholds must be committed before B begins. Analysis-only bug fixes after capture are allowed if documented, but B may never be rerun.

## 7. Exact pre-activation comparability

Find B's first sample where any leg has `known_step_*_adaptation_active == 1`.

From the common deterministic handoff through the final row strictly before that sample, compare A and B.

Require identical state-tick sequence and exact equality for every available causal state/control field, including at minimum:

- state/control clocks after handoff;
- motion stage, gait cycle and phase;
- world/base pose and velocity;
- IMU orientation, gyro and acceleration;
- physical contacts / foot forces;
- WBC/SRBD/ID outputs and contact mask;
- nominal Cartesian touchdown x/y/z before adaptation;
- actual foot x/y/z;
- all 12 motor q target, dq target, kp, kd, tau_ff, q state and dq state.

Allowed differences before activation are only intervention metadata that necessarily records feature enablement (for example the top-level known-step enabled flag). Final commanded Cartesian target, motor commands, gait reference, WBC output, and physical state must remain exact until first adaptation.

Any causal mismatch before activation -> `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`. Do not use a tolerance and do not rerun.

## 8. B isolation gates

Require all:

- feature enabled for B;
- D4 / PD pulse / D90 remain off;
- adaptation-active occurs only on scheduled swing legs with nonzero terrain rise;
- nominal touchdown x/y remain unchanged;
- final target z equals `swing_start_z + rise`;
- floor->plateau rise = 0.05 m within logging precision;
- floor->plateau effective lift = 0.080 m within logging precision;
- plateau->plateau produces zero additional rise;
- no gait timing, step length, speed policy, body-height reference, WBC/MPC/ID, contact schedule, gains or torque limits are changed by the intervention.

Any violation -> `PROTOCOL_FAILURE` unless it is specifically an exact pre-activation divergence.

## 9. B traversal success — frozen from original checkpoint

Derive each leg's floor-contact reference `z0_leg` from healthy pre-contact B samples before contact risk; references must be compatible with A's frozen pre-contact references.

B succeeds only if all are true:

1. world base x reaches at least 1.45 m;
2. after first reaching 1.45 m, base does not fall below 1.35 m for at least 0.50 s;
3. each FR/FL/RR/RL accumulates at least 0.10 s physical-contact time with actual foot x >=0.85 m and actual foot z >= `z0_leg + 0.035 m`, proving all four feet occupied the raised plateau;
4. no hard-safety marker and final controller/safety/quality/analysis/ground-truth/dynamics/completion statuses are zero;
5. max |roll| and |pitch| from the approach region through the post-crossing 0.50 s hold are <=0.25 rad;
6. WBC/SRBD/ID success is 100% where valid and equality residual p95 <=1e-3;
7. no persistent commanded/actual-foot divergence consistent with being dragged over the edge.

Do not weaken these thresholds after seeing B.

## 10. Secondary metrics

Report:

- first B adaptation time and leg;
- each adapted swing's rise and effective lift;
- base x at first adaptation;
- first plausible contact-risk time using the same readjudication definition `foot-center x>=0.778 m and z<=0.072 m`;
- each leg's first raised-platform touchdown and cumulative raised contact;
- base crossing times x=0.80 and 1.45 m;
- signed/max/p95 roll and pitch;
- base vertical velocity;
- contact-count distribution and touchdown intervals;
- commanded vs actual foot z around raised touchdown;
- torque RMS/p95/max and saturation evidence;
- WBC/SRBD/ID success/residuals.

## 11. Classification

Use exactly one:

- `SUPPORTED_ENABLES_TRAVERSAL`: exact pre-activation equality passes, isolation/protocol pass, and B satisfies full traversal success. The frozen A is the negative control and is not a successful traversal.
- `ADAPTATION_FAILED`: exact pre-activation equality and isolation/protocol pass, but B does not satisfy full traversal success. Report whether the proximate failure is safety, inability to mount the step, rear-leg completion, solver/contact failure, or another measured reason; do not tune.
- `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`: causal exact equality fails before first B adaptation.
- `PROTOCOL_FAILURE`: provenance, run budget, lockstep/paired-state, intervention isolation, or evidence-schema requirements fail.

## 12. Required closeout

Write under:

`docs/validation/phase2_known_step_5cm_b_only_20260915/`

At minimum:

- `RESULTS.md`;
- `analysis.json`;
- `preactivation_exact.csv`;
- `adaptation_isolation.csv`;
- `touchdown_summary.csv`;
- `protocol_gates.csv`;
- `provenance.csv`.

Record accepted A SHA/provenance, B runtime HEAD, run domain 232, launch count, clean worktree state, test results, simulator/controller/scene hashes, first adaptation, exact-comparison result, isolation gates, success metrics, final classification.

Commit and push closeout, then stop. No follow-up terrain experiment is authorized in this checkpoint.
