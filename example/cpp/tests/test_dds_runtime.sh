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
grep -q '^candidate_path=.* decision=DELETE reason=no_proc_reference$' \
  "$run_dir/dds_runtime/preparation_cleanup.txt"

referenced="$DDS_RUNTIME_SHM_ROOT/cdds_referenced_test"
dds_runtime_reference_matches_candidate "$referenced" "$referenced (deleted)"
if dds_runtime_reference_matches_candidate "$referenced" "${referenced}_sibling"; then
  echo "reference matcher confused a prefix-only sibling" >&2
  exit 1
fi
mkdir -p "$referenced"
fake_proc="$test_root/proc"
mkdir -p "$fake_proc/900/fd"
printf 'fake_dds_owner\n' >"$fake_proc/900/comm"
printf 'fake_dds_owner\0' >"$fake_proc/900/cmdline"
printf '7f000000-7f001000 rw-s 00000000 00:00 0 %s\n' "$referenced" \
  >"$fake_proc/900/maps"
ln -s / "$fake_proc/900/cwd"
ln -s / "$fake_proc/900/root"
ln -s "$referenced" "$fake_proc/900/fd/7"
export DDS_RUNTIME_PROC_ROOT="$fake_proc"
dds_runtime_cleanup_report="$run_dir/dds_runtime/referenced_cleanup.txt"
export DDS_RUNTIME_CLEANUP_REPORT="$dds_runtime_cleanup_report"
if dds_runtime_cleanup_stale; then
  echo "cleanup unexpectedly deleted an object referenced by /proc" >&2
  exit 1
fi
[[ -e "$referenced" ]]
grep -q 'decision=KEEP reason=process_reference_found' \
  "$dds_runtime_cleanup_report"
grep -q 'surface=fd path=' "$dds_runtime_cleanup_report"
grep -q 'surface=maps path=' "$dds_runtime_cleanup_report"

rm -rf -- "$fake_proc/900" "$referenced"
incomplete="$DDS_RUNTIME_SHM_ROOT/cdds_incomplete_test"
mkdir -p "$incomplete" "$fake_proc/901/fd"
printf 'fake_incomplete_owner\n' >"$fake_proc/901/comm"
printf 'fake_incomplete_owner\0' >"$fake_proc/901/cmdline"
: >"$fake_proc/901/maps"
ln -s / "$fake_proc/901/cwd"
ln -s / "$fake_proc/901/root"
rm -rf -- "$fake_proc/901/fd"  # Required fd surface is now unavailable.
if dds_runtime_cleanup_stale; then
  echo "cleanup unexpectedly proceeded with incomplete /proc evidence" >&2
  exit 1
fi
[[ -e "$incomplete" ]]
grep -q 'decision=KEEP reason=process_inspection_incomplete' \
  "$dds_runtime_cleanup_report"
unset DDS_RUNTIME_PROC_ROOT

mkdir -p "$DDS_RUNTIME_SHM_ROOT/cdds_fail_safe_test"
export DDS_RUNTIME_CLEANUP_REPORT="$run_dir/dds_runtime/active_cleanup.txt"
bash -c 'exec -a dds_lowstate_probe sleep 30' &
fake_pid=$!
sleep 0.05
if dds_runtime_cleanup_stale; then
  echo "cleanup unexpectedly proceeded with an active Go2-shaped process" >&2
  exit 1
fi
[[ -e "$DDS_RUNTIME_SHM_ROOT/cdds_fail_safe_test" ]]
grep -q 'decision=KEEP reason=known_go2_process_active' \
  "$DDS_RUNTIME_CLEANUP_REPORT"
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
