# Phase1 pre-motion lockstep startup determinism - 2026-09-14

Hypothesis: deterministic zero-control pre-motion and a frozen handoff before active stand-up remove startup-state/lifecycle divergence from repeated Phase1 baselines.

Primary label: **LOCKSTEP_PROTOCOL_FAIL**.

Exactly three sequential frozen baselines L1/L2/L3 were executed after Stage 2 passed. D4 and every prior A/B flag were OFF; the inherited Phase1 scene/model/profile/period/duty/WBC-full parameters and fixed CPU affinity were retained. No controller or acceptance threshold was changed.

## Stage 0 lifecycle audit

Recorded before Stage 1 behavior edits from the native WSL source inspection.

- PhysicsThread creates MuJoCo data and calls mj_forward; before the barrier, PhysicsLoop advances through the wall-clock path.
- The bridge DDS readiness check occurs before Go2Bridge construction.
- The controller creates publishers/subscribers, waits for natural settle for wall-clock 0.5 s, then captures start joints and world reference asynchronously.
- The writer thread starts after capture and performs the pre-gate LowCmdWrite(false).
- Before the barrier, RunLockstep delegates to RunWallClock; the first command completes the barrier, after which physics waits for permission and performs one mj_step.
- Before Stage 1, the epoch was tied only to task_.gait_started_; the writer gate engaged afterward.
- Stand-up and gait therefore progressed on the free-running path before the proposed handoff.
- Earliest safe freeze boundary: after mj_forward, run fixed controller-independent zero-control pre-settle, serialize the state, publish nothing until serialization completes, and hold the plant for controller capture.

Stage 1 used 4000 exact zero-control MuJoCo steps, stable double-state serialization, and writer-gate/motion-clock authority from the pre-motion handoff. Flag-off behavior remains wall-clock.

## Stage 2

Passed before launches: simulator test_lockstep and test_lockstep_sim; controller test_lockstep_writer_gate, test_lockstep_motion_clock, and test_lockstep_motion_clock_integration. Focused tests cover frozen first consumption, duplicate suppression, strictly-new ticks, state-tick 0/2 ms timing, and legacy flag-off behavior.

## Handoff state

The simulator wrote the post-4000-step state before state publication. handoff_states.csv records stable binary hashes and pairwise maxima for full qpos/qvel plus actuator-derived q/dq; the simulator double state is authoritative.

|run|steps|sim tick|binary SHA256|controller handoff tick|first gated tick|first gated gait_started|
|---|---:|---:|---|---:|---:|---:|
|L1|4000|8000|bf3a4379adfab77a4c0cf01587ac05888c7525b4326d31020b8a1e4a0cfc1137|9496|9496|0|
|L2|4000|8000|bf3a4379adfab77a4c0cf01587ac05888c7525b4326d31020b8a1e4a0cfc1137|9090|9090|0|
|L3|4000|8000|bf3a4379adfab77a4c0cf01587ac05888c7525b4326d31020b8a1e4a0cfc1137|9122|9122|0|

Handoff pairwise maxima: qpos=0, qvel=0, actuated q=0, actuated dq=0; exact binary hashes identical=true. Required maxima are <=1e-12.

## Gates

protocol_gates.csv records every protocol and handoff gate. The strict post-handoff trace requires 2 ms ticks, zero violations, exact matched-pair trigger, one command update per state tick, no duplicate active LowCmd, and no free/active motion before the handoff. Physical gates are unchanged: active-relative >=40 s, no hard stop before 40 s, continuous-trot in [32,33), excess median [+0.15,+0.35] m/s, and WBC/SRBD/ID medians <0.

|run|protocol|physical|active-relative s|[32,33) rows|excess median|WBC ax|SRBD ax|ID qdd-x|
|---|---|---|---:|---:|---:|---:|---:|---:|
|L1|FAIL|PASS|80.002|500|0.256337385|-2.563373855|-1.734537676|-2.35760439|
|L2|FAIL|PASS|80.002|500|0.25484775|-2.548477504|-1.73041128|-2.3207591895|
|L3|FAIL|FAIL||0|||||

