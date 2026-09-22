# Tooling ownership

[CURRENT](../CURRENT.md) selects the task. Tooling is not an alternate plan.

| Area | Entry and boundary |
|---|---|
| Developer quality | `python -m tools.check_quality --style`; pinned separate development venv, tracked files only |
| Current substrate | [substrate/README](substrate/README.md); source-bound admission, guarded capture and independent evidence |
| Research execution | `research/preflight.py`; HEAD, transport, lock, review and changed-surface checks |
| Atlas/Praxis | `.atlas/project.json` selects `atlas_research_task_v6.py`; workflow dispatch uses the pinned external Praxis core |

## Atlas compatibility chain

Numbered files are not duplicate copies. v6 imports behavior from
`atlas_research_task.py` and v2/v3/v4; v5 preserves the fetch-before-discovery
entrypoint. v1/v2 dispatchers and `atlas_host_experiment.py` remain compatibility
and host surfaces, tested in `tools/tests`. `atlas_issue_state.py` and
`atlas_push_research_result.py` own issue/state and validated publication.
Preserve command paths unless migrating consumers and fixtures together.

## Ownership and style

Maintained Python is `tools/**/*.py` and `example/cpp/tools/**/*.py`, selected in
`pyproject.toml`. Formatting and core lint run in CI. Syntax checks also cover
tracked upstream integration scripts without executing them. Vendor codecs,
frozen models/evidence, raw output and installed dependencies are excluded from
automatic formatting.

First-party C++ remains organized by gait, contact, kinematics, WBC, terrain,
trot and tests; [CODE_GUIDE](../docs/CODE_GUIDE.md) maps those boundaries.
Historical analyzers retain filenames and scientific semantics. New shared
helpers/directories must remove a real duplicate responsibility.
