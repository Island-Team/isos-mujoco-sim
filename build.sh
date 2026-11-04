#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo 'Usage: build.sh --output <empty-absolute-directory>' >&2
  exit 2
}

if [[ $# -ne 2 || $1 != --output || $2 != /* ]]; then
  usage
fi
output=$2
if [[ -e $output && ! -d $output ]]; then
  usage
fi
if [[ -d $output && -n $(find "$output" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
  echo 'Output directory must be empty' >&2
  exit 2
fi
: "${MUJOCO_ROOT:?Set MUJOCO_ROOT to a MuJoCo 3.16.0 installation}"

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
cmake -S "$root" -B "$scratch/build" -DMUJOCO_ROOT="$MUJOCO_ROOT" -DCMAKE_BUILD_TYPE=Release
cmake --build "$scratch/build" --parallel "${BUILD_JOBS:-4}"
python3 "$root/tools/build-backend-bundle.py" \
  --build-dir "$scratch/build" --mujoco-root "$MUJOCO_ROOT" \
  --output "$scratch/bundle"
archive=$(find "$scratch" -maxdepth 1 -type f -name '*.tar.gz' -print -quit)
if [[ -z $archive ]]; then
  echo 'Bundle builder produced no archive' >&2
  exit 1
fi
mkdir -p -- "$output"
cp -- "$scratch/bundle/release.json" "$output/release.json"
cp -- "$archive" "$output/asset.tar.gz"
