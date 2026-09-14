# Phase1 bounded stance-dq offline screen

Result: **LIVE-CANDIDATE-ELIGIBLE: BOUND_D4**.

This is exactly one offline same-state checkpoint. No new MuJoCo trajectory, live A/B, gain scan, gait scan, controller benchmark, parameter search, or follow-up experiment was executed.

## Hypothesis and unique variable

A small scalar correction of controller-stance `dq_des` toward the prior Jacobian-consistent stationary-support solution can retain a consistent instantaneous braking direction while respecting a per-joint 2 rad/s change cap and one of the predeclared D-target caps 2/4/6 Nm.

The prior full-rank solution is reproduced with the same q-target FK, restored-state local body twist, repository foot Jacobian, and SVD gates. In this screen `dq_ss` is the complete unbounded SVD solution; the bounded candidate is `dq_base + s_leg*(dq_ss-dq_base)`. The prior ±10 rad/s clamp is retained only as an audit field and is not applied before the scalar bound. Only controller-stance dq changes; swing dq, q/kp/kd/tau_ff, state, contacts, model, and WBC/SRBD/ID outputs remain ACTUAL.

## Candidate construction

For each stance leg, `s_leg = min(1, 2/max(abs(delta_dq_raw)), cap/max(abs(kd*delta_dq_raw)))`, with an inactive constraint treated as infinity. The entire three-joint correction direction is preserved; joints are not independently clipped. `D_CAP`, `DQ_CAP`, `BOTH`, `NONE`, and exact-zero cases are recorded per leg/sample.

## Validation gates

The replay selected 552 snapshots and emitted 1,656 candidate rows plus 6,624 leg/candidate rows. This is 1,100 controller-stance leg samples per candidate, 3,300 across the three candidates. All gate values are computed from the emitted audit CSVs; the binary independently checked the MuJoCo 3.3.6, mjtNum=8, `mjSTATE_INTEGRATION`, nq=19, nv=18, na=0, nu=12 signature.
Maximum snapshot↔atomic ctrl residual: `0.000000000000 Nm`; maximum captured bridge-formula residual: `0.000000000000 Nm`; maximum ACTUAL restored-state qacc[0] residual: `0.000000000000 m/s²`; maximum candidate bridge-formula residual: `0.000000000000 Nm`.
Controller join maximum absolute gap: `10.000000 ms`. Stance samples across candidates: `3300`; per candidate: `1100`; valid: `3300`; invalid: `0`; invalid fraction: `0.000000`. Minimum SVD rank: `3`; maximum condition number: `4.181536`; maximum pre-clamp residual: `0.000000000000 m/s`.
Maximum unchanged q/kp/kd/tau_ff audit: `0.000000000000`; maximum swing dq change: `0.000000000000 rad/s`; actual/candidate physical contact-mask mismatches: `0`.

| gate | result |
|---|---|
| `target_rows` | PASS |
| `snapshot_ctrl_reconstruction` | PASS |
| `bridge_formula` | PASS |
| `actual_qacc_replay` | PASS |
| `candidate_formula` | PASS |
| `q_kp_kd_tau_unchanged` | PASS |
| `swing_dq_unchanged` | PASS |
| `same_state_contact_mask` | PASS |
| `controller_join_within_10ms` | PASS |
| `all_stance_solves_valid` | PASS |
| `invalid_fraction` | PASS |
| `dq_caps` | PASS |
| `d_target_caps` | PASS |
| `candidate_changes_only_stance` | PASS |

All validation gates pass.

## Promotion screen

`delta_ax = qacc_candidate[0] - qacc_actual[0]`; negative is the desired instantaneous braking direction. Promotion additionally requires the full-window and stratum gates in the task, including at least 0.15 m/s median stance mismatch-norm reduction.

| candidate | n | median | p05 | p95 | frac<0 | frac>0 | median abs | zero frac | baseline norm | candidate norm | norm reduction | eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `BOUND_D2` | 552 | -0.450908 | -0.845331 | 0.000000 | 0.922 | 0.004 | 0.450908 | 0.074 | 3.517896 | 3.412128 | 0.105768 | NO |
| `BOUND_D4` | 552 | -0.901763 | -1.690986 | 0.000000 | 0.924 | 0.002 | 0.901763 | 0.074 | 3.517896 | 3.287072 | 0.230824 | YES |
| `BOUND_D6` | 552 | -1.350385 | -2.537993 | 0.000000 | 0.924 | 0.002 | 1.350385 | 0.074 | 3.517896 | 3.192824 | 0.325072 | YES |

Promotion gate details:

