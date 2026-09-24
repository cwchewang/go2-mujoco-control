# One-off host cleanup r2: Praxis task #178 orphan processes

## Objective

Perform one bounded host cleanup on Atlas: terminate only same-UID processes whose
environment proves they belong to the abandoned Praxis task
`cwchewang/go2-mujoco-control#178`.

This is an operations cleanup, not a research task. Do not run experiments. The
only tracked repository change allowed is appending the result section to this
task document and committing that single-file change.

## Scope and exact identity predicate

Let `target_uid = os.getuid()`, i.e. the UID of this Praxis/Codex worker.

Only inspect processes whose `/proc/<pid>/status` real UID equals
`target_uid`. Processes owned by any other UID are out of scope and must not
block the task merely because their `environ` is unreadable.

A same-UID process is a #178 target if and only if its
`/proc/<pid>/environ` contains BOTH exact entries:

- `PRAXIS_REPOSITORY=cwchewang/go2-mujoco-control`
- `PRAXIS_ISSUE_NUMBER=178`

Do not infer scope from process names, PPID, command text, usernames, worktree
paths, or approximate matches.

If any same-UID process cannot have its status or environment read reliably,
stop BLOCKED before sending signals. Permission failures for other UIDs do not
block.

## Required procedure

1. Enumerate `/proc/[0-9]*`.
2. Read `/proc/<pid>/status` first and keep only processes whose real UID equals
   `target_uid`.
3. For every same-UID process, read `/proc/<pid>/environ`. Build the #178 PID
   set only from the exact two-field predicate above.
4. Before signaling, save evidence in `$PRAXIS_EVIDENCE_DIR` containing for
   every matched #178 PID: PID, PPID, PGID, command line, real UID, and the two
   matched environment entries.
5. Separately identify same-UID PokeWorld #50 processes using BOTH:
   - `PRAXIS_REPOSITORY=cwchewang/physics-knowledge-for-control`
   - `PRAXIS_ISSUE_NUMBER=50`
   Save their PID/PPID/PGID/cmdline for safety context. Never signal them.
6. If the #178 set is non-empty, send SIGTERM individually to each exact matched
   PID. Do not use process-name matching or group-wide/service-wide killing.
7. Wait 3 seconds, then repeat the same same-UID exact scan.
8. If any exact #178 matches remain, send SIGKILL individually only to those
   remaining exact matches.
9. Wait 1 second and rescan once more. Success requires zero same-UID exact #178
   matches.
10. Save the post-cleanup scan plus the exact PID/signal ledger in
    `$PRAXIS_EVIDENCE_DIR`.
11. Append a short `## Result` section to this file stating:
    - target UID,
    - initial exact #178 PID count and PIDs,
    - PIDs sent SIGTERM,
    - PIDs sent SIGKILL if any,
    - final exact #178 PID count,
    - whether any non-#178 PID was signaled (must be NO),
    - #50 same-UID PIDs observed before/after.
    Commit only this file.

## Hard prohibitions

- Do not stop or restart `praxis-v2.service`.
- Do not use sudo.
- Do not use `pkill`, `killall`, process-name matching, cgroup-wide killing,
  or negative/PGID signal targets.
- Do not signal the Praxis daemon unless it independently satisfies the exact
  #178 predicate.
- Do not signal PokeWorld #50 or any process lacking both exact #178 entries.
- Do not alter Go2/PokeWorld/Praxis code or configuration.
- Do not run MuJoCo, training, capture, qualification, review, or scientific
  attempts.
- Do not push; Praxis will publish the result commit.

If the same-UID process inventory cannot be established reliably, stop BLOCKED
without sending any signal.
