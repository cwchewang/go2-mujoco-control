# Go2 Substrate Gate 0 benchmark v0 design

Status: `OFFLINE_SPECIFICATION_COMPLETE_PENDING_SOL_REVIEW`

Task: `px_1a0c7feca02_97025cbb46`

Exact task commit: `d650147127eda95a6caeb9e4e7c3a457fc091c5c`

Exact protected-main ancestry: `b1cec66f446c34e850c9caeeac82de52805a3889`

Specification: [`docs/validation/substrate_gate_0_benchmark_v0/SPEC.md`](../validation/substrate_gate_0_benchmark_v0/SPEC.md)

This is a design checkpoint. It freezes the comparison protocol shape and the
source-backed asset registry; it does not freeze unsupported geometry,
thresholds, backend implementation details, or a capability result.

## FACTS

### Authority and scope

- `SUBSTRATE_GATE_0` compares a later `MJPC/iLQR whole-body MPC` smoke with a
  later published `Go2 RL checkpoint` smoke under one MuJoCo evidence contract.
- `DIAL/MPPI` is a later diagnostic challenger slot, not a v0 comparison arm.
- The sealed Raibert+SRBD+WBC clean baseline remains regression/reference only.
- The exact parent closeout is
  `docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md`.
  Its `64/64` flat reproduction is retained as historical reference evidence,
  not as a Gate 0 result.
- No live MuJoCo, DDS, controller, or policy execution is authorized by this
  task. No scientific attempt is consumed.

### Shared Go2 model semantics

The common model identity is the repository asset
`unitree_robots/go2/go2.xml`, included unchanged by each scenario XML.
Source facts are:

- one free `base_link` body with the checked-in inertial data;
- four named legs `FR`, `FL`, `RR`, `RL`;
- twelve named joint motors, one abduction, thigh, and calf actuator per leg;
- front and rear thigh joints have distinct model classes/ranges;
- named foot geoms, four foot-contact sites, touch/3-D force sensors, IMU
  sensors, joint position/velocity sensors, and actuator-force sensors;
- the MuJoCo motor `ctrl` interface is the physical boundary. An adapter may
  translate a backend action representation into that boundary, but may not
  alter the model, add a hidden safety controller, or read terrain oracle data.

The model file's source hash at this checkpoint is recorded in
`docs/validation/substrate_gate_0_benchmark_v0/provenance.csv`.

### Source-backed terrain registry

The following are inventory entries, not guessed new fixtures. Dimensions in
this table are descriptions extracted from the checked-in XML (`size` is a
MuJoCo half-extent) and must be revalidated by hash at any later run.

| registry id | source asset | source-backed content | v0 status |
|---|---|---|---|
| `flat` | `unitree_robots/go2/phase2_flat.xml` | named plane `phase2_floor` | required anchor candidate |
| `single_step_5cm` | `unitree_robots/go2/phase2_step_5cm.xml` | box centered at `(0.95, 0, 0.025)` with half-size `(0.25, 0.75, 0.025)`; physical height `0.05 m` | required substrate candidate |
| `single_step_10cm` | `unitree_robots/go2/phase2_step_10cm.xml` | box centered at `(0.95, 0, 0.05)` with half-size `(0.25, 0.75, 0.05)`; physical height `0.10 m` | higher-difficulty candidate |
| `repeated_steps` | `unitree_robots/go2/phase2_repeated_steps.xml` | three source boxes: `0.05 m`, `0.15 m`, `0.05 m` high, each with source dimensions/centres | mixed-rise candidate |
| `holdout_single_step_5cm_{a,b,c}` | `unitree_robots/go2/phase2_step_5cm_holdout_{a,b,c}.xml` plus `PHASE2_HOLDOUT_MANIFEST.json` | source-backed lateral/longitudinal placement and initial-state/seed variations | reserved holdout candidates |
| `composite_stairs` | `unitree_robots/go2/scene.xml` | unnamed boxes forming a legacy obstacle/stair-like course | adapter required; not yet a named v0 case |
| `generated_stairs_rough_hfield` | `terrain_tool/terrain_generator.py`, `unitree_robots/go2/scene_terrain.xml` | box, geometry, stairs, suspended stairs, rough-ground, Perlin and image height-field generation | adapter and generation provenance required |
| `reactive_obstacle` | `unitree_robots/go2/scene_reactive_obstacle.xml` | named collidable obstacle plus non-collidable marker | diagnostic/excluded from substrate v0 |
| `low_friction_patch` | `unitree_robots/go2/scene_low_friction_patch.xml` | flush collidable friction change | diagnostic/excluded from geometry v0 |

The registry deliberately does not turn the legacy composite scene or the
generator defaults into a benchmark case. A case is admitted only when its
scene file, seed/generation recipe, goal plane, and scoring interpretation are
all auditable.

### Existing execution and analysis surfaces

- `simulate/` is the repository MuJoCo/DDS bridge. `simulate/config.yaml`
  points to a generic `scene.xml`; it is not a Gate 0 manifest.
- `example/cpp/scripts/run_trot.sh` is the canonical controller/simulator
  launch plumbing and accepts a scene path, but is a live runner and therefore
  was not invoked here. `run_trot_exact_source.sh` supplies exact-source host
  build plumbing for a later, separately authorized checkpoint.
- `run_phase2_b0_pair.sh`, `run_phase2_b0_fixed_pair.sh`, and
  `run_phase2_b0_lockstep_pair.sh` belong to the existing Phase-2 B0 route.
  Their sensor-only contract and thresholds are not silently inherited by Gate
  0.
