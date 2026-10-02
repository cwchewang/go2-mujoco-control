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

Previous engineering preparation compiled both diagnostic binaries and passed 15 focused contracts. Its eight sealed historical-response offline replays were accepted; new optimizer calls and canonical integrations were zero. Those saved receipts remain in evidence/validation-receipt.json.

## Execution hold and evidence packet

Independent science review approved the bounded design (8 optimizer calls, four workers, canonical integration 0, aggregate private reservation 32,768). Execution remains HOLD until independent admission verifies saved test output, offline replay output, both binary identities/hashes, sealed input hashes/manifest, and the prepared packet bound to the final HEAD. No optimizer is authorized by this preparation.

## Launcher and output-location repair (zero optimizer)

The import failure is sealed at _runs/mjpc_fd_duplicate_sequence_execution_84e85199f6b3/; its manifest SHA-256 remains eb1d857fb777ec381867a0c822ffa471436b5165fcb5201093f99274ad4655db. It occurred before lock acquisition, preflight, or native launch. It is not a scientific sample.

The actual entry is now the committed executable tools/substrate/run_mjpc_short_sequence, which switches to its own repository root and invokes python3 -B -m tools.substrate.mjpc_short_sequence_launcher. It works from /tmp and the repository. Preparation and execution share the existing experiment lock and preflight. --no-launch follows that same path and has a separate denied-native runner before returning. The launcher seals capture outputs and accounts for private counters by per-call deltas within each persistent process.

Before any mkdir or transport launch, the core sequence runner rejects existing output paths, symlink aliases, and sealed ancestors. The launcher additionally requires both new preparation and observation output directories to be direct children of _runs. The old sealed preparation's five original members still match their hashes; the four previously appended short_sequence_evidence files remain preserved, so its directory manifest still has a file-set mismatch. This repair does not modify, remove, or reuse that bundle as the new preparation.

The real command regression, not just consumer parsing, passed 24 tests at source commit 085e61305b669fce9aaead2856e408cb3544c1a6. It covers complete command invocations from both cwd values, no native launch, empty/nonempty existing outputs, sealed packet member preservation, core rejection before transport, and symlink bypass refusal. Actual stdout/stderr and source/build/input identities are in evidence/launcher-validation.json and evidence/launcher-tests-085e613.*.

The new independent preparation is _runs/mjpc_short_sequence_evidence_launcherfix_20261003/; its packet binds the final clean HEAD and includes runtime hashes, both copied binaries and original build identities, and all eleven sealed inputs. Its immutable manifest is separate from _runs/mjpc_short_sequence_observation_launcherfix_20261003/, the proposed fresh observation output. The tested preflight command is:

    /home/che/dev/go2-workspace/current/tools/substrate/run_mjpc_short_sequence --execute --packet /home/che/dev/go2-workspace/current/_runs/mjpc_short_sequence_evidence_launcherfix_20261003/packet.json --output /home/che/dev/go2-workspace/current/_runs/mjpc_short_sequence_observation_launcherfix_20261003 --no-launch

The future capture command has the same executable and arguments with --no-launch removed. No optimizer ran in this repair. The 8-call scope and Stage 3 OPEN scientific boundary remain as previously declared; the repaired launcher and final packet are ready for review.
