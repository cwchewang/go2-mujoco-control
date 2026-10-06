# Floor registration diagnostic results

Status: the bounded floor-only capture and its predeclared two-repeat reproducibility campaign completed. Both repeat captures reached the 3 s / 1500-step horizon and passed canonical replay. The two-repeat criteria were not fully met because first torque-saturation timing differed by 860 ticks, exceeding the predeclared 200-tick limit. These are engineering observations, not a locomotion baseline qualification or causal finding.

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

Narrow conclusion: under the frozen task and controller, changing only the private predictor floor to z=0 coincided with corrected early selected-state contact labels, a later first torque limit, and reaching the full 3 s horizon. One run cannot establish that the floor change alone caused the later trajectory or limit event.

## Two-repeat reproducibility campaign

Protocol: `tools/substrate/protocols/mjpc_floor_registration_repeat_3s_v1.json`.

Status: COMPLETED, with predeclared repeatability criteria not fully met. The two authorized captures used source HEAD `829f3c40f86f6f8a35dff33c1ff83d230f6f2d54`, packet/campaign ID `975aefc34a6c1ec1f23f544cc53f2a6c56d74ed22e27fd623b8db3462eab189a`, protocol SHA-256 `1513ad74f5574d6ae3d4080071d1391234456c6ccd11739670b5458294c0de77`, and prepared-manifest SHA-256 `c9fc85d51641120b726cef817ae92912965d0e40cb97fc19bd153c2d41bfbf51`. The source-bound science and execution reviews both approved; review bundle SHA-256 `a17f1a82efc87b4fbd83f43171cfb951f88c389c15adc2781aa16af6dd8d99d3`. The user authorization was bound to this HEAD, protocol, manifest, and two-attempt cap; authorization SHA-256 `9514f74ca69bee481168f09dc08d04d91dd7031597ff662d2a16cd1b573ebfb4`.

Campaign gate: `_runs/mjpc_floor_registration_repeat_gate_20261003_r4/CAMPAIGN_RESULT.json`, SHA-256 `c92d3ae1d21f97f8d6c689eaf421fbb15187f3731bee7b0dcabdad5cb8fe855a`. Final status is `COMPLETED_PREDECLARED_REPEATABILITY_CRITERIA_NOT_MET`: two scientific attempts, two native controller processes, 3000 canonical physics steps total, and 735600 total observed private steps against a 1228800 reserve. No retries were made.

- Repeat 1: `_runs/mjpc_floor_registration_repeat_capture_20261003_r4_repeat1`; 1500 steps, horizon reached, replay PASS, 150 optimizer calls, progress 0.859871 m, height 0.269988–0.324488 m, max |roll| 0.143825 rad, max |pitch| 0.158446 rad, no warnings/stderr or failure/forbidden-contact rows. RESULT SHA-256 `959c24be9e3683396240d451afc582af6cf60cfc465b0e92ddca57a6ad70eab9`; raw SHA-256 `c5d3f8eac0387025d9ae7995b687915a416bfc0941cd506562007073f03d6792`; manifest SHA-256 `ee27474206d57d12506568a30e8bd32c22b9fe7d10cb41c9d38175bf825dc73a`.
- Repeat 2: `_runs/mjpc_floor_registration_repeat_capture_20261003_r4_repeat2`; 1500 steps, horizon reached, replay PASS, 150 optimizer calls, progress 0.839513 m, height 0.269988–0.325158 m, max |roll| 0.133036 rad, max |pitch| 0.158795 rad, no warnings/stderr or failure/forbidden-contact rows. RESULT SHA-256 `8c125571567575a9a2eb6f02b92649045d4ea6be3bbc63aa417057f4ff0df1c6`; raw SHA-256 `a1c02c1dfeb6f687105cbcf1bcfccf401b6f445509181899e5725001aaaec76b`; manifest SHA-256 `8314864e1086cf6e82c2b6eb91cd6ed5b352622929230a933c5f9ed433605043`.

All predeclared checks passed except first torque-saturation timing: repeat 1 first saturated at tick 1155 (2.31 s, RR calf), repeat 2 at tick 295 (0.59 s, RL calf), a delta of 860 ticks versus the 200-tick maximum. Progress delta was 0.020359 m (limit 0.05 m); height-envelope differences were within 0.02 m; roll/pitch maxima differed by at most 0.010789 rad (limit 0.03 rad); tick-20 selected-state contacts matched; both horizons and replays passed.

Read-only posthoc analysis is sealed at `_runs/mjpc_floor_registration_repeat_gate_20261003_r4/SATURATION_POSTHOC.json`. Each within-run saturation episode lasted one 2 ms action sample (one event in repeat 1, two in repeat 2); this supports a threshold-timing sensitivity hypothesis but does not establish that threshold grazing caused the 860-tick cross-run difference. With n=2, these runs do not estimate a saturation timing distribution and do not establish robustness, baseline qualification, or causality.
