# Shared-transfer combination formal v2 results

## Result

**PASS.** Both prescribed cases passed under the frozen confirmatory protocol. The conclusion is limited to whether this complete pinned shared deployment combination preserved the sealed source's 1.0 m/s flat capability under this protocol. It does not establish low-speed, terrain, hardware, or general robustness. No causal explanation is inferred from the outcome. [E8, E10, E12]

## Frozen identity and gates

- Praxis issue: **#166**; starting HEAD: `9e82e56ac2a5db63d7834e86ce402d542bf10ae8`
- Source commit: `30e74dc507bec7a642a8c98be26081f2c6f0822d`
- Checkpoint SHA-256: `9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d`
- Protocol: `rl-shared-transfer-combination-v1`; SHA-256: `2d23131cb104be50aeb163737e3cfbf10f5a9291acf7726c2eda75e3fa5e9b32`
- Budget: two attempts; retry none; first non-pass stops progression.
- Frozen gates include reference mean minimum `0.8 m/s`, tracking tolerances `0.05 m/s` absolute and `0.2` relative, flat lateral maximum `0.3 m`, flat yaw maximum `0.3 rad`, and safety limits tilt `1.2 rad`, clearance minimum `0.06 m`, lateral maximum `1.5 m`.

Both independent reviews were `APPROVED` for the exact starting HEAD. The science review tip was `ace65bec9fdcad8a52d29fc3cae0d113246d7312` (reviewer `OpenAI Codex (GPT-6)`); the execution review tip was `16810592cbc342ed29d3ce92f22efe6062516bb5` (reviewer `GPT-6 Codex execution reviewer #173 r3`). The reviewer identities differ. [E1]

Resource preflight matched the frozen protocol and checkpoint hashes, all 50 locked upstream source files, and the reliable Python 3.10.12 environment with Torch 2.6.0+cpu, MuJoCo 3.3.6, and NumPy 2.2.6. The required MJPC admission binary and MuJoCo SDK header/library were present. Qualification completed clean and non-development at the frozen HEAD with all eight recorded check return codes equal to zero; its capability status was `NOT_RUN`. [E2, E3, E4]

Preparation returned `READY_AWAITING_START` with `physics_steps=0`; the campaign ledger was absent. The start record bound the prepared manifest SHA-256 `58d2cb99d5b13c014e9e2f750588b34b0214c75201159df7dcc802696afceb1e`, max attempts `2`, and the exact user instruction `好，开吧`. [E5, E6, E7]

## Verified case results

| Case | Verdict | Steps | Mean vx (m/s) | MAE (m/s) | RMSE (m/s) | Progress (m) | Lateral max (m) | Yaw max (rad) | Min clearance (m) | Policy updates | p50 (ms) | p99 (ms) | Trace SHA-256 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `combined_1` | PASS | 6000 | 0.8858825097071722 | 0.11411749029282782 | 0.11919403374163143 | 10.486111570522883 | 0.06490106716002314 | 0.03719463073879735 | 0.27 | 599 | 0.3352929779794067 | 0.541720520122907 | `1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484` |
| `combined_2` | PASS | 6000 | 0.8858825097071722 | 0.11411749029282782 | 0.11919403374163143 | 10.486111570522883 | 0.06490106716002314 | 0.03719463073879735 | 0.27 | 599 | 0.3377980028744787 | 0.6797237368300555 | `1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484` |

Each measurement window contains 5,000 samples. The repeat case has the same trace SHA-256 as `combined_1`. The authoritative campaign ledger and offline verifier both report two consumed attempts. Offline verification returned `VERIFIED`, checked the external ledger, and integrated zero physics steps. [E8, E10, E11, E12]

## Classification and verification note

| Classification | Result |
|---|---|
| PASS | `combined_1`, `combined_2` |
| PERFORMANCE_FAIL | None |
| SAFETY_STOP / INTEGRITY_STOP | None |
| Infrastructure / verification | The unmodified `baseline verify` CLI stopped with `preflight identity mismatch`: the captured preflight records the expected empty Git branch for detached HEAD, while the verifier compares that field with the logical task branch. This failure is preserved. The same offline verifier then completed with an in-memory adapter that first validated the exact five-field detached Praxis identity and mapped only the empty actual branch to the task's logical branch for the existing identity comparison. The capture bundle, preflight report, verifier source, and qualification bundle were not modified. Final verification returned `VERIFIED`, consumed `2`, `physics_steps=0`. [E9, E10, E11] |

The campaign is characterized under the frozen protocol. The two passes answer only the scoped flat capability question above. [E8, E10, E12]
