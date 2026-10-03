# Go2 — PROJECT_RECORD

> **最后更新：2026-10-02**
> **状态：R1 SHARED CONTRACTS IMPLEMENTED; NATIVE MJPC ADAPTER ENGINEERING-WIRED; GATE 0 INCOMPLETE**
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

## 1. [2026-10-02 | CURRENT | SNAPSHOT] 当前项目

#189 已形成第一张 bounded RL capability map。其封存执行与原始 case 记录仍在
[原结果](validation/rl_capability_map_successor_20260924/RESULTS.md)；
[2026-09-28 语义勘误](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)
限定了 low-friction 与 yaw 结论。5 cm、10 cm、repeated-step 的结论保留；
v1 low-friction PASS 仅是冻结场景中的几何/任务目标 PASS，不是低摩擦鲁棒性
证据；yaw 仍为冻结阈值下的 PERFORMANCE_FAIL。

### Planned architecture

MuJoCo 是当前项目 canonical evaluation physics；MuJoCo/MJX 是目标 scalable
substrate，尚未完全实现。Go2 是第一 testbed，不是项目 identity。MJPC/iLQR 是
强 gradient-based comparator，但不享有默认 truth 或 privileged planner 地位。
按任务和 failure evidence 选用 sampling/search、learning、contact-implicit 等
成熟 controller/solver infrastructure。研究 ownership 在 task / information /
timing / intervention 定义、诊断、公平比较与证据要求确实支持的新机制。基本
Go2 demo 是交付约束，可复用成熟组件；从零重写控制器本身不构成科学贡献。

最小共享合同已在 2026-10-01 分阶段落地主线：ControllerAdapter、
InformationSpec、TimingSpec、TaskSpec、ScenarioSpec 和 canonical
Evaluator / physical-oracle boundary。它们明确动作、信息、时间、任务、场景
与独立 outcome 语义；sealed 历史 runner/analyzer 未被改写，也仍不是通用 SDK。

### Currently executable capabilities

仓库现有 MuJoCo Go2 assets、schema-2 公开 RL execution/analyzer/offline verifier、
static MJPC admission，以及一个 source-pinned persistent native MJPC controller
适配面。native controller 验证 pinned source 的 nominal mjBIAS_NONE + gain/bias
事实，只在其私有 planning model 上应用显式 mjBIAS_AFFINE compatibility
correction，输出 joint-position targets，再经共享 adapter 转为 canonical
direct-torque action。零 canonical-step 工程 smoke 已证明该链可执行且不推进
evaluation plant。随后 R1 timing repair 又显式拆开 slow planning/control cadence 与
current-state feedback cadence：planning 仅在声明 tick 更新，feedback tick 不重规划，
command 也只在 planning tick 采样。2 ms feedback 是 shared canonical adaptation，
不是作者原生 feedback 频率声明；当前 observed planning 约 28 ms，因此 prospective
anchor 仍必须标记 offline_unbounded。这些都不是 locomotion capability、real-time
或跨 controller 比较结论。

第一份 prospective aligned flat anchor v1 已完成 no-physics preparation：
共享 body-frame 1 m/s TaskSpec、flat ScenarioSpec、canonical Evaluator/action
语义已冻结；RL 与 MJPC 的 InformationSpec / TimingSpec 明确分别记录，不伪装成
相同信息预算。prep commit、protocol SHA、scene physical fingerprint、RL checkpoint
与 MJPC source/binary identity 均已离线核对。该 anchor 当前
physics_step_authorized=false、scientific attempts=0、状态 PREPARED / NOT_RUN，
必须先独立审查，不能据此产生任何 locomotion 或 controller 排名结论。
该独立语义审查已于 2026-10-01 完成：确认 broad integration guardrails 不等同
于 #189 flat_reference；冻结 home key 0 的 identity quaternion 使 world-x/world-y
guardrails 与初始 body forward/left 对齐，并将该前提及 canonical direct-torque
actuator 边界加入 fail-closed preflight。状态提升为 REVIEWED / NOT_RUN，但
physics_step_authorized 仍为 false、scientific attempts 仍为 0。

