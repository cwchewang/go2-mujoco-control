# Phase1 four-thigh D90 live A/B

## Outcome

Result: **NOT SUPPORTED**.

This checkpoint tests only the pre-registered `THIGH_D_90` candidate: four thigh-joint kd values retain 90% during the declared active-relative gate. The first A launch was excluded as infrastructure-invalid because the newly added diagnostics were initially emitted in a different order from the CSV header; it was replaced within the task's third-launch allowance. The reported A/B pair below is the corrected A replacement plus the single B run.

## Hypothesis and unique variable

B enabled `TROT_FOUR_THIGH_D90_AB=1`; A used `TROT_FOUR_THIGH_D90_AB=0`. Motor-order indices 1/4/7/10 (FR_thigh/FL_thigh/RR_thigh/RL_thigh) alone use `effective_kd = 0.90 * baseline_kd` when active-relative `gait_elapsed_s` is in `[32.10,39.90)`. The flag is cached once in `Init`; no phase/contact gate is used. q/dq targets, kp, tau_ff, non-thigh kd, controller/WBC quantities, model, scene, profile, and acceptance behavior are unchanged by this intervention.

## Provenance

Target branch: `research/phase1-four-thigh-d90-live-ab-20260914`; source git head: `d5ca0a2d7fa1d9b4b57d3b91af0ddfbb021d4dca`; run metadata reports `git_dirty=true` because the source diff is the experiment plumbing.

Both corrected arms used the same command, binary, simulator, scene, profile, domain, and no explicit seed:

```text
TROT_CPU_AUTOPIN=1 TROT_DIAG_ID_CLOSURE=1 TROT_FOUR_THIGH_D90_AB={0|1} GO2_PROFILE_PATH=example/cpp/configs/phase1_velocity_varying.csv bash example/cpp/scripts/run_phase1_velocity_benchmark.sh varying _runs/phase1_four_thigh_d90_live_ab_20260914/{A_replacement|B} 232
```

Controller SHA256: `96fb64eab01d1d0ea5a4167afbce0565864fb2fe4248a4cd35ee716154ad20ab`; simulator SHA256: `a28995d205e161661824ccd118b41ebb22e9cfa5b338e4a793701cee118cb370`; scene SHA256: `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`; profile SHA256: `9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74`.

Modified source SHA256:
- `example/cpp/trot/trot_experiment.h`: `5450dd611e4e03f65ae32a91124b731037fc53b083c2da727ea5bfb76f85b3ce`
- `example/cpp/trot/trot_experiment_lifecycle.cpp`: `c3c173bc1fa0013215d6f44a24633594d29696a29c0f8f18ab12af83bd11dd89`
- `example/cpp/trot/trot_experiment_control.cpp`: `634d525f8643136ed48c93ca21ec504c81f5d0048f2d87a2aa22b76a7eb1aa27`
- `example/cpp/trot/trot_experiment_diagnostics.cpp`: `146b0e7947d9212920b44d965f37ced8787fb2b06121a4eab1fa553e4b521e6f`

Final run IDs: A `varying_20260914_081132`; B `varying_20260914_081347`; both wrapper status fields controller/safety/quality/analysis/ground_truth/dynamics/completion are `0`.

## A baseline reproduction gate

A reached active-relative `80.002 s`; the `[32,33)` gate has `500` rows and median measured−applied `+0.234625 m/s`. WBC desired/SRBD/ID qdd-x medians are `-2.346251`/`-1.758235`/`-2.216149` m/s². The negative fractions are computed from raw rows: WBC `1.000`, SRBD `0.880`, ID `0.986`. A gate: **PASS**.

## A/B comparability

Pre-window `[31.90,32.10)`: A excess `0.236351`, B excess `0.228220`, B−A `-0.008130` m/s; A/B measured `2.516968`/`2.512640`, applied `2.278967`/`2.282483` m/s. Roll/pitch p95 A→B are `0.665012`→`0.956796` and `1.398967`→`1.066232` degrees; physical contact-count medians are `2.000`→`2.000`. The excess difference is within the ±0.03 m/s gate and no obvious pre-window posture/contact divergence is present: **PASS**.

## Intervention proof

A: enabled values `[0]`, gate values `[0]`, gate rows `0`, observed gate time `NaN`–`NaN` s, gate condition **PASS**, max `effective−0.90*baseline` error `NaN`, outside-gate identity error `0.000000000`.
B: enabled values `[1]`, gate values `[0, 1]`, gate rows `3899`, observed gate time `32.101995`–`39.897993` s, gate condition **PASS**, max `effective−0.90*baseline` error `0.000000001`, outside-gate identity error `0.000000000`.

