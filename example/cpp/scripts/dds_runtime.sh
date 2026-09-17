#!/usr/bin/env bash

# Canonical, source-owned DDS preparation for Go2 launchers.
#
# This file is intentionally a sourceable library.  It never starts a Go2
# process.  Callers acquire the domain lock, prepare the tracked DDS support
# artifact, and explicitly finalize the post-state snapshot when their child
# processes have exited.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "dds_runtime.sh must be sourced by a launcher" >&2
  exit 2
fi

DDS_RUNTIME_VERSION=1
DDS_RUNTIME_PORT_BASE=4000
DDS_RUNTIME_DOMAIN_GAIN=250
DDS_RUNTIME_PARTICIPANT_GAIN=2
DDS_RUNTIME_MAX_AUTO_PARTICIPANT_INDEX=31
DDS_RUNTIME_INTERFACE_DEFAULT=lo
DDS_RUNTIME_TOPIC_LOWSTATE=rt/lowstate
DDS_RUNTIME_SHM_ROOT="${DDS_RUNTIME_SHM_ROOT:-/dev/shm}"
DDS_RUNTIME_LOCK_FD=""
DDS_RUNTIME_LOCK_PATH=""
DDS_RUNTIME_DIR=""
DDS_RUNTIME_PRELOAD=""
DDS_RUNTIME_SUPPORT_SOURCE=""
DDS_RUNTIME_SUPPORT_SOURCE_SHA256=""
DDS_RUNTIME_SUPPORT_ARTIFACT_SHA256=""
DDS_RUNTIME_ORIGINAL_LD_PRELOAD="${LD_PRELOAD:-}"

dds_runtime_error()
{
  echo "DDS runtime error: $*" >&2
  return 1
}

dds_runtime_require_integer()
{
  local name="$1"
  local value="$2"
  if ! [[ "$value" =~ ^[0-9]+$ ]]; then
    dds_runtime_error "$name must be a non-negative integer; got '$value'"
    return 1
  fi
}

dds_runtime_port_list()
{
  local domain="$1"
  dds_runtime_require_integer domain "$domain" || return
  local base=$((DDS_RUNTIME_PORT_BASE + DDS_RUNTIME_DOMAIN_GAIN * domain))
  local participant
  printf 'multicast_meta=%d\n' "$base"
  printf 'multicast_data=%d\n' "$((base + 1))"
  for ((participant = 0; participant <= DDS_RUNTIME_MAX_AUTO_PARTICIPANT_INDEX; participant++)); do
    printf 'p%d_unicast_meta=%d\n' "$participant" \
      "$((base + DDS_RUNTIME_PARTICIPANT_GAIN * participant + 10))"
    printf 'p%d_unicast_data=%d\n' "$participant" \
      "$((base + DDS_RUNTIME_PARTICIPANT_GAIN * participant + 11))"
  done
}

