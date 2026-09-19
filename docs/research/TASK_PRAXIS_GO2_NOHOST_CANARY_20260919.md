# Praxis Go2 no-host adapter canary — 2026-09-19

Mode: infrastructure

## Objective

Verify the central Praxis -> Go2 adapter path end to end without invoking any
host-live capability.

This task intentionally contains no `ATLAS_HOST_EXPERIMENT` block. It must
remain an offline/no-host task.

The path under test is:

central Praxis dispatcher -> dedicated canonical Go2 Praxis anchor -> project
adapter -> isolated task worktree -> Luna offline execution -> trusted closeout
commit -> trusted push.

## What Luna should verify

Independently inspect the execution context available to this task and verify:

- the repository/task identity and exact frozen task commit;
- the actual Git worktree used for this task;
- the configured canonical repository identity visible through Git;
- the explicit Go2 repo/task/state paths supplied by the dispatcher;
- that this task is running through the Go2 adapter and not the old
  project-local dispatcher;
- that no MuJoCo/DDS/live experiment was launched;
- that no scientific attempt was consumed.

Do not assume the expected topology is correct merely because it is stated
here. Report discrepancies if you find them.

## Constraints

- Do not launch MuJoCo, DDS, simulator/controller binaries, or any live capture.
- Do not modify controller/simulator/research code.
- Do not modify `.github/**` or `tools/atlas_*`.
- Do not touch historical raw evidence.
- Do not perform a second task or follow-up experiment.
- This is infrastructure evidence only.

## Deliverable

Write only:

`docs/validation/praxis_go2_nohost_canary_20260919/RESULTS.md`

with:

1. VERIFIED EXECUTION FACTS
2. PATH / REPOSITORY IDENTITY
3. ADAPTER / WORKTREE / STATE EVIDENCE
4. NO-HOST / NO-SCIENTIFIC-ATTEMPT EVIDENCE
5. ACCEPTANCE: whether the central Praxis -> Go2 adapter path is ready for a
   separate MuJoCo live canary, with any remaining blocker stated precisely.
