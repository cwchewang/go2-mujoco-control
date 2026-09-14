# Phase1 stance Jacobian-consistent dq counterfactual

## Outcome

Result: **SUPPORTED**.

This is one offline same-state attribution checkpoint. No new MuJoCo trajectory, live A/B, gain scan, gait scan, controller behavior change, or follow-up experiment was executed.

## Hypothesis and unique variable

For controller-stance legs only, replacing the captured `dq_des` with the clamped Jacobian solution for a world-stationary support foot should reduce part of the forward instantaneous D contribution. The exact saved integration state, `q_des`, kp, kd, tau_ff, swing dq, WBC/SRBD/ID outputs, model, and contacts are unchanged; only stance-leg dq enters the candidate bridge formula.

Stance is defined only by the joined closure `solver_contact_mask`; the snapshot and replay physical contact masks are recorded separately for audit. The controller join uses the established nearest-row rule with a maximum 10 ms gap and produced 552 target snapshots.

## Frame and math audit

After restoring each saved state and calling `mj_forward`, the tool calls `mj_objectVelocity(model, data, mjOBJ_BODY, base_link, spatial, 1)`. MuJoCo documents this result as object-centered 6D velocity in `rot:lin` order; therefore `spatial[0:3]` is local body angular velocity and `spatial[3:6]` is local body linear velocity. With the repository FK `go2::FootPosition` at captured `q_des`, it forms `v_required = -(v_base_body + omega_body x r_foot_body_des)` and solves the repository `go2_control::FootJacobian` using a full 3x3 Eigen Jacobi SVD.

The solve is accepted only when rank is 3, condition number is at most `1e4`, and pre-clamp Cartesian residual is at most `1e-6 m/s`. The per-joint reference clamp is exactly `[-10,+10] rad/s`; the post-clamp residual is reported and is not hidden.

## Validation gates

The replay selected `552` snapshots. Maximum snapshot↔bridge ctrl residual is `0.000000000000 Nm`; maximum captured bridge-formula residual is `0.000000000000 Nm`; maximum ACTUAL restored-state `qacc[0]` residual is `0.000000000000 m/s²`; maximum candidate formula residual is `0.000000000000 Nm`.
Candidate invariants are exact within the recorded precision: max q/kp/kd/tau_ff change `0.000000000000`, max swing dq change `0.000000000000`, and same-state physical contact-mask mismatches `0`. Controller join maximum absolute gap is `10.000000 ms`.
There are `1100` controller-stance leg samples, `1100` valid solves, `0` invalid solves; invalid fraction is `0.000000`. `2010/3300` solved joints hit the reference clamp, fraction `0.609091`. Pre-clamp residual median/p95 is `0.000000`/`0.000000 m/s`; post-clamp residual median/p95/max is `2.136671`/`2.440575`/`2.592457 m/s`.

All numerical validation gates pass.

## Same-state causal result

Across all 552 snapshots, `delta_ax = qacc_candidate[0] - qacc_actual[0]` has median `-14.035764`, p05/p95 `-22.730600`/`0.000000 m/s²`, negative/positive fractions `0.926`/`0.000`, and median absolute effect `14.035764 m/s²`. Negative means the stationary-support dq candidate produces more instantaneous braking / less forward acceleration in the exact restored state.

Gait-phase strata:
- `[0,0.25)` n=159, median -18.161446, p05/p95 -23.859132/-4.983250 m/s², negative/positive 1.000/0.000
- `[0.25,0.5)` n=120, median -10.180747, p05/p95 -15.078719/-2.545581 m/s², negative/positive 1.000/0.000
- `[0.5,0.75)` n=155, median -15.529888, p05/p95 -22.629447/0.000000 m/s², negative/positive 0.735/0.000
- `[0.75,1)` n=118, median -11.107707, p05/p95 -16.971059/-3.379069 m/s², negative/positive 1.000/0.000

Controller contact-mask strata; `small-n` marks n<20:
- `mask0` n=41, median 0.000000, p05/p95 0.000000/0.000000 m/s², negative/positive 0.000/0.000
- `mask6` n=232, median -15.063706, p05/p95 -21.951267/-4.712922 m/s², negative/positive 1.000/0.000
- `mask9` n=240, median -15.032574, p05/p95 -23.540811/-3.021590 m/s², negative/positive 1.000/0.000
- `mask15` n=39, median -6.469298, p05/p95 -19.006095/-4.541174 m/s², negative/positive 1.000/0.000

Physical contact-mask strata are retained in `counterfactual_summary.csv` as an audit, not as the stance selector.

## Kinematic mismatch audit

For the `1100` valid controller-stance leg samples, the actual implied-minus-required foot-velocity x mismatch has median `-2.317585`, p05/p95 `-3.700819`/`0.393225 m/s`; vector-norm mismatch has median `3.517896`, p05/p95 `2.374082`/`4.537020 m/s`.

Per-leg full-sample mismatch, Jacobian conditioning, and post-clamp residual are in `leg_summary.csv`; per-sample singular values, rank, solve residual, unclamped/clamped dq, implied velocity, and mismatch are in `counterfactual_legs.csv`.

