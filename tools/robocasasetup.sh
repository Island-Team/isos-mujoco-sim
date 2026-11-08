#!/usr/bin/env bash
set -euo pipefail

full=false
if [[ ${1:-} == --full && $# -eq 1 ]]; then
  full=true
elif (( $# )); then
  echo "Usage: ./tools/robocasasetup.sh [--full]" >&2
  exit 2
fi

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$root/tools/launcher.sh"
load_launch_config
source_dir=$(resolve_launch_path "${ROBOCASA_ROOT:-.local/robocasa}")
venv="$root/.local/robocasa-venv"
suite="$root/.local/robosuite"

python3 "$root/tools/robocasasource.py" download --path "$source_dir"
if [[ ! -x "$venv/bin/python" ]]; then
  command -v uv >/dev/null || { echo "Install uv to set up RoboCasa's Python 3.11 runtime" >&2; exit 2; }
  uv venv --python 3.11 --managed-python "$venv"
fi
if [[ ! -f "$suite/setup.py" ]]; then
  git clone --filter=blob:none --depth 1 https://github.com/ARISE-Initiative/robosuite.git "$suite"
fi
suite_revision=5ce6643f3092639d08f7b0f90ed1c6a84f50552c
if [[ $(git -C "$suite" rev-parse HEAD) != "$suite_revision" ]]; then
  git -C "$suite" fetch --depth 1 origin "$suite_revision"
  git -C "$suite" checkout --detach "$suite_revision"
fi
if [[ ! -f "$venv/.robocasa-installed" ]]; then
  uv pip install --python "$venv/bin/python" -e "$suite" -e "$source_dir"
  touch "$venv/.robocasa-installed"
fi
if [[ ! -f "$source_dir/robocasa/macros_private.py" ]]; then
  "$venv/bin/python" -m robocasa.scripts.setup_macros
fi
if [[ ! -f "$suite/robosuite/macros_private.py" ]]; then
  "$venv/bin/python" -m robosuite.scripts.setup_macros
fi
if [[ ! -f "$source_dir/.assets-ready" || ( "$full" == true && ! -f "$source_dir/.assets-full-ready" ) ]]; then
  asset_args=()
  if [[ "$full" == true ]]; then asset_args+=(--full); fi
  HF_HOME="$root/.local/huggingface" "$venv/bin/python" "$root/tools/robocasaassets.py" "$source_dir" "${asset_args[@]}"
fi
echo "RoboCasa is ready at $source_dir"
