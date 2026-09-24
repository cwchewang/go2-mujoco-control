# Go2 pre-experiment foundation

This is a source-bound offline engineering foundation, not a locomotion result.
All commands below run in the canonical native WSL checkout. They do not launch
a simulator/controller pair, hardware, training, or a terrain capability sweep.

## Reproduce

Linux x86_64 / CPython 3.10, CMake 3.20+, Ninja, GCC with C++20, git, existing
MuJoCo 3.3.6 native distribution, Unitree SDK and Eigen are required. The Python
runtime is isolated from user/system site packages; all direct/transitive wheel
versions and download hashes are locked in `requirements-linux-py310.lock`.

```sh
python3 -m tools.substrate.bootstrap --install --build
.substrate/venv-reliable/bin/python -m tools.substrate.qualify \
  --output _runs/substrate_qualification/fresh_01
.substrate/venv-reliable/bin/python -m tools.substrate.verify \
  _runs/substrate_qualification/fresh_01
```

Every output must be new. Qualify holds `/tmp/go2_mujoco_experiment.lock` for the
whole process, rebuilds the controller in `.substrate/controller-reliable`, runs
all registered CTests, substrate, preflight and repository/dispatcher tests,
checks hygiene and diff, then runs actual RL/MJPC offline admission. A clean HEAD
is required by default. `--development` explicitly records a dirty engineering
iteration; it cannot stand for clean-head final qualification. The native
optimizer build is separately sealed by bootstrap; stale inputs are rejected.

To run only admission after a successful build:

```sh
.substrate/venv-reliable/bin/python -m tools.substrate.admit \
  --output _runs/substrate_admission/fresh_01 \
  --checkpoint .substrate/rl/policy.pt \
  --mjpc-binary .substrate/headless-reliable/go2_mjpc_admit
```

Bootstrap preserves the earlier `.substrate/venv` and `.substrate/headless-build`
caches. It creates new isolated/runtime build directories rather than silently
reusing an environment that inherited host packages. Existing raw directories
are never cleaned or reused. A failed engineering invocation remains evidence.

## Identity and evidence

Native admission verifies the binary against a build identity covering actual
MJPC/Abseil commits and tracked bytes, local native source, compiler binary,
MuJoCo headers/library, CMake cache, Ninja rules and compile command database.
The CMake target builds unchanged upstream iLQG sources directly, excluding demo
models and GUI dependencies. MuJoCo Python/native libraries must match bytewise.

Runtime verification checks installed versions and installed payloads against
wheel RECORD hashes, including source and shared libraries. Generated `.pyc`
and `.pyo` compilation caches are excluded explicitly: pip may regenerate them
for the local installation path, and NumPy's wheel can contain duplicate
hashed/unhashed cache rows. Their underlying source remains verified.

Each run snapshots all registered scene/include/mesh files before model loading.
The physical fingerprint includes reset keyframes as well as physical arrays
and solver options. Unsupported plugin/attached-model/multi-compiler/external
asset conventions fail closed rather than receiving an incomplete manifest.

`started.json` is written first. Logs stream to exclusive files, including
partial stdout/stderr on timeout. The whole child process group is terminated
on failure/timeout; SIGTERM and keyboard interruption seal FAILED output.
SIGKILL can leave only an incomplete marker; such a directory cannot verify as
admitted. `manifest.json` is written last and file data is fsynced. Independent
verification rejects changed bytes, missing/extra files, symlinks, incomplete
or failed runs. These checks provide reproducibility/integrity, not an external
cryptographic attestation against a user able to rewrite the whole environment.

## Model, action, timing and state

Actuator order is FR/FL/RR/RL; policy order is FL/FR/RL/RR. Names, not positional
assumptions, determine the mapping. Input and command packets own immutable
copies. Strings, booleans, nonfinite arrays and invalid quaternion inputs are
rejected. The shared action exposes feedforward, position/velocity targets and
declared gains. Resolution records PD, total pre-clamp torque and motor ctrl.
Hip/thigh bounds are +/-40 Nm; calf bounds +/-45.43 Nm. Unsupported secondary
force limits/transmissions are rejected; the legacy 35 Nm envelope limits
feedforward, not total plant torque.

The public CTS checkpoint uses a 45-dimensional proprioceptive observation,
50 Hz update declaration, kp=20, kd=0.5 and action scale=0.25. Its verified bytes
are retained in memory so reset cannot silently load changed weights. Separate
instances have separate history; a failed inference requires explicit reset.
Admission replays 12 nontrivial synthetic packets twice after reset. This is
not a physics trajectory or a claim of achieved 50 Hz real-time control.

`ControlClock` represents 50 Hz at 500 Hz as exactly one update per ten integer
ticks, rejects fractional decimation, duplicate/skipped ticks and time drift.
The first-capture runner uses this cadence; it does not impose wall-clock pacing.

MJPC admission uses a static home state, actual iLQG, 21 predicted states at
2 ms and a minimal posture cost. External plant time remains zero. Results
must have correct types, finite nonnegative costs, no rollout warning, no
nominal-cost regression and bounded torques. The fixture is not a locomotion
objective, and its tiny improvement cannot establish useful gait optimization.
MJPC has known-model access; RL receives ideal proprioception. Shared physics
does not make these information conditions equivalent.

