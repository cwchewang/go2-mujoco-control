# Phase1 four-thigh D symmetric offline screen

## Outcome

This checkpoint is offline-only. It reuses the exact 552 target snapshots from the validated bridge-atomic replay and performs `mj_forward` counterfactuals only. No MuJoCo trajectory, live A/B, gain scan, or follow-up run was executed.

The four thigh motors use repository order indices `1, 4, 7, 10`: `FR_thigh`, `FL_thigh`, `RR_thigh`, and `RL_thigh`. The candidates are exactly:

| candidate | retained D contribution | attenuation applied to each thigh D term |
|---|---:|---:|
| `THIGH_D_90` | 90% | 10% |
| `THIGH_D_80` | 80% | 20% |
| `THIGH_D_70` | 70% | 30% |

For each candidate and snapshot, control was independently rebuilt from the exact atomic ACTUAL command as `ctrl_candidate_i = ctrl_actual_i - attenuation_fraction * kd_i * (dq_des_i - dq_sensor_i)` only for indices `1,4,7,10`. All other controls, P, tau_ff, q/dq targets, state, contacts, model, and inputs remained unchanged.

## Validation gates

| gate | result |
|---|---:|
| atomic bridge binding, max `abs(snapshot_ctrl - bridge_ctrl)` | PASS, `0` |
| bridge formula, max `abs(tau_ff + P + D - ctrl)` | PASS, `0` |
| ACTUAL replay, `qacc[0]` versus live, 552/552 | PASS, max residual `0 m/s2` |
| candidate isolation, non-thigh zero and thigh exact scaled-D delta | PASS, max residual `3.5527136788005009e-15 Nm` |
| independent state restore before ACTUAL and every candidate | PASS by construction |

No candidate branch feeds another branch or the live trajectory. The tool terminated on any failed gate; all gates passed before metrics were written.

## Full-window results

Target window is active `[31.90,33.00)`, `n=552`. `delta_ax = qacc_candidate_x - qacc_actual_x`; negative is the desired instantaneous braking direction.

| candidate | median delta_ax | p05 | p95 | fraction negative | fraction positive | median abs |
|---|---:|---:|---:|---:|---:|---:|
| `THIGH_D_90` | -0.552166 | -1.653378 | +0.247770 | 91.12% | 8.88% | 0.563019 |
| `THIGH_D_80` | -1.111000 | -3.283666 | +0.451437 | 90.22% | 9.78% | 1.128617 |
| `THIGH_D_70` | -1.646616 | -4.915920 | +0.674004 | 87.68% | 12.32% | 1.688871 |

The full-window statistics are same-state instantaneous effects only; they are not trajectory-stability or closed-loop tracking evidence.

## Physical contact-mask stratification

The table reports `n`, median `delta_ax`, and fraction negative. The task small-n rule is `n < 20`; only mask `1` is small-n and is excluded from promotion decisions.

| mask | `THIGH_D_90` | `THIGH_D_80` | `THIGH_D_70` |
|---|---:|---:|---:|
| `0`, n=129 | -1.127799, 100.00% | -2.319348, 100.00% | -3.479021, 100.00% |
| `1`, n=3, small-n | -0.889571, 100.00% | -1.779061, 100.00% | -2.668298, 100.00% |
| `4`, n=43 | -0.362149, 79.07% | -0.724156, 76.74% | -0.766505, 69.77% |
| `6`, n=170 | -0.588049, 96.47% | -1.175414, 95.88% | -1.755082, 94.12% |
| `8`, n=24 | -0.513033, 100.00% | -1.025761, 100.00% | -1.538198, 100.00% |
| `9`, n=183 | -0.318277, 81.42% | -0.636543, 79.78% | -0.954798, 75.41% |

Every non-small contact-mask median is negative for all three candidates.

## Gait-phase stratification

Each row reports `n`, median `delta_ax`, and fraction negative. All phase strata are non-small.