dds_runtime_active_processes()
{
  local self_pid="${1:-$$}"
  local parent_pid="${PPID:-0}"
  ps -eo pid=,comm=,args= | awk -v self="$self_pid" -v parent="$parent_pid" '
    $1 != self && $1 != parent {
      command = $2
      sub(/^.*\//, "", command)
      first_arg = $3
      sub(/^.*\//, "", first_arg)
      if (command == "unitree_mujoco" || command == "real_trot_go2" ||
          command == "dds_lowstate_probe" ||
          first_arg == "unitree_mujoco" || first_arg == "real_trot_go2" ||
          first_arg == "dds_lowstate_probe") print
    }
  '
}

dds_runtime_known_shm()
{
  [[ -d "$DDS_RUNTIME_SHM_ROOT" ]] || return 0
  find "$DDS_RUNTIME_SHM_ROOT" -maxdepth 1 -mindepth 1 \
    \( -name 'cdds*' -o -name 'cyclonedds*' -o -name 'iceoryx*' \) \
    -printf '%f\n' 2>/dev/null | LC_ALL=C sort
}

dds_runtime_snapshot()
{
  local output_path="$1"
  local domain="$2"
  local interface_name="${3:-$DDS_RUNTIME_INTERFACE_DEFAULT}"
  local snapshot_kind="${4:-state}"
  local active_processes
  mkdir -p "$(dirname "$output_path")"
  active_processes="$(dds_runtime_active_processes || true)"
  {
    printf 'snapshot_kind=%s\n' "$snapshot_kind"
    printf 'snapshot_time=%s\n' "$(date --iso-8601=seconds)"
    printf 'domain_id=%s\n' "$domain"
    printf 'interface=%s\n' "$interface_name"
    printf 'cyclonedds_version=0.10.2\n'
    printf 'port_base=%s\n' "$DDS_RUNTIME_PORT_BASE"
    printf 'domain_gain=%s\n' "$DDS_RUNTIME_DOMAIN_GAIN"
    printf 'participant_gain=%s\n' "$DDS_RUNTIME_PARTICIPANT_GAIN"
    printf 'max_auto_participant_index=%s\n' "$DDS_RUNTIME_MAX_AUTO_PARTICIPANT_INDEX"
    printf 'config_source=%s\n' "$DDS_RUNTIME_SUPPORT_SOURCE"
    printf 'config_source_sha256=%s\n' "$DDS_RUNTIME_SUPPORT_SOURCE_SHA256"
    printf 'support_artifact=%s\n' "$DDS_RUNTIME_PRELOAD"
    printf 'support_artifact_sha256=%s\n' "$DDS_RUNTIME_SUPPORT_ARTIFACT_SHA256"
    printf 'original_ld_preload=%s\n' "$DDS_RUNTIME_ORIGINAL_LD_PRELOAD"
    printf 'active_go2_processes_begin\n%s\nactive_go2_processes_end\n' "$active_processes"
    printf 'known_shm_begin\n'
    dds_runtime_known_shm
    printf 'known_shm_end\n'
    printf 'interface_details_begin\n'
    if command -v ip >/dev/null 2>&1; then
      ip -details link show dev "$interface_name" 2>&1 || true
      ip -brief address show dev "$interface_name" 2>&1 || true
    else
      printf 'ip_command=missing\n'
    fi
    printf 'interface_details_end\n'
    printf 'udp_bindings_begin\n'
    if command -v ss >/dev/null 2>&1; then
      ss -H -lunp 2>&1 || true
    elif command -v netstat >/dev/null 2>&1; then
      netstat -lunp 2>&1 || true
    else
      printf 'udp_inspection_command=missing\n'
    fi
    printf 'udp_bindings_end\n'
    printf 'expected_ports_begin\n'
    dds_runtime_port_list "$domain"
    printf 'expected_ports_end\n'
  } >"$output_path"
}

dds_runtime_cleanup_stale()
{
  local active_processes
  active_processes="$(dds_runtime_active_processes || true)"
  if [[ -n "$active_processes" ]]; then
    printf '%s\n' "$active_processes" >&2
    dds_runtime_error "refusing shared-memory cleanup while a Go2 DDS process is active"
    return 2
  fi

  [[ -d "$DDS_RUNTIME_SHM_ROOT" ]] || return 0
  local entry
  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    case "$entry" in
      cdds*|cyclonedds*|iceoryx*)
        rm -rf -- "$DDS_RUNTIME_SHM_ROOT/$entry"
        ;;
      *)
        dds_runtime_error "internal cleanup pattern escaped for '$entry'"
        return 1
        ;;
    esac
  done < <(dds_runtime_known_shm)
}

dds_runtime_find_dds_include()
{
  local candidate
  for candidate in \
    "${DDS_RUNTIME_DDS_INCLUDE:-}" \
    /opt/unitree_robotics/include \
    /usr/local/include \
    /usr/include; do
    [[ -n "$candidate" && -f "$candidate/dds/dds.h" ]] || continue
    printf '%s\n' "$candidate"
    return 0
  done
  return 1
}

dds_runtime_build_support_artifact()
{
  local repo_dir="$1"
  local runtime_dir="$2"
  local include_dir
  include_dir="$(dds_runtime_find_dds_include)" || {
    dds_runtime_error "CycloneDDS headers not found; expected dds/dds.h"
    return 1
  }

  DDS_RUNTIME_SUPPORT_SOURCE="$repo_dir/example/cpp/scripts/dds_base4000_preload.c"
  [[ -f "$DDS_RUNTIME_SUPPORT_SOURCE" ]] || {
    dds_runtime_error "tracked DDS support source is missing: $DDS_RUNTIME_SUPPORT_SOURCE"
    return 1
  }
  mkdir -p "$runtime_dir"
  DDS_RUNTIME_PRELOAD="$runtime_dir/dds_base4000_preload.so"
  gcc -shared -fPIC -O2 -fno-ident -frandom-seed=go2-dds-runtime \
    -Wl,--build-id=none -I"$include_dir" \
    "$DDS_RUNTIME_SUPPORT_SOURCE" -ldl -o "$DDS_RUNTIME_PRELOAD"
  chmod 0555 "$DDS_RUNTIME_PRELOAD"
  DDS_RUNTIME_SUPPORT_SOURCE_SHA256="$(sha256sum "$DDS_RUNTIME_SUPPORT_SOURCE" | awk '{print $1}')"
  DDS_RUNTIME_SUPPORT_ARTIFACT_SHA256="$(sha256sum "$DDS_RUNTIME_PRELOAD" | awk '{print $1}')"
  export DDS_RUNTIME_PRELOAD
  export DDS_RUNTIME_SUPPORT_SOURCE
  export DDS_RUNTIME_SUPPORT_SOURCE_SHA256
  export DDS_RUNTIME_SUPPORT_ARTIFACT_SHA256
  export DDS_RUNTIME_DDS_INCLUDE="$include_dir"
  export LD_PRELOAD="$DDS_RUNTIME_PRELOAD"
}

