#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
  echo "usage: $0 L1|L2|L3" >&2
  exit 2
fi
run_id="$1"
case "$run_id" in
  L1) domain_id=201 ;;
  L2) domain_id=202 ;;
  L3) domain_id=203 ;;
  *) echo "run id must be L1, L2, or L3" >&2; exit 2 ;;
esac

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
run_dir="_runs/phase1_frozen_handoff_first_divergence_20260914/$run_id"
run_abs="$repo_root/example/cpp/experiments/$run_dir"
if [[ -e "$run_abs" ]]; then
  echo "refusing to overwrite existing run directory: $run_dir" >&2
  exit 2
fi

# Inherited frozen READY baseline. No causal intervention is permitted.
export SIM_LOCKSTEP=1
unset SIM_LOCKSTEP_TRACE
unset TROT_PD_PULSE_AB
unset TROT_FOUR_THIGH_D90_AB
unset TROT_BOUNDED_STANCE_DQ_D4_AB

# Capture the exact causal chain around the deterministic tick-8000 handoff.
# The measured handoff time is 7.999999999999341 s, so start just below 8.0
# to guarantee that the pre-step tick-8000 record itself is included.
export TROT_BRIDGE_ATOMIC_RECORD=1
export TROT_MJ_SNAPSHOT_PATH="$run_abs/mj_snapshot.bin"
export TROT_MJ_SNAPSHOT_TIME_START=7.999
export TROT_MJ_SNAPSHOT_TIME_END=13.0

# Keep the accepted baseline/controller settings identical to the predecessor.
export TROT_DYNAMICS_TOLERANCE_N=20
export TROT_HS_START_PERIOD=0.20
export TROT_HS_START_DUTY=0.50
export TROT_HS_SPEED_LEAD=0.25
export TROT_HS_ACC_GAIN=10
export TROT_HS_ACC_LIMIT=4
export TROT_HS_STEP_CAP=0.52
export TROT_HS_SWING_REACH=0.90
export TROT_HS_HYBRID_CONTACT=2
export TROT_HS_PITCH_GAIN=24
export TROT_HS_PITCH_DAMP=6
export TROT_HS_ROLL_GAIN=20
export TROT_HS_ROLL_DAMP=10
export TROT_HS_STABILITY_GOV=1

cd "$repo_root"
TROT_CPU_AUTOPIN=1 bash example/cpp/scripts/run_trot.sh 140 "$run_dir" \
  --headless --wall-clock-motion --controller-duration 86 \
  --wbc-full --gait-pattern running-trot --kernel raibert-trot \
  --period 0.14 --duty 0.44 --step-length 0.50 --foot-lift 0.20 \
  --tau-limit 45 --raibert-velocity-gain 0.010 \
  --raibert-max-adjustment 0.06 --preview-horizon 4 \
  --support-anchor-feedback --support-anchor-gain 0.35 \
  --velocity-max-accel 0.80 --velocity-max-decel 1.20 \
  --velocity-max-jerk 4.0 --velocity-command-script \
  example/cpp/configs/phase1_velocity_varying.csv \
  --velocity-max-tracking-lead 0.20 \
  --domain-id "$domain_id"