B's four logged effective kd values are exactly 0.90 of their corresponding baseline values inside the half-open gate and identical outside it. The source switch maps only indices 1, 4, 7, and 10; the source diff does not alter q/dq/kp/tau_ff or any non-thigh kd path.

## Window measurements

`kernel_nominal_mps` is reported as the runtime controller's applied command because `BuildGaitTargets` explicitly assigns `kernel_nominal_velocity_x_mps_ = direction_sign * applied_mps` for this runtime velocity-command profile; the closure CSV independently records the same field in the capture window. Realized ax is the same past-100-ms local linear-regression slope used by the prior Phase1 analysis. Contact masks use physical foot-force flags and the existing internal WBC contact mask.

|run|window|data_rows|requested_mps|shaped_mps|applied_mps|kernel_nominal_mps|measured_mps|velocity_excess_median_mps|target_error_abs_median_mps|realized_ax_100ms_p05_mps2|realized_ax_100ms_median_mps2|realized_ax_100ms_p95_mps2|wbc_desired_ax_mps2|srbd_ax_mps2|id_qdd_x_mps2|governor_active_fraction|shaped_applied_gap_max_mps|roll_abs_p95_deg|roll_abs_max_deg|pitch_abs_p95_deg|pitch_abs_max_deg|physical_contact_count_median|physical_contact_count_min|physical_masks|internal_masks|mask_mismatch_fraction|lowcmd_tau_ff_max_abs_median_nm|effective_tau_max_abs_median_nm|tau_est_max_abs_median_nm|solver_ok_fraction|srbd_ok_fraction|id_wbc_ok_fraction|d90_enabled_values|d90_gate_values|fr_baseline_kd|fr_effective_kd|fl_baseline_kd|fl_effective_kd|rr_baseline_kd|rr_effective_kd|rl_baseline_kd|rl_effective_kd|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|A|pre|100.00000|2.30000|2.30000|2.27897|2.27897|2.51697|0.23635|0.21697|-0.08431|0.13141|0.39368|-2.36351|-1.94618|-2.16045|1.00000|0.02911|0.66501|0.67083|1.39897|1.63096|2.00000|0.00000|0:23|2:1|4:4|6:36|8:7|9:29|0:3|6:43|9:48|11:1|13:1|15:4|0.36000|10.30936|32.57359|25.16085|1.00000|1.00000|1.00000|0|0|3.33933|3.33933|3.15448|3.15448|3.15555|3.15555|3.34314|3.34314|
|A|early|450.00000|2.30000|2.30000|2.28282|2.28282|2.51718|0.23436|0.21718|-0.56836|0.05910|0.42711|-2.34359|-1.58668|-2.21225|0.81333|0.05200|1.50141|1.86743|1.71126|2.23904|2.00000|0.00000|0:118|1:10|2:3|4:35|6:127|8:18|9:139|0:20|1:3|6:211|9:201|11:3|15:12|0.38444|8.87230|33.36258|26.28307|1.00000|1.00000|1.00000|0|0|3.25643|3.25643|3.25653|3.25653|3.27096|3.27096|3.27438|3.27438|
|A|middle|1499.00000|2.30000|2.30000|2.27573|2.27573|2.52427|0.24855|0.22427|-0.48891|0.02413|0.38433|-2.48546|-1.65071|-2.16542|0.92061|0.05187|1.31127|1.88582|1.47447|1.91914|2.00000|0.00000|0:366|1:26|2:11|4:121|6:465|8:54|9:456|0:62|1:6|6:712|9:660|11:11|15:48|0.37225|8.87760|32.66047|26.36866|1.00000|1.00000|1.00000|0|0|3.29452|3.29452|3.22211|3.22211|3.23922|3.23922|3.30094|3.30094|
|A|late|1951.00000|2.30000|2.30000|2.27689|2.27689|2.52311|0.24621|0.22311|-0.48576|0.01712|0.39899|-2.46212|-1.58373|-2.19850|0.89185|0.05198|1.33322|1.99314|1.47634|2.08294|2.00000|0.00000|0:486|1:28|2:12|4:155|6:587|8:78|9:605|0:81|1:10|6:919|9:866|11:16|13:2|15:57|0.37160|9.00595|32.46382|26.17850|1.00000|1.00000|1.00000|0|0|3.27520|3.27520|3.23392|3.23392|3.25078|3.25078|3.28762|3.28762|
|A|full|3900.00000|2.30000|2.30000|2.27705|2.27705|2.52295|0.24590|0.22295|-0.50880|0.02275|0.39609|-2.45905|-1.61454|-2.18381|0.89385|0.05200|1.36315|1.99314|1.51027|2.23904|2.00000|0.00000|0:970|1:64|2:26|4:311|6:1179|8:150|9:1200|0:163|1:19|6:1842|9:1727|11:30|13:2|15:117|0.37333|8.93269|32.69185|26.27361|1.00000|1.00000|1.00000|0|0|3.27706|3.27706|3.22907|3.22907|3.24922|3.24922|3.29241|3.29241|
|B|pre|100.00000|2.30000|2.30000|2.28248|2.28248|2.51264|0.22822|0.21264|-0.05877|0.09624|0.34499|-2.28220|-1.54291|-2.06390|1.00000|0.02880|0.95680|1.02513|1.06623|1.10373|2.00000|0.00000|0:24|2:2|4:5|6:33|8:4|9:32|0:3|6:43|9:48|11:2|15:4|0.36000|10.24652|32.22512|26.49745|1.00000|1.00000|1.00000|1|0|3.35241|3.35241|3.13931|3.13931|3.17389|3.17389|3.35387|3.35387|
|B|early|450.00000|2.30000|2.30000|2.27336|2.27336|2.52664|0.25328|0.22664|-0.52816|0.07622|0.41181|-2.53283|-1.62670|-2.32720|0.92889|0.05417|1.51594|1.88458|1.69957|2.04081|2.00000|0.00000|0:117|1:15|2:3|4:43|6:119|8:17|9:136|0:21|1:4|6:209|9:199|11:3|15:14|0.40889|9.32605|32.13627|25.84363|1.00000|1.00000|1.00000|1|1|3.25535|2.92981|3.25411|2.92870|3.27179|2.94461|3.27614|2.94853|
|B|middle|1500.00000|2.30000|2.30000|2.27460|2.27460|2.52540|0.25080|0.22540|-0.52644|0.05779|0.41467|-2.50802|-1.65304|-2.30288|0.91133|0.05555|1.56824|2.46909|1.58258|2.28990|2.00000|0.00000|0:395|1:30|2:9|4:134|6:438|8:57|9:437|0:63|1:14|6:709|9:657|11:9|13:1|15:47|0.39667|9.33042|31.86210|26.31079|1.00000|1.00000|1.00000|1|1|3.28666|2.95799|3.22804|2.90524|3.24911|2.92420|3.31210|2.98089|
|B|late|1949.00000|2.30000|2.30000|2.27761|2.27761|2.52239|0.24478|0.22239|-0.74776|0.06934|0.49564|-2.44784|-1.62883|-2.28437|0.81632|0.06808|1.62924|2.19020|1.77175|2.61471|2.00000|0.00000|0:484|1:59|2:18|4:180|6:551|8:94|9:563|0:84|1:18|6:920|8:2|9:854|11:16|15:55|0.40328|9.32891|31.86802|26.36569|1.00000|1.00000|1.00000|1|1|3.27751|2.94976|3.23582|2.91224|3.25078|2.92571|3.30426|2.97384|
|B|full|3899.00000|2.30000|2.30000|2.27574|2.27574|2.52426|0.24852|0.22426|-0.64548|0.06424|0.45320|-2.48515|-1.64909|-2.29837|0.86586|0.06808|1.60950|2.46909|1.69843|2.61471|2.00000|0.00000|0:996|1:104|2:30|4:357|6:1108|8:168|9:1136|0:168|1:36|6:1838|8:2|9:1710|11:28|13:1|15:116|0.40138|9.32891|31.88208|26.31090|1.00000|1.00000|1.00000|1|1|3.27722|2.94950|3.23585|2.91226|3.25078|2.92571|3.30338|2.97305|

