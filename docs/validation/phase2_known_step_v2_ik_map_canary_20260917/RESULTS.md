# Phase2 known-step V2 IK-map canary closeout

Date: 2026-09-17
Primary classification: `DIRECT_V2_TARGET_INFEASIBLE`

The no-live feasibility gate failed, so no runtime code was changed and no live
canary was launched. The earliest failure is raw C row 3155 at state time
14.310 s. The reconstructed unclamped FL target was world
`(0.668859661, 0.109323078, 0.096256739) m` and body
`(0.146531546, 0.082025672, -0.106769989) m`. Direct FL IK succeeded with
`q=(-0.692312881, 2.059127542, -2.784049885) rad`, but the calf violated the
Go2 range `[-2.7227, -0.83776] rad` by `0.061349885 rad` below its lower bound.

The reconstruction covered 75 planning-valid V2 FL samples from 14.254 s
(raw row 3127) through the last swing sample at 14.402 s; the 14.404 s row is
the first touchdown/stance reset and no longer carries a V2 target. The first
28 samples passed direct IK, all three joint ranges, and FK round-trip; the
maximum round-trip error before the failure was `8.33e-17 m`. Direct IK first
failed at 14.316 s because `leg_z_squared < 0`. Pose reconstruction from the
logged RPY and frozen source FK reproduced logged FL actual world x/z over the
gate interval within `1.48e-9 m`.

Per the task stop rule, there was no target-map modification, test/build,
provenance preflight, live run, or downstream localization. The preserved raw
parent C evidence was read-only and unchanged.
