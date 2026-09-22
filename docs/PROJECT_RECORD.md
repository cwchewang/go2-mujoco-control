# Go2 — PROJECT_RECORD

> **最后更新：2026-09-22**
> **状态：ACTIVE / SUBSTRATE ENGINEERING FOUNDATION; GATE 0 CAPABILITY NOT_RUN**
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

## 1. [2026-09-22 | CURRENT | SNAPSHOT] 当前项目

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

## 1A. [2026-09-22 | CURRENT | ENGINEERING] 可执行的新阶段底座

当前准备分支为 `research/substrate-prelaunch-20260922`，任务见
`docs/research/TASK_SUBSTRATE_PRELAUNCH_20260922.md`，最新结果见
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
用户尚未授权开始。定义见 `docs/research/SUBSTRATE_FIRST_CAPTURE.md`。

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

GitHub main 最近已完成 Praxis dispatcher / runner / origin 基础设施修复，当前 main 最新可见提交为 `b1cec66f446c34e850c9caeeac82de52805a3889`（2026-09-22），这些不是新的科学 Gate 结果。

最后一份项目状态记录曾指出：Atlas 从 `e01a3730...` 建立本地 `research/substrate-gate0-20260921` 作为 clean Gate 0 起点，且当时未推送远端。

由于这是 host-local fact，**接手时必须重新用 Praxis / Git 核验，不得把它永久写成当前事实。**

截至本记录，repo 中没有正式 Substrate Gate 0 scientific closeout；不能从基础设施 commit 推断 MJPC/RL/DIAL capability 实验已完成。

## 8. [CURRENT | TOPIC STATUS] 选题状态

当前问题保持开放：

> 解除 fixed-gait / SRBD architectural bias 后，在强 whole-body predictive-control substrate 与强 learned capability baseline 下，复杂 terrain locomotion 仍有哪些稳定、可复现、可证伪的 bottleneck？

旧候选：
- L9 Preview：`HOLD / RE-AUDIT`
- L10 / TimedReach / SEFR / FSEF：`HOLD / RE-AUDIT`
- terrain-aware foothold+swing：legacy mechanism / possible benchmark intervention

Gate 0 前不得从历史候选直接继续造方法。

## 9. [CURRENT | NEXT]

1. 用 Praxis 重新核验 Atlas canonical Go2 workspace / local research branch；
2. 冻结 benchmark v0：terrain family、speed axis、success semantics、resource schema；
3. MJPC build + flat smoke + task/cost modification smoke；
4. RL checkpoint capability smoke；
5. 只在需要时做 DIAL throughput / failure diagnosis；
6. 形成 capability/failure map；
7. Gate 0 后重新做 novelty landscape，只从仍稳定存在的 bottleneck 分叉论文题。

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

普通 bug、编译、命令、参数流水不写。

更新顺序：
1. 核 repo/result 事实；
2. 先改 CURRENT snapshot / Gate / next；
3. 再补 traceability；
4. 被替代结论标 `SUPERSEDED`；
5. topic 变化同步 `docs/TOPIC_AUDIT.md`；
6. 顶层 frontier 变化才同步 Library `RESEARCH_INDEX.md`。