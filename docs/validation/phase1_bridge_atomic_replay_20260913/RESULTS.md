# Phase1 bridge-atomic PD counterfactual replay

## Outcome

This checkpoint answers the six required questions in order.

1. **Atomic bridge/snapshot binding: PASS.** Every target snapshot has a nonzero monotonic `bridge_ctrl_seq`, 12-motor record, and explicit sequence-step index. The snapshot `ctrl[12]` equals the bound atomic bridge record `ctrl[12]` with maximum absolute residual `0 Nm`. The captured record uses the same simulation mutex and LowCmd mutex as the bridge write. The snapshot capture interval contained 2,499 records; the active target selection contained 552 records in `[31.90,33.00) s`. Target `bridge_ctrl_seq` ran from 36,969 to 38,071, with `bridge_seq_steps_total=1` for every target row; no sequence reuse occurred in this run, and the explicit index was still recorded.

2. **ACTUAL replay versus live `qacc[0]`: PASS.** Restoring `mjSTATE_INTEGRATION`, setting ACTUAL `ctrl[12]` to the captured snapshot command, and running `mj_forward` reproduced live `qacc[0]` for 552/552 target snapshots. Maximum absolute residual was `0 m/s2`, tighter than the `1e-5 m/s2` gate. MuJoCo/model signature was unambiguous: MuJoCo 3.3.6, `mjtNum=8`, `state_sig=mjSTATE_INTEGRATION=8191`, `state_size=194`, `nq=19`, `nv=18`, `na=0`, `nu=12`, timestep `0.002 s`. ACTUAL and CF each started from an independently restored copy of the same saved state.

3. **Validated instantaneous effect of removing bridge PD.** The CF branch changed only `ctrl[i]` from the bound atomic record's exact `ctrl[i]` to the bound record's exact `tau_ff[i]`; it did not feed back into the live trajectory. `delta_ax = qacc_cf_x - qacc_actual_x`.

| window | n | median | p05 | p95 | frac <0 | frac >0 |
|---|---:|---:|---:|---:|---:|---:|
| [31.90,32.10) | 103 | -1.695767 | -8.251884 | 6.597329 | 76.70% | 23.30% |
| [32.10,32.20) | 50 | -1.336443 | -9.150890 | 4.730259 | 72.00% | 28.00% |
| [32.20,32.40) | 100 | -1.851080 | -8.477179 | 6.517793 | 73.00% | 27.00% |
| [32.40,32.60) | 100 | -1.450871 | -9.511600 | 5.665412 | 70.00% | 30.00% |
| [32.60,33.00) | 199 | -1.608194 | -9.505727 | 5.838554 | 71.86% | 28.14% |
| [31.90,33.00) | 552 | -1.617932 | -9.021298 | 6.293250 | 72.64% | 27.36% |

4. **Sign consistency: contact- and phase-dependent.** Dominant replay contact-mask stratification over the full target was: mask 0, n=129, median -6.531424, frac<0 100.00%; mask 1, n=3, median -7.101405, frac<0 100.00%; mask 4, n=43, median +2.317426, frac<0 44.19%; mask 6, n=170, median -1.496658, frac<0 87.06%; mask 8, n=24, median -4.507503, frac<0 100.00%; mask 9, n=183, median +0.525731, frac<0 42.62%. Phase bins were [0,.25): n=159, median -5.639207, frac<0 74.84%; [.25,.5): n=120, median +0.200380, frac<0 46.67%; [.5,.75): n=155, median -3.094438, frac<0 74.19%; [.75,1): n=118, median -1.426592, frac<0 94.07%.

The saved live pre-step contact summary and newly forward-recomputed replay contact summary agreed for ncon, nefc, and physical foot mask on 500/552 rows. This was recorded for stratification only and was not used as a failure gate because the live summary is a derived pre-step timing view. The primary exact-state plus actual-ctrl to live-`qacc[0]` gate passed.

5. **Interpretation:** This supports bridge-side joint PD as a **mixed instantaneous contributor**, with an overall negative `delta_ax` median (removing PD makes instantaneous base-x acceleration more negative, so PD is net forward / opposing braking in that aggregate) but positive regions under particular contact masks and phases (PD is locally braking there). It does not establish PD as the sole root cause of residual overspeed, nor does it establish a closed-loop trajectory effect.

6. **One next step, not executed:** repeat the same atomic replay only after a separately approved attribution design specifies which contact/phase stratum is the causal target.

## Scope and provenance

