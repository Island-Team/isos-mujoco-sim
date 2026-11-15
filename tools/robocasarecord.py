#!/usr/bin/env python3
"""Create a small robot hardware demo record or replay a selected local record."""

import argparse
import os
from pathlib import Path
import tomllib

os.environ.setdefault("MUJOCO_GL", "glfw" if os.name == "nt" else "egl")

import gymnasium as gym  # noqa: E402
import robocasa  # noqa: F401,E402
import robocasa.wrappers.gym_wrapper  # noqa: F401,E402

from robocasa_core import EpisodeRecorder, Hardware, load_record, replay_record  # noqa: E402


def environment(record):
  return gym.make(f"robocasa/{record['task']}", seed=record["seed"],
                  split=record["split"], generative_textures=False,
                  camera_widths=record["camera_width"],
                  camera_heights=record["camera_height"])


def main():
  root = Path(__file__).resolve().parent.parent
  with (root / "config.toml").open("rb") as source:
    benchmark_path = Path(os.environ.get("BENCHMARK_CONFIG",
                                         tomllib.load(source)["BENCHMARK_CONFIG"]))
  if not benchmark_path.is_absolute():
    benchmark_path = root / benchmark_path
  with benchmark_path.open("rb") as source:
    settings = tomllib.load(source)["record"]
  enabled = os.environ.get("BENCHMARK_RECORD_ENABLED", str(settings["enabled"])).lower()
  if enabled not in ("true", "false"):
    raise ValueError("BENCHMARK_RECORD_ENABLED must be true or false")
  selected_path = os.environ.get("BENCHMARK_RECORD_PATH", settings["path"])
  if not isinstance(selected_path, str) or not selected_path:
    raise ValueError("BENCHMARK_RECORD_PATH must be a nonempty path")
  default_path = Path(selected_path)
  if not default_path.is_absolute():
    default_path = root / default_path
  parser = argparse.ArgumentParser(description=__doc__)
  choice = parser.add_mutually_exclusive_group(required=True)
  choice.add_argument("--demo", nargs="?", const=default_path, type=Path, metavar="FILE",
                      help="write a demo hardware record to FILE or the configured path")
  choice.add_argument("--replay", type=Path, metavar="FILE", help="replay a selected local record")
  args = parser.parse_args()
  if args.demo is not None and enabled == "false":
    parser.error("recording is disabled; set [record].enabled=true or BENCHMARK_RECORD_ENABLED=true")
  if args.demo is not None and args.demo == default_path:
    args.demo.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
  os.umask(0o077)
  identity = {"task": "CloseFridge", "split": "target", "seed": 42,
              "camera_width": 64, "camera_height": 64}
  record = load_record(args.replay) if args.replay else identity
  hardware = Hardware(environment(record))
  try:
    if args.demo is not None:
      writer = EpisodeRecorder(hardware, **identity)
      writer.reset()
      writer.command_arm([0.05, 0, 0], [0, 0.02, 0])
      writer.command_gripper(0)
      writer.command_base([0, 0, 0])
      writer.command_torso([0.05])
      writer.set_control_mode(0)
      writer.step()
      writer.command_arm([0, 0.05, 0], [0, 0, 0.02])
      writer.command_gripper(1)
      writer.command_base([0.02, 0, 0])
      writer.command_torso([0])
      writer.step()
      writer.save(args.demo)
      print(f"saved {len(writer.record['steps'])} hardware steps to {args.demo}")
    else:
      count = replay_record(hardware, record)
      print(f"replayed {count} hardware steps from {args.replay}")
  finally:
    hardware.close()


if __name__ == "__main__":
  main()
