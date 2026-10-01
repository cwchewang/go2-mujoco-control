# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `main`.
Task: [R1 MJPC planning / feedback cadence repair](docs/research/TASK_R1_MJPC_FEEDBACK_CADENCE_20261001.md).
Closeout: [R1 MJPC planning / feedback cadence repair results](docs/validation/r1_mjpc_feedback_cadence_20261001/RESULTS.md).
Stage: Shared contracts and native MJPC adapter are implemented; MJPC planning cadence, current-state feedback cadence, and command sampling are now explicit and a two-call zero-canonical-step engineering smoke passes on exact code.
Scientific status: MuJoCo remains canonical evaluation physics; Go2 remains the first testbed; MJPC/iLQG is an executable comparator adapter, not a privileged truth source. The 2 ms feedback cadence is a prospective shared adaptation and observed planning exceeds 20 ms, so no real-time claim is made. No aligned locomotion comparison, cross-controller bottleneck, or paper gap is verified; Gate 0 remains incomplete.
Last live HEAD: `e40b0933572345f23b37e3bb06350518fde63e76`.
Next: Define and independently review the first prospective aligned closed-loop anchor with frozen TaskSpec, ScenarioSpec, per-controller InformationSpec/TimingSpec, ControllerAdapter identities, and CanonicalEvaluator. Do not start canonical physics until that anchor is reviewed and frozen.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
