# Phase1 validated PD component decomposition

## Outcome

This is one offline checkpoint using the exact validated atomic evidence from `6cd37e02385eaa98a1ea75002b21378a70120740`. No new MuJoCo trajectory, live intervention, parameter change, gain scan, controller change, or benchmark change was run.

The repository motor order is the established order: `0..11 = FR_hip, FR_thigh, FR_calf, FL_hip, FL_thigh, FL_calf, RR_hip, RR_thigh, RR_calf, RL_hip, RL_thigh, RL_calf`. The decomposition generated 51 ablation branches (3 global, 12 leg, 36 joint) and four interaction audits for every one of the 552 target snapshots. `components.csv` contains full, replay-contact-mask, and phase-bin statistics for all of them.

## Validation gates

- Atomic binding: PASS. All 552 target records had nonzero monotonic sequence, 12 motors, and `snapshot_ctrl[12] == atomic_bridge_ctrl[12]`; maximum residual was `0 Nm`.
- Bridge formula: PASS. Recomputed `tau_ff + P + D` from the atomic record; maximum residual was `0 Nm`.
- ACTUAL replay: PASS. Independently restored `mjSTATE_INTEGRATION` and ACTUAL control reproduced live `qacc[0]` for `552/552`; maximum residual was `0 m/s2`.
- NO_PD regression: PASS. `delta_ax = qacc_NO_PD_x - qacc_ACTUAL_x` full-window median was `-1.6179322500766697 m/s2`, exactly matching the prior committed CSV at double precision.
- Branch isolation: PASS by construction. Each branch restores the saved integration state before setting its own control on a separate replay `mjData`; no branch uses another branch's derived state.

## Global P versus D

Full target `[31.90,33.00)`, `n=552`:

| branch | median delta_ax | p05 | p95 | fraction <0 | fraction >0 | median abs |
|---|---:|---:|---:|---:|---:|---:|
| `NO_P` (`tau_ff + D`) | `+4.896296` | `+2.357729` | `+6.054106` | `0.00%` | `100.00%` | `4.896296` |
| `NO_D` (`tau_ff + P`) | `-7.086373` | `-13.533229` | `+0.528784` | `94.02%` | `5.98%` | `7.086373` |
| `NO_PD` (`tau_ff`) | `-1.617932` | `-9.021298` | `+6.293250` | `72.64%` | `27.36%` | `2.786981` |

The aggregate instantaneous effect is therefore driven primarily by the D-side marginal: removing D makes base-x acceleration more negative. Removing P makes it more positive, so P is an aggregate braking/counteracting marginal in these states. This is a replayed same-state causal result, not a closed-loop trajectory claim.

## Leg ranking

Rankings use median `delta_ax`; signs retain the task convention. D removal: `RR -1.523324`, `FR -1.133999`, `RL -1.069077`, `FL -1.030819 m/s2`. Full-PD removal: `RR -0.712692`, `RL -0.519964`, `FR -0.246992`, `FL -0.009117 m/s2`. P removal, which is positive overall: `FR +1.010449`, `RR +0.977636`, `FL +0.947454`, `RL +0.908074 m/s2`. The complete per-leg distributions and all strata are in `components.csv`.

## Joint ranking

- P removal, strongest positive marginal: `FL_thigh +0.558319`, `FR_thigh +0.522119`, `RL_thigh +0.442967`, `RR_thigh +0.405069 m/s2`.
- D removal, strongest negative marginal: `RR_thigh -1.090959`, `FR_thigh -1.076422`, `FL_thigh -0.991065`, `RL_thigh -0.921039 m/s2`.
- Full-PD removal, strongest negative marginal: `RR_thigh -0.435176`, `RL_thigh -0.384851`, `FR_thigh -0.383054`, `FL_thigh -0.341102 m/s2`.

The thigh joints dominate the robust marginal rankings, but the ranking is not a raw torque ranking. The complete 12-joint P/D/PD distributions, sign fractions, absolute effects, contact masks, and phases are committed in `components.csv`.

## Contact and phase dependence

For global `NO_PD`, replay contact-mask medians were: mask `0`, `-6.531424` (`100.00%` negative, `n=129`); mask `1`, `-7.101405` (`100.00%`, `n=3`, small-n); mask `4`, `+2.317426` (`44.19%` negative, `n=43`); mask `6`, `-1.496658` (`87.06%`, `n=170`); mask `8`, `-4.507503` (`100.00%`, `n=24`); mask `9`, `+0.525731` (`42.62%` negative, `n=183`).

