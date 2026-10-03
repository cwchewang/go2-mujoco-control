# Floor registration diagnostic preparation

Status: IMPLEMENTED / PRECHECK IN PROGRESS; no capture authorized or run.

This package prepares one fresh-process, one-attempt 3 s (1500 canonical-step maximum) floor-only diagnostic. It changes private task_flat.xml floor z from -0.01 m to 0 m. Canonical physics and the other planner/controller configuration stay frozen to R4. The R4 safety-stop record remains sealed and is only a comparator.

The R4 evidence precheck binds raw/prediction/outcome/attempt hashes before packet construction. At tick 20 (0.04 s), actual support labels are FR/FL/RR/RL while the selected nominal state has no reconstructed foot-contact label; its qpos max difference from actual is 0.000868. The labels are from selected-state forward reconstruction on the smoothed private model, not a future rollout. First PD saturation is tick 105 (0.21 s), after this contact record. R4 ended at tick 260 / 0.52 s on nonfoot_contact and is never retried.

The new floor0 diagnostic mode only adjusts the private-floor assertion and model identity label while retaining the existing 4096-step-per-replan reservation and 614400 total upper bound. It records selected-state contacts as reconstruction evidence. The machine diff checker verifies the source XML tree differs only at floor.pos.z and compares the sealed runtime closure with R4, allowing only the binary/build provenance, that private XML, and its identity sidecar to differ. Canonical model bytes and physical fingerprint are separately bound.

Preparation and controller-construction handshake must show zero canonical steps, zero optimizer calls, zero scientific attempts, one native controller process, the expected four workers / 36 knots / 10 ms planner step, and no startup warnings. Actual capture requires fresh exact-head science and execution reviews plus a protocol and prepared-manifest bound user start authorization; this packet does not provide that authorization.

Focused local precheck: XML diff accept/reject tests and Python syntax checks. The live status and exact packet/handshake hashes belong in the sealed _runs evidence bundle once prepared. A single result can show a floor-registration effect under this frozen condition; it cannot identify the full failure mechanism, establish a reusable baseline, or make a novelty claim.
