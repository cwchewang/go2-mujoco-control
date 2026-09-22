# Substrate foundation implementation

Mode: engineering foundation / offline adapter admission.

Authority: the user's 2026-09-22 request to start the project, improve existing
engineering, and establish the next research stage. This supersedes the old
integration pointer for this task; it does not retroactively change a frozen run.
Base: 02caf95b120bba07ae67a9e7b440194fb0ac8ddb.
Branch: research/substrate-foundation-20260922, canonical current worktree.
Design reference: ed3896c3f4355d6409077d61b14d6dc743d6655f, benchmark v0.
Historical control reference: e30782ad916ef1614a877d7a3c122f62682c8f19.

Deliver a tested foundation: hermetic DDS cleanup tests without relaxing
production fail-closed inspection; correct current-tick clean command selection;
explicit feedforward/PD/actuator semantics; source-locked backend dependencies;
named joint/action/observation contracts; transitive model provenance; a common
offline admission and evidence harness; MJPC and published RL backend readiness.

Preserve all historical raw records, baseline references, gains, model physics,
scientific acceptance thresholds and research classifications. Runtime changes
receive focused failure-path tests and remain unvalidated for locomotion.
The new substrate must not inherit legacy gait/WBC or silently expose terrain
truth. Known-map and proprioceptive regimes must be explicitly distinguished.

Budget: zero new locomotion/capability attempts. Builds, synthetic fixtures,
model loading/forward evaluation, policy inference on synthetic observations,
and offline solver/task smoke are engineering checks, not capability results.
No DDS locomotion pair, hardware control, training, or terrain sweep is included.
Do not call a static policy/optimizer smoke a Gate 0 pass.

Check: C++/MuJoCo CTest, DDS negative fixtures, strict-QP rejection, current-tick
success/failure/recovery, portable Python harness checks, real model/adapter
admission, reproducible dependency identities, hygiene, diff check.
Use the shared experiment lock for build/test work; preserve old build outputs.

Closeout: docs/validation/substrate_foundation_20260922/RESULTS.md with exact
source, checks, actual backend readiness, pending capability gates and next
command. Update CURRENT.md, project records and workspace START_HERE.md.
Commit/push the reviewable branch and open a draft PR; no merge or live verdict.
