# Phase1 baseline reproducibility audit - 2026-09-14

## Result

Classification: NONREPRODUCIBLE_BASELINE.

All three new frozen baseline runs reached active-relative about 80 s, remained continuous-trot through [32,33), passed the strict analyzer, and had no hard safety. However, the [32,33) median measured-minus-applied velocity excess was 0.214988434, 0.253537919, and 0.243529304 m/s; the range is 0.038549485 m/s, greater than the pre-registered 0.03 m/s limit. Under the task rules this is a nonreproducible baseline, even though all three runs reached the regime.

This checkpoint does not test D4. D4 remained explicitly disabled for all launches.

## Hypothesis and authorized protocol

The hypothesis was that the unchanged Phase1 varying-profile baseline would reproduce the 2.3 m/s regime under one frozen source tree, one frozen controller/simulator binary pair, one scene/profile, fixed CPUs, fresh processes, and identical commands.

The task authorized exactly three sequential baseline launches. The runs were A1 varying_20260914_111659, A2 varying_20260914_112006, and A3 varying_20260914_112206. No additional launch, tuning, synchronization, seed plumbing, or controller change was made.

## Stage 0 source audit

The exact path is run_phase1_velocity_benchmark.sh varying ... 232 (lines 17-59), which selects phase1_velocity_varying.csv, duration 86, the unchanged running-trot/WBC-full command, and DDS domain 232. run_trot.sh (lines 25-35) resolves autopin to simulator CPU 2 and controller CPU 3 on this host (nproc=8); A1-A3 also set these values explicitly through TROT_CPU_AFFINITY_SIM=2 and TROT_CPU_AFFINITY_CTRL=3.

No functional RNG was found on this path. TROT_SEED and RUN_SEED occur only in run_trot.sh:199, where they are copied to metadata; no controller or simulator code consumes them. No rand, srand, C++ random engine, distribution, scene randomization, or MuJoCo randomization hook is used by this benchmark. MuJoCo optional control noise exists in simulate/mujoco/simulate.h:252-253 with both defaults 0.0 and is guarded by simulate/src/main.cc:1408-1422; the headless benchmark does not enable the UI noise controls. Therefore fixing the seed is not an available causal control here.

The simulator loads the scene with mj_loadXML, allocates mj_makeData, and calls mj_forward (simulate/src/main.cc:1529-1561). The headless path does not call mj_resetDataKeyframe; the static home keyframe remains defined in unitree_robots/go2/go2.xml:298-301 but is not selected by this launch. The controller initializes DDS, waits for the piped newline, initializes TrotExperiment, sends stop-mode defaults from trot_experiment_lifecycle.cpp:23-38, waits for a natural settled LowState for up to 8 s, then records current joint positions as its start pose (lines 75-132 and 257-263).

The runner starts the simulator and polls Unitree DDS bridge ready every 50 ms, up to 10 s (run_trot.sh:263-290), then starts the controller immediately (lines 299-328). The simulator physics loop sleeps or yields and runs its own sync-to-wall loop (simulate/src/main.cc:1380-1435); the controller writes commands from an independent thread at dt using sleep_until (trot_experiment_lifecycle.cpp:265-278). LowState arrives through an asynchronous DDS callback with subscriber depth 1 (lines 41-55 and 223-240). With wall-clock-motion, MotionClockStep replaces state-tick motion time by the controller writer steady_clock delta (trot_experiment_control.cpp:696-762), while recording state-tick gaps and pauses. DDS delivery, thread scheduling, startup overlap after the ready marker, and wall-clock tick alignment are available run-to-run mechanisms, but these runs do not isolate any one as causal.

run_trot.sh also takes a per-domain lock and rejects a stale simulator (lines 158-170). Each new run used headless mode, fresh run directories, domain 232, explicit CPUs 2/3, closure diagnostics, and D4 value 0. The external /tmp/go2_mujoco_experiment.lock was held for each launch.
## Frozen provenance

The target branch was clean at source commit 40d634d200adfbd9f6e070edbc8c91d9b28832ed. The simulator and controller were built once in native WSL with Release CMake builds before A1, and were not rebuilt between A1-A3.

Canonical runtime command template:

~~~
TROT_CPU_AUTOPIN=1 TROT_CPU_AFFINITY_SIM=2 TROT_CPU_AFFINITY_CTRL=3 TROT_DIAG_ID_CLOSURE=1 TROT_BOUNDED_STANCE_DQ_D4_AB=0 TROT_DYNAMICS_TOLERANCE_N=20 TROT_HS_START_PERIOD=0.20 TROT_HS_START_DUTY=0.50 TROT_HS_SPEED_LEAD=0.25 TROT_HS_ACC_GAIN=10 TROT_HS_ACC_LIMIT=4 TROT_HS_STEP_CAP=0.52 TROT_HS_SWING_REACH=0.90 TROT_HS_HYBRID_CONTACT=2 TROT_HS_PITCH_GAIN=24 TROT_HS_PITCH_DAMP=6 TROT_HS_ROLL_GAIN=20 TROT_HS_ROLL_DAMP=10 TROT_HS_STABILITY_GOV=1 bash example/cpp/scripts/run_phase1_velocity_benchmark.sh varying _runs/phase1_baseline_reproducibility_audit_20260914/<A1|A2|A3> 232
~~~

