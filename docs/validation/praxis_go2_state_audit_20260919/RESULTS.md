# 1. VERIFIED FACTS

## Audit scope and evidence limits

- The audited task is `research/praxis-go2-state-audit-20260919` at
  `a7dece2f19a04680cdc2de9db13bf2b7e5c4de42`. The checkout is detached at that
  exact commit; its parent is `0f0d8e2110be81d9bbecf754cbce54688cce777f`.
- The required `git fetch origin --prune` was attempted first, but the linked
  worktree's shared Git metadata is read-only:
  `.../.git/worktrees/a7dece2f19a04680/FETCH_HEAD: Read-only file system`.
  Therefore cached refs were not treated as a fresh remote snapshot. The
  required `origin/main:CURRENT.md`, `origin/main:AGENTS.md`, and
  `origin/main:docs/research/SOP.md` were read from the available ref. A
  direct network ref refresh was also unavailable.
- The task document does not name a separate parent RESULTS file. The adjacent
  Praxis MuJoCo canary task is still in `preparing` state, with no accepted
  `RESULTS.md`, candidate commit, or host record. It is not valid parent
  evidence for a successful canary.
- No MuJoCo, DDS, or Go2 live process was running at the point of the read-only
  process inspection. User-service status could not be queried from this
  restricted session, so unit-file definitions are not treated as proof that
  services are active.

## Persistent Go2 repository

- `/home/che/dev/go2-workspace/current` is a real directory and a Git
  worktree, not a symlink and not a standalone clone. Its `.git` is a regular
  file pointing to
  `/home/che/dev/go2-workspace/primary/sprint/.git/worktrees/lean-20260904`.
- Its checked-out branch is
  `research/phase2-known-step-v2-c-continuation-20260915`, at
  `0f8a0109dc56a2dabad600aacee71c7d99bd6a46`, and it has three untracked
  files: `docs/research/WORKSPACE_INVENTORY_20260917.md`,
  `docs/research/WORKSPACE_MIGRATION_PLAN_20260917.md`, and
  `example/cpp/tools/quarantine_raw_run.py`.
- Its configured `origin` is the `kairoi-k/go2-mujoco-control` URL, while the
  GitHub Actions event and checkout evidence use
  `cwchewang/go2-mujoco-control`. The local relation to its cached
  `origin/main` is `224` commits ahead and `1` behind. This is a dirty,
  research-frontier worktree, not a clean main anchor.
- The primary repository at
  `/home/che/dev/go2-workspace/primary/sprint` owns the common Git directory.
  The workspace contains many detached task worktrees under
  `/home/che/dev/go2-agent/tasks`; these are separate task worktrees, not a
  single interchangeable repository checkout. Raw `_runs` evidence was not
  modified.

## Runner checkout and Praxis

- The Go2 Actions checkout is
  `/home/che/actions-runner/_work/go2-mujoco-control/go2-mujoco-control`,
  separate from the persistent `current` worktree. It was at `main` commit
  `c01772f01f72818028739cb86aec305db5039cb1` during this audit.
- The direct-audit runner log shows that checkout first saw the existing
  `kairoi-k` remote, deleted the checkout contents, then initialized it with
  `https://github.com/cwchewang/go2-mujoco-control` and fetched `main`. This
  is direct evidence of repository-identity drift, not evidence that the two
  paths are the same checkout.
- The current project profile has an adapter worker:
  `python3 tools/atlas_research_task_v6.py`, a `research-push.json` request,
  and a trusted push command. The central dispatcher invokes the adapter with
  `cwd=repo_root`, passes the task parameters, then expects the request file
  before invoking the trusted push command with the same `cwd`.
- The Go2 workflow pins Praxis core to
  `1594778e2a15a8fe9dcee8b4985d971a8d5110b2`. Recent runner logs show that
  materializing this private core succeeded before every listed central
  dispatch failure. The installed runtime at
  `/home/che/.local/share/praxis/runtime` is a directory copy; the persistent
  Praxis runner checkout is a separate Git repository at
  `/home/che/.local/share/praxis/runner/_work/praxis-research-runtime/praxis-research-runtime`,
  currently at `22c1b008...`.
