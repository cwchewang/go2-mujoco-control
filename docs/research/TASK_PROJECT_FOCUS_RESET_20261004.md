# Go2：主底座已选，先复现作者原生能力

## 目标与本轮范围

2026-10-04 用户明确优先自己的学习、研究与高含金量成果，服务科研实习进组与学校申请。
长期目标是可发表且有实证的新方法；教师的历史仿真跨障碍作业不再决定题目。
现有代码与实验记录保留，目前尚无成型新方法成果。仿真演示可作为研究展示材料。

用户进一步要求先比较强控制底座，再发现具体缺陷；“低速、方向控制问题”撤回为默认主线。
本轮完成来源与本地资源比较、选型和入口更新；没有安装、权重下载、推理、仿真、
optimizer 或训练。父提交 `20bd1cb9b9a4ad4daa637b0cc141ea5e493941c8` 不变。
原封账预算、PASS/FAIL/NOT_RUN 与独立分支身份保持；本轮新增运行预算为 0。

## 选型结论：MoE-CTS，作者认可的 Go2 RL RobotLab 实现

**主底座选择已完成：MoE-CTS 方法，以作者认可的 go2_rl_robotlab 为研究源码起点，
先用其 Lab v4.2/176k 发布策略走同仓原生 MuJoCo 部署。**
这是一项来源支持的技术选择；本机原生执行和性能尚未验证，具体科研问题也尚未成立。