- Branch: `research/phase1-bridge-atomic-replay-20260913`
- Source at launch: `983a74fff09611f85d77b8ada65d02256f343514`, working tree dirty only because of this diagnostic plumbing.
- Run ID: `varying_20260913_231049`
- One ordinary-PD A run only; no live PD-off pulse, no tau_ff-only live run, no parameter change, no B run.
- Run statuses: controller=0, safety=0, quality=0, analysis=0, completion=0; existing varying baseline analyzer `strict_pass=true`.
- Seed: unset.
- Scene: `unitree_robots/go2/scene_leg_lift_demo.xml`, SHA256 `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.
- Profile: `example/cpp/configs/phase1_velocity_varying.csv`, SHA256 `9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74`.
- Fixed controller argv: `--headless --wall-clock-motion --controller-duration 86 --wbc-full --gait-pattern running-trot --kernel raibert-trot --period 0.14 --duty 0.44 --step-length 0.50 --foot-lift 0.20 --tau-limit 45 --raibert-velocity-gain 0.010 --raibert-max-adjustment 0.06 --preview-horizon 4 --support-anchor-feedback --support-anchor-gain 0.35 --velocity-max-accel 0.80 --velocity-max-decel 1.20 --velocity-max-jerk 4.0 --velocity-command-script example/cpp/configs/phase1_velocity_varying.csv --velocity-max-tracking-lead 0.20 --domain-id 232`.
- Diagnostic environment additions: `TROT_BRIDGE_ATOMIC_RECORD=1`, `TROT_MJ_SNAPSHOT_PATH=.../bridge_atomic_snapshots.bin`, `TROT_MJ_SNAPSHOT_TIME_START=36.0`, `TROT_MJ_SNAPSHOT_TIME_END=41.0`, plus existing `TROT_DIAG_ID_CLOSURE=1` and `TROT_CPU_AUTOPIN=1`.

## Atomic format and implementation

The default-off bridge flag is cached once during bridge-object construction. While holding the simulation mutex and LowCmd mutex, the bridge writes the unchanged `tau + kp*(q-q_sensor) + kd*(dq-dq_sensor)` expression and then publishes one atomic record containing simulator time, LowCmd q/dq/kp/kd/tau_ff, sensor q/dq, resulting `ctrl[12]`, and the monotonically increasing sequence.

Immediately before each real `mj_step`, the simulator serializes `mjSTATE_INTEGRATION`, current time, current `ctrl[12]`, the latest full atomic bridge record, pre-step ncon/nefc/physical contact mask, and the post-step live `qacc[0]`. The binary header is format version 2. The replay tool checks sequence monotonicity and reuse indices, model/state signatures, snapshot-ctrl equality, bridge-formula equality, and the ACTUAL qacc gate before emitting CF results.

## Invocation

A run:
```
TROT_CPU_AUTOPIN=1 TROT_DIAG_ID_CLOSURE=1 TROT_BRIDGE_ATOMIC_RECORD=1 \\
TROT_MJ_SNAPSHOT_PATH=/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin \\
TROT_MJ_SNAPSHOT_TIME_START=36.0 TROT_MJ_SNAPSHOT_TIME_END=41.0 \\
GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv \\
bash example/cpp/scripts/run_phase1_velocity_benchmark.sh varying \\
_runs/phase1_bridge_atomic_replay_20260913 232
```

Offline replay:
```
./example/cpp/build/replay_bridge_atomic \\
unitree_robots/go2/scene_leg_lift_demo.xml \\
example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin \\
example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv \\
docs/validation/phase1_bridge_atomic_replay_20260913/counterfactual_atomic.csv
```

## Hashes

Source files:
- `simulate/src/main.cc`: `c0b60eedd19f77d8252f2628494bd489e54fad0d0766495f327effd1dca9c243`
- `simulate/src/unitree_sdk2_bridge.h`: `2f6b6e76e4d067dff602ec1304228e9e66c44a37783f449b47af00e412b527bb`
- `example/cpp/CMakeLists.txt`: `c72872ba97bb31fcd06417a2b84f089ae0b218d0ccbf60ef19c6a123dc84ef0c`
- `example/cpp/tools/analysis/replay_bridge_atomic.cpp`: `1873fa1c887b1f8121daecd75aff54094cedd7ba4fa23ad1336dc452dd92a371`

Built binaries:
- simulator: `9753a3b857130bf6006ffc10e7439ee14bce18783a5fa8d14d8d0c75cafc19f0`
- controller: `7aee105accc7d716312c7e65618882f52b8665b7fc1f3c1001141407432f2b4b`
- replay tool: `95b1a4f5fb474c6f76bc04dbb0704518f6acc76ee17632203bc0ea7f981e50a6`

Raw local evidence:
- `bridge_atomic_snapshots.bin`: `b6e17e79ec3fcf24895c122138c8e146118fc1820274e6e6e3bb334c5e619527`
- `data.csv`: `a97190a3d8e08abaf1ad351e5bdb9bcd11d68a158238cd9a082a39696a592cb0`
- `data.csv.id_closure.csv`: `8467468090dc61f6830d24fd3700916d479ed5ae402f0715c9703894b2bea21c`
- `run_metadata.txt`: `390f277d2d6137a2da710ed66b8d5644c8e1c73e7b0225620cb28c251b50e2f1`
- `run_manifest.json`: `953d2df6bbf07f46becd97125113eb7c5856a08ad09dd427001b38ad3d825848`
- `environment.txt`: `cdc389432b3bef410b9e4a29a7135f79ff999776992f0b176b86bb7949fcbeb2`
- `simulator.log`: `22b4d09a64fabca39c1ade8d8f54569260b3b4a20fe8d1c7b27d15046fb1e4e5`
- `controller.log`: `6c3d89e8ecea82f002ace864302449968d50e9c986fcde4f1ad187b7326f81bc`

Committed derived outputs:
- `docs/validation/phase1_bridge_atomic_replay_20260913/RESULTS.md`
- `docs/validation/phase1_bridge_atomic_replay_20260913/counterfactual_atomic.csv`
- CSV SHA256: `16aa413f1bbbe0c0c41417051515e9b7f17e457b5d0af1e61474eea7da892c6f` (552 rows, 83 fields)

No gain, WBC/SRBD/contact/model/threshold change, live intervention, terrain/Phase2 work, or follow-up run was executed.
