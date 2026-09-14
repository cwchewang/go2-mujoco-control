# Phase1 bounded stance-dq D4 live A/B — 2026-09-14

## Outcome

Result: **INCONCLUSIVE** under the pre-registered task rule.

This checkpoint tested exactly the offline-selected `BOUND_D4` live hypothesis: during active-relative `[32.10,39.90)`, replace baseline `dq_des` only on controller/WBC stance legs with the bounded whole-leg Jacobian correction. The B run completed without a wrapper hard-safety failure and the B isolation gate passed, but the pre-window A/B velocity-excess difference was `-0.037243499 m/s`, outside the required `±0.03 m/s` comparability band. There is no valid infrastructure explanation, so the negative DID is not accepted as a causal tracking result.

## Hypothesis and implementation

A used the unchanged baseline. B enabled the cached default-off `TROT_BOUNDED_STANCE_DQ_D4_AB=1`. For each selected leg the controller used current desired `q_des`, body-frame base velocity from the current orientation/world velocity, body gyro, repository `FootPosition`, and repository `FootJacobian`. It solved with full Eigen 3×3 Jacobi SVD and gates rank `3`, condition `≤1e4`, and residual `≤1e-6 m/s`; invalid solves fell back to baseline.

The applied correction was one scalar per leg:

```text
delta = dq_ss - dq_base
s = min(1, 2/max|delta|, 4/max|kd*delta|)
dq_new = dq_base + s*delta
```

Only `low_cmd_.motor_cmd()[i].dq()` is overwritten after the unchanged q/kp/kd/tau command paths have been constructed. Swing legs, non-target times, stand/preflight/stop, and A retained baseline dq. The relevant source is `example/cpp/trot/trot_experiment_control.cpp` lines 1164–1524 at source commit `50a513f5cadc940def831863b4f90da3e7419228`.

## Provenance and commands

Target branch: `research/phase1-bounded-stance-dq-d4-live-ab-20260914`. The preregistered base was `a79df26d794fcc0e69d5f8ef944ec3b96c4bef32`; offline D4 selection is in ancestor `b22ab67e8c82cb75503c91c743b6707b0d5c83e9`. The implementation commit used for both runs is `50a513f5cadc940def831863b4f90da3e7419228`.

Both arms used the same frozen command, with only the cached flag changed:

```text
TROT_CPU_AUTOPIN=1 TROT_DIAG_ID_CLOSURE=1 TROT_BOUNDED_STANCE_DQ_D4_AB={0|1} GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv bash example/cpp/scripts/run_phase1_velocity_benchmark.sh varying _runs/phase1_bounded_stance_dq_d4_live_ab_20260914/{A|B} 232
```

Run IDs: A `varying_20260914_103232`; B `varying_20260914_103517`. No explicit seed was used. Both metadata records report controller, safety, quality, analysis, ground-truth, dynamics, and completion status `0`; the existing strict analyzer returned `strict_pass=true` for both.

Controller SHA256: `68c33d28e1769fec7b616bd9080b423cfbf38fcfbeb5945021989585100d2f0f`.

Simulator SHA256: `b1fab973122332a8c9051f15746722f86c96860a454c6b77b6481b73c6fd9579`.

Scene SHA256: `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`.

Profile SHA256: `9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74`.

Modified source file SHA256:

```text
example/cpp/trot/trot_experiment.h                 288ae92b7e3b51c96ffb3c1801125f902c48b17aed7c8df21074aed6597ee275
example/cpp/trot/trot_experiment_control.cpp        d3ccdd95e4f4629b8f25322fc6f120bbe5d0aa3e57d5a93a03cb6eacaf103397
example/cpp/trot/trot_experiment_diagnostics.cpp    4e91581455c3bf9ca18c49acb3dbd233dc684dc006144210ff5729dddee764b1
example/cpp/trot/trot_experiment_lifecycle.cpp      02f0f1600f9895280225b4edfab827870dcc2612372b3bb6bfbfa327204a08cb
```

## A baseline reproduction gate

