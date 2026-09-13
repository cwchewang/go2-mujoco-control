# Phase1 same-state PD counterfactual replay

## 结论

Hypothesis result: INCONCLUSIVE.

本 checkpoint 完成了 1 次普通 PD、无脉冲的 A 诊断运行，并完成离线两分支 forward replay。状态恢复后的 ACTUAL qacc[0] 数值残差为 0，但 ACTUAL replay 未通过完整 replay validation gate：live 与 replay 的接触/约束摘要仅 91/110 条一致；按同一 state tick 从 controller closure 重构的 ctrl 与快照内实际 ctrl 的最大误差为 45.9743964421 Nm，p95 为 31.0995407796 Nm。因此不解释 tau_ff-only 分支的 delta_ax，不对 PD 因果方向作结论。

## 范围与运行

- branch: research/phase1-pd-counterfactual-replay-20260913
- source HEAD: e30c18fd43566b840f50389a0eb5d7c77f0a0c63
- source contract base: 1fc68a34233551ac9ed1e57f68cc86357fd560ad
- source run: varying_20260913_counterfactual
- source A run: 1 次；TROT_PD_PULSE_AB 未设置；未运行 live tau_ff-only 或 PD-off pulse
- controller_status=0, safety_status=0, quality_status=0, analysis_status=0, completion_status=0
- normal A 在 [32,33) 的 measured-minus-applied velocity median 为 +0.239526966 m/s；measured median 2.519763483 m/s，applied median 2.280236517 m/s
- scene: unitree_robots/go2/scene_leg_lift_demo.xml
- scene SHA256: 12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8
- profile SHA256: 9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74
- controller binary SHA256: 0e91a0a06c41370654da0881cb2bc31f9baee8bbfd38c6ab191a49261449d759
- simulator binary SHA256: a2681153d3c777ee3e58eb3572c7f2b7825103548f30bb5a2390ea5f0bb2cec4
- domain: 232; headless; controller duration 86 s; period 0.14; duty 0.44; step length 0.50; WBC full; running-trot; no seed

原有 varying_20260913_204709 raw 只有 CSV/log/manifest，没有可由 mj_setState 精确恢复的 MuJoCo integration state；因此按任务授权执行了唯一 1 次新 A 诊断运行。新运行只增加默认关闭的快照序列化和 closure 诊断，未改变控制器数学、gait、模型、scene、阈值或实时 shadow dynamics。

## 快照表示与连接

快照文件为本地 raw binary，magic=GO2PDSNP，format version=1，native little-endian x86_64，MuJoCo 3.3.6，mjtNum=8 bytes，state_sig=mjSTATE_INTEGRATION=8191，state_size=194，nq=19，nv=18，na=0，nu=12，timestep=0.002 s。每条记录包含 record index、step前的 state_tick_ms/time/qvel[0]、step后 live qacc[0]、step前 ncon/nefc/foot contact mask，以及 mj_getState 返回的完整 state；该 state 包含 time、qpos、qvel、act、plugin、ctrl、qfrc_applied、xfrc_applied、warmstart 等 integration/user state。

模拟器在每个真实 mj_step 前调用 mj_getState；不在实时环路执行 shadow mj_forward/mj_step。新 raw 共 2,499 条，过滤模拟时间 [36,41)。controller closure 的 state_tick_s 乘 1000 后四舍五入为整数，与快照 llround(d->time*1000) 做唯一 exact join；目标 [31.90,33.00) 得到 110 条，重复 snapshot tick=0、重复 closure tick=0，join key 时间错配=0 ms。目标行的 sim time 覆盖 37.872 至 38.964 s，active time 覆盖 31.900001276 至 32.990005483 s。

ctrl 重构严格使用 bridge 源码语义：
pd_i = kp_i*(q_des_i-q_i) + kd_i*(dq_des_i-dq_i)
ctrl_actual_i = tau_ff_i + pd_i
ctrl_cf_i = tau_ff_i
ACTUAL 使用快照 state 内的 ctrl；CF 只改 ctrl 为 closure 的 tau_ff，其他 state 完全相同。bridge 源码确认 data->ctrl[i] 使用 tau、kp、q、kd、dq，并沿相同 MuJoCo actuator path 进入 mj_forward；模型 motor ctrlrange 保持不变。

## Replay validation gate

预先固定的 double-precision gate：每条 ACTUAL 的 |qacc_replay[0]-qacc_live[0]| <= 1e-5 m/s2；ctrl 重构误差 <= 1e-5 Nm；ncon、nefc、physical foot contact mask 逐条一致。实际结果：

- qacc[0] residual max: 0 m/s2，110/110 条满足
- ctrl reconstruction residual p95: 31.0995407796 Nm；max: 45.9743964421 Nm；0/110 条达到 1e-5 Nm 的全局 max gate
- live/replay ncon 一致: 91/110
- live/replay nefc 一致: 91/110
- live/replay physical foot mask 一致: 91/110
- ACTUAL/CF 的 replay contact summary 相同: ncon 110/110、nefc 110/110、foot mask 110/110

这个失败证据足以停止解释 CF delta_ax。它表明当前快照时点的 bridge-applied command components 与 closure 行不能被证明为同一 actuator command，且 live 接触摘要与从快照重新 forward 的摘要也不是逐条一致；不把它归因于 PD 或某个单一根因。

