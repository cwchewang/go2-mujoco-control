# Public RL source baseline

User direction: “推进实际研究吧，把 RL 部分做到理想为止”; clarified as
“先把公开策略做成可靠、能力清楚的研究基线”. This supersedes the temporary
foundation-only hold. No training, fine-tuning or checkpoint substitution.
Parent: `81dec52dd3c83c6ffeae1f0f053dea4358eb80c4`.
Branch: `research/rl-baseline-20260923`.

## Decision and design

Can the already integrated public CTS checkpoint serve as a reproducible,
bounded forward-locomotion reference? Establish deployment validity before
judging capability or comparing controllers. This checkpoint is the pinned
upstream YAML default, not a proven optimum or the sum of all paper demos.
Source repository and asset hashes are in `tools/substrate/rl_reference.lock.json`;
checkpoint identity remains in `sources.lock.json`.

The executable protocol is `tools/substrate/protocols/rl_source_v1.json`.
Ten ordered cases, no reserves or retries: source flat 1 m/s and identical repeat;
shared policy adapter with identical plant/startup; source flat 0.15 and 0.3 m/s;
source variable speed; isolated startup timing, reset, and model changes;
source default +X cross-stairs. Each case reloads the checkpoint and MjData.
Only the explicit variable changes. Source uses direct PD control and the XML's
joint force limits; shared-model arm retains that model's actuator limits.

1 m/s is the upstream command default. Twelve simulated seconds provide two
seconds of startup and ten seconds of measurement, not a statistical sample.
Reference usability means mean body-forward speed >=0.8 m/s and MAE <=0.2 m/s,
with lateral displacement <=0.3 m and yaw excursion <=0.3 rad: a declared 20%
engineering tracking requirement for a useful forward reference, not an upstream
claim. All raw values are reported. Low-speed descriptive tracking tolerance is
max(0.05 m/s, 20% of command); it does not change the historical v1 verdict.
Variable commands 1, 0.5, 1.5, 0 m/s each last five seconds, excluding the first
second of each segment from steady metrics. Transition traces remain available.

The pinned default cross-stairs direction has 0.23 m risers, 1.84 m summit,
first edge x=2 m and last edge x=8.25 m. Twenty seconds is a bounded crossing
probe. Success requires base x>=8.7 and all four foot centers x>=8.3, with
|base y|<=1.3 m continuously for 0.5 s. A goal timeout is a negative result,
not proof of universal terrain incapability. Terrain-relative clearance is
reported; there is no flat-world maximum-height guard on stairs.

## Validity, stopping and interpretation

Source repeat is independent and still runs after a performance-only reference
failure; it measures the repeatability of that negative outcome. Source flat
repeat and shared adapter require identical trajectory digests
(qpos/qvel/control/target, excluding timings). A mismatch stops the campaign as
an integrity failure. Cases 3,7,8,9 depend on usable case 1; case 3 and transfer
cases also require repeatability. Other source capability cases are independent
performance probes. Expected tracking/goal failures remain outcomes and do not
stop the matrix. Nonfinite state/control, quaternion error, MuJoCo warnings,
base-ground contact, tilt >1.2 rad, clearance <0.06 m, |y|>1.5 m, source changes,
timeout or evidence failure stop the whole campaign. Leg/foot terrain contact
is retained and reported, not treated as a fall. No boot recovery is reserved.

Metric windows are [segment start + delay, segment end), at .002 s intervals.
Body velocity uses the quaternion rotation, lateral excursion is relative to
initial y, and yaw is unwrapped and relative to initial yaw. Clearance uses the
highest collision plane/box top under the base origin XY, excluding visual-only
labels; base contact includes all static terrain collision geometries. Stairs
success is safe crossing, not a requirement of support on each individual step.

The headless source loop matches initial MjData, .002 s step, PD every step,
and first inference after ten steps. The finite endpoint omits an unused final
inference. Telemetry forwards a separate MjData only; it never forwards the live
plant between steps. Runtime is our pinned CPU stack; exact original training
environment and historical deployment runtime remain unknown.

One-factor differences establish effects in these local conditions only. They
do not decompose the original low-speed failure or establish interactions.
Two identical runs demonstrate deterministic repeatability, not success rate.
One staircase direction and forward commands do not cover lateral/yaw tracking,
randomized robustness, all terrain families, hardware, or a capability ceiling.

Completion: source-bound runner, independently verified trace and budget,
repeat/interface conclusions, measured capability/failure map, reusable entry
point and explicit next decision. If reference fails, diagnose source semantics
offline before new experiments; if transfer fails, retain the source plant as
the validated reference and isolate transfer in a new prospective task.

## Execution

Runner: `python -m tools.substrate.baseline prepare|capture|verify` with the
reliable substrate interpreter. Preparation is zero integration. Existing clean
qualification, exact-HEAD independent science/execution review, authorization,
lock and fresh preflight apply. Raw root `_runs/rl_baseline_20260923`.
Permanent single-campaign ledger `_runs/substrate_attempts/rl-source-baseline-v1`.
The sealed `rl-flat-compatibility-v1` campaign is untouched.
