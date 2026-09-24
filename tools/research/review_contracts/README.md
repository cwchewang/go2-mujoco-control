# Review contracts

Each formal task may point at one tracked manifest here with the optional
`review_contract` field in its task JSON.

The manifest is project-owned. Praxis must not infer which source files or
fields are scientifically meaningful.

Each manifest defines three independent digest domains:

- `science`: question/protocol/metrics/thresholds/budget/retry/falsifier and
  interpretation boundaries that can change the scientific claim.
- `execution`: task/Praxis identity, loader, preflight, launcher,
  authorization, ledger and process-lifecycle semantics.
- `evidence`: trace canonicalization, analyzers, verifiers, evidence bundles
  and publication/closeout semantics.

A file may deliberately appear in multiple domains. For example, a protocol
that owns both thresholds and attempt budget may invalidate science and
execution together. The manifest, not Praxis, defines that policy.

Approval receipts bind to one or more contract hashes, not to HEAD as their
validity key. `target_head` remains provenance. A receipt is inherited across
later commits only while every domain it approved retains the same digest.

Before an expensive reviewer is started, run:

```sh
python3 -m tools.research.review_precheck \
  --task TRACKED_TASK.json \
  --contract tools/research/review_contracts/NAME.json \
  --expected-praxis-issue-number ISSUE \
  --expected-praxis-task-path TASK.md
```

A failing deterministic precheck is a mechanical/plumbing problem and must not
consume an LLM review.
