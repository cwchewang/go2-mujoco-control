# Shared baseline and bounded probes v1: candidate preparation

Status: candidate freeze / zero-physics engineering package; NOT LIVE READY.

## Decision and authority

Determine whether each frozen controller has a reproducible, useful 12 s shared
flat baseline before testing its response to four finite conditions. This serves
Gate 0 in [PROJECT_RECORD](../PROJECT_RECORD.md); it does not select a research
mechanism or establish an equal-information ranking.

Parent: ab27185f6c0ee47fdd09fecb367977bf4ab9cfde.
Branch: research/shared-baseline-probes-prep-20261002.
Owner: delegated Go2 engineering worker; parent coordinates independent reviews.
The accepted [v2 engineering closeout](../validation/aligned_flat_capture_v2_closeout_20261002/RESULTS.md)
is closed, and its broad 1 s PASS is not a capability baseline.

The user's 2026-10-02 three-stage delegation and instruction to continue cover
preparation. Preserve those source messages when binding the next exact capture
HEAD, protocol, preparation and budget; no repeated user confirmation is needed
for the same delegation. The v2 START is specific to v2 and cannot be reused.
This candidate protocol self-authorizes no physics. Any new physical capture
requires independent science/execution admission and fresh preflight.

## Source conditions before shared migration

| Surface | Pinned RL source / sealed evidence | Pinned MJPC source | Prospective shared condition |
| --- | --- | --- | --- |
| Source | wty-yy/go2_rl_gym 30e74dc507bec7a642a8c98be26081f2c6f0822d; checkpoint SHA in sources.lock | johnzhang3/mujoco_mpc e00c47a5adb9856af2e0f24231bb3a60d5be23c4 | Same pinned controller identities; no training/tuning |
| Model/reset | Source model, default MjData posture; first inference tick10; source1m/s reference already sealed | QuadrupedFlat Go2 home at0.27m; original position actuators have nominal mjBIAS_NONE despite gain/bias | Canonical phase2_flat, home key0, identity heading, zero qvel/ctrl; first controller action tick0 |
| Observation | Proprioceptive45-vector, previous policy action/history, no privileged state | WholeBodyState and private planning model | These unequal regimes remain explicit; no equal-information claim |
| Action | Position target with source PD20/0.5 | Position target with source PD60/5 | Named targets to direct torque; PD recomputed every2ms, canonical motor ranges unchanged |
| Timing | 50Hz policy, 500Hz physics/PD in sealed simulation baseline | Audited deployment2ms LowCmd write and separate asynchronous action loop; private planner timestep10ms/horizon0.35s | RL policy20ms; MJPC planning20ms/feedback2ms; all offline_unbounded |
| Changes | Shared model/home/interface combination has separate sealed evidence, but this warmup and tick0 start are new | Private-only mjBIAS_AFFINE correction, Manual/Trot Walk, Ground/fresh-plan/transport hardening | Shared MJPC is an adapted candidate, not a native reproduction |
| Evidence | Source1m/s12s PASS already sealed; reuse, do not rerun | No source-condition12s capability reproduction claimed | Two own shared baselines per controller; do not infer maturity from v2 |

Sources: [source lock](../../tools/substrate/sources.lock.json),
[sealed RL source baseline](../validation/rl_baseline_20260923/RESULTS.md),
[shared transfer](../validation/shared_transfer_combination_formal_v2_20260923/RESULTS.md),
[native adapter audit](../validation/r1_native_mjpc_shared_adapter_20261001/RESULTS.md),
[clock audit](../validation/r1_mjpc_feedback_cadence_20261001/RESULTS.md).
The pinned MJPC task XML was inspected locally; it retains native cost/gait
weights and optimizer settings. No new upstream run or literature search is
part of this package.

## Unique candidate protocol and acceptance rationale

The sole prospective constants are in
[shared_baseline_probes_v1.json](../../tools/substrate/protocols/shared_baseline_probes_v1.json).
It binds the accepted anchor SHA, scene physical fingerprint, reset, command
ramp, information, timings, controller sources and safety semantics. Only the
horizon and measurement start change for the baseline.

The 12 s task commands body-forward 1 m/s after the anchor's 0.1 s zero and 0.2 s ramp.
The half-open 2--12 s velocity window excludes startup and the terminal endpoint.
The prospective operational mean/MAE and lateral/yaw limits reuse the sealed
RL1m/s acceptance scale as an engineering requirement. They are not validated
MJPC author requirements, nor a result-dependent adaptation. Lateral and yaw
maxima use the whole episode, including the terminal frame. Review this common
requirement before calling either baseline useful.

The broad CanonicalEvaluator progress/MAE guardrails remain separately labelled.
They do not decide operational baseline PASS. Canonical safety still uses the
six accepted failure classes, tilt0.8rad, height0.12--0.55m and lateral0.4m.
These are conservative simulation stop lines inherited from the anchor, not
hardware safety or a newly validated locomotion envelope.

Two valid operational PASS baselines and max absolute repeated raw state/applied
control difference at most1e-9 are required for that controller's stage3 entry.
This tolerance is a prospective same-machine deterministic engineering
assumption requiring review. Two repeats are not independent statistics or a
success-rate estimate. Different native wall times are retained but excluded
from the dynamics comparison.