By phase, global `NO_PD` was `[0,0.25): -5.639207` (`74.84%` negative, `n=159`), `[0.25,0.5): +0.200380` (`46.67%`, `n=120`), `[0.5,0.75): -3.094437` (`74.19%`, `n=155`), and `[0.75,1): -1.426592` (`94.07%`, `n=118`). Global `NO_P` stayed positive in every listed contact/phase stratum; global `NO_D` stayed negative in every contact-mask stratum and every phase-bin median, with sign fractions varying.

The leading full-PD joint `RR_thigh` is context-dependent rather than universally harmful: its median was negative for masks `0` and `4`, but positive for masks `6`, `8`, and `9`; by phase it was positive in `[0,0.25)` and `[0.75,1)`, and negative in `[0.25,0.5)` and `[0.5,0.75)`. Mask `1` is marked small-n in the CSV. This supports a contact/phase coordination hypothesis, not deletion of a joint term.

## Additivity and interaction audit

Residual is defined per snapshot as the global effect minus the requested marginal reconstruction. Full-window pooled results are:

| audit | median signed residual | median absolute residual | p95 absolute residual |
|---|---:|---:|---:|
| `NO_PD - (NO_P + NO_D)` | `+0.012981` | `0.064437` | `3.122658` |
| `NO_P - sum(leg P)` | `-0.001159` | `0.003421` | `0.045878` |
| `NO_D - sum(leg D)` | `-0.002222` | `0.007464` | `0.062762` |
| `NO_PD - sum(leg PD)` | `-0.000749` | `0.008094` | `0.036152` |

The global P-versus-D reconstruction has materially larger tail interaction, so component rankings are marginal/context-dependent effects and must not be read as an additive force decomposition. Leg-level reconstructions are closer but still not assumed exact.

## Conclusion and recommendation

The validated instantaneous base-x effect is primarily associated with the D-side bridge marginal, especially thigh joints, while P offsets that effect in aggregate. The full-PD and joint effects flip with contact and phase, so the evidence does not justify a global PD deletion or a unique physical root-cause claim.

The single smallest future live intervention is one pre-registered, safety-gated, contact/phase-aware attenuation pulse of only the `RR_thigh` D contribution in the phase/contact stratum where its full-PD marginal is consistently negative. This recommendation was not executed.

## Provenance and reproduction

- Branch: `research/phase1-pd-component-decomposition-20260914`
- Decomposition base: `6cd37e02385eaa98a1ea75002b21378a70120740`
- Raw snapshot: `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin`, SHA256 `b6e17e79ec3fcf24895c122138c8e146118fc1820274e6e6e3bb334c5e619527`
- Diagnostic closure: `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv`, SHA256 `8467468090dc61f6830d24fd3700916d479ed5ae402f0715c9703894b2bea21c`
- Live data cross-reference: `data.csv`, SHA256 `a97190a3d8e08abaf1ad351e5bdb9bcd11d68a158238cd9a082a39696a592cb0`
- Scene: `unitree_robots/go2/scene_leg_lift_demo.xml`, SHA256 `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`
- Profile cross-reference: `example/cpp/configs/phase1_velocity_varying.csv`, SHA256 `9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74`
- Tool source: `example/cpp/tools/analysis/replay_pd_components.cpp`, SHA256 `89ed52b323e29c91324853c6d2b0ce9a6eac4ae66b1106df4afd8388f0d769ff`
- Reused atomic replay source: `example/cpp/tools/analysis/replay_bridge_atomic.cpp`, SHA256 `3bf22eb2f4d740ba1daa31623c3527fc35c1fb0a9eb2d07869b03e908d069e67`
- CMake source: `example/cpp/CMakeLists.txt`, SHA256 `1de80f2a4e40be370ede330f1aacd53d2c4807621d902fbc915bf4cbd71a1756`
- Replay binary: `example/cpp/build/replay_pd_components`, SHA256 `0536508f4631df30d4d0e3c8122c5691a01a0ad2ea543c6b794a4f34e43400dd`
- Derived output: `docs/validation/phase1_pd_component_decomposition_20260914/components.csv`, SHA256 `4b2e095fd01902d15f3262ad93089c9a85002bd29166ba3a971e51b3b1ed43c8`

Exact offline command from the target worktree:

```text
./example/cpp/build/replay_pd_components unitree_robots/go2/scene_leg_lift_demo.xml /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv docs/validation/phase1_pd_component_decomposition_20260914/components.csv
```

Build command: `cmake -S example/cpp -B example/cpp/build -DCMAKE_BUILD_TYPE=Release && cmake --build example/cpp/build --target replay_pd_components -j1`.

No new simulator trajectory or follow-up experiment was executed after this checkpoint.
