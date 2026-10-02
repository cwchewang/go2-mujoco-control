# Stage-three terrain and command admission notes

This supplements the [source-bound MJPC diagnosis](../validation/stage3_topic_diagnosis_20261002/RESULTS.md).
No additional physical experiment or runtime modification is performed.

## Terrain evidence must have valid support semantics

[episode.py](../../tools/substrate/episode.py) snapshot92--101 recognizes support
only for feet contacting the one phase2_floor geom. Active foot contact with
another geom is forbidden. Therefore adding a step XML to the current flat
runner would manufacture nonfoot/safety classifications even for valid foot-step
support. A terrain task must prospectively define allowed support geom identities,
actual effective contact/exposure and forbidden-body contact semantics, with a
source-bound evaluator check. Do not patch the old campaign or reuse its flat
classification as a terrain capability result.

Existing sealed RL5cm/10cm/repeated-step results remain bounded leads. The current
MJPC flat safety-stop raw is not terrain failure evidence. Stage-three topic
selection requires admissible capability/failure evidence and a falsifiable
question; substrate repair alone does not satisfy that criterion.

## Unsupported commands are not capability failures

[native/controller.cc](../../tools/substrate/native/controller.cc) rejects
nonzero lateral command and negative forward speed before action. A rejected
command is UNSUPPORTED under this source task, not a scientific capability FAIL.
RL command-space results remain testable within that policy's own interface,
but cannot automatically be ranked against this MJPC task on lateral/reverse
conditions. Any expanded command interface needs its own declared semantics.

## Derivative/contact settings already present

Pinned MJPC e00c47a5adb9856af2e0f24231bb3a60d5be23c4 has
mjpc/planners/ilqg/settings.h defaults fd_tolerance1e-6 and fd_mode0
(one-sided); planner.h/planner.cc default derivative_skip0.
Both compiled XML models already use elliptic cone and impratio100.
Changing to one-sided finite differences or adding impratio100 is therefore
not a new repair. Derivative skipping, TV-LQR, soft gait prior and joint-PD
prediction are established upstream mechanisms, not novelty claims.

The new read-only diagnosis establishes adaptation/model confounds and a
prediction-evidence gap; it does not establish the RR_calf causal mechanism.
Proceed to a bounded configuration/evidence admission decision before any
separate diagnostic capture. Keep terrain question formation active in
parallel, using mature references and explicit falsifiers rather than waiting
for unlimited MJPC engineering repair.
