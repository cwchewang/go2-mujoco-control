# Phase 1 LowState/HighState/LowCmd Boundary

Top-level classification: HIGHSTATE_PUBLICATION_PAIRING_DIVERGENCE

Window: ticks 11800–12600 inclusive. Exactly L1/L2/L3 were compared.

Pairwise first-boundary results:

| Pair | Tick | Boundary | Field | Classification |
|---|---:|---|---|---|
| L1–L2 | 11800 | bridge_highstate_publication | high_source_generation | HIGHSTATE_PUBLICATION_PAIRING_DIVERGENCE |
| L1–L3 | 11800 | bridge_highstate_publication | high_source_generation | HIGHSTATE_PUBLICATION_PAIRING_DIVERGENCE |
| L2–L3 | 11800 | bridge_highstate_publication | high_source_generation | HIGHSTATE_PUBLICATION_PAIRING_DIVERGENCE |

Trace payloads use fixed-width little-endian canonical fields and the trace-header-defined 64-bit FNV-style hash; every non-empty payload hash is verified offline.

The bridge records HighState trylock publication skips and source generation/tick. The controller records callback receipt, mutex-protected snapshot consumption, and LowCmd immediately before CRC/publish.

No D4 intervention, repair, controller retuning, or follow-up experiment was run.

See first_boundary.csv, provenance.csv, and analysis.json for machine-readable closeout evidence.

Source audit: PublishStateSnapshot uses blocking LowState publication and an independent HighState trylock path; LowStateMessageHandler and HighStateMessageHandler update cached messages plus diagnostic sequence shadows under state_mutex_; SnapshotState copies the exact cached tuple before control math.

Canonical fields are LowState tick plus active motor q/dq/tau_est, IMU and foot-force fields; HighState position/velocity; and LowCmd q/dq/kp/kd/tau for 12 motors. No raw struct memory or DDS bytes are hashed.

Protocol/instrumentation gates: pre-run HEAD is bc6e202a3efde6c7d7118656afde91fd4c0869d3; L1/L2/L3 each passed the inherited lockstep gate with 43554 rows at 2 ms; focused self-test and simulate/build test_lockstep passed; diagnostic OFF has no added publish/ack path; D4 remained off.
The first divergence is HighState publication generation while bridge physical payloads at tick 11800 remain equal; downstream LowState receipt, consumed tuple, and LowCmd are not called causal after this earlier boundary.

Recommended next checkpoint: offline semantic re-audit of HighState source-generation freshness/pairing at the first LowCmd divergence, with trylock and DDS behavior unchanged.
