# Go2 — PROJECT_RECORD

> **最后更新：2026-09-24**
> **状态：RL CAPABILITY MAP CHARACTERIZED; BOUNDED 1M/S TERRAIN PASS; COMMAND-SPACE FAILURES OBSERVED; GATE 0 INCOMPLETE**
> **角色：repo 内项目 canonical 入口；回答“现在是什么、已证明什么、当前 Gate 与下一步是什么”。**
> **Source of truth：本 repo 同时承载研究认知、代码、配置、实验与结果；raw evidence 以 commit / result / Praxis evidence 为准。**
> **配对文档：`docs/TOPIC_AUDIT.md` 记录选题 landscape、候选攻击与路线演化。**

## 0. 接手顺序

任何新 agent / 新负责人：

1. 先读本文件；
2. 再读 `docs/TOPIC_AUDIT.md`；
3. 核 `CURRENT.md`、当前 branch / commit / result；
4. 若涉及 Atlas host state，用 Praxis diagnostics / workspace evidence 重新验证；
5. 不用聊天、Memory、截图覆盖 repo 事实。

状态词：`CURRENT / VERIFIED / LEGACY BASELINE / HOLD / RE-AUDIT / SUPERSEDED / HISTORICAL`。

## 1. [2026-09-23 | CURRENT | SNAPSHOT] 当前项目

公开 RL 策略的源条件、接口等价、完整 shared-transfer 组合与首轮 bounded capability map 均已形成正式证据。#189 在冻结九例协议下完成 9/9 单次执行并通过零物理独立验证：1 m/s flat reference、5 cm step、10 cm step、5/15/5 cm repeated steps 与 low-friction crossing PASS；0.5 m/s、reverse、lateral、yaw probes 为 PERFORMANCE_FAIL。当前下一步不是继续加 RL terrain case，而是让 MJPC 在对齐的 command/terrain benchmark 上形成可比较 failure map；只有跨强 baseline 或可明确归因的 failure 才进入 DIAL/选题诊断。任务和精确执行 frontier 跟随 CURRENT.md。

项目以**研究为主**，老师任务是同一路线上的硬约束与早期交付；作品集价值是副产品。短期工程与长期科研不能拆成两条互不相干的线。

现行 clean-slate 方向：

`Go2 + MuJoCo full-body model`
`→ unified task / cost API`
`→ whole-body predictive-control substrate`
`→ pluggable optimizer / contact prior / learned prior`

默认研究 backend：**MuJoCo MPC / iLQR WBMPC (MJPC)**。

Challengers / baselines：
- DIAL/MPPI：sampling challenger；
- contact-implicit MPC：只在 contact sequence / timing emergence 真正成为问题时启用；
- Go2 RL RobotLab/GYM：强 capability baseline、teacher/prior/proposal source；
- 旧 Raibert + fixed trot + SRBD MPC + ID-WBC：冻结为 legacy hierarchical baseline。

**当前没有锁定论文题。** L9 / L10 / SEFR / FSEF 等旧 hierarchy 候选全部 `HOLD / RE-AUDIT`；只有在新 substrate 上仍稳定存在的 bottleneck 才可重新晋级。

## 1D. [2026-09-24 | VERIFIED / BOUNDED] RL capability map 正式完成

Praxis v2 #189 在 capture HEAD `e40b0933572345f23b37e3bb06350518fde63e76` 上完成冻结 schema-2 `rl-capability-map-v1` campaign。九个 case 各执行一次，authoritative ledger 记录 9/9 scientific attempts，capture 为 `CAPTURE_COMPLETE / CHARACTERIZED`，未发生 retry、SAFETY_STOP 或 INTEGRITY_STOP。独立 offline verifier 最终返回 `VERIFIED`，核对 external ledger、逐 case raw replay 与 sealed flat-reference digest，且 verification `physics_steps=0`。正式 closeout 为 `docs/validation/rl_capability_map_successor_20260924/RESULTS.md`，result commit `de21d8c3267e1c985cb57ed2d02004c686d05bd1`，Praxis review publication commit `35e69f652e986af13c147a6fe4e8fc9eea70c5f1`。

