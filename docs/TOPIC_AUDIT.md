# Go2 — TOPIC_AUDIT

> **最后更新：2026-09-28**
> **状态：ACTIVE TOPIC AUDIT / 尚未锁定论文题**
> **角色：repo 内 canonical 选题审计；记录“为什么选 / 为什么不选”的证据链。**
> **项目运行状态：以 `docs/PROJECT_RECORD.md` 为准。**
> **当前 canonical 决策：MuJoCo/MJX 作为统一研究 substrate；Go2 只是第一 testbed；不预先锁定 MJPC/iLQR 或任何单一 controller family，先用对齐 benchmark 让 failure structure 决定后续方法与选题。**

## 0. [CURRENT | SNAPSHOT]

2026-09-28，#189 已把 RL 侧的 bounded capability map 固化：1 m/s flat reference、5 cm、10 cm、5/15/5 cm repeated steps 与 low-friction crossing PASS；half-speed、reverse、lateral、yaw probes 为 PERFORMANCE_FAIL。这个结果已经足以作为第一张可审计 failure map，但仍只是一个 controller/checkpoint 的结果，不能把其中任何 failure 直接升格为论文 gap。

本轮对研究底座做了第二次架构审计。新的 canonical 结论不是“MJPC/iLQR 是默认主方法”，而是：

`MuJoCo / MJX unified physics & evaluation substrate → shared task / metric semantics → interchangeable controller families → failure-map comparison → mechanism diagnosis → new method only if evidence demands it`

当前角色划分：
- **MuJoCo / MJX**：真正的统一研究 substrate；CPU MuJoCo 负责 canonical deterministic evaluation，GPU/JAX 路径用于需要的大规模 rollout / learning / sampling；
- **Go2**：第一 testbed / embodiment，不再是项目 identity；未来允许扩展到其他 legged / humanoid / manipulation embodiment；
- **RL checkpoint**：learning-based capability baseline / teacher / prior；
- **MJPC/iLQR**：gradient-based whole-body MPC family 的一个强实现与 comparator，不再享有默认真理地位；
- **MJPC Predictive Sampling / CEM、DIAL/MPPI**：sampling/search family；是否启用由具体 failure mechanism 决定，而不是预先设为“后备方案”；
- **contact-implicit / hybrid methods**：仅在 contact sequence / timing / mode search 真的成为机制问题时引入；
- **旧 Raibert + fixed trot + SRBD + WBC**：legacy baseline，只保留历史对照价值。

因此当前 research question 不应写成“如何把 MJPC 做强”或“如何证明自己实现了一个 controller”，而应写成：

> 在统一物理、任务和评测语义下，不同 controller family 在哪些 locomotion / embodied-control 情况下出现稳定、可复现、机制可解释的 failure；这些 failure 中哪些需要新的算法，而不是 tuning、部署差异或已有成熟方案？

此前 L9、L10/TimedReach、SEFR、FSEF 等仍全部 `HOLD / RE-AUDIT`。只有跨强 baseline 稳定存在、且能形成清晰 falsifier 的 bottleneck 才能重新晋级。

## 1. [SUPERSEDED → REFRAMED] 老师交付不再决定科研架构

此前把“老师的 Go2 terrain demo 交付”和“论文研究路线”绑定成 dual-goal 硬约束，目的是避免做两套互不相干的系统。这个约束现在需要降级。

原因：若老师侧的最低要求只是基本控制/越障效果，而成熟开源 controller 已能轻易给出相近 demo，那么为了“显得不是 clone”而从零重写一个普通 controller，并不会自动产生科研价值。**代码是否从零手写，与 scientific novelty 是两个不同维度。**

新的原则：
1. 老师的基本控制效果只作为**最低交付约束**，尽量用成熟组件低成本满足；
2. 科研架构只由研究问题、可证伪性、强 baseline、公平 benchmark 与资源边界决定；
3. 允许直接复用成熟 solver、simulator、generic MPC/RL infrastructure；
4. 必须自己掌握并控制 task / residual / cost、benchmark、diagnostics、intervention 与 evidence chain；
5. 只有当 failure evidence 指向某个缺失机制时，才自己实现新 algorithmic component；
6. 不为了“证明工作量”重造已有成熟控制器，也不接受 clone → run demo 作为研究贡献。

