# RL sliding-friction reference v1 preparation

Status: FROZEN / NOT_RUN. This report records prospective configuration and
zero-physics/reference checks, not live execution admission.

Protocol SHA256:
`d10719424809db2037a01f755786b4f93c20ad6cfe2db1455e847ef0f57da89d`.
Task: [independent RL friction task](../../research/TASK_RL_FRICTION_REFERENCE_V1_20261002.md).

The independent id is `rl-sliding-friction-reference-v1`; two new RL-only
challenge arms `rl_friction_1/2` pair with the sealed `rl_baseline_1/2`.
Budget is2 attempts/12000 canonical steps, with no retry. The inherited original
runner/model/controller/safety semantics are unchanged. The prospective [6,12)
auxiliary algebra uses3000 samples and null values for incomplete horizons.
The old campaign's17 NOT_RUN arms remain permanently closed.

Guarded regression completed:66 existing+new targeted tests initially, then9
new-module tests after extracting the actual static model/checkpoint check.
There are67 distinct passing tests across the final selected modules (9 new,
58 unchanged shared-campaign/bounded-condition tests). Real mj_step/mj_step1/
mj_step2 were forbidden. The final-source nine tests include actual static
model/checkpoint preparation. No policy, native optimizer or capture was run.
Style/link/navigation checks and sealed source/reference precheck are recorded
in the final receipt appended below.

The only callable CLI is prospective preparation:
`python -m tools.substrate.rl_friction_reference --output <fresh-absolute-path>`.
It invokes the existing official old-capture verifier with the actual external
ledger, confirms its sealed passing RL pair, compiles/checks the canonical
model, validates friction reset and records all references in a new sealed
output. The static model check may call mj_forward; it advances no dynamics.

No current-head qualification or live preflight exists. The old qualification
has an old complete-input fingerprint and is preserved only as source
provenance. Before START, minimally bind the new two-arm catalog/sealed references
to the unchanged engine, qualify the actual increment, obtain incremental
science/execution review, and perform fresh locked preflight. Review unchanged
infrastructure by its accepted source/hash chain, not by inventing new physics.
