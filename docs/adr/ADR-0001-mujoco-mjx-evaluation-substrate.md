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
