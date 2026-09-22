# Go2 — TOPIC_AUDIT

> **最后更新：2026-09-23**
> **状态：ACTIVE TOPIC AUDIT / 尚未锁定论文题**
> **角色：repo 内 canonical 选题审计；记录“为什么选 / 为什么不选”的证据链。**
> **项目运行状态：以 `docs/PROJECT_RECORD.md` 为准。**
> **当前 canonical 决策：先完成 clean-slate whole-body Substrate Gate，再重新筛题。**

## 0. [CURRENT | SNAPSHOT]

2026-09-23 项目基础建设完成后，用户恢复实际研究，优先建立可靠且能力明确的
公开 RL 策略基线。以下候选账本保留；本轮不新增或晋级论文题。
方法/权重先按任务需要确定其证据等级，不能把工程默认选项写成已选定最优方案。
具体阶段和下一步跟随 PROJECT_RECORD 与 CURRENT。

当前不再围绕 Raibert / fixed-trot / SRBD hierarchy 直接锁题。

主 substrate：

`Go2 + MuJoCo full-body model → unified task/cost API → whole-body predictive control → pluggable backend/prior`

- MJPC/iLQR：default research backend；
- DIAL/MPPI：sampling challenger；
- contact-implicit：按问题启用；
- Go2 RL RobotLab/GYM：capability baseline / teacher / prior；
- 旧 Raibert+fixed trot+SRBD+WBC：legacy baseline。

此前 L9、L10/TimedReach、SEFR、FSEF 等全部 `HOLD / RE-AUDIT`。只有新 substrate 与强 RL baseline 下仍稳定存在的 failure 才能重新晋级。

## 1. [ACTIVE PRINCIPLE] Dual-goal 硬约束

候选必须同时满足：
1. 前期工程直接推进 Go2 terrain demo；
2. 后续有可证伪 scientific gap；
3. 核心 Gate 可在 Atlas / RTX 5080 完成；
4. 两周量级能得到继续/停止硬证据；
5. 负结果也可解释；
6. 不是旧 hierarchy 人为制造的问题。

老师任务与论文题不允许拆成两套互不相干的系统。

## 2. [HISTORICAL] 选题主线如何演化

### Phase A：5 cm step / terrain-aware
最初围绕 known step、foothold、swing clearance 和 joint-limit feasibility 推进。

用户持续追问：
- 为什么就是 5 cm？
- 为什么固定 trot？
- baseline 真的越障失败了吗？
- terrain planning 为什么只在 swing 层修？

这迫使项目从“修一个高度”转向 capability frontier。

### Phase B：L9 Preview
研究 preview / future terrain timing 对 foothold/body control 的作用。后续发现局部效应可能混有 reference-index / timing implementation 问题，且与老师任务关联不够直接，降为 `HOLD / RE-AUDIT`。

### Phase C：TimedReach → SEFR → FSEF
尝试把问题抽象成“几何可达但 schedule 不可执行”的 limb-level gap。

强前作与反对意见不断压缩空间：
- KCFRC-like path + retiming；
- TOPP / SIPP / ST-RRT*；
- SI-RRT / kinodynamic planning；
- whole-body MPC / optimizer。

最终剩余问题过窄，而且可能只是旧 decomposition 的产物，因此暂停。

### Phase D：底座重置
用户提出“为什么不能推倒重来，换最佳研究底座？”后，优先级改变：若 whole-body predictive control 能自然调整 body/contact/timing，旧候选就不值得围绕 hierarchy 发明中间层。

## 3. [SUPERSEDED] DIAL 曾作为 default 的原因与撤回

DIAL full-order、torque-level、training-free、sampling-based，且不需要把固定 gait 当硬 constraint，看起来最能解除旧架构天花板。

但继续审计后：
- typical sampling rollout 成本高；
- RTX 3090 级硬件已有实时性压力；
- 仓库维护活跃度有限。

因此“自由度最高”≠“最适合作为日常研究底座”。

DIAL 当前只做 challenger / diagnostic backend。

## 4. [CURRENT] 为什么 MJPC 是 default

不是因为它“绝对 SOTA”，而是当前约束下综合最好：
- full-body MuJoCo dynamics；
- training-free；
- Go2 路线可施工；
- task / residual / cost 易改；
- 机制实验归因清楚；
- 适合单机 CPU substrate。

边界：
- gait/contact reference 多为 soft residual/cost；
- iLQR 的 contact mode exploration 本身弱；
- 不能宣称 MJPC 是 contact-implicit。

