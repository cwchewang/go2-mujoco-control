#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cpp_dir="$(cd "$script_dir/.." && pwd)"
repo_dir="$(cd "$cpp_dir/../.." && pwd)"
simulator="$repo_dir/simulate/build/unitree_mujoco"
probe="$cpp_dir/build/dds_lowstate_probe"
scene_file="$repo_dir/unitree_robots/go2/scene_leg_lift_demo.xml"
# This is the only external dependency permitted by the task. The simulator
# itself is always built from the candidate source tree below repo_dir.
mujoco_root="/home/che/dev/go2-workspace/current/simulate/mujoco"

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

if [[ -e "$run_dir" ]]; then
  [[ -d "$run_dir" ]] || {
    echo "run directory exists but is not a directory: $run_dir" >&2
    exit 2
  }
  if [[ -n "$(find "$run_dir" -mindepth 1 -print -quit 2>/dev/null)" ]]; then
    echo "run directory must be fresh and empty: $run_dir" >&2
    exit 2
  fi
fi
mkdir -p "$run_dir"

ensure_exact_source_builds()
{
  local candidate_sha candidate_tree mujoco_realpath
  local sim_build="$repo_dir/simulate/build"
  local probe_build="$cpp_dir/build"
  local provenance="$run_dir/build_provenance.txt"
  local sim_log="$run_dir/simulator_build.log"
  local probe_log="$run_dir/probe_build.log"
  local sdk_config="/opt/unitree_robotics/lib/cmake/unitree_sdk2/unitree_sdk2Config.cmake"
  local sdk_archive="/opt/unitree_robotics/lib/libunitree_sdk2.a"
  local previous_sim_sha=""
  local previous_probe_sha=""

  candidate_sha="$(git -C "$repo_dir" rev-parse HEAD)" || {
    echo "unable to identify exact candidate source SHA" >&2
    return 2
  }
  candidate_tree="$(git -C "$repo_dir" rev-parse 'HEAD^{tree}')" || {
    echo "unable to identify exact candidate source tree" >&2
    return 2
  }
  if ! git -C "$repo_dir" diff --quiet -- simulate example/cpp ||
     ! git -C "$repo_dir" diff --cached --quiet -- simulate example/cpp; then
    echo "candidate source surfaces are dirty; refusing exact-source build" >&2
    return 2
  fi
  mujoco_realpath="$(readlink -f -- "$mujoco_root")" || {
    echo "unable to resolve permitted MuJoCo root: $mujoco_root" >&2
    return 2
  }
  [[ -f "$mujoco_root/include/mujoco/mujoco.h" &&
     -f "$mujoco_root/lib/libmujoco.so" &&
     -f "$mujoco_root/simulate/simulate.cc" ]] || {
    echo "permitted MuJoCo SDK is incomplete: $mujoco_root" >&2
    return 2
  }
  [[ -f "$sdk_config" && -f "$sdk_archive" ]] || {
    echo "Unitree SDK2 development installation is incomplete" >&2
    return 2
  }

  if [[ -f "$sim_build/go2_exact_source_build.provenance" ]]; then
    previous_sim_sha="$(sed -n 's/^candidate_sha=//p' \
      "$sim_build/go2_exact_source_build.provenance" | head -n 1)"
  fi
  if [[ -f "$probe_build/go2_exact_source_build.provenance" ]]; then
    previous_probe_sha="$(sed -n 's/^candidate_sha=//p' \
      "$probe_build/go2_exact_source_build.provenance" | head -n 1)"
  fi

  : >"$provenance"
  {
    printf 'provenance_version=1\n'
    printf 'candidate_sha=%s\n' "$candidate_sha"
    printf 'candidate_tree=%s\n' "$candidate_tree"
    printf 'candidate_source_root=%s\n' "$repo_dir"
    printf 'build_reuse_policy=never;configure_and_clean_build_each_invocation\n'
    printf 'previous_simulator_build_candidate_sha=%s\n' "$previous_sim_sha"
    printf 'previous_probe_build_candidate_sha=%s\n' "$previous_probe_sha"
    printf 'mujoco_root=%s\n' "$mujoco_root"
    printf 'mujoco_root_realpath=%s\n' "$mujoco_realpath"
    printf 'mujoco_header=%s\n' "$mujoco_root/include/mujoco/mujoco.h"
    printf 'mujoco_header_sha256=%s\n' "$(sha256sum "$mujoco_root/include/mujoco/mujoco.h" | awk '{print $1}')"
    printf 'mujoco_library=%s\n' "$mujoco_root/lib/libmujoco.so"
    printf 'mujoco_library_sha256=%s\n' "$(sha256sum "$mujoco_root/lib/libmujoco.so" | awk '{print $1}')"
    printf 'unitree_sdk2_config=%s\n' "$sdk_config"
    printf 'unitree_sdk2_config_sha256=%s\n' "$(sha256sum "$sdk_config" | awk '{print $1}')"
    printf 'unitree_sdk2_archive=%s\n' "$sdk_archive"
    printf 'unitree_sdk2_archive_sha256=%s\n' "$(sha256sum "$sdk_archive" | awk '{print $1}')"
    printf 'simulator_source_dir=%s\n' "$repo_dir/simulate"
    printf 'simulator_build_dir=%s\n' "$sim_build"
    printf 'simulator_configure_command='; printf '%q ' cmake -S "$repo_dir/simulate" -B "$sim_build" -DMUJOCO_ROOT="$mujoco_root" -DCMAKE_BUILD_TYPE=Release; printf '\n'
    printf 'simulator_build_command='; printf '%q ' cmake --build "$sim_build" --target unitree_mujoco --clean-first --parallel 2; printf '\n'
    printf 'probe_source_dir=%s\n' "$cpp_dir"
    printf 'probe_build_dir=%s\n' "$probe_build"
    printf 'probe_configure_command='; printf '%q ' cmake -S "$cpp_dir" -B "$probe_build" -DCMAKE_BUILD_TYPE=Release; printf '\n'
    printf 'probe_build_command='; printf '%q ' cmake --build "$probe_build" --target dds_lowstate_probe --clean-first --parallel 2; printf '\n'
  } >"$provenance"

  if ! cmake -S "$repo_dir/simulate" -B "$sim_build" \
      -DMUJOCO_ROOT="$mujoco_root" -DCMAKE_BUILD_TYPE=Release \
      >"$sim_log" 2>&1; then
    tail -n 80 "$sim_log" >&2 || true
    echo "exact-source simulator configure failed; see $sim_log" >&2
    return 2
  fi
  if ! cmake --build "$sim_build" --target unitree_mujoco \
      --clean-first --parallel 2 >>"$sim_log" 2>&1; then
    tail -n 80 "$sim_log" >&2 || true
    echo "exact-source simulator build failed; see $sim_log" >&2
    return 2
  fi
  if ! cmake -S "$cpp_dir" -B "$probe_build" \
      -DCMAKE_BUILD_TYPE=Release >"$probe_log" 2>&1; then
    tail -n 80 "$probe_log" >&2 || true
    echo "exact-source probe configure failed; see $probe_log" >&2
    return 2
  fi
  if ! cmake --build "$probe_build" --target dds_lowstate_probe \
      --clean-first --parallel 2 >>"$probe_log" 2>&1; then
    tail -n 80 "$probe_log" >&2 || true
    echo "exact-source probe build failed; see $probe_log" >&2
    return 2
  fi
  [[ -f "$simulator" && -x "$simulator" ]] || {
    echo "exact-source simulator output is missing or not executable: $simulator" >&2
    return 2
  }
  [[ -f "$probe" && -x "$probe" ]] || {
    echo "exact-source probe output is missing or not executable: $probe" >&2
    return 2
  }

  {
    printf 'simulator_sha256=%s\n' "$(sha256sum "$simulator" | awk '{print $1}')"
    printf 'simulator_output=%s\n' "$simulator"
    printf 'probe_sha256=%s\n' "$(sha256sum "$probe" | awk '{print $1}')"
    printf 'probe_output=%s\n' "$probe"
    printf 'simulator_build_log=%s\n' "$sim_log"
    printf 'probe_build_log=%s\n' "$probe_log"
  } >>"$provenance"
  {
    printf 'candidate_sha=%s\n' "$candidate_sha"
    printf 'candidate_tree=%s\n' "$candidate_tree"
    printf 'source_dir=%s\n' "$repo_dir/simulate"
    printf 'mujoco_root=%s\n' "$mujoco_root"
    printf 'simulator_sha256=%s\n' "$(sha256sum "$simulator" | awk '{print $1}')"
  } >"$sim_build/go2_exact_source_build.provenance"
  {
    printf 'candidate_sha=%s\n' "$candidate_sha"
    printf 'candidate_tree=%s\n' "$candidate_tree"
    printf 'source_dir=%s\n' "$cpp_dir"
    printf 'probe_sha256=%s\n' "$(sha256sum "$probe" | awk '{print $1}')"
  } >"$probe_build/go2_exact_source_build.provenance"
}

ensure_exact_source_builds
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
