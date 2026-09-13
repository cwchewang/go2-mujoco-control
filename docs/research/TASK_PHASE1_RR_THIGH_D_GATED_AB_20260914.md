# Phase1 RR-thigh D gated A/B

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first.

## Question
Does a small attenuation of the RR-thigh derivative term improve the known 1.4→2.3 m/s residual overspeed without materially harming gait stability?

## Prior evidence
Use checkpoint `bab9f56288dd74734a91945117d94c74c8b4d32f`. The validated same-state replay showed RR-thigh D removal has its cleanest harmful marginal in gait phase `[0.5,0.75)`: n=155, median delta_ax=-4.021328 m/s², 100% negative. Do not broaden the target to other joints or phases.

## Single variable
Build one binary for both arms.

A: baseline behavior.

B: only inside active-relative `[32.10,32.60)` and gait phase `[0.5,0.75)`, set RR-thigh (motor index 7) effective kd to `0.75 * baseline_kd`.

Everything else stays unchanged: kp, q/dq targets, tau_ff, every other joint, gait semantics, period/duty, shaper/governor, Raibert/preview, WBC/SRBD/ID, contact logic, model, scene, torque limits, profile and acceptance thresholds.

Do not scan attenuation values. `0.75` is the only B setting.

Use a default-off flag cached outside the hot loop. Record whether the gate is active and the applied kd scale.

## Phase gate
Before B, use A logs to verify that the runtime phase used by the intervention is equivalent to the Phase1 active gait phase used by the offline replay. If the phase semantics do not match at controller-tick resolution, stop and do not run B.

## Runs
Run A first. A must reach active 33 s, remain safe, reproduce the known overspeed/braking-mismatch regime, and pass the phase gate. Only then run B once.

Maximum 3 launches total; a third is allowed only to replace an infrastructure-invalid launch. Do not retry a genuine B instability.

## Verify B
Prove from logs that B changes only RR-thigh kd, only in the declared time/phase gate; kp, q/dq targets and tau_ff stay unchanged; normal kd returns outside the gate; all other motors are untouched.

## Compare
Time-align A/B and report:

- pre `[31.90,32.10)`
- intervention `[32.10,32.60)`
- recovery `[32.60,33.00)`
- within intervention, gated phase samples vs other phases

For each arm report requested/shaped/applied/measured velocity, measured-applied error, realized x acceleration using the established 100 ms local fit, WBC desired ax, SRBD ax, ID qdd_x, RR-thigh P and D contributions, effective kd, tau_ff/effective command, contact masks, roll/pitch and run status.

Primary effect sizes are `realized_ax_B-realized_ax_A` during gated samples and the A/B change in velocity excess through intervention/recovery.

Classify SUPPORTED only if braking/velocity excess improves with sufficiently comparable posture/contact. Use NOT SUPPORTED if it worsens or has little effect. Use INCONCLUSIVE if contact/posture changes confound the result. A safety stop after intervention begins is a valid result; do not retry it for a nicer outcome.

Do not tune anything after this A/B.

## Output
Commit one checkpoint with:

`docs/validation/phase1_rr_thigh_d_gated_ab_20260914/RESULTS.md`

`docs/validation/phase1_rr_thigh_d_gated_ab_20260914/ab.csv`

plus the minimal default-off source diff. Record run IDs and hashes. State one next step only, do not execute it. Push and stop.