## 未通过 gate 前的描述性 delta_ax

下表来自 counterfactual.csv，仅作未验证的描述性记录，不作为因果证据。delta_ax = ax_cf - ax_actual；因 replay validation 未通过，W0-W3 的方向、幅值和比例均不用于 hypothesis 判定。contact 列是 live snapshot foot mask 的十进制 mask:count；phase 使用 active_time/0.14 的周期相位。

| window | n | median delta_ax | p05 | p95 | frac <0 | frac >0 | median abs | median vel error | contact mask:count | phase coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| W0 [31.90,32.10) | 21 | -1.440778 | -9.134266 | 5.000690 | 71.43% | 28.57% | 3.787348 | +0.211563 | 0:4,1:1,6:8,8:2,9:6 | 0.071408..0.999977 |
| W1 [32.10,32.20) | 9 | -1.598730 | -8.008834 | 3.224571 | 77.78% | 22.22% | 1.772203 | +0.241114 | 0:2,4:2,6:2,9:3 | 0.357170..0.928592 |
| W2 [32.20,32.40) | 21 | -1.271883 | -9.175294 | 4.161836 | 71.43% | 28.57% | 4.161836 | +0.213416 | 0:4,1:1,6:6,8:2,9:8 | 0.000023..0.999985 |
| W3 [32.40,32.60) | 20 | -1.791961 | -8.172556 | 5.528749 | 75.00% | 25.00% | 2.914839 | +0.256312 | 0:6,1:1,4:3,6:5,9:5 | 0.000023..0.928857 |
| full [31.90,32.60) | 71 | -1.592553 | -9.565708 | 5.070961 | 73.24% | 26.76% | 3.111900 | +0.240068 | 0:16,1:3,4:5,6:21,8:4,9:22 | 0.000023..0.999985 |
| tail [32.60,33.00) | 39 | -1.634984 | -9.515741 | 4.272093 | 71.79% | 28.21% | 3.285064 | +0.247184 | 0:11,4:2,6:10,8:2,9:14 | 0.071326..0.999986 |

Dominant physical-mask stratification in the full target interval, still descriptive only: mask 6 n=21, median -1.592553, frac<0=90.48%; mask 9 n=22, median +0.998322, frac<0=45.45%; mask 0 n=16, median -7.928311, frac<0=100%; mask 4 n=5, median +2.131943, frac<0=40%; mask 8 n=4, median -1.656916, frac<0=50%; mask 1 n=3, median -7.667285, frac<0=100%. The sign change across masks is one reason not to average these unvalidated branches into a causal claim.

## 产物与 hashes

Committed outputs:
- docs/validation/phase1_pd_counterfactual_replay_20260913/RESULTS.md
- docs/validation/phase1_pd_counterfactual_replay_20260913/counterfactual.csv
- minimal source/tool plumbing: simulate/src/main.cc, example/cpp/CMakeLists.txt, example/cpp/tools/analysis/replay_pd_counterfactual.cpp

Raw exact-state snapshot remains local and is not committed:
- source run: varying_20260913_counterfactual
- snapshots.bin SHA256: 02019fb7c8e6657c4b057c69a4454661f45f584139d3c516ab9999e7913a0c4a
- data.csv SHA256: a003dc0203541ed9ce87c88ae6c8dc1d3d51d9dfc60a5b3ea45667b499bf4932
- data.csv.id_closure.csv SHA256: 626afc7854baf62e1a5811a6dbcbdb824e84abab1c038fd90dcc8230135edad4
- run_metadata.txt SHA256: fcace9b22dfeef68b6e999a10669333287849b4b52464e3f9f9f2fd590082115
- run_manifest.json SHA256: a5a12bda4414d6c8a51fad73ef1cb4707c52722ef72df1354fe372d3e0e7ed5e
- environment.txt SHA256: 6041c23c7e65e294b08f9b3b44b650bfdd98d4fe38acd8b178187c5ce4fc10df
- simulator.log SHA256: 3a970bb4e9611b0ec8c8cfe261a300fdc85a110bb9d474047200f0e0691429d0
- controller.log SHA256: 298d523788b214f443ef30b3c8fc8d033eb2557613f5e6928c1dc4030c54b896

Source/tool file SHA256:
- simulate/src/main.cc: 1a7dc42893590270f56ba6a7ecf5df12f31c8307faf360e32ef5688891b99536
- example/cpp/CMakeLists.txt: c43b9587a4d82a69e96db7f194a2a241c6e34b708fb095ee29f5904e564e9adf
- example/cpp/tools/analysis/replay_pd_counterfactual.cpp: 62d37940e49f5b339f5365d89d7d62d99f53820d5396fd09b9ca3549326249de
- replay tool binary: 0f4df513518c0b5a3b71a73dbcde45beefb1fb86bba54a7cd0154f0b5dee4081

## 下一步

仅建议、不执行：在同一 simulator mutex 和同一 state tick 下，由 bridge 原子记录实际应用的 q、dq、kp、kd、tau 与快照 state，并使 live contact/constraint 摘要对应同一 state；随后只做一次新的同状态 replay validation。未进行任何下一步运行、调参、gait/WBC/SRBD/contact/model/threshold 修改或自动 follow-up。
