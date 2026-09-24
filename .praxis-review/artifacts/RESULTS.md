# RL capability-map design closeout — 2026-09-24

## Result

**Design and zero-physics implementation complete. No capability case was
captured.** The design prepares a nine-case screen for the pinned shared Go2
deployment: one flat 1 m/s reference sentinel, four bounded flat command probes
(0.5 m/s forward, 0.5 m/s reverse, 0.25 m/s lateral, and 0.5 rad/s yaw), and
four +X terrain probes (matched 5/10 cm steps, one 5/15/5 cm three-box profile,
and the declared low-friction patch). The full protocol is
[`rl_capability_map_v1.json`](../../../tools/substrate/protocols/rl_capability_map_v1.json);
the rationale, thresholds, case table, progression and exact runner commands
are in [`RL_CAPABILITY_MAP_20260924.md`](../../research/RL_CAPABILITY_MAP_20260924.md).

The task identity is Praxis issue **#176**, logical branch
`research/rl-capability-map-design-20260924`, starting commit
`1139827bd7faf9efd05a25c2ee0ce46dd78c833e`. The final design implementation is
committed in the task worktree; the final commit identifier is recorded in the
Praxis evidence package. [E5, E8]

## What the future screen will decide

The flat sentinel checks that the exact shared deployment still meets its
existing 1 m/s reference gate before any dependent result is interpreted. Flat
probes separately screen an intermediate speed, reverse motion, body-lateral
velocity, and commanded yaw rate. The terrain cases hold the command at the
verified 1 m/s +X condition so the selected scene profile is the changed factor.
This is an intentionally sparse screen, not a terrain-by-direction Cartesian
grid or a statistical success-rate study. [E1, E2]

Lateral and yaw commands are admitted. The pinned deployment has a three-value
`[vx, vy, yaw_rate]` observation command, and the pinned config disables heading
mode and supplies explicit training and deployment ranges. The chosen probes
are bounded engineering values within the pinned config's initial command
ranges; exact training history for this checkpoint is not claimed. [E1]

The map excludes the `scene_reactive_obstacle.xml` static box because it has no
reactive behavior, and excludes direct use of pinned `cross_stairs.xml` because
that scene includes the source robot model rather than the shared model. The
pinned stairs geometry does fit the current plane/box telemetry and was
compiled in a zero-step audit. The historic 23 cm source stair base-contact
stop remains evidence and is not a required benchmark. The low-friction case
reports tracking and crossing under the locked surface condition; it will not
claim force-level slip attribution. [E2]

## Metrics, progression, and budget

The future analyzer will report body-frame axis means, MAE/RMSE, path progress,
lateral and yaw excursion, clearance, route compliance, hold duration, and
policy timing for every completed case. A terrain pass requires full-horizon
safety, forward tracking, the declared route band, all four foot centers and
the base footprint clear of the far edge, held for 250 ticks (0.5 s). Tracking
and task/goal failure remain separate classes. Safety and integrity stops end
the matrix. Unsupported-scene or other preflight failures consume no scientific
attempt. Performance failures continue through independent cases; if the flat
sentinel fails, its dependent cases are skipped and the map remains partial.

The frozen budget is **9 attempts total, one per case, no retries**. Preparation
is guarded against `mj_step`, records `physics_steps=0`, and creates no campaign
claim or attempt ledger. [E3, E4, E7]

## Implementation and validation

The runner now accepts three-axis command rows for schema 2 while retaining the
schema-1 analyzer path for historical protocols. It measures body-frame `vx`,
`vy`, and `wz`, applies command-aware cross-axis gates, validates exact
world-collision geom names and rejects terrain attached outside the Go2 body
tree before preparation. The offline verifier replays the shared adapter and
independently checks three-axis metrics, terrain goals and failure classes. The
runner distinguishes tracking, goal, safety, integrity, unsupported-scene and
preflight outcomes. Tests cover command shape/bounds, scene geometry contracts,
tracking versus goal failures, yaw semantics, progression, verifier replay,
error classification, and a zero-step preparation probe. [E4, E7]

The first static compile of pinned `cross_stairs.xml` failed because the local
evidence snapshot lacked referenced image assets. That read-only failure was
preserved. Missing assets were then fetched from the same source-locked commit,
each hash-checked against `rl_reference.lock.json`, and the complete scene audit
passed under the zero-step guard. [E1, E2, E3]

The final targeted test run passed all capability and baseline unit tests. Three
pre-existing source-policy tests were skipped because this worktree has no
`.substrate` checkpoint/runtime assets. The new selected-scene tests did run
against MuJoCo 3.3.6 and compiled the shared local models without advancing
time. No qualification, capture, or scientific episode was launched. [E7]

## Self-review and repairs

Self-review corrected the scalar-only analyzer's treatment of commanded lateral
and turning motion, added exact scene-geometry contracts to prevent silent
terrain omission, and changed zero-step preparation to probe each declared
three-axis command. The associated tests pass. The source snapshot omission
described above was also repaired and rechecked. Historical sealed results and
the #166 campaign were not modified or rerun. [E1, E2, E3, E7]

## Scope and remaining gates

This task freezes the shared-deployment flat/command/terrain screen and its
execution path. It does not test terrain under lateral or turning commands,
randomized robustness, hardware behavior, another checkpoint, or a paper gap.
No design blocker remains. A future capture still requires the normal exact
task HEAD, locked host policy/runtime assets, applicable clean qualification,
independent science and execution reviews, fresh preflight, and a separate
start authorization. The exact `prepare`, `capture`, and `verify` commands use
`tools/substrate/tasks/rl_capability_map_v1.json` and are frozen in the design
document. [E4, E8]

**Closeout counts:** `physics_steps=0`; `scientific_attempts=0`.
