# Phase2 offline checkpoint: V2 schema recovery correction and scientific readjudication

Date: 2026-09-15
Prepared branch: `research/phase2-known-step-v2-schema-recovery-correction-20260915`
Exact parent closeout: `4986a6b5c4680e0fe8e1337fef65005440d26529`
Frozen C runtime HEAD: `b281993b81b3bf6a083eccfb5805789026913837`
Frozen V2 scientific implementation lineage: `a01a74efe8abe70224e1da42d6ff65d6c7dbf172` / `be1e9acca1c6650be7d500e1e3fb63dcd5594826`

Read `docs/research/PHASE1_AGENT_CONTRACT.md`, the original V2 task, the V2 protocol-repair task/closeout, the prior schema-readjudication task, and its closeout before doing anything. This checkpoint is strictly offline. No simulator, controller, runner, DDS process, GUI replay, or new live experiment is authorized.

## 1. Why this task supersedes one narrow prior gate

The prior schema-readjudication task preregistered a specific header-defect hypothesis: it required the four excess header tokens to be empty strings. That literal hypothesis was wrong.

The completed parent audit established instead, from immutable raw bytes and runtime source, all of the following before looking at any V2 scientific outcome:

- raw C header width = 780;
- all 5005 C data rows have width 776;
- the four excess header tokens are exactly the literal string `known_step_v2_` at raw header indices `[211,264,317,370]`;
- they occur once per FR/FL/RR/RL V2 block at the same `_s_exit -> command_world_x_m` construction boundary;
- runtime `WriteCsvHeader` source contains the duplicated `known_step_v2_` prefix construction;
- runtime `LogSample` emits the corresponding values contiguously with no four omitted sample values;
- deleting exactly those four header-only tokens gives a unique 776-name candidate mapping;
- every independent source-derived semantic recovery check passed, including V2 bool fields, planning enum/reason fields, x_entry=0.777, x_exit=0.823, x_land_min=0.850, stance/swing booleans, finite command/actual values, and all four leg-block boundaries into the following D4 fields;
- the logger bug has since been minimally fixed and the no-live CSV schema regression test passes.

The prior checkpoint therefore correctly stopped under its literal task, but its `SCHEMA_RECOVERY_AMBIGUOUS` label is procedural rather than evidence that the mapping remains scientifically ambiguous.

This task supersedes only the incorrect requirement that the four extra tokens must be empty strings. It does not change any V2 scientific threshold, classification rule, raw value, run status, geometry, controller setting, or causal criterion.

## 2. Immutable inputs

Read only the existing captures:

C:
`/home/che/dev/go2-workspace/phase2-known-step-edge-aware-v2-protocol-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_edge_aware_v2_protocol_repair_20260915/C`

A:
`/home/che/dev/go2-workspace/phase2-known-step-wallclock-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`

V1 B:
`/home/che/dev/go2-workspace/phase2-known-step-b-only-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_b_only_20260915/B`

Reuse and verify parent provenance/hashes. Do not edit any raw file. Any repaired representation is derived-only and must live under validation output or in memory.

## 3. Authoritative deterministic header repair

The only authorized C header transformation is:

- parse the raw header exactly;
- assert width 780;
- assert every data row width 776;
- assert raw header indices `[211,264,317,370]` are each exactly `known_step_v2_`;
- assert source/neighbor context identifies these as the four duplicated standalone V2 prefix tokens at the per-leg `_s_exit -> command_world_x_m` transition;
- delete exactly those four header tokens and no others;
- do not insert/delete/reorder/change any data-row value.

The derived header must have exactly 776 unique nonempty canonical names and one-to-one width equality with all 5005 raw C data rows.

If any of those facts do not reproduce exactly, classify `SCHEMA_RECOVERY_AMBIGUOUS` and stop.

Reuse or regenerate `schema_repair_map.csv`, but mark the four actions as a header-only duplicated-prefix removal, not an empty-token deletion.

## 4. Recovery validation

Before scientific use, independently reproduce every semantic gate already passed by the parent audit:

- V2 feature boolean-like and enabled during active V2 locomotion;
- planning failure codes in the runtime enum;
- planning failure reasons in the runtime strings;
- x_entry populated values = 0.777 within numeric tolerance;
- x_exit = 0.823;
- x_land_min = 0.850;
- scheduled stance/swing boolean-like;
- all command x/z/vx/vz and actual x/z parse as finite where populated;
- no column drift across FR->FL->RR->RL V2 blocks or from RL into the first D4 field;
- derived mapping is unique.

