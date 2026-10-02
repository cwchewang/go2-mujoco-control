# Independent RL friction execution preparation

Status: IMPLEMENTED / NOT_RUN. The scientific protocol remains frozen at
`d10719424809db2037a01f755786b4f93c20ad6cfe2db1455e847ef0f57da89d`.
The [task](../../research/TASK_RL_FRICTION_REFERENCE_V1_20261002.md) owns the
two new RL repeats,12000-step limit,6s mu0.8-to0.3 switch, paired references,
original safety thresholds and no retry. Old17 NOT_RUN arms remain closed.

The actual [runner](../../../tools/substrate/rl_friction_campaign.py) exposes
prepare, explicit capture and independent verify. Capture directly uses the
existing shared episode, raw writer, friction hook, exposure/prefix verifier,
primary replay and STOP engine. The sole shared-runtime change is an optional
identity-check callback, preserving the old default. The RL-only callback
validates complete qualification and checkpoint without a native process.

Valid reviewed/user-bound START reserves the independent campaign ledger
before fresh preflight. Preflight failure seals a zero-arm EXECUTION_EVIDENCE_STOP
and permanently prevents retry. Otherwise the uninterrupted shared lock covers
preflight and both arms. All arm claims bind paired baseline SHA and adopted
eligibility; safety/execution/evidence failures stop the whole new campaign.
The independently computed auxiliary artifact is separate from primary analysis.
Incomplete/safety windows return null metrics without treating a nonfinite
terminal safety state as an auxiliary-analysis execution fault.

Targeted tests:25 PASS in4.187s under a canonical-integration guard.
The real capture entry uses FakePlant/FakeController only. It covers real claims,
two fresh instances, one runtime setup, all six safety stops, retained horizon
performance failure, exposure stop, boot and preflight failure, inherited/wrong
START rejection, no third arm/no replacement, external-ledger tamper, and
the actual new preflight entry with a real child/inherited lock.
Native-basis checks reject unrelated source/native/environment changes,
missing increment files or failed historical checks. These synthetic reviews
exist only in temporary test fixtures and authorize no actual capture.

The [task-specific qualifier](../../../tools/substrate/qualify_rl_friction.py)
creates a new full-current-input receipt validated by the unmodified global
qualification validator. It reruns Python substrate/preflight/tooling/quality/
diff checks. Three native configure/build/CTest logs are copied exactly from
the pinned sealed b1ac receipt, with their original producer and explicit reuse
metadata. All environment, build/compiler/link/binary/model and untouched
tracked inputs must match the sealed base; only seven named reviewed increment
files may differ. No new native optimizer admission is run or claimed.
Historical native private physics remains historical; new canonical/private
physics and scientific attempts remain0.

Qualification and current exact-head prepared references will be sealed in the
single final review packet after the clean implementation commit. Actual
science/execution approvals and bound START are still required before physics.

## Complete current-input qualification: PRECHECK PASS

Implementation/qualification producer HEAD:
`cb2de37753e316b8f97824431edce39254510507`.
New qualification:
`_runs/rl_friction_reference_exec_prep_20261002/qualification_20261002T122315376115Z`.
Manifest SHA256:
`d083d5f5a9803935da3d3a65b92ee5b27c77cec23c30b9c067025ab220b43d4b`.
Full input fingerprint:
`fd0b4ef2204cab7f8da24cc52af5388ab2e7df435163f84d265708cb66e695e1`.

The new receipt passed ordinary `qualification.validate`; no validator
relaxation or old full-input receipt substitution occurred. Fresh checks passed:
221 substrate tests in40.481s,36 preflight tests in0.807s and33 tooling tests
in0.397s, plus quality and diff checks. These are290 freshly run Python tests.
The three native operation logs retain their original b1ac producer and explicit
reuse metadata. The [native basis proof](native-basis-proof.json) verifies all
untouched model/build/binary/compiler/link/runtime inputs; the seven named
increment files are covered by the fresh current-fingerprint checks.
The [qualification reference](qualification-reference.json) and
[check receipt](checks.json) preserve this distinction.

Preparation must bind the exact final clean review HEAD. Its current reference,
full qualification, frozen protocol and source diff will live together in the
single `_runs/rl_friction_reference_exec_prep_20261002/full_review_packet_*`
bundle. This report's producer qualification remains cb2de37 when subsequent
prose-only commits reuse its identical complete fingerprint; it is never relabelled.
The final bundle is the handoff for the parent to dispatch incremental exact-head
science/execution review. Actual reviewer approval records are absent, and
scientific attempts/physics remain0. No live fresh preflight or capture has run.

Protocol/budget, old capture66630a6c..., old external ledger and its17 NOT_RUN
entries remain unchanged. Gate0 remains incomplete. The parallel MJPC diagnosis
remains the earlier [sealed read-only attachment](../rl_friction_reference_v1_prep_20261002/mjpc-readonly-diagnostic.md),
with no private predicted trajectories available and no causal failure claim.
