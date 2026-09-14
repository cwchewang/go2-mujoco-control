# Phase1 post-engagement lockstep determinism - 2026-09-14

Hypothesis: once strict one-command-per-state accounting begins at the first production LowCmd publish with gate=1 and writer_branch=gated, the frozen Phase1 varying-profile baseline will satisfy the lockstep protocol and be sufficiently reproducible for a causal D4 A/B.

Decision: LOCKSTEP_BASELINE_STILL_NONDETERMINISTIC.

Scope: exactly three sequential baseline launches L1, L2, and L3. Varying profile, running-trot, WBC-full, period=0.14 s, duty=0.44, D4 and all prior A/B flags OFF, SIM_LOCKSTEP=1, fixed CPU affinity, and distinct DDS domains. No controller math, gait/WBC/SRBD/ID behavior, bridge handshake, writer gate, motion clock, scene, profile, timestep, or acceptance threshold was changed.

The existing publish diagnostic was enabled only with TROT_LOCKSTEP_PUBLISH_DIAG=1. It is default-off outside this harness and records each production publish after lowcmd_publisher_->Write. The source tree was clean at each launch (git_dirty=false).

## Protocol boundary

The strict interval set starts at the first diagnostic row with gate_engaged=1 and writer_branch=gated. Its lockstep_cmd_seq selects simulator intervals with cmd_seq_at_publish greater than or equal to that sequence. Earlier intervals remain audit-only and are excluded from post-engagement PASS/FAIL.

|run|first gated publish|state tick|command seq|running time s|pre intervals|post intervals|pre span s|pre delta counts|post delta counts|post duplicate extras|
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|
|L1|2152|3950|2152|4.302072280|1090|41401|2.180000000|1:50,2:1039,3:1|1:41401|0|
|L2|2152|4074|2152|4.302073900|1145|41401|2.290000000|1:164,2:980,3:1|1:41401|0|
|L3|2152|3486|2152|4.302074650|1071|41401|2.142000000|1:12,2:1059|1:41401|0|

boundary_audit.csv independently records the exact boundary and pre/post counts. Pre-engagement deltas are reported but not used in the strict gate.

## Per-run gates and physical baseline

|run|protocol|physical|active-relative s|[32,33) rows|regime|measured median|applied median|excess median|WBC ax median|SRBD ax median|ID qdd-x median|
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
|L1|PASS|PASS|80.002000000|500|continuous-trot|2.526610221|2.273389779|0.253220441|-2.532204413|-1.966901288|-2.279961784|
|L2|PASS|PASS|80.002000000|500|continuous-trot|2.526165841|2.273834159|0.252331681|-2.523316817|-1.882311997|-2.243981583|
|L3|PASS|PASS|80.002000000|500|continuous-trot|2.524969238|2.275030762|0.249938477|-2.499384770|-1.786376252|-2.264189163|

Physical gates require active-relative >=40 s, no hard safety stop before 40 s, continuous-trot in [32,33), and the residual-overspeed/braking-demand regime. Detailed per-run gate rows are in protocol_gates.csv.

## Determinism analysis

Rows were filtered to active rows at or after each first gated running time and aligned only by diag_active_relative_time_s. A fixed 10 ms grid with maximum nearest-time tolerance 10 ms was used over the common post-engagement prefix; wall-clock timestamps were not used as truth. Contact-mask bits are FR/FL/RR/RL at bit positions 0/1/2/3; gait phase is the logged phase field.

|pair|post prefix s|grid points|excess p50/p95/max|measured p50/p95/max|roll p50/p95/max deg|pitch p50/p95/max deg|first sustained divergence s|before 40 s|
|---|---|---:|---|---|---|---|---:|---:|
|L1__L2|4.310000000-80.000000000|7570|0.006328054/0.070240024/0.187212126|0.005001968/0.044677578/0.142350815|0.106816780/1.214747081/3.279342619|0.117977453/1.162130889/3.209831265|13.390000000|13.390000000|
|L1__L3|4.310000000-80.000000000|7570|0.006446731/0.060333212/0.188780077|0.005063121/0.038461257/0.130412252|0.102909293/0.916108710/2.860616926|0.114844004/0.847779503/3.583251236|4.420000000|4.420000000|
|L2__L3|4.310000000-80.000000000|7570|0.006336431/0.066104353/0.191754272|0.005192230/0.043115091/0.156739706|0.122468755/1.121186150/3.040443970|0.111694856/1.067516669/3.668211939|4.420000000|4.420000000|

The complete required p50/p95/max values for measured velocity, applied velocity, velocity excess, roll, pitch, contact count/mask, and gait phase are in pairwise.csv.

Pre-registered gates: all post-engagement protocol gates PASS=true; all physical baseline gates PASS=true; velocity-excess range=0.003281964 m/s <=0.010=true; no pair has sustained divergence before 40 s=false.

## Provenance and exact launch command