The launch shell also carried TROT_BOUNDED_STANCE_DQ_AB=0; source search confirms this is not read anywhere, so it had no runtime effect and was constant across all three runs. TROT_PD_PULSE_AB, TROT_FOUR_THIGH_D90_AB, TROT_EXPLORATORY_CONTINUE, TROT_SEED, and RUN_SEED were unset. The profile was fixed by the command-line argument, with SHA256 9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74. GO2_PROFILE_PATH was not introduced because it only populates runner metadata and has no runtime effect.

| artifact | SHA256 |
|---|---|
| simulator | 35270f17c7974b97df31d96f4fa38d589664e996c9a3b6ae254d82c4665c1abc |
| controller | 05aa10bd065f1a5bc06d9aec52bbf15fb0f6944b2e7100b9e576fa4d2a1b0a8e |
| scene scene_leg_lift_demo.xml | 12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8 |
| varying profile | 9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74 |

Current runtime source files are unchanged relative to the previous D4 implementation commit 50a513f5; git diff 50a513f5..HEAD over example/cpp, simulate, and unitree_robots is empty. Historical successful A used source 50a513f5, simulator b1fab973..., controller 68c33d28...; historical failed A used source 30074fcc, simulator 23a5f6d7..., controller 508e782f.... Both historical runs used the same scene/profile, domain 232, headless mode, CPUs 2/3, D4 0, and closure 1. Their binary hashes differ, but metadata does not identify a behavioral cause; the new audit uses one exact frozen binary pair for all three runs.
## A1/A2/A3 results

run_summary.csv contains the full derived table, including the two named historical A runs. For the three new runs:

| run | active-relative s | strict | safety | [32,33) rows | measured | applied | excess | WBC ax | SRBD ax | ID qdd-x | roll max deg | pitch max deg | min height m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | 80.001480127 | true | 0 | 499 | 2.507494217 | 2.292505783 | 0.214988434 | -2.149884350 | -1.549559988 | -2.126023516 | 3.386311719 | 3.747022169 | 0.343102474 |
| A2 | 80.002039862 | true | 0 | 500 | 2.526768960 | 2.273231040 | 0.253537919 | -2.535379190 | -1.582389897 | -2.213972824 | 3.464841429 | 3.409692122 | 0.344249242 |
| A3 | 80.000018502 | true | 0 | 500 | 2.521764652 | 2.278235348 | 0.243529304 | -2.435293044 | -1.574422992 | -2.135170937 | 3.385948235 | 3.480997177 | 0.344028653 |

All three have controller, quality, analysis, ground-truth, dynamics, and completion status 0; contact median/minimum is 2/0; torque-saturation fractions are 0.000888946, 0.000999556, and 0.001055344. The gate negative-row fractions for WBC, SRBD, and ID are respectively (1.000000, 0.851703, 0.989980), (1.000000, 0.930000, 0.980000), and (1.000000, 0.920000, 0.984000).

A1 was launched with an outer path missing the _runs/ prefix, so that wrapper's analyzer initially looked in the wrong location. The runner wrote valid raw A1 data under _runs; the same existing data was then analyzed directly with the unchanged strict analyzer and returned strict_pass=true. No fourth launch and no runtime-data edit occurred. A2 and A3 used the correct _runs/ template and completed normally.

## Trajectory divergence audit

The new runs were filtered to continuous-trot active rows and aligned by diag_active_relative_time_s on a fixed 10 ms grid with maximum nearest-time tolerance 10 ms. trajectory_pairwise.csv contains median and p95 absolute differences for measured velocity, applied velocity, velocity excess, roll, pitch, physical contact count, controller contact mask, and gait phase.

| pair | common end s | measured median/p95 m/s | applied median/p95 m/s | excess median/p95 m/s | roll median/p95 deg | pitch median/p95 deg | first divergence s |
|---|---:|---:|---:|---:|---:|---:|---:|
| A1/A2 | 80.001480127 | 0.013446151/0.076942167 | 0.000037212/0.040304211 | 0.016466357/0.083893664 | 0.291894724/1.426331448 | 0.232915251/1.327181904 | 3.01 |
| A1/A3 | 80.000018502 | 0.013310653/0.072213212 | 0.000036004/0.039663819 | 0.016040822/0.080133382 | 0.288382091/1.398340684 | 0.216816168/1.245472221 | 3.02 |
| A2/A3 | 80.000018502 | 0.011227893/0.045907644 | 0.000003330/0.029152256 | 0.013117379/0.067996834 | 0.207228349/1.188235514 | 0.169837353/1.170019696 | 20.93 |

