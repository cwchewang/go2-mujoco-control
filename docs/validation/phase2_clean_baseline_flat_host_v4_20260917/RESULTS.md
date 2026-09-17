# Phase2 clean baseline flat-host v4 closeout

Date: 2026-09-17

Task commit: `73c21d184412b98b112aee1d0794b3f52b58730d`

Trusted host record: `docs/research/evidence/atlas_host/73c21d184412b98b112aee1d0794b3f52b58730d.json`

Proposed Luna primary classification: `PROTOCOL_FAILURE`

Earliest causal boundary: `execution`

No scientific attempt was consumed. The trusted host launched the frozen
command once, but the simulator failed while creating DDS domain 220 before
the DDS-ready marker and before controller startup. No live retry was made.

## FACTS

- The host record says `launched=true`, `returncode=1`, `timed_out=false`, and
  `error=null`. Its recorded elapsed wall time is 1.567746 s, from
  `2026-09-17T10:12:36.708032+00:00` through
  `2026-09-17T10:12:38.275778+00:00`.
- The host-recorded candidate commit is the task commit. The recorded command
  and domain are the frozen task manifest: domain `220`, clean baseline,
  `stand-walk-lie`, Raibert trot, period `0.60`, step length `0.091`, and
  `max-cycles=64`.
- `simulator.log` records MuJoCo 3.3.6 initialization and `Mujoco data is
  prepared`, followed by the selected `lo` interface being reported as not
  multicast-capable, then `Failed to find a free participant index for domain
  220`, and finally `Failed to create domain explicitly`.
- The simulator log contains no `Unitree DDS bridge ready` marker. There is no
  controller `data.csv` and no `controller.log`; consequently no
  LowState/LowCmd handoff or post-handoff sample is recorded.
- The run directory contains exactly the four files indexed by the host:
  `contact_ground_truth.csv`, `environment.txt`, `run_metadata.txt`, and
  `simulator.log`. Their recorded hashes and sizes are in `provenance.csv`.
- `contact_ground_truth.csv` is simulator-side boot evidence, not controller
  locomotion evidence. It has a 264-field header, 92 physical data rows, 91
  complete rows, and one final 70-field row. The final row is step 91 at
  `time_s=0.184` and ends at `FL_sensor_force_world_x_N` without a trailing
  newline.
- `run_metadata.txt` records `git_head` equal to the candidate commit,
  `git_branch=detached`, `git_dirty=false`, `headless=true`, domain 220, and
  the simulator/controller/scene hashes used by the runner.

## DERIVED METRICS

All values below are deterministic calculations from the host record and the
indexed raw files. The calculation rules and source columns are recorded in
`analysis.json`.

- Host-record elapsed time: `1.567746 s`.
- Complete contact-log sampling: rows 0--90, `time_s=0.002` through
  `0.182`, constant `dt=0.002 s`, with contiguous `step_index` 0--90.
  The step-91 row is structurally incomplete and is excluded from complete-row
  aggregates.
- Frozen nominal commanded speed: `0.091 / 0.60 = 0.1516666667 m/s`.
- Measured locomotion speed over `motion_stage==2`: **not evaluable**; no
  controller `data.csv` exists.
- Tracking ratio: **not evaluable**; neither measured locomotion speed nor a
  controller command/motion-stage interval exists.
- Completed gait cycles: `0 observed before abort`; the scientific cycle
  metric is **not evaluable** because the controller never started.
- The only available orientation is a simulator boot transient, not a gait
  measure. Applying the stated quaternion-to-RPY formula to all rows gives
  maximum absolute roll `2.7920377452e-05 rad` and maximum absolute pitch
  `0.07829484897 rad`, both at `time_s=0.184` in the partial final row.
- Clean target-feasibility rejection, strict ID-WBC rejection, torque-envelope
  saturation, joint/foot tracking error, emergency stop, and abnormal
  locomotion contact failure are **not evaluable** because no controller
  sample was produced. The simulator log instead records a DDS domain-create
  abort.

Passing-criterion evaluation:

| Criterion | Result |
|---|---|
| 64 completed cycles and normal return to stand | Not reached / not evaluable |
| No clean target-feasibility rejection | Not evaluable |
| No strict WBC rejection promoted to motion | Not evaluable |
| No emergency/hard safety stop | Not evaluable before controller start |
| Measured speed in `[0.11, 0.19] m/s` | Not evaluable |

## LUNA INTERPRETATION

The proposed classification is `PROTOCOL_FAILURE` at the `execution`
boundary, with reason code
`SIMULATOR_DDS_PARTICIPANT_INDEX_EXHAUSTION`. This is based on the exact
simulator log error and the absence of the DDS-ready marker, controller log,
controller CSV, and post-handoff sample. The incomplete simulator contact CSV
is a consequence of the boot abort and cannot support a locomotion or
controller classification.

This is not a claim that the clean baseline passed or failed scientifically.
The scientific pass criteria cannot be evaluated from this run, and no
controller, planner, scene, test, or launch-script change was made after host
execution. Sol may recompute the metrics from the immutable evidence and
revise or overturn this proposal.