## Trajectory

Pairwise alignment uses only diag_active_relative_time_s after handoff on a fixed 10 ms grid with maximum nearest tolerance 10 ms; wall-clock timestamps are not truth. pairwise.csv reports p50/p95/max for measured/applied velocity, excess, roll, pitch, physical contact count/mask, controller contact mask, and gait phase. Sustained divergence is measured as registered: measured >0.05 m/s or roll/pitch >2 deg for >=100 ms.

|pair|grid points|common prefix s|excess p50/p95/max|measured p50/p95/max|roll p50/p95/max deg|pitch p50/p95/max deg|first sustained divergence before 40 s|
|---|---:|---|---|---|---|---|---|
|L1__L2|0|-|//|//|//|//|none|
|L1__L3|0|-|//|//|//|//|none|
|L2__L3|0|-|//|//|//|//|none|

Endpoint excess range= m/s <=0.010=false; all protocol=false, handoff=false, physical=false, no sustained divergence before 40 s=false.

## Exact commands and provenance

The following three commands were run sequentially, with no fourth launch:
flock /tmp/go2_mujoco_experiment.lock env -u TROT_PD_PULSE_AB -u TROT_FOUR_THIGH_D90_AB -u TROT_BOUNDED_STANCE_DQ_D4_AB -u TROT_BOUNDED_STANCE_DQ_AB -u TROT_SEED -u RUN_SEED SIM_LOCKSTEP=1 TROT_LOCKSTEP_PUBLISH_DIAG=1 GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv TROT_CPU_AUTOPIN=1 TROT_DYNAMICS_TOLERANCE_N=20 TROT_HS_START_PERIOD=0.20 TROT_HS_START_DUTY=0.50 TROT_HS_SPEED_LEAD=0.25 TROT_HS_ACC_GAIN=10 TROT_HS_ACC_LIMIT=4 TROT_HS_STEP_CAP=0.52 TROT_HS_SWING_REACH=0.90 TROT_HS_HYBRID_CONTACT=2 TROT_HS_PITCH_GAIN=24 TROT_HS_PITCH_DAMP=6 TROT_HS_ROLL_GAIN=20 TROT_HS_ROLL_DAMP=10 TROT_HS_STABILITY_GOV=1 bash example/cpp/scripts/run_trot.sh 140 _runs/phase1_lockstep_premotion_startup_20260914/L1 --headless --wall-clock-motion --controller-duration 86 --wbc-full --gait-pattern running-trot --kernel raibert-trot --period 0.14 --duty 0.44 --step-length 0.50 --foot-lift 0.20 --tau-limit 45 --raibert-velocity-gain 0.010 --raibert-max-adjustment 0.06 --preview-horizon 4 --support-anchor-feedback --support-anchor-gain 0.35 --velocity-max-accel 0.80 --velocity-max-decel 1.20 --velocity-max-jerk 4.0 --velocity-command-script example/cpp/configs/phase1_velocity_varying.csv --velocity-max-tracking-lead 0.20 --domain-id 221
flock /tmp/go2_mujoco_experiment.lock env -u TROT_PD_PULSE_AB -u TROT_FOUR_THIGH_D90_AB -u TROT_BOUNDED_STANCE_DQ_D4_AB -u TROT_BOUNDED_STANCE_DQ_AB -u TROT_SEED -u RUN_SEED SIM_LOCKSTEP=1 TROT_LOCKSTEP_PUBLISH_DIAG=1 GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv TROT_CPU_AUTOPIN=1 TROT_DYNAMICS_TOLERANCE_N=20 TROT_HS_START_PERIOD=0.20 TROT_HS_START_DUTY=0.50 TROT_HS_SPEED_LEAD=0.25 TROT_HS_ACC_GAIN=10 TROT_HS_ACC_LIMIT=4 TROT_HS_STEP_CAP=0.52 TROT_HS_SWING_REACH=0.90 TROT_HS_HYBRID_CONTACT=2 TROT_HS_PITCH_GAIN=24 TROT_HS_PITCH_DAMP=6 TROT_HS_ROLL_GAIN=20 TROT_HS_ROLL_DAMP=10 TROT_HS_STABILITY_GOV=1 bash example/cpp/scripts/run_trot.sh 140 _runs/phase1_lockstep_premotion_startup_20260914/L2 --headless --wall-clock-motion --controller-duration 86 --wbc-full --gait-pattern running-trot --kernel raibert-trot --period 0.14 --duty 0.44 --step-length 0.50 --foot-lift 0.20 --tau-limit 45 --raibert-velocity-gain 0.010 --raibert-max-adjustment 0.06 --preview-horizon 4 --support-anchor-feedback --support-anchor-gain 0.35 --velocity-max-accel 0.80 --velocity-max-decel 1.20 --velocity-max-jerk 4.0 --velocity-command-script example/cpp/configs/phase1_velocity_varying.csv --velocity-max-tracking-lead 0.20 --domain-id 222
flock /tmp/go2_mujoco_experiment.lock env -u TROT_PD_PULSE_AB -u TROT_FOUR_THIGH_D90_AB -u TROT_BOUNDED_STANCE_DQ_D4_AB -u TROT_BOUNDED_STANCE_DQ_AB -u TROT_SEED -u RUN_SEED SIM_LOCKSTEP=1 TROT_LOCKSTEP_PUBLISH_DIAG=1 GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv TROT_CPU_AUTOPIN=1 TROT_DYNAMICS_TOLERANCE_N=20 TROT_HS_START_PERIOD=0.20 TROT_HS_START_DUTY=0.50 TROT_HS_SPEED_LEAD=0.25 TROT_HS_ACC_GAIN=10 TROT_HS_ACC_LIMIT=4 TROT_HS_STEP_CAP=0.52 TROT_HS_SWING_REACH=0.90 TROT_HS_HYBRID_CONTACT=2 TROT_HS_PITCH_GAIN=24 TROT_HS_PITCH_DAMP=6 TROT_HS_ROLL_GAIN=20 TROT_HS_ROLL_DAMP=10 TROT_HS_STABILITY_GOV=1 bash example/cpp/scripts/run_trot.sh 140 _runs/phase1_lockstep_premotion_startup_20260914/L3 --headless --wall-clock-motion --controller-duration 86 --wbc-full --gait-pattern running-trot --kernel raibert-trot --period 0.14 --duty 0.44 --step-length 0.50 --foot-lift 0.20 --tau-limit 45 --raibert-velocity-gain 0.010 --raibert-max-adjustment 0.06 --preview-horizon 4 --support-anchor-feedback --support-anchor-gain 0.35 --velocity-max-accel 0.80 --velocity-max-decel 1.20 --velocity-max-jerk 4.0 --velocity-command-script example/cpp/configs/phase1_velocity_varying.csv --velocity-max-tracking-lead 0.20 --domain-id 223

