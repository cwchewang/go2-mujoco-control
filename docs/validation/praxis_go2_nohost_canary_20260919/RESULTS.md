# Praxis Go2 no-host adapter canary closeout

Date: `2026-09-19`

Mode: `infrastructure`

## VERIFIED EXECUTION FACTS

- Requested branch: `research/praxis-go2-nohost-canary-20260919`.
- Frozen task commit: `24566b455fc31793506769e4db793dccb7a44867`.
- `HEAD` is exactly that task commit and exactly
  `origin/research/praxis-go2-nohost-canary-20260919` in the available Git
  snapshot.
- The task worktree was clean before this closeout. No controller, simulator,
  research-runtime, `.github/`, `tools/atlas_*`, or historical raw-evidence
  files were modified.
- The SOP-required parent evidence consulted was
  `docs/validation/canonical_clean_baseline_integration_20260917/RESULTS.md`;
  it records an offline/no-live canonical integration result and does not
  authorize a live run.

## PATH / REPOSITORY IDENTITY

- Actual task worktree: `/home/che/dev/go2-praxis/tasks/24566b455fc31793`.
- Canonical Go2 Praxis anchor supplied to the worker:
  `/home/che/dev/go2-workspace/praxis-anchor`.
- Git reports the anchor as a clean `main` worktree at
  `d2b6a8fb7a22961a5a8ae0aacbeabe4177d536bb`, equal to its local
  `origin/main` ref.
- Git `remote.origin.url` in the shared anchor is
  `https://github.com/cwchewang/go2-mujoco-control.git`, matching
  `GO2_CANONICAL_REPO` and the workflow’s configured canonical identity.
- Dispatcher-supplied paths were present and matched the audit context:
  `GO2_PRAXIS_ANCHOR`/`GO2_ATLAS_REPO`,
  `GO2_PRAXIS_TASKS=/home/che/dev/go2-praxis/tasks`, and
  `GO2_PRAXIS_STATE=/home/che/.local/state/praxis-go2-worker`.
- Discrepancy: the available `origin/main:CURRENT.md` navigation links name
  the `kairoi-k` GitHub URL and a different active research frontier, while
  Git’s configured canonical remote and the dispatcher workflow use
  `cwchewang` and this explicitly supplied task ref. The explicit task ref
  remains internally consistent.
- The required remote refresh was attempted. `git fetch origin --prune`
  could not write `FETCH_HEAD` because this linked worktree’s Git metadata is
  read-only; the non-writing-fetch-head fallback could not reach GitHub from
  the network-disabled sandbox. Remote conclusions above therefore use the
  available verified refs, not a fresh network assertion.

## ADAPTER / WORKTREE / STATE EVIDENCE

- `.atlas/project.json` identifies project `go2-mujoco-control`, worker kind
  `adapter`, and adapter command `python3 tools/atlas_research_task_v6.py`.
- `.github/workflows/atlas-task.yml` supplies the same canonical URL and
  paths, pins Praxis core ref
  `1594778e2a15a8fe9dcee8b4985d971a8d5110b2`, and invokes the central
  `research_orchestrator.atlas_core.cli dispatch` module before the Go2
  adapter.
- The dispatcher state record
  `/home/che/.local/state/praxis-go2-worker/24566b455fc31793506769e4db793dccb7a44867.json`
  records schema `6`, the requested branch, task path, exact task commit,
  and this exact detached worktree. This is the Go2 adapter state path, not
  the old project-local dispatcher state.
- `git worktree list --porcelain` shows the canonical anchor and this
  isolated detached task worktree; no branch checkout or shared task edits
  were used.
- The worker’s task-manifest parser returned `None` for the frozen task, so
  the trusted host-capability path was not selected.
- A process-name audit found no `mujoco`, simulator, controller, DDS probe,
  `run_trot`, or host-experiment process. No old project-local dispatcher
  process was present at audit time.

## NO-HOST / NO-SCIENTIFIC-ATTEMPT EVIDENCE

- The task explicitly contains no `ATLAS_HOST_EXPERIMENT` manifest; the
  parser independently confirmed `manifest=None`.
- The worker state contains no `host_record`, `candidate_commit`,
  `result_commit`, or `scientific_attempt_consumed` field. The host-live lock
  `/tmp/atlas-host-live.lock` was absent.
- No MuJoCo, DDS, simulator/controller launch, live capture, or raw-run
  creation occurred. No scientific attempt was consumed.

## ACCEPTANCE

**READY for a separately authorized MuJoCo live canary from the adapter-path
perspective, with a remote-refresh caveat.** The central Praxis dispatch
configuration, canonical Go2 anchor, explicit task/state paths, isolated
worktree materialization, and no-host adapter branch were verified end to end.

This closeout is not live-run evidence and does not authorize a live run. A
separate task must still pass the SOP preflight and trusted host capability
gate. Before that task relies on fresh remote state, the dispatcher environment
must also provide a writable Git admin area and network access (or an
equivalent trusted ref-refresh mechanism); this worker could verify only the
matching local remote-tracking refs.
