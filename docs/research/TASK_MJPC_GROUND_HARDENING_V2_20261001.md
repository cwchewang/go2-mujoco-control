# MJPC Ground and IPC hardening, followed by v2 preparation

Mode: engineering only. Parent: ede49cd91cae1f1c96a0739b85cc54c10024ee1d.
Owner: Base delegated Go2 engineering agent.
Authorization: user 2026-10-01 21:42 +08:00: take responsibility for this next Go2 step.
Purpose: restore an auditable native planner/IPC boundary after the sealed v1 tick-140 infrastructure stop, before considering another aligned integration capture.

Preserve the existing work on infra/mjpc-ground-hardening-v2-20261001. Change only pinned Ground miss handling, diagnostic transport, explicit ready metadata, source-bound build inputs and their engineering tests. Canonical scene/reset/actuator semantics, source controller task, planner parameters and research question remain as in v1. Source Ground failure becomes a planner-private rollout warning/failure; it must not become a successful canonical sample.

Acceptance: pinned native Release build and sealed identity; portable regression tests; actual zero-canonical-step state -> native planner -> target -> resolved torque smoke; malformed/divergent input must preserve JSON framing and be rejected; aggregate offline qualification and hygiene/style checks. Every build/test holds /tmp/go2_mujoco_experiment.lock. Native private planning rollouts are permitted; canonical mj_step/mj_step1/mj_step2 are guarded and plant time/steps must remain zero. Preserve fresh logs, including failures.

After development acceptance, commit the repair and evidence; perform clean-head offline qualification. Prepare a separately named v2 protocol and exact-head review packet with physics_step_authorized=false. v1 is permanently closed and cannot be retried. No live physics, push, merge, deployment or external reviewer dispatch is authorized here. New live v2 requires independent relevant review, fresh exact-head preparation and explicit START.

Stop on lock contention or concurrent source changes; preserve both owners' work. Engineering PASS does not establish controller ranking, locomotion performance, Gate 0 completion or a scientific result.
