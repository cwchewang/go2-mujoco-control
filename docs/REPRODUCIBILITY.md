# Reproducibility

Start with [CURRENT.md](../CURRENT.md) and its task/result. Every result belongs
to an exact revision, environment and protocol. Historical acceptance is not
inherited by a refactored binary or a new backend.

## Environments and checks

Use the native Linux/WSL filesystem. Keep pinned `.substrate/venv-reliable`
separate from `.substrate/dev-venv`, which holds the formatter/linter. Runtime
package/payload checks deliberately reject extra development dependencies.

[README](../README.md) has the quality command; the [substrate guide](../tools/substrate/README.md)
has bootstrap, qualification and verification. Native qualification builds the
controller, runs CTest/Python suites and admits actual backends offline. It takes
`/tmp/go2_mujoco_experiment.lock` internally. Other builds/tests/simulations use
the same lock; never nest lock acquisition. An ignored `simulate/mujoco` symlink
may be needed in a fresh checkout; this is environment setup, not a model edit.

## Preparation and capture

The [first-capture protocol](research/SUBSTRATE_FIRST_CAPTURE.md) freezes the
first exploratory flat checkpoint. Preparation binds HEAD, reviews, source,
checkpoint, model closure, runtime and initial state. It guards all real
integration entrypoints and consumes no scientific attempt.

After runtime/test/model/dependency changes, generate new qualification. Matching
content-bound receipts can be reused across prose or merge commits. Always create
new preparation and exact-head
reviews. Never rewrite old bundles. Only a later explicit start instruction can
authorize capture. The launcher retains the lock through SOP preflight, rejects
stale inputs, records attempts and stops on the first nonpass.

## Historical protocols and evidence

Legacy [Phase 2 acceptance](research/PHASE2_ACCEPTANCE.md),
[holdout profiles](research/PHASE2_HOLDOUT_MANIFEST.json), C++/DDS runners and
analyzers keep their original domains, budgets and thresholds. They apply only
to their task or explicit future adoption, not as shortcuts around CURRENT.

Raw `_runs/` and `example/cpp/experiments/_runs/` are ignored immutable output.
Preserve successful, failed and incomplete directories without deletion,
overwrite, rename or cleanup. Curated packages in `docs/validation/` and
`docs/research/evidence/` keep their contents and paths. Record exact revision,
clean/dirty state, effective inputs, analyzer/thresholds and hashes. Independently
verify raw bytes and semantic invariants; reopen and hash archive copies before
handoff. Engineering qualification does not certify hardware or terrain ability.
