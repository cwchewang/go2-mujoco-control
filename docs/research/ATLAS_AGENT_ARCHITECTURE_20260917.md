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

## What remains protected

The safety boundary is deliberately narrow:

- GitHub credentials stay outside Luna.
- Luna may not modify `.github/**` or `tools/atlas_*`.
- Luna may not modify raw `_runs` evidence after host execution.
- The host tool enforces exact candidate identity, fresh run directory, explicit domain, global experiment lock, exact argv, and execution provenance.

Symbolic branch attachment, Markdown trailing spaces, and source-code inference of an already explicit domain are not scientific safety properties and must not veto an otherwise valid experiment.
