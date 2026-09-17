# Phase2 known-step V2 minimum-clearance path closeout

Date: 2026-09-17
Task commit: `b314176328f26e1bf18f93dc387267d2e2656ba4`
Exact parent: `12238b768d8ac6f3d51032fc8ce19d443ca71966`
Primary classification: `MIN_CLEARANCE_PATH_INFEASIBLE`

The mandatory no-live feasibility gate failed, so runtime code was not changed
and no canary was launched. The candidate minimum-clearance corridor was
`0.075230552 m`, reconstructed over all 75 planning-valid FL V2 samples from
14.254 s through 14.402 s using the frozen parent C pose/quaternion and swing
phase. Direct FL IK succeeded for all 75 samples and FK round-tripped with a
maximum error of `8.67361737988404e-17 m`; edge clearance also passed with a
minimum margin of `0.002230552 m` over the 7 samples in `[0.777, 0.823] m`.

The earliest failure was a joint-range violation at raw row 3160, state time
14.320 s. The candidate target was world
`(0.721628193, 0.100213386001199, 0.0720739130308704) m`, body
`(0.196208893109765, 0.0698152420632898, -0.127812667918280) m`, and direct IK
returned `(-0.645318027636051, 1.33053112156358, -2.72481562160116) rad`; the
FL calf was `0.00211562160116 rad` below the frozen lower bound `-2.7227 rad`.

Per the task stop rule, no runtime edit, no test/build/provenance preflight,
and no live run was authorized after this veto. Parent raw evidence remained
read-only and unchanged.
