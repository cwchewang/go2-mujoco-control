# First formal substrate flat capture

Mode: exploratory. Exact engineering parent / merged main:
`c5582af60b802b688e4e526845402deb33cf29cd` (PR #139).
User instruction: 合入主线，然后开正式实验

Question, variables, measurements, thresholds, maximum three sequential attempts
and stop-on-first-nonpass rule are unchanged from
`SUBSTRATE_FIRST_CAPTURE.md` and `tools/substrate/protocols/rl_flat_v1.json`.
Frozen protocol SHA256:
`d8ae529b39207a1fcb4450b163bc0a8b71955513260f0cd6959911705e0d5f35`.
Scientific delta: begin the previously prepared prospective checkpoint; no tuning.
An intact failed trajectory remains FAIL; subsequent arms are NOT_RUN. No retries,
replacement campaign, terrain, MJPC capability comparison, training or hardware.

SOP requires a new branch for a first live attempt. The reserved runner branch
and navigation move to `research/substrate-first-capture-20260922`; this explicit
bookkeeping delta supersedes the preparation branch named in the original
protocol document. No state/control or primary analysis semantics change.
Preparation-only authorization statements describe the earlier task; this user
instruction now permits capture after all exact-head prerequisites pass.

Runner: `.substrate/venv-reliable/bin/python -m tools.substrate.launch`.
Fresh evidence root: `_runs/substrate_first_capture_20260922/`.
Persistent campaign ledger remains `_runs/substrate_attempts/rl-flat-compatibility-v1`.
Refresh clean-head qualification and independent science/execution review,
prepare with the real model/checkpoint at zero steps, and create the exact-head
start record with the actual user instruction. Capture holds the experiment lock
through its own SOP preflight. Verify raw evidence offline, including the separate
live ledger, archive all successful/failed artifacts, and report the earliest
failed boundary if any. Do not change the protocol after observing the result.

Parent acceptance: `docs/validation/repository_cee_20260922/RESULTS.md`.
Closeout: `docs/validation/substrate_first_capture_20260922/RESULTS.md`.
