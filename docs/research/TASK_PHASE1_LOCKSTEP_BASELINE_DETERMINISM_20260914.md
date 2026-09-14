# TASK: Phase1 lockstep baseline determinism audit — 2026-09-14

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first.

Starting evidence: checkpoint `df098e01bcff1927b4f8f1d26f53fd0eca177a33` classified the frozen wall-clock Phase1 baseline as `NONREPRODUCIBLE_BASELINE`: three otherwise-identical runs survived, but `[32,33)` median velocity excess spanned `0.038549485 m/s`, above the pre-registered `0.03 m/s` comparability band. No functional RNG exists on this benchmark path.

Mission: create and validate a verification-only lockstep version of the existing Phase1 varying-profile benchmark so future causal A/B tests can run on a lower-noise baseline. Lockstep is for causal attribution/regression only; wall-clock DDS remains the realism/robustness benchmark. Do not test D4.

Use repository `main` at frozen SHA `a3ff3bd6cd1907b79c832cfd4ceb568e5d6bb079` as the protocol authority. Do not invent a new lockstep protocol or resurrect an earlier partial version. The final port must preserve: exact state/LowCmd causal binding; ack bound to exact state and exact command sequence; one controller writer update per strictly-new state tick; duplicate frozen-state republishes cannot cause duplicate control updates; lockstep motion time comes from simulator/state ticks rather than wall time; protocol errors/timeouts fail closed; flag-off wall-clock mode remains logically unchanged.

Allowed: audit and minimal port of verification-only lockstep infrastructure from the frozen main SHA; lockstep trace/metadata/tests; minimal Phase1 lockstep runner; one simulator/controller rebuild; exactly three sequential baseline-only lockstep launches after all static/test gates pass; offline comparison of those runs.

Forbidden: D4 or other stance-dq intervention; controller/gait/WBC/SRBD/ID/contact tuning; profile changes; safety/analyzer weakening; unrelated Phase2/terrain imports; broad architecture refactor; extra runtime launches.

Stage 0 — clean-port feasibility. Compare current branch to frozen main only for lockstep-related code, including `simulate/src/lockstep.h`, relevant parts of `simulate/src/main.cc` and `unitree_sdk2_bridge.h`, lockstep tests, `example/cpp/trot/lockstep_writer_gate.h`, relevant lifecycle/control/header code, and `run_trot.sh`. Produce the exact dependency list. If the final protocol cannot be isolated without unrelated control changes, stop as `BLOCKED_NO_CLEAN_PORT`.

Stage 1 — minimal port. Lockstep defaults OFF. After the lifecycle handoff, physics advances exactly one frozen interval only after the exact current state produces the exact corresponding LowCmd/ack exchange. The controller performs one full writer/control update per strictly-new state tick. Motion time follows state/sim tick progression. Duplicate republishes cannot advance control/gait time. Violations fail closed and are traced. No Phase1 control target, gain, gait parameter, WBC target, q/dq logic, torque logic, safety threshold, or analyzer threshold may change.

Stage 2 — pre-run gates. Build simulator and controller; run relevant lockstep simulator tests; run relevant writer-gate/motion-clock tests; source-audit the flag-off wall-clock path; record exact source SHA and binary SHA256. If any protocol test fails, stop without runtime launches.

Stage 3 — exactly three lockstep baseline varying runs, L1/L2/L3. Keep D4 OFF and the same B-semantic Phase1 configuration, scene, profile, period 0.14, duty 0.44, gains/limits/governor/WBC settings, headless mode, fixed CPUs when applicable, fresh processes, and DDS-domain discipline. Do not run wall-clock comparisons here; `df098e0` is the reference. If the protocol remains valid, physical success/failure is data, so complete all three. If the protocol fails closed or its trace is invalid, stop immediately.

Per-run protocol gates: trace exists; zero violations; no `SIM_LOCKSTEP_FAIL_CLOSED`; exact constant simulator tick increment equal to model timestep; state ack matches the frozen/current published state; command ack resolves to the exact command for that exchange; exactly one full controller writer update per strictly-new state tick after handoff; lockstep motion time follows simulator tick time rather than wall time.

Baseline analysis: align L1/L2/L3 by exact simulator/diagnostic tick. Report active duration/safety, `[32,33)` measured/applied/excess, WBC/SRBD/ID x-acceleration metrics, roll/pitch, contacts, strict analyzer status. Report pairwise exact-tick differences for measured velocity, applied velocity, excess, roll, pitch, controller contact mask, and gait phase. Reuse the previous descriptive divergence locator: forward-velocity difference >0.05 m/s OR roll/pitch difference >2 deg sustained 100 ms.

Classify `READY_FOR_CAUSAL_AB` only if all three: have valid lockstep protocol; reach active-relative >=40 s without hard safety; remain continuous-trot through `[32,33)`; `[32,33)` median velocity-excess range <=0.010 m/s; pairwise p95 absolute velocity-excess difference over common active `[0,40] s` <=0.020 m/s; and no sustained descriptive divergence before 40 s. These are engineering-readiness limits, not physical-robot noise claims.

Other labels: `LOCKSTEP_PROTOCOL_FAIL`, `DETERMINISTIC_CONTROLLER_FAILURE`, `LOCKSTEP_STILL_NONREPRODUCIBLE`, `BLOCKED_NO_CLEAN_PORT`, or `INCONCLUSIVE` if genuinely necessary.

Deliver `docs/validation/phase1_lockstep_baseline_determinism_20260914/RESULTS.md` plus compact run, pairwise, and protocol-gate CSVs. Record hashes/provenance; raw files may remain under `_runs`. Push exactly one result checkpoint and stop.

Required conclusion: Does the verification-only lockstep harness make the current Phase1 baseline deterministic enough for precise causal A/B testing? End with exactly one recommended next step and do not execute it.