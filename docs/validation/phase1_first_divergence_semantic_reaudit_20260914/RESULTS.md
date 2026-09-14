# Phase1 first-divergence semantic re-audit closeout

## Decision

Top-level result: ORIGINAL_CLASSIFICATION_OVERTURNED_CONTROLLER_OR_TRANSPORT

The historical v2 report classified the candidate first divergence as SIMULATOR_DIVERGENCE. The component-aware offline review does not support that attribution. In all three pairs, the first supported difference is an explicit LowCmd field before bridge application. The existing v2 capture does not contain the exact controller-input/transport boundary, so controller versus input/transport remains intentionally unresolved.

## Scope and provenance

- Review branch: research/phase1-first-divergence-semantic-reaudit-20260914
- Review source head before derived changes: 32bb8b8388f3731a53c078a60689f56e7eb38ed7
- Parent evidence branch/worktree: research/phase1-frozen-handoff-first-divergence-20260914, parent head 6fe262a0e0dc88e145ac1a78dd6ca95f86bbc0a3
- Parent provenance: docs/validation/phase1_frozen_handoff_first_divergence_20260914/run_provenance.csv
- Raw captures were read from the parent worktree only; no raw binary is copied or committed.
- The three raw SHA-256 values and byte counts matched the parent provenance exactly:
  - L1: 6,240,068 bytes, f7da6a4970105537aa9868bb97e7768474068317e52b3e1dc92d0423ed83a75e
  - L2: 6,240,068 bytes, f0e779be179e6014c337adeeaa3c9a413b9d1642a0bb2f39e99bf65b8a6ec379
  - L3: 6,240,068 bytes, d00f454e2abb7f1365e81dc8616b669b76e090844162d3c82ef025c7f292d690
- Each capture has 2,500 records; provenance record_count, raw_bytes, and raw_sha256 all match.
- No simulator, controller, locomotion run, or new trajectory was started. No D4 or new instrumentation was executed.

## Stage 0: source audit

simulate/src/main.cc:728-730 configures mjSTATE_INTEGRATION and obtains the state size. Begin() at 798-812 calls mj_getState before the step and caches the pending time, contact metadata, bridge record, and data->ctrl. End() at 824-854 writes that pre-step state and cached control fields, while qacc[0] is read after the step.

The lockstep loop at main.cc:1526-1535 is Begin(), mj_step, ground truth, End(). The bridge lockstep path at unitree_sdk2_bridge.h:610-631 can apply the latest command under the simulation lock; ApplyLatestCommand() at 640-679 writes mj_data_->ctrl from the LowCmd-derived PD/FF command and publishes the bridge control record. State publication is separate at 681-793.

Therefore the full next mjSTATE_INTEGRATION record includes a control slice that can be changed by a bridge writer between End(i) and Begin(i+1). A full-state byte difference alone is not simulator-step evidence. The historical analyzer checked full state_raw before explicit causal fields (analyze_phase1_frozen_handoff_first_divergence.py:316-398) and labeled the next-record difference SIMULATOR_DIVERGENCE; that ordering is corrected here.

## Stage 1: state component proof

Method A was checked over all 2,500 records in each capture: state_raw[56:68] is byte-identical to that record's separately serialized actual_ctrl_raw, giving 2,500/2,500 identity for L1, L2, and L3.

Method B used the exact provenance model unitree_robots/go2/go2.xml and MuJoCo 3.3.6 without stepping. The mjSTATE_INTEGRATION layout is:

| component | scalar range |
|---|---:|
| time | [0, 1) |
| qpos | [1, 20) |
| qvel | [20, 38) |
| act | [38, 38), na=0 |
| warmstart | [38, 56) |
| ctrl | [56, 68) |
| qfrc_applied | [68, 86) |
| xfrc_applied | [86, 194) |

Thus state[56] is ctrl[0], not qpos, qvel, or another plant/solver state. The exact component ranges are recorded in state_component_map.csv.

## Stage 2: semantic pairwise result

| pair | earliest record/tick | field | value A | value B | delta B-A | state component | result |
|---|---|---|---:|---:|---:|---|---|
| L1-L2 | 2151 / 12302 | LowCmd.q[0] | 0.0056869215331971645 | 0.00568692060187459 | -9.313225746154785e-10 | ctrl[56:68] duplicate | ORIGINAL_CLASSIFICATION_OVERTURNED_CONTROLLER_OR_TRANSPORT |
| L1-L3 | 2151 / 12302 | LowCmd.q[0] | 0.0056869215331971645 | 0.00568692060187459 | -9.313225746154785e-10 | ctrl[56:68] duplicate | ORIGINAL_CLASSIFICATION_OVERTURNED_CONTROLLER_OR_TRANSPORT |
| L2-L3 | 2152 / 12304 | LowCmd.tau_ff[0] | -0.006096293218433857 | -0.006096275057643652 | 1.816079020500183e-08 | ctrl[56:68] duplicate | ORIGINAL_CLASSIFICATION_OVERTURNED_CONTROLLER_OR_TRANSPORT |

At each listed first difference, record/time, non-control integration state, and bridge sensor q/dq are equal. The explicit LowCmd differs first; bridge ctrl, actual ctrl, and the embedded state[56:68] then differ consistently. The preceding records are equal. The later qacc0_after difference is downstream of this already-supported upstream command difference and cannot establish a simulator-originated divergence.

## Acceptance and closeout

- Required analyzer: example/cpp/tools/analysis/analyze_phase1_frozen_handoff_semantic_reaudit.py
- Required CSV outputs: present under docs/validation/phase1_first_divergence_semantic_reaudit_20260914/
- Historical Results and historical CSV were not modified.
- Raw captures were not committed.
- The decision uses exactly one task-defined top-level label.
- A future immediate post-mj_step full-state capture would be the appropriate separate checkpoint if simulator attribution must be resolved; it was not run here and is outside this task.
