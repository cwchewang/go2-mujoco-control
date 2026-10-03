# Shared campaign fresh-preflight wiring repair

The accepted 0402009534a6b91040327659c704d1f3768d1e08 worker entered the
official fresh preflight at 2026-10-02T07:39:27.845972+00:00 and stopped at
07:39:35.890852+00:00 with exit code 2. It created no capture directory,
scientific claim, arm, or canonical dynamics sample. The old worker is stopped
with no_retry=true. Its original artifacts remain immutable.

The actual failure was not authorization, DDS, argparse, or the frozen protocol.
tools/substrate/shared_campaign.py lacked the explicit
TRANSPORT = "inprocess" declaration checked by reviewed_inprocess_runner.
That initial hard failure skipped qualification.validate. With no duplicate
--test command and no validated receipt, changed_surface_has_no_live_test then
failed for the changed runtime/schema surfaces. The latter was a downstream
failure, not evidence that the previously sealed qualification had failed.

The production change adds only that transport declaration. Preflight checks,
qualification validation, exact-head review, inherited lock, protocol,
controller, model, budgets, scientific thresholds, and capture semantics are
unchanged. No failure record was converted to PASS.

## Why the earlier checks missed the launch wiring

The previous 254 substrate regressions exercised FakePlant capture and evidence
identity, but test_shared_campaign.fixture replaced _fresh_preflight wholesale.
The existing preflight integration suite inspected the actual baseline.py
runner declaration, not shared_campaign.py. Passing those tests and the two
exact-head reviews therefore supplied no executed evidence for the campaign's
real fresh-preflight entry. The deterministic project-owner precheck should have
covered that entry before review; the new regression closes that omission.
Review outcomes are historical approvals, not a claim that the old launch passed.

## New regression and evidence

Four FreshPreflightTests use the actual campaign _fresh_preflight, launch.preflight,
run_logged, and child preflight.main. Only the synthetic qualification validator
boundary and fixed global lock pathname are isolated in temporary fixtures.
The child uses the same inherited descriptor for a real fixture flock. The tests
confirm that the parent's lock remains held on both success and failure. A
sentinel runner raises if executed, and zero_step_guard covers the child and
the whole regression. Fixtures are explicitly labelled and are not launch
authorization or real qualification receipts.

The four cases cover receipt-backed admission without duplicate tests, removal
of the declaration reproducing both original failures and skipping validation,
invalid qualification rejection, and wrong exact-head review rejection before
child launch. No capture or attempt ledger is created in any case.

Confirmed pre-fix reproduction:
_runs/shared_campaign_runner_prep_20261002/fresh_preflight_red_final_20261002T081130362226Z
(manifest 3c267cb09581ac15061bcca9fd32fa3cca7693119e89f705cd035af3e6fb4d98).

Final regression:
_runs/shared_campaign_runner_prep_20261002/fresh_preflight_full_regression_20261002T081240334642Z
(manifest 8b85b8cfdd101dafbb7f9ff1f34bfb4ab3fc568eb61dbd5aa2347fda58547cca).
258 substrate plus36 preflight tests passed (294 total), with quality/style
and git diff checks passing. Canonical physics steps, private planning calls,
and scientific attempts were0. These are engineering checks, not capability evidence.

Earlier fresh_preflight_red*, fresh_preflight_red_confirmed*, and the first
fresh_preflight_green* artifacts include initial fixture/driver errors
(unchanged empty fixture commit, report collection after fixture cleanup, and
a missing test-local import). They are retained as failed development records,
not counted as successful regression evidence. The confirmed pre-fix and final
regression paths above are the authoritative reproduction and fix checks.

## Version and continuation boundary

The complete implementation/test fingerprint changes, so the old040 receipt
and preparation are historical-only for this repaired source. A new clean
qualification and preparation are required. The official bounded qualifier may
perform one native static admission with real private optimizer rollouts;
canonical dynamics remain0 and private total step count is not instrumented.

The precise repair HEAD, source hashes, failure-audit hashes, new fingerprint,
qualification/preparation references, and precheck status are recorded in the
append-only external review packet. New independent reviews must bind that
exact HEAD before a new authorized capture. Do not restart the old job, reuse
its authorization binding, rerun sealed v1/v2, or replace any consumed arm.

See [the bounded task](../../research/TASK_SHARED_BASELINE_PROBES_V1_20261002.md)
and [SOP](../../research/SOP.md) for the unchanged scientific plan and gates.