## Formal experiment boundary

The SOP preflight entry `tools/research/preflight.py` is restored from historical
source and hardened. It checks exact HEAD, the expected logical branch identity
(named branch or a complete exact Praxis v2 binding for detached worktrees), a
clean state, runner/domain, all reserved participant ports, current UDP
occupancy, global/domain locks, process inspection, files/hashes, changed
surfaces, required review and tests.
Existing output is protected, and tests are skipped after an early hard failure.
Standalone preflight is a readiness snapshot. The substrate launcher now passes
its held lock descriptor to preflight and retains it through capture, with explicit
in-process transport checks. A literal runner-domain check does not replace review of runner
semantics, and a user-supplied approved SHA is not independent proof of review.

The older generic capture template remains unfrozen and is not the first-run entrypoint.
The concrete first-run protocol is now `protocols/rl_flat_v1.json`; see
`docs/research/SUBSTRATE_FIRST_CAPTURE.md` for its prospective rationale and exact
historical commands. Under SOP v0.3, `launch prepare` additionally requires
`--qualification QUALIFIED_BUNDLE --task TRACKED_TASK_JSON`. Task metadata owns
expected branch/accepted-parent/protocol identity. Project-level execution
checks accept a named expected branch for manual runs or a detached Praxis v2
worktree bound to the exact repository, logical branch and frozen commit.
Qualification must be sealed, clean, non-development and match current
runtime/test/model/dependency inputs. Matching inputs reuse offline tests; fresh
lock/process/input checks and exact-head review/start identity remain mandatory.
`launch prepare` guards every real integration entrypoint and stops at
READY_AWAITING_START, or VERIFIED_ZERO_STEP_CAMPAIGN_CLOSED when the permanent
campaign ledger is already claimed. The latter is never a new start permission.
`launch capture` requires separate explicit user start
authorization, source-bound preparation and independent exact-head reviews.
`verify_capture` verifies raw integrity and recomputes the result with an
additional independent algebraic oracle. The local CLI checks the external ledger
by default; `--ledger` selects an archived copy and `--portable` explicitly reports
that the external ledger was not verified. Contact reconstruction from the model
is available in the zero-integration `diagnose` command, separately from algebra.

The first campaign is CLOSED / FAIL and cannot be retried. Its outcome and exact
execution HEAD remain in `docs/validation/substrate_first_capture_20260922/`.
Upstream comparisons use the pinned reference manifest, not latest upstream files.

The generic `evidence.py` checks typed
completeness, unique support names and exact cadence; it preserves the earliest
failure separately from terminal state and rejects samples after termination.
These helpers do not approve or launch experiments. The first-run protocol now fixes the scientific question, reset, information regime,
goals, thresholds, horizon/repeats, support semantics, runner and attempt boundary.
A future start must still validate the exact reviewed HEAD and explicit start record.
No scientific thresholds, legacy evidence or method rankings change here.

Hosted CI runs dependency-light tests, pinned lint/format, tracked-source syntax
and portable documentation checks. Native qualification adds controller CTests,
actual Torch/model fixtures and backend admission. Exact counts belong to each
qualification report, not this guide. CI does not certify a robot capability.


## Verified public source baseline

The source-aligned runner is `python -m tools.substrate.baseline` in the reliable
runtime. See `docs/validation/rl_baseline_20260923/RESULTS.md` for exact conditions,
negative cases and source identity. The measured reference is 1 m/s flat forward
locomotion; this is not a general terrain or robustness claim.

On a fresh checkout, `python -m tools.substrate.fetch_reference` materializes and
hash-verifies the 50 pinned upstream deployment/source assets. Existing mismatched
files are rejected, never replaced. The checkpoint and reliable environment use
the existing substrate bootstrap. Do not run the upstream interactive entrypoint
as an implicit experiment.

Historical source-bound preparation used:

```sh
.substrate/venv-reliable/bin/python -m tools.substrate.baseline prepare \
  --review _runs/rl_baseline_20260923/review_f0eaa44.json \
  --qualification _runs/rl_baseline_20260923/qualification_03 \
  --output NEW_EMPTY_DIRECTORY
```

That review belongs only to the historical execution HEAD. The ten-case campaign
is now CLOSED and cannot be recaptured. New experiments require a new prospective
task/protocol and exact-HEAD review, not an edit of the closed protocol or ledger.
For offline verification of preserved native evidence:

```sh
.substrate/venv-reliable/bin/python -m tools.substrate.baseline verify \
  --prepared _runs/rl_baseline_20260923/prepared_01 \
  --capture _runs/rl_baseline_20260923/capture_01 --output NEW_EMPTY_DIRECTORY
```

Verification checks the native external ledger, replays policy history and
reconstructs contact geometry under a zero-step guard. Plotting uses a separate
analysis Python with matplotlib, without altering the frozen physics environment:
`python -m tools.substrate.plot_baseline --capture CAPTURE --verification VERIFIED --output NEW_EMPTY_DIRECTORY`.
The reusable plant, named policy interface and case definitions are in
`baseline_episode.py` and `protocols/rl_source_v1.json`; source physics retains joint
force limits, and telemetry never forwards the live MjData between steps.
