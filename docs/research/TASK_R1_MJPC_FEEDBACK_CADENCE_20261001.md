# R1 MJPC planning / feedback cadence repair — 2026-10-01

Goal: make the shared native MJPC bridge represent slow policy replanning and
higher-rate current-state iLQG feedback as separate timing semantics before any
prospective canonical closed-loop anchor.

Scope:
- extend TimingSpec with feedback_period_s, defaulting to control_period_s for
  backward compatibility;
- require physics -> feedback -> control/planning periods to have exact integer
  tick relationships;
- make the native protocol carry an explicit replan flag;
- run OptimizePolicy only on replan ticks;
- run ActionFromPolicy with current state on every feedback tick;
- sample controller command only on replan ticks and hold that sampled command
  between replans;
- separately expose planning and action compute time;
- keep the canonical plant untouched.

Source-timing note: the audited author deployment commit
ba86aa7d4c3f0efe7fee32c2b6d259d4a6d865df writes Unitree LowCmd at 2 ms, while
MJPC action is updated by a separate asynchronous loop. Therefore the 2 ms
feedback cadence used by this shared bridge is a prospective canonical
adaptation, not a claim that the author's deployment natively used 500 Hz
TV-LQR feedback.

This is infrastructure only. Scientific attempts: 0. Canonical physics stepping,
performance classification, controller ranking, tuning, and Gate 0 claims are
out of scope.
