# Stage-three topic diagnosis: MJPC baseline and minimum discriminator

Status: READ-ONLY DIAGNOSIS / PROPOSAL ONLY; topic selection remains OPEN.
The verified RL friction card is a completed local experiment. Its two final
reviews accepted that frozen scope; they do not close the user's third stage
of finding a defensible research topic. No new method or experiment is started.

## What the evidence establishes

[Read-only evidence](evidence.json) binds inspected source and the unchanged
MJPC baseline1 raw SHA e5f760c54a57d12e8da6150972cb084414c3f9d84f1827ac9582b292532a3841.
It uses model compilation and raw scalar algebra only: zero mjData objects,
mj_forward, integration, private rollouts or optimizer calls.

The [sealed diagnosis](../rl_friction_reference_v1_prep_20261002/mjpc-readonly-diagnostic.md)
establishes final active foot-floor contact loss from2.450s and floor/RR_calf
STOP at2.574s. Last height0.305223m, vertical velocity-0.912632m/s and tilt0.329593rad
remain inside posture limits. Raw PD reconstruction matches exactly with the
documented joint mapping. The last motor clip is2.150s; RR calf is not clipped
at the last action. This weakens an immediate terminal clipping/mapping account,
but does not exclude earlier saturation effects. Private QACC time2.790 is
a rollout future warning, not a canonical physics warning or a causal timestamp.
A single trial and missing private prediction/contact/phase traces prevent
identification of a stable controller-family failure mechanism.

The source private model differs materially from the evaluation plant:

| Surface | Canonical plant | Private predictor |
|---|---:|---:|
|Joint viscous damping|0.1|2.0|
|Robot mass excluding mocap goal kg|15.206408|15.806408|
|Root-body mass kg|6.921|7.521|
|Floor plane z m|0|-0.01|
|Foot solimp XML|0.9,0.95,0.001,0.5,2|0.015,1,0.022,0.5,2|
|Integration timestep s|0.002|0.01 at runtime|
|Actuation|direct torque, clipped to40/45.43Nm|position-PD60/5, no force limit|

The source XML itself has2ms timestep; controller.cc overrides it to10ms.
Total source body mass23.044637kg includes a7.238229kg nonphysical mocap goal
and must not be reported as robot mass. Mass, damping and floor facts survive
the bridge's actuator bias correction. During optimization MakeDifferentiable
sets the first solimp component to0; the remaining source contact parameters
still differ. Both XML models have elliptic cone and impratio100, so missing
impratio100 is not an explanation. Named foot size/position/friction/condim/
priority/margin agree; the stiffness/impedance law and floor elevation do not.

At identical sealed joint velocities, the extra private passive damping force
is algebraically -1.9*qvel: all-joint mean absolute3.322790Nm, maximum32.715114Nm;
RR calf mean absolute4.287654Nm, maximum21.108323Nm. These are hypothetical
same-state force differences, not a replay of private prediction or proof of
causation. Canonical raw has20 clipped action frames/22 motor entries; a private
unclipped PD model cannot represent the same actuator law on those states.

## Effect on substrate and topic judgment

MuJoCo evaluation physics and the sealed passing RL baseline remain usable.
The evidence does not justify replacing the whole substrate or generalizing
this adapted candidate's failure to MJPC/iLQG. The current adapter lacks a
demonstrated useful locomotion baseline and now has concrete prediction-model
confounds. Therefore it cannot yet support a strong-comparator ranking or a
novel optimizer/contact-planning gap. Repairing these differences is engineering,
not a research contribution. Completing a benchmark is also not topic selection.

A bounded correction has value only if it cheaply determines whether a mature
gradient comparator can be recovered. The task/model and target/torque interfaces
already exist; begin with a source-bound compiled-model/force-law parity audit.
A physical horizon extension, gait tuning, reward sweep or from-scratch
controller is not the first repair. Cost is limited by the prospective cap below;
wall-time and private optimizer integration must be measured, not invented.
If this bounded check fails, park this adapted candidate rather than making
unlimited integration repair a prerequisite for all topic work.

## Minimum proposed experiment and why zero-forward is not first

Zero vx in the current bridge still means Walk + Manual Trot. Source Trot
prescribes duty0.45, cadence2Hz and amplitude0.03m; speed zero does not remove
swing or impose static stance. Changing to Stand also changes duty, amplitude
and balance/upright/height weights, so that is a bundled task/cost intervention.
Source Walk follows a moving head-position target, rather than directly
minimizing the evaluator's body-vx error. Zero-forward success would only show
translation demand is relevant under this task; failure would show nonzero
forward demand is not necessary. Neither outcome isolates model mismatch,
gait tracking or optimizer quality. It is a conditional follow-up, not a
mechanism diagnosis or a generic standing check.

The first proposal instead asks: does removing known private plant/actuator
mismatch change the failure under the SAME forward command and Manual Trot?

1. Before any physics, enumerate all mapped physical differences and bind a
   corrected private-model fixture to canonical robot mass/inertias, geometry,
   floor, passive joint properties, contact solimp/solref and effective
   PD-plus-torque-limit law. Explicitly retain/document the derivative
   smoothing step; do not claim the optimizer uses identical unsmoothed physics.
   Preserve native task sensors/sites and optimizer/task/gait settings.
   Keep the existing10ms prediction discretization declared, not silently
   claim exact dynamics. If force-limit placement or unnamed geom mapping
   cannot be proven, stop at engineering audit; do not run.
