# MJPC adaptation diagnostic v1: preparation

Status: IMPLEMENTED / PRECHECK; formal A and B NOT_RUN.
Third-stage topic diagnosis remains ACTIVE / OPEN.

The increment adds only two bounded independent one-arm diagnostics, private
prediction evidence and exact rollout/FD-upper-bound accounting. Corrected B
changes floor registration and post-PD torque limits while preserving source
position references, PD60/5, mass/damping/contact smoothing, cost/gait and clocks.
12 named joints/actuators and23 collision geometries, including unnamed geometry,
map uniquely by body/shape/position/quaternion. Body frames and unit gear agree.
Native zero-integration tests verify affine PD clamp placement and150/151
replan admission. Both XML models already have impratio100 and use pinned Go2.

Mass+0.6kg changes predicted load distribution; damping2.0 versus0.1 adds
same-state passive force difference-1.9*qvel. Floor-1cm changes contact gap/
normal response. Solimp differences change compliant forces and derivatives.
Mass/damping are upstream choices; contact smoothing is deliberate. Their
causal role remains unresolved. B narrows the prior broad proposal to proven
frame/force mappings; two changes together identify only a package effect.
A must first reproduce the sealed stop or B remains NOT_RUN.

Private budget: two groups of10 candidate rollouts each at most35 steps give700.
Pinned skip0 derivative scheduling makes37 calls, including repeated T-2.
MuJoCo3.3.6 one-sided Euler transitionFD uses at most49 steps for each full
Jacobian and37 for sensor-only terminal: upper1801. Total2501 per solve is below
reserved4096;150 reservations cap614400 per arm. Wrappers count rollout calls
exactly and charge observed FD calls before invoking MuJoCo.
[MuJoCo derivative source](https://github.com/google-deepmind/mujoco/blob/3.3.6/src/engine/engine_derivative_fd.c)
supports the bound. Guards reject dimension/integrator/FD/configuration drift.

Records contain selected policy/candidate identity, anchor, optimization model
ID, nominal knot state/action and reconstructed contacts on a separate smoothed
copy. Live planner/task state is not replayed or stepped for recording.
Actual2ms applied target/torque remains in canonical raw; closed-loop versus
nominal prediction is not a pure model-error metric.

Development precheck:3 native zero-integration tests and23 focused Python checks
passed. One bounded native smoke had0 canonical steps/0 scientific attempts and
one optimizer call:700 rollout steps, FD upper1801, reserved4096; initial q_des
difference from sealed original0. This does not establish full-episode neutrality.
Current-input qualification and both prepared manifests will be bound in one
handoff packet before review.

Science direction attestation turn01a0fcef-18b2-753f-b7ef-ee6ca2ba89b6 guides the
increment; it is NOT an exact-head implementation approval. Formal capture
requires new genuine exact-head science/execution verdicts. All old evidence
remains unchanged; new formal attempts/canonical steps are0.