- `FR` n=279: x mismatch median/p05/p95 -2.223981/-3.696963/0.416771 m/s; norm median/p95 3.412276/4.462333 m/s; condition median/p95 4.026394/4.151776; post-clamp residual median/p95 2.233949/2.486320 m/s
- `FL` n=271: x mismatch median/p05/p95 -2.339186/-3.349634/0.356144 m/s; norm median/p95 3.624746/4.251789 m/s; condition median/p95 3.885265/4.015358; post-clamp residual median/p95 2.155467/2.401024 m/s
- `RR` n=271: x mismatch median/p05/p95 -2.428023/-3.494084/0.254295 m/s; norm median/p95 3.679501/4.302224 m/s; condition median/p95 4.006207/4.141094; post-clamp residual median/p95 2.061419/2.430054 m/s
- `RL` n=279: x mismatch median/p05/p95 -2.303397/-3.858024/0.459563 m/s; norm median/p95 3.382479/4.738944 m/s; condition median/p95 3.911994/4.018572; post-clamp residual median/p95 2.132426/2.419766 m/s

## D target and sensor-relative audit

`d_target_candidate - d_target_actual = kd*(dq_stationary_clamped - dq_actual)` is the only changed actuator term. The complete per-joint and phase-stratified distributions are in `d_target_summary.csv`; the table below highlights thigh joints.

- `FR_thigh` n=279: delta D-target median/p05/p95 -51.807302/-66.343250/-23.901687 Nm; actual dq-sensor median 1.930704 rad/s; candidate dq-sensor median -15.360511 rad/s
- `FL_thigh` n=271: delta D-target median/p05/p95 -53.409498/-65.628558/-30.793905 Nm; actual dq-sensor median 1.811977 rad/s; candidate dq-sensor median -15.642350 rad/s
- `RR_thigh` n=271: delta D-target median/p05/p95 -53.392669/-65.362525/-30.510114 Nm; actual dq-sensor median 2.796099 rad/s; candidate dq-sensor median -15.330281 rad/s
- `RL_thigh` n=279: delta D-target median/p05/p95 -52.279323/-66.326295/-20.076802 Nm; actual dq-sensor median 1.782973 rad/s; candidate dq-sensor median -15.070371 rad/s

Body-x attribution here comes only from exact same-state MuJoCo `qacc[0]`; individual joint torque signs are not interpreted as propulsion.

## Calibrated conclusion

The predeclared label is **SUPPORTED**. The candidate produces a strongly negative full-window instantaneous effect and passes all numerical gates; phase/contact strata and the clamp residual remain part of the audit. This is structural same-state evidence only, not closed-loop trajectory evidence and not authorization to modify the controller.

## Provenance and hashes

Analysis branch: `research/phase1-stance-jacobian-dq-counterfactual-20260914`; source HEAD at analysis: `644f5ba222d4c5fbd3fbbdeb74f4f529a01a43ec`.
Exact command: `./example/cpp/build/replay_stance_jacobian_dq unitree_robots/go2/scene_leg_lift_demo.xml /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual.csv docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual_legs.csv`.
Scene SHA256: `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`; replay binary SHA256: `d85c195ca74afc47d8f90c4ce6dc62a6747fd8bf9a9776e00e02f76d6d62fa1a`.

Source SHA256:
- `example/cpp/kinematics/go2_forward_kinematics.h`: `e83e9ca01d3ad91686e4cb554bdfbde94e3e9321d3df25d88f3c4b0f1014f4ad`
- `example/cpp/kinematics/go2_leg_jacobian.h`: `06a3c82d113eeb56b43aa20da4f16062212adc8e26301fb444d9b453105d383d`
- `example/cpp/tools/analysis/replay_bridge_atomic.cpp`: `3bf22eb2f4d740ba1daa31623c3527fc35c1fb0a9eb2d07869b03e908d069e67`
- `example/cpp/tools/analysis/replay_stance_jacobian_dq.cpp`: `e76ff48ddddb93de292a5c4b87bbf9d22ce05813229d048d6c4a7fcfeabb22a9`
- `example/cpp/tools/analysis/analyze_stance_jacobian_dq.py`: `924d70021846d4f22444ff2e0f88151f965b7361a65259c1d0964666ed20f397`
- `simulate/src/unitree_sdk2_bridge.h`: `2f6b6e76e4d067dff602ec1304228e9e66c44a37783f449b47af00e412b527bb`

Raw evidence SHA256:
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin`: `b6e17e79ec3fcf24895c122138c8e146118fc1820274e6e6e3bb334c5e619527`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv`: `a97190a3d8e08abaf1ad351e5bdb9bcd11d68a158238cd9a082a39696a592cb0`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv`: `8467468090dc61f6830d24fd3700916d479ed5ae402f0715c9703894b2bea21c`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/run_metadata.txt`: `390f277d2d6137a2da710ed66b8d5644c8e1c73e7b0225620cb28c251b50e2f1`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/run_manifest.json`: `953d2df6bbf07f46becd97125113eb7c5856a08ad09dd427001b38ad3d825848`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/environment.txt`: `cdc389432b3bef410b9e4a29a7135f79ff999776992f0b176b86bb7949fcbeb2`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/controller.log`: `6c3d89e8ecea82f002ace864302449968d50e9c986fcde4f1ad187b7326f81bc`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/simulator.log`: `22b4d09a64fabca39c1ade8d8f54569260b3b4a20fe8d1c7b27d15046fb1e4e5`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/contact_ground_truth.csv`: `82ba48480134f00ecf8139c858c1da0da283d0d684264fc6ba465a929127323d`

Derived outputs:
- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual.csv`
- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual_legs.csv`
- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/counterfactual_summary.csv`
- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/leg_summary.csv`
- `docs/validation/phase1_stance_jacobian_dq_counterfactual_20260914/d_target_summary.csv`

No new trajectory, live A/B, gain scan, gait scan, controller behavior change, or follow-up experiment was executed.

## Recommended next step (not executed)

Obtain separate approval for one minimal live A/B that changes only stance `dq_des` construction, keeps the exact position target and all other controller paths fixed, and uses the same endpoint and safety gates.
