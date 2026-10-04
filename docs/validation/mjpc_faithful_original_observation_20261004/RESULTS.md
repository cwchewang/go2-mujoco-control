# Faithful original fixed-input observation — completed

Status: OBSERVATION_COMPLETE / PREFIX_WITHIN_1e-9 / NOT_EXACTLY_REPEATABLE.
[Task](../../research/TASK_MJPC_FAITHFUL_ORIGINAL_OBSERVATION_20261003.md).
Producer HEAD: 3b4e25bcf9d12a0704e6dc9ca4e4cf8277b343aa.
Execution receipt: px_1a104358d2f_3e24940cea, approved, bubblewrap, rc0.
No A/B rerun, canonical capture, fixed variant, additional optimizer smoke or push.

## Actual result
Two fresh original-only controller processes each consumed the eleven sealed A states, production named-joint encoder and explicit constructor-then-live reset. Only ticks0 and10 replanned. Independent audit verified22 wire strings,2 reset sequences,4 durable reservations/completed solves, empty stderr, model/library closure and unchanged A bytes.

| Quantity | Result |
|---|---:|
| Private optimizer calls | 4 |
| Private accounted integration upper bound | 10004 |
| Private reservation | 16384 |
| Canonical integration | 0 |
| Formal live scientific attempts | 0 |
| Unverified reservations | 0 |

Ticks0–9 q_des and cost match A and reference exactly as serialized numerical values.
At tick10 cost stays0.06179009604427559 and candidate8 is selected in all observations.

| Tick10 comparison | Max absolute q_des difference, rad |
|---|---:|
| Repeat1 versus A | 1.8034018722801193e-11 |
| Repeat2 versus A | 1.4180878693537124e-11 |
| Repeat1 versus reference | 2.9003144070421927e-11 |
| Repeat2 versus reference | 2.926214826004525e-11 |
| Repeat1 versus repeat2 | 8.549605468033405e-12 |

All costs match and all comparisons satisfy the unchanged1e-9 prefix tolerance. This does not reopen the retired A reproduction gate or imply3s/12s locomotion success.

## Earliest observed divergence and mechanism
External initial state, all eleven named input packets, binary, model, library, reset contract, planner parameters and pre-second-solve policy/previous-policy summaries match.

After the first solve, the reported worker warmstart multiset matches, but its assignment to worker slots differs. This is the earliest logged hidden-history difference. The second FD pass already has different incoming warmstart hashes at knot1, before the duplicate t34 jobs. The source SetState copies only qpos/qvel/act; FD work uses worker-specific mjData without normalizing qacc_warmstart.

At tick10 t34 Jacobian hashes are182fb14e89fa8770 versusf60f593f0beb6e41. Duplicate t34 FD intervals overlap by655349ns and480128ns; source shows both jobs write the same A/B/C/D blocks without a per-knot synchronization boundary. Their incoming warmstart hashes differ. Selected policy hashes differ, although cost/candidate ID remain equal. Logged selected qpos/qvel numerical values remain equal; nominal action differences reach8.246873464071852e-11rad over the prediction horizon. A hash difference alone is not evidence that every trajectory field differs.

High confidence: the repaired observer closes the previous coarse prefix mismatch, and remaining tiny repeat differences arise inside private optimization before canonical feedback.
Strong mechanism evidence: worker-history dependence exists and duplicate t34 writes overlap.
Unresolved causal split: this experiment does not isolate worker-history versus duplicate-write contributions, nor instrument the historical A/reference binaries. Their original tick10 target drift2.6831203925326008e-11 remains consistent with this scale of optimization variability, but its unique trigger is unproven. Earlier closed-trace evidence still places physical state divergence at tick11 and later support/contact/saturation differences after feedback amplification.

Reset and joint-order repairs were applied together; their separate numerical effects were not ablated. Two repeats show an observed difference, not its frequency. Native OS PIDs were not logged; fresh processes are verified by bound launch/cleanup code, separate ready/reset records and restarted FD call indexes.

## Completed engineering
8915b0d and all old sealed evidence are preserved. The prior retired-A guard and production reset/named-order repairs remain. This task adds a source-bound four-call original-only observer with a sealed binary/model/ELF-loader/library closure, strict per-call budgets and no-retry output ownership. Independent execution review found and fixed loader-launched stale-process detection and malformed-response partial accounting.

Applicable v4 qualification bound the actual3b4e25b source and unchanged original instrumented binary92f7056463ae1f12cceea09b377712647716682254d3b911ce11d0e52bbe7f4b. It passed43 Python contracts,3 native zero-integration checks, current quality and diff checks, spending zero optimizer calls. Both independent pre-execution reviews passed, and independent closeout is VERIFIED. Failed v1 qualification and earlier review BLOCK are preserved through raw evidence and durable review/dispatch receipts.

Two pre-execution TaskSpecs incorrectly classified private calls as a formal scientific attempt. The route rejected scientific mode and nonzero scientific attempts; both commands never started. Source-backed independent classification confirmed the frozen operation is zero formal attempts with four separate private reservations. The identical command/capability/host/privilege was accepted after correcting only that metadata. Raw rejection receipts remain sealed; no permission, route or safety change was made.

## Evidence and next boundary
Raw root:
`/home/che/dev/go2-workspace/faithful-original-observation/_runs/mjpc_faithful_original_observation_20261003`
Manifest:8b3e6fc4c36a7a188715b8221d7bf4d9347683f1637355c24e4a9fcefe8e79d9.
Qualification manifest:bf2718a0e525c27760ead6f246a1ac619f3414535bee55db9cfea6b9c098e407.
Historical A raw:9a4f2711f558b80ac58c803406971f43be7c44f4c5e64f7a50c728e2a7440e55.

[analysis.json](analysis.json), [stdlib recomputation](analyze.py), [science assessment](science-review.json), [independent execution audit](execution-review.json), [provenance](provenance.csv), [dispatch receipt](dispatch.json).
The analyzer reads sealed bytes and reconstructs22 packets/counters; it never imports MuJoCo or advances dynamics.

The four-call budget is closed. No further private or canonical run was started. The smallest next causal discriminator must vary worker warmstart initialization separately from unique t34 indexing while holding external states, native parameters and instrumentation constant; it requires its own frozen task and private budget. Additional historical replay cannot recover absent historical worker state. A remains CLOSED_NO_RETRY, B NOT_RUN_REPRODUCTION_GATE_FAILED, R4 repeat gate failed,12s capture absent.
