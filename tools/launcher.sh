#!/usr/bin/env bash

launcher_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

load_launch_config() {
  local assignments
  assignments=$(python3 "$launcher_root/tools/config.py" "$launcher_root/config.toml") || return
  eval "$assignments"
  if [[ -f "$launcher_root/.env" ]]; then
    # Local shell overrides are operator-owned.
    source "$launcher_root/.env"
  fi
  case "$SIM_PROFILE" in
    dev|isos-pkg) ;;
    *) echo "SIM_PROFILE must be dev or isos-pkg" >&2; return 2 ;;
  esac
  [[ "$DEV_GUI" == true || "$DEV_GUI" == false ]] || {
    echo "DEV_GUI must be true or false" >&2; return 2;
  }
}

new_dev_log() {
  local category=$1 directory stamp log
  directory="$launcher_root/logs/dev/$category"
  mkdir -p -m 700 -- "$directory" || return
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  log="$directory/$stamp-$$.log"
  if [[ -e "$directory/latest.log" && ! -L "$directory/latest.log" ]]; then
    echo "Log shortcut is not a symlink: $directory/latest.log" >&2
    return 1
  fi
  ln -sfn -- "$(basename "$log")" "$directory/latest.log" || return
  printf '%s\n' "$log"
}

socket_is_active() {
  local path=$1
  [[ -r /proc/net/unix ]] || return 0
  awk -v path="$path" '$NF == path { found = 1 } END { exit !found }' /proc/net/unix
}

clear_stale_sockets() {
  local first=$1 second=$2 path
  for path in "$first" "$second"; do
    if [[ -e "$path" && ! -S "$path" ]]; then
      echo "Non-socket path blocks startup: $path" >&2
      return 1
    fi
    if [[ -S "$path" ]] && socket_is_active "$path"; then
      echo "Socket is owned by a live process: $path" >&2
      return 1
    fi
  done
  for path in "$first" "$second"; do
    if [[ -S "$path" ]]; then
      rm -- "$path" || return
      echo "Removed stale socket: $path" >&2
    fi
  done
}

resolve_launch_path() {
  if [[ "$1" == /* ]]; then
    realpath -m "$1"
  else
    realpath -m "$launcher_root/$1"
  fi
}

private_run_dir() {
  local directory=$1 mode
  [[ -d "$directory" && -O "$directory" ]] || return 1
  mode=$(stat -c '%a' "$directory") || return 1
  (( (8#$mode & 077) == 0 ))
}

process_start() {
  local pid=$1 stat fields
  [[ "$pid" =~ ^[0-9]+$ && -r "/proc/$pid/stat" ]] || return 1
  stat=$(<"/proc/$pid/stat")
  stat=${stat##*) }
  read -r -a fields <<< "$stat"
  [[ ${#fields[@]} -ge 20 && ${fields[0]} != Z ]] || return 1
  printf '%s\n' "${fields[19]}"
}

managed_pid() {
  local file=$1 pid started current
  [[ -f "$file" ]] || return 1
  read -r pid started < "$file" || return 1
  [[ "$pid" =~ ^[0-9]+$ && "$started" =~ ^[0-9]+$ ]] || return 1
  current=$(process_start "$pid") || return 1
  [[ "$current" == "$started" ]] || return 1
  printf '%s\n' "$pid"
}

record_process() {
  local file=$1 pid=$2 started
  started=$(process_start "$pid") || return 1
  printf '%s %s\n' "$pid" "$started" > "$file"
}

terminate_managed() {
  local file=$1 pid attempt
  if ! pid=$(managed_pid "$file"); then
    rm -f -- "$file"
    return 1
  fi
  kill -TERM "$pid" 2>/dev/null || true
  for ((attempt = 0; attempt < 50; ++attempt)); do
    if ! managed_pid "$file" >/dev/null; then break; fi
    sleep 0.1
  done
  if managed_pid "$file" >/dev/null; then
    kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f -- "$file"
}
