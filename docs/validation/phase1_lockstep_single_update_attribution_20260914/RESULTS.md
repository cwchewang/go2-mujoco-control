# Phase1 lockstep single-update attribution - 2026-09-14

Decision label: PRE_ENGAGEMENT_ONLY

Hypothesis: determine whether the one_command_update_per_state_tick failures in checkpoint 640124d5bdf6cb26e2ecda705ec55fa4c917b825 are caused by pre-handoff free-running writes, post-engagement writer behavior, a second publication path, or simulator accounting.

Scope: one D1 Phase1 varying baseline only. D4 was OFF by environment omission. Period 0.14 s, duty 0.44, the frozen phase1_velocity_varying.csv profile, running-trot, WBC-full, same lockstep protocol and existing analyzers. No controller math, gait, threshold, protocol, or duplicate-write repair was changed.

## Static source audit

The Phase1 trot target is real_trot_go2 (the CMake target contains only trot/* sources). Its only GO2_TROT_TOPIC_LOWCMD publisher is constructed in example/cpp/trot/trot_experiment_lifecycle.cpp and initialized once. The only production writer call chain is:

low_cmd_write_thread_ -> LowCmdWrite -> PublishLowCmdWithCrc -> lowcmd_publisher_->Write.

The writer loop calls LowCmdWrite(true) only in the gated branch and LowCmdWrite(false) in the free-running branch. The exact switch is lockstep_ack_enabled_ && lockstep_epoch_valid_; the epoch is set only by PublishLockstepAck when task_.gait_started_ is true. The first diagnostic gated row was publish index 2152, state tick 3436, command sequence 2152.

lockstep_epoch_valid_, lockstep_epoch_state_seq_, last_consumed_state_tick_, lockstep_cmd_seq_, and lockstep_ack_enabled_ are plain members, not atomics. After initialization, the first four are accessed by the writer thread; lockstep_ack_enabled_ is set before the writer thread starts. WriterGate synchronizes its pending tick and engagement state with its own mutex. The LowState callback copies state under state_mutex_ and forwards ticks to WriterGate::OnLowState; repeated ticks do not create a new pending tick after engagement, while pre-engagement callbacks only update the latest tick.

Static inspection finds no second Phase1 trot publication path. Other LowCmdWrite/LowCmd publisher calls under example/cpp/apps belong to separate executables, not real_trot_go2. Therefore H3 is false by source topology.

The simulator increments cmd_seq_ once per CountingLowCmd DDS arrival. On a new frozen state it stores first_publish_seq_; when the matching ack command arrives, the trace records the current arrival count as cmd_seq_at_ready. The analyzed command delta is cmd_seq_at_ready - cmd_seq_at_publish, exactly the existing exchange-window accounting.

## Diagnostic instrumentation

TROT_LOCKSTEP_PUBLISH_DIAG=1 enabled a CSV written after each production lowcmd_publisher_->Write, with publish index, steady-clock ordering timestamp, consumed state tick, associated command sequence, ack/epoch/gate state, writer branch, lifecycle flags, motion stage, and running time. The associated sequence is the next lockstep_cmd_seq_ value assigned by the immediately following same-cycle ack. With the flag absent, the instrumentation returns before logging and does not alter the legacy writer path.

## Exactly one diagnostic run

Run ID: D1; DDS domain: 204.

Exact invocation:
cd /home/che/dev/go2-workspace/phase1-lockstep-single-update-attribution-20260914
flock /tmp/go2_mujoco_experiment.lock env -u TROT_PD_PULSE_AB -u TROT_FOUR_THIGH_D90_AB -u TROT_BOUNDED_STANCE_DQ_D4_AB -u TROT_BOUNDED_STANCE_DQ_AB -u TROT_SEED -u RUN_SEED SIM_LOCKSTEP=1 TROT_LOCKSTEP_PUBLISH_DIAG=1 GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv TROT_CPU_AUTOPIN=1 TROT_DYNAMICS_TOLERANCE_N=20 TROT_HS_START_PERIOD=0.20 TROT_HS_START_DUTY=0.50 TROT_HS_SPEED_LEAD=0.25 TROT_HS_ACC_GAIN=10 TROT_HS_ACC_LIMIT=4 TROT_HS_STEP_CAP=0.52 TROT_HS_SWING_REACH=0.90 TROT_HS_HYBRID_CONTACT=2 TROT_HS_PITCH_GAIN=24 TROT_HS_PITCH_DAMP=6 TROT_HS_ROLL_GAIN=20 TROT_HS_ROLL_DAMP=10 TROT_HS_STABILITY_GOV=1 bash example/cpp/scripts/run_trot.sh 140 _runs/phase1_lockstep_single_update_attribution_20260914/D1 --headless --wall-clock-motion --controller-duration 86 --wbc-full --gait-pattern running-trot --kernel raibert-trot --period 0.14 --duty 0.44 --step-length 0.50 --foot-lift 0.20 --tau-limit 45 --raibert-velocity-gain 0.010 --raibert-max-adjustment 0.06 --preview-horizon 4 --support-anchor-feedback --support-anchor-gain 0.35 --velocity-max-accel 0.80 --velocity-max-decel 1.20 --velocity-max-jerk 4.0 --velocity-command-script example/cpp/configs/phase1_velocity_varying.csv --velocity-max-tracking-lead 0.20 --domain-id 204

Source HEAD at launch: 612c42467256068b229e90cfa040c221f16d23f8; launch tree was dirty because diagnostic-only changes were uncommitted. Instrumentation-only diff SHA256 at launch: 5b4bcd5f104addd6b9258dac7d70de460b1e84992a5c695386453e0ca326f0de.

Binary and input hashes:

|artifact|SHA256|
|---|---|
|simulator|f2ba506ccd1a48b6a9e7275e4266bb3354123bded164d77f9b6b50aa62c51077|
|controller|66b90779b12921d3660ca9652aa696520eab466faa9c3cd6219e3282173cee74|
|scene|12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8|
|profile|9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74|

## Required analysis

The run produced 43,553 controller publish rows and 43,553 simulator-observed LowCmd arrivals. The trace contained one barrier row and 42,465 lockstep intervals.

|command delta|intervals|fraction|
|---:|---:|---:|
|1|41,420|0.975391499|
|2|1,045|0.024608501|
|3+|0|0|

The complete controller log grouped by consumed state tick contained 1,062 duplicate state ticks and 1,086 extra publishes beyond one per tick. Group sizes were 1,058 groups of 2, and one group each of 3, 4, 5, and 20 rows.

All 1,086 extra controller publishes were before gate engagement: gate=0, writer branch=free. The lifecycle distribution was motion stage 0: 761 extra rows and motion stage 1: 325 extra rows; all had gait_started=0, stop_requested=0, sequence_finished=0. Exact handoff duplicates: 0. Post-engagement duplicates: 0.

The 1,045 simulator intervals with delta greater than 1 ranged from simulator tick 1312 (1.312 s) through tick 3434 (3.434 s). The duplicate controller rows joined to those windows ranged from controller motion time 0.006067977 s through 4.29807118 s. Every one of the 1,045 abnormal simulator intervals had a lossless join to its expected ack row plus one extra controller publish (2,090 joined rows total; unmatched intervals: 0). The full controller log contains 41 additional same-tick extra rows that sit at exchange-window boundaries and are not counted as delta>1 intervals; they do not create an unmatched simulator duplicate.

No actual duplicate controller publish occurred after lockstep_writer_gate_.Engaged()==true for the same consumed state tick. No second production publication path was observed. H4 is rejected: every simulator delta>1 has a corresponding extra controller publish. H2 is rejected for this run: no post-engagement same-tick duplicate exists.

Safety/stability observation: the run metadata reports controller, safety, quality, analyzer, ground-truth, dynamics, completion, and manifest status 0; the simulator reported lockstep_trace_ok rows=42466 dt_ms=2; no fail-closed marker was present. The strict one-command gate itself is nevertheless FAIL because 1,045 of 42,465 lockstep intervals had delta 2.

## Conclusion

The observed failure is PRE_ENGAGEMENT_ONLY with high confidence for this single controlled run. Before the lifecycle epoch becomes valid, the wall-clock writer continues to issue commands while the simulator is holding a frozen physics state for the existing exchange. The current strict gate labels those pre-engagement exchanges as lockstep intervals, so the free-running writes appear as duplicate updates. This attributes the observed duplicates to lifecycle handoff timing; it does not establish a broader physical-controller root cause.

Recommended next step: in a separately authorized protocol checkpoint, align the strict one-command accounting start with the first gated publish (or otherwise explicitly exclude the pre-engagement interval), then re-evaluate the post-engagement gate without changing controller math. No repair was executed here.

## Evidence files

- publish_rows.csv: exact per-publish diagnostic rows (43,553 rows).
- publish_duplicate_summary.csv: duplicate state-tick groups.
- duplicate_interval_join.csv: all 1,045 delta>1 intervals joined to expected and extra controller arrivals.

Raw run directory remains at example/cpp/experiments/_runs/phase1_lockstep_single_update_attribution_20260914/D1/.

Raw artifact hashes:

|raw artifact|SHA256|
|---|---|
|data.csv|ba572fd28691196b801a0038618656098f26308d5375709f5cc16c38b8ba1ba9|
|data.csv.lockstep_publish.csv|33c89b550ab6dcb93c3eb4c541935d11a075eca98575fa9cf2b4759510cde075|
|lockstep_trace.csv|30eb4ee20246af7e3d7d10db5827b3fa07201cc2535e44566250e6fa7aa6be47|
|run_metadata.txt|bd9db381279fa4e462baf87ed19f0b9e01d2d673959571beb2f48268859f56a1|
|run_manifest.json|6c2308d4c21ac4756e6c5aac6413ccf54dc83cf0878dd349e59559dab3268e13|
|simulator.log|faf62f9a2ce6d27eea250e086a0bd383ce7b031b8056277713cfb19594e0b8c0|
|controller.log|bd899ab8c06024224f64d4ece93ddcf6c2646ae52f78a4799516cc9628fe55c3|
|environment.txt|c22fcd04ee2fd5d7e797c7a7872479d7a05fda2d84c062bf03c299753daaa921|
|contact_ground_truth.csv|055673ebef35dac294937bc824bde94e04ff695d3806cf925194aad8934b56ac|

Derived evidence hashes:

|derived artifact|SHA256|
|---|---|
|publish_rows.csv|33c89b550ab6dcb93c3eb4c541935d11a075eca98575fa9cf2b4759510cde075|
|publish_duplicate_summary.csv|ef649b6921c51a74934581e985c5d148bca0469706981791e3bb7aacb9499ae1|
|duplicate_interval_join.csv|056804b2b835ee12f35033ea1f0cbe460fbe4115465c6400094273b72980dbd9|

Scoped source hashes:

|source|SHA256|
|---|---|
|example/cpp/trot/trot_experiment.h|6547e72d29c9ca86d52dd599083217941040f5ab2983cf279afb06ab10d4eda4|
|example/cpp/trot/trot_experiment_lifecycle.cpp|bb59931d9ab015035f4c6ca4a9f27b3f95167da98f7e726fea7fb5fe7128e678|
|example/cpp/trot/trot_experiment_control.cpp|b89a63041f7b8870fdbab77a97faba780a665f5b233201db00233c7c2b29b1ff|
|simulate/src/lockstep.h|5d29ba586502dae03aa62bf435f6e21f72e77aea565ddf9358ffe557f39a0c09|
|simulate/src/main.cc|9b9c6efa310802ba3a2db0fc796f141056dceec70f7b91a9e654cabbbaf4ecaf|
|simulate/src/unitree_sdk2_bridge.h|5bbf284c926c87c63588057dc90af308ef3e7d360830463af8e82cc1edd0d9e9|
|example/cpp/trot/lockstep_writer_gate.h|74607d9e48f0dd3092320d31743d50494068c395cd7c00bad52f22ccfaa2e0c7|
|example/cpp/trot/lockstep_motion_clock.h|704a352e39164d22fe74457f4cb9a6fb57f94e7222dfca6dd707ac135603add8|
|example/cpp/scripts/run_trot.sh|98c93ed801b04dd6032a0eee21d66a696d94d3dd3df47b40cde049be64c0bee1|
|example/cpp/configs/phase1_velocity_varying.csv|9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74|
|unitree_robots/go2/scene_leg_lift_demo.xml|12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8|

Checkpoint boundary: this is one attribution checkpoint. No duplicate-write repair, second baseline, D4 experiment, or threshold/gait/control-law change was executed after D1.