- `BOUND_D2`: median=PASS, fraction_negative=PASS, fraction_positive=PASS, controller_medians=PASS, phase_medians=PASS, mismatch_reduction=FAIL, caps=PASS
- `BOUND_D4`: median=PASS, fraction_negative=PASS, fraction_positive=PASS, controller_medians=PASS, phase_medians=PASS, mismatch_reduction=PASS, caps=PASS
- `BOUND_D6`: median=PASS, fraction_negative=PASS, fraction_positive=PASS, controller_medians=PASS, phase_medians=PASS, mismatch_reduction=PASS, caps=PASS

## Phase and contact strata

The following are `delta_ax` metrics. Contact-mask strata with n<20 are marked small-n; physical masks are audit-only.

### BOUND_D2

| stratum | n | median | p05 | p95 | frac<0 | frac>0 | small-n |
|---|---:|---:|---:|---:|---:|---:|---|
| phase:[0,0.25) | 159 | -0.623719 | -0.876770 | -0.150317 | 1.000 | 0.000 | no |
| phase:[0.25,0.5) | 120 | -0.367915 | -0.684840 | -0.052002 | 1.000 | 0.000 | no |
| phase:[0.5,0.75) | 155 | -0.418295 | -0.832647 | 0.000000 | 0.723 | 0.013 | no |
| phase:[0.75,1) | 118 | -0.497078 | -0.745549 | -0.094310 | 1.000 | 0.000 | no |
| controller_contact_mask:mask0 | 41 | 0.000000 | 0.000000 | 0.000000 | 0.000 | 0.000 | no |
| controller_contact_mask:mask6 | 232 | -0.526584 | -0.817000 | -0.102963 | 0.991 | 0.009 | no |
| controller_contact_mask:mask9 | 240 | -0.508008 | -0.866179 | -0.055559 | 1.000 | 0.000 | no |
| controller_contact_mask:mask15 | 39 | -0.250230 | -0.450156 | -0.032774 | 1.000 | 0.000 | no |
| physical_contact_mask:mask0 | 129 | -0.369452 | -0.474764 | 0.000000 | 0.736 | 0.016 | no |
| physical_contact_mask:mask1 | 3 | -0.711233 | -0.722661 | -0.071123 | 0.667 | 0.000 | yes |
| physical_contact_mask:mask4 | 43 | -0.601388 | -0.622236 | -0.388221 | 1.000 | 0.000 | no |
| physical_contact_mask:mask6 | 170 | -0.491107 | -0.830812 | -0.070585 | 1.000 | 0.000 | no |
| physical_contact_mask:mask8 | 24 | -0.649747 | -0.669520 | -0.614999 | 0.958 | 0.000 | no |
| physical_contact_mask:mask9 | 183 | -0.520730 | -0.875204 | -0.032730 | 0.962 | 0.000 | no |
### BOUND_D4

| stratum | n | median | p05 | p95 | frac<0 | frac>0 | small-n |
|---|---:|---:|---:|---:|---:|---:|---|
| phase:[0,0.25) | 159 | -1.247254 | -1.753136 | -0.283085 | 1.000 | 0.000 | no |
| phase:[0.25,0.5) | 120 | -0.735513 | -1.368996 | -0.069030 | 1.000 | 0.000 | no |
| phase:[0.5,0.75) | 155 | -0.836590 | -1.668616 | 0.000000 | 0.729 | 0.006 | no |
| phase:[0.75,1) | 118 | -0.991409 | -1.484791 | -0.188234 | 1.000 | 0.000 | no |
| controller_contact_mask:mask0 | 41 | 0.000000 | 0.000000 | 0.000000 | 0.000 | 0.000 | no |
| controller_contact_mask:mask6 | 232 | -1.052480 | -1.637766 | -0.209491 | 0.996 | 0.004 | no |
| controller_contact_mask:mask9 | 240 | -1.013508 | -1.742139 | -0.105227 | 1.000 | 0.000 | no |
| controller_contact_mask:mask15 | 39 | -0.500049 | -0.899739 | -0.166581 | 1.000 | 0.000 | no |
| physical_contact_mask:mask0 | 129 | -0.738904 | -0.949528 | 0.000000 | 0.744 | 0.008 | no |
| physical_contact_mask:mask1 | 3 | -1.423069 | -1.448520 | -0.142307 | 0.667 | 0.000 | yes |
| physical_contact_mask:mask4 | 43 | -1.202669 | -1.243938 | -0.776442 | 1.000 | 0.000 | no |
| physical_contact_mask:mask6 | 170 | -0.978004 | -1.665562 | -0.178326 | 1.000 | 0.000 | no |
| physical_contact_mask:mask8 | 24 | -1.299273 | -1.338902 | -1.229701 | 0.958 | 0.000 | no |
| physical_contact_mask:mask9 | 183 | -1.040895 | -1.750469 | -0.045584 | 0.962 | 0.000 | no |
### BOUND_D6