dds_runtime_write_metadata()
{
  local domain="$1"
  local interface_name="$2"
  local metadata_path="$DDS_RUNTIME_DIR/runtime_metadata.txt"
  {
    printf 'runtime_version=%s\n' "$DDS_RUNTIME_VERSION"
    printf 'domain_id=%s\n' "$domain"
    printf 'interface=%s\n' "$interface_name"
    printf 'topic_lowstate=%s\n' "$DDS_RUNTIME_TOPIC_LOWSTATE"
    printf 'cyclonedds_version=0.10.2\n'
    printf 'port_base=%s\n' "$DDS_RUNTIME_PORT_BASE"
    printf 'domain_gain=%s\n' "$DDS_RUNTIME_DOMAIN_GAIN"
    printf 'participant_gain=%s\n' "$DDS_RUNTIME_PARTICIPANT_GAIN"
    printf 'max_auto_participant_index=%s\n' "$DDS_RUNTIME_MAX_AUTO_PARTICIPANT_INDEX"
    printf 'config_source=%s\n' "$DDS_RUNTIME_SUPPORT_SOURCE"
    printf 'config_source_sha256=%s\n' "$DDS_RUNTIME_SUPPORT_SOURCE_SHA256"
    printf 'support_artifact=%s\n' "$DDS_RUNTIME_PRELOAD"
    printf 'support_artifact_sha256=%s\n' "$DDS_RUNTIME_SUPPORT_ARTIFACT_SHA256"
    printf 'dds_include=%s\n' "${DDS_RUNTIME_DDS_INCLUDE:-}"
    printf 'original_ld_preload=%s\n' "$DDS_RUNTIME_ORIGINAL_LD_PRELOAD"
    printf 'effective_ld_preload=%s\n' "$LD_PRELOAD"
  } >"$metadata_path"
}

dds_runtime_prepare()
{
  local domain="$1"
  local run_dir="$2"
  local repo_dir="$3"
  local interface_name="${4:-$DDS_RUNTIME_INTERFACE_DEFAULT}"

  dds_runtime_require_integer domain "$domain" || return
  if (( domain > 232 )); then
    dds_runtime_error "domain $domain is outside the CycloneDDS port range [0, 232]"
    return 1
  fi
  if [[ -n "${GO2_DDS_PRELOAD:-}" ]]; then
    dds_runtime_error "GO2_DDS_PRELOAD is unsupported; use the tracked canonical artifact"
    return 1
  fi
  if [[ "${LD_PRELOAD:-}" == *dds_base* || "${LD_PRELOAD:-}" == *cyclonedds* ]]; then
    dds_runtime_error "an external DDS preload is already active; hidden DDS setup is not authoritative"
    return 1
  fi
  [[ -d "$DDS_RUNTIME_SHM_ROOT" ]] || {
    dds_runtime_error "DDS shared-memory root does not exist: $DDS_RUNTIME_SHM_ROOT"
    return 1
  }
  command -v flock >/dev/null 2>&1 || {
    dds_runtime_error "flock is required for the per-domain DDS runtime lock"
    return 1
  }

  DDS_RUNTIME_DIR="$run_dir/dds_runtime"
  mkdir -p "$DDS_RUNTIME_DIR"
  DDS_RUNTIME_LOCK_PATH="/tmp/go2_dds_runtime_domain_${domain}.lock"
  if [[ -z "$DDS_RUNTIME_LOCK_FD" ]]; then
    exec {DDS_RUNTIME_LOCK_FD}>"$DDS_RUNTIME_LOCK_PATH"
    if ! flock -n "$DDS_RUNTIME_LOCK_FD"; then
      dds_runtime_error "another canonical DDS runtime is active for domain $domain"
      return 1
    fi
  fi

  dds_runtime_build_support_artifact "$repo_dir" "$DDS_RUNTIME_DIR" || return
  export DDS_RUNTIME_DOMAIN_ID="$domain"
  export DDS_RUNTIME_INTERFACE="$interface_name"
  dds_runtime_snapshot "$DDS_RUNTIME_DIR/pre_state.txt" "$domain" "$interface_name" pre
  dds_runtime_cleanup_stale || return
  dds_runtime_snapshot "$DDS_RUNTIME_DIR/post_clean_state.txt" "$domain" "$interface_name" post_clean
  dds_runtime_write_metadata "$domain" "$interface_name"
}

dds_runtime_boundary()
{
  local label="$1"
  local domain="${DDS_RUNTIME_DOMAIN_ID:?DDS runtime is not prepared}"
  local interface_name="${DDS_RUNTIME_INTERFACE:-$DDS_RUNTIME_INTERFACE_DEFAULT}"
  dds_runtime_snapshot "$DDS_RUNTIME_DIR/${label}_pre_state.txt" "$domain" "$interface_name" "${label}_pre" || return
  dds_runtime_cleanup_stale || return
  dds_runtime_snapshot "$DDS_RUNTIME_DIR/${label}_post_clean_state.txt" "$domain" "$interface_name" "${label}_post_clean" || return
}

dds_runtime_finalize()
{
  [[ -n "$DDS_RUNTIME_DIR" ]] || return 0
  local domain="${DDS_RUNTIME_DOMAIN_ID:?DDS runtime is not prepared}"
  local interface_name="${DDS_RUNTIME_INTERFACE:-$DDS_RUNTIME_INTERFACE_DEFAULT}"
  dds_runtime_snapshot "$DDS_RUNTIME_DIR/post_state.txt" "$domain" "$interface_name" post || return
}
