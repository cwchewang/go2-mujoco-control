# Shared campaign execution HOLD: engineering fix for re-review

Status: PRECHECK PASS; independent execution re-review pending. NOT LIVE READY.
Producer branch: research/shared-baseline-probes-prep-20261002.
Parent implementation HEAD: e87e7d3d8e34731e417f8b116e63627fef2038b8.
Regression producer: that checkout plus the owned HOLD fix.
No qualification, preparation, private optimizer or live capture was started.

## Change and enforced evidence

Before the first challenge, both controller baseline pairs are reconstructed
from raw traces. A new exclusive baseline-eligibility.json freezes each raw
SHA, replay classification and repeat comparison. Every eligible challenge claim
binds that frozen snapshot SHA and its paired repeat's baseline raw SHA.
The runner checks frozen hashes before constructing the challenge plant and
again at claim consumption. Changing a frozen raw reference stops the campaign
before a new challenge claim.

The offline verifier independently recomputes both own-baseline classifications
and repeatability. It validates the frozen snapshot and claim references, exact
eligible/ineligible skip reasons and whole-campaign stop order. Any executed arm
after a stop is rejected. Every started arm requires its analysis, matching
analysis copy and raw SHA; missing or partial analysis cannot produce VERIFIED.
Raw replay also checks frame/step/terminal accounting and classification.
A failed execution artifact may remain preserved and intentionally unverifiable.

## Validation

All248 substrate regressions passed:0 failures,0 errors. The suite contains32
campaign/evidence tests, including10 new HOLD regressions. Added rejection cases
cover failed and nonrepeatable own baselines entering challenges, post-stop
execution, raw SHA drift, missing analysis/copy, matching-but-forged reference
claim copies, forged eligibility snapshots, incorrect skip reasons and false
campaign completion. Existing safety, eligibility and unexposed-horizon cases
are retained. Snapshot/reference bindings and stopping before a challenge plant
or claim are also checked.

The continuous experiment lock and guards on mj_step, mj_step1 and mj_step2
were held for the suite. Real canonical integration steps0, private planning
calls0 and scientific attempts0. Mutation/resealing applies only to temporary
FakePlant fixtures; saved raw campaigns and old curated evidence were untouched.

## Remaining gates

This packet is for execution re-review and does not grant start authority.
Clean qualification, final exact-head preparation, required independent reviews,
delegation binding and fresh preflight remain pending. Qualification is explicitly
closed for this work; its eventual static optimizer would perform real private
rollouts with an uninstrumented integration count. V1/v2 remain sealed.
