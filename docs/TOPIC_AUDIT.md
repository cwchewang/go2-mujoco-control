# Go2 — TOPIC_AUDIT

> **最后更新：2026-10-05**
> **状态：ACTIVE TOPIC AUDIT / 尚未锁定论文题**
> **角色：repo 内 canonical 选题审计；记录“为什么选 / 为什么不选”的证据链。**
> **项目运行状态：以 `docs/PROJECT_RECORD.md` 为准。**
> **当前 canonical 决策：MuJoCo 是已有证据的 evaluation physics；新研究可按任务与资源选择其他 stack。Go2 是当前 testbed，先选择可复现的强控制实现，再定义有实际意义的任务与具体机制问题。**

> **2026-10-04 用户目标更新：** 原实习教师的仿真跨障碍作业降为历史背景；
> 优先本人学习、研究与可解释可复验的高含金量成果，用于进组与未来学校申请。
> 仿真演示是展示资产，不再是选题硬约束。当前 MJPC 扩展路线暂搁为 conditional；
> 后续用户纠正：旧权重低速/方向失败不决定新主线；后续按
> [推进卡](research/TASK_PROJECT_FOCUS_RESET_20261004.md) 复现选定原生强底座，不强制先做 PGTT 对旧 CTS 的比较。
> 这不确定论文题、不改变已有科学分类、不授予新的实验预算。
> 长期仍争取有强对照与机制证据的新方法；近期先完成可复现能力研究。
> 来源比较与主底座选型已完成：MoE-CTS 方法、作者认可 go2_rl_robotlab 原生实现；先用 Lab176k 策略在同仓 MuJoCo 复现。
> DIAL 为需要时的优化对照，PGTT 为 heightmap/phase 备选；当前 WSL 内存不足官方 IsaacLab 自训要求。
> 已完成 pinned native MuJoCo 工程复现 PASS，但 scientific/capability qualification 仍待完成；
> 具体科研问题尚未锁定，不把 Lab 发布成绩当 RSS 同表数字。

## 0A. [2026-10-05 | ENGINEERING PASS; SCIENTIFIC QUALIFICATION PENDING]

MoE-CTS native reproduction evidence at `docs/validation/moe_cts_native_reproduction_20261005/RESULTS.md`
is a deterministic, fixed-horizon engineering smoke at code
`28b4516d22617b11aeaf8ead63cc00b0c0bcd1bd` with policy SHA-256
`c602e749ac292921e3d6f5b2ab1749c4e4eaa6dbe51f751cce5b669b102d10a2`:

- `flat` 3.0 s: x=`2.5150989028` m, mean body-vx=`0.8391199433` m/s;
- `stairs` 7.0 s: x=`6.0629091387` m, mean body-vx=`0.8735359818` m/s;
- `stairs_and_slope` 10.0 s: x=`7.2067317885` m, mean body-vx=`0.7822757093` m/s.

Each run reached its fixed horizon with no runtime or numerical error. The result is
engineering evidence only: no success-rate, robustness, controller-ranking, or
research-gap claim follows, and scientific/capability qualification remains pending.
Next is bounded multi-condition/multi-seed capability measurement plus
perturbation/failure mapping before selecting a research mechanism.

## 0. [2026-09-28 / 10-02 | RETAINED SNAPSHOT]

本节原路线与结果保留。新底座选型以本页顶部用户更新与当前推进卡为准；
共享平台与 MuJoCo/MJX 迁移不再是选择研究起点的前置条件。

2026-09-28，#189 仍是第一张封存 RL capability map，但须按
[语义勘误](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)
解释：5 cm、10 cm、5/15/5 cm repeated steps 的 bounded terrain conclusions
保留；v1 `low_friction_cross` 只保留 frozen-scene 几何/task-goal PASS，不是低摩擦
robustness evidence；修正 body-local qvel-z 后 yaw probe 仍为 PERFORMANCE_FAIL。
该结果仍只属于一个 checkpoint/controller，不能把任何 case 直接升格为论文 gap。

当前 architecture decision：

`MuJoCo canonical evaluation physics → MuJoCo/MJX scalable substrate direction → shared task/evaluation semantics → reusable controller families → aligned failure map → mechanism diagnosis`

