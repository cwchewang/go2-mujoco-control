# Independent RL sliding-friction reference v1

This task asks whether the already passing frozen RL adapter sustains the same
12 s flat task after one fixed four-foot sliding-friction change. The result
decides whether this card supplies a bounded RL condition effect worth retaining
in the capability map; it does not select a controller family or explain MJPC.

Mode: prospective bounded scientific task, first delivery is FROZEN / NOT_RUN.
Parent: `d4bccb60f4fb8c6a63ed85da409b29c0b642cec8`.
Branch: `research/rl-friction-reference-prep-20261002`.
Protocol: [rl_sliding_friction_reference_v1.json](../../tools/substrate/protocols/rl_sliding_friction_reference_v1.json).

The user's continuing three-stage delegation and explicit new two-repeat
RL-only friction request cover preparation. The parent coordinates incremental
science and execution review before START. This task document and its precheck
do not grant live execution readiness. Prior campaign reviews remain historical.

## Decision and scientific delta

The old [shared campaign closeout](../validation/shared_baseline_probes_v1_closeout_20261002/RESULTS.md)
provides two complete passing RL baseline traces with identical raw bytes. Its
MJPC safety stop permanently closed that campaign, including all17 skipped arms.
This new id, output root, arm ids and ledger are independent. Old17 NOT_RUN arms,
old claims and sealed raw are immutable. No new baseline or MJPC physics is planned.

The single strength is the user-selected exploratory card: four foot geom
sliding mu0.8 to0.3 at6 s/tick3000, through tick5999. It is not an estimate of a
friction threshold. Two fresh resets use the unchanged home key0, model,
checkpoint, CPU policy/adapter, body-frame1 m/s command/ramp, proprioception,
zero latency,2 ms physics and20 ms RL decision/feedback, offline_unbounded
semantics. Torsional/rolling friction and floor/contact settings stay inherited.
The inherited task's six stop classes and all posture/lateral/nonfinite/warning/
contact thresholds remain intact; the operational performance thresholds also
stay inherited. No policy/controller tuning is allowed.

Repeat j pairs only with sealed `rl_baseline_j`, at the exact captured head and
raw SHA bound in the prospective protocol. The new task independently verifies
those two passing repeatable own references; it does not reopen the old
campaign's incomplete four-baseline gate.

## Budget, evidence and prospective analysis

The protocol binds two scientific attempts,6000 canonical steps each,12000
total. There is no retry, replacement, added seed or later card. The unchanged
engine consumes an attempt at the first valid post-handoff state/control sample.
A safety, execution or evidence failure stops the whole new campaign. The
unstarted second repeat remains NOT_RUN with the stop reason. Valid complete
horizon performance failures are retained; the predeclared second repeat may
continue. No challenge PASS is available without verified complete effective
exposure.

Reuse the existing `BoundedCondition(sliding_friction)`, shared episode/raw
writer, `verify_condition`, primary replay and whole-campaign STOP engine.
Verify the paired raw qpos/qvel, command, information, controller update, targets
and actions through the onset snapshot/action at tick3000 (the hook runs after
that snapshot). Verify actual active foot-floor contact friction, not only the
model assignment. The raw contact constraints/friction records are exposure
evidence; no contact-force claim is implied.

Primary classification remains the original [2,12) operational window and
whole-episode lateral/yaw bounds. The new auxiliary window is declared now:
[6,12), exactly ticks3000..5999,3000 body-vx samples; mean, MAE against1 m/s,
and actual-minus-paired-baseline mean/MAE deltas. Tick6000 is excluded.
Incomplete/safety windows report NOT_MEASURABLE with null values and no partial
score. Auxiliary metrics have no thresholds and never change primary PASS/FAIL.

Two fixed-condition deterministic repeats establish repeatability under these
inputs. No statistical success rate, general robustness, controller ranking,
private-planner failure mechanism or paper claim follows. A complete valid
failure supplies a bounded observation; an invalid/safety-stopped campaign
limits evidence to its recorded prefix. All outcomes close this task at its
frozen budget. Any next physical question requires a new prospective task.

## First delivery and remaining execution work

`python -m tools.substrate.rl_friction_reference --output <fresh-absolute-path>`
only freezes/checks the new spec, official old capture/real ledger, passing
reference pair, static canonical model/checkpoint and auxiliary algebra. It has
no capture/START API. The precheck takes the existing experiment lock, forbids
canonical integration and makes no policy/native planner calls.

[PRECHECK](../validation/rl_friction_reference_v1_prep_20261002/PRECHECK.md)
records the exact checks and evidence. New scientific attempts and canonical/
private physics remain0. The original runner sources are unchanged.

Before live execution, minimally bind the independent two-arm catalog and the
sealed references to that engine, create applicable clean qualification for the
actual new runtime inputs, review that binding increment, then hold the shared
lock through fresh preflight and capture. The old whole-input qualification is
reference provenance only and is not admission for a changed fingerprint.
No current-head execution qualification or live preflight is claimed here.
