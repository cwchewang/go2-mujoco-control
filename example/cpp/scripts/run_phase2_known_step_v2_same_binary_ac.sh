#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 3 ]]; then echo "usage: $0 A|C DOMAIN RUN_DIR" >&2; exit 2; fi
arm="$1"; domain_id="$2"; run_dir="$3"
case "$arm" in
  A) unset TROT_KNOWN_STEP_TRAVERSAL_V2 TROT_KNOWN_STEP_TRAVERSAL ;;
  C) export TROT_KNOWN_STEP_TRAVERSAL_V2=1; unset TROT_KNOWN_STEP_TRAVERSAL ;;
  *) echo "arm must be A or C" >&2; exit 2 ;;
esac
if ! [[ "$domain_id" =~ ^[0-9]+$ ]] || (( domain_id < 0 || domain_id > 232 )); then
  echo "DDS domain must be an integer in [0, 232]" >&2; exit 2
fi
script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
run_abs="$repo_root/example/cpp/experiments/$run_dir"
[[ ! -e "$run_abs" ]] || { echo "run directory exists: $run_dir" >&2; exit 2; }
export SIM_LOCKSTEP=1 TROT_LOCKSTEP_PAIRED_HIGHSTATE=1 TROT_BRIDGE_ATOMIC_RECORD=1
export TROT_DYNAMICS_TOLERANCE_N=20 FULL2_HOLD_CYCLES=999
export TROT_KNOWN_STEP_EDGE_X_M=0.80 TROT_KNOWN_STEP_HEIGHT_M=0.05 TROT_KNOWN_STEP_HALF_WIDTH_Y_M=1.00
unset TROT_BOUNDED_STANCE_DQ_D4_AB TROT_PD_PULSE_AB TROT_FOUR_THIGH_D90_AB
cd "$repo_root"
TROT_CPU_AUTOPIN=1 bash example/cpp/scripts/run_trot.sh 80 "$run_dir" \
  --headless --wall-clock-motion --controller-duration 34 \
  --scene-file unitree_robots/go2/scene_known_step_5cm.xml \
  --cartesian-world --wbc-full --kernel raibert-trot \
  --period 0.60 --duty 0.75 --step-length 0.091 --foot-lift 0.028 \
  --raibert-velocity-gain 0.12 --raibert-max-adjustment 0.140 \
  --no-world-feedback --no-attitude-feedback \
  --tau-limit 35 --preview-horizon 4 --max-cycles 40 --domain-id "$domain_id"