2. Add trajectory-neutral evidence output for selected current best trajectory,
   canonical-time anchor, predicted qpos/qvel and contacts/foot-clearance,
   gait phase/step targets, per-term cost and actuator saturation. Bind trace
   IDs to the actual applied policy. Reject missing/shifted evidence; scalar
   rollout-valid alone is insufficient. Do not add an algorithm.
3. Propose two NEW independent one-arm tasks: instrumented frozen adapter,
   then corrected private model, each3s/1500 canonical steps maximum
   (total3000;0.35s private horizon,20ms replanning,2ms feedback retained).
   Each has a fresh reset/claim/output, no retry; its first safety failure ends
   its task. No automatic continuation is authorized after a stop. Each task also proposes a300s wall ceiling and at most150 replan calls.
   A finite private-rollout step ceiling must be derived from the pinned
   optimizer configuration and counted before admission; it remains an
   explicit readiness gap, not an unbounded permission. Both need
   explicit scientific/execution admission and separate scope; never reopen
   the old campaign or its17 NOT_RUN arms. End-to-end runtime/evidence checks
   must establish that instrumentation preserves action semantics.
4. Record horizon/safety classification and actual/predicted contact timing,
   foot clearance, posture, saturation and tracking. A3s horizon crosses the
   known2.574s event; it cannot certify a12s useful baseline or statistical
   robustness. The pair is a total model-correction diagnostic, not a
   per-parameter ablation or independent statistical-seed comparison.

Interpretation: if the frozen arm shows the known stop and corrected arm avoids
it, the correction package is relevant and merits a separately frozen useful
baseline check; it does not identify which field caused recovery. If both stop,
inspect contemporaneous predicted-versus-actual landing evidence before selecting
a zero-forward or gait/task probe. If frozen no longer reproduces, trace identity
and nondeterminism before attributing recovery. If prediction contacts agree
but task remains unsafe/slow, model mismatch alone is insufficient; audit
task/cost/admission rather than immediately inventing a solver. Predeclare a
stop/park decision after these bounded tasks; no opportunistic tuning chain.

## Research questions that remain testable if this MJPC candidate is parked

| Question | Existing lead | Falsifier / admission limit |
|---|---|---|
|RL command-space limitations versus deployment semantics|Sealed half-speed/reverse/lateral/yaw failures; corrected yaw metric|Audit checkpoint commands/history/action mapping, then use a prospective aligned task; remove a candidate if deployment repair resolves it|
|RL temporal response to state age/decision cadence|Passing12s baseline and one exposed friction point provide anchors|Change one delivery/cadence mechanism with matched command/payload/exposure; remove the claim if effects are sampling/alias artifacts|
|RL friction robustness boundary under verified contact exposure|mu0.3-at6s PASS, modest paired tracking loss|Predeclare distinct conditions/perturbations; more PASS removes the proposed gap; one condition is not a map|
|Prediction/contact agreement of this adapted MPC|Concrete model confounds and missing prediction evidence|Admission above must first separate model/task artifacts; a repair-only explanation is engineering, not a paper gap|

These are investigation candidates, not selected paper topics or novelty claims.
A strong comparison can eventually use a different mature controller with its
own source-condition reproduction; it need not depend on recovering this MJPC
adapter. New papers/methods must be audited before any novelty verdict.
The original TOPIC_AUDIT's DOWNRANK/HOLD candidates remain unchanged: RR_calf
contact does not promote warm-start, contact search or the old hierarchy themes.


## Correct upstream configuration and existing methods

The local pinned checkout is e00c47a5adb9856af2e0f24231bb3a60d5be23c4
(subject: working go2 model), contained in local go2/origin-go2 refs.
Its task includes go2.xml. This rules out accidental use of default A1 assets
in the inspected predictor. The [author deployment README](https://github.com/johnzhang3/mujoco_mpc_deploy)
explicitly directs Go2 users to the go2 branch. A full source-condition
closed-loop reproduction remains absent; correct branch is not validation.

Both models use19 qpos/18 qvel and the same symmetric home at z0.27; names differ
in leg ordering (canonical FL,FR,RL,RR; source FR,FL,RR,RL), with explicit mapping
and exact raw PD reconstruction. Kp60/Kd5 matches the bridge's source contract;
RL's different gains are not a mapping defect. Source qpos seed/ctrl and canonical
zero-qvel/zero-ctrl reset are distinct interfaces and must remain explicit.
The source's nominal bias NONE is changed to AFFINE only in the private copy.

The [2025 paper](https://arxiv.org/html/2503.04613v2) already models joint PD
inside prediction and optimizes joint-position references, uses a soft gait
prior, TV-LQR feedback, asynchronous deployment and optional derivative skipping.
Its100Hz prediction and0.35s horizon are consistent with this pinned timing;
they are not by themselves implementation errors. Its reported model mismatch
tolerance does not validate this adaptation. These existing mechanisms cannot
be presented as new methods. Position-target task cost differs from body-vx
evaluation; forbidden nonfoot contacts are canonical safety semantics, not proof
that the source optimizer imposes that exclusion.

[RTWholeBodyMPPI](https://github.com/jrapudg/RTWholeBodyMPPI) is a published
whole-body sampling-MPC reference to audit if this comparator is parked.
It is not yet a source-locked/reproduced Go2 replacement here. DIAL remains
an optional sampling reference; no blind controller substitution is proposed.
