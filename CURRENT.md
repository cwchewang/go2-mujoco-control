# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `main`.
Task: [RL capability-map successor](docs/research/TASK_RL_CAPABILITY_MAP_SUCCESSOR_20260924.md).
Closeout: [RL capability-map successor results](docs/validation/rl_capability_map_successor_20260924/RESULTS.md).
Stage: #189 map remains sealed: 5 cm, 10 cm and repeated-step passes retained; low-friction robustness unestablished; corrected yaw remains PERFORMANCE_FAIL; architecture reframed.
Scientific status: MuJoCo is canonical evaluation physics; MuJoCo/MJX is planned but incomplete; Go2 is the first testbed and MJPC/iLQR is a comparator. No generic multi-controller platform, cross-controller bottleneck, or paper gap is verified; Gate 0 remains incomplete.
Last live HEAD: `e40b0933572345f23b37e3bb06350518fde63e76`.
Next: Audit reusable mature Go2 whole-body controller, task and runner implementations; then define a prospective aligned comparison. Any low-friction follow-up must use the v2 semantic fixture and a new task.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
