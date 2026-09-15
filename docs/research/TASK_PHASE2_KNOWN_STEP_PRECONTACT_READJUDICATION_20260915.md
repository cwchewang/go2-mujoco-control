# Phase2 offline checkpoint: readjudicate the 5 cm known-step A baseline with a geometry-valid pre-contact gate

Date: 2026-09-15
Prepared branch: `research/phase2-known-step-precontact-readjudication-20260915`
Parent closeout: `b11a7884c5e875c7ac7cf9dcf0a3c3a943b9be6e`
Frozen live A runtime HEAD: `df5d7663adc9e96d153107e071d7b49676bcdad6`
Frozen raw run: `example/cpp/experiments/_runs/phase2_known_step_5cm_wallclock_repair_20260915/A`

Read `docs/research/PHASE1_AGENT_CONTRACT.md`, `docs/research/TASK_PHASE2_KNOWN_GEOMETRY_5CM_STEP_20260915.md`, and `docs/research/TASK_PHASE2_KNOWN_STEP_WALLCLOCK_REPAIR_20260915.md` first.

## 1. Nature of this checkpoint

This is **offline analysis only**. Do not start MuJoCo, the controller, or any live process. Do not run B. Do not change the terrain adapter, scene, controller, runner, gait, WBC/MPC/ID, safety thresholds, or any runtime source.

The prior closeout remains historically correct under its preregistered gate: `BASELINE_GATE_FAILED`. This checkpoint asks whether that gate used an invalid geometric proxy for "pre-step" and therefore misclassified obstacle interaction as baseline instability.

## 2. Why the old gate is geometrically invalid

The old A gate treated `world_base_x_m < 0.65 m` as pre-step while the step leading edge is at `x=0.80 m`.

Repository geometry proves this is unsafe as a proxy:

- front hip x offset from base: `+0.1934 m` (`go2_forward_kinematics.h`);
- Cartesian-world foot target workspace permits another `+0.16 m` in x from the hip (`ClampFootToHipWorkspace`);
- foot collision sphere radius: `0.022 m` with geom margin `0.001 m` (`go2.xml`).

Thus a commanded/actual front foot can enter the step collision region substantially before the base reaches x=0.65 m. The repaired A reached raw base x=0.620934266 m before the hard-posture stop. Therefore the old gate cannot establish that the failure happened before obstacle interaction.

The old analyzer also defined active locomotion using `motion_stage==2 AND velocity_command_active`. This full2 checkpoint does not use runtime velocity commands, so `velocity_command_active` is not a valid activity predicate here. Do not use it in this readjudication.

## 3. Frozen evidence

Use only the existing A raw capture and its immutable logs/metadata from the run root above. Verify hashes against the wall-clock-repair closeout/provenance. If the raw capture is missing or hash-mismatched, classify `INSUFFICIENT_EVIDENCE` and stop.

Do not modify, truncate, regenerate, or replace raw data.

## 4. Geometry-valid clean pre-contact window

Define full2 locomotion rows as `motion_stage == 2`, regardless of `velocity_command_active`.

Define a conservative **clean pre-contact** row as all of:

1. `motion_stage == 2`;
2. `world_base_x_m <= 0.40 m`;
3. every available actual foot-center world x (`known_step_{fr,fl,rr,rl}_actual_x_m`) is `< 0.75 m`.

Rationale: even the commanded front-foot workspace maximum is approximately `0.1934 + 0.16 = 0.3534 m` ahead of base. At base x=0.40 m, adding the 0.022 m foot collision radius and 0.001 m geom margin reaches about x=0.7764 m, still below the x=0.80 m riser. The additional actual-foot-center <0.75 m rule makes the mask more conservative rather than less.

Require at least 250 clean pre-contact rows and at least 0.50 s of state-time span. Otherwise classify `INSUFFICIENT_EVIDENCE`.

## 5. Clean pre-contact health gate

Within the clean pre-contact window require all of:

- known-step adaptation disabled and zero adaptation-active samples;
- max absolute roll <= 0.25 rad;
- max absolute pitch <= 0.25 rad;
- no row crosses the controller hard-posture threshold (22 degrees; this is automatically implied by the 0.25 rad gate, but report both);
- where WBC diagnostics are valid, `wbc_full_srbd_ok == 1` and `wbc_full_id_ok == 1` on 100% of valid rows;
- WBC equality residual p95 <= 1e-3;
- at least 100 valid solver rows;
- no lockstep fail-closed or paired-HighState validation/fallback issue in the capture;
- source/runtime provenance still matches runtime HEAD `df5d7663adc9e96d153107e071d7b49676bcdad6` and the recorded controller/simulator/scene hashes.

Do not use final run status codes as a pre-contact gate because they summarize the later hard stop. Report them separately.

## 6. Contact-risk chronology

Independently derive the first **plausible foot-step contact-risk** row from actual foot geometry. For each leg, a plausible interaction with the 5 cm step begins when:

- actual foot-center x >= `0.80 - 0.022 = 0.778 m`, and
- actual foot-center z <= `0.05 + 0.022 = 0.072 m`.

Use actual world foot telemetry. Report first risk time, leg, foot x/z, and base x.

Also derive the first raw row whose abs roll or abs pitch exceeds the controller's 22-degree hard-posture threshold. Report its state time, roll/pitch, base x, and all foot x/z values.

Report the temporal ordering and delta between first plausible step-contact risk and first hard-posture crossing. Do not claim literal contact if the logger lacks geom-pair contact identity; call it `plausible_contact_risk`.

## 7. Required outputs

Create a new offline analyzer, preferably:

`example/cpp/tools/analysis/analyze_phase2_known_step_precontact_readjudication.py`

It must not invoke any runner or simulator.

Write:

- `docs/validation/phase2_known_step_precontact_readjudication_20260915/RESULTS.md`
- `analysis.json`
- `precontact_health.csv`
- `contact_risk_chronology.csv`
- `provenance.csv`

The results must include row counts, state-time span, max/p95 signed and absolute roll/pitch, solver success and residual stats, actual-foot x/z extrema, first plausible contact-risk event, first hard-posture event, and the old-vs-corrected activity predicate explanation.

## 8. Classification

Use exactly one:

- `PRECONTACT_BASELINE_HEALTHY_CONTACT_CONFOUNDED`: clean pre-contact health gate passes, and the hard-posture crossing occurs at or after the first plausible step-contact-risk event. This means the old base-x gate cannot support a baseline-instability claim and the frozen A may be eligible for reuse in a separately preregistered B-only checkpoint.
- `PRECONTACT_BASELINE_HEALTHY_ORDER_UNRESOLVED`: clean pre-contact health gate passes, but available telemetry cannot establish contact-risk vs hard-posture ordering.
- `PRECONTACT_BASELINE_UNHEALTHY`: clean pre-contact health gate fails on posture/solver/protocol/provenance before any plausible step contact.
- `INSUFFICIENT_EVIDENCE`: required raw evidence/columns are missing or the clean pre-contact window is too short.

Do not launch B in this checkpoint regardless of classification. A favorable result only authorizes the planner/reviewer to prepare a later B-only checkpoint.

## 9. Closeout

Commit analyzer and derived evidence only. Record that no live process was launched, no runtime source changed, and raw hashes match the frozen A capture. Push and stop.