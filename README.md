# Go2 model-based locomotion in MuJoCo

A 500 Hz Unitree Go2 `LowCmd` controller with online velocity shaping,
running-trot scheduling, SRBD MPC, and 18-DoF inverse-dynamics WBC. This is a
research fork of
[`unitreerobotics/unitree_mujoco`](https://github.com/unitreerobotics/unitree_mujoco).

**Bootstrap:** `main` is the stable code line and long-term route. The active
research frontier may live on a separate `research/*` branch. Read
[`CURRENT.md`](CURRENT.md) for the single maintained pointer to that branch,
its task, the canonical execution [SOP](docs/research/SOP.md), and the exact
`RESULTS.md`. Do not use Atlas directories, dated worktrees, or guessed
branch names as navigation.

![stand-walk-lie](docs/media/stand_walk_lie_wbcfull.gif)

## Verified scope

| Capability | Evidence-backed status |
|---|---|
| Online forward velocity | 0–3 m/s command path; 15/15 frozen benchmark runs passed legacy and quantitative gates |
| Sustained running-trot | Three exact-head strict revalidations at about 3.23 m/s median |
| Sequenced control | stand → walk → stop → lie through the 500 Hz state machine |
| Model-based stack | SRBD MPC + 18-DoF ID-WBC with contact, torque, solver, safety, and plan diagnostics |
| Terrain | sensor-only Phase 2 interfaces exist; no terrain crossing is accepted on `main` |

These are MuJoCo simulation results. They do not establish hardware
performance, sim-to-real transfer, or natural-animal gait. Exact claims and
boundaries are indexed in [`docs/RESEARCH_INDEX.md`](docs/RESEARCH_INDEX.md).

## System

```text
requested velocity -> Phase 1 shaper -> running-trot gait / footholds
                                           |
LowState / lidar -> state snapshot       SRBD MPC
          |                                |
          +-> sensor-only terrain        18-DoF ID-WBC
              model and planner            |
              (no actuation)       limits / safety / diagnostics
                                           |
                                      LowCmd -> MuJoCo
```

The simulator and controller are separate processes connected through Unitree
SDK2 DDS. Research code is organized as:

```text
example/cpp/
├── trot/          lifecycle, 500 Hz control, gait/WBC integration
├── gait/          running-trot and foothold generation
├── terrain/       sensor-derived model and planning interfaces
├── wbc/           SRBD MPC, inverse-dynamics WBC, dense QP
├── contact/       measured contact and wrench handling
├── kinematics/    Go2 FK, IK, Jacobians, rigid-body model
├── scripts/       reviewed runners
├── tests/         unit and integration tests
├── tools/         protocol analyzers and diagnostics
└── experiments/   retained evidence records
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for data flow and
[`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md) for source navigation.

## Build and test

Requires Linux/WSL2, MuJoCo, Unitree SDK2, and the upstream simulator
dependencies. Review `scripts/setup_ubuntu_env.sh` before using the bootstrap.

```bash
cmake -S simulate -B simulate/build
cmake --build simulate/build -j2
ctest --test-dir simulate/build --output-on-failure

cmake -S example/cpp -B example/cpp/build
cmake --build example/cpp/build -j2
ctest --test-dir example/cpp/build --output-on-failure
```

Builds and tests do not establish locomotion acceptance. Phase 2 runs must use
the exact entrypoints, manifest, experiment lock, and analyzer specified by
`CURRENT.md`. General and historical runners are classified in
[`example/cpp/scripts/README.md`](example/cpp/scripts/README.md).

## Evidence and navigation

| Need | Start here |
|---|---|
| Scientific state / current Gate / next step | [`docs/PROJECT_RECORD.md`](docs/PROJECT_RECORD.md) |
| Topic landscape / rejected routes / novelty audit | [`docs/TOPIC_AUDIT.md`](docs/TOPIC_AUDIT.md) |
| Exact active execution frontier | [`CURRENT.md`](CURRENT.md) |
| Complete documentation map | [`docs/README.md`](docs/README.md) |
| Reproduction rules | [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) |
| Accepted claims | [`docs/RESEARCH_INDEX.md`](docs/RESEARCH_INDEX.md) |
| Milestones and rejected work | [`docs/RESEARCH_HISTORY.md`](docs/RESEARCH_HISTORY.md) |
| Retained artifacts | [`example/cpp/experiments/CATALOG.md`](example/cpp/experiments/CATALOG.md) |
| Upstream boundary | [`UPSTREAM_AND_CONTRIBUTIONS.md`](UPSTREAM_AND_CONTRIBUTIONS.md) |

Raw `example/cpp/experiments/_runs/` output is ignored immutable local
evidence: it is never committed or used as instruction. Durable evidence is
curated under `docs/research/evidence/` with a manifest.

## Repository boundaries

Isaac Lab/RSL-RL velocity locomotion lives in
[`kairoi-k/go2-isaaclab-rl`](https://github.com/kairoi-k/go2-isaaclab-rl).
Kine2Go imitation/AMP lives in
[`kairoi-k/kine2go-research`](https://github.com/kairoi-k/kine2go-research).
Neither is a runtime dependency or release track of this repository.

BSD 3-Clause from the Unitree simulator base. Third-party assets retain their
original terms; see [`NOTICE.md`](NOTICE.md). Citation metadata:
[`CITATION.cff`](CITATION.cff).
