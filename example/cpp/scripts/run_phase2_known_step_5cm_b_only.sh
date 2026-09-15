#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
run_dir="_runs/phase2_known_step_5cm_b_only_20260915/B"
run_abs="$repo_root/example/cpp/experiments/$run_dir"
[[ ! -e "$run_abs" ]] || { echo "run directory exists: $run_dir" >&2; exit 2; }

export SIM_LOCKSTEP=1
export TROT_LOCKSTEP_PAIRED_HIGHSTATE=1
export TROT_BRIDGE_ATOMIC_RECORD=1
export TROT_DYNAMICS_TOLERANCE_N=20
export FULL2_HOLD_CYCLES=999
export TROT_KNOWN_STEP_EDGE_X_M=0.80
export TROT_KNOWN_STEP_HEIGHT_M=0.05
export TROT_KNOWN_STEP_HALF_WIDTH_Y_M=1.00
export TROT_KNOWN_STEP_TRAVERSAL=1

# Frozen against the accepted A capture: D4 and all prior diagnostic interventions OFF;
# no reactive obstacle / auto-environment path.
unset TROT_BOUNDED_STANCE_DQ_D4_AB TROT_PD_PULSE_AB TROT_FOUR_THIGH_D90_AB

cd "$repo_root"
TROT_CPU_AUTOPIN=1 bash example/cpp/scripts/run_trot.sh 80 "$run_dir" \
  --headless --wall-clock-motion --controller-duration 34 \
  --scene-file unitree_robots/go2/scene_known_step_5cm.xml \
  --cartesian-world --wbc-full --kernel raibert-trot \
  --period 0.60 --duty 0.75 --step-length 0.091 --foot-lift 0.028 \
  --raibert-velocity-gain 0.12 --raibert-max-adjustment 0.140 \
  --no-world-feedback --no-attitude-feedback \
  --tau-limit 35 --preview-horizon 4 --max-cycles 40 \
  --domain-id 232
