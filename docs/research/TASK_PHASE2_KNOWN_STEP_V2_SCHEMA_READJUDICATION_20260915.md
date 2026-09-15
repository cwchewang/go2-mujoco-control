# Phase2 offline checkpoint: V2 CSV schema readjudication

Date: 2026-09-15
Prepared branch: `research/phase2-known-step-v2-schema-readjudication-20260915`
Exact parent closeout: `68c3c2ecd6a706c0949eb4be793b741ed8889f1e`
Frozen C runtime HEAD recorded by parent: `b281993b81b3bf6a083eccfb5805789026913837`
Frozen V2 scientific implementation lineage: `a01a74efe8abe70224e1da42d6ff65d6c7dbf172` / `be1e9acca1c6650be7d500e1e3fb63dcd5594826`

Read `docs/research/PHASE1_AGENT_CONTRACT.md`, `docs/research/TASK_PHASE2_KNOWN_STEP_EDGE_AWARE_V2_20260915.md`, `docs/research/TASK_PHASE2_KNOWN_STEP_EDGE_AWARE_V2_PROTOCOL_REPAIR_20260915.md`, and both V2 closeouts before doing anything.

This checkpoint is **strictly offline**. It does not authorize a simulator, controller, runner, GUI replay, DDS process, or any new live experiment.

## 1. Question

Can the already captured C/domain-230 V2 run be read unambiguously despite the `780 header / 776 data` CSV width mismatch, and if so what scientific classification does that frozen run support under the original V2 criteria?

The parent closeout correctly classified the capture as `PROTOCOL_FAILURE` because the analyzer refused to consume a malformed CSV. Subsequent source review identified a specific candidate schema defect in `TrotExperiment::WriteCsvHeader`: for each of the four legs, the V2 header text around `_s_exit` appears to emit two consecutive delimiters, while `LogSample` emits one normal sequence of values. If that is exactly what happened, the raw data rows are not missing measurements; the header contains four empty field names.

This checkpoint must prove or reject that hypothesis from immutable raw bytes and runtime source before interpreting any C values.

## 2. Immutable inputs

Use the existing raw C capture only:

`/home/che/dev/go2-workspace/phase2-known-step-edge-aware-v2-protocol-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_edge_aware_v2_protocol_repair_20260915/C`

Frozen comparison captures remain read-only:

A:
`/home/che/dev/go2-workspace/phase2-known-step-wallclock-repair-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`

V1 B:
`/home/che/dev/go2-workspace/phase2-known-step-b-only-20260915/example/cpp/experiments/_runs/phase2_known_step_5cm_b_only_20260915/B`

Use the hashes/provenance already committed by the parent closeout to prove these inputs have not changed.

Do not edit, rewrite, normalize, truncate, or replace the raw C `data.csv`, logs, metadata, lockstep files, or ground-truth files. Any repaired representation must be derived outside the raw run directory and its derivation must be machine-auditable.

## 3. First prove the exact schema defect

Before any scientific analysis, inspect the raw C CSV with `csv.reader` or an equivalently exact parser and inspect the runtime source at the recorded C HEAD.

Required findings to proceed with recovery:

1. raw header width is exactly 780;
2. every one of the 5005 data rows has exactly 776 fields;
3. the raw header contains exactly four empty field-name tokens;
4. each empty token occurs at the V2 per-leg transition immediately after `known_step_v2_<leg>_s_exit` and immediately before `known_step_v2_<leg>_command_world_x_m`, for legs `fr`, `fl`, `rr`, `rl`;
5. no other header field is empty or duplicated in a way that makes mapping ambiguous;
6. runtime source proves the header contains the double-delimiter construction at exactly those four transitions;
7. runtime `LogSample` source proves there is no corresponding omitted data value: it emits `s`, `s_entry`, `s_exit`, then command x/z/vx/vz, actual x/z, and scheduled stance/swing in a single contiguous sequence for every leg.

If any of these seven conditions fail, classify this checkpoint `SCHEMA_RECOVERY_AMBIGUOUS`, record why, and stop without scientific reclassification.

## 4. Deterministic header recovery

If Section 3 passes, create a **derived in-memory header** by deleting only the four empty header tokens. Do not insert, delete, reorder, infer, or edit any data-row value.

The repaired header must have:

- exactly 776 names;
- no empty names;
- no duplicate names;
- exact one-to-one width equality with every raw data row.

Write a machine-readable `schema_repair_map.csv` containing, at minimum:

- original raw header index;
- original token;
- action (`KEEP` or `DROP_EMPTY_HEADER_TOKEN`);
- repaired header index where applicable;
- preceding and following canonical field names.

Also record raw and derived-header SHA-256 values. A full duplicate repaired `data.csv` is not required; prefer reading raw rows under the repaired header in memory. If a derived CSV is emitted for debugging, it must live only under the validation output directory, never under the raw run directory, and its provenance must be recorded.

