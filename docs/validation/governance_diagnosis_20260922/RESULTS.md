# Governance repair and offline diagnosis

Parent: `9f7ee6eb226cbdedad5b514328b8fa72463c1d0f`.
The original campaign remains FAIL; attempts 2/3 remain NOT_RUN.
This task adds no physical integration or scientific attempts.

## Finding

The checkpoint is a real pretrained public RL policy, but the first test was a
transfer to our model/reset and a 0.15 m/s tracking requirement, not an exact
reproduction of upstream deployment. It moved 0.364124 m in 10 s and achieved
0.042597 m/s mean world-forward velocity in the last 5 s. Both frozen endpoint
gates failed: progress <1 m and velocity MAE 0.107403 >0.1 m/s. No fall, forbidden
contact, simulator warning or torque saturation explained that failure.

Independent replay on all 500 recorded policy inputs gives exactly zero maximum
error in the observation, upstream/current joint target, recorded joint target,
and all 5000 applied PD controls. Reconstructing all 5001 recorded contact states
with `mj_forward` also gives zero mismatches. This substantially narrows the
search away from observation scales, joint order and the PD implementation on
this trajectory; it does not certify unobserved trajectories or the source
checkpoint's original training setup.

## Why a pretrained policy can still track poorly

The pinned upstream YAML defaults to 1 m/s; our frozen test requests 0.15 m/s.
The visible training reward uses `exp(-velocity_error_squared / sigma)` with
sigma 0.25 at this low command. Standing still scores 0.913931 at 0.15 m/s, versus
0.018316 at 1 m/s. Substitution of our measured body velocities yields a mean
reward of 0.950846 in the primary window despite poor tracking. That illustrates
weak low-speed discrimination in this reward term; it is not the total reward,
and no training-run configuration/log proves this checkpoint used these exact
settings. Rough-terrain success is not a certificate of precise low-speed
tracking on a modified deployment model.

The policy does respond to the command. Fixed-state inference with fresh history
per command gives joint-target RMS differences from zero-command inference of
0.267671 rad at 0.15 m/s, 0.460881 at 0.3 m/s and 0.534798 at 1 m/s. This rejects
an ignored command or hard low-speed dead zone on these inputs. These are
open-loop sensitivities, not predicted speeds or new closed-loop results.
The source's separate `norm > 0.2` mask is in the non-dynamic sampling branch;
visible GO2Cfg enables dynamic sampling, so that mask is not a valid explanation.

The deployment plant also differs. Effective joint damping is 0.1 versus
upstream 0.001; friction loss is 0.2 versus 0.1. Collision geometries, contact
settings and force limits differ. Total mass agrees at 15.206408 kg. Additional
same-state viscous damping is only 0.035372 Nm RMS compared with 3.691622 Nm
recorded control RMS, but this calculation excludes constraint friction and
closed-loop effects; it cannot dismiss model mismatch. Our bent-leg reset at
base z=0.27 m and inference at tick 0 also differ from upstream's default
z=0.445 m, zero joint reset and first inference after ten PD steps. Both policy
periods are 20 ms. Four-foot support occupies 63.65% of our last-five-second
samples, a description of the slow trace rather than proof of a particular cause.

The defensible diagnosis is therefore: interface-consistent transfer with
unresolved command-domain, plant and startup differences. A single failed trace
cannot rank their causal contributions. It does not establish that the upstream
RL method is intrinsically weak.

## Governance repairs

Qualification now binds maintained source/tests/assets, actual Python packages
and interpreter, checkpoint, native build/library identity, CPU identity, and
the controller build products plus compiler header/link dependencies. Every
reuse validates this fingerprint and freshly checks lightweight repository
quality. Prose/task metadata can change without repeating the whole test suite;
exact execution HEAD, task identity, review and authorization remain fresh.
Task protocols must be tracked JSON within the qualified protocol directory.
Authorization and protocol attempt budgets must agree before any ledger claim.