冻结结果：
- `flat_reference`：PASS，mean vx 0.8858825097 m/s，sealed digest 与 #166 精确一致；
- `flat_half_speed`：PERFORMANCE_FAIL；纵向 tracking 本身通过，但 flat cross-axis gate 失败，lateral displacement 0.57465 m、yaw 0.24710 rad；
- `flat_reverse_probe`：PERFORMANCE_FAIL，目标 -0.5 m/s，mean vx -0.35590 m/s；
- `flat_lateral_probe`：PERFORMANCE_FAIL，目标 vy 0.25 m/s，mean vy 0.16589 m/s；
- `flat_yaw_probe`：PERFORMANCE_FAIL，目标 wz 0.5 rad/s，mean wz 0.10438 rad/s；
- `step_5cm_cross`、`step_10cm_cross`、`repeated_steps_cross`、`low_friction_cross`：均 PASS，其中 repeated steps 为冻结 5/15/5 cm profile。

该结果只说明此 checkpoint / adapter / reset / scene / command set 下，**1 m/s 前向 terrain crossing 在这些 bounded cases 中不是最先暴露的弱点；速度与方向 command-space probe 更早出现性能边界。** 不能由此推出“terrain 已解决”“方向控制是论文 gap”或“MJPC 一定更好”。下一步必须在同一 benchmark 语义上跑 MJPC，对比 failure map；若 MJPC 在同一处也失败，再判断是否值得用 DIAL/MPPI 区分 local-gradient、contact-mode 或 multimodality 机制。

标准 verifier 首次因 detached-worktree branch identity 比较限制在 raw replay 前失败；最终只用 documented in-memory identity adapter 纠正 detached actual branch 与逻辑 Praxis branch 的比较，未修改 source、protocol、prepared/capture evidence 或任何 raw trace。该事件属于 verification plumbing，不是科学失败。

## 1C. [2026-09-24 | VERIFIED / BOUNDED] shared-transfer 正式组合确认

Praxis v2 #166 在精确起始 HEAD `9e82e56ac2a5db63d7834e86ce402d542bf10ae8` 上完成冻结 `rl-shared-transfer-combination-v1` campaign。两例 `combined_1` / `combined_2` 均 PASS，各 6000 steps，mean vx = 0.8858825097 m/s；两例 trace SHA-256 完全一致。authoritative ledger 与 offline verifier 都确认恰好消耗 2 次 scientific attempts，且无 retry。正式 closeout 为 `docs/validation/shared_transfer_combination_formal_v2_20260923/RESULTS.md`，result commit `6f67769851aaffed1c1826d138293e52265dbba7`，Praxis review publication commit `076f72dfcbab32dbed0c364b5f88f753f500123e`。

该结果只证明：**完整 pinned shared deployment combination 在冻结 1 m/s 平地协议下保持已封存源策略能力，并具有精确重复性。** 它不证明低速、terrain、hardware 或 general robustness。原先“单因素通过不等于组合通过”的未决点至此关闭。

执行侧发生过两个非科学故障：原始 offline verifier 对 detached HEAD 的 branch identity 比较不兼容；Praxis 旧 closeout 一度拒绝目录型 evidence bundle。前者通过不修改 capture/raw evidence 的窄 identity adapter 完成零物理 offline verification；后者由 Praxis publication-only salvage 修复，未重新运行 capture、未增加 scientific attempt。不得把这些 closeout/verification 基础设施问题写成科学失败。

## 1B. [2026-09-23 | VERIFIED / BOUNDED] 公开RL源条件基线

十例固定协议已封存，见[完整结果](validation/rl_baseline_20260923/RESULTS.md)。
源模型1 m/s指令平均速度0.938050 m/s；源重复与共享策略接口三条轨迹完全一致。
原条件0.15 m/s仍仅0.021824 m/s，低速不足不能全归模型或接口移植；奖励机制
尚未证实。变速纵向跟踪好但横漂超限；默认23 cm楼梯在2.5 s因机身前部接触
第二级立面停止，不能称摔倒或证明永远无法跨越。共享模型单因素1 m/s通过，
不等于模型/home/接口组合已确认。这是有限平地参考，不是强地形能力天花板。

## 1A. [2026-09-22 | CURRENT | ENGINEERING] 可执行的新阶段底座

