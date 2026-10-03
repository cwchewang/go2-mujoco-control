# MJPC Ground/IPC hardening engineering acceptance

Status: PRECHECK PASS / LIVE V2 NOT_RUN / SCIENTIFIC ATTEMPTS 0.

The inherited repair replaces only the exact source-pinned Ground fatal miss block with a planner-private BADQPOS warning. CheckWarnings then rejects that rollout. MuJoCo warnings use stderr, and native ready metadata declares both policies. The canonical model, reset, torque contract, controller source task, timing, optimizer parameters and engineering thresholds remain frozen.

Actual source-bound native Ground regression passed: ordinary plane query unchanged; missed downward ray increments BADQPOS; CheckWarnings rejects it; data time remains zero; the fixture calls no integrator. Release build and sealed identity passed. Actual native IPC at the canonical reset returned finite resolved torque (max 0.10329455263302645 Nm; no saturated motors), canonical steps=0/time=0; an unsupported lateral command returned structured JSON failure; the process survived, reset, and returned finite output again.

Full offline substrate discovery: 175 tests PASS. Project aggregate development qualification: ENGINEERING_ADMITTED (controller CMake/CTest, substrate, preflight, tooling, quality, diff and actual RL/MJPC offline admission). Full pinned Ruff lint/format PASS. The earlier broad test attempt exposed two nested test-fixture locks; fixtures now explicitly use their own temporary locks while the outer global experiment lock protects the complete test invocation. Production experiment locking is unchanged.

Preserved engineering harness failure: an underground initial state did not guarantee a Ground miss because private planning could recover; that assertion was withdrawn, not used as evidence. Exact Ground behavior is covered by the native zero-integration fixture. All failed and successful raw logs remain in the evidence root recorded in acceptance.json.

Reproduction: bootstrap --build; cmake --build .substrate/headless-reliable --target go2_mjpc_ground_test; ctest --test-dir .substrate/headless-reliable --output-on-failure; reliable Python full substrate unittest discovery under flock; pinned development quality --style; reliable Python tools.substrate.qualify with a fresh output (clean HEAD, no --development); tools.substrate.verify; then separate v2 zero-step prepare. Hold /tmp/go2_mujoco_experiment.lock throughout each build/test command; bootstrap/qualify/prepare already acquire it internally.

The immutable clean-head qualification receipt and exact-head v2 preparation are generated after committing these inputs. Their raw paths and producer HEAD must be supplied to independent review. This repair changes how invalid private planner rollouts are handled; trajectory neutrality and scientific relevance require independent review. Engineering PASS is not locomotion performance, controller ranking, real-time evidence, or Gate 0 completion. v1 remains permanently closed.