Source HEAD: de00ff0fee553aed38de375f71c0b9ae9feb6b7d.
Branch: research/phase1-lockstep-post-engagement-determinism-20260914.
Frozen simulator SHA256: b2296e02739f7763d2496b18428be267d366e439a3e2b51da9503e3a05dcdd21.
Frozen controller SHA256: 34d84b8290be65aa52580afab0f738597a2b6f522501913aaeff11f15f87f477.
Scene SHA256: 12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8.
Profile SHA256: 9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74.

    flock /tmp/go2_mujoco_experiment.lock env -u TROT_PD_PULSE_AB -u TROT_FOUR_THIGH_D90_AB -u TROT_BOUNDED_STANCE_DQ_D4_AB -u TROT_BOUNDED_STANCE_DQ_AB -u TROT_SEED -u RUN_SEED SIM_LOCKSTEP=1 TROT_LOCKSTEP_PUBLISH_DIAG=1 GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv TROT_CPU_AUTOPIN=1 TROT_DYNAMICS_TOLERANCE_N=20 TROT_HS_START_PERIOD=0.20 TROT_HS_START_DUTY=0.50 TROT_HS_SPEED_LEAD=0.25 TROT_HS_ACC_GAIN=10 TROT_HS_ACC_LIMIT=4 TROT_HS_STEP_CAP=0.52 TROT_HS_SWING_REACH=0.90 TROT_HS_HYBRID_CONTACT=2 TROT_HS_PITCH_GAIN=24 TROT_HS_PITCH_DAMP=6 TROT_HS_ROLL_GAIN=20 TROT_HS_ROLL_DAMP=10 TROT_HS_STABILITY_GOV=1 bash example/cpp/scripts/run_trot.sh 140 _runs/phase1_lockstep_post_engagement_determinism_20260914/L1 --headless --wall-clock-motion --controller-duration 86 --wbc-full --gait-pattern running-trot --kernel raibert-trot --period 0.14 --duty 0.44 --step-length 0.50 --foot-lift 0.20 --tau-limit 45 --raibert-velocity-gain 0.010 --raibert-max-adjustment 0.06 --preview-horizon 4 --support-anchor-feedback --support-anchor-gain 0.35 --velocity-max-accel 0.80 --velocity-max-decel 1.20 --velocity-max-jerk 4.0 --velocity-command-script example/cpp/configs/phase1_velocity_varying.csv --velocity-max-tracking-lead 0.20 --domain-id 211

L2 used the identical command with run directory _runs/phase1_lockstep_post_engagement_determinism_20260914/L2 and domain 212. L3 used the identical command with run directory _runs/phase1_lockstep_post_engagement_determinism_20260914/L3 and domain 213. No fourth launch was run.

## Raw artifact SHA256

