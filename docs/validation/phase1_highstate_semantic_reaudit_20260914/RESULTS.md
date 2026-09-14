# Phase 1 HighState semantic re-audit

Top-level classification: HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD

This is an offline-only semantic re-audit of exactly the parent L1/L2/L3 raw captures. No simulator, controller, new trajectory, or repair was run.

Parent label: HIGHSTATE_PUBLICATION_PAIRING_DIVERGENCE at parent closeout SHA 859bb66f7d9dfe712bd7cd58186f99541ebc8e33. It required re-audit because the parent first compared HighState generation metadata before establishing whether a different canonical HighState value was actually consumed.

Metadata-only versus value-carrying boundary:
- Metadata-only HighState publication-history divergence occurs at ticks 11800, 11800, 11800 while the aligned bridge canonical HighState payload is equal.
- The first consumed HighState canonical value divergence occurs at ticks 11800, 11802, 11800; it is downstream of the metadata-only difference and is compared by payload bytes plus decoded fields.

Pairwise result:

| Pair | Metadata-only tick | First consumed HighState value tick | First LowCmd payload tick | Classification |
|---|---:|---:|---:|---|
| L1-L2 | 11800 | 11800 | 12302 | HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD |
| L1-L3 | 11800 | 11802 | 12304 | HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD |
| L2-L3 | 11800 | 11800 | 12302 | HIGHSTATE_PAIRING_CAUSAL_TO_LOWCMD |

value_boundary.csv independently reports metadata history, bridge LowState/HighState payloads, controller receipt payloads, consumed LowState, consumed HighState, the consumed tuple, and pre-publish LowCmd. Payload differences are decoded with the fixed-width little-endian canonical layouts from the parent trace header.

At each first LowCmd payload divergence, lowcmd_causal_snapshot.csv records the exact consumed receipt sequence identifiers, consumed HighState position/velocity values, aligned bridge HighState hashes and generation/tick/skip metadata, the first differing LowCmd field/value, and whether each consumed HighState maps to the same physics tick or an earlier available bridge publication.

The causal result is a HighState freshness/pairing difference: aligned bridge LowState and HighState physical payloads remain equal, LowState consumption remains equal, and the controller consumes different valid HighState payloads from current versus earlier available publications before the first LowCmd payload difference. Receipt sequence numbers are lineage metadata, not physical values.

Live repair experiment justified: yes, as a separate minimal-fix checkpoint. No repair is implemented here.

Parent provenance was rehashed from /home/che/dev/go2-workspace/phase1-lowstate-lowcmd-boundary-20260914/docs/validation/phase1_lowstate_highstate_lowcmd_boundary_20260914/provenance.csv; all listed raw artifact bytes and SHA-256 values matched. Runtime source HEAD in the captures is bc6e202a3efde6c7d7118656afde91fd4c0869d3. Protocol errors: 0.

Recommended next checkpoint: a separate minimal-fix checkpoint that deterministically pairs the consumed HighState with each LowState/control tick while preserving normal behavior with diagnostic/fix mode disabled; do not modify this re-audit branch further.
