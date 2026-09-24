# RL capability map design — 2026-09-24

## Decision served

After the shared-model, shared-home, ten-step-start, adapter deployment passed
the frozen 1 m/s flat reference twice, determine which command axes and small,
interpretable terrain profiles deserve a bounded next capability screen. This
design prepares the RL side of Substrate Gate 0. It does not identify or claim a
paper gap.

The reference condition stays fixed in every case: the pinned checkpoint, the
shared Go2 model, shared home pose, first policy inference after ten plant
steps, the `FrozenPolicy` adapter, deterministic seed 0, 2 ms plant period and
50 Hz policy period. Only scene, command, or the duration needed for a bounded
flat probe varies.

## Source and command coverage

The pinned deployment exposes a three-value command `[vx, vy, yaw_rate]` in the
policy observation and scales it by `[2.0, 2.0, 0.25]`. Its deployment YAML sets
`cmd_init` to `[1.0, 0.0, 0.0]` and joystick maxima to `[2.0, 1.0, 2.5]`. The
pinned `GO2Cfg` sets `heading_command=False`, initial class ranges of `vx` and
`vy` in `[-0.5, 0.5]` m/s and yaw rate in `[-1.0, 1.0]` rad/s; its curriculum
later expands the ranges. These values come from the [pinned deployment
config](https://github.com/wty-yy/go2_rl_gym/blob/30e74dc507bec7a642a8c98be26081f2c6f0822d/deploy/deploy_mujoco/configs/go2.yaml),
[pinned deployment loop](https://github.com/wty-yy/go2_rl_gym/blob/30e74dc507bec7a642a8c98be26081f2c6f0822d/deploy/deploy_mujoco/deploy_go2.py)
and [pinned Go2 training config](https://github.com/wty-yy/go2_rl_gym/blob/30e74dc507bec7a642a8c98be26081f2c6f0822d/legged_gym/envs/go2/go2_config.py).
The repository source lock records these files at commit
`30e74dc507bec7a642a8c98be26081f2c6f0822d`.

The campaign admits lateral and yaw commands through the same adapter. The
negative-forward probe tests a reverse command; the positive lateral and yaw
probes test the other exposed dimensions. Probe magnitudes stay within the
pinned config's initial class ranges. They are bounded engineering probes, not
a claim that the exact checkpoint training history sampled every value. The
flat 1 m/s case is the already verified deployment reference, not an inferred
training-range claim.

Terrain cases use only `+X` at 1 m/s. This keeps terrain comparisons on the
verified command condition and avoids a full terrain-by-command Cartesian
product. Flat probes separately screen speed and command-axis behavior. No
lateral, reverse, or turning terrain crossing is claimed by this map.

## Scene audit and selection

The current `Plant` checks the 12-joint/12-actuator Go2 embodiment and derives
clearance from horizontal world-body planes and boxes under the base origin. It
records foot centers and terrain contact geom pairs. It does not record contact
forces or identify foothold support per foot. Every selected scene compiled
with the existing telemetry geometry assumptions in a zero-step check. The
protocol now lists the exact colliding world-geometry names per scene; an
unexpected name, non-plane/non-box, or tilted world terrain fails preparation
as `UNSUPPORTED_SCENE_PREFLIGHT_FAILURE` before any scientific attempt.

| Scene | Static geometry and telemetry fit | Decision |
|---|---|---|
| `phase2_flat.xml` | One horizontal plane; the already verified shared-model reference scene. | Select as the first sentinel and for command probes. |
| `phase2_step_5cm.xml` | A 0.5 m long by 1.5 m wide box from x=0.70 to 1.20 m, 0.05 m high, over the plane. | Select with the matched 10 cm case as the lower point of a two-height engineering screen. It is not privileged by its historical name. |
| `phase2_step_10cm.xml` | Same plan dimensions and x interval as the 5 cm box; height is 0.10 m. | Select to double the isolated-step height while holding its footprint fixed. The pair screens a coarse height contrast; it is not a universal threshold. |
| `phase2_repeated_steps.xml` | Three 0.40 m long boxes, each 1.5 m wide, spanning x=[0.70,1.10], [1.25,1.65], and [1.80,2.20] m, with heights 0.05, 0.15, and 0.05 m. Gaps are 0.15 m. | Select as one compound multi-transition profile. Its 15 cm peak and repetition are confounded, so a failure will be attributed to this profile, not to repetition alone. |
| `scene_low_friction_patch.xml` | A 1.6 m long by 1.2 m wide, 1 mm thick box from x=0 to 1.6 m with explicit friction `[0.0001, 0.0001, 0.0005]`, over the plane. | Select as the non-height terrain case. Progress and tracking answer whether the policy crosses this declared condition; telemetry cannot explain friction forces or slip mechanics. |
| `scene_reactive_obstacle.xml` | Static 0.20 m by 0.20 m by 0.32 m colliding box; its top marker is non-colliding. It contains no moving or reactive obstacle. | Exclude. The name overstates its behavior, and this fixed block would add a high obstacle case without testing reactivity. |
| pinned `cross_stairs.xml` | The source scene contains 65 colliding world geoms represented as horizontal boxes plus a plane and compiles with `Plant`. The +X stair rises in 0.23 m increments to 1.84 m. | Audit, but exclude from this matrix. It includes the pinned source robot model; using it directly would replace the verified shared model. A derived shared-model stair scene would be an additional terrain asset. The old source-condition base-contact stop remains evidence, not a required rerun. |

The two single-step scenes share footprint and differ only in height. The
repeated profile adds a sequence with gaps; the low-friction patch changes
traction without a meaningful step. These terrain cases answer distinct
screening questions. The matrix intentionally does not add the static obstacle
or duplicate the old 23 cm source stairs result.

## Frozen prospective matrix

All nine cases are deterministic, use one fresh `MjData` and one case-local
policy state, and allow no retry. Each case has a maximum of one scientific
attempt. The campaign-wide hard budget is **9 attempts**. A case consumes an
attempt at the first valid post-handoff state/control sample; preparation and
static parsing consume none.

Tracking MAE uses the body-frame commanded axis and the half-open measurement
window after its stated startup delay. The prospective engineering tolerance
is `max(0.05, 0.20 * abs(command))` in that axis's units. Flat command probes
also bound uncommanded translation and yaw as listed below. The reference
sentinel retains its existing gates: mean forward speed at least 0.8 m/s,
lateral displacement at most 0.30 m, and yaw excursion at most 0.30 rad.

For a terrain case, success requires a complete horizon, passing forward-speed
tracking, all four foot centers beyond the terrain's far x edge plus their
0.022 m radius, the base center beyond that edge plus the 0.1881 m rearward
extent of the base collision box, and those conditions held for 250 consecutive
ticks (0.5 s). While the base traverses the profile's x interval, its lateral
offset must remain within the declared route band. The bands (0.55 m for the
1.5 m wide steps and 0.40 m for the 1.2 m patch) reserve the measured 0.142 m
foot-center lateral offset and 0.022 m foot radius from the scene edge.

| Order / case | Changed variable and command `[vx,vy,wz]` | Horizon / metric window | Success gate and question | Attempt / progression |
|---|---|---|---|---|
| 1 `flat_reference` | Flat scene; `[1.0,0,0]` m/s. | 6,000 ticks / ticks [1,000,6,000). | Existing flat reference gates above. If it does not pass, all later cases remain `NOT_RUN`; no terrain interpretation is valid. | 1; sentinel. |
| 2 `flat_half_speed` | Flat; `[0.5,0,0]` m/s, the pinned class-range endpoint and half the verified reference speed. | 6,000 / [1,000,6,000). | Forward MAE gate; lateral displacement and yaw excursion each <=0.30. Screens the intermediate speed condition. | 1; continue after performance failure. |
| 3 `flat_reverse_probe` | Flat; `[-0.5,0,0]` m/s. | 6,000 / [1,000,6,000). | Reverse-axis MAE gate; uncommanded lateral displacement and yaw excursion each <=0.30. Screens reverse command semantics. | 1; continue after performance failure. |
| 4 `flat_lateral_probe` | Flat; `[0,0.25,0]` m/s, half the pinned initial positive lateral range. | 2,500 / [100,2,500). | Lateral-axis MAE gate; forward displacement and yaw excursion each <=0.30; absolute lateral safety limit remains 1.50 m. Screens the lateral input channel with margin to its configured range. | 1; continue after performance failure. |
| 5 `flat_yaw_probe` | Flat; `[0,0,0.5]` rad/s, half the pinned initial positive yaw-rate range. | 2,500 / [100,2,500). | Yaw-rate MAE gate; x and y displacement each <=0.30 m. The commanded yaw excursion is reported and is not capped by the flat zero-yaw gate. | 1; continue after performance failure. |
| 6 `step_5cm_cross` | 5 cm isolated step; `[1,0,0]` m/s. | 6,000 / [1,000,6,000). | Forward MAE plus crossing gate; terrain x=[0.70,1.20], route band +/-0.55 m. Screens the lower single-step height. | 1; continue after performance failure. |
| 7 `step_10cm_cross` | Matched 10 cm isolated step; `[1,0,0]` m/s. | 6,000 / [1,000,6,000). | Same footprint, route, clearance, and hold gates as the 5 cm case. Screens a doubled isolated-step height. | 1; continue after performance failure. |
| 8 `repeated_steps_cross` | 5/15/5 cm three-box profile; `[1,0,0]` m/s. | 6,000 / [1,000,6,000). | Forward MAE plus crossing the x=2.20 m far edge, route band +/-0.55 m, and 0.5 s hold. Screens the compound sequence. | 1; continue after performance failure. |
| 9 `low_friction_cross` | 1 mm patch with the XML friction values; `[1,0,0]` m/s. | 6,000 / [1,000,6,000). | Forward MAE plus crossing the x=1.60 m far edge, route band +/-0.40 m, and 0.5 s hold. Screens gross traversal under the specified patch condition. | 1; continue after performance failure. |

## Outcome, stop, and evidence semantics

The analyzer preserves each raw row and reports all command-axis means, MAE and
RMSE, progress, lateral excursion, yaw excursion, clearance, policy timing,
route compliance, and maximum goal-hold ticks, including failed cases.

- `TRACKING_FAILURE`: a complete case misses the commanded-axis or applicable
  flat cross-axis/reference gate.
- `TASK_GOAL_FAILURE`: a terrain case completes without the declared crossing,
  route, or hold condition. It may coexist with `TRACKING_FAILURE`.
- `SAFETY_STOP`: non-finite state/control, quaternion error, MuJoCo warning,
  base-terrain contact, tilt above 1.2 rad, clearance below 0.06 m, or absolute
  lateral displacement above 1.5 m. No later case runs.
- `INTEGRITY_STOP`: a prepared bundle, source identity, scene fingerprint, or
  campaign claim changes after readiness, or a declared deterministic trace
  comparison disagrees. No retry or continuation.
- `UNSUPPORTED_SCENE_PREFLIGHT_FAILURE` / `PREFLIGHT_FAILURE`: a scene does not
  match its declared world-geometry contract or another required qualification,
  review, identity, environment, or fresh-preflight gate fails. No scientific
  attempt is consumed.
- A complete expected tracking/goal failure does not stop later independent
  cases. If the reference sentinel fails, its dependents are skipped and the
  capability map is partial. No terrain claim follows from that capture.

Every case requires `flat_reference`. The campaign uses the existing
`performance_continue_safety_integrity_stop` progression, no retry, and the
nine-attempt hard cap. Deterministic single cases describe these fixed
conditions; they are not success-rate estimates. Foot contact pairs are raw
telemetry, not proof of stance support or a force-level friction mechanism.

## Exact future execution entrypoint

On a clean, qualified, reviewed task HEAD with the reliable Substrate Python,
the zero-step preparation command is:

```bash
python -m tools.substrate.baseline prepare \
  --task tools/substrate/tasks/rl_capability_map_v1.json \
  --output <prepared-bundle> \
  --review <approved-review.json> \
  --qualification <qualification-receipt.json>
```

Only after the normal fresh preflight and a separate start authorization, the
capture command is:

```bash
python -m tools.substrate.baseline capture \
  --task tools/substrate/tasks/rl_capability_map_v1.json \
  --prepared <prepared-bundle> \
  --authorization <start-record.json> \
  --output <capture-bundle>
```

Offline verification is:

```bash
python -m tools.substrate.baseline verify \
  --capture <capture-bundle> \
  --prepared <prepared-bundle> \
  --output <verification-bundle>
```

The task file pins the current logical task branch, protocol hash, and parent
commit. A later Praxis task must bind the final design commit and its own logical
identity before capture. This design task authorizes no capture.

## Self-review

The review identified three issues and repaired them before this freeze:

1. Reusing the scalar analyzer would have treated intended lateral motion as
   cross-axis drift and intended turning as a yaw-limit failure. The v2 analyzer
   now reports body-frame `vx`, `vy`, and `wz`, gates only the commanded axis,
   and applies cross-axis limits to the other motions. The offline verifier now
   replays `FrozenPolicy` for adapter cases and independently checks all three
   command-axis metrics and terrain goals. Synthetic tests exercise a yaw probe
   whose requested excursion exceeds 0.30 rad and the three-axis replay path.
2. The old scene reader could omit world-body terrain geometry not named in the
   protocol or miss terrain attached to an unrelated body. Case geometry
   contracts now compare the exact colliding world-geom name set, reject
   collision geoms outside the Go2 body tree, restrict measured terrain to
   planes/boxes, and return an explicit unsupported-scene preparation result.
   World and nested-body mismatch tests verify rejection before an attempt.
3. Preparation formerly used `[1,0,0]` for every shape probe. The new schema
   sends each case's declared three-axis command through the shape check and
   verifies the live `MjData` and time remain unchanged. The preparation test
   runs under the zero-step guard.

Historical schema-1 analysis remains on its original code path. The sealed
baseline and shared-transfer results are not rewritten or rerun.

## Scope and blockers

This design will test one verified flat sentinel, bounded flat speed/reverse/
lateral/yaw probes, and four +X terrain profiles under the shared deployment.
It will not test lateral or turning terrain traversal, randomized robustness,
hardware, retries, statistical success rates, all obstacle semantics, the
23 cm source stairs, another checkpoint, or a paper gap. The design is frozen
for a future prospectively authorized campaign. There is no scientific result
or live-capture authorization in this task. Future execution still needs the
locked host assets/runtime, applicable clean qualification, exact-HEAD reviews,
fresh preflight, and separate start authorization.
