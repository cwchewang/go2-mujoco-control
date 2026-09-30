# MJPC comparator feedback repair — results

## Identity and decision served

- Task branch: `research/mjpc-comparator-feedback-repair-20260930`.
- Task HEAD: `c529d99e43cc348054a9d906838c2c709fd01964` (the worktree parent is `eb4c6917e0ae77a1c3315697c5871b29010b3b0d`).
- Pinned source: `johnzhang3/mujoco_mpc@e00c47a5adb9856af2e0f24231bb3a60d5be23c4`.
- Result: repaired source-conditioned engineering admission **PASS**; scientific attempts: **0 / 0**.

This admission checks the bounded headless Agent path with iLQG feedback evaluated against the current Agent state. It supersedes the R3 action-feedback interpretation only. It does not classify locomotion capability, select a project default, or complete Gate 0.

## Deterministic precheck

**PRECHECK PASS** — exact branch, task HEAD, expected parent, and initially clean worktree matched. Git metadata writes are prohibited by the task-session guardrail, so no remote fetch was run; the existing `origin/main` guidance was read without modifying refs.

**PRECHECK PASS** — the pinned MJPC checkout was clean at the required commit. In upstream `mjpc/planners/ilqg/policy.cc`, `iLQGPolicy::Action` performs state-reference interpolation and feedback-gain application only when `state` is non-null. Upstream `mjpc/testspeed.cc` passes `agent.state.state().data()`. The task/model XMLs loaded with the expected 19/18/12 dimensions and 2 ms plant step; the nominal actuator semantics remained gain 60, bias `0 -60 -5`, and `mjBIAS_NONE`. MuJoCo SDK files, MuJoCo Python 3.3.6, and NumPy 2.2.6 were present. The new output path was absent and is ignored under `_runs`.

## Implementation

The existing plan-before-action loop now passes `agent.state.state().data()` to `ActionFromPolicy` after `agent.SetState(data)`. The probe emits `action_feedback_state: current_agent_state` only when the pointer passed is the current Agent state vector; a null or different pointer emits an invalid label and fails the probe. The metadata validator rejects missing, null, or changed feedback-state labels. Deterministic tests cover label drift and verify the C++ call passes the state vector set by `agent.SetState`.

Planner, task, command, timing, source pin, actuator compatibility correction, plant semantics, and the 500-step home-hold checks were unchanged.

## Build and tests

Build environment: Ubuntu GCC 11.4.0, CMake 3.22.1, Ninja 1.10.1, Release. The existing headless target built successfully. The compile database verified `-fno-strict-aliasing` for `agent.cc`, `quadruped.cc`, and `comparator_probe.cc`; `ldd` showed MuJoCo 3.3.6 and no GLFW dependency.

```sh
cmake -S tools/substrate/native \
  -B /tmp/mjpc-comparator-feedback-repair-build \
  -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DMJPC_SOURCE_DIR=/home/che/dev/go2-workspace/current/.substrate/mjpc \
  -DFETCHCONTENT_SOURCE_DIR_ABSEIL=/home/che/dev/go2-workspace/current/.substrate/headless-reliable/_deps/abseil-src
cmake --build /tmp/mjpc-comparator-feedback-repair-build \
  --target go2_mjpc_comparator_probe -j 4
```

`.substrate/venv-reliable/bin/python -m unittest tools.substrate.test_mjpc_comparator` completed with **10 tests passed**.

## Repaired engineering admission

The exclusive lock was held for the full wrapper preflight and probe. Exact command:

```sh
flock -n /tmp/go2_mujoco_experiment.lock \
  .substrate/venv-reliable/bin/python -m tools.substrate.mjpc_comparator \
  --source-root /home/che/dev/go2-workspace/current/.substrate \
  --mujoco-root /home/che/.mujoco/mujoco-3.3.6 \
  --build-dir /tmp/mjpc-comparator-feedback-repair-build \
  --binary /tmp/mjpc-comparator-feedback-repair-build/go2_mjpc_comparator_probe \
  --output example/cpp/experiments/_runs/mjpc_comparator_feedback_repair_20260930/run_01
```

The wrapper revalidated the source, resources, model semantics, build flags, metadata, and fresh output path. The 500-step (1.0 s) home-hold passed: corrected setpoint force 0, minimum trunk height 0.2458165 m, maximum planar displacement 0.0214311 m, and maximum joint error 0.1180236 rad. In the 50-update / 250-step (0.5 s) Agent probe, all checked values were finite and mode was Walk. Measured displacement was x=-0.333530251728 m, y=0.0000121784 m, planar 0.333530251951 m; planning p50/p95/max was 48.9669 / 60.3771 / 62.5398 ms. These are engineering measurements only.

R3's historical output recorded 0.333530251951 m planar displacement with a null feedback-state pointer. The repaired run recorded the same value at the reported precision. Both values are retained descriptively; neither is a locomotion capability classification or evidence of a capability change.

New ignored raw run (preserved unchanged after capture):
`example/cpp/experiments/_runs/mjpc_comparator_feedback_repair_20260930/run_01/`.

| Raw member | SHA-256 |
|---|---|
| `started.json` | `4cb81a19d48433cf82a8e85127250111104a28d4b7b2f639ed2872d6b7672a2a` |
| `stdout.log` | `d994fe662c5e58ee5f5307862679de887720b30db75cae5f256c0c59a1b42214` |
| `stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `terminal.json` | `f2a0933750ee12e910ac9c13fbc906e7efe8ba6df0dd11a0da714d01080a0b28` |
| `metadata.json` | `75635c8bbb67dc96ec314a198c4d3a5d7e635133b246a6f02b4d19da83493ba4` |

## Historical R3 evidence retained

The parent R3 closeout remains the historical record of its original capture and engineering results. Its recorded raw path was `example/cpp/experiments/_runs/mjpc_comparator_admission_20260930/run_01/` in the R3 worktree. The R3 capture was a 50-update / 250-step finite Walk probe, with 0.333530251951 m measured planar displacement and no performance classification. Its recorded raw hashes are retained here as provenance; this repair did not modify that historical path.

| R3 raw member | SHA-256 recorded by the parent closeout |
|---|---|
| `started.json` | `f7c754fc818a7b5db8074040c73ecfb84a67d3ae76fdcf74442ee439e587c74e` |
| `stdout.log` | `55f1cc4a9eda6fa0cadb331212680229cd60309de6e2c9d885edb6ecadabc72e` |
| `stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `terminal.json` | `935eb21051d693b2fc33ed89fd3f3949e5d1ce35c3adab00c5188f33a13c247c` |
| `metadata.json` | `960917354fb48ab5301bbc9da1d716cbad1b37c0352f018fb8fb89877f49bb7e` |

The tracked [metadata](metadata.json) now describes the repaired run and links it to the historical R3 measurement. Gate 0 remains incomplete; the next scientific step remains a separate prospective aligned multi-controller comparison on canonical evaluation semantics.

## Closeout

No retry, tuning, terrain sweep, or scientific attempt was introduced. `PROJECT_RECORD.md`, `CURRENT.md`, and `TOPIC_AUDIT.md` remain accurate: the admission is bounded engineering evidence, the aligned comparison remains next, and Gate 0 is incomplete. Intended tracked changes remain uncommitted for the trusted wrapper; no Git metadata writes were made.
