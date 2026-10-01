# ADR-0001: MuJoCo/MJX evaluation substrate and controller ownership

- **Date:** 2026-09-28
- **Status:** Accepted as the project architecture direction; implementation is
  partial.
- **Decision served:** establish a reusable evaluation foundation that lets
  evidence, rather than an assumed controller default, identify which
  locomotion failures merit new mechanisms.

## Decision

MuJoCo is the canonical evaluation physics for the current project. MuJoCo/MJX
is the intended scalable substrate direction; the shared interfaces and
scalable execution path are not yet fully implemented.

Go2 is the first testbed, not the project identity. MJPC/iLQR is a strong
gradient-based comparator, not a privileged default or source of truth.
Sampling/search, learning, and contact-implicit methods remain available when
the task and observed failure structure justify them.

Reuse mature simulator, solver, and controller infrastructure where it fits.
Scientific ownership resides in task, information, timing, and intervention
definitions; diagnostics; fair comparisons; and any new mechanism that the
evidence shows is needed. Reimplementing a mature controller from scratch is
not a contribution by itself.

## Planned boundary

The next minimal contract direction is `TaskSpec`, `ScenarioSpec`,
`InformationSpec`, `TimingSpec`, `ControllerAdapter`, and a canonical
`Evaluator` / physical-oracle boundary. The evaluator owns common physical
execution and canonical outcome evidence; the information contract states what
each controller may observe. This is a direction for later implementation,
not a universal SDK or a claim that a generic multi-controller platform
already exists.

## Current and verified state

The repository has task-specific MuJoCo Go2 assets, a reviewed schema-2 public
RL execution/analyzer/verifier path, and static MJPC/iLQG admission utilities.
These are executable components, not yet the shared multi-controller contract
above. In particular, static MJPC admission is not a closed-loop locomotion
comparison.

The verified #189 conclusions and their semantic corrections are recorded in
the [versioned erratum](../validation/rl_capability_map_successor_20260924/ERRATUM_20260928.md).
They do not yet establish a cross-controller bottleneck or a paper topic.

## First concrete controller boundary

The first implemented adapter boundary keeps the evaluation plant direct-torque.
A controller that natively emits joint-position targets must declare and validate
its source actuator semantics before entering the evaluator. For an affine
position-PD source model, the adapter extracts joint order, target limits, Kp
and Kd, clips the source position target exactly as the source model would,
then emits the existing TorqueCommand contract. The canonical plant still
receives torque; source-controller actuator defaults cannot silently redefine
evaluation physics.

The extractor fails closed unless MuJoCo reports an affine joint actuator with
unit transmission, fixed positive gain, bias [0, -Kp, -Kd, ...], finite
control range, and no secondary force limit. This specifically prevents a
biasprm declaration with a non-affine biastype from being treated as PD.

## First concrete information boundary

The canonical plant now exposes a simulator-handle-free WholeBodyState packet for
model-based controllers: base world position, base world linear velocity, body
quaternion, body-frame angular velocity, named joint position/velocity, and
simulation time. The existing RL path remains proprioceptive and does not receive
the added base position or linear velocity fields.

Controller comparison must therefore record the information regime explicitly.
Sharing the evaluation plant does not imply that a learned proprioceptive policy
and a model-based predictive controller receive identical observations.

## Explicit information and timing specs

InformationSpec records the dynamic observation regime, declared predictive-model
access, fixed observation latency, and noise model. Delivered observations carry
sample, availability, and controller times so observation age is evidence rather
than an implicit assumption. Noise other than none is rejected until implemented.

TimingSpec distinguishes offline_unbounded computation from real_time computation.
The former cannot claim a solve budget or timeout behavior. Real-time semantics
require a solve budget no larger than the slow control/policy-update period and
an explicit overrun policy (hold_previous or fail). A separate
feedback_period_s defaults to the control period, preserving existing controller
semantics, but can explicitly represent faster feedback evaluation between slow
policy/planning updates. Physics, feedback, and control periods must have exact
integer tick relationships. Output is held between feedback ticks. This contract
does not by itself claim that the existing synchronous episode runner emulates
real-time plant evolution during solver computation.

## Explicit task, scenario, and evaluator boundary

TaskSpec owns command schedule, horizon, measurement window, support semantics,
physical stop conditions, success thresholds, and the named longitudinal metric.
ScenarioSpec owns scene/reset identity, an optional compiled-physics fingerprint,
and fail-closed expectations for implemented interventions. Effective contact friction and dimensionality expectations are checked against
active MuJoCo contact records after model compilation/forwarding, rather than
inferred from one geom's XML or compiled fields. Verification fails closed when
the expected contact pair is not active.

CanonicalEvaluator consumes raw state/contact/warning evidence plus TaskSpec. It
recomputes physical failures, endpoint progress, tracking error, and mandatory
support completion independently of controller-reported failure/success labels.
The sealed runner and analyzer remain unchanged; legacy protocol fields can be
mapped into the new specs for prospective aligned comparisons.

## First native MJPC controller integration

The pinned author Go2 MJPC implementation now has a persistent headless process
surface for prospective shared evaluation. Its binary is sealed against native
source/build inputs. It consumes WholeBodyState in the source joint order,
returns joint-position targets, and is wrapped by PositionTargetControllerAdapter
before any torque reaches the canonical plant.

The pinned task source is validated in its actual nominal form: gain/bias encode
position-PD intent while biastype is mjBIAS_NONE. The controller fails closed on
any drift, then applies mjBIAS_AFFINE only to its private planning-model copy.
The canonical direct-torque evaluation plant is never modified. Manual/Trot Walk
selection and iLQG current-state feedback are explicit.

A zero-canonical-step engineering smoke confirmed one complete
state -> native MJPC -> q_des -> shared PD -> canonical torque path with finite
output and no canonical plant advancement. This is wiring evidence only. It does
not establish locomotion performance or real-time feasibility; those require a
separate prospective aligned evaluation under the shared task/scenario/information/
timing contracts.

## Native MJPC planning / feedback cadence

The shared native MJPC bridge now separates policy replanning from current-state
iLQG feedback. The process protocol receives an explicit replan flag.
OptimizePolicy runs only on declared planning ticks; ActionFromPolicy receives the
current WholeBodyState on every declared feedback tick. Controller commands are
sampled on planning ticks and held between replans, so a high-rate feedback call
cannot silently reset the upstream Walk target.

The audited author deployment uses a 2 ms Unitree LowCmd/PD write thread but a
separate asynchronous MJPC action loop. Therefore a 2 ms MJPC feedback period in
the canonical evaluator is explicitly a prospective shared adaptation, not a
claim about the author's native feedback frequency. The first prospective anchor
uses offline_unbounded compute semantics until timing evidence supports a
real-time claim.
