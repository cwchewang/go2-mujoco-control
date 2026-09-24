# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `main`.
Task: [RL capability-map successor](docs/research/TASK_RL_CAPABILITY_MAP_SUCCESSOR_20260924.md).
Closeout: [RL capability-map successor results](docs/validation/rl_capability_map_successor_20260924/RESULTS.md).
Stage: RL capability map characterized: flat reference plus 5 cm, 10 cm, repeated-step and low-friction cases pass; half-speed, reverse, lateral and yaw probes fail frozen performance gates.
Scientific status: strong RL baseline shows bounded 1 m/s terrain success but command-space weaknesses; no cross-controller bottleneck or paper gap established; full Gate 0 remains incomplete.
Last live HEAD: `e40b0933572345f23b37e3bb06350518fde63e76`.
Next: run MJPC on aligned command/terrain cases, compare failure maps, and use DIAL only for a specific diagnosed local-gradient/contact-mode/multimodality question.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
