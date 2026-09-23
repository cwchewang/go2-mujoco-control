# Atlas task runner

This repository dispatches a small allow-list of trusted tasks to the Atlas
WSL2 self-hosted runner through a labeled GitHub Issue.

The workflow listens only for newly opened Issues carrying the `atlas-task`
label and only accepts Issues authored by an owner, member, or collaborator.
It checks out trusted `main` code with checkout credentials removed. The Issue
body is parsed as data; it is never passed to a shell.

## Maintenance tasks

These remain available:

~~~json
{"task":"repo-smoke","parameters":{}}
~~~

~~~json
{"task":"workspace-status","parameters":{}}
~~~

## Research task

A research task is a pointer to an already committed repository task, not an
arbitrary prompt or shell command:

~~~json
{
  "task": "research-task",
  "parameters": {
    "branch": "research/example",
    "task_path": "docs/research/TASK_EXAMPLE.md",
    "task_commit": "0123456789abcdef0123456789abcdef01234567"
  }
}
~~~

The dispatcher accepts only normalized `research/*` branches,
`docs/research/TASK_*.md` paths, and full lowercase commit SHAs. Before Luna
starts, Atlas fetches `origin`, requires the named remote branch to point
exactly at `task_commit`, verifies the task exists at that commit, and verifies
that trusted `origin/main` still provides `AGENTS.md` and
`docs/research/SOP.md`.

Each research task receives a dedicated detached Git worktree under the Atlas
agent workspace. The user's normal `current/` worktree is never checked out,
reset, cleaned, or used for task-local edits. The normal worktree is exposed
to Luna only as a read-only reference location for ignored historical raw
evidence that is not present in Git.

Atlas launches a fresh non-interactive Codex session with the fixed model
`gpt-6-luna` at `max` reasoning effort, `workspace-write` sandboxing, and the task worktree as the
workspace. The bootstrap prompt contains only repository protocol and task
identity. Scientific instructions remain in the committed task document.

The worker stores the Codex thread ID by task commit. If a workflow is
interrupted and retried for the same task, the same task session can be
resumed. A new task commit creates a new session.

Luna may modify the task worktree but receives no GitHub write token and is
explicitly forbidden from changing `.github/**` or `tools/atlas_*`. Luna
commits its closeout locally and never pushes.

After Luna exits, trusted wrapper code verifies that:

- the result is descended from the exact task commit;
- the worktree is clean;
- `git diff --check` passes;
- protected Atlas/workflow paths were not changed;
- raw `_runs` evidence was not added to Git.

Only then does a separate workflow step receive `GITHUB_TOKEN`. It re-fetches
the remote branch and pushes only if the branch still points at the original
`task_commit`, using `--force-with-lease` as a compare-and-swap guard. If the
remote branch moved while Luna was working, the push is rejected rather than
overwriting newer work.

All Atlas jobs are serialized by workflow concurrency and the research worker
also has a machine-local lock. Research jobs may run for up to six hours.

Results, Codex JSONL output, stderr, and the trusted push request are uploaded
as the existing per-Issue artifact. Successful Issues are labeled
`atlas-complete` and closed; failures are labeled `atlas-failed` and remain
open.

The runner itself is installed outside the checkout, registered with the
`atlas` label, and managed by the existing user-level service/startup setup.
