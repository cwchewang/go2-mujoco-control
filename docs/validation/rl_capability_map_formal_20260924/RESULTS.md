# RL capability-map formal capture results — 2026-09-24

## Campaign identity and status

- Protocol: schema-2 `rl-capability-map-v1`, SHA-256 `0eda1a046d4d9c456a3ee5a281cc183eaf188b0ff9db9fe0767bc5f6011dc803`.
- Capture HEAD: `0de58642d110067ba6622fa44287710cb170dd2d` (detached Praxis worktree; issue #178).
- Campaign status: **FAILED / INCOMPLETE** (`EXECUTION_OR_EVIDENCE_FAILURE`). Exactly one capture command was issued. It consumed the `flat_reference` attempt and returned `TypeError: Object of type bool is not JSON serializable` while finalizing that case. No capture retry was made.
- The permanent ledger records one `flat_reference` claim. The other eight cases have no attempt claim and remain `NOT_RUN`.

## Readiness gates

The exact-head owner precheck passed. At the launch HEAD, before this closeout file was added, the diff from reviewed base `de5e396331e01576a2bfd0fe1ccdf662835aa15a` contained only the specified preflight integration fixture repair and this task prose; the protocol bytes were unchanged. All 27 preflight integration tests and all 8 targeted `CurrentIdentityTests` passed. The two original r2 reviews approved the reviewed base, and the prescribed review inheritance bundle validated against the launch HEAD.

Clean non-development qualification passed as `ENGINEERING_ADMITTED`. Schema-2 preparation returned `READY_AWAITING_START` with `physics_steps=0`, nine model records, and 75 snapshotted source inputs. The start authorization bound the exact HEAD, protocol hash, prepared-manifest hash, and `max_attempts=9`, recording the user instruction `好，继续`. The final capture-boundary checks passed immediately before capture.

## Case outcomes

| Case | Recorded capture outcome | Offline raw-trace audit | Result |
|---|---|---|---|
| `flat_reference` | `ERROR` — `TypeError: Object of type bool is not JSON serializable`; attempt consumed | `PASS`; sealed digest reproduced; zero physics steps | Full 6,000-tick trace and ordinary flat gates pass offline, but capture finalization failed. |
| `flat_half_speed` | `NOT_RUN` | Not run | Capture stopped on the `flat_reference` execution/evidence error. |
| `flat_reverse_probe` | `NOT_RUN` | Not run | Capture stopped on the `flat_reference` execution/evidence error. |
| `flat_lateral_probe` | `NOT_RUN` | Not run | Capture stopped on the `flat_reference` execution/evidence error. |
| `flat_yaw_probe` | `NOT_RUN` | Not run | Capture stopped on the `flat_reference` execution/evidence error. |
| `step_5cm_cross` | `NOT_RUN` | Not run | Capture stopped on the `flat_reference` execution/evidence error. |
| `step_10cm_cross` | `NOT_RUN` | Not run | Capture stopped on the `flat_reference` execution/evidence error. |
| `repeated_steps_cross` | `NOT_RUN` | Not run | Capture stopped on the `flat_reference` execution/evidence error. |
| `low_friction_cross` | `NOT_RUN` | Not run | Capture stopped on the `flat_reference` execution/evidence error. |

### `flat_reference` offline details

The preserved raw trace has 6,001 valid rows from tick 0 through tick 6,000 (terminal time `12.000000000000677` s), with no terminal safety failure. The focused zero-integration audit recomputed the trace SHA-256 as `1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484`, exactly matching the sealed #166 reference digest.

The frozen measurement window contains 5,000 `vx` samples. Mean `vx` is `0.885882509707172` m/s, MAE is `0.11411749029282788` m/s, and RMSE is `0.11919403374163151` m/s. The offline audit reports `tracking_pass=true`, `flat_cross_axis_pass=true`, and `reference_pass=true` (reference mean threshold: `0.8` m/s). It replayed 599 policy updates, rebuilt 6,001 contact frames, and found maximum target error `0.0`.

These raw-trace findings do not change the capture record from `ERROR`, complete the campaign, or authorize later cases. The independent full-campaign verifier returned `FAILED: capture incomplete`; the focused audit only adjudicated the preserved `flat_reference` rows. No `INTEGRITY_STOP` was found for those rows.

## Execution notes and evidence

Two qualification invocations failed before capture while the locked runtime assets were being staged: the host interpreter failed the isolation guard, and the first task-local controller build lacked the ignored MuJoCo 3.3.6 SDK link. After staging the already-installed locked runtime and ignored host assets without downloading or installing runtime/model packages, clean qualification passed. All failures and successful receipts remain in the Praxis evidence package.

The raw capture, original campaign ledger, byte-identical ledger copy with SHA-256 manifest, standard verifier failure bundle, and focused raw-trace audit bundle are preserved with Praxis task #178. Evidence IDs E1–E15 and their exact paths are listed in the accompanying `closeout.json`.
