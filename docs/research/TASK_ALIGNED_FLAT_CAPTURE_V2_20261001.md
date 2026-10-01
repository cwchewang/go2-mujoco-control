# Aligned flat capture v2: preparation for independent review

Status: PREPARED FOR REVIEW / NOT_STARTED.
Parent: sealed v1 infrastructure stop and MJPC Ground/IPC hardening engineering acceptance.
Purpose: decide whether the repaired shared native boundary can complete the bounded engineering anchor before any capability comparison. The result remains engineering integration evidence only.

This is a new campaign, not a retry or replacement of v1. Executable plan: tools/substrate/protocols/aligned_flat_capture_v2.json. It reuses the exact frozen aligned_flat_anchor_v1.json because canonical scene/reset/metrics, information asymmetry, 2 ms physics, 20 ms planning, 2 ms MJPC feedback and 50 Hz RL cadence are intentionally unchanged. The only runtime intervention is source-bound invalid-rollout/diagnostic handling; its neutrality needs independent review.

Prospective budget after approval and START: RL then MJPC, one attempt each, at most 500 canonical steps (1 second) per arm, no retry, 300 s wall bound, scientific attempts=0. Same broad integration thresholds, safety stops, controller snapshots, append-only JSONL capture and independent CanonicalEvaluator replay as the frozen anchor. A failed arm is retained; no tuning, replacement or threshold change. Output root and attempt ledger are exclusively aligned_flat_capture_v2. v1 remains sealed and closed.

If both arms complete valid terminal evidence, report engineering interface/evaluator integration and then decide a separate capability task. Infrastructure or evidence failure closes v2 without controller ranking. A valid performance/safety failure is retained as bounded engineering evidence; it does not establish a scientific bottleneck.

Current authorization: physics_step_authorized=false; scientific_attempts_authorized=0. This plan does not self-authorize physics. Review must bind the actual clean HEAD, v2 protocol hash, prepared bundle hash, native binary/source identity, qualification fingerprint and trajectory-affecting diffs. Science and execution reviewers must be independent. Parent coordinates dispatch; this worker does not contact reviewers.

Preparation entry: reliable Python calls tools.substrate.aligned_capture.prepare(fresh_output, Path("tools/substrate/protocols/aligned_flat_capture_v2.json"), qualification_path=fresh_clean_receipt). It acquires the experiment lock, applies zero_step_guard, verifies exact identities, and records canonical time/steps=0. Future capture must explicitly pass plan_path=v2; protocol hash, anchor hash, prepared HEAD, independent reviews and actual user START are revalidated before plant/controller creation. No capture is run by this task.

Reviewer checklist: inspect Ground fallback/warning invalidation (including reset and failure selection), warnings/IPC transport, continuous stderr draining/log retention, startup/request deadlines and owned-process cleanup, generated-source/build identity, v2 ledger isolation, frozen anchor reuse, model/actuator neutrality, divergent-rollout handling, rejected missing/invalid START before plant creation, no changed research question/thresholds. Require exact-head PRECHECK PASS evidence and a fresh clean process/lock preflight before any live START.

HOLD remediation: prior 73fae9b review is HOLD and cannot authorize this runtime. See docs/validation/mjpc_hold_repair_v2_20261001/RESULTS.md. Preparation/start must bind and revalidate the new clean receipt; review all-failed current-candidate rejection and generated/actual compilation dependency bytes. Independent rereview is required.
