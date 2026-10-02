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

## Minimum next observation replay (completed)

Use four cold starts: original and fixed variants, each repeated twice. In each process, keep the same four-worker controller alive while feeding the verified sealed external input rows for ticks 0–10 in order. Preserve the logged replan schedule: optimizer calls at ticks 0 and 10 only. This is eight optimizer calls total and a 32,768 aggregate reservation at 4,096 per call. Do not step the canonical evaluation plant or claim a forward-physics result.

Record, per optimizer call: input tick/time/state/command digest; policy ID and selected candidate ID; cost and q_des; pre-call and post-call policy/trajectory hash with dimensions and finite-value checks; and the existing private accounting. Record, per FD task, knot, worker ID, start/end interval, and qacc_warmstart before/after as a stable hash plus norm and max-absolute value. Hash summaries explain history without storing full internal arrays.

Compare exact external-input digests and replan schedule across all four runs. Compare candidate ID exactly and cost/q_des/trajectory numeric summaries with predeclared absolute tolerance 1e-9; report worker assignment and warmstart summaries rather than requiring identical scheduling. Confirm original has duplicate t34 tasks per replan and fixed has one. Compare tick-10 versus tick-0 summaries within each process to expose state carried between replans, and compare both repeats before interpreting variant differences.

Stop the entire paired sequence on any missing or changed sealed input, nonconsecutive tick/time, dimension/nonfinite input, replan schedule drift, worker count other than four, stale/missing candidate, missing warmstart/policy summary, any warning/stderr, unknown or over-reservation private budget, or any canonical integration step. Do not retry or fill a stopped pair.

Previous engineering preparation compiled both diagnostic binaries and passed 15 focused contracts. Its eight sealed historical-response offline replays were accepted; new optimizer calls and canonical integrations were zero. Those saved receipts remain in evidence/validation-receipt.json.

## Completed same-process observation

Joint science/execution review approved the packet bound to HEAD 6c2dbadc72bfcfd64bfafe4a63d77b2ff2ed9174. The user then explicitly authorized execution. Fresh preflight passed under the exclusive experiment lock; the run used four native processes, four workers each, all 11 ticks, and two optimizer calls per process at ticks 0 and 10. **Attempted/completed: 8/8.** All four runs completed without stderr or warning. Canonical integration steps were 0.

The exact input digests matched across all four runs. All selected candidate IDs were 8. At tick 0, all costs were 0.06608674148251567 and q_des matched exactly. At tick 10, all costs were 0.06179540548852948; maximum q_des difference was 1.0067746636366337e-10 within repeats and 1.0056555588278115e-10 across variants, below the predeclared 1e-9 tolerance. Cost differences were zero at both anchors.

Original emitted two t34 FD events per call; fixed emitted one. Tick-0 t34 Jacobian summary was 0aa12e12d06c1ff1 across all runs. Tick-10 hashes were 997cc10f76ee60c9 for repeat 1 and 352f0a5fcba0ec7f for repeat 2, matching across variants within each repeat despite differing worker assignments.

Planner policy/selected-trajectory hash was 783924e4fe084d93 in all four runs at tick 0. At tick 10 it varied by run: original repeats 5d10479541baf28a and 48deae72a791bc34; fixed repeats e8e53f897fea1acf and 8e9ddcea76b70575. Tick-0 warmstart input was zero (hash ec32669a74fcae65); each process's tick-10 pre-call worker warmstarts equal its own tick-0 post-call summaries, confirming state persisted within that process. Worker assignments and the corresponding per-worker warmstart hashes/norms vary across runs. The selected cost and q_des remain within tolerance, so these summaries show internal-history variation without identifying its cause or reproducing old A's hidden state.

Private integration upper bounds were 2,501 per original call and 2,452 per fixed call, 19,812 total. The run reserved 4,096 per call, 32,768 total. This is a bounded engineering observation, not a capability result, controller ranking, or real-time claim. Stage 3 topic selection remains OPEN.

Immutable run evidence is _runs/mjpc_short_sequence_observation_launcherfix_20261003/. Its manifest SHA-256 is f25395406e10ae9ef0f4ffa723d5784fedfebe6888803c5c4da79ba2a4f10f9f, RESULT.json SHA-256 is 2acd26298c93a26d7505949e8f90d937817384360fbba8879618c4c22d069f72, private-accounting.json SHA-256 is b1a4c916de6ce403532aee09df49fff3ada6fac0ab044af0eec2f0f75e714897, and admission.json SHA-256 is 018f67ba34d8c8c61813091e72c12631271f664fb4b23b6056f1e98585ef3894. The fresh-preflight record is sealed in the same manifest. The prepared packet remains _runs/mjpc_short_sequence_evidence_launcherfix_20261003/packet.json with SHA-256 a0cefd7b8b453a9c2a689da92cba627875c6509c6d37b892e2600a6c4e0567c7; its manifest SHA-256 is 946e72ab52668836bb4ef92f72f12dff93248a6ee9d284e0f937a3059a4dfd43. The sealed input raw SHA-256 is 9a4f2711f558b80ac58c803406971f43be7c44f4c5e64f7a50c728e2a7440e55.

## Launcher and output-location repair

The import failure is sealed at _runs/mjpc_fd_duplicate_sequence_execution_84e85199f6b3/; its manifest SHA-256 remains eb1d857fb777ec381867a0c822ffa471436b5165fcb5201093f99274ad4655db. It occurred before lock acquisition, preflight, or native launch. It is not a scientific sample.

The actual entry is now the committed executable tools/substrate/run_mjpc_short_sequence, which switches to its own repository root and invokes python3 -B -m tools.substrate.mjpc_short_sequence_launcher. It works from /tmp and the repository. Preparation and execution share the existing experiment lock and preflight. --no-launch follows that same path and has a separate denied-native runner before returning. The launcher seals capture outputs and accounts for private counters by per-call deltas within each persistent process.

Before any mkdir or transport launch, the core sequence runner rejects existing output paths, symlink aliases, and sealed ancestors. The launcher additionally requires both new preparation and observation output directories to be direct children of _runs. The old sealed preparation's five original members still match their hashes; the four previously appended short_sequence_evidence files remain preserved, so its directory manifest still has a file-set mismatch. This repair does not modify, remove, or reuse that bundle as the new preparation.

The real command regression, not just consumer parsing, passed 24 tests at source commit 085e61305b669fce9aaead2856e408cb3544c1a6. It covers complete command invocations from both cwd values, no native launch, empty/nonempty existing outputs, sealed packet member preservation, core rejection before transport, and symlink bypass refusal. Actual stdout/stderr and source/build/input identities are in evidence/launcher-validation.json and evidence/launcher-tests-085e613.*.

The independent preparation is _runs/mjpc_short_sequence_evidence_launcherfix_20261003/; its immutable packet binds source, build products, binaries and all eleven sealed inputs. The actual same-process observation completed in the separate top-level output directory _runs/mjpc_short_sequence_observation_launcherfix_20261003/. The earlier launcher-repair step itself had zero optimizer calls; the completed observation and its results are recorded above.
