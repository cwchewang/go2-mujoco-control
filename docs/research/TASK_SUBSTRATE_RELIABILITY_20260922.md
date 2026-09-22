# Pre-experiment substrate reliability

Parent: 82dc82f470973f9a5031c052b89611ba32438d10; same foundation branch and PR.
User instruction: make all pre-experiment foundations as reliable as possible.
Scope: offline tooling, integrity, environment isolation, source/binary binding,
typed contracts, deterministic policy reset, robust subprocess/evidence handling,
restored SOP preflight and regression coverage. No legacy controller tuning.

All existing evidence remains immutable. All build/test/admission work uses the
shared lock. Zero new scientific/locomotion/hardware attempts. Synthetic fault
injection, real dependency builds, model forward, checkpoint inference and static
optimizer checks are engineering tests. No invented performance optimum or Gate
0 capability verdict. Keep existing scientific thresholds unchanged.

Acceptance: fresh isolated pinned environment; native build provenance verified
against source, dependencies, compiler, library and executable; strict model and
result validation; negative tests for corruption, stale build, malformed input,
timeout, output collision, lock contention and interrupted evidence; independent
offline replay/reset; preflight fixtures restored with fail-closed behavior;
current CTest and hosted CI pass; committed clean remote-matching head.

Closeout: docs/validation/substrate_reliability_20260922/RESULTS.md.
Update PR #138 and workspace START_HERE. Keep formal experiment approval and
scientific configuration separate from engineering readiness.