## Four single-strength condition cards

Each arm changes one declared condition, never combines cards. Each condition
has exactly one frozen strength. Report within-controller changes from its own
baseline; differing controller information prevents a fair-information ranking.

| Card | Unique variable / strength | Interface and time | Required actual evidence |
| --- | --- | --- | --- |
| Sliding friction | Four foot sliding coefficients0.8 to0.3; other components fixed | Canonical geom_friction[feet,0], from6s through episode end | Active foot-floor friction[0.3,0.3,0.02,0.01,0.01], condim6; physical fingerprints before/after |
| Observation delay | Measurement transport0 to20ms | Immutable sampled-state buffer for whole episode | Original payload and sample/available/controller times; current native clock explicitly separate |
| Decision period | Policy/replan20 to40ms | Whole episode; RL target hold40ms, MJPC feedback remains2ms | Real policy update/replan ticks, sample times and held actions |
| Lateral force | Base world-y0 to50N for0.2s | xfrc_applied[base_link],6--6.2s | Actual six-component world wrench every tick;100 force ticks and10N*s input impulse; cleanup |

These strengths are prospective engineering probe hypotheses, not source-derived
robustness thresholds. Delay equals one baseline decision period; the timing
probe halves the decision rate; friction becomes37.5% of the baseline sliding
parameter; the push supplies a bounded10N*s input. Each tests response to one
finite degradation without searching intensities or fitting a boundary.

For delay, initial reset state is explicitly available during the first20ms.
No negative-time samples are fabricated. Afterwards the full measurement packet
is20ms old. The native packet carries the current control time while the original
measurement timestamp remains in evidence. Current-state PD realizes the target
each physics tick: the intervention delays controller observations, not the
low-level PD loop. The policy's internal previous-action memory is not delayed.

For friction, geometry, priority, contact dimension, torsional/rolling friction
and controller private model are fixed. Only the foot sliding parameter changes.
The resulting mismatch with unchanged MJPC prediction makes this a total
condition-effect probe, not pure contact-mechanism attribution. An absent or
incorrect actual changed contact is insufficient/invalid evidence.

The force is a prescribed input impulse, not proof of a particular velocity
change or recovery mechanism. The fixed world direction is part of the card.
The slower period tests decision-rate sensitivity, not compute-budget or
real-time capability.

## Budget, stopping and interpretation

Baseline order: rl_1, rl_2, mjpc_1, mjpc_2. Then for each eligible controller,
card order friction, delay, period, force, each with two fresh repeats.
Each repeat starts a fresh plant/controller process or policy instance and
reset state; no cross-arm histories. Reserve each attempt durably before its
first valid action, using the existing external ledger discipline.

Maximum 4 baseline plus 16 challenge attempts, each 6000 canonical steps:
120000 steps / 240 simulated seconds. Skipped arms remain NOT_RUN; no substitutes.
Native private planning work is separately measured, never called canonical
evaluation steps. Proposed per-arm execution watchdog300s follows v2 plumbing;
it is not a real-time bound. Failed prelaunch output remains immutable.

Safety or execution/evidence failures stop the whole campaign. Complete-horizon
performance failures remain outcomes and may continue the predefined matrix;
a failed or nonrepeatable own baseline prevents its stage3 arms. No opportunistic
retry, recovery, tuning, threshold change or extra budget is permitted.

PASS/response degradation can support only this condition's bounded within-
controller result. Baseline failure means the candidate is not ready for these
probes; diagnose offline and close without chasing PASS. Invalid or ineffective
conditions yield insufficient evidence. All probes passing removes these
particular failures as candidates; it does not prove a continuous boundary.
Stage3 may close with no positive scientific finding.

Raw JSONL replay, independent scalar quaternion/body-vx algebra, external ledger
checks and actual contact static reconstruction require zero additional physics.
No replayed dynamics or physical regression is budgeted in preparation. Any
later need for one requires an explicit amended budget and admission.

## Engineering package and next gate

[shared_baseline.py](../../tools/substrate/shared_baseline.py) loads the candidate
and computes operational metrics separately from the physical oracle.
[bounded_conditions.py](../../tools/substrate/bounded_conditions.py) implements
the four closed conditions through an explicit optional episode argument.
Existing calls without a condition retain their previous semantics and nonzero
latency still fails closed without the matching hook.

Tests use FakePlant for episode clocks/delay/holds and real compiled model
mj_forward only for contact/friction and applied-input checks. All three native
integration functions are guarded. Cleanup on evidence exceptions is checked.

This package deliberately has no stage2/3 live campaign CLI. Before launch, add
the smallest specific campaign runner binding these hooks, budget, eligibility,
external claims, fresh instances, durable campaign stops and per-arm watchdog.
Then perform clean qualification, snapshot preparation, both exact-head reviews
and fresh lock/process/input preflight. Use new prepared/authorization bindings,
never v2 receipts. No runtime START is provided by this document.

Completion: candidate loader, hook implementation and guarded precheck available
for independent semantic/execution review, with v2 closeout persisted and
navigation corrected. Test and review status is recorded in
[preparation results](../validation/shared_baseline_probes_prep_20261002/RESULTS.md).