候选仍需满足：Atlas / RTX 5080 可承担、近期能得到继续/停止证据、负结果可解释、且不是人为弱 baseline 或旧 decomposition 制造的问题。

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

### Phase E：从“MJPC-based Go2”升级为“MuJoCo/MJX multi-controller substrate”

#189 之后重新审视“最佳研究底座”的含义。结论是：MJPC/iLQR 可以很强，但把它预设成默认主方法会偷偷限制问题空间；Go2 也不应成为项目 identity。真正需要长期保留的是统一 physics / task / metric / evidence substrate，以及可替换 controller family。

同时纠正一个研究工程误区：为了避免老师觉得“只是 clone”，从零重写成熟 MPC/RL stack 并不会自动提升科研含金量。更有价值的 ownership 是：能解释、修改、替换关键控制链，并在证据要求出现时实现新的 mechanism。

## 3. [SUPERSEDED] DIAL 曾作为 default 的原因与撤回

DIAL full-order、torque-level、training-free、sampling-based，且不需要把固定 gait 当硬 constraint，看起来最能解除旧架构天花板。

但继续审计后：
- typical sampling rollout 成本高；
- RTX 3090 级硬件已有实时性压力；
- 仓库维护活跃度有限。

因此“自由度最高”≠“最适合作为日常研究底座”。

DIAL 当前只做 challenger / diagnostic backend。

## 4. [CURRENT] 为什么不再锁定 MJPC/iLQR 为 default planner

MJPC 仍是重要且成熟的研究框架，iLQR 也仍是强 comparator：full-body MuJoCo dynamics、training-free、task / residual / cost 易修改、机制归因清楚、CPU 上可做严格实验。这些优点全部保留。

但“研究 substrate”与“默认 planner”必须分离。若预先把 iLQR 定为主方法，会把研究问题偏向 gradient-based trajectory optimization；而当前真正可能重要的 failure 恰恰包括 local basin、nonsmooth contact、contact-mode exploration、multimodality、learned prior 与 online search。把其中任一 planner 设为默认真理，都会提前裁掉问题空间。

因此新的结构是：
- substrate：MuJoCo / MJX + shared task / metric / evidence semantics；
- gradient family：MJPC/iLQR 等；
- sampling/search family：Predictive Sampling / CEM / DIAL / MPPI 等；
- learning family：公开 RL checkpoint 与后续必要的 learned prior / policy；
- contact-implicit / hybrid：仅在机制证据需要时加入。

比较时优先保持 physical model、initial state、command、scene、terminal metrics 与 success semantics 对齐；controller 内部 reward/cost、信息条件和优化方式可以不同，但必须显式记录。目标不是选出“永久唯一 controller”，而是定位 failure mechanism。

## 5. [CURRENT] RL baseline 的研究作用

公开 Go2 RL policy 不只是“另一个 controller”，而是能力对照：
- 测哪些 terrain 已能轻松解决；
- 暴露 learning policy 与 predictive-control 的共同 failure；
- 可作为 teacher/prior/proposal；
- 防止围绕弱 baseline 造假问题。

第一阶段优先使用公开 checkpoint，不从头训练。

2026-09-23 已建立冻结 1 m/s 源条件平地参考；2026-09-24 完成完整 shared-transfer 两次正式 PASS，并进一步完成 #189 九例正式 capability map。结果显示 1 m/s 的 5 cm、10 cm、5/15/5 cm repeated steps 与 low-friction crossing 均通过，而 half-speed、reverse、lateral、yaw 在冻结性能门槛下失败。这个对比提示“当前 RL checkpoint 的首先暴露边界更偏 command-space 而非这些简单前向 terrain cases”，但尚不足以宣布 terrain 天花板、跨控制器共同瓶颈或论文题。详见 PROJECT_RECORD。

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

当前不直接“找论文题”，而是完成统一 substrate + multi-controller failure map：

