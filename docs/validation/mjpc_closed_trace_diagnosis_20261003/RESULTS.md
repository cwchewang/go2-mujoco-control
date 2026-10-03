# Closed MJPC A/reference trace diagnosis

This offline engineering increment identifies the earliest observable divergence,
repairs three demonstrated execution/diagnostic defects, and selects the next
minimum discriminator. It does not reopen either adaptation v1 scope or claim a
stable locomotion mechanism. Stage 3 remains ACTIVE / OPEN.

Authorization: continuing Go2 delegation, “重新全权负责起 go2 吧，持续推进”
(2026-10-03 18:58 UTC, Sentinel_b53fcca2fd38819194a7104c5becc0c7),
restated by the source thread 01a0f08f-d223-7240-813b-ee93267b700d.
Actual writable checkout: Atlas /home/che/dev/go2-workspace/current,
branch research/mjpc-floor-registration-12s-20261003, entry HEAD
e1728c8c51f010444a16333722b31519a0fd8b3a. Origin was refreshed once; local
HEAD remains one commit ahead. The pre-existing floor-registration RESULTS.md
edit is preserved. The c99bef8 adaptation worktree and its passed qualification
were not changed or rerun.

## Sealed inputs and earliest divergence

[analysis.json](analysis.json) and [analyze.py](analyze.py) provide source-bound,
reproducible calculations. The script checks every member of the A, reference,
and historical short-sequence manifests, as well as the two fixed raw hashes.
It imports no MuJoCo and invokes neither integration nor an optimizer.

A: _runs/mjpc_adaptation_diagnostic_execution_20261002/original_capture_20261002T164948Z,
HEAD 61e543cfd657b455585637b92e8ad3b7a80decad, 887 frames / 886 steps.
Reference: example/cpp/experiments/_runs/shared_baseline_probes_v1/run_20261002T085338452324Z/mjpc_baseline_1.jsonl,
HEAD b1ac4f700cc0f8ed3bd431e28a230bc1ae71058d, 1288 frames / 1287 steps.
Both terminate for nonfoot contact. A is CLOSED_NO_RETRY; B remains
NOT_RUN_REPRODUCTION_GATE_FAILED. The original absolute 1e-9 reproduction
threshold and required stop tick 1287 remain unchanged.

| Observable | First nonzero difference | First difference above 1e-9 |
|---|---:|---:|
| Position target | tick 10, 2.6831203925326008e-11 | tick 20, 8.226478609429932e-9 |
| Applied torque | tick 10, 1.6098722355195605e-9 | tick 10 |
| qvel | tick 11, 5.896094723567558e-11 | tick 21, 1.2109907854274127e-8 |
| qpos | tick 11, 1.1790568521519162e-13 | tick 32, 2.659279685346405e-9 |
| Command | identical throughout paired prefix | none |
| Support/forbidden classification | tick 113 | exact categorical comparison |

At tick 10 (20 ms), the second replan, qpos, qvel, command and cost are
exactly equal. The largest target difference is RR_calf_joint. Both PD laws
use kp=60; the difference in PD torque equals 60 times the target difference,
with maximum algebraic residual 8.88e-16. Neither arm is saturated there.
Tick 0 targets/actions and the entire state/control prefix through tick 9
match exactly.

The q_des difference grows to 8.23e-9 at replan 20, 9.39e-7 at replan 30,
and 0.1249 at tick 90. Torque difference first exceeds 1 Nm at tick 85,
before support classification differs at tick 113 (A loses FL; reference
retains FL/RR). First saturation is tick 178 in A versus 105 in the
reference. First logged native stderr is tick 130 in A versus 110 in the
reference, both after the tick-10 divergence. Warnings refer to private
rollouts; their embedded simulation time is not the canonical tick.

Thus a small planner output difference precedes state divergence; subsequent
feedback/replanning amplifies it. Contact switching, saturation and warnings
are later observations, not explanations for the earliest recorded difference.
Raw qpos/qvel maxima mix component types; they are descriptive absolute
component differences, not a normalized stability metric.

## Initial conditions, versions and hidden state

The observable reset, initial qpos/qvel, targets/actions, commands and early
support classifications agree. This excludes a changed logged initial pose or
velocity as the trigger; unlogged planner/task/worker state is not excluded.

Canonical physical fingerprint is identical:
1c7ec61af1297fe1715e3d412481709bf4ad3ad42196e483c444d1a54db73e94.
Both pin MJPC e00c47a5adb9856af2e0f24231bb3a60d5be23c4.
Archived MJPC and Abseil file maps, compiler, MuJoCo library, MuJoCo headers
and source-lock identity match exactly. Controller binary hashes differ:
8f6867c911067db654f4af45b98407fd72066e9ba5316ca5dcf8706a0147784a
versus a0c6198d65253d94863a40a92b0780ba376a4b6f358fdf83695ff1182ec04f24.
The source diff adds diagnostic budget reservations/counting and prediction
recording. Recording uses a separate private copy after action selection.
A direct change to canonical physics is unsupported; instrumentation,
memory layout or scheduling effects remain possible.

Source inspection shows parallel derivative/rollout tasks reuse worker mjData.
Derivative SetState replaces state/control/time without clearing per-worker
qacc_warmstart. Original T=36/skip0 scheduling duplicates t34 into the same
Jacobian slots. Existing reviewed fixed-input observations show varying
worker warmstart/policy/trajectory hashes across fresh processes; the
fixed schedule removes duplication while costs/q_des remain within 1e-9 for
those logged inputs. The tick-10 inputs are now known to use the wrong joint
order, so this is not an elimination test under the production A inputs.
This supports internal-history variation as a candidate, but does not prove
that duplicate-FD scheduling caused the original A/reference divergence.

