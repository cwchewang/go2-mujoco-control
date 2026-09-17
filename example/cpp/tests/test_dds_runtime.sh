#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:?repository path is required}"
script_dir="$repo_dir/example/cpp/scripts"
source "$script_dir/dds_runtime.sh"

test_root="$(mktemp -d "${TMPDIR:-/tmp}/go2-dds-runtime-test.XXXXXX")"
cleanup_test_root()
{
  if [[ -n "${fake_pid:-}" ]]; then
    kill "$fake_pid" 2>/dev/null || true
    wait "$fake_pid" 2>/dev/null || true
  fi
  rm -rf -- "$test_root"
}
trap cleanup_test_root EXIT

export DDS_RUNTIME_SHM_ROOT="$test_root/shm"
mkdir -p "$DDS_RUNTIME_SHM_ROOT"
mkdir -p "$DDS_RUNTIME_SHM_ROOT/cdds_test_segment"
mkdir -p "$DDS_RUNTIME_SHM_ROOT/iceoryx_test_segment"
touch "$DDS_RUNTIME_SHM_ROOT/cyclonedds_test_file"
touch "$DDS_RUNTIME_SHM_ROOT/unrelated_entry"

run_dir="$test_root/run"
mkdir -p "$run_dir"
dds_runtime_prepare 220 "$run_dir" "$repo_dir" lo

[[ ! -e "$DDS_RUNTIME_SHM_ROOT/cdds_test_segment" ]]
[[ ! -e "$DDS_RUNTIME_SHM_ROOT/iceoryx_test_segment" ]]
[[ ! -e "$DDS_RUNTIME_SHM_ROOT/cyclonedds_test_file" ]]
[[ -e "$DDS_RUNTIME_SHM_ROOT/unrelated_entry" ]]
[[ -s "$DDS_RUNTIME_PRELOAD" ]]
[[ "$(sha256sum "$DDS_RUNTIME_PRELOAD" | awk '{print $1}')" == "$DDS_RUNTIME_SUPPORT_ARTIFACT_SHA256" ]]
grep -q '^domain_id=220$' "$run_dir/dds_runtime/runtime_metadata.txt"
grep -q '^port_base=4000$' "$run_dir/dds_runtime/runtime_metadata.txt"
grep -q '^max_auto_participant_index=31$' "$run_dir/dds_runtime/runtime_metadata.txt"
grep -q '^p0_unicast_meta=59010$' "$run_dir/dds_runtime/pre_state.txt"
grep -q '^p31_unicast_data=59073$' "$run_dir/dds_runtime/pre_state.txt"

mkdir -p "$DDS_RUNTIME_SHM_ROOT/cdds_fail_safe_test"
bash -c 'exec -a dds_lowstate_probe sleep 30' &
fake_pid=$!
sleep 0.05
if dds_runtime_cleanup_stale; then
  echo "cleanup unexpectedly proceeded with an active Go2-shaped process" >&2
  exit 1
fi
[[ -e "$DDS_RUNTIME_SHM_ROOT/cdds_fail_safe_test" ]]
kill "$fake_pid" 2>/dev/null || true
wait "$fake_pid" 2>/dev/null || true
unset fake_pid

dds_runtime_cleanup_stale
[[ ! -e "$DDS_RUNTIME_SHM_ROOT/cdds_fail_safe_test" ]]
[[ -e "$DDS_RUNTIME_SHM_ROOT/unrelated_entry" ]]

dds_runtime_boundary second_cycle
[[ -s "$run_dir/dds_runtime/second_cycle_post_clean_state.txt" ]]
dds_runtime_finalize
[[ -s "$run_dir/dds_runtime/post_state.txt" ]]

echo "DDS runtime deterministic checks passed"
