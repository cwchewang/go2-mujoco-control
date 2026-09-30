# MJPC comparator admission R3 — results

## Identity and decision served

- Task branch: `research/mjpc-comparator-admission-r3-20260930`.
- Task HEAD: `ed23bd62c2ab524e41dd441b0721cfbf3daa5258`.
- Frozen parent/base main: `83b3833f53f66f404cf5f428b9648860adb88323`.
- Upstream source: `johnzhang3/mujoco_mpc@e00c47a5adb9856af2e0f24231bb3a60d5be23c4`.
- Result: source-conditioned engineering admission **PASS**; scientific attempts consumed: **0 / 0**.

The decision served is whether the pinned upstream Agent + QuadrupedFlat can be
reused as an engineering comparator in a later aligned comparison. Passing this
admission advances that separate task. It does not choose MJPC as the project
default, evaluate controller capability, or change canonical evaluation
semantics. Gate 0 remains incomplete.

## Deterministic precheck

**PRECHECK PASS** — branch, exact HEAD, frozen parent, initially clean worktree,
and locally observed `origin/main` were checked read-only. `origin/main` matched
the frozen base. A remote fetch was not performed because the session guardrail
forbids Git metadata writes. The upstream MJPC checkout was clean at the pinned
commit; the declared task/model XML, MuJoCo SDK header/library, MuJoCo Python
3.3.6, and NumPy 2.2.6 were present.

**PRECHECK PASS** — MuJoCo loaded pinned `task_flat.xml`: `nq=19`, `nv=18`,
`nu=12`, plant step 0.002 s. All 12 general actuators had fixed gain 60,
`biasprm="0 -60 -5"`, and `biastype=mjBIAS_NONE`. The implementation repeats
these checks in C++ and fails closed on drift.

## Build and tests

Build environment: Ubuntu GCC 11.4.0, CMake 3.22.1, Ninja 1.10.1, Release.
The pinned Agent/QuadrupedFlat target built without a GLFW or interactive-app
dependency. `ldd` showed the MuJoCo 3.3.6 library and no GLFW library.

Exact build commands used:

```sh
cmake -S tools/substrate/native \
  -B /tmp/mjpc-comparator-admission-r3-build \
  -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DMJPC_SOURCE_DIR=/home/che/dev/go2-workspace/current/.substrate/mjpc \
  -DFETCHCONTENT_SOURCE_DIR_ABSEIL=/home/che/dev/go2-workspace/current/.substrate/headless-reliable/_deps/abseil-src
cmake --build /tmp/mjpc-comparator-admission-r3-build \
  --target go2_mjpc_comparator_probe -j 4
```

The first link attempt exposed missing upstream direct-planner and spline
support sources in the isolated target; those pinned support sources were
included, and the subsequent build completed. No probe was launched by the
failed link attempt. Compile database checks confirmed
`-fno-strict-aliasing` on `agent.cc`, `quadruped.cc`, and
`comparator_probe.cc`; the complete commands and compile database hash are in
[metadata](metadata.json).

Deterministic pin, actuator-semantic, command, and compatibility-metadata tests:

```sh
python3 -m unittest tools.substrate.test_mjpc_comparator
```

Result: **8 tests passed**.

## Engineering probe

The wrapper validates source, runtime, model semantics, build flags, and a new
output path before execution. Exact command:

```sh
flock -n /tmp/go2_mujoco_experiment.lock \
  .substrate/venv-reliable/bin/python -m tools.substrate.mjpc_comparator \
  --source-root /home/che/dev/go2-workspace/current/.substrate \
  --mujoco-root /home/che/.mujoco/mujoco-3.3.6 \
  --build-dir /tmp/mjpc-comparator-admission-r3-build \
  --binary /tmp/mjpc-comparator-admission-r3-build/go2_mjpc_comparator_probe \
  --output example/cpp/experiments/_runs/mjpc_comparator_admission_20260930/run_01
```

The source XML remained unchanged. The correction was applied only to an
ephemeral comparator model copy: `actuator_biastype=mjBIAS_AFFINE`. At the home
setpoint, the nominal model's maximum actuator force was 108; the corrected
model's force was 0. With zero MPC, the corrected model completed 500 plant
steps (1.0 s): all checked values were finite, minimum trunk height was
0.2458165 m, maximum planar displacement was 0.0214311 m, and maximum joint
error from home was 0.1180236 rad. The bounded engineering sanity gate required
finite state, trunk height at least 0.15 m, planar displacement at most 0.10 m,
joint error at most 0.35 rad, nominal setpoint force above 1, and corrected
setpoint force below 1e-8. These are implementation stability checks for this
engineering fixture, not scientific capability thresholds. The home-hold
check passed.

The upstream Agent probe initialized QuadrupedFlat, selected Manual gait
switching and Trot, set Walk speed to 1.0 m/s and turn to 0, then selected Walk
mode. In 50 planning updates and 250 plant steps (0.5 s), all checked values
were finite. Wall time was 2.4405 s; planning p50/p95/max were 47.7981 / 65.8722
/ 67.1570 ms. Trunk height ranged from 0.256145 to 0.366205 m and ended at
0.256145 m. Measured displacement was x=-0.333530 m, y=0.000012 m, planar
0.333530 m. The displacement is recorded as engineering output without a
performance classification or capability inference.

Raw run directory (ignored and preserved unchanged):
`example/cpp/experiments/_runs/mjpc_comparator_admission_20260930/run_01/`.
SHA-256 values:

| Raw member | SHA-256 |
|---|---|
| `started.json` | `f7c754fc818a7b5db8074040c73ecfb84a67d3ae76fdcf74442ee439e587c74e` |
| `stdout.log` | `55f1cc4a9eda6fa0cadb331212680229cd60309de6e2c9d885edb6ecadabc72e` |
| `stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `terminal.json` | `935eb21051d693b2fc33ed89fd3f3949e5d1ce35c3adab00c5188f33a13c247c` |
| `metadata.json` | `960917354fb48ab5301bbc9da1d716cbad1b37c0352f018fb8fb89877f49bb7e` |

The tracked machine-readable copy is [metadata.json](metadata.json). It records
source and XML hashes, MuJoCo/compiler identity, exact command, compatibility
corrections, timing, height/displacement, and finite status. Canonical
evaluation plant modification is recorded as `false`.

## Closeout

`git diff --check` passed. The worktree changes remain present and uncommitted
for the trusted wrapper; no Git metadata writes were made. The next action is a
separate prospective aligned multi-controller comparison task on canonical
evaluation semantics. No terrain map, tuning, paper-gap claim, retry, or new
scientific attempt was introduced.

`python3 -m tools.check_quality` reached the repository hygiene phase, which
reported four links to this task's new, currently untracked `RESULTS.md` and
`metadata.json`. The link targets exist. The session guardrail reserves staging
for the trusted wrapper, so the tracked-link check must be rerun after wrapper
staging.