A's first four selected nominal candidates are all index 8. One-knot nominal
versus actual gaps already occur at anchor 0: at canonical tick 5 the
max qpos difference is 0.01216 and qvel difference 1.64189. These compare
the private 10 ms nominal with five 2 ms feedback transitions, using different
model/actuation conditions; they are not pure model-error estimates or proof
of the stop's cause. The reference has no saved selected trajectories or
complete planner/worker arrays, so its hidden histories cannot be reconstructed
exactly from existing raw.

Confidence: high for the observable ordering and PD amplification; medium
for scheduler/worker-history variation as a trigger class; unproven for a
specific warmstart/duplicate-FD cause and for the final calf-contact mechanism.
Binary/instrumentation effects remain a competing explanation.

## Demonstrated defects and actual repairs

1. Capture admission used only a checkout-local attempt directory.
   A new worktree's empty ledger could permit the same consumed v1 identifier.
   Current mjpc_diagnostic_capture.capture now permanently refuses both
   mjpc-adaptation-original-3s-v1 and mjpc-adaptation-corrected-3s-v1 immediately
   after sealed prepared-bundle verification, before model loading, identity
   checks or native launch. Historical audit functions and frozen protocols
   remain intact. The new regression uses an empty root and proves neither
   controller launch nor attempt/output mutation occurs.

2. The short-sequence observer omitted the explicit reset that the live
   PositionTargetControllerAdapter/NativeMJPCController path sends after
   construction. All four historical sequence native logs contain zero
   reset requests even though their step packets match the A inputs exactly.
   Their tick-10 cost is 0.06179540548852948 versus A's 0.06179009604427559.
   This is a concrete initialization-parity defect in that observer; it does
   not by itself explain A/reference divergence, since both live captures
   use the reset path. The observer now logs and validates a strict reset
   handshake before any optimizer reservation, rejects malformed replies,
   timeout or stderr, and labels the initialization in its result.

3. The observer packed canonical qpos/qvel in FL/FR/RL/RR order directly
   into a native interface that expects FR/FL/RR/RL. Production step_packet
   performs named reordering. All four old sequence logs match unreordered
   raw bytes but differ from the production wire packet starting at tick 1
   (max component difference 0.008324372889734847); q_des differs from A by
   2.199039369439929e-6 at that same tick. Symmetric tick 0 hid the defect.
   The sequence observer now reconstructs WholeBodyState with canonical
   joint names and calls the production step_packet. It logs both orders
   and rejects a selected prediction whose initial state does not match
   the native packet. Asymmetric and real-sealed-input regressions pass.
   The retained old one-call _packet helper remains available for historical
   contract replay; it must not be used for the new faithful observation.

4. current.json and generated CURRENT still described formal attempts as zero
   and directed a fresh A/B review. They now point to this superseding record
   and explicitly retain A's consumed attempt, B's failed gate and R4's repeat
   failure. Sealed preparation reports/manifest members are not rewritten.

## Validation and limits

29 relevant Python regressions pass under the zero-step guard: 14 capture/
diagnostic and 15 reset/mapping/sequence tests. All three existing native
no-integration CTests pass with the exact pinned SDK library. Check logs are
in checks/. Failed first-check logs are retained: the reset-test harness had
incorrect positional arguments and then a missing mocked replan field (both
corrected in tests); initial CTest loading lacked the pinned MuJoCo library
search path (corrected only in the test command after checking exact SHA-256). No scientific attempt or
optimizer call was consumed by either failure.

The guard and observer fixes change runtime input fingerprints. They have
targeted regressions, but are not a new clean-head capture qualification or
a scientific/execution review. Current retains the user's pre-existing dirty
file; no old qualification is misrepresented as qualifying these changed
inputs. A future observation must finish its own applicable qualification,
deterministic precheck and exact-head review. The already passed c99
qualification remains intact historical evidence.

## Selected minimum next observation

The immediate discriminator is faithful transport/history parity after the
demonstrated mapping and reset repairs, before wider warmstart interventions.
Use one sealed original diagnostic binary, unchanged A tick 0..10 canonical
inputs, the production named-state encoder and live explicit reset, in two
fresh-process repeats. Replans occur only at ticks 0 and 10. Total: four
optimizer calls, 16384 reserved private-step upper bound, zero canonical steps,
zero live scientific attempts. Four workers and all model/command parameters
remain fixed. Use a new source-bound observation task, never an old A/B ID.

Log reset request/reply, both joint orders, all wire packets/responses,
selected policy/cost/q_des and existing warmstart/FD summaries. Check each
wire packet against the production encoder, then compare every tick's
q_des/cost against A and compare the two repeats. Keep absolute 1e-9 and
every failure. Stop the whole pair on incorrect reset/input/binary/ordering,
warning, candidate/evidence/accounting failure or budget overrun; no fill-in.

If corrected input/reset reproduces A within tolerance, it supports fidelity
of the observer and withdraws the previous observer's use as a discriminator
for A/reference divergence. It does not identify which repair contributes
which output change or explain the live A/reference trigger. If differences
remain with repeat variation, a separately bounded worker-history experiment
becomes useful. If both repeats agree but differ from A, first audit remaining
hidden initialization and instrumentation/binary effects.

A new paired variant study is justified only after faithful inputs are
established. No output authorizes B, replacement A, 12s capture or a controller
ranking. R4's two replay-PASS 3s runs still have a 860-tick saturation spread
above the unchanged 200-tick limit; no 12s capture exists.

This concrete four-call observation was selected, but not executed during
this offline increment. Its own qualification/precheck/exact-head review is
the remaining execution work.
