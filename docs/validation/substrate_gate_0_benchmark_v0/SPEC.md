# SUBSTRATE_GATE_0 benchmark v0 specification

Specification status: `protocol_shape_frozen`

Scientific status: `no_live_runs_authorized`

Design authority: `docs/research/TASK_SUBSTRATE_GATE_0_BENCHMARK_V0_20260922.md`

Task: `px_1a0c7feca02_97025cbb46`

## 1. Scope and frozen roles

This specification defines one auditable MuJoCo comparison protocol for a
future `MJPC/iLQR whole-body MPC` arm and a future published `Go2 RL
checkpoint` arm. `DIAL/MPPI` is a later diagnostic challenger only. The
repository's sealed Raibert+SRBD+WBC clean baseline is a legacy
regression/reference and is not a third Gate 0 arm.

The protocol shape, field names, terminal taxonomy, provenance requirements,
and deterministic naming rule are frozen here. Any numerical threshold,
unresolved adapter semantics, or new scene member requires Sol review before
capture.

## 2. Immutable shared contract

### 2.1 Model and scenario identity

Each case must record:

| field | rule |
|---|---|
| `robot_id` | `go2` |
| `model_path` | `unitree_robots/go2/go2.xml` |
| `model_sha256` | SHA-256 of the exact bytes loaded by the harness |
| `scenario_id` | registry ID below; no free-text substitute |
| `scenario_path` | immutable XML or generated XML path |
| `scenario_sha256` | SHA-256 of exact scenario bytes |
| `scenario_generation` | `checked_in_xml` or a deterministic recipe plus seed and output hash |
| `initial_state_id` | canonical serialized initial state and SHA-256 |
| `goal_id` | named goal plus all resolved goal fields |

The model is loaded unchanged from `go2.xml`. The common physical boundary is
the twelve named MuJoCo motor controls. The four legs, contact sites, force
sensors, IMU, and joint sensors are the shared semantic labels from that model.

### 2.2 Source-backed scenario registry

The registry is frozen as an inventory. `required` means the case is a
candidate anchor for Sol's final member list; it does not authorize execution.

| `scenario_id` | family | source | registry state |
|---|---|---|---|
| `flat` | flat | `unitree_robots/go2/phase2_flat.xml` | required anchor candidate |
| `single_step_5cm` | single rise | `unitree_robots/go2/phase2_step_5cm.xml` | required substrate candidate |
| `single_step_10cm` | single rise | `unitree_robots/go2/phase2_step_10cm.xml` | higher-difficulty candidate |
| `repeated_steps` | repeated rise/descent | `unitree_robots/go2/phase2_repeated_steps.xml` | mixed-rise candidate |
| `single_step_5cm_holdout_a` | holdout single rise | `unitree_robots/go2/phase2_step_5cm_holdout_a.xml` | reserved holdout candidate |
| `single_step_5cm_holdout_b` | holdout single rise | `unitree_robots/go2/phase2_step_5cm_holdout_b.xml` | reserved holdout candidate |
| `single_step_5cm_holdout_c` | holdout single rise | `unitree_robots/go2/phase2_step_5cm_holdout_c.xml` | reserved holdout candidate |
| `composite_stairs` | staircase/legacy composite | `unitree_robots/go2/scene.xml` | adapter required |
| `generated_stairs_rough_hfield` | generated mixed terrain | `terrain_tool/terrain_generator.py` and `scene_terrain.xml` | generation manifest required |

`scene_reactive_obstacle.xml` and `scene_low_friction_patch.xml` remain
diagnostic assets outside the geometry-focused v0 registry. Their presence
does not define a Gate 0 obstacle or friction task.

The XML geometry is source-derived only. For example, the checked-in 5 cm and
10 cm step files provide their own box centres and half-extents, and the
repeated-step file provides its three box definitions. No replacement size,
clearance, goal plane, or terrain threshold is inferred here.

### 2.3 Common goals

Each admitted case declares one or more of these goals before capture:

1. `flat_progress`: make forward progress on the flat anchor while satisfying
   the evidence-completeness contract.
2. `substrate_crossing`: cross the declared terrain fixture from its start side
   to its goal plane; every declared crossed surface receives a
   force-supported touchdown; no non-foot collision occurs.
3. `post_goal_stability`: remain in the declared valid state for the declared
   post-goal interval.

The goal is common across backends. Ground-truth surface identity, contact,
collision, and final position are harness-only signals. The controller/policy
may use only the observation stream declared by its adapter.

`goal_plane_clearance_m`, `episode_horizon_s`, `post_goal_stability_s`, the
contact-force rule, and all pass thresholds are `UNRESOLVED_FOR_SOL`.

## 3. Backend adapter boundary

The harness owns:

- exact model/scene loading and hashing;
- initial state, scenario, goal, seed, and timebase;
- simulator ground-truth contact/collision and surface labels;
- common trajectory sampling and artifact writing;
- resource counter collection that is available outside a backend;
- terminal classification and precedence.

An adapter owns only:

- observation conversion from the declared common observation stream;
- one backend invocation;
- conversion of the backend output to the twelve-motor MuJoCo action;
- backend-local inference/solver counters and adapter provenance.

An adapter must not read scene XML, geom identity, obstacle coordinates, step
index, future terrain, simulator contact/collision, or an oracle map. It must
not add a second velocity authority, terrain-specific controller, hidden
recovery policy, controller/planner mutation, or threshold override.

