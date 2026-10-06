# MoE-CTS native MuJoCo engineering reproduction — 2026-10-05

Status: **PASS (engineering reproduction only)**

Pinned source: `wertyuilife2/go2_rl_robotlab@28b4516d22617b11aeaf8ead63cc00b0c0bcd1bd`
Policy: `go2_moe_cts_176k_0.6984.pt`, SHA-256 `c602e749…d10a2`
Runtime: Python 3.10.12, Torch 2.6.0+cpu, MuJoCo 3.3.6

No author repository file was modified. The external headless runner mirrors the author deployment observation, internal TorchScript history, 2 ms MuJoCo physics, 50 Hz policy update, position-target PD and default 1 m/s command.

| Scene | Horizon | Progress x | Mean body-vx | Last-1s body-vx | Max |roll| | Max |pitch| | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| flat.xml | 3.0s | 2.515m | 0.839m/s | 0.918m/s | 0.068 | 0.065 | horizon |
| stairs.xml | 7.0s | 6.063m | 0.874m/s | 0.907m/s | 0.092 | 0.201 | horizon |
| stairs_and_slope.xml | 10.0s | 7.207m | 0.782m/s | 1.071m/s | 0.184 | 0.609 | horizon |

Interpretation boundary: flat, the first 5 cm stair sequence in `stairs.xml`, and the author default large-stairs-plus-slope scene all execute to their fixed horizons without numerical/runtime failure. The 10 s default scene reaches x=7.207 m, beyond the staircase and onto the ramp. These are deterministic engineering smokes, not success-rate estimates or a scientific comparison.
