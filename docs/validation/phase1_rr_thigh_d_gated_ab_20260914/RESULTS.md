# Phase1 RR-thigh D gated A/B checkpoint

## Outcome

This is one completed checkpoint for the pre-registered RR-thigh D attenuation hypothesis. Arm A is the baseline. Arm B attenuates only the effective RR-thigh (`motor 7`) D gain to `0.75 * baseline` when both gates are true:

- active-relative time `[32.10, 32.60)` seconds;
- gait phase `[0.50, 0.75)` using the controller's `period_s=0.14` clock.

No kp, q, dq, tau_ff, other motor, gait, shaper, governor, Raibert, preview, WBC, SRBD, ID, contact, model, scene, limit, profile, or threshold setting was changed. The flag is default-off and cached at initialization.

## Phase gate and execution

The A phase gate passed before B was launched. In A, 551 active continuous-trot controller ticks covered `[31.90,33.00)`. The logged `rr_thigh_d_gate_time_s` matched `diag_active_relative_time_s` with maximum absolute error `0`; logged phase matched the offline `fmod(active_time/0.14,1)` phase with maximum wrapped error `4.286311305889967e-10`. The hypothetical target phase contained 72 samples and A had zero active gate samples.

Exactly two launches were made, A first and B second; no third launch or follow-up experiment was made. Both runs reached the target window, stayed in the continuous-trot regime, and completed without safety stop. Metadata statuses for both runs were `controller=0`, `safety=0`, `quality=0`, `analysis=0`, `ground_truth=0`, `dynamics=0`, and `completion=0`.

## Gate audit

The B log contains 70 active gate samples. They span logged gate time `32.131997241` to `32.583994567` seconds and phase `0.500007800` to `0.742851450`; the logged scale is exactly `0.75`, and `kd_effective/kd_baseline` is exactly `0.75` for all active samples. All B gate-active samples are inside the declared time and phase gate. Outside the active gate, the logged scale is `1.0`.

The branch is isolated to motor index 7 (`RR_thigh`) in both WBC and fallback command paths. The source records baseline/effective kd and leaves kp, q, dq, and tau_ff assignments unchanged. A's controller log records `RR-thigh D gated A/B=disabled`; B's records `...=enabled`, both with the declared gate and motor.

## Time-aligned results

Values below are medians unless a percentile or fraction is explicitly shown. `realized_ax` is the local 100 ms ordinary-least-squares slope of measured velocity. `velocity_excess` is measured minus applied velocity. Pairwise deltas are `B-A`, using B active-relative timestamps and linear interpolation of A.

| window | arm | n | measured m/s | applied m/s | excess m/s | realized ax m/s2 | ax p05..p95 | WBC ax | SRBD ax | ID qdd_x | RR D Nm | kd base -> eff | roll/pitch abs p95 deg | physical mask | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pre `[31.90,32.10)` | A | 100 | 2.519653 | 2.276656 | 0.242674 | 0.208303 | -0.122331..0.427164 | -2.426740 | -1.627608 | -2.201466 | -0.233670 | 3.166068 -> 3.166068 | 1.277/1.319 | 6 | off |
| pre `[31.90,32.10)` | B | 100 | 2.517531 | 2.280229 | 0.237019 | 0.153119 | -0.185468..0.369233 | -2.370191 | -1.654583 | -2.148367 | -0.872480 | 3.165544 -> 3.165544 | 0.931/1.257 | 6 | off |
| intervention `[32.10,32.60)` | A | 250 | 2.530646 | 2.269354 | 0.261292 | -0.025840 | -0.230809..0.296860 | -2.612915 | -1.636191 | -2.283356 | 9.600509 | 3.292031 -> 3.292031 | 0.938/1.167 | 9 | off |
| intervention `[32.10,32.60)` | B | 249 | 2.527030 | 2.272970 | 0.254059 | 0.009987 | -0.150501..0.170855 | -2.540591 | -1.463516 | -2.236655 | 9.532938 | 3.291869 -> 3.073710 | 0.880/1.041 | 9 | 28.11% |
| gated phase `[0.50,0.75)` | A | 72 | 2.518842 | 2.281158 | 0.237684 | -0.087423 | -0.223932..0.201873 | -2.376840 | -0.859117 | -2.227051 | 30.647268 | 3.441418 -> 3.441418 | 1.244/1.196 | 0 | 0% |
| gated phase `[0.50,0.75)` | B | 70 | 2.519259 | 2.280741 | 0.238519 | 0.005089 | -0.108069..0.095202 | -2.385187 | -0.465245 | -2.397946 | 28.767232 | 3.428986 -> 2.571739 | 1.076/0.875 | 0 | 100% |
| other phase | A | 178 | 2.532956 | 2.267044 | 0.265913 | -0.004814 | -0.230761..0.313442 | -2.659130 | -1.694093 | -2.326470 | 1.177250 | 3.186244 -> 3.186244 | 0.675/1.163 | 9 | 0% |
| other phase | B | 179 | 2.529689 | 2.270311 | 0.259378 | 0.018324 | -0.156385..0.173625 | -2.593782 | -1.463516 | -2.173072 | 1.548745 | 3.186152 -> 3.186152 | 0.617/1.099 | 9 | 0% |
| recovery `[32.60,33.00)` | A | 201 | 2.524132 | 2.275868 | 0.248264 | 0.063953 | -0.465357..0.299512 | -2.482638 | -1.803564 | -2.264952 | 8.589262 | 3.270391 -> 3.270391 | 1.580/1.637 | 9 | 0% |
| recovery `[32.60,33.00)` | B | 201 | 2.524253 | 2.275747 | 0.248507 | 0.054394 | -0.384557..0.244980 | -2.485068 | -1.694320 | -2.217199 | 7.722879 | 3.270388 -> 3.270388 | 1.089/1.442 | 9 | 0% |