因此 contact-sequence/timing emergence 若成为核心问题，要引入 sampling/contact-implicit challenger，而不是硬让 MJPC承担所有问题。

## 5. [CURRENT] RL baseline 的研究作用

公开 Go2 RL policy 不只是“另一个 controller”，而是能力对照：
- 测哪些 terrain 已能轻松解决；
- 暴露 learning policy 与 predictive-control 的共同 failure；
- 可作为 teacher/prior/proposal；
- 防止围绕弱 baseline 造假问题。

第一阶段优先使用公开 checkpoint，不从头训练。

## 6. [CANDIDATE LEDGER]

| 候选 | 状态 | 核心原因 / 重启条件 |
|---|---|---|
| learned proposal → WBMPC | DOWNRANK | hybrid / learned prior 拥挤；需明确 unresolved interface |
| decision-relevant active sensing | HOLD | active probing/VoI 不新；需可信 contact-uncertainty gap |
| warm-start/contact basin | DOWNRANK | literature 成熟；需实证成为 terrain WBMPC 核心瓶颈 |
| risk / lazy verification | DOWNRANK | TAMP/risk calibration 已覆盖；需 legged-specific structure |
| long-horizon depth | DOWNRANK | 太通用；需 contact-search 专属效应 |
| state/cache abstraction | DOWNRANK | 更像 implementation defect；修复后再谈一般问题 |
| L9 Preview | HOLD / RE-AUDIT | 可能是 reference/timing bug；需新 substrate 跨-controller复现 |
| L10 / SEFR / FSEF | HOLD / RE-AUDIT | 与 retiming/planning/WBMPC 重叠；可能是旧 hierarchy 产物 |

## 7. [CURRENT | GATE] Substrate Gate 0 对选题的作用

当前不直接“找论文题”，而先建立 capability/failure map：

1. MJPC；
2. strong Go2 RL checkpoint；
3. 必要时 DIAL/MPPI；
4. shared terrain × speed benchmark。

只有同时满足以下条件的 failure 才进入下一轮：
- 跨强 baseline 稳定；
- 可复现；
- 有明确机制假设；
- 近期强前作不能直接覆盖；
- 有 falsifier / stop condition；
- 资源可承担；
- 实现直接推进 Go2 demo。

## 8. [TRACEABILITY] 关键质疑

- “baseline 干净了，但路线本身会不会不好？” → 架构审计。
- “baseline 不是没做越障吗？” → 修正事实边界。
- “为什么是 trot / 5 cm？” → capability frontier。
- “老师任务和论文题不能拆” → dual-goal。
- “为什么不能推倒重来？” → whole-body substrate reset。
- “DIAL 太重且仓库不活跃” → DIAL 降为 challenger。
- “这领域发展这么快，别拿 2018 当当下” → 选题必须以近两年强工作重新审计。

## 9. [CURRENT | NEXT AUDIT]

2026-09-22 首轮正式平地 RL 移植验收完整采集但未达位移和速度误差门槛，
结果见 `docs/validation/substrate_first_capture_20260922/RESULTS.md`。这是单次
部署兼容性失败，尚未完成因果归因；不改变候选排序，也不能晋级为论文问题。
保留轨迹与锁定部署语义的离线诊断已经完成，见
[诊断结果](validation/governance_diagnosis_20260922/RESULTS.md)。当前按新任务
推进源条件复现与受控测试；能力结果不足时，不把部署差异升级为选题。

先读 `docs/PROJECT_RECORD.md` 的 Substrate Gate 结果，再问：

> 解除 fixed-gait / SRBD architectural bias 后，强 WBMPC substrate 与强 learned baseline 仍共同暴露哪些稳定 terrain-locomotion failure？

Gate 未完成前，不得从某个历史候选直接继续补方法。

## 10. [2026-09-22 | GOVERNANCE]

从 2026-09-22 起，本文件与 `docs/PROJECT_RECORD.md` 由 GitHub 统一维护。Library 不再保存正文副本。

## 11. 维护协议

每轮尽量恢复：
`TRIGGER → EVIDENCE → HYPOTHESIS → GATE → VERDICT → CARRY-FORWARD`

规则：
- 没搜到前作 ≠ novelty；
- 摘要/全文/源码/真实运行证据等级不能混写；
- current candidate status 只维护一个 canonical ledger；
- 路线变化先改 CURRENT，再补历史；
- 执行状态变化同步 `docs/PROJECT_RECORD.md`；
- 普通工程流水不写。
