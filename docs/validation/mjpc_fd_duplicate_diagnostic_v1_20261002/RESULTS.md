# MJPC duplicate-FD diagnostic — closeout and next discriminator

## Completed bounded diagnostic

**Status:** complete; Stage 3 topic selection remains ACTIVE / OPEN.

Eight one-call trials compared the upstream and duplicate-index-fixed binaries at sealed tick 0 and tick 10 anchors, with two fresh-process repeats per variant and four workers. All eight calls were accepted; summed private upper bound was 19,812 within the 32,768 reservation; canonical integration steps were zero.

The original schedule recorded two overlapping duplicate t34 FD tasks on different workers at both anchors. The fixed schedule recorded one t34 task per anchor. Repeats matched within each anchor, and original/fixed paired candidate IDs, costs, q_des outputs, and t34 Jacobian summaries matched. The fix removes the duplicate scheduling defect; this cold-start comparison found no output effect. The earlier warm-trajectory divergence remains unexplained.

This was not an exact replay. These one-call trials started fresh planner processes, and the raw anchor inputs do not contain prior planner policy or worker mjData state.

## Old A input audit

Sealed source: `_runs/mjpc_adaptation_diagnostic_execution_20261002/original_capture_20261002T164948Z/`. Its verified `raw.jsonl` SHA-256 is `9a4f2711f558b80ac58c803406971f43be7c44f4c5e64f7a50c728e2a7440e55`; capture status is ENGINEERING_ADMITTED, range tick 0–886, with the original stop at tick 886 for nonfoot contact.

For ticks 0–10, the raw stream has every consecutive tick, qpos (19), qvel (18), command (3), and `sim_time_s`; all values are finite, times advance from 0 to 0.020 s in 2 ms increments, and the command remains [0,0,0]. Recorded controller diagnostics report replans only at ticks 0 and 10. Those external inputs are complete for a short sequence replay with two optimizer calls per process.

The raw stream does not contain the old process's full planner policy or per-worker mjData warmstart. A new sequence therefore preserves planner and worker history only between its own tick-0 and tick-10 replans; it cannot be called an exact continuation or reproduction of old A's hidden state.

## Minimum next observation replay (implemented; execution pending independent admission review)

Use four cold starts: original and fixed variants, each repeated twice. In each process, keep the same four-worker controller alive while feeding the verified sealed external input rows for ticks 0–10 in order. Preserve the logged replan schedule: optimizer calls at ticks 0 and 10 only. This is eight optimizer calls total and a 32,768 aggregate reservation at 4,096 per call. Do not step the canonical evaluation plant or claim a forward-physics result.

Record, per optimizer call: input tick/time/state/command digest; policy ID and selected candidate ID; cost and q_des; pre-call and post-call policy/trajectory hash with dimensions and finite-value checks; and the existing private accounting. Record, per FD task, knot, worker ID, start/end interval, and qacc_warmstart before/after as a stable hash plus norm and max-absolute value. Hash summaries explain history without storing full internal arrays.

Compare exact external-input digests and replan schedule across all four runs. Compare candidate ID exactly and cost/q_des/trajectory numeric summaries with predeclared absolute tolerance 1e-9; report worker assignment and warmstart summaries rather than requiring identical scheduling. Confirm original has duplicate t34 tasks per replan and fixed has one. Compare tick-10 versus tick-0 summaries within each process to expose state carried between replans, and compare both repeats before interpreting variant differences.

Stop the entire paired sequence on any missing or changed sealed input, nonconsecutive tick/time, dimension/nonfinite input, replan schedule drift, worker count other than four, stale/missing candidate, missing warmstart/policy summary, any warning/stderr, unknown or over-reservation private budget, or any canonical integration step. Do not retry or fill a stopped pair.

Existing fd-trace logs already record knot, worker and interval. The offline real-response regression validates the sealed tick-0 native response through the current consumer and checks the old incorrect 37-state expectation is rejected. `python3 -m unittest -v tools.substrate.test_fd_duplicate_real_response` passed all 7 tests; its no-launch guard blocks native transport and optimizer calls. No optimizer, model build, or physics was run for this preparation.

## Execution hold and evidence packet

Independent science review approved the bounded design (8 optimizer calls, four workers, canonical integration 0, aggregate private reservation 32,768). Execution remains HOLD until independent admission verifies saved test output, offline replay output, both binary identities/hashes, sealed input hashes/manifest, and the prepared packet bound to the final HEAD. No optimizer is authorized by this preparation.
