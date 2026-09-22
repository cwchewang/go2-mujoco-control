# Go2 workspace rules

The user's current instruction defines the authorized task. Repository AGENTS.md
and docs/research/SOP.md govern science and code; this file governs storage and
workspace ownership. These scopes complement each other; ambiguity is resolved
before the affected action, not by blocking unrelated work.

Use `/home/che/dev/go2-workspace/current` as the default writable checkout.
Read its CURRENT.md and exact task/result; START_HERE.md is a generated convenience.
Fetch origin and verify branch, HEAD and dirty state on task entry. Preserve any
divergence. Historical/reference worktrees are retained read-only unless explicitly
assigned. Their mere existence does not block work in current.

All builds, tests and physics runs hold `/tmp/go2_mujoco_experiment.lock`.
Raw `_runs` and sealed archive objects must never be overwritten, renamed or
deleted. New archives may be added under archive/evidence with verified checksums;
generated indexes may be refreshed. Quarantine moves require the existing audited
tool; permanent deletion still requires a new explicit user instruction naming
the exact path and an independently verified surviving copy.

One branch per task/campaign, not per replicate. Classify remote branches and
worktrees as active, retained reference or pending owner review. Retire only owned,
completed branches after preserving their tips in archive tags; never bulk-delete
unreviewed history. Generate inventory and handoff with tools.research.workspace.
See WORKSPACE_STANDARD.md for storage definitions.
