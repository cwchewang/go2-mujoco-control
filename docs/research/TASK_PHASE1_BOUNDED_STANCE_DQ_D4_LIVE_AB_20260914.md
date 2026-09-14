# Task: Phase1 bounded stance-dq D4 live A/B — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first. Complete exactly one checkpoint, push it, then stop.

## Goal
Test exactly one live hypothesis: does the offline-selected `BOUND_D4` stance velocity-reference correction improve real 2.3 m/s closed-loop tracking while preserving stability?

Offline evidence at `b22ab67...` selected D4 as the smallest eligible correction. Do not test D2, D6, D90, RR-thigh-only, or the full stationary-support solution.

## Arms
A: unchanged baseline.

B: only during active-relative `[32.10,39.90)` and only for controller/WBC-stance legs, replace baseline joint `dq_des` with a bounded correction toward the world-stationary-support Jacobian solution.

For each active stance leg:
1. Let baseline velocity reference be `dq_base[3]`.
2. Compute `v_required = -(v_base_body + omega_body x r_foot_body_des)` using the current desired foot position corresponding to `q_des`.
3. Solve repository `FootJacobian(q_des) * dq_ss = v_required` with the same validity gates as the offline checkpoint: rank 3, condition <= 1e4, solve residual <= 1e-6 m/s.
4. `delta = dq_ss - dq_base`.
5. Apply one scalar to the whole leg: `s = min(1, 2/max|delta|, 4/max|kd*delta|)`; inactive zero denominators are ignored.
6. Write `dq_new = dq_base + s*delta` to all three joints of that stance leg.

Do not independently clip joints. Swing legs, invalid solves, all non-target times, stand/preflight/stop, and A must use baseline `dq_des` unchanged.

## Fixed variables
Do not change `q_des`, `kp`, `kd`, `tau_ff`, WBC/SRBD/ID, gait, shaper/governor, contact logic, model, scene, profile, torque/safety limits, or swing `dq_des`.

Use a default-off cached flag such as `TROT_BOUNDED_STANCE_DQ_D4_AB`.

Log enough to prove: enabled/gate state, controller contact mask, stance selector, baseline/solved/applied dq, scalar `s`, solve validity, baseline kd, per-joint `kd*(dq_new-dq_base)`, max `|Δdq|`, max `|ΔD_target|`.

## Run budget
Maximum 3 launches total: A, B, plus one replacement only for a demonstrable infrastructure/logging failure. Do not retry an unfavorable physical result.

Use the existing varying benchmark/profile and no explicit seed.

## A gate
Run A first. B is forbidden unless A:
- reaches active-relative >=40 s without hard safety stop;
- stays in continuous trot;
- has median `measured-applied` in `[+0.15,+0.35] m/s` over `[32.0,33.0)`;
- has negative median WBC desired ax, SRBD ax, and ID qdd_x over `[32.0,33.0)`.

If A physically fails this gate, stop.

## B isolation gate
Before interpreting tracking, confirm:
- correction exists only in `[32.10,39.90)`;
- only controller-stance `dq_des` changes;
- swing dq and all q/kp/kd/tau_ff paths are unchanged;
- every active correction satisfies max `|Δdq| <= 2 rad/s` and max `|kd*Δdq| <= 4 Nm`;
- invalid solves fall back to baseline dq.

## Metrics
Windows: pre `[31.90,32.10)`, early `[32.10,33.00)`, middle `[33.00,36.00)`, late `[36.00,39.90)`, full `[32.10,39.90)`.

Primary quantity: `velocity_excess = measured - applied`.

Primary comparison: `DID_excess = (B_full-B_pre) - (A_full-A_pre)`. Negative is improvement.

Pre-window comparability requires `|B_pre_excess-A_pre_excess| <= 0.03 m/s`.

Decision:
- `SUPPORTED` only if comparability passes, `DID_excess <= -0.02 m/s`, B has no hard safety failure, and 1.4→2.3 settling is not worse.
- `NOT SUPPORTED` if comparability and isolation pass but `DID_excess > -0.02 m/s` or settling is worse.
- `REJECTED FOR SAFETY` if B introduces a hard safety/posture failure absent in A.
- `INCONCLUSIVE` if comparability fails without a valid infrastructure explanation.

Also report measured/applied/excess, realized ax, overspeed peak, WBC/SRBD/ID ax, roll/pitch, contact-mask distributions, solver health, correction active fraction, `s` distribution, `|Δdq|`, `|ΔD_target|`, invalid solves.

## Outputs
Commit:
- `docs/validation/phase1_bounded_stance_dq_d4_live_ab_20260914/RESULTS.md`
- `docs/validation/phase1_bounded_stance_dq_d4_live_ab_20260914/ab.csv`

Record exact commands, run IDs, source SHA, controller/simulator hashes, scene/profile hashes, and raw evidence hashes. Push one checkpoint and stop. Do not automatically try another cap or candidate.