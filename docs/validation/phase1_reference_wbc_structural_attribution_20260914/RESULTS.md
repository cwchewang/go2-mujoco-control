# Phase1 reference/WBC structural attribution

## Outcome

Result: **PARTIALLY SUPPORTED**.

This is an offline/source-analysis checkpoint only. No MuJoCo trajectory, live A/B, gain scan, controller behavior change, or new logging run was executed. The evidence supports a structural conflict mechanism as a contributor, but does not isolate it as the sole closed-loop root cause.

## Required conclusions

1. LowCmd `dq_des` is not an analytic task-space velocity solution. `BuildGaitTargets` first obtains body-frame foot targets from the running-trot kernel and maps them through `AllLegInverseKinematicsClamped`; `UpdateJointVelocityFeedforward` then computes each joint velocity as the finite difference `(joint_targets - previous_joint_targets) / motion_dt`, clamped to ±10 rad/s, when velocity feedforward is enabled. The same resulting joint dq array is written for stance and swing legs.
2. The harmful D marginal is mixed/context-dependent, with a net target-motion contribution larger than the sensor-damping contribution in this replay. Negative branch delta means removing that component lowers instantaneous base-x acceleration, so the removed D component had a forward marginal at that state.
3. The stance reference has a structural phase shape. For the actual running-trot kernel, `x_offset = start - direction * stance_travel * Smoothstep(u)`, `u=leg_phase/duty`, `stance_travel=step_length*duty`; after the established-gait blend, `dx/dt = -direction*(step_length/period)*6u(1-u)`. Its mean magnitude over stance is `v_nominal=step_length/period`, while its peak is `1.5*v_nominal` at `u=0.5`.
4. The kinematic and WBC paths demand incompatible behavior in part of the overspeed/braking window: the stance reference is tied to scheduled step/period and varies from zero to a 1.5× peak, while the WBC/SRBD/ID path uses measured body velocity and requests base-x braking. The code also treats commanded foot velocity differently: `commanded_body_feet_velocity_` enters the swing-foot WBC `v_des`, but the running full-WBC stance task uses foot position/velocity damping and does not use that commanded foot velocity.
5. The label is **PARTIALLY SUPPORTED**, not SUPPORTED: exact replay gates pass; D removal is net forward in aggregate and changes sign by phase/contact context; the stance-reference mismatch is present and largest in the phase-shaped mid-stance; however, the existing evidence is marginal same-state acceleration, not a closed-loop trajectory counterfactual, and it does not prove that the mismatch alone causes residual overspeed.
6. One next step, not executed: design and approve one same-state-plus-trajectory attribution that replaces only the stance reference velocity with the measured-speed-consistent stationary-support value while preserving foot positions, WBC targets, and all gates; then compare against the unchanged baseline.

## Side-by-side dependency graph

```text
runtime velocity -> ScheduleContinuousVelocityGait -> step/period/duty
  -> RaibertTrotKernel::Compute -> body-frame foot position x(t)
  -> IK -> joint q targets -> finite-difference joint dq_des
  -> LowCmd q,dq,kp,kd -> bridge tau_ff + kp*(q-q_sensor) + kd*(dq-dq_sensor)

applied/nominal body velocity -> velocity error -> SRBD desired acceleration/forces
  -> ID-WBC qdd/contact forces/tau -> LowCmd tau_ff -> same bridge PD formula

shared: applied/nominal speed, gait time/phase, body state, contact state, model
can disagree: scheduled foot trajectory/dq_des versus measured-speed base-x braking objective
```

## Stage 1 source trace

