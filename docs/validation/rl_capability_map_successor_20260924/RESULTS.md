# RL capability-map successor results — 2026-09-24

## Campaign identity and execution

- Praxis issue: **#189**; logical branch: `research/rl-capability-map-successor-20260924`.
- Capture HEAD: `e40b0933572345f23b37e3bb06350518fde63e76` (detached Praxis worktree).
- Frozen protocol: schema-2 `rl-capability-map-v1`, SHA-256 `0eda1a046d4d9c456a3ee5a281cc183eaf188b0ff9db9fe0767bc5f6011dc803`.
- Frozen attempt policy: 9 cases, `max_attempts=9`, retry=`none`; physics period 0.002 s.
- Exact-head deterministic owner precheck: **PASS**. Clean non-development qualification: **ENGINEERING_ADMITTED** with all eight checks returning 0.
- Zero-step preparation: **READY_AWAITING_START**, `physics_steps=0`; the task-local campaign ledger was absent before capture.
- One authorized capture invocation completed as **CAPTURE_COMPLETE / CHARACTERIZED**. The permanent ledger records nine consumed attempts; no recapture was made.
- No case ended in a safety or integrity stop. Case classifications and their metrics are recorded individually below.

## Case outcomes

Commands are the protocol vectors `[start_tick, vx, vy, wz]`. Each metric and trace hash below comes from the captured case analysis and was matched by offline verification.

### 1. `flat_reference` — **PASS**

- Frozen scenario: scene `unitree_robots/go2/phase2_flat.xml`; commands `[[0,1.0,0.0,0.0]]`; horizon 6000 ticks; tracked axes `vx`; reset `shared_home`.
- Execution: complete `true`; steps 6000; failure `None`; failure classes `none`.
- `vx` window [0, 6000): command 1.0, samples 5000, mean 0.885882509707172, MAE 0.11411749029282788, RMSE 0.11919403374163151.
- Motion and clearance: progress 10.486111570522883 m; maximum lateral displacement 0.06490106716002314 m; maximum absolute yaw 0.03719463073879735 rad; minimum clearance 0.27 m.
- Gates: tracking `true`; flat cross-axis `true`.
- Reference gate: `true`; mean vx 0.885882509707172 m/s; expected and observed trace digest `1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484` (match `true`).
- Policy: 599 updates; p50 0.3442899906076491 ms; p99 0.6499195145443081 ms.
- Trace SHA-256: `1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484`.

### 2. `flat_half_speed` — **PERFORMANCE_FAIL**

- Frozen scenario: scene `unitree_robots/go2/phase2_flat.xml`; commands `[[0,0.5,0.0,0.0]]`; horizon 6000 ticks; tracked axes `vx`; reset `shared_home`.
- Execution: complete `true`; steps 6000; failure `None`; failure classes `TRACKING_FAILURE`.
- `vx` window [0, 6000): command 0.5, samples 5000, mean 0.4034335714063999, MAE 0.09656642859360011, RMSE 0.10216555438276635.
- Motion and clearance: progress 4.761425319825732 m; maximum lateral displacement 0.5746526775977416 m; maximum absolute yaw 0.24710140155723373 rad; minimum clearance 0.27 m.
- Gates: tracking `true`; flat cross-axis `false`.
- Policy: 599 updates; p50 0.34820701694115996 ms; p99 0.8398914011195293 ms.
- Trace SHA-256: `2b15c066d67f52b574ef7d5a1065a7bc241edab26c9f37c546ed38334d27e3b0`.

### 3. `flat_reverse_probe` — **PERFORMANCE_FAIL**

- Frozen scenario: scene `unitree_robots/go2/phase2_flat.xml`; commands `[[0,-0.5,0.0,0.0]]`; horizon 6000 ticks; tracked axes `vx`; reset `shared_home`.
- Execution: complete `true`; steps 6000; failure `None`; failure classes `TRACKING_FAILURE`.
- `vx` window [0, 6000): command -0.5, samples 5000, mean -0.3558962752716792, MAE 0.14410372472832078, RMSE 0.14594246239619435.
- Motion and clearance: progress -4.274084690130656 m; maximum lateral displacement 0.19089431587079722 m; maximum absolute yaw 0.046392298307842646 rad; minimum clearance 0.27 m.
- Gates: tracking `false`; flat cross-axis `true`.
- Policy: 599 updates; p50 0.3349630278535187 ms; p99 0.619353918591514 ms.
- Trace SHA-256: `501d046f43af6c3a35636b0c41fd8bb53a66136443dbbd9cf0a548f5fa6f0661`.