- Unless explicitly overridden, the Go2 adapter resolves
  `GO2_ATLAS_REPO` to `/home/che/dev/go2-workspace/current`, task worktrees to
  `/home/che/dev/go2-agent/tasks`, and state to
  `/home/che/.local/state/go2-research-worker`. Thus the adapter's default
  control-plane paths are not the Actions checkout paths.
- The canary worker state at
  `/home/che/.local/state/go2-research-worker/ba23b754ed9e4ed8ac8f422408790bb217fb0865.json`
  remains `preparing`. There is no accepted canary result or host record.

# 2. FALSE ASSUMPTIONS / MISDIAGNOSES

- `current` is not a symlink or an ordinary clone whose `.git` must be a
  directory. It is a valid linked worktree whose `.git` is a file. The
  `test -d "$anchor/.git"` check was therefore a false topology check.
- The persistent `current` path is not `$GITHUB_WORKSPACE`, the runner's
  checkout, or Praxis's own checkout. Treating those paths as interchangeable
  caused the target-path and anchor-path migration churn.
- `current` is not a clean `main` checkout. Its dirty research branch, stale
  cached refs, shared Git metadata, and different remote identity make it
  unsafe to use implicitly as a dispatcher anchor.
- The successful private-core materialization step proves only that the
  pinned core could be obtained. It does not prove that the central dispatcher
  reached the adapter, that the adapter prepared a task, or that a host
  capability was invoked.
- Praxis runner repair/restart jobs and the separate physics-runner jobs are
  not evidence that the Go2 adapter or Go2 host path ran successfully.
- The canary task's existence, queueing, or `preparing` state is not accepted
  parent evidence. No scientific result or host failure can be inferred from
  it.
- The 17:20 failure was not a MuJoCo or DDS fault: the runner canceled the
  dispatch process and sent SIGINT. The 17:54 failures were pre-dispatch
  workflow checks. None of these failures consumed a scientific attempt.

# 3. ACTUAL TOPOLOGY (persistent repo, task worktrees, runner checkout, Praxis core)

```text
GitHub event: cwchewang/go2-mujoco-control
        |
        +-- Actions checkout
        |   /home/che/actions-runner/_work/go2-mujoco-control/go2-mujoco-control
        |   (job-local checkout; main at c01772f... during audit)
        |
        +-- central dispatcher (pinned core 1594778...)
        |   cwd = dispatcher repo_root
        |   invokes tools/atlas_research_task_v6.py
        |
        +-- adapter defaults (unless explicit environment overrides)
            /home/che/dev/go2-workspace/current
            /home/che/dev/go2-agent/tasks
            /home/che/.local/state/go2-research-worker

Persistent Go2 control plane:
  /home/che/dev/go2-workspace/current
    .git -> /home/che/dev/go2-workspace/primary/sprint/.git/worktrees/...

Praxis service/runtime:
  installed copy: /home/che/.local/share/praxis/runtime
  runner checkout: /home/che/.local/share/praxis/runner/_work/...
```

The topology is therefore a job-local checkout feeding an adapter whose
default state is in a separate persistent worktree family. The current
workflow does not make that identity boundary explicit enough, and some
historical workflow revisions mixed `target`, `$GITHUB_WORKSPACE`, and
`$HOME/dev/go2-workspace/current`.

# 4. RECENT FAILURE CHAIN with exact earliest failing boundary for each attempt

