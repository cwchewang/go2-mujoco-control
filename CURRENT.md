# Go2 current research frontier

`main` remains the stable code line and long-term route.

## Active research frontier

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) and [TOPIC_AUDIT](docs/TOPIC_AUDIT.md)
for scientific context; the [SOP](docs/research/SOP.md) governs evidence.

- Branch: `main` after the first-capture closeout PR; `research/substrate-first-capture-20260922` while that PR is pending.
- Task: [First formal flat capture](docs/research/TASK_SUBSTRATE_FIRST_CAPTURE_20260922.md)
- Closeout: `docs/validation/substrate_first_capture_20260922/RESULTS.md`
- Current stage: first formal capture CLOSED / FAIL; attempt 1 complete, attempts 2 and 3 NOT_RUN. No automatic rerun.
- Scientific status: flat deployment compatibility failed both frozen endpoint metrics; full Substrate Gate 0 remains incomplete.

The 2026-09-17 integration and flat repeats are sealed legacy references, not
the current execution task. Existing v0 design lives at immutable reference
`ed3896c3f4355d6409077d61b14d6dc743d6655f`; it is not a live-run authorization.

Foundation PR #139 is merged at `c5582af60b802b688e4e526845402deb33cf29cd`.
This branch continues the user's explicit merge-and-start instruction; the
first-capture task supersedes the preparation-only stop boundary. Its frozen
scientific protocol and stop rules remain unchanged.

Exact execution HEAD: `09a9a31e2ab6eefcd4d3193107e8e17dad642129`.
Next work is offline diagnosis of preserved evidence and locked deployment
semantics. A new live intervention requires a separately frozen task; this
campaign is sealed and cannot be retried or replaced.
