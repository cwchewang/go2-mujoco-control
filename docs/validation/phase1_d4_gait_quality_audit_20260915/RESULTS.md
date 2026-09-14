# Phase1 D4 gait-quality audit

Classification: UNSTRUCTURED_INSTABILITY
Scope: active-relative [32.10, 39.90) s; period 0.14 s; 50 phase bins; prewindow [31.90, 32.10) s.
Parent evidence: deterministic D4 A/B closeout commit 0a9e977573081270b630119b0696cdedc03357a0.
Raw captures: reused only from /home/che/dev/go2-workspace/phase1-bounded-stance-dq-d4-deterministic-ab-20260914/example/cpp/experiments/_runs/phase1_d4_deterministic_ab_20260914/{A,B}.
Provenance: provenance.csv has all 12 required artifacts as MATCH, including exact bytes and SHA-256.
Execution: offline CSV analysis only; no simulator/controller, replay, D4/control/WBC/solver change, or new experiment was run.

## Decision

B maximum signed pitch is 18.9268 deg, but maximum angle alone is not the criterion. B roll/pitch are not phase-locked: explained variance is 0.01098/0.00784, median cycle-template correlation is 0.4484/0.3256, and pitch cycle ptp median/p95 is 5.0414/16.2956 deg.
The prepared structured-periodic rule therefore fails even though the progressive-ptp-drift rule is false. Contact quality also degrades materially, with no evidence of actuator saturation or solver failure.
This is UNSTRUCTURED_INSTABILITY, not DYNAMIC_GAIT_WITH_COST: the latter requires clear phase locking and repeatability before cost is considered.

## Attitude and phase structure

- A roll: mean/median/std 0.4720/0.5696/0.5275 deg; phase EV 0.6788; cycle correlation median 0.9785.
- A pitch: mean/median/std -0.4950/-0.4723/0.4540 deg; phase EV 0.6514; cycle correlation median 0.8902.
- B roll: mean/median/std 0.3998/0.3421/4.1716 deg; p05/p95 -6.0200/7.8874 deg; phase EV 0.0110; cycle correlation median 0.4484.
- B pitch: mean/median/std 1.6257/0.5183/4.7362 deg; p05/p95 -3.4001/13.4931 deg; phase EV 0.0078; cycle correlation median 0.3256.
- B pitch cycle-template RMSE p90 is 7.5946 deg; roll RMSE p90 is 6.5757 deg, with negative/low cycle-correlation tails.
- B pitch cycle-ptp slope is 0.1508 deg/s; its predicted window growth remains below the preregistered progressive-drift threshold, so the result is weakly structured rather than progressively diverging.

## Contact/slip

- Physical contact-count fractions A/B for 0/1/2/3/4 contacts are 0.2626/0.1151/0.6223/0/0 and 0.2000/0.4423/0.3436/0.0141/0.
- Expected WBC diagonal masks 6-or-9 are 0.9108 (A) versus 0.8697 (B); <=1-contact fraction is 0.3777 versus 0.6423.
- Touchdown events are 222 in A versus 177 in B; interval p95/max are 0.070/0.074 s versus 0.085/0.150 s. These event streams include same-timestamp multi-events and are supporting evidence, not a standalone instability criterion.
- Support-foot kinematics are valid for 0.0 of active rows in both arms; support speed median/p95/max are therefore unavailable, not zero-slip observations.
- Logged low-friction evidence is 0.0 in both arms. The contact loss/irregularity supports the instability classification, while a quantitative slip claim is not made.

## Actuation/solver

- WBC shadow, full SRBD, and full ID solver success fractions are 1.0 for both arms.
- WBC shadow/full-equation residual p95 is 2.4402e-05 (A) versus 2.7144e-05 (B).
- Effective PD+FF torque proxy RMS is 15.1575 versus 15.6526 Nm (+3.3%); p95 is 34.3509 versus 36.8548 Nm.
- Closure torque maxima are 26.8885 versus 29.3035 Nm, with p95 25.1003 versus 26.9478 Nm; both are 0.0 at the logged 45 Nm limit.
- D4 gate active fraction is 0.0 (A) versus 0.9464 (B); B nonzero scalar-s median is 0.3078, max applied delta-dq is 1.4747, and max kd-times-delta-dq is 4.0.
- Solver and saturation evidence do not indicate actuator-limit failure; the dominant quality boundary is weak attitude phase structure plus degraded contact organization.

## Required conclusions

1. The approximately 19-degree B pitch maximum is primarily unstructured instability, not organized periodic gait motion.
2. D4 remains a credible causal velocity-excess result from its parent A/B experiment, but B is not a qualified future locomotion-baseline gait without further qualification.
3. This audit does not justify or execute an additional live D4 experiment before obstacle-traversal work; any follow-up requires a separately authorized checkpoint.

## Provenance and implementation

- The analyzer was fixed only for existing-schema offline accounting: invalid support-foot rows are excluded from speed statistics, closure saturation is reported in Nm against 45 Nm, per-cycle closure/torque proxies are carried through, and touchdown/0--4-contact summaries are explicit.
- py_compile and the analyzer completed with classification=UNSTRUCTURED_INSTABILITY, structured=False, drift=False, costs=1, and no protocol errors.
- Generated tables are attitude_summary.csv, phase_folded.csv, cycle_summary.csv, contact_quality.csv, actuation_quality.csv, provenance.csv, and analysis.json.
- PNG phase folds are roll_deg_phase.png, pitch_deg_phase.png, world_base_z_m_phase.png, and contact_count_phase.png.
- No offline clip was generated; no safe state-only renderer was used or needed for this table-backed decision.

Closeout: commit and push this audit on research/phase1-d4-gait-quality-audit-20260915, then stop.