A reached active-relative `80.000005 s`, with `500` rows in `[32,33)`. The median measured-applied velocity excess was `+0.252958393 m/s`; WBC desired ax, SRBD ax, and ID qdd-x medians were `-2.529583929`, `-1.720416217`, and `-2.188675721 m/s²`. Negative-row fractions were `1.000`, `0.900`, and `0.988`; the run remained `continuous-trot` in the gate window. A gate: **PASS**.

## B isolation gate

The B log contains `3725` gate rows spanning active-relative `32.100025723`–`39.899996790 s`; enabled values are `[1]` and gate values are `[0,1]`. The gate-selected correction occurred on `7567` stance-leg events, with `7567` nonzero correction events. Maximum applied `|Δdq|` was `1.408111362 rad/s`, and maximum applied `|kd*Δdq|` was exactly `4.000000000 Nm`. Swing-leg baseline/applied dq identity error was `0.0`; invalid solves were `0`, so invalid-solve fallback was vacuously satisfied. A had zero correction identity error and no gate rows.

The correction scalar `s` over active stance-leg events had p05/median/p95/min/max `0.087956440/0.336517305/0.932250789/0.053258370/1.000000000`. Applied `|Δdq|` had p05/median/p95/min/max `1.104061290/1.237150524/1.362434169/0.121606275/1.408111362`; applied `|kd*Δdq|` had p05/median/p95/min/max `4.000000000/4.000000000/4.000000000/0.415595505/4.000000000 Nm`. Source inspection confirms the helper writes only dq after q/kp/kd/tau have been assigned; the CSV logs unchanged baseline kd and per-joint `kd*(dq_new-dq_base)`.

## Window measurements

`velocity_excess` is measured minus applied. `realized_ax` is the past-100-ms local linear-regression slope of measured velocity. Full-window data are also in `ab.csv`.

| run | window | rows | measured | applied | excess | realized ax | WBC ax | SRBD ax | ID qdd-x | roll p95/max deg | pitch p95/max deg | physical contacts median/min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | pre | 100 | 2.513266100 | 2.279348334 | 0.232944058 | 0.140773984 | -2.329440574 | -1.674447108 | -2.258092616 | 1.0976/1.1675 | 0.9609/1.4747 | 2/0 |
| A | early | 450 | 2.527734808 | 2.272265192 | 0.255469616 | -0.002725970 | -2.554696167 | -1.703615101 | -2.156507227 | 1.0493/1.5365 | 1.3306/1.8989 | 2/0 |
| A | middle | 1500 | 2.521079783 | 2.278920218 | 0.242159565 | 0.046770042 | -2.421595652 | -1.563093511 | -2.190421098 | 1.4530/1.9262 | 1.5092/2.2605 | 2/0 |
| A | late | 1950 | 2.518860425 | 2.281139575 | 0.237720850 | 0.107021075 | -2.377208502 | -1.561544027 | -2.153479240 | 1.5365/2.0312 | 1.6389/2.0310 | 2/0 |
| A | full | 3900 | 2.521317494 | 2.278682505 | 0.242634989 | 0.065092054 | -2.426349896 | -1.587624873 | -2.168460879 | 1.4628/2.0312 | 1.5772/2.2605 | 2/0 |
| B | pre | 99 | 2.494442902 | 2.292350227 | 0.195700559 | 0.270620018 | -1.957005589 | -1.259320597 | -1.961073867 | 1.4614/1.5481 | 1.7318/1.8102 | 2/0 |
| B | early | 450 | 2.485924397 | 2.300000000 | 0.185924397 | 0.152290954 | -1.859243968 | -0.473160316 | -1.737923743 | 4.3901/4.9771 | 3.9883/4.5175 | 2/0 |
| B | middle | 1500 | 2.337872629 | 2.300000000 | 0.037872629 | 0.360544964 | -0.378726285 | 0.803390967 | -0.819105364 | 7.9256/12.0168 | 6.4439/11.3560 | 1/0 |
| B | late | 1951 | 2.313379126 | 2.300000000 | 0.013379126 | 0.410715035 | -0.133791262 | 0.613577493 | -0.796082034 | 8.7093/15.0406 | 7.3346/11.8609 | 1/0 |
| B | full | 3901 | 2.346594646 | 2.300000000 | 0.046594646 | 0.360424065 | -0.465946458 | 0.552634817 | -0.963892898 | 7.9944/15.0406 | 6.7406/11.8609 | 1/0 |

