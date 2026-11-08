#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$root/tools/launcher.sh"
load_launch_config
scene=$(resolve_launch_path "$SIM_SCENE")
check_only=false
snapshot=""

usage() {
  cat <<'EOF'
Usage: tools/view.sh [--check | --snapshot PATH] [--scene PATH]

Compile the benchmark scene, then open it in MuJoCo's interactive viewer.
--check validates model loading without opening a window.
--snapshot renders a PNG overview without opening a window.
MUJOCO_ROOT must point to the MuJoCo installation containing bin/compile and bin/simulate.
EOF
}

while (($#)); do
  case "$1" in
    --check) check_only=true; shift ;;
    --snapshot)
      if (($# < 2)); then usage >&2; exit 2; fi
      snapshot="$2"; shift 2 ;;
    --scene)
      if (($# < 2)); then usage >&2; exit 2; fi
      scene="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done
if [[ "$check_only" == true && -n "$snapshot" ]]; then
  echo "Choose either --check or --snapshot" >&2
  exit 2
fi

if [[ -z "${MUJOCO_ROOT:-}" || ! -x "$MUJOCO_ROOT/bin/compile" || ! -x "$MUJOCO_ROOT/bin/simulate" ]]; then
  echo "Set MUJOCO_ROOT to an installation with bin/compile and bin/simulate" >&2
  exit 2
fi
if [[ ! -f "$scene" ]]; then
  echo "Scene not found: $scene" >&2
  exit 2
fi
scene=$(realpath "$scene")

"$MUJOCO_ROOT/bin/compile" "$scene"
echo "Scene loaded: $scene"
if [[ "$check_only" == true ]]; then exit 0; fi
if [[ -n "$snapshot" ]]; then
  if [[ ! -x "$MUJOCO_ROOT/bin/render" ]]; then
    echo "MuJoCo bin/render is required for --snapshot" >&2
    exit 2
  fi
  exec "$MUJOCO_ROOT/bin/render" "$scene" "$snapshot" --width=960 --height=720 --azimuth=135 --elevation=-30
fi
if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  echo "A desktop display is required to open the MuJoCo viewer; use --check on headless hosts" >&2
  exit 2
fi
exec "$MUJOCO_ROOT/bin/simulate" "$scene"