Preflight classifies previously missed substrate modules and unknown executable
files conservatively; explicit runner changes always produce a reviewable diff.
Portable synthetic checks use an independently implemented numerical oracle.
Local historical verification checks the permanent external ledger by default,
derives claims from consumed trajectories and rejects extra/unconsumed claims.
Portable archive-only verification is explicit and reports its reduced scope.

The SOP distinguishes engineering checks, exploratory experiments and
confirmatory claims. A future prospectively declared diagnostic matrix may
continue after an expected performance failure, while safety/integrity failure
still stops it. This does not change v1's frozen failure-stop rule or restore
its consumed budget. Independent science/execution review applies at meaningful
execution boundaries, not every documentation edit; no model brand is mandated.

Versioned workspace policy separates immutable archive objects from refreshable
indexes. CURRENT and START_HERE derive from one status source. The archive
catalog records hashes, retained branches and worktrees without bulk deletion.
GitHub archive-tag update/deletion protection was enabled through ruleset
23830463. Historical unknown-owner branches remain retained pending review;
their existence does not block work in the canonical checkout.

## Evidence and reproducibility

Raw capture: `_runs/substrate_first_capture_20260922/capture_01/attempt_01.jsonl`,
SHA256 `c398a7c6dfffd65c6d9195bcf0fc68c388848af07c67e6e5f8946ed10a87476f`.
Live source: `09a9a31e2ab6eefcd4d3193107e8e17dad642129`.
Frozen protocol SHA256:
`d8ae529b39207a1fcb4450b163bc0a8b71955513260f0cd6959911705e0d5f35`.
Checkpoint SHA256:
`9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d`.

New append-only evidence root: `_runs/governance_diagnosis_20260922/`.
`diagnosis_01` contains independent interface/model/contact reconstruction;
`sensitivity_01` contains fixed-state command response and reward arithmetic.
Both are sealed with zero physics steps and zero new scientific attempts.
The implementation is `tools/substrate/diagnose.py` and `policy_sensitivity.py`.
The reference manifest records all fetched source blob identities and SHA256s;
the closeout archive includes these sources alongside raw diagnostics and checks.
Machine-readable diagnostic copies accompany this report.

Final qualification, exact-head reviews, zero-step preparation, original-evidence
reverification and archive member verification are recorded in this evidence
root's final acceptance/closeout records. A closed v1 campaign can only return
`VERIFIED_ZERO_STEP_CAMPAIGN_CLOSED` during preparation, never a ready-to-start
status. Repository engineering admission remains distinct from Gate 0 capability.
Clean qualification `qualification_clean_02` passed 175 checks: 34 controller
CTest cases, 86 substrate tests, 26 preflight tests and 29 tooling tests. Producer
HEAD is `d5d05586b7e67f8cad91628b02355878086c4e68`; the final prose/navigation
update deliberately reuses that receipt under fresh input and quality checks.

Pinned primary upstream sources, commit
`30e74dc507bec7a642a8c98be26081f2c6f0822d`:

- [Deployment configuration](https://github.com/wty-yy/go2_rl_gym/blob/30e74dc507bec7a642a8c98be26081f2c6f0822d/deploy/deploy_mujoco/configs/go2.yaml).
- [Deployment loop](https://github.com/wty-yy/go2_rl_gym/blob/30e74dc507bec7a642a8c98be26081f2c6f0822d/deploy/deploy_mujoco/deploy_go2.py).
- [Training task](https://github.com/wty-yy/go2_rl_gym/blob/30e74dc507bec7a642a8c98be26081f2c6f0822d/legged_gym/envs/base/legged_robot.py).
- [Go2 configuration](https://github.com/wty-yy/go2_rl_gym/blob/30e74dc507bec7a642a8c98be26081f2c6f0822d/legged_gym/envs/go2/go2_config.py).

## Next scientific decision

Before a new campaign, freeze a small, separate source-deployment reproduction
and controlled transfer matrix: establish the pinned upstream reference, then
vary command, reset and model groups separately with fixed metrics, exclusions,
budget and retained failures. Define replicates and paired perturbations before
looking at results; identical deterministic reruns establish reproducibility,
not independent statistical sample size. Acquire checkpoint training provenance
if available. No such campaign is launched or authorized by this report.
