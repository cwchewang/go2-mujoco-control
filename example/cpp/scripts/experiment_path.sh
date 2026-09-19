#!/usr/bin/env bash

# Resolve the second run_trot positional argument to the canonical experiment
# directory. Accept historical short forms plus the canonical repo-relative
# _runs path used by Praxis TaskSpec.
resolve_go2_experiment_dir()
{
  local repo_dir="$1"
  local cpp_dir="$2"
  local experiment_name="$3"

  if [[ "$experiment_name" == example/cpp/experiments/_runs/* ]]; then
    printf '%s\n' "$repo_dir/$experiment_name"
  elif [[ "$experiment_name" == go2_* || "$experiment_name" == _runs/* ]]; then
    printf '%s\n' "$cpp_dir/experiments/$experiment_name"
  else
    printf '%s\n' "$cpp_dir/experiments/_runs/$experiment_name"
  fi
}