Each run_metadata.txt records source HEAD, dirty state, simulator/controller/scene hashes, domain, and argv. Profile SHA256: 9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74.

Raw artifact SHA256 (large raw files remain under _runs):
|run|file|SHA256|
|---|---|---|
|L1|contact_ground_truth.csv|6eb3af3aac427d6d070bad93f1b28ec6f356f39d9d9c44acc3a270461af3bb09|
|L1|contact_ground_truth_analysis.txt|ccf2a7f1b20dc2d928020028ed914911c44f6a411c51c5984b4202ef2c7bbcf9|
|L1|contact_ground_truth_dynamics_analysis.txt|744d41f9e29667501447e2e65dabbe3dbf7a2cb2f7bdd1b4ececec247f1a273c|
|L1|controller.log|e223115091f49b918bc05ba0c884a4622a58fdf98376c05931de2d58f1047201|
|L1|data.csv|5f8f4014fbc89219fc74dfb1e17387ee0b4d0202d821ae86a574613902c212a2|
|L1|data.csv.lockstep_publish.csv|5f1248b1523cbeb0720ca87e9219dcd3bb9ebed57191ef3d10b2295c959d8feb|
|L1|environment.txt|c22fcd04ee2fd5d7e797c7a7872479d7a05fda2d84c062bf03c299753daaa921|
|L1|lockstep_handoff.csv|a3d7a12dfce3e9cac9565ad59e0c7925bf5edbf394c6a6fafd3625d0aa0d7abc|
|L1|lockstep_handoff.csv.bin|bf3a4379adfab77a4c0cf01587ac05888c7525b4326d31020b8a1e4a0cfc1137|
|L1|lockstep_trace.csv|cac0a240f384ec169b30313a4d976876cf1b987af475a4112a6a23a5be544277|
|L1|run_manifest.json|f97e7b7ea94f33cf534757765384ad3f376a427f5002f61453c96c6f96972f02|
|L1|run_metadata.txt|13a521415888c3befb455f7b5aeabc2e77dc623189a2a2c843571a27850981ca|
|L1|simulator.log|2f42621b580227f0d801429b139728385e7fb78a8d8905efa203089a0bafc0ff|
|L2|contact_ground_truth.csv|9ecfc1811707685eec99610d7b169a9a1b4ca3b528d027ffec8efdbd2278ebee|
|L2|contact_ground_truth_analysis.txt|5ae5c53544c0b8cdb035cf149abb8ef6c0a70b5b0c26c34d9e9c876884ac96fe|
|L2|contact_ground_truth_dynamics_analysis.txt|3426a88147e8b2f5513b38deaf7bd151f0f5d27ef5beade1fb073963df79cee3|
|L2|controller.log|4da3774f0807147c978ade7cd5b5d49f6262403ebe4feb50f8f3126e64f0084f|
|L2|data.csv|f33399525a008437951243d8a42d0ab78bfc9d320de1bc5ffdbebc0170532c32|
|L2|data.csv.lockstep_publish.csv|a997b9bd293f45862198d30aa22b872b1c278f0bcf1f9da33ab871b1b96c0180|
|L2|environment.txt|c22fcd04ee2fd5d7e797c7a7872479d7a05fda2d84c062bf03c299753daaa921|
|L2|lockstep_handoff.csv|a3d7a12dfce3e9cac9565ad59e0c7925bf5edbf394c6a6fafd3625d0aa0d7abc|
|L2|lockstep_handoff.csv.bin|bf3a4379adfab77a4c0cf01587ac05888c7525b4326d31020b8a1e4a0cfc1137|
|L2|lockstep_trace.csv|d51ac24cad1131c1db53eb3571c840957bfca5fd66d862652ea23d9a8ee33d1d|
|L2|run_manifest.json|1f229e62ec2a695d0d7aa9f37e1926c461a8509ed7fe266d4a1ae74fd05bd42a|
|L2|run_metadata.txt|18ba9c7bc0d851cde6bc0ddb9446eb1afa5e63dbc446a231ee1d87b444c9128a|
|L2|simulator.log|86562e26e38166852e510940d4fb63f609bc76915f07c19a990bb4345d54adbc|
|L3|contact_ground_truth.csv|aedcb2a08789f9f468e8f607826e73cdf159636db1ef7d8b0e1a08d21e1c1e5b|
|L3|contact_ground_truth_analysis.txt|8247e5ebfdce43caf7455fe5f5f0966c64bcbe100e9427ff66b5b8bf287e8438|
|L3|contact_ground_truth_dynamics_analysis.txt|da41e1b4de1fbf36175eddb21d9aa7985286e563d80b28c225be8bdd9926f1a5|
|L3|controller.log|cd84de07acee0468655dd76663f7a9671c9655cc7b7de41d0833951341cf1434|
|L3|data.csv|8cd4a696e49a1252b4bf26e38d052eeb5755795c4f52048f2c2b2ec4c3bd7f89|
|L3|data.csv.lockstep_publish.csv|58583d574618fbe71dff32c99f992c756ccdcc3a2ed4ae8b97f509d8d66baeb3|
|L3|environment.txt|c22fcd04ee2fd5d7e797c7a7872479d7a05fda2d84c062bf03c299753daaa921|
|L3|lockstep_handoff.csv|a3d7a12dfce3e9cac9565ad59e0c7925bf5edbf394c6a6fafd3625d0aa0d7abc|
|L3|lockstep_handoff.csv.bin|bf3a4379adfab77a4c0cf01587ac05888c7525b4326d31020b8a1e4a0cfc1137|
|L3|lockstep_trace.csv|d1b5cc3b70c7bd6f914f49d9ea9750410af0c9e9740afbe4e09d9fc03cae855f|
|L3|run_manifest.json|ec3681177d72120563b994483402cbfce5f6fd50509ad4e03a32858de6faa6fc|
|L3|run_metadata.txt|d9269f040b0ebd1bad67b2d00167174485089d843f9660a37d0b856bcb29ce1d|
|L3|simulator.log|ac0a3f4ac40051592fa638f39afcb433e9c9536fdc7c1bfc96cc80910ffa9c06|