首次 live aligned capture v1 随后在独立 capture task / exact HEAD
2411c4af1f8ab95e50f7e07e672466b5c0abb406 上实际执行。RL 完成 500 个
canonical physics steps，宽松 1 s integration anchor 的独立 replay 为 PASS
(progress 0.612566 m，body-vx MAE 0.152334 m/s)。MJPC 的唯一 attempt 已消费，
完成 140 physics steps 后在 tick 140 replan 遇到 source Ground() raycast
no group 0 geom detected，通过严格 stdout JSON IPC 表现为 invalid JSON 并
基础设施中止。最后保存状态未触发 canonical physical failure。v1 永久关闭、
不得 retry；因此跨 controller comparison 仍 INCOMPLETE，不能产生排名或科学结论。

The separately admitted aligned capture v2 is now permanently closed at
ab27185f6c0ee47fdd09fecb367977bf4ab9cfde: RL and MJPC each completed500 canonical
steps/501 frames and passed the broad1s engineering horizon without a canonical
safety failure. The independent science closeout accepted only that frozen
engineering scope. MJPC body-vx MAE was0.811741m/s, and median planning28.453ms
does not establish20ms real-time performance. No mature-controller capability,
ranking, safety-stop live validation or scientific bottleneck follows.
See [v2 closeout](validation/aligned_flat_capture_v2_closeout_20261002/RESULTS.md).
V1 and v2 remain sealed; scientific attempts for v2 remain0.

The [shared baseline/probe campaign](research/TASK_SHARED_BASELINE_PROBES_V1_20261002.md)
ran at b1ac4f700cc0f8ed3bd431e28a230bc1ae71058d after final exact-head dual
approval and fresh in-process preflight. Its frozen whole-campaign safety stop
closed execution after3 scientific attempts and13287 canonical steps.
Both RL12s baseline repeats passed the declared operational thresholds
(mean body-vx0.885292m/s, MAE0.114708m/s), with identical raw bytes and maximum
raw state/applied-control repeat difference0. Adapted MJPC baseline1 stopped
at tick1287/2.574s for nonfoot_contact; zero-integration terminal reconstruction
confirmed the floor/RR_calf pair. One MJPC trial does not establish a stable
failure mechanism or controller-family ranking. The remaining17 arms, including
all16 challenges, were NOT_RUN. The four-baseline stage did not complete;
the old campaign challenge stage has no result and the MJPC useful-baseline gate remains unmet.
The local official verifier checked raw integrity and the real external ledger.
The campaign is permanently closed with no retry or replacement; see
[verified safety-stop closeout](validation/shared_baseline_probes_v1_closeout_20261002/RESULTS.md).
Native private rollouts were real and their total integration count is unknown.
Gate0 remains incomplete. The read-only diagnosis is complete: all foot contact
constraints disappear from2.450s, with floor/RR_calf safety stop at2.574s; sealed
raw has no private predicted trajectory/contact sequence, so no causal mechanism
is established. The separately delegated [RL friction task](research/TASK_RL_FRICTION_REFERENCE_V1_20261002.md)
now closes at live HEAD849b7aa13c82b13880cfc214083f2473e794e83e. Its independent
mu0.8-to0.3-at6s card consumed2 fresh scientific attempts/12000 canonical steps,
with0 private planning calls; both12s arms PASS. Primary mean body-vx is0.874101m/s
and MAE0.125899m/s, giving paired mean delta−0.011191m/s. The predeclared [6,12)
auxiliary mean is0.866755m/s, paired delta−0.018652m/s. Whole-episode lateral
max0.215713m and yaw max0.058913rad pass their original0.3 bounds.
Each arm verifies5726 changed active foot-floor contact-friction records over2948
ticks, first exposed state tick3001/6.002s; these are contact records, not
independent statistical samples or contact forces. Paired pre-intervention
prefix difference is0. Identical raw SHA151dfa3c8a7a24418dd0fbbfcfaaa015788b00e0cf56002a6ad38397adb7fb58
establishes deterministic reproduction, not independent statistical seeds.
The official independent raw/real-ledger replay is VERIFIED; both original
science and execution final read-only reviews approved. Current-input
qualification ran292 fresh Python checks and explicitly reused unchanged
sealed native checks. The failed initial wrapper entered no capture API and
consumed0 attempts/physics; its source and full logs remain preserved alongside
the actual CLI logs, claims and94-member archive.
See the [verified friction closeout](validation/rl_sliding_friction_reference_v1_closeout_20261002/RESULTS.md).

