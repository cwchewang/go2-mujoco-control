# Shared transfer combination: design and implementation closeout

## Decision and prospective design

The sealed ten-case source baseline already proves that source-condition
1.0 m/s flat tracking passes and repeats exactly, the shared adapter preserves
the source trajectory, and the shared model-only and shared-home-only cases
each pass. It does not prove that the shared model, shared home, source-aligned
ten-step startup, and shared `FrozenPolicy` adapter pass together. This is the
minimal next comparison: the source reference and single-factor controls are
already sealed, so the new campaign contains only the complete combination and
one exact repeat.

The question is whether that complete combination preserves the frozen source
1.0 m/s flat capability. The falsifier is a performance failure, safety stop,
or failure to reproduce the exact same-condition trace in either episode. A
performance FAIL establishes failure of at least one predeclared gate for this
deployment; a safety stop or integrity stop bounds the result and does not
become a performance verdict. A PASS establishes only that this setup met the
gates in two identical deterministic episodes. Neither outcome identifies a
single causal factor, estimates statistical success probability, establishes
low-speed/terrain/hardware transfer, generalizes to another checkpoint, or
explains the sealed low-speed failure.

Both cases freeze the same shared flat model, shared home reset, ten 2 ms PD
startup steps before first inference at tick 10, shared `FrozenPolicy` adapter,
pinned public source/checkpoint, and constant 1.0 m/s forward command. Duration
is 12 s and measurement is ticks `[1000, 6000)`. Gates reuse the source baseline:
mean forward speed `>= 0.8 m/s`, MAE `<= 0.2 m/s`, lateral drift `<= 0.3 m`,
and absolute yaw change `<= 0.3 rad`. Existing safety/contact rules are frozen:
nonfinite/invalid orientation/warning, any base-terrain contact, tilt `> 1.2`
rad, clearance `< 0.06` m, or lateral position `> 1.5` m stops the episode;
foot-ground contact remains allowed. Two total attempts are authorized by the
future protocol, with exact trace equality and first-nonpass stop. No threshold
was selected from a new outcome.

Relative to the sealed source reference, the shared model, shared home/reset,
and shared adapter are changed together. The source-aligned ten-step startup,
checkpoint/source identity, flat task and 1.0 m/s command, duration, measurement
window, deterministic settings, gates, and safety semantics are held fixed.

## Implementation

- Added `tools/substrate/protocols/rl_shared_transfer_combination_v1.json` and
  `tools/substrate/tasks/rl_shared_transfer_combination_v1.json`; neither
  sealed v1 protocol or ledger is reused.
- Updated `tools/substrate/baseline.py` for explicit task selection, source and
  checkpoint lock validation, declared repeat matching, and first-nonpass
  progression. Updated `tools/substrate/baseline_episode.py` and
  `tools/substrate/baseline_verify.py` for generic repeat/gate/stop semantics.
- Added focused regression coverage in `tools/substrate/test_baseline.py` for
  protocol identity, source-lock binding, progression, repeat matching,
  reference gates, and synthetic startup cadence.
- Added the prospective protocol description at
  `docs/research/SHARED_TRANSFER_COMBINATION_V1.md` and this closeout at
  `docs/validation/shared_transfer_combination_design_20260923/RESULTS.md`.

## Checks and evidence boundary

`python3 -m unittest tools.substrate.test_baseline.BaselineContractTests -v`
passed all 16 contract tests. Coverage includes the frozen combination
configuration, source-lock binding, synthetic startup cadence, metric gate,
declared repeat comparison, and first-nonpass accounting. The startup test uses
`FakePlant`; no campaign MuJoCo model was loaded or stepped.

`python3 -m tools.check_quality` passed syntax and repository hygiene checks
for 174 tracked source files. `python3 -m tools.research.workspace --check`
passed. `python3 -m tools.substrate.baseline prepare --help` confirms the new
`--task` selector is available without invoking preparation. The protocol SHA
matches the hash bound in its tracked task JSON. Final `git diff --check` and
`git status --porcelain` are run at closeout; the intended changes remain in
the worktree for the trusted wrapper.

No preparation, capture, formal-start authorization, or campaign MuJoCo step
was invoked. Scientific attempts consumed: **0**. No historical capture, raw
data, or attempt ledger was modified. The optional Ruff style mode was not
available because the pinned `.substrate/dev-venv` is absent and system Python
has no Ruff module; standard repository quality checks passed.

## Next task and remaining uncertainty

Exact next task: **clean-HEAD qualification plus real zero-step preparation
only**, after this implementation result commit is trusted. That task may stop
at `READY_AWAITING_START`. Formal capture remains a separate authorization
boundary. It remains unknown whether the complete combination preserves the
source 1.0 m/s flat capability and whether the observed outcome, if any, is
deterministic across identical episodes; no terrain, low-speed, causal, or
hardware claim follows from this design task.

Implementation base: branch `research/shared-transfer-combination-design-20260923`,
HEAD `ac88062a60514f96a2fdeec884f26ab276e41d47`. The worktree is intentionally
dirty with the prospective protocol, runner/verifier support, tests, and these
closeout documents pending trusted-wrapper validation and commit.