Scoped source SHA256:
|path|SHA256|
|---|---|
|simulate/src/lockstep.h|21978241c8450e24aad8fbb5a9367f75a478dfe991253b04c91ffab5ddfa1427|
|simulate/src/main.cc|b09333ce2593c2bd641fbd88e26cdf57ee213dcd8042cd640730091cf2d6db57|
|simulate/src/unitree_sdk2_bridge.h|44e1bc6437498579a46fd4883d3c8e6d93cc338b8cb99c9141cd688cc9d05c6c|
|simulate/src/param.h|ca101b1b9b0f02b935d72726b0787f0ce8cf77e918f208243027e0f2dd4fc1cc|
|example/cpp/trot/lockstep_writer_gate.h|f96c7ce9c088f56f5105c9718d3bc63e61fa77458733977eb4c219d61a8f9bab|
|example/cpp/trot/lockstep_motion_clock.h|704a352e39164d22fe74457f4cb9a6fb57f94e7222dfca6dd707ac135603add8|
|example/cpp/trot/trot_experiment.h|f9aa1a426561c46f468ee7e803de866d89606854e5f4d57dfc19a183e4e8ff20|
|example/cpp/trot/trot_experiment_lifecycle.cpp|f33fd7709e0743c41b2b0bda35bec64f8f0c0a72b72f51cc8f4c062ab5fb4edf|
|example/cpp/trot/trot_experiment_control.cpp|52ede281d7e16ec6506469b758040c2601ec1d02d6d19d4a0762dc3ab75bb15d|
|example/cpp/scripts/run_trot.sh|f566b7285687e5ce4746778f0aaf6bf0ce0b7663cbe52963cc683f34be52ffc2|
|example/cpp/tools/analysis/analyze_phase1_lockstep_premotion_startup.py|0bf894bbb3d7b22ca00bb7bd3e0ddb183d41e832d2e43589f6024e49f48cd735|
|example/cpp/configs/phase1_velocity_varying.csv|9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74|
|unitree_robots/go2/scene_leg_lift_demo.xml|12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8|

Derived evidence SHA256:
|file|SHA256|
|---|---|
|handoff_states.csv|17e63aad9d0c9bcb501b465fc8d5a98eb1ee4c69aace4b31f867c916998f78f7|
|protocol_gates.csv|d134cc25d9b623abd34acaad4aee086a504884802eaf374d0ada7c0b3dcbbe8d|
|run_summary.csv|359203b62c3508bb1601b4f4ddbec8a33bb22ff76d341569daecfe091fcf407c|
|pairwise.csv|1c58aacd41fccf5439b37a352102076bf0f4b6435997b36d4e184d683a8d8169|

Checkpoint boundary: exactly three launches and their audit are complete. No fourth launch, D4, A/B intervention, tuning, retry, or follow-up experiment was executed.

Recommended next step: inspect the failing causal/tick protocol gate in a separately authorized checkpoint; not executed here.