- **Go2**：第一 testbed，不是项目 identity。
- **MuJoCo/MJX**：统一物理与评测的 substrate 方向；MJX scalable path 尚未完全实现。
- **MJPC/iLQR**：强 gradient-based comparator，不是 privileged default truth。
- **RL checkpoint**：learning capability baseline / possible teacher or prior。
- **Sampling/search、contact-implicit/hybrid**：按 task 和 failure evidence 决定是否启用。
- **成熟 infrastructure**：优先复用；科学 ownership 在 task/information/timing/intervention、diagnostics、比较和 evidence-driven 新机制。

研究问题保持开放：

> 在统一物理、任务和评测语义下，不同 controller family 在哪些 embodied-control 情况下出现稳定、可复现、机制可解释的 failure；其中哪些确实需要新算法，而不是 tuning、部署差异或成熟方案？

L9、L10/TimedReach、SEFR、FSEF 仍为 `HOLD / RE-AUDIT`。本项目尚无 generic multi-controller evaluation platform。

## 1. [SUPERSEDED → REFRAMED] 老师交付与科研架构

本节保留截至 2026-10-02 的路线记录。下述“最低交付约束 / 交付要求”已被
2026-10-04 用户目标更新取代；原教师作业不再是当前必须交付的目标。

曾将老师的 Go2 terrain demo 与科研路线绑定为 dual-goal 硬约束，以避免维护两套
互不相关的系统。现在将其改为最低交付约束：如果成熟开源 controller 能低成本
满足基本效果，可直接复用。为了看起来“不是 clone”而从零重写成熟控制器，不会
自动产生科学价值。

新的原则：
1. 基本 Go2 控制/越障效果是交付要求，不决定科研架构。
2. 可复用成熟 simulator、solver、controller 和 RL infrastructure。
3. 项目必须掌握 task、information、timing、intervention、benchmark、diagnostics 和 evidence。
4. 只有 failure evidence 指向缺失机制时，才实现新 algorithmic component。
5. 候选仍需可证伪、近期能收缩问题空间、资源可承担，且不是弱 baseline 或旧 decomposition 制造的问题。

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

### Phase E：统一 substrate 与 controller-family 比较

#189 后，项目保留 MuJoCo 作为当前 canonical evaluation physics，把 MuJoCo/MJX 作为
目标 substrate；不把 Go2 或 MJPC/iLQR 当作项目身份或先验主方法。成熟 solver/controller
优先复用，研究工作转向任务与信息语义、对齐比较、诊断及由证据支持的新机制。

## 3. [SUPERSEDED] DIAL 曾作为 default 的原因与撤回

DIAL full-order、torque-level、training-free、sampling-based，且不需要把固定 gait 当硬 constraint，看起来最能解除旧架构天花板。

但继续审计后：
- typical sampling rollout 成本高；
- RTX 3090 级硬件已有实时性压力；
- 仓库维护活跃度有限。

因此“自由度最高”≠“最适合作为日常研究底座”。

DIAL/MPPI 归于 sampling/search family；只有具体任务的 failure evidence 指向相关
机制时，才评估它是否适合作为比较对象，不预先赋予 default 或 designated challenger 角色。

## 4. [CURRENT] 为什么不预选 MJPC/iLQR 为 default planner

MJPC/iLQR 仍是强 comparator：它使用 full-body MuJoCo dynamics、可修改 task/residual/cost，
且能支持可解释的 gradient-based whole-body control comparison。这些优点保留。

但 physics/evaluation substrate 和 planner family 是不同决策。预先锁定 iLQR 会把问题
偏向 gradient-based optimization，并可能裁掉 sampling/search、learned controller 或
contact-mode 方法本来应该解释的 failure。现阶段保留 controller-family 选择空间：

- gradient family：MJPC/iLQR 等；
- sampling/search family：Predictive Sampling/CEM、DIAL/MPPI 等；
- learning family：公开 RL checkpoint 与按需 learned prior；
- contact-implicit/hybrid：仅在 contact sequence/timing/mode search 成为问题时。

公平比较优先共享 physical model、initial state、command、scene、terminal metrics 和
success semantics；controller 内部 cost、information condition 与优化方式不同则显式
记录。目标是定位 failure mechanism，不是选择永久唯一 controller。

## 5. [CURRENT] RL baseline 的研究作用

公开 Go2 RL policy 不只是“另一个 controller”，而是能力对照：
- 测哪些 terrain 已能轻松解决；
- 暴露 learning policy 与 predictive-control 的共同 failure；
- 可作为 teacher/prior/proposal；
- 防止围绕弱 baseline 造假问题。

第一阶段优先使用公开 checkpoint，不从头训练。

