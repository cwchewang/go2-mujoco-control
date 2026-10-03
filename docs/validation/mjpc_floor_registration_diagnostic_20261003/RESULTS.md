# Floor registration diagnostic preparation

Status: PRECHECK PASS / AWAITING INDEPENDENT REVIEW; formal capture NOT_RUN.

This package prepares one fresh-process, one-attempt 3 s (1500 canonical-step maximum) floor-only diagnostic. It changes private task_flat.xml floor z from -0.01 m to 0 m. Canonical physics and all other planner/controller settings stay frozen to R4. R4 remains sealed and is only a comparator.

The sealed R4 evidence precheck binds the raw, prediction, outcome and attempt records. At tick 20 (0.04 s), actual support labels are FR/FL/RR/RL while the selected nominal state has no reconstructed foot-contact label; its qpos maximum difference from actual is 0.000868. These labels come from forward reconstruction of the selected state on the smoothed private model; they are not future rollout predictions. First PD torque saturation occurred at tick 105 (0.21 s), after the tick-20 contact record. R4 stopped at tick 260 / 0.52 s on nonfoot_contact. It must never be rerun.

The dedicated floor0 diagnostic mode preserves the fixed-index controller, 4096-per-replan reservation and 614400 total private-step cap while recording selected-state contact reconstruction under the correct floor0 model identity. The prepared packet machine-checks that private task XML differs only at floor.pos.z, that the canonical model is byte-identical, and that the runtime closure differs from R4 only in the diagnostic binary/build provenance, private task XML and its identity sidecar.

The real native-controller construction handshake passed before any episode: one native process, four workers, 36 knots at 10 ms; zero canonical steps, optimizer calls and scientific attempts; zero stderr; no prediction or FD trace output. The handshake only established construction/readiness. It did not run an optimizer call or physics step.

Three focused Python tests cover the exact one-attempt/one-intervention protocol and XML diff acceptance/rejection. The changed Python files pass Ruff checks and syntax compilation. Full repository style checking still reports preexisting findings in untouched files.

The prepared packet awaits independent exact-head science and execution reviews. Formal capture also requires a separate one-attempt, packet/manifest-bound user start authorization. This single run can show whether floor registration changes this frozen controller/task outcome; it cannot establish that floor is the sole cause, qualify a reusable locomotion baseline, estimate robustness or support a novelty claim. Packet and construction evidence are sealed under _runs/mjpc_floor_registration_*.