Together with the old RL baseline PASS and single adapted MJPC safety stop,
this completes one local experiment: a frozen
RL friction-condition point, without an aligned12s MJPC comparator. It does not
complete the user's third stage of finding a research topic. It does not
establish a controller ranking, stable MJPC failure mechanism, generic robustness
or a complete Gate0. The old campaign and17 NOT_RUN remain closed, and #189's
low-friction erratum remains unchanged. RL boundary and MJPC zero-forward-command
studies remain conditional diagnostic proposals requiring independent
prospective tasks. No fourth-stage method work is started.

The user corrected the stage scope after local closeout: third-stage topic
selection remains ACTIVE / OPEN. The premature stage-completion wording in the
local closeout/navigation at3ae9a7c is superseded here; scientific raw, metrics,
claims and two reviewers' local acceptance remain unchanged.
The [new read-only diagnosis](validation/stage3_topic_diagnosis_20261002/RESULTS.md)
confirms the correct pinned Go2 source branch, but finds private-versus-canonical
joint damping2.0 versus0.1, root mass7.521 versus6.921kg, floor-0.01 versus0m,
foot-contact impedance differences and missing private actuator force limits.
Both use impratio100; home and named PD mapping agree. These are material
prediction/adaptation confounds, not proof of the RR_calf cause or an iLQR limit.
MuJoCo evaluation and passing RL remain usable; this adapted MJPC is not yet
a useful strong comparator. Repair is engineering and must stay bounded.
Zero-forward still forces Walk/Manual Trot and cannot isolate static stability.
The minimum proposal is a source-bound parity/evidence audit followed only
under new independent scopes by instrumented frozen-versus-corrected prediction
one-arm3s diagnostics, total proposed canonical cap3000steps; none is launched.
RL command-space and temporal-response candidates remain testable without this
MJPC candidate; none is yet a novelty verdict or selected paper topic.
[Terrain/command admission](research/STAGE3_TERRAIN_ADMISSION_NOTES_20261002.md)
requires a new support-geom specification before any terrain capture: current
flat episode.py treats foot contact outside phase2_floor as forbidden. MJPC
lateral/reverse rejection is UNSUPPORTED, not capability FAIL. One-sided
finite differences at1e-6, derivative_skip0 and impratio100 already exist.
Stage-three selection still needs admissible terrain capability/failure evidence
and a falsifiable research question; engineering repair is not its endpoint.

### Scientifically verified results

已验证结论限于公开 RL checkpoint 在封存 adapter、reset、scene 和命令上的
#189 九例 map。原始轨迹与尝试账本未改写；语义修正见 erratum。没有证据证明
跨 controller bottleneck、普遍低摩擦鲁棒性或论文 gap；Gate 0 仍未完成。
2026-10-02 的12s shared baseline 两次 RL PASS 和一次 adapted MJPC 非足接触安全停止，亦限于该冻结条件；旧 shared campaign 的所有挑战未运行。独立 RL friction card 两次 PASS 已经 raw/真实账本验证和双末审通过，仅提供单一冻结条件点和确定性复现，不构成普遍 robustness map 或跨控制器排名。执行 frontier 跟随 `CURRENT.md`。