Full-window solver/SRBD/ID-WBC status fractions were `1.0/1.0/1.0` for both arms. B reported measured-speed maximum `3.065195385 m/s`, overshoot excursion maximum `0.265195385 m/s`, roll maximum `15.040626386 deg`, pitch maximum `11.860935108 deg`, and torque saturation fraction `0.001033023`; A corresponding values were `3.078293680 m/s`, `0.278293680 m/s`, `3.608934929 deg`, `3.501291801 deg`, and `0.000916790`. B triggered existing health-governor emergency-support-cap messages but did not trigger a hard safety stop.

## Primary comparison and decision

Pre-window excess: A `0.232944058`, B `0.195700559`, B−A `-0.037243499 m/s`; comparability: **FAIL** because the absolute difference exceeds `0.03 m/s`.

Full-window excess: A `0.242634989`, B `0.046594646`, B−A `-0.196040343 m/s`.

`DID_excess = (B_full−B_pre)−(A_full−A_pre) = -0.158796844 m/s`; negative is improvement, but this DID is not interpretable under the failed pre-window comparability gate. Direct B−A excess changes were early `-0.069545219`, middle `-0.204286937`, late `-0.224341724`, and full `-0.196040343 m/s`.

The original analyzer reported the 1.4→2.3 settling time as A `NaN` (not settled within its transition window) and B `7.887990598 s`; this does not override failed comparability. B had no wrapper hard-safety failure, but its full-window posture/contact degradation is recorded above.

Therefore the pre-registered decision is **INCONCLUSIVE**, not SUPPORTED or NOT SUPPORTED: isolation passed, but comparability failed without a valid infrastructure explanation. This is a live A/B result with an invalid causal comparison, not an offline replay acceptance.

## Raw evidence hashes

A `varying_20260914_103232`:

```text
data.csv                    23148586706ec4e792afb4edf6af331a52fa94fad0517ed60cc4b570757b987f
data.csv.id_closure.csv     893b770c58e00b5017b24b1d84e9b15c0174e216a5fbf25bcd66b16001b7fa32
controller.log              93a4ed359d012e1189938f6d69e04b5e602f74d077468b191565dd570d197c87
simulator.log               98e7e91e456da43d1d8e9e14af38f98a517ad110152a24b2cef9515a5e5c2c39
run_metadata.txt            9d0cdc1d1968c5c936048b527ea1e08900f210c705d1ba74479affc61fdd8474
run_manifest.json           d3905d29051c528e036f2b4151746bf60c5f590bcd3ebc57798102120e6cc123
environment.txt             28633acc2968fd589e005dea595d297b2b0a54243c7620aff27c67fe1ccf62f9
contact_ground_truth.csv    0d37745dab0b640a664f96426206bb168166bd5e7c37f2f04da9f8ea41af98c5
```

B `varying_20260914_103517`:

```text
data.csv                    301a2c54fd96fee00f85b83159d2edff4478994e108114f2561d63dbc3c56176
data.csv.id_closure.csv     a6ef233b5a8413fcc0ce2f58031a8521168d228e959c0fd4404284a261a5deac
controller.log              6fd215ba709b9dd3bb91ff4c559f6be3732d8ce1c82a54f3486de016d0d3d234
simulator.log               8fde095155bc62e7d2d0216d3b76e372e3a038a63f55380db35253eeccd08f86
run_metadata.txt            30f93334454e472d3ba8bda9be4fb8d299cdec8c205030566ae38714c1eb8bb6
run_manifest.json           6e596ddad326ed14d1b9536ca3d7c55ebfafd244b7d997231feb560ff200f304
environment.txt             b5fdbc63d2ea3801544ae39d1c85fc4ec57a59a39120d0ea8f04f5a780b2b971
contact_ground_truth.csv    64710d4a38f621f7a52fbae08b8f068d3ffb939a3e5499915c89e8072ced2a13
```

## Recommendation

Retain this `INCONCLUSIVE` checkpoint and stop. Do not automatically rerun, change the cap, or test another candidate.
