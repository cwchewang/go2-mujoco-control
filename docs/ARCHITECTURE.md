# Architecture

This document maps the code; it does not define research status or the next
task. For Phase 2, read [`CURRENT.md`](../CURRENT.md) first.

## Runtime data flow

The MuJoCo process and 500 Hz C++ controller communicate through the Unitree
SDK2 DDS interface.

```text
MuJoCo -> LowState / lidar -> state snapshot and filtering
                                  |
requested velocity -> Phase 1 shaper -> gait/foothold targets
                                           |
                         clean target contract + direct IK feasibility
                                           |
                                        SRBD MPC
                                           |
                              strict 18-DoF ID-WBC acceptance
                                           |
                              final finite/ramp/torque envelope
                                           |
                                      LowCmd -> MuJoCo
```

The sensor-only terrain path derives a terrain model, feasibility results, and
a plan from lidar. On the current line it may be logged and analyzed, but it
does not alter gait, MPC, WBC, contact policy, or velocity. There is no
production terrain-actuation path.

## Active modules

| Area | Primary files | Responsibility |
|---|---|---|
| CLI and lifecycle | `example/cpp/trot/trot_cli.*`, `trot_experiment_lifecycle.cpp` | configuration, DDS, startup, shutdown |
| Control loop | `example/cpp/trot/trot_experiment_control.cpp` | state snapshot, phase execution, command publication |
| Gait | `example/cpp/trot/trot_experiment_gait.cpp`, `example/cpp/gait/*` | running-trot phase, footholds, velocity targets |
| Terrain interfaces | `example/cpp/terrain/*` | sensor-derived model, feasibility, immutable plan interface |
| MPC and WBC | `example/cpp/trot/trot_experiment_wbc.cpp`, `example/cpp/wbc/*` | SRBD preview and inverse-dynamics control |
| Kinematics | `example/cpp/kinematics/*` | FK, IK, Jacobians, rigid-body model |
| Contact | `example/cpp/contact/*` | measured-contact filtering, wrench allocation, torque mapping |
| Timing | `example/cpp/trot/lockstep_*` | lockstep clock/writer diagnostics; not a realtime acceptance claim |
| Diagnostics | `example/cpp/trot/trot_experiment_diagnostics.cpp`, `trot_types.h` | limits, status, structured logs |
| Clean baseline contract | `example/cpp/wbc/clean_baseline.h`, `go2_inverse_kinematics.h`, `inverse_dynamics_wbc.h` | exact targets, authoritative limits, strict solver result, final command envelope |
| Canonical DDS runtime | `example/cpp/scripts/dds_runtime.sh`, `run_trot.sh`, `run_trot_exact_source.sh` | tracked support artifact, fail-closed cleanup, exact-source launch plumbing |
| Tests and analysis | `example/cpp/tests/`, `example/cpp/tools/` | unit/integration checks and protocol analyzers |

## Target Phase 2 planner

The active Stage C target adds `TerrainBelief` for estimated state, measured
contact, terrain freshness, and uncertainty. `TerrainFeasibility` remains the
hard-filter/candidate layer. A receding-horizon `TerrainPlanner` then jointly
optimizes future footholds, body/CoM references, touchdown/contact timing, and
swing duration. Its complete output is one atomic `TerrainExecutionState`
consumed by gait, SRBD-MPC, and ID-WBC.

The first implementation stays in running-trot topology and runs in
shadow/replay before actuation. The existing per-leg scorer is not the target
planner, and archived Stage-C code is not a design source. `CURRENT.md` owns
the ordered implementation and acceptance sequence.

## Phase 2 invariants

The Phase 1 shaper remains the only velocity authority. Planned contact and
force-supported measured contact remain separate. A future terrain execution
path must publish one immutable, time-indexed snapshot shared by gait, SRBD-MPC,
and ID-WBC; no consumer may invent its own timing, contact, or recovery state.
Any actuation-capable terrain planner must explicitly enable the clean baseline
contract and enter through `exact foot targets -> direct IK feasibility ->
strict WBC -> final safety envelope`. Sensor-only terrain remains observer-only.
The Cartesian-world and legacy clamp/overlay path is incompatible with
`--clean-baseline`.

The retained `example/cpp/leg_lift/` executable and multi-step configurations
are historical experiments. They are not a Phase 2 route or design source.
Removed crawl/three-contact code and Git history are not fallback
implementations.

## Repository boundaries

`simulate/` and `unitree_robots/go2/` remain close to the upstream Unitree
simulator. Research-specific model control lives in `example/cpp/`. Isaac Lab
RL and Kine2Go imitation live only in their companion repositories and are not
runtime dependencies here.

See [`CODE_GUIDE.md`](CODE_GUIDE.md) for source navigation,
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) for execution rules, and
[`../UPSTREAM_AND_CONTRIBUTIONS.md`](../UPSTREAM_AND_CONTRIBUTIONS.md) for
provenance.