Also compare the derived canonical header to the already-fixed logger's intended canonical ordering. This comparison is a structural validation only; do not replace raw values with a new run or regenerated telemetry.

Any inconsistency -> `SCHEMA_RECOVERY_AMBIGUOUS` and stop.

## 5. Runtime status handling

Preserve raw metadata exactly:

- controller_status=0
- ground_truth_status=0
- dynamics_status=0
- quality_status=0
- analysis_status=1
- safety_status=1
- completion_status=1

Explain `analysis_status=1` as the original logger-schema failure after the deterministic header repair succeeds. Do not erase it from provenance.

`safety_status=1` and `completion_status=1` remain genuine experimental outcomes. Identify the exact first hard-posture / hard-safety log marker and align it to recovered state-time telemetry. Do not downgrade or normalize them.

A hard-safety stop means traversal cannot be classified successful, but it is not itself a protocol failure once the evidence mapping is deterministically recovered and lockstep/paired/provenance gates pass.

## 6. Scientific analysis: use the original V2 rules unchanged

After Sections 3-5 pass, run the original V2 scientific analysis against the recovered in-memory C mapping. Reuse/import the existing V2 analysis code where sensible, but make the recovery step explicit and auditable.

Recompute, at minimum:

1. protocol, lockstep, paired HighState, frozen provenance;
2. exact A/C preactivation equality through the row strictly before first V2 crossing latch;
3. V2 feature/isolation and planning-valid gates;
4. latched crossing timing relative to first geometric risk;
5. C1 corridor invariants and analytic velocity continuity;
6. per-front-leg command vs actual x/z at edge-envelope entry;
7. actual-below-clearance / contact-blockage evidence;
8. touchdown positions and raised-platform physical contact duration;
9. body/contact/solver chronology;
10. max base x and hard-safety timing;
11. original full traversal criteria.

Do not modify any threshold or classification precedence from `TASK_PHASE2_KNOWN_STEP_EDGE_AWARE_V2_20260915.md`.

The scientific classification, after successful deterministic schema recovery, must be exactly one of the original V2 labels:

- `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`
- `PLANNING_GEOMETRY_FAILED`
- `SUPPORTED_ENABLES_TRAVERSAL_V2`
- `TRACKING_LIMITED`
- `FRONT_PAIR_ESTABLISHED_BUT_COORDINATION_FAILED`
- `OTHER_CONTROL_LIMIT_IDENTIFIED`
- `INSUFFICIENT_EVIDENCE`

`PROTOCOL_FAILURE` remains allowed only for a real remaining run-order/provenance/lockstep/paired-state/evidence failure other than the now-deterministically-recovered duplicated-prefix header defect.

`SCHEMA_RECOVERY_AMBIGUOUS` is allowed only if Sections 3 or 4 fail.

## 7. Required outputs

Write a new validation directory:

`docs/validation/phase2_known_step_v2_schema_recovery_correction_20260915/`

At minimum:

- `RESULTS.md`
- `analysis.json`
- `schema_repair_map.csv`
- `schema_recovery_validation.csv`
- `preactivation_exact.csv`
- `planning_isolation.csv`
- `front_crossing_summary.csv`
- `edge_tracking_timeline.csv`
- `touchdown_summary.csv`
- `body_contact_chronology.csv`
- `protocol_gates.csv`
- `provenance.csv`

Clearly distinguish raw statuses, derived schema repair, and scientific result.

Do not overwrite the prior schema-readjudication closeout or the raw C directory.

## 8. Source changes

The parent already fixed the logger duplicated-prefix defect and added a no-live CSV schema regression test. Preserve those changes. No controller/planner/runtime scientific change is authorized in this task.

Only offline analysis/result changes required for this superseding readjudication are allowed. If another logger/tooling defect is discovered, record it and stop rather than adding a live run or modifying scientific controller behavior.

## 9. Stop

Commit and push the offline closeout, then stop.

No live C rerun. No new DDS domain. No V2 tuning. No speed/gait/WBC/MPC/ID/planner/scene/safety change.