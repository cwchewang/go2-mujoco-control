#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cpp_dir="$(cd "$script_dir/.." && pwd)"
repo_dir="$(cd "$cpp_dir/../.." && pwd)"
simulator="$repo_dir/simulate/build/unitree_mujoco"
probe="$cpp_dir/build/dds_lowstate_probe"
scene_file="$repo_dir/unitree_robots/go2/scene_leg_lift_demo.xml"

domain_id=""
run_dir=""
usage()
{
  echo "usage: $0 --domain-id N --run-dir PATH" >&2
}

while (( $# > 0 )); do
  case "$1" in
    --domain-id)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      domain_id="$2"
      shift 2
      ;;
    --run-dir)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      run_dir="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

[[ "$domain_id" =~ ^[0-9]+$ ]] || { usage; exit 2; }
(( domain_id <= 232 )) || { echo "domain outside [0,232]" >&2; exit 2; }
[[ -n "$run_dir" ]] || { usage; exit 2; }
if [[ "$run_dir" != /* ]]; then
  run_dir="$repo_dir/$run_dir"
fi
[[ -x "$simulator" ]] || { echo "missing simulator: $simulator" >&2; exit 2; }
[[ -x "$probe" ]] || { echo "missing read-only probe: $probe" >&2; exit 2; }
[[ -f "$scene_file" ]] || { echo "missing scene: $scene_file" >&2; exit 2; }

source "$script_dir/dds_runtime.sh"
mkdir -p "$run_dir"
dds_runtime_prepare "$domain_id" "$run_dir" "$repo_dir" lo

sim_pid=""
probe_pid=""
stop_children()
{
  if [[ -n "$probe_pid" ]] && kill -0 "$probe_pid" 2>/dev/null; then
    kill -TERM "$probe_pid" 2>/dev/null || true
    wait "$probe_pid" 2>/dev/null || true
  fi
  probe_pid=""
  if [[ -n "$sim_pid" ]] && kill -0 "$sim_pid" 2>/dev/null; then
    kill -TERM "$sim_pid" 2>/dev/null || true
    for _ in $(seq 1 100); do
      kill -0 "$sim_pid" 2>/dev/null || break
      sleep 0.05
    done
    if kill -0 "$sim_pid" 2>/dev/null; then
      kill -KILL "$sim_pid" 2>/dev/null || true
    fi
    wait "$sim_pid" 2>/dev/null || true
  fi
  sim_pid=""
}
trap 'stop_children; dds_runtime_finalize || true' EXIT INT TERM

run_cycle()
{
  local label="$1"
  local cycle_dir="$run_dir/cycle_$label"
  local simulator_log="$cycle_dir/simulator.log"
  local probe_log="$cycle_dir/lowstate_probe.log"
  local probe_evidence="$cycle_dir/lowstate_probe.txt"
  mkdir -p "$cycle_dir"
  dds_runtime_snapshot "$cycle_dir/pre_state.txt" "$domain_id" lo "cycle_${label}_pre"

  env -u GO2_DDS_PRELOAD \
    LD_PRELOAD="$DDS_RUNTIME_PRELOAD" \
    "$simulator" -i "$domain_id" -n lo -r go2 -s "$scene_file" \
    --headless >"$simulator_log" 2>&1 &
  sim_pid=$!

  local ready=false
  for _ in $(seq 1 400); do
    if grep -Fq "Unitree DDS bridge ready" "$simulator_log"; then
      ready=true
      break
    fi
    if ! kill -0 "$sim_pid" 2>/dev/null; then
      echo "cycle $label: simulator exited before DDS-ready" >&2
      return 1
    fi
    sleep 0.05
  done
  if [[ "$ready" != true ]]; then
    echo "cycle $label: DDS-ready marker timeout" >&2
    return 1
  fi

  env -u GO2_DDS_PRELOAD \
    LD_PRELOAD="$DDS_RUNTIME_PRELOAD" \
    "$probe" --domain-id "$domain_id" --interface lo --samples 10 \
    --timeout-s 10 --evidence "$probe_evidence" >"$probe_log" 2>&1 &
  probe_pid=$!
  local probe_status=0
  wait "$probe_pid" || probe_status=$?
  probe_pid=""
  if (( probe_status != 0 )); then
    echo "cycle $label: read-only LowState probe failed" >&2
    return 1
  fi
  stop_children
  dds_runtime_snapshot "$cycle_dir/post_state.txt" "$domain_id" lo "cycle_${label}_post"
  if [[ -n "$(dds_runtime_active_processes || true)" ]]; then
    echo "cycle $label: Go2 process leaked after clean termination" >&2
    return 1
  fi
}

run_cycle A
dds_runtime_boundary between_cycles
run_cycle B

echo "DDS_RUNTIME_SMOKE_PREPARED domain=$domain_id"
echo "DDS_RUNTIME_SMOKE_CYCLES=2"
echo "DDS_RUNTIME_SMOKE_SUPPORT_SHA256=$DDS_RUNTIME_SUPPORT_ARTIFACT_SHA256"