### 4. `flat_lateral_probe` — **PERFORMANCE_FAIL**

- Frozen scenario: scene `unitree_robots/go2/phase2_flat.xml`; commands `[[0,0.0,0.25,0.0]]`; horizon 2500 ticks; tracked axes `vy`; reset `shared_home`.
- Execution: complete `true`; steps 2500; failure `None`; failure classes `TRACKING_FAILURE`.
- `vy` window [0, 2500): command 0.25, samples 2400, mean 0.16589076891998328, MAE 0.08410923108001674, RMSE 0.08640330946693603.
- Motion and clearance: progress 0.0010082593621852161 m; maximum lateral displacement 0.815447406508547 m; maximum absolute yaw 0.025402165923079416 rad; minimum clearance 0.27 m.
- Gates: tracking `false`; flat cross-axis `true`.
- Policy: 249 updates; p50 0.3339109825901687 ms; p99 0.8237285306677227 ms.
- Trace SHA-256: `ccd4fc0ea3ec4e14d00b7c5ee3276c5234779ac5107dda5cb694eaa6a6d34f7b`.

### 5. `flat_yaw_probe` — **PERFORMANCE_FAIL**

- Frozen scenario: scene `unitree_robots/go2/phase2_flat.xml`; commands `[[0,0.0,0.0,0.5]]`; horizon 2500 ticks; tracked axes `wz`; reset `shared_home`.
- Execution: complete `true`; steps 2500; failure `None`; failure classes `TRACKING_FAILURE`.
- `wz` window [0, 2500): command 0.5, samples 2400, mean 0.10438385495279155, MAE 0.39561614504720843, RMSE 0.4025020751487876.
- Motion and clearance: progress 0.013335806353059223 m; maximum lateral displacement 0.02098132787660068 m; maximum absolute yaw 0.5539720637493629 rad; minimum clearance 0.27 m.
- Gates: tracking `false`; flat cross-axis `true`.
- Policy: 249 updates; p50 0.3486889763735235 ms; p99 0.7308811973780407 ms.
- Trace SHA-256: `ac2e35d9bea75c45ce8f4847445914972afd983ada18c8b0c72918d1bd09f6a7`.

### 6. `step_5cm_cross` — **PASS**

- Frozen scenario: scene `unitree_robots/go2/phase2_step_5cm.xml`; commands `[[0,1.0,0.0,0.0]]`; horizon 6000 ticks; tracked axes `vx`; reset `shared_home`.
- Execution: complete `true`; steps 6000; failure `None`; failure classes `none`.
- `vx` window [0, 6000): command 1.0, samples 5000, mean 0.8853913335442055, MAE 0.11460866645579447, RMSE 0.11984091186900767.
- Motion and clearance: progress 10.445638270568374 m; maximum lateral displacement 0.24529999682155512 m; maximum absolute yaw 0.05533571843174896 rad; minimum clearance 0.27 m.
- Gates: tracking `true`; flat cross-axis `true`.
- Terrain gates: route `true`; task goal `true`; maximum hold 5003 ticks.
- Policy: 599 updates; p50 0.33905095187947154 ms; p99 0.6599366490263489 ms.
- Trace SHA-256: `81e441638915d124e186dbecda00ecf354daad54807e2e95d8d66bc968c248b4`.

### 7. `step_10cm_cross` — **PASS**