治理与首次失败的离线诊断见
`docs/validation/governance_diagnosis_20260922/RESULTS.md`。资格缓存按真实源码、
环境、构建及依赖内容复用，执行仍绑定当前 HEAD、任务、独立审查与授权；
原实验预算和 FAIL 均未改变。500 次策略输入及 5000 次 PD 控制与上游独立
实现逐点一致，5001 帧接触重建一致。0.15 m/s 指令确有策略响应；低速奖励
区分度、模型及启动条件差异仍是候选解释，不能从单条轨迹宣布单一根因。
该轮没有新物理步进，也没有新增能力通过结论。其提出的上游复现与受控移植
方案现按新任务推进；不继续已封存的 v1。

工程准备分支 `research/substrate-prelaunch-20260922` 已通过 PR #139 合入主线
`c5582af60b802b688e4e526845402deb33cf29cd`。其任务见
`docs/research/TASK_REPOSITORY_CEE_20260922.md`，最新结果见
`docs/validation/repository_cee_20260922/RESULTS.md`。首轮准备验收保留于
`docs/validation/substrate_prelaunch_20260922/RESULTS.md`。可靠性验收保留于
`docs/validation/substrate_reliability_20260922/RESULTS.md`。首轮工程记录保留于
`docs/validation/substrate_foundation_20260922/RESULTS.md`。

现有 clean 控制出口改为根据当前周期求解/映射结果决策；增加失败、恢复、
非有限/越界候选测试。DDS 清理测试采用隔离 proc fixture，生产 fail-closed
检查不变。旧 sealed evidence 不变；新二进制尚无行走验收。

`tools/substrate/` 新增命名关节/观测/动作边界、源锁定、模型资产闭包与物理
指纹、真实 public RL 推理、原生 MJPC iLQG 静态求解准入，以及原始证据输出。
两者共同使用现有 MuJoCo 3.3.6 模型与力矩出口，但信息条件不同，不能据此做
公平能力对比。工程准入不是 Gate 0。首轮平地 RL 移植验收已有前瞻协议、
闭环 runner、分析器及三次失败即停预算；其准备流程禁止真实物理步进，
准备阶段没有启动授权。用户现已明确要求“合入主线，然后开正式实验”；
正式采集在 `research/substrate-first-capture-20260922` 的准确 HEAD
`09a9a31e2ab6eefcd4d3193107e8e17dad642129` 完成。执行任务见
`docs/research/TASK_SUBSTRATE_FIRST_CAPTURE_20260922.md`，协议定义见
`docs/research/SUBSTRATE_FIRST_CAPTURE.md`。

首轮完整运行 5000 个物理步 / 10 秒，5001 帧证据通过独立复算及外部次数
账本核验。冻结终点位移 0.364124 米（要求 >=1 米），末 5 秒速度 MAE
0.107403 m/s（要求 <=0.1 m/s）；两项均失败，科学结果 FAIL。未触发安全
条件，未发生力矩饱和。按原协议停止，第 2、3 次 NOT_RUN；重复性未检验。
最早失败边界为 scientific / metric_failure，具体机制尚未归因。该结果
不能外推为策略整体能力失败或完整 Gate 0 结论。原始证据与授权、账本已
归档；见 `docs/validation/substrate_first_capture_20260922/RESULTS.md`。

后续可靠性加固补齐独立依赖环境、源码/二进制构建绑定、模型输入快照、策略
状态隔离和重放、严格类型/时钟契约、超时子进程清理、失败证据封存及独立
校验，并恢复 SOP 预检入口。统一 `tools.substrate.qualify` 命令在干净提交上
完成工程验收；其通过仍不是正式实验的科学授权或能力结论。

## 2. [2026-09-17 | VERIFIED / LEGACY] Sealed flat baseline

已验证 legacy chain：

`speed target → fixed low-speed trot → Raibert nominal foothold → prebuilt swing → exact/direct IK → SRBD MPC → strict ID-WBC → torque envelope → MuJoCo`

冻结配置：
- period 0.60 s；
- duty 0.75；
- step length 0.091 m；
- nominal speed ≈0.15167 m/s；
- nominal foot lift 0.020 m；
- torque envelope 35 N·m。

2026-09-17 三次 fresh-worktree / fresh-build / 零调参平地重复均通过：64/64 cycles，clean target reject=0，strict WBC/QP reject=0，hard/emergency stop=0。

