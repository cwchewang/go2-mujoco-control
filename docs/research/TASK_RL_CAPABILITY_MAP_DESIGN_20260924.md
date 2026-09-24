# RL capability-map design — 2026-09-24

## Objective

Design and freeze the next bounded Go2 RL capability-mapping campaign using the now-verified shared deployment as the reference. This task is **design + implementation + zero-physics/static validation only**. Do not consume a new scientific campaign or run MuJoCo plant integration.

Canonical starting point: main after PR #175.
Verified reference:
- formal campaign #166
- result commit `6f67769851aaffed1c1826d138293e52265dbba7`
- shared deployment condition: model + shared_home + ten-step startup + adapter
- 1.0 m/s flat: two deterministic PASS cases, mean vx 0.8858825097 m/s
- no retry; exact evidence discipline remains required.

Read first:
- `CURRENT.md`
- `docs/PROJECT_RECORD.md`
- `docs/TOPIC_AUDIT.md`
- `docs/research/SOP.md`
- `docs/research/TASK_RL_BASELINE_20260923.md`
- `docs/validation/rl_baseline_20260923/RESULTS.md`
- `docs/validation/shared_transfer_combination_formal_v2_20260923/RESULTS.md`
- `tools/substrate/protocols/rl_source_v1.json`
- `tools/substrate/protocols/rl_shared_transfer_combination_v1.json`
- `tools/substrate/baseline.py`
- `tools/substrate/baseline_episode.py`
- existing Go2 scenes under `unitree_robots/go2/`.

## Research question

Given that the complete shared deployment preserves the pinned public policy's 1 m/s flat capability, what is the **smallest prospective terrain × direction/speed campaign** that can expose a useful capability/failure map without confusing deployment artifacts, unsupported telemetry, or arbitrary historical choices?

This stage should prepare the RL side of Substrate Gate 0. It must not claim a paper gap.

## Required work

1. Audit the currently available scenes and runner semantics.
   - Identify which existing scenes are actually compatible with current Plant/telemetry assumptions.
   - Explicitly examine at least: `phase2_step_5cm.xml`, `phase2_step_10cm.xml`, `phase2_repeated_steps.xml`, `scene_low_friction_patch.xml`, `scene_reactive_obstacle.xml`, and the pinned upstream `cross_stairs.xml`.
   - Do not select a scene merely because it exists.
   - If a scene cannot be interpreted safely by current telemetry, either exclude it with evidence or make the smallest auditable runner extension needed. Do not silently weaken safety checks.

2. Audit command coverage.
   - Current protocol machinery is primarily scalar forward speed although the policy observation contains [vx, vy, yaw-rate] commands.
   - Determine from pinned upstream source/config what lateral and yaw command semantics are actually supported.
   - Decide whether this campaign should include lateral/yaw cases now. If yes, extend protocol/runner minimally and test it. If not, document the evidence-based reason and keep "direction" scoped to what is actually supported.
   - Never invent command ranges from memory; derive them from upstream/source/config or use explicitly labeled bounded engineering probes.

3. Propose the smallest informative matrix.
   - Preserve the verified shared deployment condition unless the variable under test explicitly requires otherwise.
   - Prefer deterministic, interpretable cases over broad randomization.
   - Include a flat reference sentinel so terrain results are not interpreted after deployment/reference regression.
   - Terrain/speed/direction cases should answer distinct questions; avoid redundant cases.
   - Explicitly state why each chosen terrain height/geometry, speed, and direction exists.
   - Historical 5 cm is not privileged merely because it was used before.
   - The old 23 cm source stairs stop is evidence, not a mandatory benchmark.

4. Define prospective metrics and semantics.
   - Separate tracking failure, task/goal failure, safety stop, integrity stop, and unsupported-scene/preflight failure.
   - Define terrain-specific success without post-hoc threshold changes.
   - Preserve raw metrics even when a case fails.
   - Define progression/stop rules and a hard scientific-attempt budget for the future capture.
   - Keep the future campaign small enough that a negative result remains interpretable.

5. Implement the frozen design.
   - Add a new protocol under `tools/substrate/protocols/` and corresponding task config under `tools/substrate/tasks/`.
   - Add/modify only the minimum runner/analyzer code needed.
   - Add tests that cover any new command shape, scene semantics, success logic, progression and zero-step preparation behavior.
   - Write a human-readable design document under `docs/research/`.
   - Write a design closeout under `docs/validation/rl_capability_map_design_20260924/RESULTS.md`.

6. Self-review and repair autonomously.
   - Before closeout, perform your own science and execution review of the candidate design.
   - Minor problems (paths, task metadata, tests, unsupported scene handling, stale references, evidence formatting, local implementation bugs) should be repaired directly, then re-reviewed.
   - Escalate only if fixing the issue would change the scientific question, materially change the attempt budget/threshold meaning after seeing data, require a large new training effort, or invalidate sealed evidence.
   - Do not stop for ordinary implementation friction.

## Zero-physics boundary

This task may inspect XML/config/source, build, run unit/static tests, parse models if that does not integrate the external plant, and run zero-step preparation/qualification-style checks. It must not execute a capability episode or call the scientific capture path. Record `scientific_attempts=0`.

## Deliverables

A single final commit containing:
- frozen prospective protocol/task config;
- minimal runner/test changes if needed;
- design rationale;
- explicit case table with variables, metrics, gates, progression and attempt budget;
- self-review findings and repairs;
- `docs/validation/rl_capability_map_design_20260924/RESULTS.md`.

Closeout must clearly state:
- what the future campaign will test;
- what it will **not** test;
- why the selected matrix is minimal/informative;
- which existing scenes were rejected and why;
- whether lateral/yaw commands are admitted;
- exact future execution entrypoint;
- exact remaining blockers, if any;
- `physics_steps=0`, `scientific_attempts=0`.

Do not modify historical sealed results or rerun #166.
