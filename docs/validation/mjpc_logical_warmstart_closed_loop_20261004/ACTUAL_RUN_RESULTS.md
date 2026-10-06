# Logical warmstart closed-loop capture — actual results

**Outcome:** the logical-seed arm was exactly repeatable in this frozen condition, while worker-local seeding was not. The logical arm was not worse on the measured repeatability metrics or progress, but absolute forward progress remained low; this is not a locomotion-performance qualification.

## Receipt and scope

The original Praxis dispatch `px_1a104c0ea54_a2026843e1` was rejected before runner execution because `workspace-exec tasks must use maintenance mode`. That dispatch consumed no attempts. After explicit user authorization, the same reviewed packet was captured through Base’s existing SSH connection to Atlas WSL, using the producer at `research/mjpc-logical-warmstart-closed-loop-20261004`, HEAD `190e56939de0d8f57670747b73b4252b4d9ae603`. No remote Codex backend or Praxis execution was involved.

The actual campaign `RESULT.json` is `CAMPAIGN_COMPLETE`, budget `CLOSED`, with all four slots completed, no retry, and no omitted slot: 4 attempts, 6000 canonical steps, 600 optimizer calls, 2,457,600 private steps reserved and 1,471,200 upper bound. Every slot has 1501 recorded frames (ticks 0–1500), and all canonical replays passed.

Evidence is under `/home/che/dev/go2-workspace/logical-warmstart-closed-loop/_runs/mjpc_logical_warmstart_closed_loop_20261004/`; ledger: `/home/che/dev/go2-workspace/logical-warmstart-closed-loop/_runs/logical_warmstart_campaign_38d7f7b56ce2eeccbd545f72d10e658e143644e4b59d02943d739845c7bd3639.json`. `RESULT.json` SHA-256 is `b3f9825e3e90ca67a59e9ae114b8aa0a199896b6147a814a86d3f201d05d3ac9`; ledger SHA-256 is `c1520e0b04518d29ee037f0e73c26b58224dac8c61d3efb56f69daa327b3e024`. The runner binary SHA-256 is `b161f969ca5d8e48c7cc3fc7ab98b4e9c93d94b0d67fa721acf1ba4bfef45fef`; packet SHA-256 is `38d7f7b56ce2eeccbd545f72d10e658e143644e4b59d02943d739845c7bd3639`.

## Raw trajectory checks

Offline recomputation from each slot’s `raw.jsonl` used base x displacement, qpos height, the root quaternion (MuJoCo w-x-y-z order) for roll/pitch, and the recorded per-joint saturation flags. Torque values are in N·m. The actuator clipped limit observed in every slot was 45.43 N·m; unclipped requested peaks are also shown.

| Slot | Progress (m) | Height min–max (m) | Max |roll| (rad) | Max |pitch| (rad) | First saturation / saturated ticks | Peak unclipped torque (N·m) | End |
|---|---:|---:|---:|---:|---:|---:|---|
| logical1 | 0.928938 | 0.269988–0.324490 | 0.138035 | 0.170986 | 425 / 1 | 47.701 | horizon, tick 1500 |
| logical2 | 0.928938 | 0.269988–0.324490 | 0.138035 | 0.170986 | 425 / 1 | 47.701 | horizon, tick 1500 |
| worker1 | 0.814417 | 0.269988–0.325195 | 0.122263 | 0.200675 | 675 / 3 | 51.948 | horizon, tick 1500 |
| worker2 | 0.879740 | 0.269988–0.324487 | 0.118284 | 0.168125 | 925 / 1 | 48.891 | horizon, tick 1500 |

Logical trajectories match exactly for recorded control, target, qpos and qvel. Worker controls differ above 1e-9 beginning at tick 10; qpos differs above 1e-9 at tick 44. The worker progress gap is 0.065322 m; the first-saturation gap is 250 ticks. The frozen engineering checks pass for logical and fail for worker progress, pitch and saturation timing. Across all four raw logs there are no warning counts, recorded failures, or forbidden-contact frames. Since every run ended at the fixed horizon, later stopping behavior is right-censored; no stop-rate or generalization claim follows.

## Scientific interpretation and next question

This supports a narrow conclusion: logical ownership removes the worker-arm divergence in this exact condition and did not reduce progress relative to either worker repeat. It does not show strong locomotion performance: even the logical arm moved only about 0.929 m over the 3-second horizon, and one worker repeat had lower pitch than logical. The result does not establish a causal performance advantage, broad repeatability, or that historical A’s stopping behavior is fixed. Historical A remains `CLOSED_NO_RETRY`; B remains `NOT_RUN_REPRODUCTION_GATE_FAILED`; R4 remains FAIL; no 12-second run exists.

The key unresolved question is whether the repeatability and low absolute progress persist under an independent initialization. A minimal discriminating study is a newly reviewed matched 2×2 capture (two logical and two worker repeats) at one predeclared fresh seed/initialization. It is **outside the existing authorization and budget**: this four-slot campaign is CLOSED. No additional run was started, and this report does not reopen budget.

## Direct SSH recovery and receipt

The successful route is Base SSH alias `atlas`, then WSL Ubuntu-22.04, invoking the already-built producer capture entrypoint. The preserved launcher is `/tmp/go2_logical_warmstart_capture_20261004.sh`; it invokes `python -B -m tools.substrate.mjpc_logical_warmstart capture` with the frozen qualification packet, review, authorization and output paths. The run used tmux session `go2-logical-warmstart-capture-20261004`; wrapper PID was 1459503 and runner PID 1459506. Resume diagnosis reads `/tmp/go2_logical_warmstart_capture_20261004.log` and `/tmp/go2_logical_warmstart_capture_20261004.exit`, then independently checks `RESULT.json`, the packet-bound ledger, and the raw per-slot JSONL. Exit receipt is `0`. The capture is complete; these are recovery/receipt references, not instructions to rerun it.

The contemporaneous pre-capture dispatch note remains at [RESULTS.md](RESULTS.md) to preserve the earlier rejection history. The active frontier now links to this actual-run supplement.