- `example/cpp/tools/analyze_phase2_b0.py` and
  `analyze_phase2_terrain.py` are useful precedent for manifest/hash and
  contact/terrain checks, but neither is a backend-neutral Gate 0 analyzer.
- `example/cpp/tools/write_run_manifest.py` is reusable provenance plumbing;
  it is not itself a Gate 0 result schema.
- The repository contains no MJPC/iLQR, DIAL/MPPI, or published Go2 RL
  checkpoint adapter implementation. The RL repository/checkpoint identity and
  observation/action mapping are therefore unresolved external inputs.

## BENCHMARK_V0

The full field-level contract is in `SPEC.md`. Its frozen shape is:

1. Load the same `go2.xml` model and an immutable, hashed scenario asset.
2. Give every backend the same initial-state, goal, observation, action, and
   horizon contract. Backend adapters may translate interfaces but may not
   expose scene XML, geom IDs, future terrain, simulator contact truth, or an
   oracle map to the controller/policy.
3. Score task completion from simulator ground truth in the harness only.
   Record trajectory, contacts, collisions, command tracking, backend timing,
   and provenance in one schema.
4. Produce one deterministic run name from backend, scenario, split, repeat,
   seed, and source revision. Existing raw evidence must never be overwritten.
5. Apply the same terminal taxonomy and precedence to both comparison arms.

### Common goals

- `flat_progress`: forward progress on the flat anchor while preserving the
  declared locomotion task and evidence completeness.
- `substrate_crossing`: traverse the declared fixture from its start side to
  its goal plane, with force-supported touchdown on every surface that the
  scenario declares as crossed and no non-foot collision.
- `post_goal_stability`: retain valid evidence for the declared post-goal
  interval. The interval is a protocol field and remains unresolved until Sol
  reviews the backend-independent timing choice.

The goals are semantic, not numerical guesses. Goal-plane clearance, horizon,
stability window, contact-force definition, and all primary pass thresholds are
explicit `UNRESOLVED_FOR_SOL` fields in v0.

### Terminal taxonomy

Every run emits exactly one terminal code and one boundary:

`PASS`, `TASK_INCOMPLETE`, `LOSS_OF_STABILITY`, `NONFOOT_COLLISION`,
`BACKEND_REJECTION`, `UNSUPPORTED_ADAPTER`, `EVIDENCE_INVALID`, or
`EXECUTION_INVALID`.

The precedence is deterministic: evidence/execution invalidity, unsupported
adapter admission failure, safety/collision failure, task failure, backend
rejection, then pass. A
pre-capture unsupported adapter is not a scientific failure; it is an admission
veto and cannot be compared as capability evidence.

### Backend boundary

The common harness owns model loading, scenario selection, initial state,
ground-truth contact/collision scoring, timekeeping, artifact hashing, and
terminal classification. A backend adapter owns only observation conversion,
backend invocation, action conversion to the 12-motor MuJoCo interface, and
backend-local resource counters. No adapter may change scene geometry,
controller semantics, gait topology, or scientific thresholds.

## ASSET_GAPS

- No Gate 0 manifest loader or backend-neutral analyzer exists.
- No versioned MJPC/iLQR source/build identity or action/observation adapter is
  present in this repository.
- No published RL checkpoint URI, commit, checksum, licensing record, or
  action/observation mapping is present here; the companion RL repository is
  only named by repository governance.
- Existing terrain generator output combines multiple surfaces and does not
  provide a v0 case manifest with seed and generated-scene hash.
- Existing scenes do not uniformly declare semantic start/goal planes or
  surface IDs. The harness needs a non-mutating scene metadata/ground-truth
  adapter.
- Existing analyzers are route-specific and have no common backend/resource
  record or terminal precedence implementation.

## UNRESOLVED_FOR_SOL

Sol review is required before any live or capability claim. The following must
not be filled by an execution worker:

- official v0 case membership and ordering within the asset registry;
- exact start pose, goal-plane clearance, episode horizon, post-goal stability
  interval, and repeat/seed count;
- primary success thresholds for progress, stability, tracking, contacts,
  collision, and resource budgets;
- whether the existing Phase-2 B1/B2/B3 gates are merely diagnostic references
  or are adapted into a new Gate 0 contract;
- MuJoCo timestep/control cadence and the allowed action parameterization,
  including torque scaling/clipping semantics;
- MJPC/iLQR version/build and observation/action adapter;
- published RL checkpoint repository/commit/checksum and observation/action
  adapter;
- exact source of solver/inference timing measurements and hardware-normalized
  comparison policy;
- whether the five named Phase-2 holdout inputs are Gate 0 members or remain a
  later anti-memorization holdout;
- whether any staircase/rough/hfield asset is admitted after a deterministic
  generator manifest is supplied.

## NO_LIVE_VALIDATION

This checkpoint performed source inspection and documentation-only validation.
It did not launch `unitree_mujoco`, `real_trot_go2`, any DDS process, MJPC,
MPPI, or an RL policy; no raw `_runs` evidence was touched. Static validation
and exact changed-path evidence are recorded in the task closeout:
`docs/validation/substrate_gate_0_benchmark_v0/RESULTS.md`.

## NEXT_GATE

Sol first reviews the unresolved list and signs the exact v0 case/threshold/
adapter manifest. Only then may a separate execution task add adapter/runtime
surfaces, run no-live adapter tests, pass the SOP preflight, and request a live
capability checkpoint. That later task must preserve the clean baseline as a
reference route and must not use the Gate 0 design document as permission to
modify controller/planner behavior.
