# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `main`.
Task: [Aligned flat anchor v1 independently reviewed](docs/research/TASK_ALIGNED_FLAT_ANCHOR_V1_20261001.md).
Closeout: [Aligned flat anchor v1 independently reviewed results](docs/validation/aligned_flat_anchor_v1_review_20261001.md).
Stage: The first RL-vs-MJPC shared flat integration anchor has passed independent semantic review and exact-code no-physics re-preflight; status remains REVIEWED / NOT_RUN and canonical physics is still disabled.
Scientific status: MuJoCo remains canonical evaluation physics; Go2 remains the first testbed. The 1 s anchor is explicitly an interface/evaluator integration check with broad guardrails, not the sealed #189 performance task. RL/MJPC information and timing regimes remain intentionally different and explicit. No locomotion comparison, ranking, real-time result, bottleneck or paper gap is verified; Gate 0 remains incomplete.
Last live HEAD: `e40b0933572345f23b37e3bb06350518fde63e76`.
Next: Prepare a separate exact-commit capture task and runner with one bounded attempt per controller, raw evidence and independent CanonicalEvaluator replay. Keep physics_step_authorized=false until that capture task itself is reviewed and explicitly authorized.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
