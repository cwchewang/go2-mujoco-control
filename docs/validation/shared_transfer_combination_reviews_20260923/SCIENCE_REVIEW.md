# Independent science review: shared transfer combination v1

Reviewer identity: `gpt6-luna-max-science-review`
Target HEAD: `b882a5d775ffe01e2cfae6da13c68a040d1ed7b4`
Verdict: **APPROVED**

## Evidence reviewed

- Target protocol and task binding: [`SHARED_TRANSFER_COMBINATION_V1.md`](../../research/SHARED_TRANSFER_COMBINATION_V1.md), [`rl_shared_transfer_combination_v1.json`](../../../tools/substrate/protocols/rl_shared_transfer_combination_v1.json), and [`rl_shared_transfer_combination_v1.json`](../../../tools/substrate/tasks/rl_shared_transfer_combination_v1.json).
- Implementation diff from `ac88062a60514f96a2fdeec884f26ab276e41d47` to the target HEAD, including the generic case gate, repeat comparison, and first-nonpass progression handling.
- Sealed source evidence: [`rl_baseline_20260923/RESULTS.md`](../rl_baseline_20260923/RESULTS.md) and `analysis.json`, plus the source protocol and task. The source 1.0 m/s case, exact repeat, and shared adapter case passed; the source trace SHA was `e9ac1645cf6be7684cb4e4522d7fd0e0ff976f24da23f917b9def2fef24dc441`. The isolated shared-home case passed at 0.937649 m/s mean forward speed, and the isolated shared-model case passed at 0.886330 m/s.
- Canonical `origin/main` PROJECT_RECORD, TOPIC_AUDIT, and Research Execution SOP; and the target HEAD's [`#148 design closeout`](../shared_transfer_combination_design_20260923/RESULTS.md).

## Review reasoning

The decision is whether the pinned 1.0 m/s flat reference remains usable when
deployed with the Praxis shared model, shared home/reset, and shared
`FrozenPolicy` adapter together. The sealed source campaign already supplies
the source reference and the adapter-, home-, and model-only evidence. Those
single-factor passes do not establish that their combination passes, as the
canonical PROJECT_RECORD explicitly states. Testing the complete combination
is therefore the smallest direct test of the stated package-level question;
adding the already established source arm would spend an attempt without
isolating the still-untested interaction.

Against the source reference, the declared changes are the shared model/flat
scene, shared home/reset, and shared adapter. The source-aligned ten-step PD
startup, pinned source commit and checkpoint, flat forward task, 1.0 m/s
command, 12 s horizon, measurement window, deterministic settings, gates, and
safety semantics are held fixed. The machine-readable protocol binds two cases
to the same scene, reset, adapter, seed, inference cadence, and command; the
second is explicitly a repeat of the first and requires it to pass.

The prospective gates match the sealed source 1.0 m/s gates: mean forward speed
at least 0.8 m/s, MAE at most 0.2 m/s, lateral drift at most 0.3 m, and absolute
yaw change at most 0.3 rad. The protocol also retains the established safety
stops, allows foot-ground contact, sets a two-attempt budget, disables retries,
and stops on the first non-pass. These thresholds are inherited from the
declared source reference, not chosen from a new outcome. The first-nonpass
semantics correctly preserve a performance failure as an outcome while
preventing a later repeat from being run after a non-pass.

No hidden confound makes this design unable to answer its stated question. A
pass means this exact combined deployment met the frozen gates in two
same-condition episodes; a performance failure means it missed at least one
gate in this setup. Safety or repeat-integrity stops appropriately limit the
verdict. The result cannot attribute an outcome to one component of the bundle,
estimate a success probability, establish transfer to another speed, terrain,
checkpoint, or hardware, or explain the prior low-speed failure. Those limits
are explicit and fit the package-level decision. The exact-trace repeat checks
repeatability under the pinned deterministic setup; it is not an independent
statistical replicate.

## Non-blocking caveat

The shared-model intervention uses the Praxis flat scene/model binding as a
bundle. If the combination fails, this review does not support attributing that
failure separately to robot-model details, scene details, reset, or adapter.
That attribution is outside the stated deployment-combination decision.

## Execution boundary

This review authorizes only progression of this exact target HEAD to execution
review and zero-step readiness. It does not authorize formal capture.

Scientific attempts: **0**
Physics steps: **0**
