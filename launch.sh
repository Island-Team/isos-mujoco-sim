#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tools/launcher.sh"
load_launch_config
umask 077

usage() {
  cat <<'EOF'
Usage: ./launch.sh --list-benchmarks [--split target|pretrain|all] [--filter TEXT]
       ./launch.sh --list-kitchens [--split target|pretrain|all]
       ./launch.sh [--robocasa|--benchmark TASK] [--split target|pretrain|all]
                   [--kitchen-scene LAYOUT:STYLE] [--seed N] [--steps N]
                   [--camera NAME] [--camera-width N] [--camera-height N]
                   [--gui-width N]
                   [--gui|--no-gui]
       ./launch.sh --list-scenes
       ./launch.sh --native [--scene pick-place|navigation|PATH]
                   [--gui|--no-gui] [--run-dir PATH] [--executable PATH]
                   [--manual-step]
       ./launch.sh --show-config

SIM_PROFILE=dev runs the configured benchmark with a GUI by default.
SIM_PROFILE=isos-pkg selects the IsOS package profile. Use --benchmark
to run RoboCasa explicitly, or --scene for the local wrapper.
List RoboCasa tasks before selecting one; only CloseFridge has a verified
local smoke run, and other tasks may require more upstream assets.
--scene starts the native compatibility simulator in the background.
--gui opens a separate static viewer, not the live EOS state.
Use ./kill.sh [--run-dir PATH] to stop a native process started here.
EOF
}

