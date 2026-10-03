# Private floor registration diagnostic

Mode: PREPARATION / NOT_RUN. One fresh-process, one-arm, bounded diagnostic.
Parent evidence: sealed R4 at HEAD `6e829bed5dcd4a8b4dc6b575f70b1a5be422cb78`.
Decision: determine whether changing only the private predictor floor from z=-0.01 m to z=0 m changes the early selected-state contact mismatch or safety-stop trajectory under the existing R4 controller/task.

## Intervention and frozen inputs

The only physical-model intervention is `private_task_flat.floor.pos.z: -0.01 -> 0.0`. The canonical evaluation model remains byte-identical and has floor z=0. Preserve the home reset, robot mass/inertia, joint damping, contact smoothing, PD60/5, torque limits, objective and gait weights, Trot/Manual gait, command protocol, horizon, planner and feedback cadence, four workers, and fixed FD-index patch. Do not alter warm starts.

The controller uses the R4 fixed-index implementation. A narrow `floor0` instrumentation mode keeps the 4096-per-replan upper-bound reservation and 614400 total private-step cap while recording selected nominal states and reconstructed contacts with the accurate model identity. It does not change the planner's control calculations. The R4 runtime closure, source/model assets, binary/build inputs, protocol and current code are hashed into the packet.

One attempt is permitted, up to 1500 canonical steps / 3.0 seconds, no more than 150 replan calls, a 300-second wall ceiling, and a 614400 private-step upper bound. Stop on the first safety, execution, warning, identity, evidence, or budget failure; never retry. The next capture remains NOT_RUN until fresh independent exact-head science/execution reviews and a separate one-attempt, packet-bound user start authorization exist.

## Comparison and interpretation

Compare the one new episode with sealed R4 only over the shared input prefix. R4 stopped at tick 260 / 0.52 s for `nonfoot_contact`; it is permanently closed and must not be rerun. In R4, actual tick-20 supports were all four feet while the selected nominal state had no reconstructed foot contact, with max qpos difference 0.000868. Those labels came from forward reconstruction of a selected state on the smoothed private model; they are not future rollout predictions. First PD torque saturation occurred at tick 105 / 0.21 s, later than the tick-20 contact record.

If the floor-only arm changes early reconstructed contact labels or the safety trajectory, floor registration is relevant under this fixed task; one trial cannot establish that it is the sole cause or a stable baseline. If the stop is unchanged, the floor-only change is insufficient here; it does not rule out contact smoothing, mass/damping, gait/task mismatch, planner behavior, or later saturation. A horizon reached is a bounded engineering observation, not a useful-baseline qualification, robustness estimate, or research novelty claim. No old R4 evidence is modified and no claim about the old A binary is made.

## Preparation interface

After packet review and explicit authorization, the prepared module's `capture` command is the only one-shot entry. Preparation and the real-controller construction handshake must record zero canonical steps, zero optimizer calls, and zero scientific attempts. The handshake must produce the expected controller-ready identity and loaded-library closure without a warning or optimizer trace.
