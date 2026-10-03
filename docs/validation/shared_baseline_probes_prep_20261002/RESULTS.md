# Shared baseline/probe candidate preparation

Status: PRECHECK PASS / candidate package for independent review / LIVE NOT READY.

Parent code: ab27185f6c0ee47fdd09fecb367977bf4ab9cfde.
Branch: research/shared-baseline-probes-prep-20261002.
The source identities tested before commit are retained in
[runtime_hashes.json](runtime_hashes.json); tests ran on the explicitly dirty
candidate worktree, not a new clean qualification. The final commit must retain
these exact runtime bytes. A future live runner needs its own clean qualification.

The [task](../../research/TASK_SHARED_BASELINE_PROBES_V1_20261002.md) explains
source/shared-condition differences, operational acceptance, safety, unequal
information/timing, deterministic repeats, condition cards and the budget.
Candidate protocol SHA256:
d5cc8c43c71ae0d82b5f1748bc2bba943727ca7373fa6e69eec7ed40bf6bbaeb.

## Checks actually completed

- All216 substrate tests PASS under experiment_lock and zero_step_guard.
- Focused41 hook/episode/campaign-stop/native-clock/anchor tests PASS.
- The16 new tests cover delayed content and timestamps, native current clock,
  timing cadence/holds, actual compiled contact friction, force interval and
  ownership, cleanup on emit failure, half-open metrics, yaw/body-frame algebra,
  safety/performance separation, malformed raw/commands, repeats and budgets.
- Accepted parent helper versus new default helper: RL and MJPC information/timing
  regimes each produce identical6001 FakePlant rows and terminal results on the
  prospective6000-tick task. These are fake transitions, not replayed dynamics or
  v2 recapture; [comparison evidence](default_fake_neutrality.json) records hashes.
- Static canonical model/reset/physical fingerprint, policy checkpoint and native
  binary/source identity were verified without stepping the evaluation plant.
- Candidate loader validates bound anchor, source contracts, fixed cards and caps.
- V2 raw manifest and all three external ledger records were verified read-only;
  arm claim copies match. [Accepted closeout](../aligned_flat_capture_v2_closeout_20261002/RESULTS.md)
  and its forwarded key science signoff are preserved separately.

Canonical physics steps and new scientific attempts for this preparation:0.
The guard forbids Python-visible mj_step, mj_step1 and mj_step2. Real model checks
use mj_forward only; fake episode steps are explicitly synthetic.
The candidate precheck starts no native controller/planning process.
Full test results and source-bound receipt are retained in this bundle and its
[provenance](provenance.csv); raw evidence was not altered.

Full quality checks passed for198 tracked source files; Ruff checked162 maintained
Python files. Generated CURRENT consistency and staged git diff --check passed.

## Review target and remaining execution boundary

Review the prospective engineering acceptance scale, same-machine1e-9 repeat
criterion, four fixed hypothesis strengths, delay boot seed and native clock
adaptation, current-state PD boundary, and friction/private-model mismatch.
The interface defaults preserve prior behavior; no prior live result is re-run.

The protocol is a candidate freeze, not an approved scientific or execution
design. It self-authorizes no physics. The package has no stage2/3 live CLI and
no newly admitted capture bundle. The next implementation is the minimal specific
campaign runner for claims, fresh controller/plant instances, baseline eligibility,
per-arm watchdog and campaign stops. Qualification, preparation, new exact-head
dual review and fresh preflight follow. Bind the existing three-stage delegation
to the new action/HEAD/protocol/prepared bundle/budget; never reuse v2 START.

No push, merge, deployment, training, tuning or additional physical experiment
was performed. V1/v2 remain permanently closed. Gate0 remains incomplete.
