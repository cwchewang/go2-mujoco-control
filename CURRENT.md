# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `research/mjpc-floor-registration-12s-20261003`.
Task: [Unique-index diagnostic excludes duplicate writes as sole repeat-drift source](docs/research/TASK_MJPC_FAITHFUL_DEDUP_OBSERVATION_20261004.md).
Closeout: [Unique-index diagnostic excludes duplicate writes as sole repeat-drift source](docs/validation/mjpc_faithful_dedup_observation_20261004/RESULTS.md).
Stage: Stage 3 ACTIVE / OPEN; unique-index-only private diagnostic COMPLETE / VERIFIED.
Scientific status: New4privatecalls completed:9808upper/16384reserved,canonical0/formal0. Verified one t34 percall; tick10repeatdiff1.3625101047409771e-11/cost0,within unchanged1e-9. Duplicate simultaneous t34 writes unnecessary for observed repeat drift; warmstart unique contribution unisolated. A/B remain closed,R4failed,no12s..
Last live HEAD: `829f3c40f86f6f8a35dff33c1ff83d230f6f2d54`.
Next: New four-call budget CLOSED. Further causal split requires warmstart-only intervention with separate frozen scope/budget; do not rerun old A/B or reopen either completed ledger.

**Related bounded diagnostic:** [Duplicate-FD cold-start diagnostic](docs/validation/mjpc_fd_duplicate_diagnostic_v1_20261002/RESULTS.md) — The fixed-index bug removes duplicate t34 tasks. The reviewed same-process 8-call observation completed at HEAD 6c2dbad: all calls passed, canonical integration 0, costs identical and tick-10 q_des differed by at most 1.01e-10. Planner/warmstart hashes varied across processes; causal interpretation remains open.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
