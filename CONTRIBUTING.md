# Contributing

Read [AGENTS.md](AGENTS.md), [PROJECT_RECORD](docs/PROJECT_RECORD.md) and
[CURRENT.md](CURRENT.md) first. Scientific state, active execution and code
navigation have different owners; old experiments cannot override the active
task and [SOP](docs/research/SOP.md).

## Development

Use the isolated development environment and quality recipe in [README](README.md).
Ruff is pinned with a wheel hash. Format maintained Python with
`.substrate/dev-venv/bin/python -m ruff format`; configuration selects `tools/`
and `example/cpp/tools/`. Do not mass-format upstream/vendor sources, robot
assets, frozen protocols or retained evidence.

Prefer one module per responsibility and explicit imports. Reuse named packets,
evidence primitives and launcher guards instead of alternate launch paths.
Test behavior: malformed inputs, state/cadence, process termination, evidence
identity and old/new equivalence. Avoid tests that just restate implementation.

Run affected tests, then native qualification for runtime/evaluator/preflight
changes. It owns the shared lock; do not wrap it in another flock. Use existing
CTest targets for legacy C++ changes. Formatting and compilation are not
performance evidence. Routine scans read Git-tracked source only.

Historical filenames are part of provenance. Versioned Atlas adapters are a
dependency chain, not interchangeable old copies. Preserve upstream attribution.

## Research semantics and reviews

Call out changes to trajectories, protocol, analyzer meaning or claims. Follow
SOP review rules and bind execution approval to the final SHA. Preparation is
always new for the actual execution identity; sealed offline qualification may
be reused only when the complete implementation/environment fingerprint matches.
Prepare requires `--qualification` and a tracked `--task`; never edit old bundles.
User permission to start formal experiments remains separate. Local capture
verification checks the attempt ledger; `--portable` explicitly omits that check.

Edit `docs/research/current.json`, then run `python -m tools.research.workspace`
to regenerate CURRENT.md. `--check` detects drift. Workspace policy sources are
under `docs/governance/`; `--workspace /home/che/dev/go2-workspace` applies them,
refreshes the verified archive inventory, and generates START_HERE.md.

PRs should explain the concrete behavior/change, validation and historical
comparison boundary. Failed experiments remain in the evidence record.