| stratum | n | median | p05 | p95 | frac<0 | frac>0 | small-n |
|---|---:|---:|---:|---:|---:|---:|---|
| phase:[0,0.25) | 159 | -1.870630 | -2.629104 | -0.421661 | 1.000 | 0.000 | no |
| phase:[0.25,0.5) | 120 | -1.102860 | -2.052797 | -0.061481 | 1.000 | 0.000 | no |
| phase:[0.5,0.75) | 155 | -1.254885 | -2.506445 | 0.000000 | 0.729 | 0.006 | no |
| phase:[0.75,1) | 118 | -1.486593 | -2.224996 | -0.280278 | 1.000 | 0.000 | no |
| controller_contact_mask:mask0 | 41 | 0.000000 | 0.000000 | 0.000000 | 0.000 | 0.000 | no |
| controller_contact_mask:mask6 | 232 | -1.577824 | -2.457954 | -0.327905 | 0.996 | 0.004 | no |
| controller_contact_mask:mask9 | 240 | -1.518516 | -2.621075 | -0.155595 | 1.000 | 0.000 | no |
| controller_contact_mask:mask15 | 39 | -0.744236 | -1.334653 | -0.298745 | 1.000 | 0.000 | no |
| physical_contact_mask:mask0 | 129 | -1.108356 | -1.419133 | 0.000000 | 0.744 | 0.008 | no |
| physical_contact_mask:mask1 | 3 | -2.135122 | -2.175264 | -0.213512 | 0.667 | 0.000 | yes |
| physical_contact_mask:mask4 | 43 | -1.806806 | -1.867516 | -1.152791 | 1.000 | 0.000 | no |
| physical_contact_mask:mask6 | 170 | -1.464506 | -2.501107 | -0.293108 | 1.000 | 0.000 | no |
| physical_contact_mask:mask8 | 24 | -1.948620 | -2.008893 | -1.844166 | 0.958 | 0.000 | no |
| physical_contact_mask:mask9 | 183 | -1.560567 | -2.625444 | -0.033673 | 0.962 | 0.000 | no |

## Bounded correction and foot-velocity audit

Limiter fractions are over valid controller-stance leg samples. Per-leg/per-joint distributions and all per-sample values are in `joint_summary.csv`, `leg_summary.csv`, and `screen_legs.csv`.

| candidate | s median | s p05/p95 | D_CAP | DQ_CAP | BOTH | NONE | ZERO | max abs dq change | max abs D-target change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `BOUND_D2` | 0.029554 | 0.022895/0.037156 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.694651324056 | 2.000000000000 |
| `BOUND_D4` | 0.059109 | 0.045789/0.074313 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.389302648112 | 4.000000000000 |
| `BOUND_D6` | 0.087847 | 0.068155/0.111469 | 0.857 | 0.143 | 0.000 | 0.000 | 0.000 | 2.000000000000 | 6.000000000000 |

Per-leg/per-joint bounded correction distributions (median/p05/p95):

