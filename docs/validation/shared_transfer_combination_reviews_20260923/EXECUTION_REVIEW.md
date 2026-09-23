# Shared transfer combination v1 execution review

Reviewer identity: `gpt6-luna-max-execution-review`

Target execution HEAD: `b882a5d775ffe01e2cfae6da13c68a040d1ed7b4`

Verdict: `APPROVED`

## Readiness basis

The reviewed task config binds the protocol SHA-256, qualified protocol path,
reserved branch, and implementation diff base. Task loading requires the task
and protocol to be tracked, checks the protocol hash and positive attempt
budget, and verifies the diff base is an ancestor. `current_identity` requires
the reserved branch and a clean worktree. Preparation validates both reviews
against the actual HEAD, while preflight binds that same HEAD and branch. The
accepted review JSON therefore cannot be reused for a different HEAD.

The fresh qualification path is reproducible with the provisioned reliable
interpreter. `tools.substrate.qualify` builds the controller into
`.substrate/controller-reliable`, runs the required checks, records the clean
HEAD, and fingerprints tracked execution inputs, checkpoint, interpreter,
runtime, native build, linked libraries, CPU identity, and controller build
dependencies. The follow-up preparation revalidates that receipt and its
fingerprint. In this worktree the canonical checkpoint, pinned upstream source,
reliable interpreter, and headless admission binary are present; preparation
also hashes and snapshots the protocol's scene closure and source inputs.

Preparation holds the experiment lock, uses `zero_step_guard`, and records an
exclusive evidence bundle. It loads the model and policy, checks a policy
output, and confirms the plant step count, time, and state are unchanged. The
plant's telemetry forward calculation uses a separate `MjData`; no integration
step is taken. It rechecks HEAD, source manifest, task, input hashes, and
qualification before recording `READY_AWAITING_START`. This is sufficient for
the task's zero-step readiness boundary; this review did not run qualification
or preparation.

## Future capture controls

- The protocol freezes two same-seed episodes, the exact repeat relation, and
  `first_nonpass_stop`. Input validation requires unique cases, a matching
  attempt budget, and any repeat reference to name a preceding case. The second
  episode also requires the first to pass.
- The durable campaign claim prevents a second invocation. For each episode,
  the external attempt claim is fsynced before its first state/control row is
  emitted. An initial safety stop before that boundary remains unconsumed and
  is verified as such. Any later non-pass, execution error, or timeout stops
  the campaign; no replacement attempt is available.
- Capture rechecks exact HEAD and source inputs before, during, and after the
  run, verifies the preparation manifest around each episode, and checks the
  model physical fingerprint before integration. It validates a separate
  `START_FORMAL_CAPTURE` record bound to the prepared manifest, protocol hash,
  HEAD, and attempt budget.
- Safety is checked each tick for nonfinite state, invalid orientation,
  warnings, base contact, posture/clearance, and lateral limits. Nonfinite
  torque raises and terminates execution. Foot-ground contacts are recorded
  without being treated as a stop. Per-episode wall deadlines use both a
  Python deadline and watchdog process. A timeout fails closed; the external
  claim prevents retry.
- Repeat integrity compares hashes over qpos, qvel, target, and applied control.
  The offline verifier independently replays the source policy and PD algebra,
  rebuilds telemetry and safety classifications without integration, checks
  the stored analysis, and reconciles consumed attempts with the external
  ledger. `EvidenceRun` uses exclusive outputs, fsyncs claims, and writes a
  digest manifest last.

## Non-blocking caveats and boundary

The GitHub #147 acceptance thread could not be fetched in this environment
because network access was denied. I used the acceptance facts recorded in the
#148 design task and closeout; the current resource links are present, and the
fresh qualification and preflight remain authoritative checks of their
identity.

If the watchdog must use SIGKILL during an unresponsive native call, the run may
remain unsealed and cannot pass the normal capture verifier. Its durable
campaign/attempt claim blocks retry, so this remains a preserved failed
execution requiring inspection rather than a result or pass. A nonfinite
torque is likewise recorded as an execution error rather than a structured
`SAFETY_STOP`, but it terminates before another row or control step can run.

Approval is readiness review only and grants no capture permission. This review
used source/evidence inspection only: scientific attempts = 0; physics steps =
0. Formal capture still requires separate explicit user authorization.