依据：RSS 2026 的 RoboGauge/MoE-CTS 在 Go2 上对 CTS、HIM、DreamWaQ 有直接比较，
覆盖多地形与扰动；公开训练源码、发布 actor 与 full checkpoint，提供 expert encoder、
history/latent、CTS supervision 与任务修改接口。[RSS 最终论文](https://www.roboticsproceedings.org/rss22/p156.pdf)

该选择可能仍落在原策略的方法家族，但依据是新增比较证据，不是既有投入。
现用 Gym/164k 权重、RSS Gym/137k 论文策略、新 Lab/176k 策略以及旧共享 adapter
是不同身份；不要求继续修现用权重和 adapter。原作者 Gym README 直接链接 Lab 实现，
HF 同时发布两套资源。[原作者仓库](https://github.com/wty-yy/go2_rl_gym)、
[作者认可 Lab 实现](https://github.com/wertyuilife2/go2_rl_robotlab)、
[发布权重](https://huggingface.co/wty-yy/go2_rl_gym_data)

## 比较实际支持什么

本次覆盖 9 种学习方法、4 种优化方法；框架另列，不能当作已经验证的控制策略。

| 方法 | 本轮选择与原因 |
|---|---|
| MoE-CTS | 默认主方法：Go2 多地形直接对照、训练/部署源码、actor/full checkpoint 与研究接口 |
| CTS、HIM、DreamWaQ | 重要 parent/representation 对照；MoE 作者发布其 Go2 复现策略，不冒称原作者 Go2 权重 |
| PGTT | heightmap/phase 任务备选：有发布策略与受控 reward 比较，但未与 MoE/HIM/REAL 同场，不能因易部署称最强 |
| REAL | 若选 depth-vision parkour，更契合其问题；two-stage/estimator/depth 管线较重，公开权重本轮未核 |
| SoloParkour、Extreme Parkour | 成熟视觉机制前作；原生机器人分别 Solo-12、A1，Go2 移植和训练成本不应隐去 |
| LoComposition | constraints/energy/perception 分解的重要前作；官方公开代码/权重尚未核，不优先重建 |
| DIAL-MPC | 需要优化机制对照时优先：原生 Go2，sampling/contact-search；实时走跳与离线 all-contact crate 必须分开，版本/action/compute 条件需锁 |
| 作者 native WBMPC/iLQR | 连续跟踪、不稳定姿态、低延迟 CPU 反馈的更合适路线；当前 adapter 失败不代表方法失败，native actuator 模型也要核 |
| RTWholeBodyMPPI | CPU/contact-rich 优化参考；论文与主要 release 是 Go1，不能假装即用 Go2 |
| OCS2 perceptive ANYmal | foothold/SDF 约束与多重射击强参考；ROS/ANYmal 栈重建成本高，不是现成 Go2 替换 |

真实同文比较分三组：RoboGauge 四法、PGTT 对 MassLoco/Wild、REAL 对视觉 parkour 方法。
不同组的 success、score、地形、信息条件与训练预算不同，不能串成全球数值榜。
RoboGauge 各法 3 training seeds 中选最佳；MoE/CTS command limit 2m/s，HIM/DreamWaQ 1m/s。
因此它是有边界的选型证据，不是完全等条件的跨 seed 均值结论。
Lab README .6984、HF 卡 Lab185k .6828、RSS Gym .6713 也不是同一发布身份。
[PGTT 原论文](https://arxiv.org/html/2510.18348v2)、[REAL 原论文](https://arxiv.org/html/2603.17653v1)、
[DIAL 原论文](https://arxiv.org/html/2409.15610)、[WBMPC 原论文](https://arxiv.org/html/2503.04613v3)

## 固定的起点与资源边界

- 源码：`28b4516d22617b11aeaf8ead63cc00b0c0bcd1bd`，任务 `RobotLab-Go2-v0`。
- HF revision：`b9cd72d5046358b4ca6840a3d795d001402e6bfc`。
- Actor：`go2_rl_robotlab/go2_moe_cts_v4.2_176k_0.6984_20260626/exported/policy.pt`。
  发布元数据 LFS SHA256：`c602e749ac292921e3d6f5b2ab1749c4e4eaa6dbe51f751cce5b669b102d10a2`；本轮未下载字节验证。
- Full checkpoint 同目录 `model_176000.pt`；历史源码/config/seed、export 参数对应和模型身份仍需核，
  不能拿当前源码反推当时训练的全部条件。
- 本机 RTX5080 16GiB、WSL 8 CPU/约15GiB RAM；Windows 实装32GiB，`.wslconfig` 限16GB、swap0。
  IsaacLab v2.3.2 官方需32GB RAM/16GB VRAM，当前 WSL 不满足 RAM 条件；不改配置、不重启。
  已有 Isaac 环境版本不同且源码 dirty，保留原样。[官方要求](https://isaac-sim.github.io/IsaacLab/v2.3.2/source/setup/installation/index.html)

先验证发布策略的同仓 MuJoCo 部署，不以自训为前置。训练需要单独解决资源和版本，
GPU 型号不证明训练可用或 DIAL 达到作者实时成绩。DIAL 此刻不要求同步搭起第二套栈。

## 从现在到新方法的路线

1. **原生能力复现**：锁 release，核 loader/history/观测动作/PD/model/self-collision，
   再复现作者多地形与扰动的代表能力；留下源身份、配置、原始轨迹与正确指标。
   建议准备2个工作日、资格验证1周，是投入时间盒而非复现工时保证，不能无限修安装。
2. **在已成立能力域里定义问题**：以连续多地形通行及扰动恢复为起点，选一族有意义任务。
   明确机器人知道什么、可用计算、成功标准；验证稳定残余限制。成熟方法、常规配置、
   信息增加或参数调整能解决时，不把它称为新算法 gap。DIAL/PGTT/REAL 按这一步的机制需要进入。
3. **机制验证和新方法**：提出可证伪解释，实施必要机制，用匹配任务/信息/预算的强基线、
   多种子、独立 holdout、消融和跨条件测试检验；再形成论文主张、代码和研究展示。
   MoE、history、terrain switching、perception、constraint/energy 的一般组合已有前作，不能当作创新。

不把“找到任意崩溃”当研究目标；没有稳定且成熟解法不能解释的剩余问题时，换任务或研究点，
而不是继续围绕弱权重造问题。当前题目仍开放，但主实现不再开放筛查。

## 既有结果与执行收束

旧 RL 平地、冻结台阶与命令能力证据按原勘误保留。当前 MJPC adapter 默认扩展
仍为 PARKED/CONDITIONAL；不自动追加 warmstart/horizon，不取消独立已授权任务。
新主栈允许换 physics，不将跨环境数字直接视为公平排名。原始数据、归档清单和
用户未提交结果未修改。本轮无 commit/push/合并，选型完成与运行资格必须分别记账。

## 已有 PGTT 来源审计（保留，非强制下一步）

已有一个公开方法的有界来源审计：**PGTT → CONDITIONAL**，值得最小准备，
尚未资格化，也未证明能解决 CTS 的命令失败。官方来源锁为
`9bd133884bbf2eeaa40c82aee534246ccaaf02f8`；发布 tree 中有
`policies/policy_go2_pgtt_level03_run0`，Git blob `9019953d719ac6df712054ec190567a2d0717182`。

- [论文](https://arxiv.org/html/2510.18348v2) 与
  [训练入口](https://github.com/NtagkasAlex/phase_guided_terrain_traversal/blob/9bd133884bbf2eeaa40c82aee534246ccaaf02f8/training/train.py)
  包含正负 vx/vy/yaw；训练入口最终覆盖为三轴 ±1，不能用配置默认范围代替。
- 发布权重与实际训练配置/种子的强绑定尚缺；run0/run1 不证明独立随机种子。
- [配置](https://github.com/NtagkasAlex/phase_guided_terrain_traversal/blob/9bd133884bbf2eeaa40c82aee534246ccaaf02f8/go2/robot_config.py) 与
  [部署入口](https://github.com/NtagkasAlex/phase_guided_terrain_traversal/blob/9bd133884bbf2eeaa40c82aee534246ccaaf02f8/deploy/deploy_heightmap.py)
  显示需要 phase/frequency 与 11×9 heightmap；position residual scale 0.5、Kp40/Kd0.5、50 Hz。
  平地可先核正确常零相对 heightmap，不必先搭 LiDAR/ROS 或重训；不得直接删除观测维度。

若选定 PGTT，最小准备仍是锁定 checkpoint，核 loader/normalizer、观测顺序和
joint/action/model；它不必围绕 CTS 低速失败开展，来源支持亦不等于性能通过。


## 交接状态

来源比较与主底座选型完成；下一步是选定发布策略的有界原生复现。
本机能力尚未实测，论文问题尚未锁定，原训练与 capture 预算仍关闭。