## 5. Recovery validation before scientific use

Before running the V2 scientific analyzer, prove the repaired mapping is semantically correct using source-derived invariants. At minimum check across the recovered C rows:

- `known_step_v2_feature_enabled` has plausible boolean values and is enabled during active V2 locomotion;
- each leg's `planning_failure_code` parses as the known integer enum and `planning_failure_reason` is one of the source-defined strings;
- `x_entry_m` is approximately 0.777 when a V2 plan is populated;
- `x_exit_m` is approximately 0.823;
- `x_land_min_m` is approximately 0.850;
- scheduled stance/swing fields are boolean-like;
- finite numeric parsing succeeds for command x/z/vx/vz and actual x/z where populated;
- there is no one-column drift when crossing from one leg block to the next or from the V2 block into the following D4 diagnostics block.

Record these checks in `schema_recovery_validation.csv`.

Any mapping inconsistency -> `SCHEMA_RECOVERY_AMBIGUOUS` and stop.

## 6. Preserve the observed runtime statuses correctly

The parent C metadata recorded:

- controller_status = 0;
- ground_truth_status = 0;
- dynamics_status = 0;
- quality_status = 0;
- analysis_status = 1;
- safety_status = 1;
- completion_status = 1.

Do not rewrite these values.

The original `analysis_status=1` came from the CSV width check and is expected to be explained by the recoverable header-only defect if Sections 3-5 pass.

`safety_status=1` is independent evidence from `controller.log` and must not be erased or reinterpreted as a CSV artifact. Identify the exact controller-log marker that caused it, with state-time context from recovered telemetry where possible. `completion_status=1` must likewise be reported as an experimental outcome, not silently normalized.

For scientific reclassification, follow the **original V2 task's classification logic and traversal criteria**. A hard-safety event prevents successful traversal but does not by itself become a new `PROTOCOL_FAILURE` once the evidence schema is deterministically recovered. A true lockstep/paired-state/provenance/run-order failure still takes precedence as protocol failure.

## 7. Re-run the frozen V2 analysis offline

Create a dedicated analyzer, preferably:

`example/cpp/tools/analysis/analyze_phase2_known_step_v2_schema_readjudication.py`

It may reuse/import logic from the existing V2 analyzer, but the raw C input must be parsed with the proven repaired header mapping rather than by mutating the raw file.

Recompute all originally required V2 evidence:

- protocol/lockstep/paired HighState/provenance;
- exact A/C preactivation equality through the row strictly before first V2 crossing latch;
- V2 planning/isolation gates;
- per-front-leg edge-envelope command/actual tracking;
- C1 corridor and analytic-velocity invariants;
- touchdown and raised-platform contact evidence;
- body/contact/solver chronology;
- max base x and traversal outcome;
- exact hard-safety marker/timing;
- original full-traversal criteria.

Use the original thresholds and labels. Do not tune, weaken, reinterpret, or invent criteria after seeing the recovered data.

The final scientific label after successful schema recovery must be one of the original V2 labels:

- `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`
- `PLANNING_GEOMETRY_FAILED`
- `SUPPORTED_ENABLES_TRAVERSAL_V2`
- `TRACKING_LIMITED`
- `FRONT_PAIR_ESTABLISHED_BUT_COORDINATION_FAILED`
- `OTHER_CONTROL_LIMIT_IDENTIFIED`
- `INSUFFICIENT_EVIDENCE`

`PROTOCOL_FAILURE` remains allowed only if an actual protocol/provenance/lockstep/paired-state failure remains after the deterministic header-only repair. `SCHEMA_RECOVERY_AMBIGUOUS` is specific to this readjudication if the mapping cannot be proven unique.

## 8. Fix the logger defect for future runs, but do not run live

After the offline mapping is proven, make the minimal non-control source repair so future CSVs do not reproduce the malformed header:

- remove the extra delimiter at the four per-leg `_s_exit -> command_world_x_m` transitions;
- do not change any telemetry value, ordering, V2 planner/control behavior, or scientific parameter.

Add a regression test or deterministic no-DDS check that would fail if the CSV header/sample width diverges or if an empty V2 header token is reintroduced. The test must run without launching the simulator/controller.

Build/test only as needed for this logger/tooling fix. No live run is authorized.

## 9. Outputs

Write results under:

`docs/validation/phase2_known_step_v2_schema_readjudication_20260915/`

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

Clearly separate:

1. raw-capture facts;
2. deterministic schema-recovery facts;
3. scientific interpretation after recovery;
4. future logger source fix/tests.

## 10. Stop

Commit and push the offline closeout, then stop.

Do not launch MuJoCo, the controller, the runner, DDS, replay, or any new terrain experiment. Do not rerun C. Do not tune V2. Do not change speed, gait, WBC/MPC/ID, planner geometry, body references, safety limits, scene, or thresholds.