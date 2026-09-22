# First capture: frozen flat deployment compatibility, v1

This prospectively defines the first experiment only. No dynamics result was
used to select these values. The current user authorization stops before formal
capture; preparing or reviewing this document is not authorization to start.

## Question and scope

Can the pinned public CTS checkpoint produce repeatable, bounded low-speed
flat locomotion through the shared Go2/MuJoCo torque interface? This is an
exploratory deployment-compatibility checkpoint, not a trained-policy optimum,
strong terrain capability baseline, fair RL/MJPC comparison, or Gate 0 verdict.
Passing permits design of subsequent Gate 0 experiments; it does not automatically
launch terrain, MJPC, DIAL, training, or hardware. Failure stops for explanation.

Scientific source: `PROJECT_RECORD.md` sections 5–6. Exact engineering parent:
`96859ea767efac5557eaf55d95cfd25c95025367`. This is a new scientific protocol;
legacy acceptance thresholds and archived results are not changed.

## Frozen inputs and timing

Machine-readable source: `tools/substrate/protocols/rl_flat_v1.json`.
Branch: `research/substrate-prelaunch-20260922`.
Runner: `python -m tools.substrate.launch`; transport is in-process, with no DDS.
Use the pinned isolated CPython 3.10 runtime and one Torch intra/inter-op thread,
deterministic algorithms, seed 0. CPU only. Exact model closure, physical hash,
checkpoint hash, source file hashes, HEAD, runtime and reviews are materialized
by preparation. Any source/HEAD/input drift invalidates preparation.

Unchanged `phase2_flat.xml`: the plane `phase2_floor`; unchanged MuJoCo solver,
friction, robot mechanics and direct-torque motors. Reset every attempt to home
qpos, zero qvel, zero ctrl, time zero, fresh model/data and a reset checkpoint.
The XML home ctrl contains position-like values and is explicitly discarded.
Policy sees ideal proprioception only; no simulator handle or terrain state.

Physics: 2 ms; policy inference: 20 ms. Inference starts at tick 0; target is
held for ten physics ticks, but FF + PD and actuator clipping are recomputed
every physics tick. This intentionally differs from the public deployer's
first ten DEFAULT-target ticks and is a shared-substrate compatibility test,
not an exact reproduction of its startup sequence. No policy retraining,
warm-start trajectory, gains, action scale, smoothing or alternate reset tuning.

Command is body-frame [vx, vy, yaw-rate]: zero until tick 500; linear ramp
from 0 to 0.15 m/s over ticks 500–1000; then [0.15, 0, 0] to tick 5000.
At tick 5000 record endpoint and stop, without another inference or physics step.
Exactly 5001 state frames and 500 target updates in a full successful attempt.
State, contact and warning evidence refer to the same time: `mj_forward` follows
each `mj_step`, without another integration. Endpoint row has no action.

## Prospective engineering gates

Safety evaluated at initial state and every 2 ms endpoint: finite state, quaternion
norm within 1e-6 of unity (otherwise reason `orientation`), no MuJoCo warning,
base-origin z in [0.16, 0.55] m, body-z/world-z
angle <=0.6 rad, and absolute world lateral displacement from initial base <=0.2 m.
Active contact means MuJoCo `efc_address >= 0`. Only floor contact with the four
named foot geoms FR/FL/RR/RL is permitted; other active robot contacts fail.
No minimum instantaneous foot count is imposed during trot. Flat traversal
does not require touching any particular support in sequence.

Endpoint gates: world x displacement from initial base >=1.0 m; mean absolute
world vx error against 0.15 m/s <=0.1 m/s over the inclusive state sample window
ticks 2500–5000 (2501 samples). Turning/slip effects remain visible through
world-frame measurement. Command's ideal continuous integral is 1.275 m; the
1.0 m gate is about 78% of that target. Tracking tolerance is deliberately a
loose deployment gate, not a claim of high-quality tracking. Height/posture and
lateral bounds are prospective engineering guardrails, not empirically tuned
failure separators or replacements for historical acceptance standards.

