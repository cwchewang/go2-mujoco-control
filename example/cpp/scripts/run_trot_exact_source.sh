#!/usr/bin/env bash
set -euo pipefail

# Exact-source preparation wrapper for the trusted host canary.  This script
# owns build/provenance plumbing only; run_trot.sh remains the single launch
# implementation and receives the original argv unchanged.
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/experiment_path.sh"
cpp_dir="$(cd "$script_dir/.." && pwd)"
repo_dir="$(cd "$cpp_dir/../.." && pwd)"
canonical_runner="$script_dir/run_trot.sh"
simulator="$repo_dir/simulate/build/unitree_mujoco"
controller="$cpp_dir/build/real_trot_go2"
scene_file="$repo_dir/unitree_robots/go2/scene_leg_lift_demo.xml"

# External MuJoCo is a dependency only; simulator/controller are always built
# from the candidate source tree.  Host jobs may set MUJOCO_ROOT explicitly;
# otherwise use the standard per-user MuJoCo installation.
mujoco_root="${MUJOCO_ROOT:-$HOME/.mujoco/mujoco-3.3.6}"
candidate_mujoco_link="$repo_dir/simulate/mujoco"

if (( $# < 2 )); then
  echo "usage: $0 <wall-timeout-s> <experiment-name> [run_trot.sh options ...]" >&2
  exit 2
fi

timeout_arg="$1"
experiment_name="$2"

run_dir="$(resolve_go2_experiment_dir "$repo_dir" "$cpp_dir" "$experiment_name")"

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

created_mujoco_link=false
cleanup_created_dependency_link()
{
  if [[ "$created_mujoco_link" == true && -L "$candidate_mujoco_link" ]]; then
    rm -f -- "$candidate_mujoco_link"
  fi
}
trap cleanup_created_dependency_link EXIT

sha256()
{
  sha256sum "$1" | awk '{print $1}'
}

require_file()
{
  [[ -f "$1" ]] || {
    echo "required file is missing: $1" >&2
    exit 2
  }
}

require_hashable_dependency()
{
  local dependency_realpath
  dependency_realpath="$(readlink -f -- "$mujoco_root")" || {
    echo "unable to resolve permitted MuJoCo root: $mujoco_root" >&2
    exit 2
  }
  [[ -d "$dependency_realpath/include" &&
     -d "$dependency_realpath/lib" &&
     -d "$dependency_realpath/simulate" ]] || {
    echo "permitted MuJoCo SDK is incomplete: $mujoco_root" >&2
    exit 2
  }
  require_file "$mujoco_root/include/mujoco/mujoco.h"
  require_file "$mujoco_root/lib/libmujoco.so"
  require_file "$mujoco_root/simulate/simulate.cc"
}

assert_tracked_worktree_clean()
{
  if [[ -n "$(git -C "$repo_dir" status --porcelain --untracked-files=no)" ]]; then
    echo "candidate worktree has tracked changes; refusing exact-source build" >&2
    git -C "$repo_dir" status --short --untracked-files=no >&2 || true
    exit 2
  fi
}

ensure_dependency_link()
{
  local dependency_realpath existing_realpath
  dependency_realpath="$(readlink -f -- "$mujoco_root")"
  if [[ -e "$candidate_mujoco_link" || -L "$candidate_mujoco_link" ]]; then
    existing_realpath="$(readlink -f -- "$candidate_mujoco_link")" || {
      echo "candidate MuJoCo dependency path cannot be resolved: $candidate_mujoco_link" >&2
      exit 2
    }
    [[ "$existing_realpath" == "$dependency_realpath" ]] || {
      echo "candidate MuJoCo dependency does not resolve to the permitted SDK" >&2
      echo "  path: $candidate_mujoco_link" >&2
      echo "  resolved: $existing_realpath" >&2
      echo "  permitted: $dependency_realpath" >&2
      exit 2
    }
  else
    ln -s -- "$mujoco_root" "$candidate_mujoco_link"
    created_mujoco_link=true
  fi
}

assert_tracked_worktree_clean
require_hashable_dependency
ensure_dependency_link
require_file "$canonical_runner"
require_file "$scene_file"

candidate_sha="$(git -C "$repo_dir" rev-parse HEAD)"
candidate_tree="$(git -C "$repo_dir" rev-parse 'HEAD^{tree}')"
mujoco_realpath="$(readlink -f -- "$mujoco_root")"
sim_build="$repo_dir/simulate/build"
controller_build="$cpp_dir/build"
provenance="$run_dir/build_provenance.txt"
sim_log="$run_dir/simulator_build.log"
controller_log="$run_dir/controller_build.log"
sdk_config="/opt/unitree_robotics/lib/cmake/unitree_sdk2/unitree_sdk2Config.cmake"
sdk_archive="/opt/unitree_robotics/lib/libunitree_sdk2.a"

require_file "$sdk_config"
require_file "$sdk_archive"

{
  printf 'provenance_version=1\n'
  printf 'candidate_sha=%s\n' "$candidate_sha"
  printf 'candidate_tree=%s\n' "$candidate_tree"
  printf 'candidate_source_root=%s\n' "$repo_dir"
  printf 'tracked_worktree_status=clean\n'
  printf 'build_reuse_policy=configure_and_clean_build_each_invocation\n'
  printf 'canonical_runner=%s\n' "$canonical_runner"
  printf 'canonical_runner_sha256=%s\n' "$(sha256 "$canonical_runner")"
  printf 'exact_source_wrapper=%s\n' "$script_dir/run_trot_exact_source.sh"
  printf 'exact_source_wrapper_sha256=%s\n' "$(sha256 "$script_dir/run_trot_exact_source.sh")"
  printf 'task_scene=%s\n' "$scene_file"
  printf 'task_scene_sha256=%s\n' "$(sha256 "$scene_file")"
  printf 'simulator_source_dir=%s\n' "$repo_dir/simulate"
  printf 'simulator_build_dir=%s\n' "$sim_build"
  printf 'controller_source_dir=%s\n' "$cpp_dir"
  printf 'controller_build_dir=%s\n' "$controller_build"
  printf 'mujoco_root=%s\n' "$mujoco_root"
  printf 'mujoco_root_realpath=%s\n' "$mujoco_realpath"
  printf 'mujoco_header=%s\n' "$mujoco_root/include/mujoco/mujoco.h"
  printf 'mujoco_header_sha256=%s\n' "$(sha256 "$mujoco_root/include/mujoco/mujoco.h")"
  printf 'mujoco_library=%s\n' "$mujoco_root/lib/libmujoco.so"
  printf 'mujoco_library_sha256=%s\n' "$(sha256 "$mujoco_root/lib/libmujoco.so")"
  printf 'mujoco_simulate_source=%s\n' "$mujoco_root/simulate/simulate.cc"
  printf 'mujoco_simulate_source_sha256=%s\n' "$(sha256 "$mujoco_root/simulate/simulate.cc")"
  printf 'unitree_sdk2_config=%s\n' "$sdk_config"
  printf 'unitree_sdk2_config_sha256=%s\n' "$(sha256 "$sdk_config")"
  printf 'unitree_sdk2_archive=%s\n' "$sdk_archive"
  printf 'unitree_sdk2_archive_sha256=%s\n' "$(sha256 "$sdk_archive")"
  printf 'simulator_configure_command='; printf '%q ' cmake -S "$repo_dir/simulate" -B "$sim_build" -DMUJOCO_ROOT="$mujoco_root" -DCMAKE_BUILD_TYPE=Release; printf '\n'
  printf 'simulator_build_command='; printf '%q ' cmake --build "$sim_build" --target unitree_mujoco --clean-first --parallel 2; printf '\n'
  printf 'controller_configure_command='; printf '%q ' cmake -S "$cpp_dir" -B "$controller_build" -DCMAKE_BUILD_TYPE=Release; printf '\n'
  printf 'controller_build_command='; printf '%q ' cmake --build "$controller_build" --target real_trot_go2 --clean-first --parallel 2; printf '\n'
  printf 'host_timeout_arg=%q\n' "$timeout_arg"
  printf 'host_experiment_arg=%q\n' "$experiment_name"
  printf 'canonical_argv_shell='
  printf '%q ' "$canonical_runner" "$@"
  printf '\n'
} >"$provenance"

if ! cmake -S "$repo_dir/simulate" -B "$sim_build" \
    -DMUJOCO_ROOT="$mujoco_root" -DCMAKE_BUILD_TYPE=Release \
    >"$sim_log" 2>&1; then
  tail -n 80 "$sim_log" >&2 || true
  echo "exact-source simulator configure failed; see $sim_log" >&2
  exit 2
fi
if ! cmake --build "$sim_build" --target unitree_mujoco \
    --clean-first --parallel 2 >>"$sim_log" 2>&1; then
  tail -n 80 "$sim_log" >&2 || true
  echo "exact-source simulator build failed; see $sim_log" >&2
  exit 2
fi

if ! cmake -S "$cpp_dir" -B "$controller_build" \
    -DCMAKE_BUILD_TYPE=Release >"$controller_log" 2>&1; then
  tail -n 80 "$controller_log" >&2 || true
  echo "exact-source controller configure failed; see $controller_log" >&2
  exit 2
fi
if ! cmake --build "$controller_build" --target real_trot_go2 \
    --clean-first --parallel 2 >>"$controller_log" 2>&1; then
  tail -n 80 "$controller_log" >&2 || true
  echo "exact-source controller build failed; see $controller_log" >&2
  exit 2
fi

[[ -x "$simulator" ]] || {
  echo "exact-source simulator output is missing or not executable: $simulator" >&2
  exit 2
}
[[ -x "$controller" ]] || {
  echo "exact-source controller output is missing or not executable: $controller" >&2
  exit 2
}

{
  printf 'simulator_output=%s\n' "$simulator"
  printf 'simulator_sha256=%s\n' "$(sha256 "$simulator")"
  printf 'controller_output=%s\n' "$controller"
  printf 'controller_sha256=%s\n' "$(sha256 "$controller")"
  printf 'simulator_build_log=%s\n' "$sim_log"
  printf 'controller_build_log=%s\n' "$controller_log"
} >>"$provenance"

# Building must not have changed any tracked candidate file.  Keep the
# dependency symlink alive through the canonical runner because its RPATH is
# the repository's conventional ignored dependency path.  Do not use exec:
# the EXIT trap must remove a symlink created by this wrapper after launch.
assert_tracked_worktree_clean
runner_status=0
bash "$canonical_runner" "$@" || runner_status=$?
exit "$runner_status"
