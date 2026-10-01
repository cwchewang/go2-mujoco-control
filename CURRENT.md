# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `main`.
Task: [Prospective aligned flat anchor v1 prepared](docs/research/TASK_ALIGNED_FLAT_ANCHOR_V1_20261001.md).
Closeout: [Prospective aligned flat anchor v1 prepared results](docs/validation/aligned_flat_anchor_v1_20261001/RESULTS.md).
Stage: The first RL-vs-MJPC shared flat integration anchor is fully specified and identity-checked, but remains PREPARED / NOT_RUN with canonical physics disabled.
Scientific status: MuJoCo remains canonical evaluation physics; Go2 remains the first testbed. The prepared anchor shares task, scenario, action and evaluator semantics while explicitly preserving different RL/MJPC information and timing regimes. No locomotion comparison, controller ranking, real-time result, cross-controller bottleneck, or paper gap is verified; Gate 0 remains incomplete.
Last live HEAD: `e40b0933572345f23b37e3bb06350518fde63e76`.
Next: Independently review aligned_flat_anchor_v1 task thresholds, body-frame metric, RL/MJPC InformationSpec and TimingSpec differences, and evidence/attempt rules. Keep physics_step_authorized=false until a separate exact-commit capture task is reviewed and explicitly authorized.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