The descriptive threshold was fixed before interpreting late-run outcomes: first sustained interval where forward-velocity difference exceeds 0.05 m/s or roll/pitch difference exceeds 2 deg for 100 ms. It is a locator, not an acceptance gate. The earliest new-run divergence is A1/A2 at 3.01 s, before the [32,33) gate. Controller contact masks were identical on the grid; physical contact-count p95 differences reached 1 because transitions did not always align exactly.

Historical successful A versus A1 has similar early divergence at 3.02 s despite different binary hashes. Historical failed A versus A1 reaches the threshold at 1.61 s; its common prefix ends at 29.020011491 s and its hard failure is the logged posture/safety stop. Thus the failed trajectory was already separated long before final posture collapse; no endpoint value is assigned to its missing [32,33) gate.
## Raw evidence hashes

Raw files remain in the native-WSL _runs directories. Hashes below cover each new run's data, closure data, logs, metadata, manifest, environment, contact ground truth, and strict analysis output.

~~~
A1 varying_20260914_111659
data.csv 7290127547c2db4fd29c891a73bbba5802273a45eddd6d050a0c3d764ca383a1
data.csv.id_closure.csv 753156f7804e7d98734f6b1dd9a986dac8de2c2650d8215643d90d77af5d388a
controller.log 2bcc300a37e33e3a846166c5d7b1920f9b1a0ffa7188bb0d7fe2453a24651773
simulator.log 9ba0bd243f5de73fe4da1e21910148ce95202ccbc800e88186cfb18577b6f953
run_metadata.txt 8cedf36298a5bc62534537a72d48456a788218ad2e74a2024b6737bdafc64f33
run_manifest.json 2e4d2aab4fc236d59aae8885c792cd1857e5ae16b0bb0092ee21e1e1b618a292
environment.txt ab748537b320ad872cae259ac53319677cd8bb0c7b391911580e16fc23a40120
contact_ground_truth.csv d5ff6e204ffad15805f4b7f0839986bd25b48aadec7ac0ff3d3a504c66cd9d41
phase1_velocity_analysis.txt 0698cfad70094e8040b079dc54c9fcb0f7be677ff2ff0e7abefdd4ef764f5645

A2 varying_20260914_112006
data.csv a789fc760cf28517246d01f4a550c3fbb06365666b302d55e3dc8ec6ad3053cd
data.csv.id_closure.csv e7148607f0943fcfca028d9d7cf96ffb3fe8f354605577677759b743e2fcaa09
controller.log f3be1b8f2468e9f76fa4452d52f678064cbff4d2e287e0cbe66a9fca00a9a766
simulator.log 60bf07783501f100f8d768f75221b3411a94df8151245f52b6d832748321af91
run_metadata.txt 1f8d675d8b6d1b0825e0b1b7bcb8f4b756ebcb464b6eff33bf94a9490db3983c
run_manifest.json bd1ee20ee8930fbe4cbc0c404d4355bdd5f252aba8b57b4efaf75d4b5747386b
environment.txt ab748537b320ad872cae259ac53319677cd8bb0c7b391911580e16fc23a40120
contact_ground_truth.csv 129ecacafc9db9bfbf6d810f70aa76dda79b981d17af33b6479ae2e402a0c694
phase1_velocity_analysis.txt 3f90be9b007d1ee98f0eaca419b91ceaed76a023be2b74ac75652f9d83718a1d

A3 varying_20260914_112206
data.csv bf95d964ca053087497c50387ae4d4a7563e5ecc06d71f08af35fa9f12c5be3b
data.csv.id_closure.csv 7827f91243b9cd4e5cab0de8c49563d7a6b4c3b341fe622de8ee33c4c0c9ff85
controller.log 2bb9e92568c121364453bc9c9298651346edb409c926a2ec3b72feeb9bf64391
simulator.log 97f788c860a69ff618ce88f06d261bb930017a4ba7d7e864d49b1d2dbc268ae8
run_metadata.txt 9052e89414d32af86d3d6969752dea1cd16675b37b7085e9c5f32dc01c38c468
run_manifest.json b1019812ce7c6f0b33c39f107c8c7af2e04aa381779cca9a938826c52ed0e58b
environment.txt ab748537b320ad872cae259ac53319677cd8bb0c7b391911580e16fc23a40120
contact_ground_truth.csv f6e6f3002c9a791495843f3d02ec03c083efa8b2e3fe9ead17ccc16c29139d85
phase1_velocity_analysis.txt c81dea468625f7942f606ec6bcb154c777d41eb0c3bb53918f9f79e14e7e2dfb
~~~

## Conclusion

The unchanged baseline is stable enough in all three launches to reach the 2.3 m/s regime, and the frozen runs share the same simulator/controller/scene/profile hashes and explicit CPU affinity. Nevertheless, the gate excess range violates the pre-registered <=0.03 m/s reproducibility criterion, and trajectory differences appear by about 3 s. The evidence therefore supports NONREPRODUCIBLE_BASELINE, not a physical root-cause attribution and not a D4 result.

## Recommendation

Next step: isolate the earliest wall-clock/DDS scheduling divergence with a separately authorized instrumentation-only task; not executed here.