| candidate | leg.joint | delta dq rad/s | delta D-target Nm |
|---|---|---|---|
| `BOUND_D2` | FR.hip | 0.007103/-0.004901/0.023207 | 0.023022/-0.016222/0.083709 |
| `BOUND_D2` | FR.thigh | -0.506373/-0.614798/-0.214448 | -1.643190/-2.000000/-0.776468 |
| `BOUND_D2` | FR.calf | 0.606674/0.553487/0.672376 | 2.000000/1.991317/2.000000 |
| `BOUND_D2` | FL.hip | 0.016783/-0.017247/0.027663 | 0.051955/-0.059587/0.084134 |
| `BOUND_D2` | FL.thigh | -0.518467/-0.625527/-0.277251 | -1.680173/-1.958971/-0.982500 |
| `BOUND_D2` | FL.calf | 0.630936/0.563833/0.687844 | 2.000000/2.000000/2.000000 |
| `BOUND_D2` | RR.hip | -0.002681/-0.015433/0.011981 | -0.009258/-0.049664/0.035122 |
| `BOUND_D2` | RR.thigh | -0.512996/-0.642519/-0.273505 | -1.647690/-2.000000/-0.972111 |
| `BOUND_D2` | RR.calf | 0.618275/0.562703/0.687824 | 2.000000/1.945237/2.000000 |
| `BOUND_D2` | RL.hip | 0.015973/-0.002011/0.031435 | 0.055028/-0.006098/0.101668 |
| `BOUND_D2` | RL.thigh | -0.495847/-0.629888/-0.204231 | -1.631186/-2.000000/-0.736584 |
| `BOUND_D2` | RL.calf | 0.604849/0.552809/0.671441 | 2.000000/1.941486/2.000000 |
| `BOUND_D4` | FR.hip | 0.014206/-0.009802/0.046415 | 0.046045/-0.032444/0.167417 |
| `BOUND_D4` | FR.thigh | -1.012746/-1.229595/-0.428896 | -3.286380/-4.000000/-1.552935 |
| `BOUND_D4` | FR.calf | 1.213348/1.106973/1.344752 | 4.000000/3.982633/4.000000 |
| `BOUND_D4` | FL.hip | 0.033566/-0.034493/0.055325 | 0.103911/-0.119175/0.168268 |
| `BOUND_D4` | FL.thigh | -1.036933/-1.251053/-0.554503 | -3.360346/-3.917942/-1.965001 |
| `BOUND_D4` | FL.calf | 1.261872/1.127665/1.375689 | 4.000000/4.000000/4.000000 |
| `BOUND_D4` | RR.hip | -0.005362/-0.030865/0.023962 | -0.018515/-0.099329/0.070244 |
| `BOUND_D4` | RR.thigh | -1.025992/-1.285038/-0.547010 | -3.295381/-4.000000/-1.944222 |
| `BOUND_D4` | RR.calf | 1.236549/1.125406/1.375648 | 4.000000/3.890474/4.000000 |
| `BOUND_D4` | RL.hip | 0.031945/-0.004021/0.062870 | 0.110057/-0.012195/0.203336 |
| `BOUND_D4` | RL.thigh | -0.991694/-1.259776/-0.408461 | -3.262372/-4.000000/-1.473168 |
| `BOUND_D4` | RL.calf | 1.209697/1.105618/1.342882 | 4.000000/3.882972/4.000000 |
| `BOUND_D6` | FR.hip | 0.021309/-0.014703/0.069622 | 0.069067/-0.048666/0.251126 |
| `BOUND_D6` | FR.thigh | -1.519119/-1.844393/-0.643344 | -4.929570/-6.000000/-2.329403 |
| `BOUND_D6` | FR.calf | 1.820022/1.660460/2.000000 | 6.000000/5.913430/6.000000 |
| `BOUND_D6` | FL.hip | 0.050069/-0.051740/0.082988 | 0.154744/-0.178762/0.252402 |
| `BOUND_D6` | FL.thigh | -1.555400/-1.876580/-0.831754 | -5.040519/-5.876913/-2.947501 |
| `BOUND_D6` | FL.calf | 1.892808/1.691498/2.000000 | 6.000000/5.815269/6.000000 |
| `BOUND_D6` | RR.hip | -0.008043/-0.046298/0.035122 | -0.027773/-0.148993/0.103230 |
| `BOUND_D6` | RR.thigh | -1.538988/-1.927556/-0.820515 | -4.943071/-6.000000/-2.916333 |
| `BOUND_D6` | RR.calf | 1.854824/1.688108/2.000000 | 6.000000/5.800473/6.000000 |
| `BOUND_D6` | RL.hip | 0.047918/-0.006022/0.094305 | 0.165085/-0.018266/0.305004 |
| `BOUND_D6` | RL.thigh | -1.487541/-1.889664/-0.612692 | -4.893559/-6.000000/-2.209752 |
| `BOUND_D6` | RL.calf | 1.814546/1.658427/2.000000 | 6.000000/5.824458/6.000000 |

Baseline versus candidate stationary-support mismatch norm and x-component, full valid stance samples:

| candidate | baseline norm median/p05/p95 m/s | candidate norm median/p05/p95 m/s | baseline x median/p05/p95 m/s | candidate x median/p05/p95 m/s |
|---|---|---|---|---|
| `BOUND_D2` | 3.517896/2.374082/4.537020 | 3.412128/2.297252/4.409396 | -2.317585/-3.700819/0.393225 | -2.247881/-3.597019/0.381566 |
| `BOUND_D4` | 3.517896/2.374082/4.537020 | 3.287072/2.215623/4.279347 | -2.317585/-3.700819/0.393225 | -2.172933/-3.494291/0.367056 |
| `BOUND_D6` | 3.517896/2.374082/4.537020 | 3.192824/2.137477/4.149247 | -2.317585/-3.700819/0.393225 | -2.095372/-3.394797/0.352582 |

