# Floor registration diagnostic results

Status: first bounded floor-only capture completed; two-repeat reproducibility campaign NOT_RUN pending fresh independent review and campaign authorization.

## Single floor-only capture

The one fresh-process capture completed the frozen 3 s / 1500 canonical-step horizon. The canonical replay verdict was PASS with no first failure and no missing supports. It used 150 optimizer calls, reached the private observed upper bound 367800 of 614400, emitted no warnings, and had an empty native stderr log. This is a bounded observation, not a locomotion baseline qualification.

Evidence is sealed under `_runs/mjpc_floor_registration_capture_20261003_r2`:
- HEAD: `c008a2ad5c4bd73f06b3a20e9aee18ccc74166e6`
- packet SHA-256: `7662c2d96ca664162888e8f5870b9013f2919c26eca295994d53bb73c04de402`
- RESULT.json SHA-256: `47cf21600c3f56ab60b709242fcfa14454ffb67beaad6c6c1bed72aedb3f2c26`
- manifest SHA-256: `7c0325594655728b488e8be320f7fe7b2deb9075541642975a0c7bd89986327f`
- raw SHA-256: `f685bde4897f3c4e576d57a295fef6def460b23758d3541489e79b59e37f0296`
- prediction trace SHA-256: `45ac194513f65443a5ca2ea35390dd351bc202a0a37ab7bfb0d3323867ffcf10`

At tick 20 / 0.04 s, actual supports were all four feet and the selected-state forward reconstruction on the smoothed private model also labeled all four feet. Its qpos maximum absolute difference from the actual state was 0.000863 m. Sealed R4 had all four actual supports but no selected-state reconstructed foot labels, with qpos difference 0.000868 m. The reconstructed labels are not future-rollout predictions; the qpos mismatch changed very little.

The first actuator torque limit was reached at tick 925 / 1.85 s on RR calf at 45.43 Nm; no position-target saturation occurred. In R4 the same actuator first hit its torque limit at tick 105 / 0.21 s. The new run's body-height range was 0.269988–0.324488 m; maximum absolute roll and pitch were 0.108 and 0.192 rad; forward progress was 0.844 m. R4 stopped at tick 260 / 0.52 s on `nonfoot_contact`; it remains sealed and must never be rerun.

Narrow conclusion: under the frozen task and controller, changing only the private predictor floor to z=0 coincided with corrected early selected-state contact labels, a later first torque limit, and reaching the full 3 s horizon. One run cannot establish that the floor change alone caused the later trajectory or limit event. The repeat campaign below is the next check; it does not expand duration or change any controller, model, warm-start, or task input.

## Two-repeat reproducibility campaign

Protocol: `tools/substrate/protocols/mjpc_floor_registration_repeat_3s_v1.json`.

Status: NOT_RUN. It reuses the verified floor0 packet/runtime and existing capture entrypoint. Each repeat is one new native process and one fresh 1500-step maximum episode; both use the same floor-corrected configuration. The packet-keyed campaign reservation allows only slots 1 and 2; slot 2 is blocked unless slot 1 has a sealed 1500-step `HORIZON_REACHED` result. Any safety, execution, warning, identity, evidence, or budget failure stops the campaign with no retry.

Per-repeat caps remain 1500 canonical steps / 3 s, 150 replans, 614400 private steps and 300 s wall time. The total private upper-bound reserve is 1228800. Predeclared engineering repeatability checks compare horizon/replay pass, tick-20 selected-state contact sets, forward progress (max 0.05 m difference), body-height envelope (max 0.02 m difference), maximum absolute roll/pitch (max 0.03 rad difference), and first torque-limit tick (max 200 tick difference). These are reproducibility checks only, not robustness or baseline qualification. Both runs must pass the safety/evidence gates; no R4 replay is part of the campaign.

The two-repeat packet must bind the single-run result above, the exact source HEAD, the existing floor0 binary/runtime identity, and this protocol. Run only after fresh independent science and execution reviews approve that exact packet and a single user authorization is bound to its HEAD, protocol, manifest, and two-slot budget.
