# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `main`.
Task: [R1 native MJPC shared adapter](docs/research/TASK_R1_NATIVE_MJPC_SHARED_ADAPTER_20261001.md).
Closeout: [R1 native MJPC shared adapter results](docs/validation/r1_native_mjpc_shared_adapter_20261001/RESULTS.md).
Stage: Shared contracts are implemented; the pinned native MJPC controller is engineering-wired through WholeBodyState and PositionTargetControllerAdapter into canonical direct-torque semantics with a zero-canonical-step PASS.
Scientific status: MuJoCo remains canonical evaluation physics; Go2 remains the first testbed; MJPC/iLQG is now an executable comparator adapter, not a privileged truth source. No aligned locomotion comparison, cross-controller bottleneck, or paper gap is verified; Gate 0 remains incomplete.
Last live HEAD: `e40b0933572345f23b37e3bb06350518fde63e76`.
Next: Define and review the first prospective aligned closed-loop anchor using the shared TaskSpec, ScenarioSpec, InformationSpec, TimingSpec, ControllerAdapter and CanonicalEvaluator. Do not reuse sealed #189 attempts or treat zero-step wiring as locomotion evidence.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
