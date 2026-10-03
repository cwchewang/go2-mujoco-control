# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `research/mjpc-floor-registration-12s-20261003`.
Task: [MJPC closed-trace diagnosis and observer parity repair](docs/research/TASK_MJPC_CLOSED_TRACE_DIAGNOSIS_20261003.md).
Closeout: [MJPC closed-trace diagnosis and observer parity repair](docs/validation/mjpc_closed_trace_diagnosis_20261003/RESULTS.md).
Stage: Stage 3 ACTIVE / OPEN; offline diagnosis and three admission/observer repairs; old adaptation v1 closed.
Scientific status: Original A consumed one attempt/886 steps at 61e543c and failed reference reproduction; CLOSED_NO_RETRY. B NOT_RUN_REPRODUCTION_GATE_FAILED. R4 two 3s replay PASS runs fail saturation repeat tolerance (860 > 200 ticks); no 12s capture. This increment adds zero integration/optimizer/scientific attempts..
Last live HEAD: `829f3c40f86f6f8a35dff33c1ff83d230f6f2d54`.
Next: Finish source-bound qualification/precheck and independent reviews for a NEW four-call, zero-canonical-step original-only observation with production joint mapping and explicit live reset. Do not relaunch A/B v1.

**Related bounded diagnostic:** [Duplicate-FD cold-start diagnostic](docs/validation/mjpc_fd_duplicate_diagnostic_v1_20261002/RESULTS.md) — The fixed-index bug removes duplicate t34 tasks. The reviewed same-process 8-call observation completed at HEAD 6c2dbad: all calls passed, canonical integration 0, costs identical and tick-10 q_des differed by at most 1.01e-10. Planner/warmstart hashes varied across processes; causal interpretation remains open.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