## Primary causal effects

DID_excess = `(B_full−B_pre)−(A_full−A_pre)` = **0.010741 m/s**; negative is improvement. Early B−A excess is `0.018925` m/s, full B−A excess `0.002611` m/s, measured velocity `0.001305` m/s, and realized ax `0.041491` m/s². Full overspeed peak from the unchanged analyzer is A/B `3.073993`/`3.076499` m/s, B−A `0.002506` m/s.

Direct B−A by window (excess / measured / realized ax):

- `pre`: `-0.008130` m/s / `-0.004328` m/s / `-0.035174` m/s²
- `early`: `0.018925` m/s / `0.009462` m/s / `0.017123` m/s²
- `middle`: `0.002256` m/s / `0.001128` m/s / `0.033663` m/s²
- `late`: `-0.001428` m/s / `-0.000714` m/s / `0.052216` m/s²
- `full`: `0.002611` m/s / `0.001305` m/s / `0.041491` m/s²

## Original Phase1 settling analyzer

A original analyzer 1.4→2.3 transition: `FAIL (not settled within analyzer transition window)`, settling latency `NaN s`, excursion `0.252005 m/s`; strict analyzer pass `True`.
B original analyzer 1.4→2.3 transition: `FAIL (not settled within analyzer transition window)`, settling latency `NaN s`, excursion `0.268080 m/s`; strict analyzer pass `True`.

