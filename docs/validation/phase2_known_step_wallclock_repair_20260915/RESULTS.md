# Phase2 known-step wall-clock repair closeout

Date: 2026-09-15
Branch: research/phase2-known-step-wallclock-repair-20260915
Parent closeout: 9a3611e5e64150c45241cee92514d38ea6732857
Runtime HEAD: df5d7663adc9e96d153107e071d7b49676bcdad6

## Classification

BASELINE_GATE_FAILED

The repaired A baseline was not healthy before the preregistered pre-step
gate. B was therefore not authorized and was not launched. This checkpoint
does not claim that the wall-clock omission was proven to cause the previous
failure; the new run is evidence for the isolated startup-clock repair only.

## Launch disposition

- One preflight invocation stopped before any process launch because the
  expected controller binary was missing. It created an empty A directory;
  that exact empty residue was removed, with no raw capture produced.
- A was then launched exactly once with DDS domain 231 and produced raw
  evidence. The controller stopped on hard posture safety.
- B/domain 232 launch count: zero. No retry, replacement domain, or extra
  experiment was performed.
- The previous raw run root was not deleted, overwritten, renamed, or reused.

## A gate

| Gate | Result | Evidence |
|---|---|---|
| Lockstep transport | PASS | 4,879 rows, 2 ms, zero protocol violations |
| Paired HighState | PASS | 4,879 cycles, zero validation failures, zero async fallbacks |
| A adapter disabled | PASS | known-step active samples = 0 |
| Statuses zero | FAIL | safety_status=1, completion_status=1 |
| No hard safety | FAIL | hard posture limit and EMERGENCY_STOP markers |
| Healthy active locomotion to pre-step | FAIL | analyzer healthy-gate rows = 0; raw max base x=0.620934 m |
| Solver health | FAIL | valid solver rows = 0 in the gate window |
| Source/provenance | PASS | HEAD=df5d7663..., dirty=false, expected HEAD matched |

The raw capture ended with world_base_x_m=0.578118 m. The raw peak briefly
reached 0.620934 m, but no row satisfied the analyzer's healthy active
locomotion gate, so this does not pass the preregistered 0.60 m condition.

## Wall-clock repair audit

The A manifest and metadata contain --wall-clock-motion once, and the
repair runner contains it once. The lockstep handoff captured
pre_motion_steps=4000 at sim tick 8000. The diagnostic rows retain
motion_clock_wall_mode=1 and have positive wall-clock deltas on 4,878 of
4,879 rows. After the handoff, all 4,878 state intervals were exactly 2 ms,
all 4,878 motion_dt_s values were 0.002 s, and there were zero state-tick
delta violations. This is consistent with wall-clock startup selection and
state-synchronous motion after handoff; it is not a causal proof of the
previous failure mechanism.

## Frozen provenance and tests

- Previous failed runtime HEAD: 89658121e002c9f95f47ee8d09ec83cd41f17845.
- Previous failure: no active locomotion rows, hard safety before the step,
  and B not run.
- Controller Release CTest: 31/31 PASS.
- Focused adapter and motion-clock integration tests: PASS.
- Simulator test_lockstep and simulator CTest: 2/2 PASS.
- Scene, simulator, controller, runner, analyzer, and raw-capture hashes
  are recorded in provenance.csv.

After this closeout is pushed, stop. No 10 cm step, perception, D4,
speed-increase, repair, or other terrain checkpoint is authorized here.
