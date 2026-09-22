# Go2 substrate engineering foundation

This package admits real backend dependencies on the existing Go2 physical
model. It is an offline engineering tool, not a locomotion controller or a
Substrate Gate 0 capability verdict. The current admission runs no external
plant timesteps, DDS pair, hardware, terrain sweep, or training.

## Boundaries

`contracts.py` owns named joints, proprioception, and the common action boundary.
The model's actuator order is FR/FL/RR/RL; the published policy uses FL/FR/RL/RR.
Joint position addresses are discovered by actuator transmission names. No
backend may assume those two orders coincide.

The shared action has feedforward, q/dq targets and declared kp/kd. Resolution
records feedforward, PD, their sum, clipping, and applied motor ctrl separately.
This model's hip/thigh limits are +/-40 Nm and calf limits +/-45.43 Nm. The
legacy 35 Nm feedforward envelope is not a total-plant-torque limit.

`rl.py` implements the pinned public CTS checkpoint's 45-dimensional input:
body angular velocity, projected gravity, command, joint position deviation,
joint velocity, previous action. Its declared regime is ideal simulated
proprioception, without terrain access; inference is 50 Hz, kp=20, kd=0.5 and
action scale=0.25. A reset reloads the exported module to reset internal history.
The upstream deployment/configuration identities are in `sources.lock.json`.

`native/admit.cc` uses unchanged upstream MJPC iLQG optimizer source, with a
minimal custom static posture task and 21 prediction states at the model's
2 ms timestep. It does not import the upstream Go2 actuator/model parameters.
The task costs are engineering fixtures, not accepted locomotion objectives.
Its information regime is `known_model_oracle`, distinct from the RL policy.
Identical physics does not make these information budgets equivalent.

The native build intentionally excludes upstream GUI/demo tasks, estimators,
Menagerie and dm_control assets. It links the installed MuJoCo 3.3.6 library;
admission requires its SHA-256 to match the Python MuJoCo library exactly.

`model.py` hashes the registered local scene/include/mesh closure and compiled
physical arrays/options. Task user-sensor decoration must preserve the physical
fingerprint. The include/asset resolver is scoped to these local Go2 MJCFs;
plugins, external URIs and arbitrary MJCF asset conventions are not supported.

`evidence.py` preserves the first failure independently of the terminal reason,
rejects duplicated/skipped/misaligned ticks, and distinguishes traverse from
mandatory-support tasks. Its contract checker checks completeness only; it
cannot authorize a capture. `capture.template.json` intentionally has unfrozen
fields. No live capture command is exposed in this package.

## Reproduce in the canonical native WSL worktree

Prerequisites: Python 3.10+, CMake 3.20+, Ninja, GCC with C++20, git, the existing
MuJoCo 3.3.6 native distribution. All source/checkpoint pins are tracked; large
dependencies and builds stay in ignored `.substrate/`.

```sh
python3 -m tools.substrate.bootstrap --install
python3 -m tools.substrate.bootstrap --build
flock -n /tmp/go2_mujoco_experiment.lock .substrate/venv/bin/python -m unittest tools.substrate.test_substrate tools.substrate.test_native_boundary -v
.substrate/venv/bin/python -m tools.substrate.admit \
  --output _runs/substrate_foundation_manual/admission_01 \
  --checkpoint .substrate/rl/policy.pt \
  --mjpc-binary .substrate/headless-build/go2_mjpc_admit
```

Choose a new output directory for each engineering invocation. Existing output
is rejected; failed directories are preserved. Admission holds the shared lock
itself, records source hashes, source diff, dependency versions/library hashes,
model closure, action decomposition, native stdout/stderr and a file manifest.
Do not nest admission inside another holder of the shared flock.

Hosted CI runs the 12 portable NumPy contract tests. The three real-model checks,
real checkpoint, native optimizer and 34 controller CTests are native-only checks;
hosted CI must not be described as simulator/capability acceptance.

## Next stage

Review benchmark v0 at immutable design commit
`ed3896c3f4355d6409077d61b14d6dc743d6655f`, then freeze start state, command,
duration/repeats, success and failure thresholds, support semantics, shared
physical model, each backend's actuator/frequency declaration, and information
regime. Specify timestamp ordering and reset semantics before implementing the
closed-loop runner. First capability admission should use flat ground with a
predeclared budget and stop gate; terrain is conditional on that result.
No conclusion about MJPC versus RL performance follows from this package.