|run|file|SHA256|
|---|---|---|
|L1|contact_ground_truth.csv|016034573faa0294f515b734168caa4698357df953717f26fd70377d57f1d7e9|
|L1|contact_ground_truth_analysis.txt|e97af49e5d18b5080ed849e6f6f2c0844b5ef720bc026238ab1fa585c6bca1d6|
|L1|contact_ground_truth_dynamics_analysis.txt|de247c2ef0064fe75b74c3c1083de96eae545be2edb4fd300a3678255a25de92|
|L1|controller.log|a5d97a466a8caa22f3c1054a4a1f06707a7b3fc36185dd7ff997d1e148a1b3fe|
|L1|data.csv|cb6a105acccd47f5489f53d9ba92b94ccfaa0ccf8e86feabffedf032bd4f65c9|
|L1|data.csv.lockstep_publish.csv|63b3e4f3f22cad0b596f4ca6e0187b5f99e256c65686caef240c34ced63e678f|
|L1|environment.txt|c22fcd04ee2fd5d7e797c7a7872479d7a05fda2d84c062bf03c299753daaa921|
|L1|lockstep_trace.csv|a0fb650c7833e79aa2640c0ba042b137780e6522c8ff0a6bd75908e72f0fc007|
|L1|run_manifest.json|3dd225783918338695ce0ddb97b6fa19d2ab75c3be078e37e51f8a9af8831b03|
|L1|run_metadata.txt|800ed876bcc591137b0c3691bc8ebf01e707114071ceace816680cf4d05dc12a|
|L1|simulator.log|beda2aff22c1ab9ee1a22a22fb601da0b382c7b5544697ae5cdf162a69871039|
|L2|contact_ground_truth.csv|09e3d9d8f7275245e2699efc8950d80fa6afa1920c9616f174bfced926ba4c82|
|L2|contact_ground_truth_analysis.txt|d03ba24a6dd9cf5a1db26f822cdcb7e64980694ccc4503548617b94c950b00f7|
|L2|contact_ground_truth_dynamics_analysis.txt|e084429c214dba4b289bbb60830a49339ca696aa4d32a7b7f5f2bef7963590be|
|L2|controller.log|6f07c393be4e6873851f2dc6156ec481c0a4a81ca88e64e47df9be5a4267526b|
|L2|data.csv|c1c56d5643ee88441edbfb0fa3ef1afe31df67b7da8d4aa46f8f1509ab370438|
|L2|data.csv.lockstep_publish.csv|b1efd8e6c17533dc0edaf6939e6f92a4243c1184ca50b1d927eda32a63fa1b88|
|L2|environment.txt|c22fcd04ee2fd5d7e797c7a7872479d7a05fda2d84c062bf03c299753daaa921|
|L2|lockstep_trace.csv|55bca78b0055af0180f67d7cdbf636c99abe84a8d379ae2b98ae68898f8514e4|
|L2|run_manifest.json|6d180ad5061d0f46a42893c98c1715290e6ad1173d168eb5503e9c7d7d430dde|
|L2|run_metadata.txt|8996725a9784063da3caee34227d34d17eea997e9da862a56a3a854338355fd3|
|L2|simulator.log|62be39f8365111a2a4911167539bb286493ecee98dcb64a0cd1a580d6ba2287a|
|L3|contact_ground_truth.csv|866fa3917843731508be035cb9268d0e8ed1e658b9b89352850262f93841722f|
|L3|contact_ground_truth_analysis.txt|27b3ccd78c4b534b6997e7254023e56c1e95ef413ec9506f13b6c61d43fce1c7|
|L3|contact_ground_truth_dynamics_analysis.txt|5f0d9ea5f710ae3426935002531ff5eb5f596cdc3e80c20965060bdfd874ea6c|
|L3|controller.log|f909d50b61be14c9f0be485fdec3482838123c56c8c263e7c3cf2892eda96e4e|
|L3|data.csv|bbe6f8215c24f4a38455026b70c8b9b796507d9a2dba8200b6ba9da2cc9f4926|
|L3|data.csv.lockstep_publish.csv|7564eda3f57db697d4da4832a37eaa773d2c735bc164ec9e9d6826f853eb54b0|
|L3|environment.txt|c22fcd04ee2fd5d7e797c7a7872479d7a05fda2d84c062bf03c299753daaa921|
|L3|lockstep_trace.csv|d8b51f652d241e006fe70b5b6130d1434f07885bf31272e58c5c971077ae96d7|
|L3|run_manifest.json|8e8b6e53483123eef9b57b120af9424c39096b76e1cdd91cc79e8449746d93bf|
|L3|run_metadata.txt|795eb7939a1bd080ecbc67a4ff26b01b44327ddc5da047ab55f77ab9f2c032c4|
|L3|simulator.log|7e8990586f663cc5baa59fd169e5dda3d643ab762738c705d7e352ea173ff962|

## Derived evidence SHA256

|file|SHA256|
|---|---|
|boundary_audit.csv|9c875961c59007d3d12b61a07fe4a8719acf64d7aef7da38347a557b3d274f71|
|protocol_gates.csv|93e9a64af5d4d581133df58f57492855d25dae3cfc42437cf64fe00367dca998|
|run_summary.csv|3d01dbcd90915645c113db746e9bc6f3f666795de56c1c8c3bfcc3ac9dbf399d|
|pairwise.csv|a0798497c8ceb13a9eb7783ed72a2e217609ec34878dc89a524fb32b7ec4aabf|

## Scoped source SHA256

|path|SHA256|
|---|---|
|simulate/src/lockstep.h|5d29ba586502dae03aa62bf435f6e21f72e77aea565ddf9358ffe557f39a0c09|
|simulate/src/main.cc|9b9c6efa310802ba3a2db0fc796f141056dceec70f7b91a9e654cabbbaf4ecaf|
|simulate/src/unitree_sdk2_bridge.h|5bbf284c926c87c63588057dc90af308ef3e7d360830463af8e82cc1edd0d9e9|
|example/cpp/trot/lockstep_writer_gate.h|74607d9e48f0dd3092320d31743d50494068c395cd7c00bad52f22ccfaa2e0c7|
|example/cpp/trot/lockstep_motion_clock.h|704a352e39164d22fe74457f4cb9a6fb57f94e7222dfca6dd707ac135603add8|
|example/cpp/trot/trot_experiment.h|6547e72d29c9ca86d52dd599083217941040f5ab2983cf279afb06ab10d4eda4|
|example/cpp/trot/trot_experiment_lifecycle.cpp|bb59931d9ab015035f4c6ca4a9f27b3f95167da98f7e726fea7fb5fe7128e678|
|example/cpp/trot/trot_experiment_control.cpp|b89a63041f7b8870fdbab77a97faba780a665f5b233201db00233c7c2b29b1ff|
|example/cpp/scripts/run_trot.sh|98c93ed801b04dd6032a0eee21d66a696d94d3dd3df47b40cde049be64c0bee1|
|example/cpp/configs/phase1_velocity_varying.csv|9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74|
|unitree_robots/go2/scene_leg_lift_demo.xml|12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8|

Checkpoint boundary: exactly three authorized baseline launches and their post-engagement analysis are complete. No D4, fourth run, tuning, controller repair, or acceptance-threshold change was executed.

Recommended next step: resolve the remaining post-engagement determinism failure in a separately authorized verification checkpoint; not executed here.
