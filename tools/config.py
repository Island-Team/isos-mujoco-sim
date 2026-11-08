#!/usr/bin/env python3
"""Print shell-safe assignments from repository and benchmark TOML files."""

import shlex
import sys
import tomllib
from pathlib import Path


KEYS = {
  "MUJOCO_ROOT": str,
  "SIM_PROFILE": str,
  "DEV_GUI": bool,
  "SIM_EXECUTABLE": str,
  "SIM_SCENE": str,
  "SIM_RUN_DIR": str,
  "SIM_GUI": bool,
  "SIM_MANUAL_STEP": bool,
  "ROBOCASA_ROOT": str,
  "BENCHMARK_CONFIG": str,
}

BENCHMARK_FIELDS = {
  "task": {"name": ("BENCHMARK_TASK", str),
           "split": ("BENCHMARK_SPLIT", str),
           "scene": ("BENCHMARK_SCENE", str),
           "seed": ("BENCHMARK_SEED", int),
           "steps": ("BENCHMARK_STEPS", int)},
  "camera": {"name": ("BENCHMARK_CAMERA", str),
             "width": ("BENCHMARK_CAMERA_WIDTH", int),
             "height": ("BENCHMARK_CAMERA_HEIGHT", int)},
  "gui": {"width": ("BENCHMARK_GUI_WIDTH", int)},
}


def print_assignment(key: str, value: object) -> None:
  if isinstance(value, bool):
    value = str(value).lower()
  print(f"{key}={shlex.quote(str(value))}")


def main() -> None:
  root_file = Path(sys.argv[1])
  with root_file.open("rb") as source:
    config = tomllib.load(source)
  unknown = config.keys() - KEYS.keys()
  if unknown:
    raise ValueError(f"Unknown config.toml keys: {', '.join(sorted(unknown))}")
  for key, value in config.items():
    if type(value) is not KEYS[key]:
      raise ValueError(f"{key} must be {KEYS[key].__name__}")
    print_assignment(key, value)

  benchmark_path = Path(config["BENCHMARK_CONFIG"])
  if not benchmark_path.is_absolute():
    benchmark_path = root_file.parent / benchmark_path
  with benchmark_path.open("rb") as source:
    benchmark = tomllib.load(source)
  unknown_sections = benchmark.keys() - BENCHMARK_FIELDS.keys()
  if unknown_sections:
    raise ValueError(f"Unknown benchmark sections: {', '.join(sorted(unknown_sections))}")
  for section, fields in BENCHMARK_FIELDS.items():
    values = benchmark.get(section)
    if not isinstance(values, dict):
      raise ValueError(f"Missing benchmark section: [{section}]")
    unknown_fields = values.keys() - fields.keys()
    missing_fields = fields.keys() - values.keys()
    if unknown_fields or missing_fields:
      raise ValueError(f"Invalid [{section}] keys: unknown={sorted(unknown_fields)}, missing={sorted(missing_fields)}")
    for name, (key, expected_type) in fields.items():
      value = values[name]
      if type(value) is not expected_type:
        raise ValueError(f"[{section}].{name} must be {expected_type.__name__}")
      print_assignment(key, value)


if __name__ == "__main__":
  main()
