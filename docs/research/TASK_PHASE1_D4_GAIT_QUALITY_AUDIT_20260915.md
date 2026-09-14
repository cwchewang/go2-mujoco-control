# Phase1 D4 gait-quality audit — 2026-09-15

Read `docs/research/PHASE1_AGENT_CONTRACT.md` first.

## Scope

- Parent evidence SHA: `0a9e977573081270b630119b0696cdedc03357a0`.
- Branch: `research/phase1-d4-gait-quality-audit-20260915`.
- Accepted parent result: deterministic D4 A/B classified `SUPPORTED` with exact pre-window equality and DID excess `-0.242994545 m/s`.
- This checkpoint is OFFLINE ONLY. Reuse exactly the existing local A/B raw captures under `example/cpp/experiments/_runs/phase1_d4_deterministic_ab_20260914/{A,B}`.
- Do not start simulator/controller, do not rerun A or B, do not change D4, gait, WBC, solver, HighState pairing, or any parameter.

## Question

The parent A/B proved that D4 causally removes most of the 2.3 m/s velocity excess, but B also showed much larger roll/pitch magnitude. Determine whether B represents:

1. `DYNAMIC_GAIT_STRUCTURED`: larger but gait-phase-locked, cycle-repeatable body motion with acceptable contact/slip/actuation quality;
2. `DYNAMIC_GAIT_WITH_COST`: structured body motion, but accompanied by material contact/slip/actuation degradation;
3. `UNSTRUCTURED_INSTABILITY`: weak phase locking / poor cycle repeatability and/or progressive drift with degraded contact/actuation quality;
4. `INSUFFICIENT_EVIDENCE`;
5. `PROTOCOL_FAILURE`.

This is a gait-quality audit, not a pass/fail threshold for future baseline adoption. Do not relabel the parent causal D4 result.

## Data and provenance

Use only parent A/B `data.csv`, `data.csv.id_closure.csv`, metadata/logs, and other already existing raw artifacts if needed. Rehash all used raw artifacts and verify parent runtime/source provenance. Missing/mismatched raw => `PROTOCOL_FAILURE`; do not regenerate.

Primary audit window is active-relative `[32.10,39.90)` because D4 is active there. Also report a short pre-window `[31.90,32.10)` only as a sanity reference.

## Required analyses

### 1. Signed attitude, not absolute attitude

For A and B report in the active window:

- signed roll mean, median, std, p05/p95, min/max;
- signed pitch mean, median, std, p05/p95, min/max;
- peak-to-peak roll/pitch per gait cycle and distribution across cycles;
- linear trend of cycle-mean roll/pitch versus time to detect drift.

Do not infer instability from absolute max angle alone.

### 2. Gait-phase-folded waveform

Use the actual per-row gait period when available (`velocity_command_gait_period_s`), otherwise the frozen 0.14 s period, and active-relative time to compute normalized gait phase in `[0,1)`. Use 50 equal phase bins.

For A and B, generate phase-folded mean/std for:

- signed roll and pitch;
- world base z / available body-height signal;
- measured/applied velocity and velocity excess;
- contact count and each leg contact indicator / WBC contact mask where available;
- support-foot speed where available.

For each attitude channel report:

- phase-waveform peak-to-peak amplitude;
- fraction of total variance explained by phase-bin mean (`1 - within_bin_variance / total_variance`, clipped/report raw as appropriate);
- cycle-to-template RMSE distribution;
- cycle-to-template correlation distribution (only for cycles with sufficient finite samples).

High explained variance + low cycle-to-template scatter supports organized periodic motion; low explained variance / large cycle scatter supports unstructured motion.

### 3. Cycle-to-cycle repeatability

Segment complete cycles fully inside `[32.10,39.90)`.

For each arm and each complete cycle, record:

- roll/pitch mean and peak-to-peak;
- body-z mean and peak-to-peak if available;
- measured velocity mean/excess;
- contact-mask occupancy fractions;
- minimum contact count;
- support-foot-speed median/p95 if available;
- torque saturation max and RMS/mean torque proxy if available from closure/raw data.

Summarize coefficient of variation / robust dispersion across cycles. Explicitly test for progressive growth in attitude amplitude over time.

### 4. Contact and support-foot quality

Compare A versus B in the active window:

- physical contact-count distribution;
- each physical/internal contact-mask distribution;
- expected diagonal-trot masks 6 and 9 occupancy;
- zero/one/two/three/four-contact fractions;
- touchdown counts/timing irregularity if recoverable;
- support-foot-speed median/p95/max and low-friction/slip evidence if available.

Do not call a larger body-angle waveform harmful unless contact/slip evidence supports that interpretation.

### 5. Actuation / solver quality

Compare A versus B:

- WBC/SRBD/ID success fractions and residuals;
- torque saturation fraction/max;
- RMS/median/p95 absolute `tau_ff` and, if reconstructable from logged state/targets, effective PD+FF torque proxy per motor and globally;
- D4 scalar `s`, applied `|delta dq|`, `|kd*delta dq|`, active fraction.

Distinguish a dynamic but controlled gait from one that simply spends more time near actuator limits.

### 6. Visual evidence (optional, no live physics)

If an existing repository tool can reconstruct/render the already recorded trajectory directly from raw state without integrating or resimulating physics, create matched A/B clips for active-relative `32.1–39.9 s` (or representative 3–5 s subwindows) with identical camera settings and timestamps. Do not run MuJoCo dynamics to regenerate a trajectory. If no safe offline reconstruction path exists, state that visual evidence is unavailable and continue; this is not a blocker.

## Interpretation

Do not use arbitrary animal-like angle thresholds. Base classification on structure and control quality:

- `DYNAMIC_GAIT_STRUCTURED`: B attitude is strongly phase-locked/repeatable, does not progressively diverge, and contact/slip/actuation/solver metrics are broadly healthy relative to A.
- `DYNAMIC_GAIT_WITH_COST`: B is clearly phase-locked/repeatable but has material contact loss/slip/actuator-loading degradation relative to A.
- `UNSTRUCTURED_INSTABILITY`: B attitude is poorly phase-locked or cycle repeatability degrades/progressively grows, especially with contact/slip/actuation degradation.
- `INSUFFICIENT_EVIDENCE`: key raw signals needed to distinguish these are absent.
- `PROTOCOL_FAILURE`: provenance/raw integrity failure.

The conclusion must separately state:

1. whether the ~19° maximum pitch is primarily organized gait motion or instability;
2. whether D4 is a credible candidate for the future locomotion baseline;
3. whether any additional live D4 experiment is justified before returning to obstacle-traversal work.

Do not run that follow-up experiment here.

## Deliverables

Create `docs/validation/phase1_d4_gait_quality_audit_20260915/` containing at least:

- `RESULTS.md`
- `attitude_summary.csv`
- `phase_folded.csv`
- `cycle_summary.csv`
- `contact_quality.csv`
- `actuation_quality.csv`
- `provenance.csv`
- `analysis.json`
- phase-folded plots (PNG) for attitude/contact/body-z where available
- optional matched A/B offline-rendered clips only if reconstruction is available without live physics

Use the prepared analyzer `example/cpp/tools/analysis/analyze_phase1_d4_gait_quality.py`; extend/fix it only if necessary for existing schema. Commit/push closeout and STOP.