## 1D. [2026-09-24 | VERIFIED / BOUNDED; 2026-09-28 ERRATUM] RL capability map 正式完成

Praxis v2 #189 在 capture HEAD `e40b0933572345f23b37e3bb06350518fde63e76` 上完成冻结 schema-2 `rl-capability-map-v1` campaign。九个 case 各执行一次，authoritative ledger 记录 9/9 scientific attempts，capture 为 `CAPTURE_COMPLETE / CHARACTERIZED`，未发生 retry、SAFETY_STOP 或 INTEGRITY_STOP。独立 offline verifier 最终返回 `VERIFIED`，核对 external ledger、逐 case raw replay 与 sealed flat-reference digest，且 verification `physics_steps=0`。正式 closeout 为 `docs/validation/rl_capability_map_successor_20260924/RESULTS.md`，result commit `de21d8c3267e1c985cb57ed2d02004c686d05bd1`，Praxis review publication commit `35e69f652e986af13c147a6fe4e8fc9eea70c5f1`。

原始冻结结果分类及 #194 勘误后的解释：
- `flat_reference`：PASS，mean vx 0.8858825097 m/s，sealed digest 与 #166 精确一致；
- `flat_half_speed`：PERFORMANCE_FAIL；纵向 tracking 本身通过，但 flat cross-axis gate 失败，lateral displacement 0.57465 m、yaw 0.24710 rad；
- `flat_reverse_probe`：PERFORMANCE_FAIL，目标 -0.5 m/s，mean vx -0.35590 m/s；
- `flat_lateral_probe`：PERFORMANCE_FAIL，目标 vy 0.25 m/s，mean vy 0.16589 m/s；
- `flat_yaw_probe`：PERFORMANCE_FAIL；从未修改的 raw trajectory 离线更正后，目标 wz 0.5 rad/s、mean body-local qvel-z 0.1038956543 rad/s、MAE 0.3961043457 rad/s，仍超过冻结 0.1 rad/s tolerance；
- `step_5cm_cross`、`step_10cm_cross`、`repeated_steps_cross`：PASS 结论保留，其中 repeated steps 为冻结 5/15/5 cm profile；
- `low_friction_cross`：原始输出 PASS 保留为 frozen-scene 几何/task-goal classification；因 v1 effective contact 使用 foot friction 且足底也由 normal floor 支撑，低摩擦 robustness interpretation 撤回。

该结果只说明此 checkpoint / adapter / reset / scene / command set 下，**1 m/s 的 5/10/repeated-step 几何任务在冻结条件下通过，command probes 出现性能边界；低摩擦 robustness 未被验证。** 不能由此推出“terrain 已解决”“方向控制是论文 gap”或“MJPC 一定更好”。先审计成熟 Go2 whole-body control implementation 可复用面，再为对齐比较定义独立任务。

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
- **MuJoCo**：当前 canonical evaluation physics；比较应共享物理模型与 outcome semantics。
- **MuJoCo/MJX**：目标 scalable substrate 方向；MJX/GPU execution 尚未成为完整可执行项目接口。
- **Go2**：第一 testbed，因现有资产与路线基础；不是 project identity 或预设 contribution。

### Controller families and scientific ownership

MJPC/iLQG 是强 gradient-based comparator，不是默认 truth。公开 Go2 RL 是 learning
capability baseline / possible teacher or prior。Sampling/search、contact-implicit
或 hybrid methods 按具体 failure evidence 再选。比较需显式记录各控制器的信息条件、
内部 cost/reward 和优化方式，同时尽可能固定模型、初态、命令、场景与 terminal
metrics。

优先复用成熟 solver/controller infrastructure。项目的科学 ownership 位于 task、
information、timing、intervention 的定义，diagnostics、对齐比较和证据链，以及
证据支持的新机制。已有 Go2 demo 可由成熟组件满足；从头重写通用控制器不自动
产生 novelty。旧 Raibert + fixed trot + SRBD MPC + ID-WBC 保留为 legacy baseline。

