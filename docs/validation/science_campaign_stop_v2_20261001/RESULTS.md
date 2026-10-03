# Go2 v2 science HOLD S1: campaign stop repair

Status: PRECHECK PASS / NEW EXACT-HEAD SCIENCE AND EXECUTION REVIEWS REQUIRED.
Reviewed parent: c0c6e40f268d869804114edd5729d8586a71e437.
The authentic science HOLD and distinct execution approval on that parent are
retained with source thread IDs and persistence times. Execution approval does
not override science HOLD. Neither receipt approves the repaired new HEAD.

## Repair

Any CanonicalEvaluator first_failure stops and seals the entire campaign as
SAFETY_STOP. The terminal raw row, replay, classified analysis and consumed
claim remain. The owned controller closes before classification. Later arms
stay NOT_RUN, without plant/controller creation, raw file or attempt claim.
The durable campaign claim prevents retry after safety or any execution/evidence
failure, including tick-zero failure before an arm attempt is consumed.

Only an explicitly predeclared complete-horizon progress/vx-MAE failure with no
canonical failure is PERFORMANCE_FAIL and may continue in v2. This prospective
policy is frozen in the v2 protocol and requires scientific review before live.
Unannounced performance failure stops. Missing/incomplete or inconsistent replay,
IPC/solver, timeout, identity, evidence-write and close errors stop the campaign
and preserve available partial raw data, claims, failure artifact and manifest.
Durable attempt reservation is counted immediately, including failure to write
its in-run claim copy. It is never converted into performance failure.

Nonfinite state components in a safety terminal row are recorded as JSON null
at the same positions. Replay converts them to nonfinite floating values and
retains the same nonfinite first_failure; finite components are unchanged.
This prevents strict JSON serialization from losing the raw safety terminal.

The 300 s bound is per-arm episode execution, not an entire-campaign deadline;
setup/replay/cleanup are outside that episode deadline. The existing 10 s startup
and 30 s native request watchdogs remain infrastructure limits, not real-time
proof. Canonical model, reset, action resolution, timing, thresholds and controller
implementations are unchanged by this repair.

## Evidence and limits

200 complete substrate tests PASS under zero_step_guard, which forbids Python
canonical mj_step/mj_step1/mj_step2 integration. Eleven new campaign regression
tests use FakePlant and mock controllers only. They cover every frozen stop_on
(nonfinite, orientation, physics_warning, nonfoot_contact, posture, lateral),
initial safety stop, later arm/claim absence, single durable RL claim and no retry,
both horizon metric failure policies, partial raw/claim preservation, replay/
storage/owned-close errors and identity failure before first or second plant.
FakePlant step counters are synthetic counters, not canonical physics steps.
Full style passes for 195 tracked source files.

Canonical physics steps=0; scientific attempts=0; live v2 NOT_RUN; v1 remains
permanently closed. The Python guard does not intercept C++ controller-private
planning rollouts. Earlier native smoke on the parent did integrate private
planning; its prior evidence is not new canonical integration or a neutrality
proof. No controller ranking, upstream equivalence, real-time result or scientific
Gate 0 approval is claimed. Failed/intermediate checks remain in the raw root.

After this source/evidence commit, create and verify a clean qualification and
qualification-bound v2 preparation on the exact new HEAD. Their post-commit
identities belong to the raw exact_head_review_packet.json, not an inherited
review receipt. Require new independent science and execution reviews, fresh
preflight and user START before live.
