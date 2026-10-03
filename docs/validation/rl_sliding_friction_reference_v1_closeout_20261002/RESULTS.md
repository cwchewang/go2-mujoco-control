# RL sliding-friction reference v1: local verified closeout

Status: CAPTURE_COMPLETE; both arms PASS; independent raw/real-ledger replay
VERIFIED. Both original independent reviewers completed read-only closeout:
science APPROVED and execution APPROVED / VERIFIED. Their final turn references
and delegated attestations are retained in [closeout review](closeout-review.json).

## Frozen execution and result

The separately authorized protocol ran at
`849b7aa13c82b13880cfc214083f2473e794e83e`. Four-foot sliding mu changed
0.8 to0.3 at6s/tick3000, with inherited RL policy, reset, command, information,
timing, safety and performance thresholds. Exactly2 fresh controller/plant
instances consumed2 scientific attempts and12000 canonical steps.
Each reached12s/6000 steps/6001 frames. Private planning calls were0.

| Declared measure | RL friction1 | RL friction2 | Paired sealed baseline |
|---|---:|---:|---:|
|[2,12) body-vx mean m/s|0.8741013304|0.8741013304|0.8852922675|
|[2,12) body-vx MAE m/s|0.1258986696|0.1258986696|0.1147077325|
|Whole episode lateral max m|0.2157132126|0.2157132126|0.1680091859|
|Whole episode yaw max rad|0.0589126058|0.0589126058|0.0450763438|
|[6,12) auxiliary mean m/s|0.8667549071|0.8667549071|0.8854064689|
|[6,12) auxiliary MAE m/s|0.1332450929|0.1332450929|0.1145935311|

Primary paired mean changes−0.0111909371m/s and MAE changes+0.0111909371m/s.
The predeclared auxiliary mean changes−0.0186515619m/s and MAE
changes+0.0186515619m/s relative to each own baseline. These auxiliary metrics
have no thresholds and do not alter primary PASS. The primary window contains
5000 samples, auxiliary3000; tick6000 is excluded from both means.

The raw paired prefix through tick3000 is exactly equivalent (maximum
difference0). Each arm has5726 changed active foot-floor contact-friction
records covering2948 ticks and verified complete effective exposure. The first confirmed exposed
state is tick3001/6.002s, after the hook applies at tick3000. These are contact
constraint/friction records, not independent statistical samples or measured
contact forces. Whole-episode lateral max0.215713m and yaw max0.058913rad
both pass their original0.3 bounds.
Both raw files share SHA256
`151dfa3c8a7a24418dd0fbbfcfaaa015788b00e0cf56002a6ad38397adb7fb58`;
maximum repeated state/applied-control difference is0.

## Third-stage local conclusion and limits

The two arms are deterministic reproduction under the same reset, policy,
environment and seed setting. They are not independent statistical seeds.
Identical raw confirms same-machine repeatability; it does not estimate a
success probability or sampling uncertainty.

Together with the sealed two12s RL baseline PASS traces, this card shows that
the frozen RL adapter retains the declared operational task after this one
6s friction reduction, with a small paired speed-tracking change.
The [old shared campaign](../shared_baseline_probes_v1_closeout_20261002/RESULTS.md)
has one adapted MJPC baseline safety stop at2.574s (floor/RR_calf), leaving17
arms NOT_RUN and its four-baseline gate incomplete. That truncated single trial
does not supply an aligned12s comparator or identify a stable mechanism.
The new card supplies one RL-only condition point; cross-family conclusions,
broader friction thresholds, other conditions and the complete Gate0 remain open.
The prior #189 low-friction erratum is unchanged. Fourth-stage method work has
not been started.

## Execution provenance, failures and preservation

Formal START:2026-10-02T13:14:08.813216Z, PID773698. Real science/execution
final approvals and delegated user START are retained in [review](review.json)
and [authorization](authorization.json). Fresh in-process preflight and capture
held the same experiment lock continuously. [Analysis](analysis.json) and
[verification](verification.json) contain the exact claims, SHA and metric replay.

The first convenience wrapper (PID772778) failed to import `tools` before it
entered the reviewed capture API. At that point the campaign ledger, output,
scientific attempts and physics were absent. Its original stdout/stderr and
source remain preserved; [failure receipt](preentry-wrapper-failure.json)
records the defect. The same authorization/output was then invoked through the
reviewed module CLI. The formal entry consumed exactly the frozen two arms.
The official CLI stdout is retained; its stderr is empty. No formal arm or
started campaign was retried and no runtime/controller code changed after review.
The execution closeout accepted this preserved pre-entry dispatch correction
and confirmed the worker exited and the real ledger has one campaign/two claims.

Capture:
`example/cpp/experiments/_runs/rl_sliding_friction_reference_v1/run_20261002T130923251546Z`.
Capture manifest SHA:
`5154e8406abff5ed2a6f3f5721fd8879893a5292bc0a9314fa1fc861ad2425a8`.
Verification manifest SHA:
`23797caaf3dc8a2b54dc5836874245eaa283847658df690db9dc8161d353b33f`.
The [archive receipt](archive-receipt.json) records24403045bytes/94 verified
members, including all failure/log files, raw, actual ledger, qualified/prepared
inputs and the live source snapshot. Archive SHA:
`1891bb0f5a755f559ea6e00fed11ae99a25dd934952b005a433c6a7ba82ac13a`.
Original absolute references are preserved; no portable execution claim is made.

The frozen budget is exhausted and this protocol is closed. Old17 NOT_RUN and
all prior sealed evidence remain unchanged. Both closeout reviews approve the
bounded third-stage deliverable. Broader stage-three evidence gaps remain.
RL boundary probing and an MJPC zero-forward-command study are possible next
stage options awaiting user selection; neither is started or authorized here.
Further physical investigation requires a separate prospective task.