Path A: `example/cpp/trot/velocity_command.h:186-199` clamps the runtime speed, fixes period `0.14 s`, duty `0.44`, and sets `step_length=speed*period`. `trot_experiment_gait.cpp:200-211` installs those values into the kernel and disables the effective-speed convention. `raibert_trot_kernel.h` computes the schedule nominal as `direction_sign*step_length/period`, uses running-trot offsets FR/RL `0.0` and FL/RR `0.46`, and applies Smoothstep stance interpolation. `trot_experiment_gait.cpp:1493-1503` finite-differences the final body-frame foot targets for `commanded_body_feet_velocity_`; it is not an analytic IK velocity. `trot_experiment_gait.cpp` then performs IK, `trot_experiment_control.cpp:214-216` calls `UpdateJointVelocityFeedforward`, and `trot_experiment_control.cpp:1379-1397` finite-differences the joint targets. `WriteMotorCommands` writes the same q/dq to stance and swing motors; only kp/kd/tau_ff composition differs by WBC contact state. The bridge applies the PD formula in `simulate/src/unitree_sdk2_bridge.h`.
Path B: `trot_experiment_wbc.cpp:414-476` forms the SRBD input and uses `kernel_nominal_velocity_x_mps_` as the body velocity reference; `trot_experiment_wbc.cpp:520-560` passes the first SRBD acceleration into ID-WBC, with later velocity-task/braking logic in the same function. ID-WBC returns qdd/contact forces/tau; `PrepareWbcTorqueFeedforward` maps the motor rows to `wbc_torque_ff`, which is written as LowCmd `tau_ff` in `WriteMotorCommands`. `trot_experiment_wbc.cpp:780-822` confirms swing `v_des = linear_vel_world + R*(omega×r + commanded_body_feet_velocity)`, whereas the stance branch above it uses the actual foot velocity and position error/damping, not `commanded_body_feet_velocity_`.

## Stage 2 validation and D decomposition

The tool selected exactly `552` target snapshots from active-relative `[31.90,33.00)`. Atomic snapshot↔bridge ctrl maximum residual is `0.000000000000 Nm`; bridge formula maximum residual is `0.000000000000 Nm`; ACTUAL replay↔live `qacc[0]` maximum residual is `0.000000000000 m/s²`. Every branch calls `mj_setState` from the saved state before `mj_forward`, so branches are independently restored.
NO_D_ALL regression against the prior committed `components.csv` is `-7.086372995036299` versus `-7.086372995036301`, delta `0.000000000000002` m/s²: PASS.

Full target-window branch deltas (`qacc_branch[0] - qacc_ACTUAL[0]`; negative means the removed component was forward-contributing):

- `NO_D_ALL`: median -7.086373, p05/p95 -13.533229/0.528784, negative/positive fractions 0.940/0.060 m/s²
- `NO_D_TARGET_ALL`: median -3.360566, p05/p95 -13.451867/6.641507, negative/positive fractions 0.697/0.303 m/s²
- `NO_D_SENSOR_ALL`: median -1.199165, p05/p95 -13.394260/10.049390, negative/positive fractions 0.634/0.366 m/s²
- `NO_D_TARGET_THIGHS`: median -3.081571, p05/p95 -17.660968/8.974582, negative/positive fractions 0.587/0.413 m/s²
- `NO_D_SENSOR_THIGHS`: median -1.400455, p05/p95 -13.670085/16.340608, negative/positive fractions 0.543/0.457 m/s²

The target/sensor split is not additive by assumption: the two single-component removals are separate marginal replays. The full-window medians show a larger target-motion marginal than sensor-damping marginal, while phase/contact rows in `d_decomposition_summary.csv` retain the sign changes needed to call it mixed/context-dependent.

## Stage 3 structural attribution

For stance samples, the exact Smoothstep derivative reconstructs commanded body-frame foot x velocity with median `-2.553327` m/s and p05/p95 `-3.394753`/`-0.428209`. The measured-speed-consistent stationary-support approximation `v_foot,body,x ≈ -v_body,x` has median `-2.521986` m/s. The signed reference-minus-requirement disagreement has median `-0.066458` m/s and absolute median/p95 `0.749488`/`2.089313` m/s.

The disagreement stratification is descriptive, not a newly selected acceptance threshold. Using `|disagreement|=0.5 m/s` only to separate the existing samples, the NO_D_ALL removal delta is:

- low-disagreement `n=163`: median -7.240788, p05/p95 -11.073182/-2.026987, negative/positive fractions 0.994/0.006 m/s²; target/sensor `-4.286082`/`-0.278297` m/s²
- high-disagreement `n=309`: median -7.131437, p05/p95 -13.347931/0.782437, negative/positive fractions 0.896/0.104 m/s²; target/sensor `-4.304009`/`-0.907340` m/s²

The high-disagreement group has the stronger forward D marginal when its NO_D delta is more negative, but the per-phase/contact CSV is the audit trail: sign and magnitude remain context-dependent. Thigh `dq_des-dq_sensor` stance medians by FR/FL/RR/RL are `2.694302/2.050782/2.900043/2.196346` rad/s; swing medians are `0.084035/1.938099/0.636570/-0.005262` rad/s.

## Prior evidence boundary