case "${1:-}" in
  --help|-h) usage; exit 0 ;;
  --list-scenes) [[ $# -eq 1 ]] || { usage >&2; exit 2; }; python3 "$launcher_root/tools/scenes.py"; exit ;;
  --show-config)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    printf 'Profile: %s | dev GUI: %s\n' "$SIM_PROFILE" "$DEV_GUI"
    printf 'Benchmark config: %s\n' "$(resolve_launch_path "$BENCHMARK_CONFIG")"
    printf 'Benchmark: %s | split=%s kitchen=%s seed=%s steps=%s\n' \
      "$BENCHMARK_TASK" "$BENCHMARK_SPLIT" "${BENCHMARK_SCENE:-random}" "$BENCHMARK_SEED" "$BENCHMARK_STEPS"
    printf 'Camera: %s | render=%sx%s GUI width=%s\n' \
      "$BENCHMARK_CAMERA" "$BENCHMARK_CAMERA_WIDTH" "$BENCHMARK_CAMERA_HEIGHT" "$BENCHMARK_GUI_WIDTH"
    printf 'RoboCasa root: %s\n' "$(resolve_launch_path "${ROBOCASA_ROOT:-.local/robocasa}")"
    printf 'Native scene: %s | executable=%s\n' "$SIM_SCENE" "$SIM_EXECUTABLE"
    exit ;;
esac

if [[ $# -eq 0 && "$SIM_PROFILE" == isos-pkg ]]; then
  echo "IsOS package profile selected. Run ./build.sh --output ABSOLUTE_EMPTY_DIRECTORY to create a package asset; use --benchmark or --scene for a local launch." >&2
  exit 2
fi

camera_args=(--camera "$BENCHMARK_CAMERA" --camera-width "$BENCHMARK_CAMERA_WIDTH"
             --camera-height "$BENCHMARK_CAMERA_HEIGHT" --gui-width "$BENCHMARK_GUI_WIDTH")

if [[ $# -eq 0 || ${1:-} == --robocasa || ${1:-} == --benchmark ||
      ${1:-} == --task || ${1:-} == --seed || ${1:-} == --steps ||
      ${1:-} == --camera || ${1:-} == --camera-width ||
      ${1:-} == --camera-height || ${1:-} == --gui-width ||
      ${1:-} == --split || ${1:-} == --kitchen-scene ||
      ${1:-} == --list-benchmarks || ${1:-} == --list-kitchens ]]; then
  if [[ ${1:-} == --robocasa ]]; then shift; fi
  if [[ ${1:-} == --list-benchmarks || ${1:-} == --list-kitchens ]]; then
    list_option=$1
    shift
    venv="$launcher_root/.local/robocasa-venv"
    source_dir=$(resolve_launch_path "${ROBOCASA_ROOT:-.local/robocasa}")
    if [[ ! -x "$venv/bin/python" ]] ||
       ! python3 "$launcher_root/tools/robocasasource.py" check --path "$source_dir" >/dev/null 2>&1; then
      echo "Run ./build.sh to install the RoboCasa task catalog" >&2
      exit 2
    fi
    exec "$venv/bin/python" "$launcher_root/tools/robocasahrun.py" \
      --task "$BENCHMARK_TASK" --split "$BENCHMARK_SPLIT" \
      --kitchen-scene "$BENCHMARK_SCENE" \
      --seed "$BENCHMARK_SEED" --steps "$BENCHMARK_STEPS" \
      "${camera_args[@]}" \
      "${list_option/--list-benchmarks/--list}" "$@"
  fi
  source_dir=$(resolve_launch_path "${ROBOCASA_ROOT:-.local/robocasa}")
  venv="$launcher_root/.local/robocasa-venv"
  if [[ -x "$venv/bin/python" ]] &&
     python3 "$launcher_root/tools/robocasasource.py" check --path "$source_dir" >/dev/null 2>&1; then
    "$venv/bin/python" "$launcher_root/tools/robocasahrun.py" \
      --task "$BENCHMARK_TASK" --split "$BENCHMARK_SPLIT" \
      --kitchen-scene "$BENCHMARK_SCENE" \
      --seed "$BENCHMARK_SEED" --steps "$BENCHMARK_STEPS" "${camera_args[@]}" "$@" --validate
  fi
  selected_task=${BENCHMARK_TASK#robocasa/}
  selected_kitchen=$BENCHMARK_SCENE
  options=("$@")
  for ((index = 0; index < ${#options[@]}; ++index)); do
    case "${options[index]}" in
      --benchmark|--task)
        if ((index + 1 < ${#options[@]})); then selected_task=${options[index + 1]#robocasa/}; fi ;;
      --kitchen-scene)
        if ((index + 1 < ${#options[@]})); then selected_kitchen=${options[index + 1]}; fi ;;
    esac
  done
  full_assets=false
  if [[ "$selected_task" != CloseFridge || -n "$selected_kitchen" ]]; then full_assets=true; fi
  if ! python3 "$launcher_root/tools/robocasasource.py" check --path "$source_dir" >/dev/null 2>&1 ||
     [[ ! -f "$venv/.robocasa-installed" || ! -f "$source_dir/.assets-ready" ]] ||
     [[ "$full_assets" == true && ! -f "$source_dir/.assets-full-ready" ]]; then
    if [[ "$full_assets" == true ]]; then
      prompt="RoboCasa task or fixed kitchen needs full assets (about 8 GB compressed, plus extraction) under $source_dir. Download now? [y/N] "
    else
      prompt="RoboCasa source, runtime, or assets are missing. Download and set up under $source_dir? [y/N] "
    fi
    read -r -p "$prompt" answer
    [[ "$answer" == y || "$answer" == Y ]] || { echo "RoboCasa setup cancelled" >&2; exit 2; }
    if [[ "$full_assets" == true ]]; then
      "$launcher_root/tools/robocasasetup.sh" --full
    else
      "$launcher_root/tools/robocasasetup.sh"
    fi
  fi
  gui_args=()
  if [[ "$SIM_PROFILE" == dev && "$DEV_GUI" == true ]]; then gui_args+=(--gui); fi
  log=$(new_dev_log robocasa)
  echo "RoboCasa log: $log"
  set +e
  "$venv/bin/python" "$launcher_root/tools/robocasahrun.py" \
    --task "$BENCHMARK_TASK" --split "$BENCHMARK_SPLIT" \
    --kitchen-scene "$BENCHMARK_SCENE" \
    --seed "$BENCHMARK_SEED" --steps "$BENCHMARK_STEPS" "${camera_args[@]}" \
    "${gui_args[@]}" "$@" 2>&1 | tee "$log"
  result=${PIPESTATUS[0]}
  exit "$result"
fi

if [[ ${1:-} == --native ]]; then shift; fi

scene=$SIM_SCENE
run_dir=$SIM_RUN_DIR
executable=$SIM_EXECUTABLE
gui=$SIM_GUI
if [[ "$SIM_PROFILE" == dev ]]; then gui=$DEV_GUI; fi
manual_step=$SIM_MANUAL_STEP
while (($#)); do
  case "$1" in
    --scene|--run-dir|--executable)
      if (($# < 2)); then usage >&2; exit 2; fi
      case "$1" in
        --scene) scene=$2 ;;
        --run-dir) run_dir=$2 ;;
        --executable) executable=$2 ;;
      esac
      shift 2 ;;
    --gui) gui=true; shift ;;
    --no-gui) gui=false; shift ;;
    --manual-step) manual_step=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

case "$scene" in
  pick-place) scene=assets/scene.xml ;;
  navigation) scene=assets/scenes/navigation/scene.xml ;;
esac
scene=$(resolve_launch_path "$scene")
run_dir=$(resolve_launch_path "$run_dir")
executable=$(resolve_launch_path "$executable")
[[ -f "$scene" ]] || { echo "Scene not found: $scene" >&2; exit 2; }
[[ -x "$executable" ]] || { echo "Run ./build.sh first; executable missing: $executable" >&2; exit 2; }
[[ "$gui" == true || "$gui" == false ]] || { echo "SIM_GUI must be true or false" >&2; exit 2; }
[[ "$manual_step" == true || "$manual_step" == false ]] || {
  echo "SIM_MANUAL_STEP must be true or false" >&2; exit 2;
}
if [[ "$gui" == true ]]; then
  [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] || {
    echo "--gui requires a desktop display; use --no-gui on a headless host" >&2
    exit 2
  }
  "$launcher_root/tools/view.sh" --check --scene "$scene" >/dev/null
fi

if [[ ! -e "$run_dir" ]]; then mkdir -p -m 700 -- "$run_dir"; fi
private_run_dir "$run_dir" || {
  echo "Run directory must be owned by you and accessible only to you: $run_dir" >&2
  exit 2
}
exec 9>"$run_dir/launcher.lock"
flock -w 10 9 || { echo "Another launcher operation is active" >&2; exit 1; }
sim_pid_file="$run_dir/simulator.pid"
viewer_pid_file="$run_dir/viewer.pid"
socket="$run_dir/simulator.sock"
benchmark_socket="$run_dir/benchmark.sock"
if managed_pid "$sim_pid_file" >/dev/null || managed_pid "$viewer_pid_file" >/dev/null; then
  echo "A managed process is already running in $run_dir; use ./kill.sh first" >&2
  exit 1
fi
rm -f -- "$sim_pid_file" "$viewer_pid_file"
clear_stale_sockets "$socket" "$benchmark_socket" || exit 1

sim_log=$(new_dev_log native)
viewer_log="${sim_log%.log}-viewer.log"

command=("$executable" --socket "$socket" --benchmark-socket "$benchmark_socket" --scene "$scene")
if [[ "$manual_step" == true ]]; then command+=(--manual-step); fi
nohup "${command[@]}" >"$sim_log" 2>&1 </dev/null 9>&- &
sim_pid=$!
if ! record_process "$sim_pid_file" "$sim_pid"; then
  echo "Simulator exited during startup; see $sim_log" >&2
  exit 1
fi

startup_failed() {
  echo "$1; see $sim_log" >&2
  terminate_managed "$viewer_pid_file" || true
  terminate_managed "$sim_pid_file" || true
  rm -f -- "$socket" "$benchmark_socket"
  exit 1
}

ready=false
for ((attempt = 0; attempt < 100; ++attempt)); do
  if [[ -S "$socket" && -S "$benchmark_socket" ]]; then ready=true; break; fi
  if ! managed_pid "$sim_pid_file" >/dev/null; then break; fi
  sleep 0.1
done
[[ "$ready" == true ]] || startup_failed "Simulator did not open both sockets"

if [[ "$gui" == true ]]; then
  nohup "$launcher_root/tools/view.sh" --scene "$scene" >"$viewer_log" 2>&1 </dev/null 9>&- &
  viewer_pid=$!
  record_process "$viewer_pid_file" "$viewer_pid" || startup_failed "Viewer exited during startup"
  sleep 0.4
  managed_pid "$viewer_pid_file" >/dev/null || startup_failed "Viewer exited during startup"
fi

echo "Simulator started (PID $sim_pid)"
echo "Scene: $scene"
echo "EOS socket: $socket"
echo "Benchmark socket: $benchmark_socket"
echo "Log: $sim_log"
if [[ "$gui" == true ]]; then
  echo "Independent viewer started (PID $viewer_pid); log: $viewer_log"
fi