| Evidence | Earliest failing boundary | Classification |
| --- | --- | --- |
| Historical `1b2cbfe`/`f7af2f3` central reusable-workflow path | Source-level topology boundary: the reusable action addressed `$GITHUB_WORKSPACE/target`; no surviving accepted result proves a later boundary. | Structural migration risk; not a host fault. |
| Historical `8bbf56c` workflow revision | The checkout of `target` was removed while the dispatch command still referenced `$GITHUB_WORKSPACE/target`. The first failure must be before adapter execution when the configured repo/config path is resolved. | Proven bad path assumption from source; no scientific attempt. |
| Runner `Worker_20260919-092019-utc.log` | Checkout and pinned-core materialization succeeded. The dispatch process was canceled at 09:25:39Z, received SIGINT, and exited 130 at 09:25:44Z. | External runner/job cancellation during dispatch; not a MuJoCo/DDS fault, and adapter reachability is unproven. |
| Runner `Worker_20260919-092557-utc.log` and `092638-utc.log` | Pinned-core materialization succeeded; the dispatch step exited 2 after 0.0668s and 0.0456s. Surviving logs contain no nested stdout and no artifact directory, so the exact subcommand inside the dispatch shell cannot be identified. | Pre-adapter/dispatch execution failure; not classifiable as host failure. |
| Runner `Worker_20260919-095408-utc.log` and `095426-utc.log` | The workflow explicitly ran `test -d "$anchor/.git"` before dispatch. The inspected anchor has a regular-file `.git`, so this check exits 2 before fetch, config materialization, or the central CLI. | Confirmed false worktree-shape check; no scientific attempt. |
| Runner `Worker_20260919-101112-utc.log` (direct audit job) | The revised `-e` plus `git rev-parse --is-inside-work-tree` checks passed in the workflow script, but the dispatch step exited 1 after 1.12s. No task state, candidate, host record, or dispatcher artifact survived; nested stderr was not retained. The exact inner command is unresolved. | Dispatch/anchor execution failure with insufficient evidence to name a deeper boundary; not evidence of a host fault. |

The most specific supported conclusion is that no listed migration attempt
reached an accepted adapter candidate or a host launch. The two classes must not
be collapsed into one “runner fault”: one was cancellation, and the others
were path/configuration or otherwise unobserved dispatch failures.

# 5. MINIMAL SAFE MIGRATION PLAN

1. Keep this audit result as the decision input. Do not change controller,
   planner, simulator, DDS, raw evidence, `.github/**`, or `tools/atlas_*` as
   part of this audit.
2. Select one canonical repository identity, currently the event repository
   `cwchewang/go2-mujoco-control`, and one explicitly named Go2 anchor. Before
   any migration write, verify the anchor's remote URL, Git common directory,
   `HEAD`, default branch, worktree list, cleanliness, and reachability of the
   exact task commit. Do not silently use the `kairoi-k` alias.
3. Make dispatcher `repo_root`, adapter `GO2_ATLAS_REPO`, task-worktree root,
   state root, and output root explicit and record them in the preflight
   evidence. The adapter command must be resolved relative to the same
   checkout that the dispatcher passes as `cwd`.
4. Replace shape checks with Git-semantic checks (`-e` plus
   `git rev-parse --is-inside-work-tree`) and make the remote/config source
   explicit. A `FETCH_HEAD`-based config read is only valid after verifying the
   anchor's remote identity and fetch result; it must not bridge two repository
   identities.
5. Run a no-host adapter preparation check for the frozen task. Require a
   verifiable task worktree, task state, progress/output logs, and an accepted
   local candidate/closeout before enabling any trusted push or host capability.
   Preserve all failed logs instead of retrying blindly.
6. Only after the above passes should Sol choose a separate, SOP-authorized
   canary. The migration itself must remain infrastructure-only and must not
   change scientific meaning.

# 6. WHAT MUST BE VERIFIED BEFORE ANY LIVE MUJOCO CANARY

- Fresh remote evidence: the exact GitHub repository identity, `origin/main`,
  task branch, task commit, parent evidence, and no local divergence or dirty
  files in the selected anchor/worktree.
- Exact execution chain: pinned Praxis core content, dispatcher `repo_root`,
  adapter command and `cwd`, all Go2 path environment variables, task-worktree
  root, state root, output root, and the trusted push request path.
- A successful no-host adapter run that reaches the intended task boundary and
  produces inspectable state/output. There must be no reliance on a missing
  `target` directory, a `.git` directory-only test, or an unverified remote
  alias.
- Actual runner/service readiness, including readable service status, runner
  identity/labels, exclusive host-live lock ownership, no stale competing
  worker, and no unexplained active MuJoCo/DDS process. Unit files alone are
  insufficient.
- SOP preflight on the exact branch and clean worktree, including protected
  path checks and the task's frozen variables, run budget, thresholds, and
  classification. No live run is authorized by this audit result.
- Before launch, immutable records of controller/planner/simulator/scenario
  identities, output directory, raw-evidence manifest plan, and recovery path.
  After launch, preserve raw `_runs` exactly and do not infer a scientific
  outcome from an infrastructure failure.
