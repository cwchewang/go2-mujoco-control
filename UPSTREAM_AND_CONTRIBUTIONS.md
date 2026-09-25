# Upstream and research contributions

This repository combines the Unitree MuJoCo simulator with a shared research
substrate and retained C++ control/experiment code. CURRENT and PROJECT_RECORD
identify the active task and scientific status.

## Upstream components

| Component | Upstream | Role here |
|---|---|---|
| Unitree Go2 MuJoCo simulator | Unitree Robotics `unitree_mujoco` | simulator base |
| Unitree SDK2 / DDS | Unitree Robotics | runtime dependency |
| MuJoCo | DeepMind | physics; 3.3.6 in the research environment |
| Robot/URDF assets | Unitree | this checkout vendors Go2 only; H1/G1/B2/… remain upstream |
| MJPC / iLQG | pinned MuJoCo MPC Go2 source | unchanged optimizer compiled for static admission |
| Public CTS policy | pinned wty-yy/go2_rl_gym source and checkpoint | CPU inference behind shared named state/action contracts |

Exact source commits, checkpoint identity and source URLs are locked in
[`tools/substrate/sources.lock.json`](tools/substrate/sources.lock.json).
Python versions/wheel hashes and native build identity are documented in the
[substrate guide](tools/substrate/README.md). These dependencies keep their own
licenses; the root license does not relicense externally downloaded code/weights.

Isaac Lab / RSL-RL velocity RL is maintained in the companion repository
[`cwchewang/go2-isaaclab-rl`](https://github.com/cwchewang/go2-isaaclab-rl).
Genesis / Kine2Go imitation is maintained in a separate companion repository.

Original Unitree READMEs: `docs/upstream/`. The repository root README is the research-project README (avoids case-only collisions with `readme.md`).

## Research contributions in this repository

- stand/walk/lie sequencing and 500 Hz low-level control experiments;
- diagonal-trot gait generation and Raibert planning;
- world/support feedback and simulation instrumentation;
- constrained contact-force/wrench allocation;
- `--wbc-full` 18-DoF inverse-dynamics WBC and receding-horizon SRBD MPC; `--wbc-primary` remains incremental feedforward with guarded fallback;
- controlled experiment runners and retained evidence.

Historical `--wbc-full` cruise records report about 0.12–0.15 m/s on their exact
configurations. They do not establish current substrate performance. The retained
`--wbc-full` implementation is an 18-DoF inverse-dynamics WBC.

## Licensing and citation

Root `LICENSE` is BSD 3-Clause from Unitree, with the upstream copyright notice preserved. Cite upstream work separately from the research extensions.