### RL baseline

优先直接使用公开 checkpoint，不从头训练。#189 的封存结果可作 bounded RL
capability map：5 cm、10 cm 与 repeated-step 结论保留；low-friction case 只保留
v1 frozen-scene 几何/task-goal PASS，不证明低摩擦 robustness；half-speed、reverse、
lateral、yaw 仍为原有 PERFORMANCE_FAIL，其中 yaw 的 corrected metric 见
[erratum](validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md)。这些
RL-only findings 不能直接升格为跨-controller bottleneck，也不能外推到更高台阶、
hardware 或 general robustness。0.15 m/s 仍是历史局部兼容性设定，不是全项目目标。

### DIAL / MPPI and other challengers

不预设单一 challenger。Sampling/search 或 contact-implicit 方法只有在统一 benchmark
指出 gradient basin、nonsmooth contact、mode search 或 multimodality 等具体诊断问题
时，才按任务决定是否启用。

## 6. [CURRENT | SUBSTRATE GATE 0] 当前 Gate

当前 Gate 建立可复用的统一评测与 controller-family failure map；不以预选 MJPC
或发明新 controller 为目标。依赖关系：

`benchmark semantics → mature implementation audit → aligned controller comparisons → failure-mechanism diagnosis → method decision`

阶段边界：
1. 任务化定义共享 model / scenario / reset / metrics / success and safety semantics。
2. #189 已提供第一张 RL map；其 low-friction / yaw 解释按 erratum 修正。
3. 下一步先审计可复用的 Go2 whole-body controller/MJPC implementation、任务和 runner，避免从零重写已有闭环能力。
4. 随后为所选 comparator families 写独立的对齐任务；cost、信息和优化差异均须显式记录。MJPC/iLQG、sampling/search 或 learning family 都不享有先验 truth 地位。
5. 需要大规模 rollout / learning 时再实现 MuJoCo/MJX 扩展，不为“统一外观”提前宣称 GPU substrate 已完成。

Gate 目的不是选“永远唯一 controller”，而是定位可复现 failure，再决定成熟方案、
tuning、部署修正或新 mechanism 哪种解释得到证据支持。任何 live execution 都由其
单独 task 与 SOP 授权；本轮 R0 不启动 experiment.

## 7. [CURRENT | EXECUTION] Repo / host 状态边界

实际工作区、branch/HEAD、dirty 状态和远端关系每次接手重新核验，命令见
[项目推进指南](OPERATING_GUIDE.md)。本文件不维护会过期的“最新 main SHA”或
机器工作分支快照；具体运行的历史 SHA 保留在对应结果中。

首轮 0.15 m/s 平地 RL 移植验收的 FAIL closeout 仍保留；随后 1 m/s shared-transfer 正式组合已两次 PASS。两者回答的是不同冻结条件，不能互相改写。完整 Substrate Gate 0 仍未完成；当前尚不能代表 MJPC/RL/DIAL 地形能力已完成验证.

## 8. [CURRENT | TOPIC STATUS] 选题状态

当前问题保持开放：

> 在统一 MuJoCo/MJX 物理、任务与评测语义下，learning、gradient-based MPC 与 sampling/search controller 分别在哪些 embodied-control 条件下出现稳定 failure；哪些 failure 能被复现、机制化，并确实需要新算法，而非 tuning、部署差异或成熟方案？

旧候选：
- L9 Preview：`HOLD / RE-AUDIT`
- L10 / TimedReach / SEFR / FSEF：`HOLD / RE-AUDIT`
- terrain-aware foothold+swing：legacy mechanism / possible benchmark intervention

Gate 0 前不得从历史候选直接继续造方法。

## 9. [CURRENT | NEXT]

