# Aligned flat capture v2 closeout

Status: CHARACTERIZED / independently APPROVED engineering evidence; permanently closed.

Capture HEAD: ab27185f6c0ee47fdd09fecb367977bf4ab9cfde.
The [forwarded key science signoff](science_review_received.json) records the
reviewer, scope, exact capture identity and verbatim received summary. It is
labelled as a forwarded receipt; it is not a reconstructed original review file.

Authoritative Atlas capture:
`example/cpp/experiments/_runs/aligned_flat_capture_v2/run_20261002T020745814946Z`.
Manifest SHA256:
25cb69d719c8789c4b1f56d8b442ba334acd2b555d2e9c001f6375910da476d5.
Clean qualification fingerprint:
bb749e7a6f4ffa2e04f736ac27fa9bf49a328e5de2d7bad54ad13b45204b7c10.

| Arm | Canonical steps / frames | Broad 1 s horizon | Progress m | Body-vx MAE m/s |
| --- | --- | --- | --- | --- |
| RL | 500 / 501 | PASS | 0.6125663634194687 | 0.15233371941469068 |
| MJPC | 500 / 501 | PASS | 0.1319220088049042 | 0.8117407906248247 |

The external ledger contains campaign, RL and MJPC claims: exactly two engineering
attempts and 1000 canonical steps, scientific attempts zero. Both arms had no
canonical safety failure. Independent review checked manifests, continuous lock,
authorization, external claims, raw clocks, six safety conditions, PD/torque and
metrics, using the original JSONL and independent standard-library algebra.

MJPC had 23 motor-sample torque clips. Its 50 planning calls took
22.662--45.333 ms, median 28.453 ms. This remains offline_unbounded and does not
establish a 20 ms real-time result. The safety-stop branch was not triggered by
this live capture; its fake regression evidence remains separate.

The sealed v1 and v2 files, claims and failed prelaunch artifacts remain intact.
No rerun, ranking, mature-controller claim or scientific bottleneck follows.
The next [candidate baseline/probe preparation](../../research/TASK_SHARED_BASELINE_PROBES_V1_20261002.md)
requires its own runner, exact-head dual review, applicable qualification,
new binding to the existing three-stage delegation, and fresh preflight.
The v2 START receipt cannot authorize it.
