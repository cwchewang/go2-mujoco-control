# Phase2 known-step V2 C continuation

Mode: `confirmatory`

SOP: `docs/research/SOP.md` v0.2  
Parent: `f5ec48caeb78179b1a1a9b4b20fbef34cacf41cd`  
Branch: `research/phase2-known-step-v2-c-continuation-20260915`

## Question

Using the already-consumed fresh V2-off A from the parent, does V2 improve the original 5 cm known-step outcome when C is run with the exact same controller/simulator binaries?

## Delta from parent

The parent stopped C because it reused the obsolete full-run A gate (`safety_status=0`, `completion_status=0`, no hard posture). That gate is superseded by the already-established clean pre-contact baseline criterion from `phase2_known_step_precontact_readjudication_20260915`.

Do **not** rerun A.

Fresh A is eligible iff the same clean pre-contact predicate passes on the parent A capture:

`motion_stage == 2 AND world_base_x_m <= 0.40 AND every actual foot-center x < 0.75`

with the previously established health requirements unchanged: >=250 rows, >=0.50 s span, V2/adaptation disabled, |roll|/|pitch| <=0.25 rad, no 22-degree crossing inside the clean window, >=100 valid WBC rows, all SRBD/ID OK, equality-residual p95 <=1e-3, healthy lockstep/paired HighState, and valid A provenance.

Hard posture/safety after plausible obstacle contact is an A outcome, not an A eligibility failure.

## C authorization

If fresh A passes that clean pre-contact gate, authorize exactly one C and no new A.

Before C, verify the currently installed binaries exactly match the parent A capture:

- controller SHA-256: `fe7339d50346e53069d81a27504ae4de4217baab29a6695cdd5073d1898b1fd2`
- simulator SHA-256: `29caa74aa8e5cf1988190ecb8978d2fe15ce6a21146182c66e5efc91121c022b`
- scene SHA-256: `8293c8b635e6ff052fa72a02155c1b220c1aa08f80c0d4068f24a6844baf49dc`

Do not rebuild. If any hash differs, stop at `execution` with a specific reason code.

The runner, locomotion configuration, V2 intervention, scientific thresholds and original V2 classification precedence remain unchanged. Use a valid free DDS domain according to preflight; domain identity is execution metadata, not a scientific variable.

## Analysis correction

For A/C provenance, exact binary identity is authoritative. Require:

- A runtime HEAD = `4834baea49f5aac9430dbdeaf8e3d93fe6124b2d`, dirty=false;
- C runtime HEAD = the exact current prepared HEAD, dirty=false;
- identical controller/simulator hashes across A and C;
- unchanged scene and runner semantics;
- fresh A/C exact preactivation equality through the row strictly before first C V2 crossing latch.

Do not require A and C `git_head` strings themselves to be equal: the parent closeout and this task are analysis/governance-only commits after A, and the runtime binaries must remain byte-identical.

Then apply the original V2 scientific analysis/classification unchanged.

## Run budget and closeout

Additional live budget: C only, at most one scientifically consumed run. No A rerun and no C retry after scientific capture begins.

Default closeout outputs only: `RESULTS.md`, `analysis.json`, `provenance.csv`; add another table only if necessary evidence.