RL shared-transfer 与首轮九例 capability map 已完成封存，不重跑。先审计成熟 Go2
whole-body control implementation 是否已有可复用的闭环 task/controller/runner。完成该
审计后，再定义 MuJoCo 上对齐的 command/terrain comparison：保留平地 reference、
half-speed/reverse/lateral/yaw probes、5 cm/10 cm/repeated-step anchors；low-friction
anchor 在修正后的 v2 scene 上只能由新 task 前瞻授权，不能接续 #189 或由本次
engineering task 自动启动。若需要 scale-up，再评估 MJX。

0.15 m/s 不足、横漂与 23 cm 楼梯 base-contact stop 仍是观察边界，不是论文问题。
Gate 0 前不从历史 L9/L10/FSEF 候选直接造方法；新 mechanism 必须由跨 controller
结果或可证伪的 controller-specific failure 对比支持。

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

## 2026-10-01 | MJPC Ground/IPC engineering hardening

The inherited source-locked Ground repair has passed zero-integration native
regression and zero-canonical-step IPC/torque/reset acceptance, together with
175 substrate tests and style checks. See
[engineering acceptance](validation/mjpc_ground_hardening_v2_20261001/RESULTS.md).
The private invalid-rollout handling is an intervention requiring independent
review; this does not establish trajectory neutrality or controller performance.
v1 remains permanently closed. A separately identified v2 retains the frozen
canonical anchor and awaits exact-head independent reviews and explicit START;
scientific attempts remain 0 and Gate 0 remains incomplete.

### 2026-10-01 | Exact-head review HOLD repaired, not scientifically approved

The 73fae9b independent review held readiness on four runtime/qualification
findings. Those findings were confirmed and repaired with source-bound tests;
see [HOLD repair](validation/mjpc_hold_repair_v2_20261001/RESULTS.md).
The new runtime requires independent exact-head rereview. Canonical steps remain
0 in engineering acceptance; private planning integrates private rollouts.
Scientific attempts remain 0; v1 is closed and live v2 has not started.

### 2026-10-01 | Science campaign-stop HOLD S1 repaired, rereview required

Science review of c0c6e40 held v2 because canonical safety failure did not stop
the whole campaign. The separate execution approval does not override that
HOLD. The bounded repair now seals safety/execution/evidence stops and explicitly
predeclares only horizon metric failure continuation; see
[campaign-stop repair](validation/science_campaign_stop_v2_20261001/RESULTS.md).
200 guarded substrate tests passed with canonical steps 0. Private C++ planning
is a distinct integration surface. Both roles must review the new exact HEAD;
scientific attempts remain 0, Gate 0 incomplete and live v2 NOT_RUN.


2026-10-02 third-stage diagnostic increment: [bounded adapter task](research/TASK_MJPC_ADAPTATION_DIAGNOSTIC_V1_20261002.md) implements separate3s original/corrected scopes. B retains source position-PD and corrects floor registration/effective torque clamp; source mass, damping and deliberate smoothing remain. Rollout and FD upper-bound accounting covers private integration; B requires A verified original prefix/stop reproduction. Formal attempts/canonical steps0 pending new exact-head reviews; qualification optimizer smoke is engineering only. This does not select a topic or start a new method.


## 2026-10-03 | Closed-trace engineering diagnosis

[Offline diagnosis and repairs](validation/mjpc_closed_trace_diagnosis_20261003/RESULTS.md)
correct the stale formal-NOT_RUN pointer: adaptation A consumed its sole
attempt, stopped at tick886 and failed the tick1287 reproduction gate;
B stays NOT_RUN_REPRODUCTION_GATE_FAILED. Live logs first differ at the
second replan, before contact classifications; the hidden trigger is unproven.
Current capture refuses the old identifiers despite a checkout-local empty
ledger. The observer now restores the live reset and production named-joint
state packing. Previous tick10 observer inputs were misordered and cannot
exclude production A configuration/history effects. No new optimizer or
canonical step was run. Existing scientific claims and Stage3 ACTIVE/OPEN
remain unchanged. R4's saturation-repeat failure and no12s capture are retained.
