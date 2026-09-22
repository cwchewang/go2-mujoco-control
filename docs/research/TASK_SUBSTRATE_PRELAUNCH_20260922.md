# Substrate first-capture preparation

Parent: `96859ea767efac5557eaf55d95cfd25c95025367`.
User direction: complete preparation up to, but excluding, formal experiments.
Mode now: infrastructure. New branch `research/substrate-prelaunch-20260922`
because the added runner and analyzer define future runtime/evidence semantics.

Deliver a frozen, prospective first-capture protocol, in-process RL runner,
independent analyzer, exclusive attempt accounting, exact-head review/readiness,
and a zero-physics-step rehearsal through the real runtime. Synthetic plant
fixtures may exercise the full runner. Do not call `mj_step` on a real plant,
execute a capability trial, tune from trajectory outcomes, or start training.

The first future checkpoint is exploratory flat RL deployment compatibility,
not the entire Gate 0 and not a method comparison. Flat compatibility must be
understood before terrain or optimizer comparisons; MJPC retains its separate
static admission. The prospective protocol and rationale live in
`tools/substrate/protocols/rl_flat_v1.json` and
`docs/research/SUBSTRATE_FIRST_CAPTURE.md`.

Review the committed runner/analyzer semantics under SOP before handoff. Review
is separate from user authorization to start. No authorization is created here.
This branch is reserved for that first scientific checkpoint. A future start
requires fresh exact-head preparation; preparation is repeatable on a fresh output.

Acceptance: full synthetic success/failure/cadence/stop tests; actual checkpoint
and model prepare with zero steps; current qualification and CI; source-bound
review record; preserved evidence and local/remote matching clean commit.
