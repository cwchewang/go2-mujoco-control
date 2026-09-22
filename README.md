# Go2 whole-body control research

Go2 + MuJoCo with a shared, source-bound experiment substrate, a public RL
checkpoint and an offline MJPC/iLQG backend. The original C++ gait/MPC/WBC stack
is retained as a traceable legacy baseline. This is a research fork of
[Unitree MuJoCo](https://github.com/unitreerobotics/unitree_mujoco).

Start with [CURRENT.md](CURRENT.md) for the exact branch, task and evidence.
[PROJECT_RECORD](docs/PROJECT_RECORD.md) owns scientific status; the
[SOP](docs/research/SOP.md) owns execution rules. The present boundary is before
formal experiments: engineering admission does not certify locomotion or Gate 0.

## Development

From the native Linux/WSL repository root, install the independent formatting
and lint environment once. Keep it separate from the frozen experiment runtime.

```sh
python3 -m venv .substrate/dev-venv
.substrate/dev-venv/bin/python -m pip install --require-hashes -r tools/requirements-dev-linux-x86_64.txt
.substrate/dev-venv/bin/python -m tools.check_quality --style
```

Checks read Git-tracked sources, parse Python without executing it, check shell
syntax and maintained documentation, and enforce pinned lint/format rules.
They do not traverse raw outputs or installed dependencies.

For complete native engineering qualification after runtime/bootstrap setup:

```sh
.substrate/venv-reliable/bin/python -m tools.substrate.qualify --output _runs/qualification/fresh_01
```

Use a new output every time. Qualification holds the experiment lock internally.
Setup and zero-step preparation: [substrate guide](tools/substrate/README.md).
Formal capture is separate; the [first-capture protocol](docs/research/SUBSTRATE_FIRST_CAPTURE.md)
fixes its inputs, budget and stopping rules.

## Repository map

| Area | Responsibility |
|---|---|
| [tools/substrate](tools/substrate/README.md) | current runtime contracts, backend admission, preparation, capture and evidence replay |
| [tools](tools/README.md) | developer quality checks, SOP preflight and Atlas/Praxis adapters |
| [example/cpp](example/cpp/README.md) | retained gait, SRBD MPC, ID-WBC, tests and historical analyzers |
| [simulate](simulate) / [simulate_python](simulate_python) | Unitree simulator integration and inherited Python bridge |
| [unitree_robots/go2](unitree_robots/go2) | shared robot/scene assets; frozen physics for the first capture |
| [docs](docs/README.md) | current scientific records, source navigation and indexed history |
| [experiments catalog](example/cpp/experiments/CATALOG.md) | retained records; historical entries do not authorize new runs |

Current capabilities and limitations live in PROJECT_RECORD. Earlier speed,
stand/walk/lie and terrain records remain in [RESEARCH_INDEX](docs/RESEARCH_INDEX.md);
they do not transfer acceptance to a new runtime. No hardware result is implied.

See [CONTRIBUTING](CONTRIBUTING.md), [CODE_GUIDE](docs/CODE_GUIDE.md) and
[ARCHITECTURE](docs/ARCHITECTURE.md) before changing code. Raw `_runs/` and
`example/cpp/experiments/_runs/` are ignored immutable evidence, never cleanup
candidates. Frozen reports and upstream copies retain their original paths.

BSD 3-Clause from the Unitree simulator base. Third-party assets retain their
terms: [NOTICE](NOTICE.md), [upstream boundary](UPSTREAM_AND_CONTRIBUTIONS.md),
[citation metadata](CITATION.cff).
