# Exact-head HOLD repair: Go2 v2 native boundary

Status: PRECHECK PASS / INDEPENDENT REREVIEW REQUIRED / LIVE V2 NOT_RUN.
Parent reviewed HEAD: 73fae9beb73ada145410e62c8db86674271992e5 (HOLD).
This record supersedes its readiness claim, not sealed v1 results.

Four findings were confirmed and repaired:
1. Native stderr is continuously drained in 4096-byte reads to an exclusive persistent log. In-memory diagnostics keep at most 16 chunks; JSON frames are limited to 64 KiB and requests to 4096 bytes. Startup deadline is 10 s; per-request write+response watchdog is 30 s. These are infrastructure watchdogs, not realtime/solver-performance claims. Bad frames/timeouts close and reap the owned process group, including startup validation failure; streams/readers close. Native capture retains the complete per-arm stderr log.
2. Before each replan all candidate flags are invalidated. Success requires an actual current valid rollout and published policy with the current initial state/time, finite return and no failure. Old upstream fallback is rejected. Ready/response metadata makes this explicit; Python requires reset after a failed step.
3. Identity binds generated/compiled translation-unit bytes, pre-build compiler-discovered native header bytes and actual post-build Ninja dependency bytes. Existing dependency bytes must remain stable during build; newly discovered dependencies are sealed afterward. Cache changes are revalidated during admission.
4. Capture preparation requires a verified clean non-development qualification receipt and stores its full reference. Startup and each arm revalidate that receipt's manifest, producer HEAD and applicable content fingerprint before plant/controller creation. Old/absent/mismatched receipts cannot authorize preparation/start.

Evidence: 189 complete substrate tests PASS; two native zero-integration CTests PASS (Ground miss and current/fallback plan rejection). Real-child pipe tests cover >pipe-capacity stderr flood, startup/response timeouts, malformed/oversized/duplicate-key JSON, ready-validation failure and process cleanup. Actual native smoke first builds a successful policy, then rejects a synthetic all-failed private planning input; subsequent feedback is rejected instead of using the old policy; reset recovers; unknown JSON operation stays structured. Actual generated-source tampering and the old clean qualification receipt are rejected. Tampered build-cache source was restored byte-for-byte. Full style and intermediate aggregate development qualification passed; the final clean receipt is generated only after the source/evidence commit and must be revalidated, not inferred from development status.

Canonical plant steps=0 and time=0 throughout these native smokes. Controller-private planning DOES integrate private rollouts. The two native CTest fixtures themselves call no integrator. Scientific attempts remain 0. No v1 rerun, live v2, push, merge or reviewer dispatch occurred.

Raw evidence root is recorded below; failed fixture/parser/build attempts are retained. No source/physics/threshold change was made to force a performance PASS. The invalid-rollout rejection remains a runtime intervention requiring independent science/execution rereview on the new exact HEAD.

Next gate: verify the new clean receipt and qualification-bound zero-canonical-step v2 bundle, then independently rereview their exact HEAD and source diff. Only new explicit START plus fresh preflight can authorize live v2.
