# Repository governance

These are ownership and lifecycle rules. Use [OPERATING_GUIDE](OPERATING_GUIDE.md)
for planning/handoff and [SOP](research/SOP.md) for scientific execution.

## One owner for each kind of truth

| Question | Authority |
|---|---|
| What work is authorized now? | Current user instruction and active task; [CURRENT](../CURRENT.md) locates that task |
| What is the project for; what is established? | [PROJECT_RECORD](PROJECT_RECORD.md) |
| Why pursue or reject a topic? | [TOPIC_AUDIT](TOPIC_AUDIT.md) |
| How do experiments execute and retain evidence? | [SOP](research/SOP.md) and the task's frozen protocol |
| How do code changes get validated? | [CONTRIBUTING](../CONTRIBUTING.md) and module guides |
| What happened in a run? | Immutable raw, source/protocol identity and verified result |

docs/research/current.json owns navigation. CURRENT and workspace START_HERE
are generated views. A new user instruction can narrow the scope; update the
navigation instead of continuing a stale next-action list. History is context,
not new authorization. Do not duplicate authoritative state in convenience pages.

## Repository scope

This repository owns the shared Go2/MuJoCo evaluation substrate, pluggable runtime
adapters, task/evaluation definitions and source-bound evidence. Public RL
adapters are within scope. Keep third-party training frameworks and downloaded
checkpoints outside maintained source with pinned provenance and licenses;
integrating an adapter does not require vendoring a whole training repository.
The old fixed-gait Phase 2 stack is a retained baseline, not the current route.
Historical multi-repository names do not establish current ownership; discover
the actual remote and active task through AGENTS.

## Branches and identity

main is the integrated line and changes through reviewed PRs with required CI.
Use one owned branch per coherent task/campaign, not per replicate or prose edit.
Record the base SHA and scope. Preserve divergence and other owners' work.

Accepted milestone tags are annotated with source SHA, evidence and acceptance
scope. Archive tags preserve exact completed branch tips without upgrading their
scientific status. Existing lightweight archive tags remain valid identity
anchors. Tags are immutable; never move them to repair a record. Remote archive
tags are protected against update/deletion. Retire only owned completed branches
after verifying their current remote tip and surviving main/tag reference;
never delete historical branches by wildcard.

## Evidence and claims

Code merged, engineering admitted, experiment valid, task passed and causal claim
supported are separate statements. Retain failed and incomplete evidence.
Raw `_runs/`, builds, dependencies and checkpoints stay ignored; compact
protocols/results and provenance belong in Git. Raw and sealed archives are
immutable; generated archive indexes may be refreshed. The
[workspace standard](governance/WORKSPACE_STANDARD.md) owns storage rules.

For the legacy controller, configuration precedence is compiled defaults,
versioned profile, then explicit CLI override; record semantic environment.
Other backends declare effective configuration through their task and input
manifest. There is no implicit permission to override a frozen protocol.

## Proportional review

PRs explain the concrete change, relevant validation and scientific impact.
Prose-only work does not need experimental artifacts or full native qualification.
Runtime and scientific changes follow SOP review rules. Review the diff and
required checks before merging. Hosted portable CI does not certify native
simulator integration or robot capability. Complete fields and hashes cannot
substitute for a justified research decision.
