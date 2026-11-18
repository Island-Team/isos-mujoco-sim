#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 || $1 != /* || $2 != /* ]]; then
  echo 'Usage: package_robocasa_setup.sh ABSOLUTE_DATA_DIRECTORY ABSOLUTE_OUTPUT_JSON' >&2
  exit 2
fi

data_dir=$1
output=$2
package_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source_dir="$data_dir/robocasa"
suite="$data_dir/robosuite"
venv="$data_dir/robocasa-venv"
mkdir -p -- "$data_dir"

python3 "$package_root/bin/robocasasource.py" download --path "$source_dir"
if [[ ! -x $venv/bin/python ]]; then
  command -v uv >/dev/null || { echo 'Install uv for RoboCasa Python 3.11 setup' >&2; exit 2; }
  uv venv --python 3.11 --managed-python "$venv"
fi
if [[ ! -f $suite/setup.py ]]; then
  git clone --filter=blob:none --depth 1 https://github.com/ARISE-Initiative/robosuite.git "$suite"
fi
suite_revision=5ce6643f3092639d08f7b0f90ed1c6a84f50552c
if [[ $(git -C "$suite" rev-parse HEAD) != "$suite_revision" ]]; then
  git -C "$suite" fetch --depth 1 origin "$suite_revision"
  git -C "$suite" checkout --detach "$suite_revision"
fi
if [[ ! -f $venv/.robocasa-installed ]]; then
  uv pip install --python "$venv/bin/python" -e "$suite" -e "$source_dir"
  touch "$venv/.robocasa-installed"
fi
if [[ ! -f $source_dir/robocasa/macros_private.py ]]; then
  "$venv/bin/python" -m robocasa.scripts.setup_macros
fi
if [[ ! -f $suite/robosuite/macros_private.py ]]; then
  "$venv/bin/python" -m robosuite.scripts.setup_macros
fi
if [[ ! -f $source_dir/.assets-ready ]]; then
  HF_HOME="$data_dir/huggingface" "$venv/bin/python" "$package_root/bin/robocasaassets.py" "$source_dir"
fi
"$venv/bin/python" - "$source_dir" "$venv" "$output" <<'PY'
import json
from pathlib import Path
import sys
source, venv, output = map(Path, sys.argv[1:])
Path(output).write_text(json.dumps({
    "robocasa_assets": str((source / "robocasa/models/assets").resolve()),
    "python_interpreter": str((venv / "bin/python").absolute()),
}) + "\n")
PY