Record per-physics-step state, command, targets/gains, FF, PD, total unclipped
torque, applied torque and saturation. Report CPU time, process peak RSS, total
elapsed time, policy p50/p95, achieved simulation/wall-time ratio, all failures.
Logging cost is included in wall time; this is not a real-time pacing benchmark.

## Budget, stop and evidence

Maximum three identical sequential deterministic attempts, each 10 simulated
seconds. They test execution repeatability, not independent statistical samples.
Each must pass and match the first complete state/action/contact trace bitwise
(wall-time fields excluded). A mismatch or any other nonpass stops the campaign;
remaining attempts are explicitly NOT_RUN. No automatic retries, replacements,
threshold changes or alternative scenes/checkpoints. A fresh exclusive campaign
claim under `_runs/substrate_attempts/rl-flat-compatibility-v1` prevents changing
output directory or SHA to bypass that stop. A boot failure also stops for review;
the claim itself is not falsely counted as a scientific sample.

The attempt is consumed durably just before persisting its first valid t=0
post-handoff state/control sample. Initial-state failure consumes no scientific
attempt; after reservation, interruption conservatively preserves the consumed
marker. A partial row/write failure can never yield a pass. NaN/Inf cannot be
serialized into strict JSON: preserve the finite prefix and exception, classify
ERROR/incomplete evidence, and stop the campaign; do not claim a complete FAIL
trajectory. Finite non-unit quaternion failures retain their terminal row.
The wall budget is
300 s per episode; a Python alarm attempts normal failure sealing. An independent
watchdog sends TERM one second later and KILL after one additional second if
the owner is unresponsive in native code. Hard kill leaves incomplete evidence,
which verification rejects; the ledger prevents a replacement run.

The formal verifier checks copied campaign/attempt claims, explicit start record,
passing exact-head preflight, attempt count and every recomputed trajectory gate.
Its portable bundle verification does not inspect the separate live retry ledger;
that ledger stays immutable locally and must be archived with a future campaign.

The shared lock is held continuously through exact-head SOP preflight and the
campaign. In-process transport is checked explicitly; legacy DDS checks remain
mandatory for DDS runners. Preflight tests never execute the runner. Reviews
must independently approve science and execution at the exact same HEAD.
These review records are provenance, not cryptographic proof of human consent.

## Prepare, stop, and future start

After independent reviews are recorded in a new ignored JSON file:

```sh
.substrate/venv-reliable/bin/python -m tools.substrate.qualify --output _runs/substrate_prelaunch_20260922/qualification_clean_01
.substrate/venv-reliable/bin/python -m tools.substrate.launch prepare --review _runs/substrate_prelaunch_20260922/review.json --output _runs/substrate_prelaunch_20260922/prepared_01
.substrate/venv-reliable/bin/python -m tools.substrate.verify _runs/substrate_prelaunch_20260922/prepared_01
```

Preparation guards all MuJoCo integration entrypoints before model construction,
loads the real model/checkpoint, checks the initial state's safety and repeated
initial action, but creates no scientific attempt or physics step. Stop at
`READY_AWAITING_START`. Every output must be fresh; suffixes are examples.

Only after a later explicit instruction to begin, record that actual instruction
in a new authorization JSON: action START_FORMAL_CAPTURE, authorized_by user,
user_instruction verbatim, exact head, protocol_sha256, prepared_manifest_sha256,
max_attempts 3. No such start authorization is created during this task.
Invoke `launch capture --prepared PREPARED --authorization AUTH --output NEW_RAW`;
it revalidates the complete preparation and reruns locked SOP preflight.
Analyze without rerunning physics using
`python -m tools.substrate.verify_capture RAW --prepared PREPARED`.

Default launch parser has no implicit capture mode. Engineering admission remains
separate from formal CAPTURE_COMPLETE; a scientifically failed but intact campaign
can verify as FAIL, while infrastructure errors/incomplete raw cannot verify.
