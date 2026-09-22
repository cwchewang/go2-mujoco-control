# Pre-experiment engineering reliability — 2026-09-22

Parent: `82dc82f470973f9a5031c052b89611ba32438d10`. Same foundation branch and
draft PR #138. User request: strengthen all pre-experiment foundations.
Scope: offline engineering. Formal capability, locomotion and hardware: NOT_RUN.

## Changes and acceptance

The previous foundation admitted real backends but did not bind the executable
to current build inputs, inherited host Python packages, reread mutable weights
on reset, lost partial subprocess output on timeout, accepted some weakly typed
evidence fields, and lacked the SOP's live preflight executable.

The implementation now has a fully version/hash-locked isolated Python runtime;
installed source/library payload verification; a native source/compiler/library/
build-command identity; complete model input snapshots; immutable named state
and action packets; strict native result validation; verified in-memory weights,
stateful reset replay and failure latching; exact integer cadence; transactional
evidence, process-group cleanup, failure sealing and standalone verification.

The restored preflight is based on `0e728f20:tools/research/preflight.py`, with
additional lock, UDP-port, process-inspection, test-mutation and output guards.
It preserves exact HEAD/review and changed-surface requirements. It never
launches the runner. A preflight snapshot is not an atomic live-launch guarantee;
the future launcher must recheck while holding its lock.

`tools.substrate.qualify` provides the common offline qualification path. Its
default requires clean HEAD and checks that source bytes, Git diff and HEAD do
not change during the tests. Development iterations are explicitly marked.
Clean-head qualification and independent manifest verification passed at
`1fe1818ea521e457216f821ae2abec1ddae5ed79`. All 131 tests passed. The 17,610 installed
payload files were verified; regenerable bytecode rows are explicitly excluded.
Exact counts, binary/library identities, source hashes, replay result and archive
location are recorded in `analysis.json`; `provenance.csv` identifies raw logs.
Later closeout-only commits preserve these exact executable source bytes.

## Verification scope

The suite covers 34 controller CTests, 52 substrate tests (including real-model,
real TorchScript and fault-injection checks), 20 preflight tests and 25 dispatcher
tests: 131 total. Hosted CI runs the 90 dependency-light tests; native checks are
separate. The final record is based on actual logs rather than this target count.

Fault cases include stale executable identity; dependency/source corruption;
unlocked packages; incorrect booleans, hashes, shapes and support sets; aliasing;
NaN/Inf and float32 overflow; duplicate/skipped/drifting ticks; evidence after
termination; existing output; changed/missing/extra evidence and symlinks; lock
contention; partial timeout diagnostics; forked child termination; SIGTERM and
keyboard interruption; and dirty/wrong-head or mutation during preflight.

Both real backends remain offline admissions. RL replays 12 synthetic packets
identically after reset. MJPC evaluates a short static fixture without advancing
external plant time. This does not establish walking, terrain skill, wall-clock
real-time frequency, comparative optimizer performance or an optimal controller.

## Engineering iterations and preserved evidence

Local immutable raw root:
`/home/che/dev/go2-workspace/current/_runs/substrate_reliability_20260922/`.
`admission_01` and `qualification_01` established the first strengthened path.
`qualification_02` rejected a NumPy wheel bytecode hash: pip had regenerated its
path-dependent `.pyc`, and RECORD contained hashed/unhashed rows for that cache.
The fix excludes regenerable bytecode while continuing to verify its source and
all immutable package payloads. Source corruption remains a failing test.
`qualification_03` passed that check. `qualification_clean_01` is the final
clean-head qualification. Its archive was reopened and every manifest-listed
member rehashed successfully; the archive itself has a separate SHA256SUMS.
All successful and failed directories remain unchanged.

## Remaining scientific decisions

No acceptance thresholds or run counts were invented. The capture template
remains DRAFT_NOT_AUTHORIZED. The initial condition, task goals, information
regimes, horizon/repeats, support semantics, scientific stop conditions, runnable
closed-loop experiment and reviewed exact SHA must be frozen before capture.
No changes were made to legacy controller behavior in this reliability follow-up.
Original flat/terrain evidence and conclusions remain historical and immutable.

Entry commands and constraints: `tools/substrate/README.md`.