| phase | `THIGH_D_90` | `THIGH_D_80` | `THIGH_D_70` |
|---|---:|---:|---:|
| `[0,0.25)`, n=159 | -0.744309, 88.68% | -1.490120, 88.68% | -2.236368, 86.79% |
| `[0.25,0.5)`, n=120 | -0.383051, 86.67% | -0.766023, 84.17% | -1.149101, 80.00% |
| `[0.5,0.75)`, n=155 | -0.788548, 90.32% | -1.593014, 89.03% | -2.389521, 85.16% |
| `[0.75,1)`, n=118 | -0.581216, 100.00% | -1.164749, 100.00% | -1.747071, 100.00% |

Every non-small phase-bin median is negative for all three candidates.

## Approximate monotonicity

The simple expectation for increasing attenuation magnitude is `delta_ax_90 >= delta_ax_80 >= delta_ax_70`, without assuming linearity. This ordering holds for `472/552` snapshots and is violated for `80/552` (`14.4928%`). Positive-sign counts, where a candidate is not in the desired negative direction, are `49/552` (`8.8768%`) for `THIGH_D_90`, `54/552` (`9.7826%`) for `THIGH_D_80`, and `68/552` (`12.3188%`) for `THIGH_D_70`.

The larger attenuations strengthen the median negative effect but also increase the positive tail and sign violations. This is an approximate ordering audit, not a linearity claim.

## Promotion rule and decision

The pre-registered rule requires full-window median `< -0.25 m/s2`, fraction negative `>=70%`, non-small phase medians `<=0`, non-small contact-mask medians `<=0`, and no smaller candidate also satisfying all rules.

All three candidates satisfy the first four conditions. `THIGH_D_90` is the smallest attenuation magnitude among the allowed candidates and already satisfies all conditions. Therefore the result is:

**RECOMMENDED FOR ONE FUTURE LIVE A/B: `THIGH_D_90` (10% symmetric attenuation on all four thigh D contributions).**

This is only a same-state offline screen. It does not establish closed-loop benefit, gait stability, or a controller fix. The recommended live A/B was not executed.

Next step, not executed: run one separately pre-registered safety-gated live A/B for `THIGH_D_90`, with no gain scan or additional candidate.

## Provenance and reproduction

- Branch: `research/phase1-four-thigh-d-offline-screen-20260914`.
- Starting checkout: `846124309d13007f1c4bfd4754668967bb51880a`.
- Snapshot source: `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin`, SHA256 `b6e17e79ec3fcf24895c122138c8e146118fc1820274e6e6e3bb334c5e619527`.
- Diagnostic closure: `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv`, SHA256 `8467468090dc61f6830d24fd3700916d479ed5ae402f0715c9703894b2bea21c`.
- Scene/model: `unitree_robots/go2/scene_leg_lift_demo.xml`, SHA256 `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.
- Replay source: `example/cpp/tools/analysis/replay_four_thigh_d_screen.cpp`, SHA256 `c5ad85d695ec3b65ef541c4ea278c12b6f8a1f49ff59e2ba44f20b4f2f895c47`.
- Reused bridge source: `example/cpp/tools/analysis/replay_bridge_atomic.cpp`, SHA256 `3bf22eb2f4d740ba1daa31623c3527fc35c1fb0a9eb2d07869b03e908d069e67`.
- CMake source after adding the offline target: `example/cpp/CMakeLists.txt`, SHA256 `bbe7617626f6dc1be3fcdf4a4f125118af8aeefdb605db6fb415cafa2b75708e`.
- Replay binary: `example/cpp/build/replay_four_thigh_d_screen`, SHA256 `e0d73a8fd9c0a8deaf1448e0207c3b872334227054fecf62da26b9ef18af5a1c`.
- Derived screen: `docs/validation/phase1_four_thigh_d_offline_screen_20260914/screen.csv`, SHA256 `bdf3adc036c69cc6a93cefc427ef6773dbecca4977b7db8177495ef88cb87e64`.

Exact offline command:

```text
./example/cpp/build/replay_four_thigh_d_screen unitree_robots/go2/scene_leg_lift_demo.xml /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv docs/validation/phase1_four_thigh_d_offline_screen_20260914/screen.csv
```

Build command:

```text
cmake -S example/cpp -B example/cpp/build -DCMAKE_BUILD_TYPE=Release && cmake --build example/cpp/build --target replay_four_thigh_d_screen -j2
```

No live trajectory, A/B trial, retry, or follow-up action was executed after this offline checkpoint.
