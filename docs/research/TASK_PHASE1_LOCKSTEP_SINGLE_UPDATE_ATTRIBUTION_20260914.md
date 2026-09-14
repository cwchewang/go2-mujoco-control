# Phase1 lockstep single-update attribution — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first and obey it. Complete exactly one checkpoint, push it, then stop.

## Context

The prior checkpoint `640124d5bdf6cb26e2ecda705ec55fa4c917b825` established that simulator-side lockstep is mostly correct: all three L1/L2/L3 runs had exact 2 ms simulator tick spacing, zero protocol violations, matching ack state ticks, `kAckMatched` exchange triggers, and no fail-closed marker. The only protocol gate that failed was `one_command_update_per_state_tick`:

- L1: delta counts `1:41420, 2:1054, 3:1`
- L2: `1:41904, 2:774, 3:8`
- L3: `1:41417, 2:1058`

Do not test D4. Do not modify gait/WBC/PD/controller math. Do not tune thresholds.

## Research question

Why does the controller publish more than one LowCmd for some frozen physics ticks despite the lockstep writer gate?

The task is attribution only. Do not repair the behavior in this checkpoint unless the root cause can be proven entirely offline with no runtime ambiguity; even then, stop with the proposed minimal fix rather than executing it.

## Hypotheses to distinguish

H1. Extra LowCmd writes occur only before the lockstep writer gate is engaged / during lifecycle handoff.

H2. Extra writes occur after the gate is engaged because the writer loop can consume or publish more than once for the same state tick.

H3. A second LowCmd publication path exists outside the normal `LowCmdWrite -> PublishLowCmdWithCrc` path.

H4. The simulator trace's command-arrival accounting is double-counting/reclassifying arrivals rather than the controller actually publishing twice.

Do not assume any hypothesis in advance.

## Stage 1 — static source audit

Trace every production publication path for `GO2_TROT_TOPIC_LOWCMD` and every call path to `LowCmdWrite`, `PublishLowCmdWithCrc`, and `lowcmd_publisher_->Write` on the Phase1 trot path.

Document:

- all publisher construction sites for the trot LowCmd topic;
- all calls to `LowCmdWrite`;
- the exact condition that switches the writer from wall-clock/free-running mode to `lockstep_writer_gate_` mode;
- where `lockstep_epoch_valid_`, `lockstep_epoch_state_seq_`, `last_consumed_state_tick_`, and `lockstep_cmd_seq_` are written/read;
- whether these fields are atomic or otherwise synchronized;
- whether duplicate LowState republishes can cause duplicate pending ticks after gate engagement;
- how the simulator lockstep trace derives `cmd_seq_at_ready` / command deltas.

If static inspection alone proves H3 false, state so explicitly.

## Stage 2 — minimal publication instrumentation

Add diagnostic-only instrumentation, default OFF, enabled by a dedicated environment flag such as `TROT_LOCKSTEP_PUBLISH_DIAG=1`. It must not change control timing or publication behavior except negligible logging overhead.

For every actual trot LowCmd publish, record one CSV row with at least:

- monotonic diagnostic publish index;
- wall-clock timestamp or steady-clock ns for ordering only;
- `state_snapshot.tick()` consumed by that `LowCmdWrite`;
- `lockstep_cmd_seq_` value associated with the cycle;
- `lockstep_ack_enabled_`;
- `lockstep_epoch_valid_`;
- `lockstep_writer_gate_.Engaged()`;
- lifecycle phase sufficient to distinguish pre-gait / gait / stop (or equivalent booleans);
- current `running_time_` / motion-clock time;
- whether this publish came from the writer thread's gated branch or free-running branch.

If necessary, add a tiny enum/marker passed from the writer loop into the diagnostic path. Do not alter the LowCmd payload, control law, simulator exchange protocol, or acceptance logic.

Also capture enough simulator-side information to join each published command to the existing `lockstep_trace.csv` command sequence. Prefer existing command sequence/accounting; do not invent a new synchronization mechanism.

## Stage 3 — exactly one diagnostic run

Run exactly one Phase1 varying baseline with:

- D4 OFF;
- lockstep ON;
- the same period/duty/profile/model as checkpoint `640124d...`;
- diagnostic publication logging ON;
- same lockstep protocol and analyzers.

No rerun is authorized even if the run physically fails; attribution of duplicate publication is the endpoint.

## Required analysis

For every simulator interval whose command delta is >1, determine whether there are corresponding multiple controller publish rows for the same consumed state tick.

Report:

1. Total controller publishes and total simulator-observed command arrivals.
2. Number and fraction of physics intervals with delta 1 / 2 / 3+.
3. Number of duplicate controller publishes grouped by:
   - before gate engagement;
   - exact engagement/handoff interval;
   - after gate engagement.
4. Earliest and latest duplicate interval in simulator time and controller motion time.
5. Lifecycle phase distribution of duplicates.
6. Whether every simulator duplicate can be matched to an actual extra controller publish.
7. Whether any actual controller duplicate occurs after `lockstep_writer_gate_.Engaged()==true` for the same consumed state tick.
8. Whether any second production LowCmd publication path was observed.

If duplicates are confined to pre-engagement / handoff, quantify exactly how many and explain why the current strict gate sees them. If duplicates persist after engagement, identify the exact writer/gate failure mechanism if the evidence permits.

## Decision labels

Choose exactly one:

- `PRE_ENGAGEMENT_ONLY` — all extra commands are explained by free-running lifecycle before the writer gate owns cadence; no post-engagement duplicate publish exists.
- `POST_ENGAGEMENT_WRITER_BUG` — actual duplicate controller publishes for the same state tick occur after gate engagement and the writer/gate path is responsible.
- `SECOND_PUBLISH_PATH` — a distinct production LowCmd publication path causes duplicates.
- `SIM_ACCOUNTING_MISMATCH` — simulator command deltas exceed one without corresponding extra controller publishes.
- `MIXED`
- `INCONCLUSIVE`

## Deliverables

Create:

`docs/validation/phase1_lockstep_single_update_attribution_20260914/RESULTS.md`

and compact CSV evidence sufficient to audit the conclusion, including per-publish rows or a lossless derived table and a duplicate-interval join table.

Record source SHA, simulator/controller binary SHA256, scene/profile hashes, exact command, run ID, and raw artifact hashes.

## Stop rule / next step

Do not repair the duplicate-update behavior in this task. End with exactly one recommended minimal next step based on the label, and stop after one pushed checkpoint.
