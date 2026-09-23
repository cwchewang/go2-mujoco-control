# TASK — Praxis substrate resource provisioning live acceptance

Date: 2026-09-23
Mode: infrastructure acceptance / zero scientific execution
Scientific attempts: 0 required

## Objective

Verify on the real Atlas Praxis research-task path that the isolated task worktree
receives the canonical, hash-bound Go2 substrate resources needed by research
workers without network download or manual copying.

## Required checks

1. `git branch --show-current` equals
   `research/praxis-resource-provisioning-acceptance-20260923`.
2. HEAD remains descended from this frozen task commit; do not rewrite task identity.
3. `.substrate/rl/policy.pt` exists and SHA-256 equals
   `9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d`.
4. Every file declared by `tools/substrate/rl_reference.lock.json` exists under
   `.substrate/upstream-go2-30e74dc5` and matches its declared SHA-256.
5. `.substrate/venv-reliable/bin/python` imports torch, mujoco and numpy and
   reports the expected accepted versions: Torch 2.6.0+cpu, MuJoCo 3.3.6,
   NumPy 2.2.6.
6. `.substrate/headless-reliable/go2_mjpc_admit` exists.
7. Confirm the bound resources are links into the persistent canonical resource
   root, not copied tracked files.
8. Confirm `git status --porcelain` does not show the ignored substrate resources.

## Output

Write only:
`docs/validation/praxis_resource_provisioning_acceptance_20260923/RESULTS.md`

Record PASS/FAIL for each check, model/effort observed from trusted checked-in
worker configuration, and an overall acceptance verdict.

## Constraints

- Do not download or install anything.
- Do not use network.
- Do not run MuJoCo physics, policy inference, qualification, or scientific capture.
- Do not modify .github/**, tools/atlas_*, .substrate/**, raw evidence, or any
  scientific protocol.
- Do not consume a scientific attempt.
- Do not push or write Git metadata; the trusted wrapper owns closeout.