The exact control cadence, action scaling/clipping, observation subset, and
MJPC/RL versions are unresolved. They must be identical in physical meaning
across the two admitted arms once Sol resolves them.

## 4. Evidence and metrics

### 4.1 Required trajectory evidence

At each declared sample, the common record contains:

`sim_time_s`, `wall_time_s`, base pose/twist, all joint position/velocity
values, commanded/reference values, twelve applied motor controls, four foot
poses, per-foot measured contact/normal force, simulator ground-truth contact
and collision labels, and backend status.

Terrain/scenario ground truth is harness-only and is marked as such in the
schema. The adapter's observation stream is recorded separately so privileged
data cannot be mistaken for policy input.

### 4.2 Required primary and resource metrics

The analyzer computes, without backend-specific substitutions:

- progress and goal-plane completion;
- per-surface touchdown coverage;
- non-foot collision and loss-of-stability events;
- command/reference versus realized motion;
- base orientation/height and contact continuity;
- action/control latency and deadline misses;
- backend solver/inference time, iterations/status where available;
- wall time, CPU time, peak resident memory, and real-time factor;
- artifact completeness and hash/provenance validity.

Metric definitions are frozen; acceptance thresholds are not. Resource metrics
are reported per run and cannot be converted into a capability ranking until
Sol approves the hardware-normalization and missing-counter policy.

### 4.3 Terminal taxonomy and precedence

Exactly one terminal code and one SOP boundary are required:

| terminal code | meaning |
|---|---|
| `PASS` | all resolved task and evidence gates pass |
| `TASK_INCOMPLETE` | episode ends without the declared goal |
| `LOSS_OF_STABILITY` | resolved stability/safety rule fails |
| `NONFOOT_COLLISION` | resolved non-foot collision rule fails |
| `BACKEND_REJECTION` | backend/adapter cannot produce a valid action during capture |
| `UNSUPPORTED_ADAPTER` | adapter fails admission before scientific capture |
| `EVIDENCE_INVALID` | bytes, schema, or provenance cannot support a verdict |
| `EXECUTION_INVALID` | wrong source/model/config/process or other execution boundary fails |

Precedence is: `EVIDENCE_INVALID` or `EXECUTION_INVALID`, then
`UNSUPPORTED_ADAPTER`, then safety/collision failure, then task incompletion,
then backend rejection, then `PASS` only when all gates pass. The exact
boundary/reason code is always retained; a missing artifact is not silently
reclassified as a scientific failure.

## 5. Provenance and deterministic naming

### 5.1 Required provenance fields

Every run manifest records:

| group | required fields |
|---|---|
| task | gate ID, spec version, task ID, exact task commit, exact protected-main ancestry |
| source | Git branch/ref, HEAD, dirty state, source tree/diff identity, adapter commit |
| model | robot ID, model path/hash, MuJoCo version, compiler/build flags |
| scenario | scenario ID/path/hash, generation recipe/hash, split, repeat, seed |
| goal | goal ID and every resolved goal/threshold field |
| backend | backend ID/version, model/checkpoint ID and checksum, adapter version, observation/action schema |
| runtime | OS/kernel, CPU/GPU, CPU slots, memory, timebase/cadence, environment snapshot |
| execution | exact argv, start/end time, exit status, process/resource counters |
| evidence | raw artifact paths and SHA-256, schema/analyzer version and hash, terminal code/boundary/reason |

External checkpoint provenance must include a retrievable repository/URI,
commit or release identifier, checksum, and license record. A bare model name
is insufficient.

### 5.2 Run naming

The deterministic run ID is:

`sg0-{backend}-{scenario}-{split}-r{repeat:02d}-s{seed}-{head8}`

where `backend`, `scenario`, and `split` are lowercase registry tokens,
`repeat` and `seed` are fixed manifest values, and `head8` is the first eight
hex characters of the exact source HEAD. A pre-existing directory with the
same ID is a preflight failure; no raw run is overwritten or renamed.

## 6. Unresolved fields blocking the next gate

Sol must resolve the following before any scientific capture:

- final case membership/order and whether the three holdouts are v0 or later;
- start states, goal planes, horizon, stability interval, repeats, and seeds;
- all numerical success, safety, contact, tracking, and resource thresholds;
- control timestep/cadence, observation subset, action scaling, and clipping;
- MJPC/iLQR implementation/version/build and adapter;
- RL checkpoint identity and adapter;
- analyzer implementation/version and hardware-normalized resource policy;
- deterministic manifests for generated stairs/rough/hfield cases.

Existing values in `PHASE2_ACCEPTANCE.md` and
`PHASE2_HOLDOUT_MANIFEST.json` remain source/diagnostic references until this
review; they are not imported as Gate 0 thresholds by implication.

## 7. Admission checklist for a future task

Before a separate live task is even eligible:

1. Sol signs the unresolved fields and exact member manifest.
2. The adapter and analyzer are added under a new scoped task; runtime-semantic
   changes receive the required review under the SOP.
3. No-live tests prove model/action/observation/ground-truth separation and
   manifest/hash determinism.
4. The exact candidate HEAD is clean and passes the SOP preflight immediately
   before launch.
5. The later task explicitly authorizes a run budget. This design task's budget
   is zero and cannot be reused.
