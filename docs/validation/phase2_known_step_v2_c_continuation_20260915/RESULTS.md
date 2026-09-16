# Phase2 known-step V2 C continuation closeout

Date: 2026-09-16
Primary classification: `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`
Earliest informative failure boundary: `causal` — strict A/C preactivation equality failed immediately after the common handoff.

Exactly one authorized C capture was consumed after the required immediate preflight passed. No retry, replacement run, tuning, A rerun, or follow-up live run was made. C produced 5,005 data rows and 5,005 paired HighState cycles with 2 ms lockstep and zero trace violations. The captured runtime stopped on the existing hard safety/posture path (`safety_status=1`, `completion_status=1`); this is preserved as an outcome, not repaired or reclassified.

Provenance passed: A runtime HEAD=`4834baea49f5aac9430dbdeaf8e3d93fe6124b2d`, C runtime HEAD=`3f6f12b62d1131eb0aed5d0eb65a6132f804f701`, both clean; controller SHA-256=`fe7339d50346e53069d81a27504ae4de4217baab29a6695cdd5073d1898b1fd2`; simulator SHA-256=`29caa74aa8e5cf1988190ecb8978d2fe15ce6a21146182c66e5efc91121c022b`; scene SHA-256=`8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc`. A/C binary identity, frozen V1 B hashes, V2-on/V1-off isolation, DDS/domain, lockstep, and launch-budget gates passed.

The common handoff was state tick 8.000 s. A/C were compared for 3,127 rows through the row strictly before C's first V2 crossing latch at 14.254 s (FL, base x=0.511724145); 770 causal fields were compared and 1,000 mismatches were recorded (capped). The first mismatch was row 0 at 8.000 s (`wbc_shadow_within_budget`, A=`0`, C=`1`); the next row also contains small WBC full-ID numeric/status differences. The C V2 feature flag first became active at 12.302 s (row 2,151). Therefore the required exact preactivation gate fails before any valid A/C V2 causal attribution, and the original precedence selects `INCONCLUSIVE_PREACTIVATION_DIVERGENCE`.

The existing V2 analysis was still applied descriptively. The first FL command entered the edge at 14.332 s with x=0.778435267 m, z=0.130230552 m, while the actual foot entered at 14.394 s with x=0.777368072 m, z=0.042044500 m, contact=true and force=100 N. Its actual-commanded z absolute max/p95 were 0.113197807/0.111193878 m; commanded touchdown was x/z=0.850000000/0.075230552 m versus actual x/z=0.785232410/0.046628094 m. FR first entered at 15.154 s with actual x/z=0.778506104/0.023192198 m, contact=true and force=82 N. Planning gates recorded the first latch before first plausible contact risk (14.396 s) but failed later latch-validity/final-x/effective-lift and FL/FR zero-segment boundary checks.

No qualified raised-platform contact was established for any leg. Body progression reached max x=0.883443139 m and first x=0.80 m at 15.744 s, never x=1.45 m. Contact chronology began with 2 contacts at handoff, reached 4 at 8.118 s, then became intermittent from 12.476 s; the first posture threshold crossing was 15.208 s. In the analyzed post-contact window, WBC had 1,539 valid rows, SRBD success=1.0, ID success=1.0, and equality-residual p95=1.352373e-4; runtime safety/completion and traversal gates remained failed.

Detailed raw hashes, metadata, protocol gates, exact preactivation mismatches, planning, tracking, contact chronology, and WBC/SRBD/ID metrics are in `analysis.json` and `provenance.csv`. Raw `_runs` artifacts are unchanged.
