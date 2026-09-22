# First formal substrate flat capture — 2026-09-22

Final status: **FAIL / CLOSED**. Attempt 1 completed; attempts 2 and 3 NOT_RUN.
Earliest failed boundary: **scientific**; reason code: **metric_failure**.
Merged parent: `c5582af60b802b688e4e526845402deb33cf29cd` (PR #139).
Exact execution HEAD: `09a9a31e2ab6eefcd4d3193107e8e17dad642129`.
Task: `docs/research/TASK_SUBSTRATE_FIRST_CAPTURE_20260922.md`.
Frozen protocol: `tools/substrate/protocols/rl_flat_v1.json`.

## Result

The pinned public CTS policy completed the entire frozen 10-second flat scenario,
but did not meet either endpoint deployment-compatibility metric. The campaign
stopped after this first nonpass; there were no retries or replacement runs.

| Frozen metric | Observation | Gate | Result |
|---|---:|---:|---|
| Forward displacement | 0.3641241079 m | >=1.0 m | FAIL |
| World vx MAE, ticks 2500–5000 inclusive | 0.1074027971 m/s | <=0.1 m/s | FAIL |
| Safety conditions | No trigger | All ticks safe | Met |
| Attempts 2 and 3 | NOT_RUN | Stop on first nonpass | Met |

The primary window contains 2501 state samples, with mean forward speed
0.0425972029 m/s against the constant 0.15 m/s command. This is a descriptive
recomputation, not a new acceptance rule. Heights ranged from 0.2700 to 0.3691 m,
maximum tilt was 0.05705 rad, and maximum lateral displacement was 0.03686 m.
No warnings, forbidden contacts, nonfinite state or torque saturation occurred.

Exactly 5000 physics steps, 5001 contiguous frames and 500 policy target updates
were recorded. Termination was `horizon`, not a safety stop. The first trace's
`repeatability_matches=true` only initializes the reference; repeatability is
**NOT_EVALUATED**, because the later attempts were correctly skipped.

## Execution and verification

The user instruction was recorded verbatim: “合入主线，然后开正式实验”.
PR #139 was merged before launch. SOP required a new scientific branch; the only
executable delta from merged main was the launcher's reserved branch string.
No protocol, model, checkpoint, controller or analyzer semantics were changed.

Clean-head qualification passed 164 checks: 34 CTest, 77 substrate, 24 preflight
and 29 repository/dispatcher. Hosted portable CI passed at the execution HEAD.
Two independent exact-head reviews approved the task; actual-model preparation
reported zero physics steps. Capture then passed its own locked exact-head SOP
preflight before the first sample.

Independent `verify_capture` recomputed the raw actions, safety, metrics and stop
sequence as VERIFIED / FAIL. Separate offline verification additionally compared
the persistent ledger byte-for-byte against the capture's claim copies: one
campaign, one consumed attempt, no attempts or raw files after the stop. Both
independent reviewers accepted the closeout classification and evidence chain.

Policy inference p50/p95 was 0.291/0.928 ms. Recorded episode wall time was
1.9144 s (simulation/wall ratio 5.2235); total attempt processing, including
post-episode analysis, was 2.8123 s. User/system CPU time was 2.7413/0.0495 s;
process lifetime peak RSS was 715292 KiB. These are observations from one logged
CPU run, not real-time pacing guarantees or backend comparison results.

## Evidence

Raw root: `_runs/substrate_first_capture_20260922/`.
The immutable folders are `qualification_clean_01`, `prepared_01`, `capture_01`,
`analysis_01` and `closeout`; review/start records are preserved alongside them.
The separate ledger is `_runs/substrate_attempts/rl-flat-compatibility-v1/`.
Tracked derived artifacts: `analysis.json` and `provenance.csv` in this directory.

Protocol SHA256: `d8ae529b39207a1fcb4450b163bc0a8b71955513260f0cd6959911705e0d5f35`.
Raw attempt SHA256: `c398a7c6dfffd65c6d9195bcf0fc68c388848af07c67e6e5f8946ed10a87476f`.
Canonical trace SHA256: `1ff68709d354dcd16406285a1090573b369bb83d873a51bd0141aabe1a52d152`.

Archive:
`/home/che/dev/go2-workspace/archive/evidence/substrate_first_capture_20260922/09a9a31e2ab6eefcd4d3193107e8e17dad642129/first-capture.tar.gz`.
Archive SHA256: `e644991e3533f3e1f567bdde29591a9d335705cbbb6995cd9e3090d063fb2a3e`.
All 100 archived files, including the external ledger and analysis scripts, were
reopened and individually hash-verified. Prior raw evidence remains intact.

## Interpretation and next boundary

The deployment-compatibility checkpoint failed its frozen endpoint gates. The
execution and evidence boundaries passed. This one trajectory does not identify
whether policy behavior, model mismatch or adapter/startup differences caused
the low progress; it cannot reject the policy's overall capability. Full Gate 0,
terrain capability, backend comparisons and repeatability remain unestablished.

Next work is offline diagnosis of the preserved trajectory and locked upstream
deployment semantics: initialization, observation scaling, joint mapping,
command/target/PD progression and contact patterns. No threshold adjustment,
additional attempt, alternate scene or causal claim is authorized by this result.
A later live intervention requires its own prospective task and run budget.
