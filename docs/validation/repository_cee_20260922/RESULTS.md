# Repository maintainability consolidation — 2026-09-22

Parent: `af4e49856ba10481a77ba6f1aab99bcfe4048095`.
Scope: infrastructure, same preparation branch/PR; no formal experiments.
Task: `docs/research/TASK_REPOSITORY_CEE_20260922.md`.

## Findings and changes

The inventory covered 946 parent tracked files across current tooling, legacy
C++/DDS, simulator integration, robot assets, documentation and retained evidence.
No byte-identical duplicate code group was found. Numbered Atlas files have real
imports/consumers; deleting them would break compatibility rather than simplify it.

README, documentation index, architecture, source guide, reproduction instructions,
contribution guide and upstream map now agree with the current substrate. Old
Phase 2 designs/claims are explicitly historical. Tool ownership is indexed in
`tools/README.md`, without moving frozen files or breaking historical paths.

Maintained Python (`tools/`, `example/cpp/tools/`) now has pinned Ruff formatting
and core lint rules, an independent hash-pinned development environment and
editor defaults. The quality command and CI read Git-tracked sources; they do not
recursively scan venvs, raw outputs or frozen evidence. Link checks reject outside-
checkout or ignored/untracked targets, so local-only files cannot make CI appear
portable. The reviewed developer inventory covers 125 maintained Python files
and 161 tracked Python/shell syntax inputs.

The launcher retains its public entrypoints while review/start validation and
runtime guards live in `readiness.py` and `guards.py`. Formal verification no
longer imports the capture launcher to validate an authorization record. The
analyzer separates frame and action invariants and streams canonical trace
hashing instead of materializing an episode-sized filtered list and JSON string.
Unused imports/bindings were removed explicitly; those are recorded separately
from formatting-only changes.

CMake groups common tests/dependencies, registers each test with its target and
shares the production/test source list. Default Release is preserved. Unlike the
parent, an explicitly requested Debug configuration is now respected; this is a
deliberate developer-build behavior improvement, not a controller change.

## Evidence and measurements

Raw root: `_runs/repository_cee_20260922/`.

| Check | Observed result |
|---|---|
| `audit_01/source-audit.json` | 80 changed Python files have identical ASTs; structural/unused-binding changes listed individually |
| Protected source/assets/history | 695 parent files byte-identical; frozen first protocol SHA unchanged |
| Existing raw bundles | 15 successful/failed historical bundles independently reverified, unchanged |
| Old/new analyzer | 10 synthetic success/fault inputs give identical results or exact exception type/message |
| CMake Release identity | all 82 compile/link plan files identical, same 34 CTest names |
| Explicit Debug/default Release | both configured and effective controller flags checked |
| Development qualification | 164 passed: 34 CTest + 77 substrate + 24 preflight + 29 repository/dispatcher |
| Backend admission | actual RL reset/inference and native MJPC static optimization passed; external plant time zero |

On the same synthetic 5,001-frame trace, the old and new canonical hash are equal.
Tracemalloc peak temporary allocation for hashing fell from 18,095,666 to 18,215
bytes (~99.9% lower). Median time across five untraced calls was 0.1040 vs 0.1036 s.
That supports a memory improvement with approximately unchanged wall time for
this fixture, not a robot throughput or universal performance claim. Full frames
are still retained for analyzer metrics; this is not a fully streaming capture
analyzer. Raw measurements: `audit_01/trace-hash-benchmark.json`.

Development checks live in `qualification_dev_01/`; build comparisons and Debug
checks in `build_audit_01/`. All validation artifacts remain immutable.

## Final exact-head handoff

The accepted current handoff requires fresh `qualification_clean_01/`, independent
science/execution `review.json`, `prepared_01/` and remote portable CI at one final
HEAD. Preparation guards real integration and must report zero physics steps and
zero attempts. The final SHA, archive hash and exact accepted paths live in
`closeout/analysis.json` and workspace `START_HERE.md`. Earlier af4e498 preparation
remains preserved as historical evidence; it is not silently reused at a new HEAD.

The frozen protocol, robot model and legacy controller mathematics are unchanged.
Large legacy C++ control modules and vendor codecs remain explicit ownership
boundaries; rewriting them just to reduce line counts would add experimental
risk without demonstrated benefit. This checkpoint establishes maintainable,
continuously checked development criteria, not an unmeasurable absolute optimum.
Formal capture remains NOT_RUN and awaits a separate future start instruction.
