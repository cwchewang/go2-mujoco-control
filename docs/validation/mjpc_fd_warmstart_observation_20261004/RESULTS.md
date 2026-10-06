# Incoming FD warmstart contrast — completed and independently verified

[Task](../../research/TASK_MJPC_FD_WARMSTART_OBSERVATION_20261004.md). Producer: 5b13c02d5460fee49ae80c5a95a0426cd341c88a. Execution: px_1a1047e1251_d29d3a031c, approved bubblewrap, return code 0.

The same archived fixed controller and sealed shim were used in both arms. The sole mode-dependent intervention retained or zeroed the 18 incoming qacc_warmstart entries immediately before finite differences. Unique indices 0–35, model, workers, planner, reset, encoder and rollout code were unchanged.

The shared task queue assigns jobs to waking workers. Rollouts and finite differences both use data[WorkerId()]. State restoration copies qpos/qvel/act without clearing qacc_warmstart, allowing preceding rollout/job history to supply the next FD seed. The shim delegates exactly once to pinned MuJoCo and records effective seeds separately from the earlier native trace.

| Result | Retain | Zero |
|---|---:|---:|
| New private optimizer calls | 4 | 4 |
| Tick-10 repeat target maximum difference | 2.052338680946786e-11 | 0 |
| Repeat cost difference | 0 | 0 |
| Repeat t34 Jacobian/policy hashes | Differ at tick 10 | Match at both solves |
| Selected nominal action repeat difference | 3.905875622933763e-11 | 0 |

Both arms match their own repeat exactly through tick 9. Zero repeats also match at tick 10 in serialized targets, costs, qpos, qvel, actions and recorded t34/policy hashes. All 144 zero-arm FD entries have effective all-zero seed hash ec32669a74fcae65; all 144 retain-arm entries preserve their incoming hashes. Four ready/reset streams and 44 production wire inputs verify.

**Causal finding:** clearing FD-entry warmstart removed the observed repeat drift in this matched diagnostic, supporting a causal role under these inputs. The prior unique-index experiment showed duplicate t34 writes were unnecessary for the observed drift. Two repeats per arm do not establish a rate, sole explanation or universal sufficiency. Clearing can change subsequent worker/rollout history and scheduling; those downstream effects remain part of this intervention.

**Unchanged 1e-9 threshold:** all within-arm target differences remain below it. Across retain/zero arms, target differences exceed it at ticks 0–3, peaking at 4.495396499493154e-9. Tick-10 difference is 9.973715187072685e-10 and cost difference is 6.823951126389005e-12. Exact zero-arm repeatability does not establish trajectory neutrality. This result does not approve a production replacement or change the historical reproduction gate.

**Closed-loop gap:** historical target divergence at tick 10 precedes state divergence at tick 11 and later contact/saturation changes, consistent with feedback amplification. This fixed-input experiment has zero canonical feedback integration and different instrumentation from historical A. It cannot identify A's unique trigger, establish that clearing removes the 886/1287 stop difference or demonstrate locomotion. Rollout-entry warmstarts were not directly controlled.

Qualification passed 51 existing and two new Python contracts, three native checks without integration, fake forwarding/state-preservation contracts, actual ready/reset checks without FD in both modes, and quality checks. The sealed compiler/header/source and loaded-library closure were verified. An independent execution pre-review found terminal RESULT status overwritten by preflight expansion. That recording defect was fixed before any optimizer call; new exact-head v2 reviews passed. The prior BLOCK and qualification evidence remain retained. No controller rebuild or physics smoke was needed.

Independent science and execution closeouts verify 39 capture members, 76 qualification members, 288 FD records and all numeric results. The execution audit used a complete hash/call/interval-constrained correspondence; overlapping worker intervals alone cannot uniquely identify associations. One earlier read-only parser assumption was corrected without rerunning or modifying evidence.

Eight new calls used 19616 accounted private upper steps within 32768 reservations. Canonical integration and formal live scientific attempts were both zero; no unverified reservations or stderr. **Budget CLOSED.** Old A/B and prior budgets remain closed. R4 failed and no 12-second capture exists. Stage 3 remains ACTIVE / OPEN. No push, physical robot or permission change.

[Analysis](analysis.json), [standard-library recomputation](analyze.py), [pre-reviews](pre-reviews.json), [actual receipt](dispatch.json), [science closeout](science-review.json), [execution closeout](execution-review.json), [provenance](provenance.csv).

Raw evidence: /home/che/dev/go2-workspace/fd-warmstart-observation/_runs/mjpc_fd_warmstart_observation_20261004
Raw manifest SHA-256: 43d68bb104338cd322fb1ae1742b84b374f920c6d809fd17989dedde42118844
Qualification manifest SHA-256: c3c755d4abd1aba5250348d6238f9886e10acb4e50055a2f5c4ee2b3cb15739c
