# Atlas agent architecture — host experiment boundary

This document defines the intended execution boundary for unattended Go2 research.

## Principle

Luna is a research executor, not a privileged shell on the Atlas host.

- Luna runs in the Codex workspace sandbox and may inspect/edit the task worktree, build, test, and perform offline analysis.
- A live MuJoCo/DDS experiment is executed by a small trusted host capability outside the Codex sandbox.
- The live command comes from a machine-readable manifest frozen in the exact task commit, not from Luna's free-form output.
- After host execution, the same Luna thread resumes to analyze immutable evidence and write the closeout.
- Sol reviews the committed evidence and may accept, revise, or overturn Luna's interpretation.

## Evidence layers

Every host-backed task must preserve enough information to distinguish:

1. **Facts** — host-recorded source/candidate identity, exact command, selected environment, timestamps, exit status, raw-evidence paths and hashes.
2. **Derived metrics** — deterministic calculations from facts/raw evidence.
3. **Luna interpretation** — mechanism and classification proposed by Luna.
4. **Sol review** — independent acceptance, revision, or overturning of the interpretation.

The host facts are generated outside the Luna sandbox. The worker verifies their hashes after Luna's analysis phase, so Luna cannot silently rewrite the execution record or raw evidence.

## Host manifest

A live-capable task may contain exactly one block:

```text
<!-- ATLAS_HOST_EXPERIMENT
{ ... JSON manifest ... }
ATLAS_HOST_EXPERIMENT -->
```

The wrapper reads this block from the exact task commit. The initial supported schema is intentionally small:

- `schema_version`: `1`
- `command`: argv array; no shell string
- `domain_id`: explicit DDS domain; never inferred from source text
- `run_dir`: fresh path under `example/cpp/experiments/_runs/`
- `timeout_s`: host execution timeout
- `environment`: optional non-secret runtime environment overrides

The host capability rejects shell `-c`, path traversal, unsupported executable locations, a pre-existing run directory, and secret-bearing environment keys.

## Two-phase agent loop

For a task with a host manifest:

1. Luna preparation phase: code/test/offline preparation only; no live simulator/DDS execution.
2. Trusted wrapper commits the exact candidate if preparation changed tracked files.
3. Host capability executes the frozen manifest as the normal Atlas user, records provenance, and hashes raw evidence.
4. Same Luna thread resumes in analysis-only mode and reads the host record/raw evidence.
5. Wrapper verifies host record and raw hashes are unchanged, normalizes purely mechanical closeout whitespace, commits the closeout, and requests the trusted push.

A wrapper restart after host completion must not repeat the host experiment.

## Dispatch vNext

GitHub Issues carrying `atlas-task` are the authoritative task queue. GitHub
Actions issue workflows are wake-up signals only; correctness does not depend on
the survival or order of pending workflow runs.

The dispatcher scans the open queue repeatedly and keeps a small local worker
pool. `ATLAS_MAX_WORKERS` defaults to `2`. Different tasks may therefore execute
Luna preparation or analysis concurrently. A resumable task with persisted local
state is scheduled ahead of new FIFO work.

Locking is split by purpose:

- each task commit has its own non-blocking ownership lock, preventing duplicate
  execution of the same frozen task;
- shared repository worktree metadata setup is serialized briefly;
- the global host-live lock is blocking and held only while a trusted host
  capability is executing;
- preparation, analysis, builds, tests, and ordinary closeout do not hold the
  host-live lock.

A dispatcher stays alive for a short idle grace and rescans Issues while active.
This means a task created while another task is already running can be discovered
by the existing dispatcher even if its own GitHub Actions wake-up is later
cancelled by workflow concurrency.

Progress is deliberately allow-listed. Safe states are `queued`, `claimed`,
`preparing`, `candidate_committed`, `waiting_for_host`, `host_running`,
`host_completed`, `analyzing`, `complete`, and `failed`. The dispatcher stores
the safe state locally, emits it to Actions stdout, and maintains one Issue
progress comment in place. Heartbeats update elapsed time during long phases.
Chain-of-thought and raw model output are never published. Comment/API failures
are observability failures only and do not fail the research worker.

Repository-specific policy is exposed through a small configuration seam:
task root, allowed branch prefix, protected prefixes, evidence roots, worker
count, polling/idle timing, and host policy. Go2 remains the first concrete
configuration; the host policy is currently fixed to serialized execution.

## What remains protected

The safety boundary is deliberately narrow:

- GitHub credentials stay outside Luna.
- Luna may not modify `.github/**` or `tools/atlas_*`.
- Luna may not modify raw `_runs` evidence after host execution.
- The host tool enforces exact candidate identity, fresh run directory, explicit domain, global experiment lock, exact argv, and execution provenance.

Symbolic branch attachment, Markdown trailing spaces, and source-code inference of an already explicit domain are not scientific safety properties and must not veto an otherwise valid experiment.
