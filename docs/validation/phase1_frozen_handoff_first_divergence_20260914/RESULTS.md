# Phase 1 frozen-handoff first-divergence — 2026-09-14

## Conclusion

Classification: `SIMULATOR_DIVERGENCE`.

All three preregistered runs reached the frozen READY handoff at simulation tick 8000 with identical headers and bitwise-identical first integration-state bytes. In all three pairwise comparisons, the pre-step integration state, command sequence, full LowCmd tuple, bridge sensor q/dq, bridge-computed ctrl, actual `mjData.ctrl`, contact metadata, bridge step index, and post-step qacc remained equal at the detector record. The earliest observed difference was the next captured integration state, so the first supported boundary is simulator integration/contact-constraint evolution, not controller or bridge output.

This localizes the first divergence; it does not identify the underlying MuJoCo/contact/solver mechanism and does not authorize a repair or D4 run.

| pair | detector record / tick | first differing next state | field | value in run A | delta B-A | classification |
|---|---:|---:|---|---:|---:|---|
| L1-L2 | 2150 / 12300 ms | 2151 / 12302 ms | `state[56]@byte448` | -0.7763282246604041 | -2.432071379843137e-06 | `SIMULATOR_DIVERGENCE` |
| L1-L3 | 2150 / 12300 ms | 2151 / 12302 ms | `state[56]@byte448` | -0.7763282246604041 | -2.432071379843137e-06 | `SIMULATOR_DIVERGENCE` |
| L2-L3 | 2151 / 12302 ms | 2152 / 12304 ms | `state[56]@byte450` | -0.7034361128596134 | 1.816079020500183e-08 | `SIMULATOR_DIVERGENCE` |

The machine-readable pairwise output is `first_divergence.csv`. Its `record_index` and `time_ms` identify the equal pre-step detector record; `category=next_state` identifies the following captured state as the first differing state.

## Protocol and handoff gates

- Branch: `research/phase1-frozen-handoff-first-divergence-20260914`
- Pre-run/runtime source SHA: `d3e7b5b00ff214b6754a02de1dacf60dc73f6a8a`
- Frozen handoff: `sim_tick_ms=8000`, `sim_time_s=7.999999999999341`
- Snapshot header: GO2PDSNP v2, MuJoCo version 336, `mjtNum=8`, state size 194, `nq=19`, `nv=18`, `nu=12`, timestep 0.002 s, capture window [7.999, 13.0]
- First snapshot record: tick 8000 in L1/L2/L3; first-state SHA-256 is identical: `809728a3bd2f044b5c548dfd5eca8a6068d9790746d5f7d55bb508a2e1c2f1e9`
- Records: 2500 per run; each raw snapshot is 6,240,068 bytes.
- Lockstep: 43,554 trace rows per run, `violations=0`, `fail_closed=0`, `controller_ready=1`, `ready_tick=8000`, `first_post_step_tick=8002`, `dt_ms=2`, and zero pre-first-exact-command steps.
- Stage B: not authorized; Stage A established `SIMULATOR_DIVERGENCE`.

## Provenance

The exact runner and comparator were used without source changes. D4 and all causal A/B flags were off. Runs were sequential, domains 201/202/203, CPU affinity simulator/controller 2/3, headless, controller duration 86 s, wall timeout 140 s. The full launch configuration is preserved in each run directory under `run_metadata.txt` and `environment.txt`.

| artifact | SHA-256 |
|---|---|
| simulator binary | `f17f5561cb37c9ca8fd38733dec954360cd00d43e324ff186c2456b897c73741` |
| controller binary | `9836f944bf86426eac933a5233d7bc66516efb807de6cfa0e56a6ed6553f3ec3` |
| scene | `12286418247d0e240ae131b5ae5c60f3a7a481d4754aefe4517476e937aa05b8` |
| profile | `9efcc3b2d89fb349a12990ace1cf6ceb45e0d731deb470bdf2af084d82449d74` |
| MuJoCo `libmujoco.so` | `b9173509d0c282a9b24b7f5825a40177a9967df0cd6395a9dc39522196e44495` |
| runner script | `25438fac0b58d1e733dee2c7f6540fa84270cf6cec6f88a2a40439ee434cf8d5` |
| comparator script | `17a326ea1fa1992a8a5a37bf4a26320c292972bd3ed53e648f7787cc41f94ab9` |

See `run_provenance.csv` for per-run paths and raw snapshot hashes. Raw binaries remain local and are not committed.

## Recommended next checkpoint

Authorize a separate, narrower simulator-side determinism checkpoint for MuJoCo/contact/solver ordering at the localized tick. It was not executed here.
