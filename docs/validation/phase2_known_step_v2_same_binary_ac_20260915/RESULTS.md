# Same-binary V2 A/C closeout

Date: 2026-09-15
Primary classification: PROTOCOL_FAILURE
Reason code: A_BASELINE_GATE_FAILED.

Exactly one fresh A run was consumed at domain 231. No retry was made. A produced 4880 lockstep rows and PAIRED_HIGHSTATE_SUMMARY cycles=4879 validation_failures=0 async_fallbacks=0. Runtime statuses are {"analysis_status": "0", "completion_status": "1", "controller_status": "0", "dynamics_status": "0", "ground_truth_status": "0", "quality_status": "0", "safety_status": "1"}; safety/completion and hard-posture gates therefore failed. Hard markers: TROT HARD SAFETY LIMIT REACHED, TROT HARD POSTURE LIMIT, EMERGENCY_STOP.

C was not launched because the task requires A baseline/protocol health before C. No simulator/controller rerun, tuning, or follow-up experiment was made. Frozen V1 B, A raw hashes, scene, runner, captured runtime metadata, and pre-live tests are recorded in provenance.csv and analysis.json.
