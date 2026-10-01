# R1 native MJPC shared adapter — engineering closeout

Status: ENGINEERING PASS / SCIENTIFIC ATTEMPTS 0.

The project now has a persistent headless bridge to the pinned author Go2 MJPC implementation at e00c47a5adb9856af2e0f24231bb3a60d5be23c4. It consumes WholeBodyState, runs the source QuadrupedFlat+iLQG problem, returns joint-position targets, and passes them through the shared PositionTargetControllerAdapter into canonical direct-torque semantics.

Source compatibility is explicit. The pinned task has gain 60 and bias 0 -60 -5 while biastype is mjBIAS_NONE. The controller validates that nominal source fact before changing only its private planning-model copy to mjBIAS_AFFINE. The canonical evaluation plant is not modified. Manual/Trot Walk selection and current-agent-state iLQG feedback are explicit.

The successful zero-step smoke was rerun on tracked bridge code commit ba12f3bd7ad376eb92395018c045c9e21ab1ac72 after the selection-parameter repair was committed.

A sealed Release controller binary was built from the pinned source. Final observed binary SHA-256:
56e631591c60f15630cee76dd5e24386e8ce1f27ed8d5e5c2753cff4bf0ab1ac

Zero-canonical-step integration smoke:
- command: vx=1.0 m/s, vy=0, wz=0;
- canonical plant steps: 0;
- canonical plant time: 0.0 s;
- planner compute time: 0.029837 s in the final exact-code smoke;
- iLQG reported cost: 0.08976081533117637;
- resolved canonical torque: finite;
- saturated motors: 0;
- maximum absolute resolved torque: 0.10329455263302645 Nm.

The earlier startup probe failed before any controller action because the direct bridge incorrectly used ParameterIndex for selection parameters such as Gait switch. The implementation was corrected to mirror upstream Agent selection indexing. The preserved raw MuJoCo startup log remains under the ignored engineering run directory and was not deleted.

Regression evidence:
- 63 focused portable contract tests passed;
- broader system-Python run passed 105 tests; the sole loader error was test_policy_runtime importing Torch from an interpreter where Torch is intentionally absent;
- rerun in the reliable runtime passed 41 policy/baseline tests;
- 9 native MuJoCo boundary/scenario tests passed;
- Ruff and diff checks passed;
- sealed controller identity re-verified against the pinned MJPC checkout;
- CTest reported no registered tests in this native build directory, not a test failure.

Interpretation is strictly bounded: this proves the mature native MJPC controller can be wired into the shared controller/action contracts without advancing or redefining canonical evaluation physics. It does not prove locomotion performance, real-time feasibility, superiority to RL, or a scientific bottleneck. The next step is a separate prospective aligned closed-loop anchor governed by TaskSpec, ScenarioSpec, InformationSpec, TimingSpec and CanonicalEvaluator.