这只证明**低速平地 low-level stack 可重复、可审计**。

没有证明：
- clean baseline 已完成 5 cm terrain crossing；
- terrain planner 有效；
- fixed trot / Raibert 是最佳长期路线；
- 高速、变速、多地形能力成立。

关键纠正：sealed clean baseline **从未正式做过 5 cm terrain crossing**。

## 3. [HISTORICAL] 旧 terrain 线留下的 failure clues

旧路线曾经历：
`normal swing → known-step adapter → V2 corridor → workspace clamp → direct IK guard`

可保留线索：
- world-frame 足端轨迹合理，不代表 body/hip motion 后中间腿姿态可行；
- min-clearance / V2 target 曾遇到 calf joint-limit infeasibility；
- 不断加 workspace clamp 可能掩盖真正 feasibility boundary。

这些只属于旧架构 failure clues，不是当前 whole-body substrate 的已知 failure，也不是论文题。

## 4. [2026-09-18→19 | TRACEABILITY] 为什么推倒旧底座

关键触发：

| 质疑 | 结论 |
|---|---|
| “baseline 干净了，但路线本身会不会不好？” | 不再把 Raibert/fixed trot/SRBD 当长期架构 |
| “baseline 不是没做越障吗？” | 纠正叙事：clean baseline 未正式做 5 cm terrain |
| “terrain-aware 不应该在 swing 上层开始吗？” | foothold/swing/body/timing 作为独立 planning freedoms 审计 |
| “老师任务和论文题不能拆两条” | 形成同一路线 dual-goal 硬约束 |
| “为什么不能推倒重来，换最佳研究底座？” | 转向 whole-body substrate audit |
| “DIAL 算力太重、仓库也不活跃” | DIAL 从 default 降为 challenger |

重要原则：clean baseline 的价值是**可信对照组**，不是最终系统的架构前提。

## 5. [CURRENT | SUBSTRATE] 现行研究底座

### Physics / embodiment
- Go2：第一主 embodiment，因为已有资产、模型、生态与未来实机可能性；不是 contribution。
- MuJoCo：shared physics / evaluation substrate。

### Default backend：MJPC / iLQR
选择理由：training-free、full-body dynamics、task/cost 易修改、归因干净。

边界：nominal gait/contact reference 主要通过 soft residual/cost 进入，不是硬 contact constraint；但 iLQR 对 contact-mode exploration 本身不强，不能把 MJPC 写成 contact-implicit solver。

### RL baseline
优先直接用公开 checkpoint，不从头训练。目标是建立 terrain capability ceiling / failure map，并防止把 learning policy 已轻松解决的问题当科研 gap。

现已接入的 Gym checkpoint 已通过冻结 1 m/s 平地源条件复现、接口等价核验、完整 shared model/home/ten-step-start/adapter 组合的两次正式 PASS，以及 #189 九例 capability map。#189 中 5 cm、10 cm、5/15/5 cm repeated steps 与 low-friction 1 m/s crossing 均 PASS，而 half-speed、reverse、lateral、yaw probes 为 PERFORMANCE_FAIL。因此该 shared deployment 已可作为 bounded terrain 与 command-space 对照，但仍不能外推到更高台阶、障碍、hardware 或 general robustness，也不能把这些 RL-only failure 直接升格为跨控制器 bottleneck。默认后端和已投入的工程成本不能替代科学
选型依据。0.15 m/s 是历史局部兼容性协议的工程设定，没有被论证为全项目目标；
今后参数先说明需求/来源/假设和对决策的作用，再定义验收。原 FAIL 不追溯改写。

### DIAL / MPPI
只作为 challenger：判断 iLQR failure 是否来自 local gradient、nonsmooth contact 或 multimodality。先做小规模 throughput smoke，不承担默认 backend。

## 6. [CURRENT | SUBSTRATE GATE 0] 当前 Gate

依赖关系：

`benchmark v0 → (MJPC smoke ∥ RL checkpoint smoke) → capability/failure map → targeted DIAL diagnosis → benchmark v1 / Gate verdict`

