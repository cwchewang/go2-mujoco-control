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

## Sealed PRECHECK PASS receipt

Preparation source HEAD:
`eaa9976627bbb6df4e67df385e236f14df93db1d` (clean named branch).
Output:
`_runs/rl_friction_reference_prep_20261002/freeze_precheck_20261002T101816347837Z`.
Manifest SHA256:
`72bc4db5e8b29c6ef8e641be6aaec17171dd6f6da20ad9b973cf9de3e789fb57`.

The production precheck returned PRECHECK_PASS. It verified the original
capture manifest66630a6c..., its actual external ledger, all source closure and
the two passing repeatable RL references. All15 inherited runtime-source files
were compared byte-for-byte to the original capture head with git object bytes.
The new output root and new ledger were absent. Real canonical integration
was forbidden; controller construction and native identity startup were also
explicitly blocked around this invocation. Counts: new scientific attempts0,
canonical physics0, private planning calls0. Static compilation/mj_forward
does not imply an integrated trajectory.

Curated exact copies are [precheck admission](precheck-admission.json),
[reference chain](reference-chain.json), [source verifier](source-verification.json),
[arm catalog](planned-arms.json), [sealed reference auxiliary values](auxiliary-reference.json)
and [source hashes](unchanged-runtime-source-hashes.json).
[Checks receipt](checks.json) states the exact test invocations; it is not a
native qualification. [Review packet](review-packet.json) scopes the incremental
review and explicitly marks live admission NOT_CREATED. Final prose/hygiene/
navigation checks passed with203 tracked source files and167 formatted files.
[Manifest](manifest.json) covers this curated package with
[provenance](provenance.csv).

The parallel [MJPC read-only diagnosis](mjpc-readonly-diagnostic.md) describes
sealed actual contact constraints/joint tracking and missing private predictions.
No MJPC controller, optimizer or new physics was used for that diagnosis.