## Safety, posture, contact, and interpretation

A/B had no hard safety failure (`safety_status=0`); full-window roll/pitch p95 are A `1.363145`/`1.510269` versus B `1.609502`/`1.698431` degrees, and maxima are A `1.993142`/`2.239035` versus B `2.469094`/`2.614713` degrees. B physical contact masks are `0:996|1:104|2:30|4:357|6:1108|8:168|9:1136` versus A `0:970|1:64|2:26|4:311|6:1179|8:150|9:1200`; mismatch fractions are A/B `0.3733`/`0.4014`. Solver/SRBD/ID status fractions remain 1.0 in both full windows.

The comparability gate passes, but the primary criterion requires DID_excess ≤ −0.02 m/s and observed DID is `0.010741`; early plateau excess change is `0.018925` m/s and the original 1.4→2.3 settling result does not improve in B. Therefore D90 is **NOT SUPPORTED** for real closed-loop tracking. This is a calibrated physical A/B result, not an offline replay causality claim.

## Raw evidence hashes

A `varying_20260914_081132`:
- `data.csv`: `c9251400deb9d5b7b35b27a0d2b48aea5a3c1e9203b038979a84706d7b7d2886`
- `data.csv.id_closure.csv`: `1bc6588fecf06dd0c4fbcab979d4a6ed9d08d737a640fd881ee0d5e54e77ccc4`
- `controller.log`: `77d02fccbfbb879096e0eb0b2cb4c7e3f376a034e33fd47b2f26ec1de87bbb92`
- `simulator.log`: `48e307de34b98bb1cf3105e97fd774491d36e5ec629df4f97430325234b056ff`
- `run_metadata.txt`: `83e96c1e95226c4ea0b2b350189560377e9f069d322a7ee1ad9c9dfc41de58a6`
- `run_manifest.json`: `5ca118cf3998228fe8c39fbc5329e4883b820e411da96658de94da5a6b9f550b`
- `environment.txt`: `d1e56d0e6cfa622a6ce2e07f21b47ba7ae4a88e14296936eced8606e559e8922`
- `contact_ground_truth.csv`: `6c248a2e9d1c3ad19dd404a6284f5e6382de24bdb6a164ed7d242214591c6dce`
B `varying_20260914_081347`:
- `data.csv`: `b71d4c039c0e353bd1761bf277782e712f8cb1350317c89ad48eb3d9c7e43585`
- `data.csv.id_closure.csv`: `405914f183b73c3c95a68cad38d63c289c14f4df098060df573a39cc3a17210c`
- `controller.log`: `5d7d890e252bec74376862f6239a529895c6e9c9de47d4ddc4e304db3874a334`
- `simulator.log`: `bba638ca59da275e7caab6cfca0b6db2db6fccc1eceaee2591e5aa7f834d29b6`
- `run_metadata.txt`: `d82dd6e582abd1b12849b59cce8bd0ab872d5c6ef0e3827fe136d34c5f0a414a`
- `run_manifest.json`: `c1118d17770a5f1e919c72f8bb4743722d6995a5077d3405d1a9335e335c35f6`
- `environment.txt`: `cd3a82662f9b05b4db1c449ea7440e1f642510653fe821b977484dfadab7c622`
- `contact_ground_truth.csv`: `d200d22e3b73cf91fa561118aa3fec8e8c064ca972b43ec611fa8aed685a0eeb`

## Next step

One next recommendation only, not executed: retain this NOT SUPPORTED result and obtain human approval for a new single-variable actuator-composition isolation that preserves the stable baseline gait before any further live run. Do not scan THIGH_D_80/70 or tune other controller parameters.