Gate 内容：
1. MJPC Go2 build/flat/terrain task-cost modification；记录 Atlas 9700X policy update frequency、CPU/RAM。
2. Go2 RL checkpoint 在 MuJoCo flat / step / stairs / obstacle 的 strong capability baseline。
3. DIAL RTX 5080 小规模 seq-jump/crate throughput smoke。
4. 统一 terrain family、任务目标、成功语义、资源记录，形成 shared benchmark。

Gate 目的不是选“永远唯一 controller”，而是建立高天花板、可插拔、可比较 substrate。

## 7. [CURRENT | EXECUTION] Repo / host 状态边界

实际工作区、branch/HEAD、dirty 状态和远端关系每次接手重新核验，命令见
[项目推进指南](OPERATING_GUIDE.md)。本文件不维护会过期的“最新 main SHA”或
机器工作分支快照；具体运行的历史 SHA 保留在对应结果中。

首轮 0.15 m/s 平地 RL 移植验收的 FAIL closeout 仍保留；随后 1 m/s shared-transfer 正式组合已两次 PASS。两者回答的是不同冻结条件，不能互相改写。完整 Substrate Gate 0 仍未完成；当前尚不能代表 MJPC/RL/DIAL 地形能力已完成验证.

## 8. [CURRENT | TOPIC STATUS] 选题状态

当前问题保持开放：

> 解除 fixed-gait / SRBD architectural bias 后，在强 whole-body predictive-control substrate 与强 learned capability baseline 下，复杂 terrain locomotion 仍有哪些稳定、可复现、可证伪的 bottleneck？

旧候选：
- L9 Preview：`HOLD / RE-AUDIT`
- L10 / TimedReach / SEFR / FSEF：`HOLD / RE-AUDIT`
- terrain-aware foothold+swing：legacy mechanism / possible benchmark intervention

Gate 0 前不得从历史候选直接继续造方法。

## 9. [CURRENT | NEXT]

RL shared-transfer 与首轮九例 capability map 均已完成并封存，不再重复这些 campaign。下一阶段直接把 MJPC 放到与 #189 对齐的 command/terrain benchmark：至少覆盖 1 m/s reference、0.5 m/s、reverse、lateral、yaw，以及已通过的 step/repeated-step/low-friction anchor。先问 MJPC 是否复现 RL 的 command-space failure、是否在 terrain 上出现不同 failure；只有出现稳定且机制上可分解的差异后，才启用 DIAL challenger 诊断 local-gradient / nonsmooth-contact / multimodality。

低速 0.15 m/s 不足、横漂与 23 cm 楼梯 base-contact stop 仍是已观察边界，但未形成论文问题；必须先在统一 benchmark 与强 baseline 下复现、分离 deployment artifact 与真实 capability bottleneck。Gate 0 前仍不从历史 L9/L10/FSEF 等候选直接造方法。

## 10. [2026-09-22 | GOVERNANCE] Repo-native 项目记录

从 2026-09-22 起，本文件与 `docs/TOPIC_AUDIT.md` 是项目级研究认知 source of truth。Library 不再维护正文副本，只保留跨项目 `RESEARCH_INDEX` 与不可恢复历史材料。

## 11. 维护协议

重大变化必须更新：
- research question；
- substrate / benchmark；
- 正式 Gate verdict；
- 重要正/负结果；
- 会改变判断的失败根因；
- 用户质疑触发的路线修正。

2026-09-24 review 流程事件形成一条长期执行规则：在创建昂贵 science /
execution / evidence reviewer 前，项目负责人必须先做 task-specific deterministic
precheck。strict loader、五字段 Praxis identity、path/ref/hash、targeted tests、
zero-step/readiness 等机器可判定问题应由负责人先发现、修复并重跑，不能交给
reviewer 首次发现。此前 contract-hash / approval-inheritance prototype PR #183
已明确不合入 main；当前选择“ChatGPT 负责人现场 precheck + 现有项目检查”的
轻量方案，只有未来真实反复漏检时才考虑增加极薄 runtime gate。

普通 bug、编译、命令、参数流水不写。

更新顺序：
1. 核 repo/result 事实；
2. 先改 CURRENT snapshot / Gate / next；
3. 再补 traceability；
4. 被替代结论标 `SUPERSEDED`；
5. topic 变化同步 `docs/TOPIC_AUDIT.md`；
6. 顶层 frontier 变化才同步 Library `RESEARCH_INDEX.md`。
