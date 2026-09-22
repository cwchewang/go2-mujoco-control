# Go2 workspace standard — 2026-09-22

Repository scientific/execution policy is versioned in docs/research/SOP.md.
Workspace rules cover locations, preservation and ownership only. There is no
requirement for repository Markdown to link outside the checkout.

current/ is the default writable repository. primary/, reference/ and existing
historical worktrees are retained references. external/ contains independent
dependencies. New task checkouts need explicit ownership and a reason; do not
create a second permanent entrypoint. Unknown or unrelated legacy objects are
inventoried for separate review, not deleted or used to stop unrelated code work.

Generated build/cache files outside raw runs may be rebuilt or cleaned. All raw
run objects, including failed and development runs, are preserved. Sealed evidence
objects are read-only by policy; archive/evidence accepts new exclusive archives.
Raw plus verified archive is an intentional preservation copy, not a second mutable
source. Derived CATALOG.json, SHA256SUMS and the generated INDEX block are mutable
indexes; do not edit raw evidence to reconcile them.

The authoritative generated archive/branch/worktree inventory is
archive/evidence/CATALOG.json. Per-archive manifests remain integrity authorities.
Generate it with `python -m tools.research.workspace --workspace /home/che/dev/go2-workspace`.
This verifies checksums and records unknown historic ownership without deleting
anything. Human history in archive/INDEX.md is preserved before the generated block.

Raw movement uses the audited quarantine tool after path/reference/hash checks.
No agent may permanently delete raw or quarantine content without a new user
instruction naming that exact path and an independently verified surviving copy.
Archive tags are ordinary Git references unless server protection enforces the
policy; describe actual protection instead of claiming cryptographic immutability.

CURRENT.md is generated from repository docs/research/current.json. Tasks own
execution scope, result bundles own scientific facts, PROJECT_RECORD owns research
conclusions. START_HERE is generated from these plus observed Git identity; it is
not a competing status authority. Update it at handoff. One campaign may contain
all predeclared repeats; branch creation is per task, not per repeat.