1. **benchmark layer**：固定 MuJoCo physical model、scene、reset、command、metrics、success / safety semantics；
2. **learning baseline**：#189 已完成第一张 RL capability map；
3. **gradient MPC family**：先审计并复用成熟 Go2 whole-body MJPC locomotion implementation，避免从零重造已有闭环；在对齐 benchmark 上形成 iLQR failure map；
4. **sampling/search family**：优先利用同 substrate 中的 Predictive Sampling / CEM；只有具体 failure 需要时再引入 DIAL/MPPI；
5. **GPU / learning branch**：需要大规模 rollout、training 或 learned prior 时再用 MJX/MJX-Warp / learning stack，不为统一外观强行提前迁移；
6. **cross-controller diagnosis**：由 PASS/FAIL 结构决定后续机制实验，而不是先决定“要发明哪种方法”。

只有同时满足以下条件的 failure 才进入下一轮：
- 在强 baseline 下稳定可复现，或形成清晰的 controller-specific mechanism contrast；
- 不是 deployment / tuning / benchmark artifact；
- 有明确机制假设；
- 有 falsifier / stop condition；
- 近期强前作不能直接覆盖；
- Atlas / RTX 5080 资源可承担；
- 即使负结果也能收缩问题空间。

## 8. [TRACEABILITY] 关键质疑

- “baseline 干净了，但路线本身会不会不好？” → 架构审计。
- “baseline 不是没做越障吗？” → 修正事实边界。
- “为什么是 trot / 5 cm？” → capability frontier。
- “老师任务和论文题不能拆” → dual-goal。
- “为什么不能推倒重来？” → whole-body substrate reset。
- “DIAL 太重且仓库不活跃” → DIAL 不做预设 default，仅在具体 search/contact 机制诊断时启用。
- “MJPC/iLQG 听起来也不怎么强，当时不是说选最强成熟方案吗？” → 区分“强成熟 research framework”与“绝对最强 planner”；取消单一 default planner 锁定。
- “为了老师看起来不像 clone，自己实现控制算法到底有什么意义？” → 老师最低交付与科研 novelty 解耦；不以从零重写成熟 stack 证明研究价值。
- “如果不考虑老师交付，这套底座最佳吗？” → 保留 MuJoCo 根基，但把 canonical substrate 提升为 MuJoCo/MJX + multi-controller，而不是 MJPC-based Go2。
- “这领域发展这么快，别拿 2018 当当下” → 选题必须以近两年强工作重新审计。

## 9. [CURRENT | NEXT AUDIT]

#189 已完成 RL 侧 terrain × direction/speed capability map，因此不再把“RL failure map 长什么样”作为开放问题。下一步不是立刻自己写一个 MJPC closed-loop controller，而是先做一次**成熟 Go2 whole-body control implementation audit**：核清 pinned MJPC fork、上游 quadruped task、现成 Go2 whole-body deployment 与可直接复用的 gait/task/runner 到底已经提供什么，避免把成熟能力重新实现一遍。

随后在统一 benchmark 上建立 cross-controller map：
- anchors：flat 1 m/s、repeated steps、low friction；
- high-information probes：half-speed、reverse、lateral、yaw；
- gradient family：MJPC/iLQR；
- sampling family：优先同 substrate 的 Predictive Sampling / CEM，必要时 DIAL/MPPI；
- learning family：#189 RL checkpoint。

判读原则：
- RL FAIL / model-based PASS → 优先解释为该 checkpoint / training / command-utilization 局限，不急于造新控制算法；
- RL PASS / iLQR FAIL / sampling PASS → 强指向 local-gradient / basin / contact-search 机制；
- 多 family 在同一 case 稳定 FAIL → 才值得审计 shared task difficulty、contact reasoning、information limitation 或更普遍的 embodied-control gap；
- 全部 PASS → 直接从研究候选删除。

此前 0.15 m/s 不足、横漂与 23 cm 楼梯 base-contact stop 继续保留为观察边界，不直接升格为论文问题。当前更准确的问题是：

> 在统一 MuJoCo/MJX 物理、任务和评测语义下，learning、gradient-based MPC 与 sampling/search controller 分别在哪些 embodied-control 情况下出现稳定 failure；哪些 failure 能被机制化并真正需要新的算法？

Gate 未完成前，不得从某个历史候选或某个 planner 的局部失败直接继续补方法。

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
