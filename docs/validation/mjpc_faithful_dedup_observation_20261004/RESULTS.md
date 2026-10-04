# Unique-index-only diagnostic — completed

Status: OBSERVATION_COMPLETE; science PASS; execution VERIFIED.
[Task](../../research/TASK_MJPC_FAITHFUL_DEDUP_OBSERVATION_20261004.md).
Producer: fd9a9205a8bdd5fe3a9ff2423fa7e42a968ebfb8.
Execution: px_1a104619055_698d10e5af, approved bubblewrap, rc0.

Only FD indices change from 0..34,34,35 to 0..35; warmstart behavior is unchanged. The archived matched fixed binary is reused. Static reconstruction verifies the sole generated-source delta and common compilation/instrumentation provenance. All45 model/library bytes match the sealed original control. Current generator formatting differs but renders the identical archived bytes. Two fresh fixed processes use the same eleven A inputs, production reset/encoder and replans0/10 as the previous sealed original pair.

| Result | Value |
|---|---:|
| New private calls | 4 |
| Accounted upper / reserved steps | 9808 / 16384 |
| Canonical / formal live attempts | 0 / 0 |
| t34 tasks per call | 1, verified in all4 calls |
| Fixed-repeat tick10 q_des difference | 1.3625101047409771e-11 |
| Fixed-repeat cost difference | 0 |
| Maximum fixed/original q_des difference | 2.549982447419552e-11 |

Ticks0–9 targets/costs are exactly equal across fixed repeats. All comparisons satisfy unchanged1e-9. Prior8.549605468033405e-12 is0.855% of that threshold, about117 times smaller; unequal numerical values did not constitute a threshold failure.

**Mechanism result:** numerical drift survives without duplicate simultaneous t34 writes. Those writes are therefore unnecessary for this observed drift and cannot be its sole source. This does not exclude their contribution to original/historical drift.

First-solve post-worker warmstart assignments and multisets differ. Second-solve incoming seeds already differ at knot0, hashes69078ca7d2004bce/f023c14c1fcf18b1, before unique t34. t34 Jacobian hashes410d9d024fd2cd07/8bb844d6231cf282 and selected policy hashes differ; cost/candidate8 match. Selected serialized qpos/qvel match; nominal actions differ up to4.720956958692568e-11.

Retained worker history is supported as a remaining mechanism to investigate. Warmstart alone has not been proven causal: removing one job changes scheduling/history downstream, hidden worker state is not held equal across variants, and the original control is historical. Two repeats do not estimate frequency or identify historical A's unique trigger. No locomotion claim.

Applicable qualification passed51 Python checks,3 native zero-integration checks and quality withzero optimizer smoke. Both exact-head pre-execution reviews passed; independent closeout verifies21 raw members,22 mapped inputs,4 ledgers/counters, resets, libraries, empty stderr and no active controllers. Qualificationv1 failed before solver on an unresolved historical MuJoCo library path and is retained. v2 resolved libraries from the previously sealed original closure and passed; a later v1-summary-path error was fixed by reading/prechecking passedv2, without requalification.

[Analysis](analysis.json), [no-simulator recomputation](analyze.py), [science](science-review.json), [execution audit](execution-review.json), [pre-reviews](pre-reviews.json), [receipt](dispatch.json), [provenance](provenance.csv).

Raw: /home/che/dev/go2-workspace/faithful-dedup-observation/_runs/mjpc_faithful_dedup_observation_20261004.
Manifest:2e5fa41e23f9334037c59aeffe0fc064473286bb68af2d81a1006a9f546aecb2.
Qualification:30bd091bfa733021d205f118fc366c4746dc3da30a7cb8a74146b7f3577e5980.
Original control:8b3e6fc4c36a7a188715b8221d7bf4d9347683f1637355c24e4a9fcefe8e79d9.

New budget CLOSED; no extra calls or retries. Next orthogonal discriminator would vary warmstart initialization alone under its own frozen budget. daef3c0,8915b0d, all previous evidence and dirty floorRESULTS are preserved. A/B remain closed; R4 failed/no12s unchanged. No push, real-robot operation or permission changes. Stage3 ACTIVE/OPEN.
