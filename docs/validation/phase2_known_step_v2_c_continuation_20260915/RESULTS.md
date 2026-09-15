# Phase2 known-step V2 C continuation closeout

Date: 2026-09-15
Primary classification: `PROTOCOL_FAILURE`
Reason code: `EXECUTION_BINARY_HASH_MISMATCH`.

The already-consumed parent V2-off A was rejudicated with the superseding clean
pre-contact predicate and passed: 870 clean rows, 1.738 s span, no adaptation,
maximum absolute roll/pitch 0.03432/0.08669 rad, 870 valid WBC rows, SRBD/ID
success 1.0, equality-residual p95 `6.4272e-06`, and healthy lockstep/paired
HighState plus raw/runtime provenance.

C was not launched. Before C, the installed controller hash was
`d14358e42da7cf57e0f1ae7f4738ae5da277e7eaa951a473836dbf759894f5fd`, but the
parent A requires `fe7339d50346e53069d81a27504ae4de4217baab29a6695cdd5073d1898b1fd2`;
the installed simulator hash was
`8c9df32482df3e2e92fb4c1cdf0faa8a3ab50f8d418388977e553f9a40c8f210`, but the
parent A requires `29caa74aa8e5cf1988190ecb8978d2fe15ce6a21146182c66e5efc91121c022b`.
The scene hash matched. The task requires stopping at execution on any mismatch;
no rebuild, binary replacement, retry, or live process was performed.

Detailed machine-readable evidence is in `analysis.json` and `provenance.csv`.
