# Execution review basis

Target: `a31fe64afd6b7669765fa83137d70ab6dad11c75`
Reviewer identity: `gpt6-luna-max-execution-review-v2-20260923`

## Veto findings

1. **START is replayable before campaign claim.** `baseline.capture` validates the prepared bundle, task, identity, authorization, qualification and runtime, then starts an evidence run and performs fresh preflight before `ledger.mkdir(...)` and writing `campaign.json` (`reviewed_sources/tools/substrate/baseline.py`, lines 208-272). If an invocation fails during the earlier validation or preflight, it leaves no protocol ledger. The same valid authorization can then be supplied to another invocation. The frozen formal task says capture is invoked exactly once regardless of outcome. The code does not persist consumption of the authorization before these failure points.

2. **External ledger claims are not crash-durable by construction.** `write_new` opens exclusively, flushes and fsyncs the file (`reviewed_sources/tools/substrate/integrity.py`, lines 39-48). It does not fsync the containing directory. `baseline.capture` creates and writes the campaign/attempt claim names in the ledger (`reviewed_sources/tools/substrate/baseline.py`, lines 265-312). `EvidenceRun.__exit__` later fsyncs only the capture output directory, not the ledger directory (`reviewed_sources/tools/substrate/integrity.py`, lines 132-151). A filesystem crash can therefore lose ledger directory entries even when claim contents were fsynced, reopening the replacement-run guard.

3. **Capture deadline excludes setup and analysis.** The per-case `Plant` and policy construction occur before `wall_deadline`; trace analysis occurs after it (`reviewed_sources/tools/substrate/baseline.py`, lines 284-350). The independent watchdog only runs while `wall_deadline` is active (`reviewed_sources/tools/substrate/guards.py`, lines 30-59; `reviewed_sources/tools/substrate/watchdog.py`). A stall in those uncovered regions can leave the already-claimed campaign hanging without the task's 300-second bound.

## Other review findings

- Detached identity is exact for repository, logical branch, task commit, complete Praxis environment and clean worktree: `identity.py`, `launch.py`, and `preflight.py` snapshots are included.
- Source, checkpoint, model, task/protocol and runtime content are checked before use. Qualification binds clean state and static engineering admission; it does not execute the formal campaign.
- Preparation wraps MuJoCo step functions with a zero-step guard and records its exact source/review/resource bindings.
- The explicit START record binds the exact prepared manifest, protocol, HEAD and attempt budget. User provenance is a procedural string, not a signature.
- First-nonpass behavior and declared exact-repeat digest comparisons match the protocol.
- The prescribed `baseline verify` path performs substantial offline replay. It recomputes performance output using the same `analyze` function as capture, with an independent body-axis MAE oracle only; mean speed, lateral drift and yaw do not have separate metric implementations.
- `tools/substrate/verify_capture.py` has a different status schema, but is not called by the formal task's `baseline verify` command; it is not used as a veto finding here.

## Review scope

Static inspection only. The frozen task prohibits qualification/capture/scientific runs for this reviewer. No tests or policy inference were invoked.
