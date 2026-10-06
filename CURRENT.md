# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `research/mjpc-floor-registration-12s-20261003`.
Task: [Go2 主底座已选：先复现作者原生 MoE-CTS 能力](docs/research/TASK_PROJECT_FOCUS_RESET_20261004.md).
Closeout: [Go2 主底座已选：先复现作者原生 MoE-CTS 能力](docs/PROJECT_RECORD.md).
Stage: Stage 3 ACTIVE / OPEN；来源比较与主底座选型完成；MoE-CTS 原生 MuJoCo 工程复现 PASS；科学/能力 qualification 待完成；具体科研问题尚未锁定；旧 MJPC adapter 扩展 PARKED / CONDITIONAL.
Scientific status: MoE-CTS 原生 MuJoCo 工程复现 PASS：固定 horizon 的 flat 3.0s / x=2.5150989028m / mean vx=0.8391199433，stairs 7.0s / x=6.0629091387m / mean vx=0.8735359818，stairs_and_slope 10.0s / x=7.2067317885m / mean vx=0.7822757093；三条运行均无 runtime 或 numerical error。该结果是 deterministic engineering smoke only，不构成 success-rate、robustness、controller-ranking 或 research-gap claim；科学/能力 qualification 仍待完成。Logical 四槽闭环已完成（4 attempts / 6000 canonical），其重复性改善不代表有用行走资格。下午独立 checkout 的 H36 满速窗 mean body-vx 0.344924 m/s；H56 在测量窗前因私有 warning 与记账门槛停止，配对比较 CENSORED_OR_INCOMPLETE。旧预算全部保持 CLOSED，本次新增科学尝试、optimizer、训练与物理积分均 0。原始数据与用户既有未提交结果保留；独立分支结果尚未自动进入 main.
Last live HEAD: `3bda7e45724258902aa380e2489432ee6598e739`.
Next: 在工程复现 PASS 后，先做 bounded multi-condition/multi-seed capability measurement plus perturbation/failure mapping，再选择 research mechanism；不把本次 smoke 解读为 success rate、robustness、controller ranking 或 research gap。当前 WSL 16GB 内存限额低于 IsaacLab 32GB 要求，训练资源另行解决；DIAL 为需要时使用的异范式对照，PGTT 为 heightmap/phase 任务备选。本轮只完成既有证据的 canonical 集成，无新运行、训练或合并发布动作.

**Related bounded diagnostic:** [已有 RL 能力图（按勘误解释）](docs/validation/rl_capability_map_successor_20260924/RESULTS.md) — 冻结台阶任务通过，部分命令性能失败；只属于该 checkpoint 与条件，不是算法类别瓶颈或已确定论文 gap.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
