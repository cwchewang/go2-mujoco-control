# Bounded shared campaign runner: minimal engineering handoff

Status: PRECHECK PASS for the guarded implementation regression; NOT LIVE READY.
Producer checkout: research/shared-baseline-probes-prep-20261002, based on
710d374829e555386ee4eb253af1b61a383db4e8 with owned runner edits.
This is not a clean qualification receipt or an independent final review.

## Implemented and checked

The fixed20-arm runner enforces own-baseline eligibility and repeat pairing,
fresh plants/controllers, one durable external claim per consumed attempt,
continuous experiment lock,300s per-arm watchdog and whole-campaign stop.
A tick0 safety failure closes with zero claims/steps; all later NOT_RUN reasons
are closed. No retry, tuning, new scene or v1/v2 rerun is added.

The independent raw verifier reconstructs delivered normalized payload hashes,
source ticks and separate native retimed hashes; verifies actual update/replan
and command clocks, paired unmodified prefixes and actual friction/force exposure.
The cards are sliding friction, controller observation delivery delay, decision
period and external force pulse. Delay affects MJPC planning and2ms feedback.
RL period changes observation consumption, target hold, history and command
sampling; MJPC period changes replan/command sampling with2ms feedback retained.
No equal-information, equivalent-feedback or pure-compute interpretation is made.

Tick3000 safety precedes physical input application. Setting, confirmed exposure
and complete valid horizon are distinct. Unexposed trials never earn robustness
PASS; later arms close NOT_RUN. Only the original operational metric window is
used, without post6s/recovery-time claims.

All238 substrate tests passed under mj_step/mj_step1/mj_step2 guards and the
experiment lock. They include22 new runner/evidence tests. Real canonical
integration steps0; private planning calls0. FakePlant transitions and compiled
model mj_forward with synthetic clocks are explicitly engineering fixtures.

## Preserved failures and remaining gates

First focused50:49 passed, one fixture nested-lock error; corrected focused50
passed. First full238 failed with3 failures/5 errors due synthetic NumPy command
scalars rejected by the JSON evidence checker; corrected full238 passed. Raw
attempts remain immutable under _runs/shared_campaign_runner_prep_20261002.

Clean qualification, final clean preparation, exact-head science/execution
reviews, bound three-stage delegation and fresh preflight remain required.
Qualification intentionally invokes the native static optimizer with real private
21-step rollouts; exact private integration count is uninstrumented. Preparation
will perform zero canonical integration and zero private planning calls.
No live capture or scientific attempt has occurred in this runner work.
