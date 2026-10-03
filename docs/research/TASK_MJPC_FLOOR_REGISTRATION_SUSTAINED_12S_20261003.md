# MJPC floor registration sustained 12-second diagnostic v1

## Purpose and decision

The two sealed floor-corrected 3-second repeats both reached 1500 steps and passed canonical replay, but the first torque-saturation tick differed by 860 ticks (0.59 s versus 2.31 s). Post-hoc traces show only one isolated 2 ms saturation sample in repeat 1 and two isolated samples in repeat 2. This follow-up asks whether that sparse clipping remains isolated or becomes sustained during one 12-second run.

This is a one-arm engineering/safety diagnostic. It can describe one frozen-condition trajectory and its actuator-clamp burden. It cannot establish repeatability, robustness, a locomotion baseline, or that floor registration caused the prior timing difference. A horizon result supports only completion under this one condition; a safety stop is retained as the observed outcome.

## Frozen setup and sole task change

Reuse the successful floor-corrected runtime and all 3-second settings: private task floor z=0 (the previous private value was -0.01 m), unchanged canonical model/home reset, mass, damping, contact smoothing, PD 60/5, torque limits, cost, Manual Trot gait, 0.35 s planner horizon, 10 ms planner dt, 20 ms replan cadence, 2 ms feedback, one-sided 1e-6 finite differences, derivative_skip=0, four workers, and the duplicate-FD fix. Keep xfrc_std=0, with no seed or warmstart change. Keep the same 1 m/s body-forward command, 50 zero-command ticks and 100-tick ramp. The only task change is horizon: 6000 canonical ticks (12 s). Safety/replay thresholds remain those already encoded by the frozen TaskSpec.

Do not change the 200-tick repeatability criterion from the closed two-run task or use it to label this one-arm task. This 12-second task has no saturation pass/fail threshold. Report saturation burden for every joint from stored pre-clamp torque and actuator ctrlrange.

## Resource and stop bounds

- One scientific attempt, one capture controller process, no retry or replacement.
- At most 6000 canonical physics steps and 600 optimizer/replan calls.
- At most 4096 private-step upper-bound units per replan; total observed/reserved private upper bound at most 2,457,600.
- 300 s wall-clock timeout for capture.
- One separate native process maximum for the zero-step construction handshake; it is closed before any later capture.
- Stop on first canonical safety failure, transport/native warning, identity/evidence failure, wall timeout, or private-budget exceedance. Preserve raw and partial evidence; classify interrupted/broken evidence as invalid. No retry.

## Required report

Record terminal classification, step/time, safety-stop reason, canonical replay, command, and source/runtime identities. For all 12 named actuators report peak absolute requested torque, maximum amount beyond ctrlrange, saturated action tick count and percentage of action samples, longest consecutive saturated ticks, and every start/end tick and duration. Also report total saturated action ticks, total saturated joint-ticks, warning count, and stderr bytes. Do not turn these descriptive quantities into a post-hoc acceptance threshold.

## Preparation and execution boundary

Protocol: tools/substrate/protocols/mjpc_floor_registration_sustained_12s_v1.json. The real entry is the existing floor-registration prepare/handshake/capture module with this protocol id; capture uses the shared aligned episode runner and canonical replay. After authorized capture, its offline analyze command verifies the sealed manifest and writes the per-joint report without stepping physics.

Prepare the packet and run the zero-step construction handshake only. The offline analyzer is not run until a future capture exists. The handshake may construct the canonical model and start one native controller to verify readiness, but must record zero canonical physics steps, optimizer calls and scientific attempts. It is not a capture authorization. Capture remains NOT AUTHORIZED until fresh exact-head science and execution reviews and a user start record bind the resulting packet, manifest, protocol hash and one-attempt limit.

For the final exact HEAD, prepare at _runs/mjpc_floor_registration_sustained_12s_prepared_20261003_r3 and run the zero-step handshake at _runs/mjpc_floor_registration_sustained_12s_handshake_20261003_r3. Preserve earlier r1/r2 preparation and handshake records; never reuse or overwrite sealed 3-second or R4 evidence.