## Provenance and reproduction

Analysis branch: `research/phase1-bounded-stance-dq-screen-20260914`; source HEAD before this checkpoint commit: `053c415cb969579a5ebee333afcd960beece3ca7`.

Exact replay command:

```text
./example/cpp/build/replay_bounded_stance_dq unitree_robots/go2/scene_leg_lift_demo.xml /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin /home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv docs/validation/phase1_bounded_stance_dq_screen_20260914/screen.csv docs/validation/phase1_bounded_stance_dq_screen_20260914/screen_legs.csv docs/validation/phase1_bounded_stance_dq_screen_20260914/replay_summary.txt
```

Exact analysis command:

```text
python3 example/cpp/tools/analysis/analyze_bounded_stance_dq.py
```

Scene SHA256: `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8`; replay binary SHA256: `4dd2b8ae80714cfc5591e8b6e7862870d6cbbde74acb42e8947537c0ffc94b09`.

Source SHA256:
- `example/cpp/kinematics/go2_forward_kinematics.h`: `e83e9ca01d3ad91686e4cb554bdfbde94e3e9321d3df25d88f3c4b0f1014f4ad`
- `example/cpp/kinematics/go2_leg_jacobian.h`: `06a3c82d113eeb56b43aa20da4f16062212adc8e26301fb444d9b453105d383d`
- `example/cpp/tools/analysis/replay_bridge_atomic.cpp`: `3bf22eb2f4d740ba1daa31623c3527fc35c1fb0a9eb2d07869b03e908d069e67`
- `example/cpp/tools/analysis/replay_bounded_stance_dq.cpp`: `6e37ce12057b45f94b7cf7a4c615a18a50cad25abeb4671294f2f259dd6fad81`
- `example/cpp/tools/analysis/analyze_bounded_stance_dq.py`: `45835ca4df9c9c1990e471b1454d2cbc325a16c2e3c35cf2f40bc47c1bd88401`
- `simulate/src/unitree_sdk2_bridge.h`: `2f6b6e76e4d067dff602ec1304228e9e66c44a37783f449b47af00e412b527bb`

Raw evidence SHA256:
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/bridge_atomic_snapshots.bin`: `b6e17e79ec3fcf24895c122138c8e146118fc1820274e6e6e3bb334c5e619527`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv`: `a97190a3d8e08abaf1ad351e5bdb9bcd11d68a158238cd9a082a39696a592cb0`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/data.csv.id_closure.csv`: `8467468090dc61f6830d24fd3700916d479ed5ae402f0715c9703894b2bea21c`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/run_metadata.txt`: `390f277d2d6137a2da710ed66b8d5644c8e1c73e7b0225620cb28c251b50e2f1`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/run_manifest.json`: `953d2df6bbf07f46becd97125113eb7c5856a08ad09dd427001b38ad3d825848`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/environment.txt`: `cdc389432b3bef410b9e4a29a7135f79ff999776992f0b176b86bb7949fcbeb2`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/controller.log`: `6c3d89e8ecea82f002ace864302449968d50e9c986fcde4f1ad187b7326f81bc`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/simulator.log`: `22b4d09a64fabca39c1ade8d8f54569260b3b4a20fe8d1c7b27d15046fb1e4e5`
- `/home/che/dev/go2-workspace/phase1-bridge-atomic-replay-20260913/example/cpp/experiments/_runs/phase1_bridge_atomic_replay_20260913/varying_20260913_231049/contact_ground_truth.csv`: `82ba48480134f00ecf8139c858c1da0da283d0d684264fc6ba465a929127323d`
- `/home/che/dev/go2-workspace/phase1-bounded-stance-dq-screen-20260914/example/cpp/configs/phase1_velocity_varying.csv`: `9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74`

Derived outputs:

- `screen.csv` (1,656 candidate/snapshot rows)
- `screen_legs.csv` (6,624 candidate/leg/snapshot rows)
- `screen_summary.csv`, `joint_summary.csv`, `leg_summary.csv`

The raw evidence remains in its prior worktree and was not modified, renamed, or deleted.

## Interpretation

This is same-state instantaneous evidence only. A passing candidate is not a controller fix, does not establish closed-loop trajectory behavior, and does not authorize a live run. Body-x attribution comes only from exact MuJoCo qacc[0] replay; individual joint torque signs are not interpreted as propulsion or braking.

## Recommended next step (not executed)

对 BOUND_D4 申请一次单独批准的最小 live A/B，只改变 controller-stance dq_des 构造。
