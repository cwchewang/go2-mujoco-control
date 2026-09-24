# One-off host cleanup: Praxis task #178 orphan processes

## Objective

Perform exactly one bounded host cleanup on Atlas: terminate only processes whose
environment proves they belong to the abandoned Praxis task
`cwchewang/go2-mujoco-control#178`.

This is an operations cleanup, not a research task. Do not run experiments. The
only tracked repository change allowed is appending the result section to this
task document and committing that single-file change.

## Exact identity predicate

A process is in scope if and only if its `/proc/<pid>/environ` contains BOTH exact
entries:

- `PRAXIS_REPOSITORY=cwchewang/go2-mujoco-control`
- `PRAXIS_ISSUE_NUMBER=178`

Do not infer scope from process names, PPID, command text, usernames, worktree
paths, or approximate matches.

## Required procedure

1. Enumerate `/proc/[0-9]*/environ`. Build the exact in-scope PID set using only
   the two environment predicates above.
2. Before sending any signal, save evidence in `$PRAXIS_EVIDENCE_DIR` containing
   for every matched PID: PID, PPID, PGID, command line, and the two matched
   environment entries.
3. Separately snapshot any processes matching
   `PRAXIS_REPOSITORY=cwchewang/physics-knowledge-for-control` and
   `PRAXIS_ISSUE_NUMBER=50` for safety context. Never signal those processes.
4. If the #178 set is non-empty, send SIGTERM to each PID in that exact set.
   Do not use `pkill`, `killall`, service/systemd stop, process-name matching,
   cgroup-wide killing, or any signal target that includes processes outside the
   exact set.
5. Wait 3 seconds, rescan using the exact predicate. If any #178 PIDs remain,
   send SIGKILL only to those remaining exact matches.
6. Rescan once more. Success requires zero remaining exact #178 matches.
7. Save the post-cleanup scan and the exact list of signaled PIDs/signals in
   `$PRAXIS_EVIDENCE_DIR`.
8. Append a short `## Result` section to this file stating only:
   - initial exact #178 PID count,
   - PIDs sent SIGTERM,
   - PIDs sent SIGKILL, if any,
   - final exact #178 PID count,
   - whether any non-#178 PID was signaled (must be NO),
   - whether #50 was observed during the safety snapshot.
   Commit only this file.

## Hard prohibitions

- Do not stop or restart `praxis-v2.service`.
- Do not signal the Praxis daemon itself unless it independently satisfies the
  exact #178 environment predicate.
- Do not signal PokeWorld #50 or any process lacking both exact #178 environment
  entries.
- Do not alter Go2/PokeWorld/Praxis code or configuration.
- Do not create, switch, or attach Git branches.
- Do not run MuJoCo, training, capture, qualification, review, or scientific
  attempts.
- Do not push; Praxis will publish the result commit.

If `/proc` cannot be read reliably, stop BLOCKED without sending any signal.
