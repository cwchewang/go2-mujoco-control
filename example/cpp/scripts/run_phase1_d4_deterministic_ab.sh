#!/usr/bin/env bash
set -euo pipefail
arm="${1:-}"
case "$arm" in
  A) domain_id=221 ;;
  B) domain_id=222 ;;
  *) echo "usage: $0 A|B" >&2; exit 2 ;;
esac
script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
run_dir="_runs/phase1_d4_deterministic_ab_20260914/$arm"
run_abs="$repo_root/example/cpp/experiments/$run_dir"
[[ ! -e "$run_abs" ]] || { echo "run directory exists: $run_dir" >&2; exit 2; }
export SIM_LOCKSTEP=1
export TROT_LOCKSTEP_PAIRED_HIGHSTATE=1
export TROT_DIAG_ID_CLOSURE=1
export TROT_BRIDGE_ATOMIC_RECORD=1
export TROT_DYNAMICS_TOLERANCE_N=20
unset TROT_PD_PULSE_AB TROT_FOUR_THIGH_D90_AB
if [[ "$arm" == "B" ]]; then export TROT_BOUNDED_STANCE_DQ_D4_AB=1; else unset TROT_BOUNDED_STANCE_DQ_D4_AB; fi
export TROT_HS_START_PERIOD=0.20 TROT_HS_START_DUTY=0.50 TROT_HS_SPEED_LEAD=0.25
export TROT_HS_ACC_GAIN=10 TROT_HS_ACC_LIMIT=4 TROT_HS_STEP_CAP=0.52 TROT_HS_SWING_REACH=0.90
export TROT_HS_HYBRID_CONTACT=2 TROT_HS_PITCH_GAIN=24 TROT_HS_PITCH_DAMP=6 TROT_HS_ROLL_GAIN=20 TROT_HS_ROLL_DAMP=10 TROT_HS_STABILITY_GOV=1
cd "$repo_root"
TROT_CPU_AUTOPIN=1 bash example/cpp/scripts/run_trot.sh 140 "$run_dir"   --headless --wall-clock-motion --controller-duration 86   --wbc-full --gait-pattern running-trot --kernel raibert-trot   --period 0.14 --duty 0.44 --step-length 0.50 --foot-lift 0.20   --tau-limit 45 --raibert-velocity-gain 0.010   --raibert-max-adjustment 0.06 --preview-horizon 4   --support-anchor-feedback --support-anchor-gain 0.35   --velocity-max-accel 0.80 --velocity-max-decel 1.20   --velocity-max-jerk 4.0 --velocity-command-script example/cpp/configs/phase1_velocity_varying.csv  --velocity-max-tracking-lead 0.20 --domain-id "$domain_id"
