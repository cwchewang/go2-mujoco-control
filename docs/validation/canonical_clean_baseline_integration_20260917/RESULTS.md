# Canonical clean-baseline integration closeout

Date: `2026-09-17`

Task commit: `7ab6fbf6e08e57d0d6d1b536ab7870887ac602e7`

Exact main parent: `041c36c499ff24ab6c8edf74fa6283e0ba923db6`

Mode: `engineering-correctness / no-live / canonicalization`

Proposed Luna classification: `CANONICAL_CLEAN_BASELINE_READY`

## FACTS

- No simulator/controller pair or locomotion run was launched. Raw `_runs`
  evidence was not modified.
- The accepted reference commits were inspected as trees and evidence sources,
  not merged or cherry-picked as history:
  - P0 clean-baseline source/reference: `cdb0888d02c195935a88d9c404fb4d45c5b0ac1a`;
  - accepted DDS root-fix result: `2eb92bc62be6fba2dee26ac9229520d8835c6246`;
  - validated flat result: `8b189c1bd7dab761c014f1db98e1223f3d73120d`;
  - exact validated live candidate/wrapper source: `0009b5fbd1e962e38135922da61245a99b522aab`.
- The port is limited to the clean controller seams, focused tests, tracked DDS
  runtime/probe/exact-source plumbing, build-root portability, and canonical
  documentation. Historical task documents, intermediate recovery scaffolds,
  and full historical analysis were not imported.
- Clean controller implementation is in:
  `example/cpp/wbc/clean_baseline.h`,
  `example/cpp/kinematics/go2_inverse_kinematics.h`,
  `example/cpp/wbc/inverse_dynamics_wbc.h`,
  `example/cpp/trot/trot_experiment_gait.cpp`,
  `example/cpp/trot/trot_experiment_wbc.cpp`, and
  `example/cpp/trot/trot_experiment_control.cpp`.
- Canonical runtime implementation is in
  `example/cpp/scripts/dds_runtime.sh`, `run_trot.sh`,
  `run_trot_exact_source.sh`, `dds_runtime_root_smoke.sh`, and the read-only
  `apps/dds_lowstate_probe.cpp`; `example/cpp/CMakeLists.txt` and
  `simulate/CMakeLists.txt` accept explicit SDK roots.
- Accepted flat evidence remains externally auditable at the referenced
  closeout and host-record paths. Its frozen command and core result are
  preserved: `64/64` cycles, nominal `0.1516666667 m/s`, measured OLS speed
  about `0.153806 m/s`, and zero primary rejection/safety counts.
- Validation completed without live execution: full controller CTest `34/34`,
  including `test_dds_runtime`, `test_clean_baseline`,
  `test_go2_inverse_kinematics`, `test_inverse_dynamics_wbc`,
  `test_terrain_interfaces`, and `test_lean_route_guard`; the simulator
  `test_lockstep` unit test also passed. The simulator-launch integration CTest
  was excluded by the no-live task boundary.
- `bash -n` passed for all canonical shell scripts and `git diff --check`
  passed. The required remote refresh was attempted but the linked worktree’s
  Git metadata rejected `FETCH_HEAD` writes as read-only; the supplied exact
  task ref, `HEAD`, `origin/main`, and accepted reference refs were verified
  read-only without changing Git metadata.

## INVARIANT AUDIT

1. **Planner/foot target identity — PASS.** Clean gait target construction
   calls `ResolveFootTargetsToJointPositions` with the requested targets and
   does not call the legacy clamped solver. The direct-IK rejection and
   non-mutation cases pass in `test_go2_inverse_kinematics` and
   `test_clean_baseline`.
2. **Authoritative joint limits — PASS.** Clean acceptance checks the Go2
   ranges represented in `unitree_robots/go2/go2.xml`, including distinct front
   and rear thigh ranges, after direct IK. The joint-range-invalid fixture is
   rejected without projection.
3. **Strict optimizer acceptance — PASS.** `require_qp_acceptance` rejects a
   failed constrained solve before its iterate can become output. The dense-QP
   rejection fixture and strict ID-WBC test pass; clean runtime failure clears
   solver/mapping acceptance and cannot reuse a stale result.
4. **Correct swing acceleration — PASS.** `AddSwingFootAccelerationTask`
   includes `Jdot*qdot` in the acceleration residual. The focused swing test
   checks both the gradient term and Hessian.
5. **No post-optimizer actuation overlays — PASS.** Clean
   `WriteMotorCommands` returns through the accepted torque plus the explicit
   final finite/ramp/absolute envelope. Legacy force, lean, Cartesian, and
   sprint overlays are enclosed by `!params_.clean_baseline`.
6. **Final command identity — PASS.** Clean LowCmd torque is sourced from the
   mapped accepted ID-WBC torque and passed only to
   `ApplyFinalTorqueSafetyEnvelope`; failed WBC uses a zero-feedforward safe
   hold rather than a legacy command path.
7. **Fail closed — PASS.** Direct target failure requests the existing stop
   sequence, strict WBC failure disables primary output, and clean command
   writing emits a zero-feedforward hold instead of falling back to legacy
   torque/position overlays. The route and contract tests cover these seams.
8. **Cartesian-world incompatibility — PASS.** CLI validation rejects
   `--clean-baseline --cartesian-world`, and `test_lean_route_guard` passes.

## LEGACY ISOLATION

- `AllLegInverseKinematicsClamped` and `ClampFootToHipWorkspace` remain only
  for compatibility and are explicitly labeled legacy. The clean target branch
  precedes both legacy paths and uses a const requested-target boundary.
- Cartesian-world is a separate CLI route and is fail-closed against clean
  mode. Its post-WBC behavior cannot be reached after clean mode is selected.
- Terrain observation remains sensor-only in the maintained runtime. The
  `TerrainPlannerConfig` actuation boundary now rejects any actuation-capable
  planner unless `clean_baseline_contract` is explicitly enabled; its focused
  test proves the rejection and the opt-in contract path.
- The legacy helpers were not deleted because existing compatibility callers
  and historical tests still depend on them. They are not the clean extension
  seam or default Phase-2 route.

## CANONICAL SURFACE

Future Phase-2 work should start from `CURRENT.md`, use the tracked DDS layer
through `example/cpp/scripts/run_trot.sh`, and extend only this contract:

`gait/foothold + predicted body/hip state -> clean swing planner -> exact foot targets -> direct IK feasibility -> strict WBC -> final safety envelope`

The clean controller entry is `real_trot_go2 ... --clean-baseline`; Cartesian
world and legacy terrain-actuation options remain separate or retired. Exact
source builds use `simulate/CMakeLists.txt` with `-DMUJOCO_ROOT` and
`example/cpp/CMakeLists.txt` with `-DGO2_MUJOCO_ROOT`. The read-only DDS probe
is `dds_lowstate_probe --domain-id N --interface lo`.

## LUNA INTERPRETATION

`CANONICAL_CLEAN_BASELINE_READY` is proposed because the minimal accepted clean
implementation is coherently integrated on current-main ancestry, all eight
control invariants have source and focused-test evidence, the accepted flat and
DDS records remain referenced with hashes, and legacy clamp/overlay entry is
explicitly isolated. This is an offline integration result. It does not claim
new repeatability or authorize a live run; repeatability remains a later task
after protected-main integration.
