# Shared campaign protocol identity fix: source re-review handoff

Status: zero-integration regression PASS; NEW EXACT-HEAD DUAL REVIEW REQUIRED.
Producer parent HEAD: afa786312fa842c7bc44bef804e827bf19d888f8 plus owned repair.
Candidate input fingerprint: 8c066c5fe8e817c8a289800cc9d7fe3163982a4a6b42dea1022aa55a1815cd3a. This is not a qualification receipt.
The final science HOLD is preserved in science_hold_received.json; START is prohibited.

## Defect and resulting behavior

The original frozen protocol bytes hash to 76c94c60b98d4dc452ea3c18e2746f6b39990b061e894013462173715e467265; sorted write_new archival
serialization hashes to 42f509301c8d24e94121bddf4e100476c5849d465326ea93959e8e527d2e494d. Equal parsed content does not make byte
identities equal. The previous verifier demanded the archive SHA for a claim
that bound the original protocol SHA, so a normal production capture would fail.

Preparation now preserves original frozen-protocol.json bytes and separately
records protocol_sha256 and capture_plan_sha256. Capture copies both prepared
files byte-for-byte and binds both identities plus the prepared manifest in its
external campaign claim. Startup and offline verification check both byte hashes
and unchanged parsed content. Verification follows the preparation manifest and
its qualification manifest/fingerprint/head, then checks exact-head review,
authorization and campaign claim bindings. No identity check was removed.

## Validation and recovery

All254 substrate tests passed with0 failures/errors under the experiment lock
and mj_step/mj_step1/mj_step2 guards. Six new tests cover real original bytes via
normal preparation serialization into FakePlant capture/verify, swapped identities,
original/archive byte drift, preparation reference tampering, authorization using
the wrong identity and qualification reference tampering after outer rebinding.

The positive regression invokes the real prepare code and static compiled model
forward operations. Qualification validation and native identity are explicit
temporary fixtures; controller inference/planning is forbidden there. The later
32-tick FakePlant campaign is a lifecycle/identity test, not a12s physics trial.
All fixture START records and mutation tests are confined to TemporaryDirectory.
Real canonical integration0, private planning0, qualification invocations0 and
scientific attempts0. The real formal campaign ledger remains absent.

The previous tool transport error did not establish non-execution. Reconnection
found the complete immutable PASS log and summary, so no suite or physical work
was relaunched. Original raw evidence and sealed qualification/preparation
manifests remain unchanged.

## New version gates

The prior qualification/prepared receipts belong to the prior runtime and are
retained as historical evidence. They do not admit this modified source. Fresh
versioned qualification and preparation plus exact-head independent science and
execution reviews are required. A future qualification retains exactly one
frozen static native admission per new version, with120s native timeout,
canonical0 and no locomotion. Real private optimizer rollout integration is
expected;21 is its trajectory horizon, and total private steps remain uncounted.
A failed invocation is preserved and stops without retry/tuning. No new native
admission, actual preparation or live START was issued for this repair package.