The atomic snapshot and matching closure are from the validated bridge-atomic checkpoint `6cd37e02385eaa98a1ea75002b21378a70120740`; the prior replay gates and NO_D baseline are retained as evidence. This checkpoint does not reinterpret the prior live D90/RR-thigh failures and does not claim a closed-loop improvement from any same-state branch.

## Provenance and hashes

Analysis branch: `research/phase1-reference-wbc-structural-attribution-20260914`; source HEAD at analysis: `ccf78bf975e0084443719b0ae043fd74b6a2dcaf`.
Primary evidence run: `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049`; snapshot records are selected only by the existing atomic join to closure ticks within 10 ms and active-relative `[31.90,33.00)`.
Offline replay binary SHA256: `d1edbe4ebb08e92ad7941b5d57f384beed9bcb3fc6ce90016782dddcb91fd08d`.

Source SHA256:
- `example/cpp/trot/velocity_command.h`: `e871a36f3f4db83e034a0a554a0e0f2f6242c1a7ea5854dd18af587d28f62e5f`
- `example/cpp/gait/raibert_trot_kernel.h`: `456bb9484e7d4e051567a8609ee99e40a15a9288688af9e31bb385a9ebc6e669`
- `example/cpp/gait/locomotion_kernel.h`: `6ed29d2c38e55f4fdc680c3b5150b35ec70ea042f1aa4e9e7ae07397f88fc5f4`
- `example/cpp/trot/trot_experiment_gait.cpp`: `8c286b6910735cbae0dfef31653683fd80fb9fddcb91d0a14c6e4c2ecd02aa9b`
- `example/cpp/trot/trot_experiment_control.cpp`: `634d525f8643136ed48c93ca21ec504c81f5d0048f2d87a2aa22b76a7eb1aa27`
- `example/cpp/trot/trot_experiment_wbc.cpp`: `fa79d23080ae7e46ef795a9e38f200be651ee28e0a14850de86239cb1f8ab6bc`
- `simulate/src/unitree_sdk2_bridge.h`: `2f6b6e76e4d067dff602ec1304228e9e66c44a37783f449b47af00e412b527bb`
- `example/cpp/tools/analysis/replay_pd_d_decomposition.cpp`: `fd47cf74d0c07a07da2c0e6c15455e8dbbf4e590f51af583e937d9c3a25ad8c3`

Raw/derived evidence SHA256:
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin`: `b6e17e79ec3fcf24895c122138c8e146118fc1820274e6e6e3bb334c5e619527`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv`: `a97190a3d8e08abaf1ad351e5bdb9bcd11d68a158238cd9a082a39696a592cb0`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv`: `8467468090dc61f6830d24fd3700916d479ed5ae402f0715c9703894b2bea21c`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/run_metadata.txt`: `390f277d2d6137a2da710ed66b8d5644c8e1c73e7b0225620cb28c251b50e2f1`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/run_manifest.json`: `953d2df6bbf07f46becd97125113eb7c5856a08ad09dd427001b38ad3d825848`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/environment.txt`: `cdc389432b3bef410b9e4a29a7135f79ff999776992f0b176b86bb7949fcbeb2`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/controller.log`: `6c3d89e8ecea82f002ace864302449968d50e9c986fcde4f1ad187b7326f81bc`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/simulator.log`: `22b4d09a64fabca39c1ade8d8f54569260b3b4a20fe8d1c7b27d15046fb1e4e5`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/contact_ground_truth.csv`: `82ba48480134f00ecf8139c858c1da0da283d0d684264fc6ba465a929127323d`
- `/home/che/dev/go2-workspace/phase1-reference-wbc-structural-attribution-20260914/docs/validation/phase1_pd_component_decomposition_20260914/components.csv`: `4b2e095fd01902d15f3262ad93089c9a85002bd29166ba3a971e51b3b1ed43c8`

Committed derived outputs:
- `docs/validation/phase1_reference_wbc_structural_attribution_20260914/d_decomposition.csv`
- `docs/validation/phase1_reference_wbc_structural_attribution_20260914/d_decomposition_summary.csv`
- `docs/validation/phase1_reference_wbc_structural_attribution_20260914/kinematic_attribution.csv`
- `example/cpp/tools/analysis/replay_pd_d_decomposition.cpp`
- `example/cpp/tools/analysis/analyze_reference_wbc_structural_attribution.py`

No new trajectory, live A/B, gain scan, controller behavior change, WBC rewrite, acceptance change, or follow-up experiment was executed.
