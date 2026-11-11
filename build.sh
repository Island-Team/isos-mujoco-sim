#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo 'Usage: ./build.sh [--output <empty-absolute-directory> --version 0.2.x]' >&2
  exit 2
}

if [[ $# -ne 0 && ( $# -ne 4 || $1 != --output || $2 != /* || $3 != --version || ! $4 =~ ^0\.2\.[0-9]+$ ) ]]; then
  usage
fi
if [[ $# -eq 4 ]]; then
  output=$2
  if [[ -e $output && ! -d $output ]]; then usage; fi
  if [[ -d $output && -n $(find "$output" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
    echo 'Output directory must be empty' >&2
    exit 2
  fi
fi
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$root/tools/launcher.sh"
explicit_mujoco_root=${MUJOCO_ROOT-}
load_launch_config
if [[ -n $explicit_mujoco_root ]]; then
  MUJOCO_ROOT=$explicit_mujoco_root
fi
: "${MUJOCO_ROOT:?Set MUJOCO_ROOT in the environment or .env to a MuJoCo 3.3.1 installation}"
if [[ $# -eq 0 ]]; then
  cmake -S "$root" -B "$root/build" -DMUJOCO_ROOT="$MUJOCO_ROOT" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$root/build" --parallel "${BUILD_JOBS:-4}"
  echo "Built $root/build/eos-mujoco-sim and $root/build/mujoco-core ($SIM_PROFILE profile)"
  if [[ "$SIM_PROFILE" == isos-pkg ]]; then
    echo "IsOS package build is ready; use ./build.sh --output ABSOLUTE_EMPTY_DIRECTORY for a bundle"
    exit 0
  fi
  source_dir=$(resolve_launch_path "${ROBOCASA_ROOT:-.local/robocasa}")
  venv="$root/.local/robocasa-venv"
  if [[ -x "$venv/bin/python" ]] &&
     python3 "$root/tools/robocasasource.py" check --path "$source_dir" >/dev/null 2>&1; then
    "$venv/bin/python" "$root/tools/robocasahrun.py" \
      --task "$BENCHMARK_TASK" --split "$BENCHMARK_SPLIT" \
      --kitchen-scene "$BENCHMARK_SCENE" \
      --seed "$BENCHMARK_SEED" --steps "$BENCHMARK_STEPS" --validate
  fi
  full_assets=false
  if [[ "${BENCHMARK_TASK#robocasa/}" != CloseFridge || -n "$BENCHMARK_SCENE" ]]; then
    full_assets=true
  fi
  if ! python3 "$root/tools/robocasasource.py" check --path "$source_dir" >/dev/null 2>&1 ||
     [[ ! -f "$venv/.robocasa-installed" || ! -f "$source_dir/.assets-ready" ]] ||
     [[ "$full_assets" == true && ! -f "$source_dir/.assets-full-ready" ]]; then
    if [[ "$full_assets" == true ]]; then
      prompt="Configured benchmark needs full RoboCasa assets (about 8 GB compressed, plus extraction) under $source_dir. Download now? [y/N] "
    else
      prompt="RoboCasa source, runtime, or assets are missing. Download and set up under $source_dir? [y/N] "
    fi
    if ! read -r -p "$prompt" answer; then
      echo "RoboCasa setup needs an interactive confirmation; run ./build.sh in a terminal" >&2
      exit 2
    fi
    [[ "$answer" == y || "$answer" == Y ]] || { echo "RoboCasa setup cancelled" >&2; exit 2; }
    if [[ "$full_assets" == true ]]; then
      "$root/tools/robocasasetup.sh" --full
    else
      "$root/tools/robocasasetup.sh"
    fi
  fi
  echo "RoboCasa is ready at $source_dir"
  exit 0
fi
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
cmake -S "$root" -B "$scratch/build" -DMUJOCO_ROOT="$MUJOCO_ROOT" -DCMAKE_BUILD_TYPE=Release
cmake --build "$scratch/build" --parallel "${BUILD_JOBS:-4}"
python3 "$root/tools/bundle.py" \
  --build-dir "$scratch/build" --mujoco-root "$MUJOCO_ROOT" \
  --output "$scratch/bundle" --version "$4"
archive=$(find "$scratch" -maxdepth 1 -type f -name '*.tar.gz' -print -quit)
if [[ -z $archive ]]; then
  echo 'Bundle builder produced no archive' >&2
  exit 1
fi
mkdir -p -- "$output"
cp -- "$scratch/bundle/release.json" "$output/release.json"
cp -- "$archive" "$output/$(basename -- "$archive")"