2026-09-23 已建立冻结 1 m/s 源条件平地参考；2026-09-24 完成完整 shared-transfer
两次正式 PASS，并进一步完成 #189 九例正式 capability map。5 cm、10 cm、5/15/5 cm
repeated-step 的 PASS 结论保留；`low_friction_cross` 仅是原 v1 scene 上几何/task-goal
PASS，不是低摩擦 robustness evidence；half-speed、reverse、lateral、yaw 仍为冻结
门槛下的 PERFORMANCE_FAIL。yaw 的更正指标为 mean body-local qvel-z 0.1038956543
rad/s、MAE 0.3961043457 rad/s，仍超过 0.1 tolerance。这个 bounded 结果不足以宣布
terrain 天花板、跨控制器共同瓶颈或论文题。详见 PROJECT_RECORD 与
[语义勘误](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)。

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

当前先建立统一评测与 multi-controller failure map：

1. 固定 MuJoCo physical model、scene/reset、command、metrics 与 success/safety semantics。
2. #189 已完成第一张 RL map；low-friction 和 yaw 解释按 erratum 修正。
3. 先审计成熟 Go2 whole-body control implementation、MJPC task 和 runner，复用已有闭环能力。
4. 为选定的 controller families 编写独立对齐任务，并记录信息条件、controller cost/reward 与优化方式。
5. 只有明确 failure structure 后才启动 sampling/search 或 contact-implicit diagnosis；需要大规模 rollout/learning 时再推进 MJX。

值得进入研究筛选的 failure 必须稳定可复现，且不是 deployment/tuning/benchmark
artifact；它应有 falsifier、机制假设、资源边界和近期 continue/stop evidence。跨强
baseline failure 或清晰的 controller-specific contrast 都可能有价值。全部通过则从
候选中删除。

## 8. [TRACEABILITY] 关键质疑

- “baseline 干净了，但路线本身会不会不好？” → 架构审计。
- “baseline 不是没做越障吗？” → 修正事实边界。
- “为什么是 trot / 5 cm？” → capability frontier。
- “老师任务和论文题不能拆” → dual-goal。
- “为什么不能推倒重来？” → whole-body substrate reset。
- “DIAL 太重且仓库不活跃” → 撤销 DIAL default；本轮架构决策进一步取消预设的单一 challenger 角色。
- “这领域发展这么快，别拿 2018 当当下” → 选题必须以近两年强工作重新审计。

## 9. [CURRENT | NEXT AUDIT]

#189 的 RL failure map 不重跑。下一步先审计成熟 Go2 whole-body control implementation
能提供哪些 pinned controller、task/cost、runner 和可复用 gait/contact infrastructure，
避免从零实现已有闭环方案。之后再定义 MuJoCo 上的对齐比较：1 m/s flat reference、
command-space probes、5 cm/10 cm/repeated-step anchors；若需要 low-friction case，须使用
语义修正后的 v2 fixture，并由新任务前瞻授权，不能接续 #189 的 sealed result。

随后让 learning、gradient MPC、sampling/search 按证据进入 benchmark。判读要区分
controller-specific issue、共同 failure、成熟方案/tuning 和 deployment artifact。只有
可证伪且不能由已有方法直接覆盖的机制才进入新方法任务；此处不授予 live run 或新
scientific attempt。

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


## 12. [2026-10-02 | ACTIVE] Third-stage topic selection remains open

The user's third-stage delegation concerns finding a research topic. Local
two-repeat RL friction acceptance does not complete that stage. The
[read-only MJPC diagnosis and minimum proposal](validation/stage3_topic_diagnosis_20261002/RESULTS.md)
finds concrete private-model/plant confounds on the correctly pinned Go2 branch;
the single RR_calf stop cannot establish a stable algorithmic failure.
Model/actuator correction is engineering, not novelty. MuJoCo evaluation and
RL anchors remain useful; the adapted MJPC comparator needs bounded admission,
not unlimited repair or a blind switch to a new planner.

Current decision: retain substrate, keep this MJPC candidate conditional, first
complete configuration/force/contact evidence audit, then consider separately
reviewed minimum diagnostics. Zero-forward/Manual Trot is not a static-standing
test. No new physics or fourth-stage method is authorized by this audit.
RL command-space and timing-response questions remain testable independently;
their deployment falsifiers and recent prior-work checks precede topic selection.
Warm-start/contact basin and other old DOWNRANK/HOLD entries remain unchanged.