- Frozen scenario: scene `unitree_robots/go2/phase2_step_10cm.xml`; commands `[[0,1.0,0.0,0.0]]`; horizon 6000 ticks; tracked axes `vx`; reset `shared_home`.
- Execution: complete `true`; steps 6000; failure `None`; failure classes `none`.
- `vx` window [0, 6000): command 1.0, samples 5000, mean 0.8848593507754705, MAE 0.11514064922452952, RMSE 0.12077927699699824.
- Motion and clearance: progress 10.316233535684782 m; maximum lateral displacement 0.5071761720099065 m; maximum absolute yaw 0.0846304426479088 rad; minimum clearance 0.27 m.
- Gates: tracking `true`; flat cross-axis `true`.
- Terrain gates: route `true`; task goal `true`; maximum hold 4958 ticks.
- Policy: 599 updates; p50 0.3515739808790386 ms; p99 0.6095593539066612 ms.
- Trace SHA-256: `b730d737fa575ba309c8331a4879c32240c9d26724743871fc0adccebde8c6d0`.

### 8. `repeated_steps_cross` — **PASS**

- Frozen scenario: scene `unitree_robots/go2/phase2_repeated_steps.xml`; commands `[[0,1.0,0.0,0.0]]`; horizon 6000 ticks; tracked axes `vx`; reset `shared_home`.
- Execution: complete `true`; steps 6000; failure `None`; failure classes `none`.
- `vx` window [0, 6000): command 1.0, samples 5000, mean 0.8843932607398814, MAE 0.11686979766562774, RMSE 0.1277256214711996.
- Motion and clearance: progress 10.321470513615303 m; maximum lateral displacement 0.18679926838388208 m; maximum absolute yaw 0.07137341555903155 rad; minimum clearance 0.23563461113616693 m.
- Gates: tracking `true`; flat cross-axis `true`.
- Terrain gates: route `true`; task goal `true`; maximum hold 4367 ticks.
- Policy: 599 updates; p50 0.3437289851717651 ms; p99 0.5759880307596169 ms.
- Trace SHA-256: `a2081dbf9eb98bf26a00660b95a725a1b4262235a9d29c7c94f8d336329c520d`.

### 9. `low_friction_cross` — **PASS**

- Frozen scenario: scene `unitree_robots/go2/scene_low_friction_patch.xml`; commands `[[0,1.0,0.0,0.0]]`; horizon 6000 ticks; tracked axes `vx`; reset `shared_home`.
- Execution: complete `true`; steps 6000; failure `None`; failure classes `none`.
- `vx` window [0, 6000): command 1.0, samples 5000, mean 0.8859848801308108, MAE 0.11401511986918915, RMSE 0.11911001394124833.
- Motion and clearance: progress 10.484724619322083 m; maximum lateral displacement 0.05881391653496797 m; maximum absolute yaw 0.03659068158954195 rad; minimum clearance 0.269 m.
- Gates: tracking `true`; flat cross-axis `true`.
- Terrain gates: route `true`; task goal `true`; maximum hold 4829 ticks.
- Policy: 599 updates; p50 0.3377870307303965 ms; p99 0.6849226250778883 ms.
- Trace SHA-256: `494cd5d5abd15823b55fe99e88a205c9b0ca98aa62792dbde0400a80d008587e`.

## Independent verification and interpretation

The unmodified `tools.substrate.baseline verify` invocation stopped before row replay with `ValueError: preflight identity mismatch`. Its failed bundle is preserved. The captured preflight correctly records an empty actual Git branch for the detached worktree while binding the logical task branch through the complete Praxis identity.

The same offline verifier then returned **VERIFIED**, checked the permanent external ledger, consumed 9 cases, and recorded `physics_steps=0`. A transient in-memory adapter first revalidated all five Praxis identity fields and then mapped only the detached empty actual branch to the task logical branch for the verifier’s existing comparison. No source file or prepared/capture/preflight bundle was modified. The verifier independently recomputed the `flat_reference` sealed digest as `1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484`; it also replayed per-case policy targets and reconstructed contact telemetry without integrating physics.

Under this frozen simulated protocol, the reference and terrain cases meet their recorded gates. The half-speed, reverse, lateral, and yaw probes are classified `PERFORMANCE_FAIL` under the unchanged thresholds. These results characterize only this checkpoint, adapter, reset, scenes, and command set. They do not establish hardware performance, general robustness, or paper novelty.

Raw case traces, analysis records, the byte-verified permanent-ledger copy, the failed standard verifier bundle, the final offline verifier bundle, and supporting precheck/qualification/preparation evidence are preserved in the Praxis evidence package for task #189.
