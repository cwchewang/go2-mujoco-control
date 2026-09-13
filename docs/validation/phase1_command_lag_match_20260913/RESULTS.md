# Phase1 command-lag matching checkpoint

Overall result: INCONCLUSIVE for PD causal attribution. Stage 1 failed the predeclared command-reconstruction gate, so Stage 2 was not executed and no new MuJoCo simulation was run.

## 1. Did causal command-lag matching pass?

NOT SUPPORTED by the task's strong gate.

The active target was [31.90, 33.00). There were 110 target snapshots, all 110 had at least one candidate from the causal past-only 50 ms search window. The selected candidate lag was concentrated at 0, 2, or 4 ms, but no target snapshot met the required max_abs_ctrl_error <= 1e-5 Nm.

## 2. Measured controller-to-bridge lag distribution

The one-time nominal clock-offset estimate was the median of snapshot time minus the exact state-tick-selected closure row: 9.876544027e-10 ms; the p95 absolute offset was 1.585220843e-9 ms, so no nonzero clock correction was needed.

For the objective-selected candidates, raw double-precision command age was:

| statistic | age |
|---|---:|
| min | -6.536993e-13 ms |
| p05 | -5.407230e-13 ms |
| median | 4.867218e-13 ms |
| p95 | 4.000000000 ms |
| max | 4.000000001 ms |

The negative values are floating-point roundoff around zero. Interpreted at controller tick resolution, the histogram is: 0 ms: 62, 2 ms: 29, 4 ms: 19.

## 3. Can matched LowCmd reconstruct actual simulator ctrl?

NOT SUPPORTED.

For each snapshot, the objective minimized maximum motor residual first and L2 residual second. Across the 110 selected matches, the best maximum residual was:

- min: 1.547675012 Nm
- median: 5.511919060 Nm
- p95: 14.318433084 Nm
- max: 18.885437826 Nm
- strong-gate pass: 0/110 (0.0%; required >=95%)

Thus the concentrated lag is not an objectively strong explanation of the simulator snapshot ctrl. The matched tau_ff is not valid for causal counterfactual attribution under this gate.

## 4. Validated instantaneous PD contribution to base-x acceleration

INCONCLUSIVE and not executed. Because Stage 1 did not pass, there is no counterfactual_validated.csv, no mj_forward counterfactual result, and no pooled/contact-topology/phase delta_ax result in this checkpoint.

## 5. Does the evidence support or oppose PD as an instantaneous contributor to overspeed?

INCONCLUSIVE.

This checkpoint does not support PD, oppose PD, or establish a mixed phase/contact effect. It only shows that the currently logged controller rows cannot reconstruct the bridge-applied simulator ctrl tightly enough to make that causal claim. The result is not evidence that PD is the sole root cause.

## 6. One next step only

Not executed: perform one ordinary-PD baseline run with bridge-side atomic logging under the simulator mutex immediately before mj_step, recording the consumed LowCmd q/dq/kp/kd/tau, resulting mj_data->ctrl[12], the exact integration state, simulator time/sequence, and explicitly pre- or post-forward contact summary.

## Reproducible evidence

- branch: research/phase1-command-lag-match-20260913
- initial task branch HEAD: 14f1a52b92085f787281a98a9c96cb3b6deb9cfe
- prior source checkpoint: e6474211d4b60ffe9cb67786eafbc776f5c09935
- source run: varying_20260913_counterfactual
- controller data.csv rows used as candidates: 43,551; closure rows used for target-window state-tick selection: 120
- raw run metadata git_head: e30c18fd43566b840f50389a0eb5d7c77f0a0c63
- raw run metadata recorded git_dirty=true; inherited statuses: controller/safety/quality/analysis/ground-truth/dynamics/completion all 0
- scene: unitree_robots/go2/scene_leg_lift_demo.xml
- scene SHA256: 12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8
- profile: example/cpp/configs/phase1_velocity_varying.csv
- profile SHA256: 9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74
- controller binary SHA256: 0e91a0a06c41370654da0881cb2bc31f9baee8bbfd38c6ab191a49261449d759
- simulator binary SHA256: a2681153d3c777ee3e58eb3572c7f2b7825103548f30bb5a2390ea5f0bb2cec4
- snapshots.bin SHA256: 02019fb7c8e6657c4b057c69a4454661f45f584139d3c516ab9999e7913a0c4a
- data.csv SHA256: a003dc0203541ed9ce87c88ae6c8dc1d3d51d9dfc60a5b3ea45667b499bf4932
- data.csv.id_closure.csv SHA256: 626afc7854baf62e1a5811a6dbcbdb824e84abab1c038fd90dcc8230135edad4
- run_metadata.txt SHA256: fcace9b22dfeef68b6e999a10669333287849b4b52464e3f9f9f2fd590082115
- run_manifest.json SHA256: a5a12bda4414d6c8a51fad73ef1cb4707c52722ef72df1354fe372d3e0e7ed5e
- environment.txt SHA256: 6041c23c7e65e294b08f9b3b44b650bfdd98d4fe38acd8b178187c5ce4fc10df
- simulator.log SHA256: 3a970bb4e9611b0ec8c8cfe261a300fdc85a110bb9d474047200f0e0691429d0
- controller.log SHA256: 298d523788b214f443ef30b3c8fc8d033eb2557613f5e6928c1dc4030c54b896

The matching implementation is example/cpp/tools/analysis/match_command_lag.py, SHA256 5b5c47a5acb8105d9f720be88215becb1fb3f69ba1f8bdcf191bb68b6ce10170. It uses bridge semantics confirmed at simulate/src/unitree_sdk2_bridge.h:315-320, the Go2 sensor order at unitree_robots/go2/go2.xml:241-266, and the snapshot state serialization at simulate/src/main.cc:725-827.

Derived output:

- docs/validation/phase1_command_lag_match_20260913/lag_match.csv
- lag_match.csv SHA256: bebf474917be3c4fab17bed607eb7e1cffaf472715c176a22b8881fcc53c9ad0

Exact analysis command:

python3 example/cpp/tools/analysis/match_command_lag.py --snapshots /home/che/dev/go2-workspace/phase1-pd-counterfactual-replay-20260913/example/cpp/experiments/_runs/phase1_pd_counterfactual_replay_20260913/A/varying_20260913_counterfactual/snapshots.bin --closure /home/che/dev/go2-workspace/phase1-pd-counterfactual-replay-20260913/example/cpp/experiments/_runs/phase1_pd_counterfactual_replay_20260913/A/varying_20260913_counterfactual/data.csv.id_closure.csv --controller /home/che/dev/go2-workspace/phase1-pd-counterfactual-replay-20260913/example/cpp/experiments/_runs/phase1_pd_counterfactual_replay_20260913/A/varying_20260913_counterfactual/data.csv --output docs/validation/phase1_command_lag_match_20260913/lag_match.csv
