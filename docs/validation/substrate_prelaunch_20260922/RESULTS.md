# First-capture preparation — 2026-09-22

Parent: `96859ea767efac5557eaf55d95cfd25c95025367`.
Branch: `research/substrate-prelaunch-20260922`.
User boundary: complete preparations, stop before formal experiment start.
Scientific status: NOT_RUN. No real external-plant integration is authorized here.

## Delivered boundary

The prospective first experiment is public CTS flat deployment compatibility,
specified in `docs/research/SUBSTRATE_FIRST_CAPTURE.md` and the machine-readable
`tools/substrate/protocols/rl_flat_v1.json`. It freezes unchanged flat physics,
home/zero-velocity/zero-control reset, tick-zero inference, 50 Hz target updates
with 500 Hz PD, a 10 s command schedule, primary metrics and safety thresholds,
three deterministic repeats, bitwise trace comparison, and first-nonpass stop.
These are prospective engineering goals, not thresholds selected from outcomes.

`launch prepare` performs exact-head SOP preflight, runtime/source/input identity,
real model/checkpoint reset and initial inference with all MuJoCo integrators
guarded before model construction. It produces READY_AWAITING_START at zero
plant time and zero scientific attempts. `launch capture` is a separate explicit
command requiring an actual future user start record, exact prepared manifest,
two independent reviews and continuously locked preflight. No such authorization
is issued here. The independent reviews and final preparation are recorded in
the ignored immutable evidence root, outside the self-referential Git commit.

The formal runner preserves targets, gains, FF/PD/unclipped/clipped torque,
state, aligned contacts and warnings at each tick. An exclusive campaign ledger
prevents output-path changes from becoming retries. Formal verification checks
the sealed manifest, start authorization, passing preflight, copied attempt claims,
attempt count, initial state, every torque resolution and timing invariant,
classification and repeatability. It does not falsely attest the external ledger.

## Validation and review fixes

Development qualification `_runs/substrate_prelaunch_20260922/qualification_dev_02`
passed 159 tests: 34 controller CTests, 76 substrate, 24 preflight and 25 dispatcher.
The same command also admitted real RL inference/reset and native MJPC static
optimization; external plant time stayed zero. The earlier `qualification_dev_01`
is preserved as an earlier implementation, not final exact-head evidence.

Synthetic fixtures exercise all 5000 episode transitions, 500 target updates,
per-tick PD recomputation, full three-pass campaigns, first-failure NOT_RUN arms,
forbidden contacts, posture/quaternion errors, timing corruption, premature
termination, stale PD, forged summaries, missing authorization, repeatability
mismatch, attempt collision and independent reanalysis. They do not call actual
MuJoCo integration. Real TorchScript/model tests are offline admissions only.

Independent review identified missing native-call timeout enforcement, incomplete
zero-step guard coverage, incomplete formal evidence checks, quaternion tolerance
inconsistency and nested process cleanup races. All received focused fixes/tests.
The cleanup test uncovered a real Python selectors interaction: InterruptedError
was swallowed as retryable EINTR; SIGTERM now raises RuntimeError to unwind and
reap the test group. The outer cleanup grace exceeds the inner grace. A separate
watchdog bounds an unresponsive owner; SIGKILL leaves rejected incomplete evidence.

## Exact-head closeout artifacts

The final handoff is accepted only with all of these produced at the same HEAD:

- `qualification_clean_01/`: clean-head 159-test qualification and backend admission;
- `review.json`: independent science/execution decisions bound to that exact HEAD;
- `prepared_01/`: passing SOP preflight, runtime and input hashes, initial state and
  action, zero physics steps and zero attempts, terminal manifest;
- `closeout/`: analysis and provenance for independent verification and archive;
- remote `portable-checks`: 118 dependency-light tests and repository checks.

All are under `_runs/substrate_prelaunch_20260922/`. Failed or interrupted variants,
if any, remain immutable and are named separately; the accepted paths and precise
SHA are recorded by workspace `START_HERE.md` and closeout analysis. Do not infer
formal authorization from a successful preparation, qualification, CI or review.

## What remains after this boundary

Only a later explicit start instruction can authorize this frozen first campaign.
The launcher must still revalidate current inputs/reviews/HEAD under lock at that
time. No further tuning or scientific design choices are needed for this first
campaign. Broader Gate 0 terrain/MJPC/DIAL tasks are subsequent experiments and
are not implied by this flat compatibility protocol or its eventual result.
