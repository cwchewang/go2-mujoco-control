# Substrate foundation — 2026-09-22

Disposition: engineering implementation and offline admission. Capability:
NOT_RUN. Base: `02caf95b120bba07ae67a9e7b440194fb0ac8ddb`. Branch:
`research/substrate-foundation-20260922`. The final branch commit contains this
report; exact hashes of the executable source and binaries are in admission.json.

The user authorized starting the project, improving existing engineering, and
establishing the next phase. This task intentionally implements the foundation
before freezing a new locomotion experiment. No legacy scientific result or
acceptance threshold has been changed.

## Existing control improvements

Clean WriteMotorCommands now re-evaluates eligibility after the current tick's
WBC update. Previously the boolean was captured before that update, so entry,
failure and recovery could use the previous tick's eligibility. Focused tests
exercise the actual writer through success, solver rejection, mapping rejection,
recovery, excessive torque and NaN. Rejection retains explicit impedance and
zero feedforward/desired velocity; it is not zero total plant torque.

The strict QP test now starts with an accepted output, forces inconsistent
normal-force inequalities, and verifies that no stale success/torque survives.
DDS tests use a private proc fixture for positive cleanup while preserving
referenced, unreadable and active-process negative cases. Production cleanup
permission checks remain unchanged.

The final current-source C++ suite and the substrate/dispatcher checks are
recorded in `checks.json`. No new tuning or claims of best achievable gait,
terrain capability or real-time control latency are made.

## Executable foundation

Source pins: MJPC Go2 fork `e00c47a5adb9856af2e0f24231bb3a60d5be23c4`;
public RL repository `30e74dc507bec7a642a8c98be26081f2c6f0822d`;
Abseil `fb3621f4f897824c0dbe0615fa94543df6192f30`.
Checkpoint SHA-256:
`9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d`.
MuJoCo 3.3.6, Torch 2.6.0+cpu, NumPy 2.2.6. No training was performed.

Four existing scene closures were loaded/forward-evaluated: flat, 5 cm step,
10 cm step and repeated steps. This is loader admission, not terrain traversal.
The model's named actuator mapping and limits are recorded. The decorated MJPC
task preserves the compiled physical fingerprint. Native and Python MuJoCo
libraries have identical bytes. Both backends enter the same named action
resolution interface, which records feedforward/PD/total/clipped motor torque.

The frozen RL model produces finite position targets and reproducible first
inference after reset. MJPC runs the actual upstream iLQG optimizer on a static
home state with a 40 ms prediction horizon, finite cost, no rollout warning and
finite bounded action. External plant time remains zero. The tiny cost change
at this short static fixture is not evidence of useful gait optimization.

RL uses ideal proprioception; MJPC has known-model access. Internal RL training
objectives and the static MJPC residual fixture are different. This admission
therefore establishes wiring and provenance, not comparative control quality.

## Evidence and engineering iterations

Immutable local raw root:
`/home/che/dev/go2-workspace/current/_runs/substrate_foundation_20260922/`.
The final admitted directory is listed in `checks.json`; its curated JSON and
manifest are copied alongside this report without replacing the raw source.

admission_01 failed because wrapping MJCF outside the scene directory changed
relative mesh resolution. It is preserved. Explicit mesh source resolution
fixed this; admission_02 passed. admission_03 additionally checked exact dynamic
library identity and native rollout status. admission_04 added the final named output boundary; admission_05 covers
the sealed implementation, secondary-force-limit rejection, and the tested
bootstrap entrypoint. All five raw directories are preserved. These are engineering iterations, not scientific
attempts under a failed capability gate.

Initial upstream GUI build encountered missing Xinerama headers and an unrelated
large Menagerie asset download. The task's configure process was stopped, and a
minimal target now builds unchanged optimizer sources directly; no host packages
or upstream source were patched. Bootstrap logs remain under `.substrate/logs/`.

## Next acceptance boundary

Benchmark v0 design reference:
`ed3896c3f4355d6409077d61b14d6dc743d6655f`. Next freeze the initial state,
commands, information regimes, action/frequency semantics, terminal metrics,
thresholds, horizon, repeats and support semantics; then implement and review
the closed-loop runner. Preserve earliest backend failure separately from task
termination. Decide traverse versus mandatory-support explicitly.

The capture template intentionally contains nulls and fails completeness checks.
The generic evidence checker does not provide scientific approval. Formal Gate
0, flat locomotion, terrain capability, DIAL/MPPI and hardware remain NOT_RUN.
The legacy data remains historical; the new control binary needs a separately
authorized and frozen acceptance protocol before inheriting any live claim.

Reproduction commands and module contracts are in
`tools/substrate/README.md`. This branch is submitted as a draft PR for review,
not merged into the stable line by this task.