## Primary A/B effects

| window | paired n | delta realized ax B-A m/s2 | delta ax p05..p95 | delta velocity excess B-A m/s | delta measured velocity B-A m/s |
|---|---:|---:|---:|---:|---:|
| pre | 100 | -0.057062 | -0.088575..-0.016161 | -0.005271 | -0.002636 |
| intervention | 249 | -0.004795 | -0.145913..0.160206 | -0.003831 | -0.001916 |
| gated phase | 70 | +0.097841 | -0.105949..+0.165208 | +0.003214 | +0.001607 |
| other phase | 179 | -0.034606 | -0.160885..+0.141927 | -0.008049 | -0.004024 |
| recovery | 201 | +0.027719 | -0.185229..+0.107286 | +0.006111 | +0.003055 |

In the declared gated phase, B did not reduce velocity excess: the paired median excess moved slightly upward by `+0.003214 m/s`. The paired realized acceleration moved by `+0.097841 m/s2`, which is the opposite of the desired additional braking direction when interpreted against A's negative gated acceleration. The effect distribution crosses zero (`p05=-0.105949`, `p95=+0.165208 m/s2`), so this is a small, non-robust change rather than evidence of benefit. Physical and diagnostic contact-mask modes match in the gated phase (`0` for both arms); posture remains comparable and both runs remain safe.

## Decision

**NOT SUPPORTED.** The pre-registered RR-thigh D attenuation did not improve the velocity-excess endpoint and did not show a robust braking improvement in its gated phase. The clean gate audit and matching gated contact mask avoid an implementation-confound explanation, but the small cross-zero effect is insufficient for promotion.

Next step, not executed: register one new checkpoint for a different RR-thigh D candidate only if a future task explicitly authorizes it; do not promote this `0.75` attenuation.

## Provenance

- Branch: `research/phase1-rr-thigh-d-gated-ab-20260914`
- Run-time git head for both arms: `d61d7b02098171cb1f908c559d7e8e4d32339a15`; both manifests record `git_dirty=true` because the default-off experiment diff was uncommitted at launch.
- A run ID: `varying_20260914_065525`; B run ID: `varying_20260914_065915`.
- Profile: `example/cpp/configs/phase1_velocity_varying.csv`, SHA256 `9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74`.
- Scene: `unitree_robots/go2/scene_leg_lift_demo.xml`, SHA256 `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.
- Simulator: `simulate/build/unitree_mujoco`, SHA256 `a28995d205e161661824ccd118b41ebb22e9cfa5b338e4a793701cee118cb370`.
- Controller: `example/cpp/build/real_trot_go2`, SHA256 `124f5d3dd921a57c2293bb068c5735a72410696fa4ad6eb3bb824efef080b7d1`.
- A data: `example/cpp/experiments/_runs/phase1_rr_thigh_d_gated_ab_20260914/varying_20260914_065525/data.csv`, SHA256 `1779158c8326ccb3ab8c1958035b34a3b065f87ef0f091c1d27f89afbef30399`.
- B data: `example/cpp/experiments/_runs/phase1_rr_thigh_d_gated_ab_20260914/varying_20260914_065915/data.csv`, SHA256 `d02c50cb913cd06342a4d7c05305e20ecdcb7287938b7cf4b2ff85ce2a2450b0`.
- A manifest: `run_manifest.json`, SHA256 `9c3b99857dbd4ac2dad108bfeb511c035dc549fe776909e083d7cd5ef141daea`.
- B manifest: `run_manifest.json`, SHA256 `28b3a4561f44ff5da8d1cf0c86ab3a5dc6cb77e97a73a707f2e88f267099c78d`.
- A controller log SHA256 `9d167f16d6e760a25dc1ef49acce51bbce7f23eb0a3b8cca3792a58550add8ee`; B controller log SHA256 `fd2364a471fe1c395263c2f2dca7f8121481c0aba62ecf324418af83d3945f8c`.
- Derived comparison: `ab.csv`, SHA256 `e7efdc7a2ba949bf477237fa44b90bbd991a25cc2b13c44dc23194a2a0977157`.

The exact run command for both arms was the repository's `run_phase1_velocity_benchmark.sh varying` entry point with `TROT_CPU_AUTOPIN=1`, `TROT_DIAG_ID_CLOSURE=1`, profile `phase1_velocity_varying.csv`, output root `_runs/phase1_rr_thigh_d_gated_ab_20260914`, domain `232`, and arm flag `TROT_RR_THIGH_D_GATED_AB=0` for A or `=1` for B. Build commands were `cmake -S simulate -B simulate/build -DCMAKE_BUILD_TYPE=Release && cmake --build simulate/build --target unitree_mujoco -j2` and the corresponding `example/cpp` command for `real_trot_go2`.

No new simulator trajectory, parameter scan, retry, or follow-up action was executed after this checkpoint.
