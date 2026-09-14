# Phase1 D4 deterministic live A/B — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first.

Base evidence SHA: `6970d3c9406a4297cb67a4a397e8b84335732d25`.
Branch: `research/phase1-bounded-stance-dq-d4-deterministic-ab-20260914`.
Prerequisite accepted: `FIX_VALIDATED_FULL_BASELINE_REPRODUCIBLE`.

Goal: repeat exactly the previously inconclusive bounded stance-dq D4 live A/B after fixing baseline determinism. The old result at `e65c8830905c2c744c85d82ec08c3e4b7f6989c4` is historical only; its causal comparison was invalid because pre-window comparability failed.

A = deterministic baseline with D4 off. B = the inherited `TROT_BOUNDED_STANCE_DQ_D4_AB=1` implementation. Do not change D4 math: only in active-relative `[32.10,39.90)`, only controller/WBC stance legs, solve the existing stationary-support Jacobian target and apply the inherited whole-leg scalar `s=min(1,2/max|delta|,4/max|kd*delta|)`. Swing legs, invalid solves, A, and all times outside the gate remain baseline. Do not change q/kp/kd/tau_ff, WBC/SRBD/ID, gait, velocity profile, solver, model, scene, safety limits, or the validated HighState-pairing repair.

All live runs must use `SIM_LOCKSTEP=1` and `TROT_LOCKSTEP_PAIRED_HIGHSTATE=1`. Exactly two launches are authorized: A, then B only if A gate passes. No retries, replacement IDs, extra replicates, tuning, or other interventions.

A gate: protocol/pairing gates pass; all status codes are zero; active-relative reaches >=40 s; motion stage remains locomotion in `[32,40)`; median measured-minus-applied in `[32,33)` is within `[+0.15,+0.35] m/s`; median WBC requested ax, SRBD ax and ID qdd-x in `[32,33)` are negative; no hard-safety marker. Use the prepared analyzer with `--a-gate-only` before launching B.

Because baseline determinism is now exact, pre-intervention comparability is also exact, not the old ±0.03 rule. Over `[31.90,32.10)`, A and B must have identical row count/timestamps and identical preregistered causal fields: state/control clocks; requested/shaped/applied/measured velocity; body/world velocity; IMU attitude/gyro; WBC/SRBD/ID longitudinal quantities; contacts; and all 12 active motors' q target, dq target, kp, kd, tau_ff, q state and dq state. D4 diagnostic enabled metadata may differ. Any causal difference => `INCONCLUSIVE_PREWINDOW_DIVERGENCE`.

B isolation: A has no correction; B correction is nonzero only in `[32.10,39.90)`; outside gate every applied dq equals baseline dq; non-stance legs never change dq; max applied `|delta dq| <=2 rad/s`; max `|kd*delta dq| <=4 Nm`; invalid solves fall back to baseline; paired HighState has zero validation failures and zero async fallbacks.

Windows: pre `[31.90,32.10)`, early `[32.10,33.00)`, middle `[33,36)`, late `[36,39.90)`, full `[32.10,39.90)`. Primary quantity is velocity excess = measured - applied. Primary statistic: `DID_excess=(B_full-B_pre)-(A_full-A_pre)`. Negative is improvement. Report posture, contacts, solver health, correction activity/scalar/caps, overspeed and WBC/SRBD/ID quantities as secondary evidence.

Settling guard: derive the 1.4→2.3 transition from applied command reaching >=2.29 m/s. Settled means measured stays within ±0.15 m/s of applied for >=0.5 s. B is not worse if its settling <= A +0.25 s. If A never settles, a finite B settling is not worse; if A settles and B never does, B is worse.

Decision labels:
- `SUPPORTED`: all gates pass, B safe, DID <= -0.02 m/s, settling not worse.
- `NOT_SUPPORTED`: gates pass but DID > -0.02 or settling worse.
- `REJECTED_FOR_SAFETY`: B introduces a hard safety/posture failure absent in A.
- `INCONCLUSIVE_PREWINDOW_DIVERGENCE`: deterministic pre-window gate fails.
- `BASELINE_GATE_FAILED`: A gate fails.
- `PROTOCOL_FAILURE`: pairing/lockstep/provenance consistency fails.

Execution: verify branch/head/clean; audit inherited D4 definition; run relevant focused pairing/lockstep tests; run `bash example/cpp/scripts/run_phase1_d4_deterministic_ab.sh A`; run the prepared analyzer with `--a-gate-only`; only on PASS run the same runner with `B`; then run full analyzer; close out and push. Do not start any follow-on experiment.

Required validation directory: `docs/validation/phase1_d4_deterministic_ab_20260914/` containing `RESULTS.md`, `ab.csv`, `prewindow_exact.csv`, `isolation.csv`, `protocol_gates.csv`, and `provenance.csv`. Raw artifacts stay local/immutable and must be hashed.