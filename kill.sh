#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tools/launcher.sh"
load_launch_config
umask 077

usage() {
  echo "Usage: ./kill.sh [--run-dir PATH]"
}

run_dir=$SIM_RUN_DIR
while (($#)); do
  case "$1" in
    --run-dir)
      if (($# < 2)); then usage >&2; exit 2; fi
      run_dir=$2; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done
run_dir=$(resolve_launch_path "$run_dir")
if [[ ! -d "$run_dir" ]]; then
  echo "No managed simulator in $run_dir"
  exit 0
fi
private_run_dir "$run_dir" || {
  echo "Run directory must be owned by you and accessible only to you: $run_dir" >&2
  exit 2
}
exec 9>"$run_dir/launcher.lock"
flock -w 10 9 || { echo "Another launcher operation is active" >&2; exit 1; }

sim_file="$run_dir/simulator.pid"
viewer_file="$run_dir/viewer.pid"
clear_stale_for_stop() {
  if { [[ -e "$run_dir/simulator.sock" && ! -S "$run_dir/simulator.sock" ]] ||
       [[ -e "$run_dir/benchmark.sock" && ! -S "$run_dir/benchmark.sock" ]]; }; then
    echo "Non-socket state in $run_dir was left alone" >&2
    return 0
  fi
  clear_stale_sockets "$run_dir/simulator.sock" "$run_dir/benchmark.sock"
}
if [[ ! -f "$sim_file" && ! -f "$viewer_file" ]]; then
  clear_stale_for_stop || exit 1
  echo "No managed process in $run_dir"
  exit 0
fi
terminate_managed "$viewer_file" || true
if terminate_managed "$sim_file"; then
  rm -f -- "$run_dir/simulator.sock" "$run_dir/benchmark.sock"
  echo "Stopped managed processes in $run_dir"
else
  clear_stale_for_stop || exit 1
  echo "No matching managed simulator was running" >&2
fi
