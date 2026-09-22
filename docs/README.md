# Documentation map

Read [PROJECT_RECORD](PROJECT_RECORD.md) for scientific status and
[TOPIC_AUDIT](TOPIC_AUDIT.md) for research direction. Then follow
[CURRENT.md](../CURRENT.md) to the exact branch, task and result. Repository
[AGENTS.md](../AGENTS.md) and the [SOP](research/SOP.md) govern execution.
A historical protocol applies only when the active task adopts it explicitly.

## Current development and preparation

| Need | Entry |
|---|---|
| Human/agent onboarding, decisions and handoff | [Operating guide](OPERATING_GUIDE.md) / [short task template](research/TASK_TEMPLATE.md) |
| Build, isolate dependencies, qualify and verify | [Substrate guide](../tools/substrate/README.md) |
| Frozen first-capture definitions and stop boundary | [First capture](research/SUBSTRATE_FIRST_CAPTURE.md) |
| Runtime and evidence data flow | [Architecture](ARCHITECTURE.md) |
| Find the smallest source area to change | [Code guide](CODE_GUIDE.md) |
| Quality checks, ownership and compatibility adapters | [Tooling](../tools/README.md) |
| Locks, environments and immutable evidence | [Reproducibility](REPRODUCIBILITY.md) |
| Contribution and review rules | [Contributing](../CONTRIBUTING.md) |

## Retained references

| Area | Meaning |
|---|---|
| [RESEARCH_INDEX](RESEARCH_INDEX.md), [RESEARCH_HISTORY](RESEARCH_HISTORY.md) | historical claims, milestones and rejected work |
| [validation](validation) / [research evidence](research/evidence) | dated result packages; preserve contents and paths |
| [Phase 2 acceptance](research/PHASE2_ACCEPTANCE.md) / [holdout manifest](research/PHASE2_HOLDOUT_MANIFEST.json) | frozen legacy contracts, not current defaults |
| [C++ guide](../example/cpp/README.md) / [WBC and MPC](WBC_MPC.md) | retained hierarchical controller |
| [runners](../example/cpp/scripts/README.md) / [analyzers](../example/cpp/tools/analysis/INDEX.md) | exact historical entrypoints |
| [experiments catalog](../example/cpp/experiments/CATALOG.md) | retained artifacts |
| [upstream](upstream) | upstream documentation preserved verbatim |

Dated delivery files are historical unless adopted by CURRENT.
