# Shared baseline and bounded probes v1 closeout

Status: SCIENTIFIC SAFETY_STOP / permanently closed, local raw and external ledger VERIFIED.

Capture HEAD: b1ac4f700cc0f8ed3bd431e28a230bc1ae71058d.
Actual formal START: 2026-10-02T08:53:56.582893+00:00 (Atlas16:53:56).
The first scientific claim file was written at08:54:06.089739+00:00.
The capture was sealed at08:54:35.988910+00:00; the worker completion record
was written at08:54:35.994029+00:00. PID706616 used the official capture path.

The exact-head final science and execution APPROVED conclusions were forwarded
by the parent and bound to this preparation, qualification and packet before
launch. Original review threads/turns are preserved in review.json; those
forwarded records do not fabricate original review text. The actual fresh
preflight passed while capture retained the same inherited experiment lock.
The sealed original040 prelaunch failure and its no_retry job are unchanged.

| Arm | Classification | Canonical steps / frames | Outcome |
| --- | --- | --- | --- |
| rl_baseline_1 | PASS | 6000 / 6001 | Full12s horizon |
| rl_baseline_2 | PASS | 6000 / 6001 | Full12s horizon, identical raw bytes |
| mjpc_baseline_1 | SAFETY_STOP | 1287 / 1288 | nonfoot_contact at2.574s |
| Remaining17 arms | NOT_RUN | 0 | Frozen whole-campaign safety stop |

Exactly3 scientific attempts and13287 canonical steps were consumed, within the
20-arm/120000-step budget. No retry, replacement, tuning or sealed v1/v2 rerun
occurred. mjpc_baseline_2 and all16 challenge arms were NOT_RUN. The four-baseline
stage did not complete and no baseline-eligibility artifact was frozen.

## Bounded findings

Both RL repeats satisfy the frozen operational acceptance window[2,12):
mean body-forward velocity0.8852922675342852m/s, MAE0.11470773246571479m/s,
whole-episode lateral maximum0.16800918587598115m and yaw maximum
0.045076343833307386rad. Their raw SHA256 is
61259f7cd8d4398e307a798419f60cd3f1cce349a62f96e9973c7a4d168d07c8.
The offline maximum raw-state/applied-control difference is0. This supports
same-machine repeatability under this frozen shared deployment, not a statistical
success rate or challenge robustness.

The adapted MJPC first baseline stopped before its12s operational window could
complete. The terminal raw forbidden pair[0,53] maps to phase2_floor and an
unnamed geom on RR_calf. An independent one-mj_forward reconstruction at the
sealed terminal qpos/qvel, using the prepared identical physical model,
reproduces the pair with MuJoCo contact distance+0.0008041157844224708m.
This is contact evidence under the frozen guard, not a penetration claim,
planner root-cause finding, reproducible MJPC failure mechanism, or a ranking
of controller families. There is one MJPC scientific trial.

The declared safe-stop branch was exercised by real canonical dynamics and
correctly stopped the whole campaign. The shared MJPC useful-baseline admission
remains unmet; stage3 challenges have no results. Gate0 remains incomplete.
Information and native/private model differences preclude an equal-information
comparison. No terrain, hardware or real-time capability follows.

Canonical dynamics in this capture were13287 steps. Native MJPC planning used
real private optimizer rollouts; total private integration steps are not
instrumented. Qualification separately contained one static native admission.
Official verification, repeat/contact audits and archival added0 canonical
steps and0 private planning calls.

## Read-only prefix and optimizer diagnosis

For MJPC ticks0--499, height was0.269986--0.356433m, maximum tilt0.224301rad,
and maximum absolute roll/pitch/yaw0.184183/0.157535/0.084925rad.
There was no forbidden contact or canonical warning. Foot support was absent
for60 of500 samples (ticks132--175 and404--419), which is an observation rather
than a frozen safety failure. There were13 clipped motor-samples in11 frames,
first at tick105 on RR_calf_joint; no position-target clips. Applied torque
reached45.43Nm versus unclipped59.8680Nm.

All50 prefix planning calls took more than20ms (min/median/max
20.673/29.3855/45.682ms), while the500 feedback samples had observation age0.
Across the1287 applied-control samples,129 planning calls had
19.886/27.25/45.682ms min/median/max;128 exceeded20ms. This is offline_unbounded
compute time, not a measured end-to-end IPC latency or induced observation delay.

Native stderr had two rollout-divergence events first observed at tick110/140
and six overall. At canonical tick1230/2.460s the logger also contained a private
QACC warning with rollout Time2.7900. The pinned trajectory handler marks warned
rollouts failed/max-return and returns. Every returned selected current rollout
was valid, and the native controller checked freshness/failure/finite return
before responding. Candidate IDs and total rejected batch counts were not logged.
Canonical warning_count remained0 and state/control were finite. These channels
must not be conflated.

Despite identical binary/model/anchor/checkpoint identities, the new MJPC prefix
differs from sealed v2: first torque difference above1e-9 is at tick10
(max2.0973e-9Nm at that tick), qvel at21 and qpos at31. By tick499 the maximum
state/control-group differences reach0.6310 in qpos,17.5936 in qvel and44.0295Nm
in control. RL's same prefix difference is0. The initial MJPC pose/action/cost and
tick10 input state match; the cause of subsequent small optimizer/action
differences and amplification remains unresolved. This is a separate repeatability
or adaptation question, not proof of a specific implementation defect. Detailed
read-only metrics and source-grounded limits are in read_only_diagnostic.json.

## Evidence and continuation

Authoritative Atlas capture:
example/cpp/experiments/_runs/shared_baseline_probes_v1/run_20261002T085338452324Z.
Capture manifest:
66630a6c749c10891e59cfd454c7cf3174d7c310ac65ddd73076308a49a9bf8f.

The local official verifier checked original raw SHA, real external ledger,
review/authorization/preparation/qualification binding, classifications,
attempt counts and complete stop/NOT_RUN order. It returned VERIFIED for3
scientific attempts; its separate scope is0 new integration. No eligibility
artifact was reconstructed because stopping occurred before the challenge stage.
The machine analysis, provenance and verification receipts in this bundle link
the exact raw and append-only audit artifacts.

Source-bound archive:
shared_baseline_probes_v1_20261002T085338452324Z.tar.gz,
SHA256 ac7b3030de5b7283c006d9d3d806d42709196504ec664dba15fd7c619936fc2e.
All148 file members were checked against source bytes. The archive preserves
original absolute preparation/qualification references; no relocated portable
verifier execution is claimed.

This frozen campaign is closed. Continue only with read-only diagnosis of the
adapted MJPC baseline failure and assessment of what the observed pair means.
Any later physical investigation needs a new prospective task, budget and
corresponding admission; this closeout does not authorize replay of consumed
arms or a partial continuation of the stopped challenge catalog.

See [the frozen task](../../research/TASK_SHARED_BASELINE_PROBES_V1_20261002.md),
[PROJECT_RECORD](../../PROJECT_RECORD.md) and [SOP](../../research/SOP.md).
