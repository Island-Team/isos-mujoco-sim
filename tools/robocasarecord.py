#!/usr/bin/env python3
"""Create a small robot hardware demo record or replay a selected local record."""

import argparse
import os
from pathlib import Path

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
  parser = argparse.ArgumentParser(description=__doc__)
  choice = parser.add_mutually_exclusive_group(required=True)
  choice.add_argument("--demo", type=Path, metavar="FILE", help="write a demo hardware record")
  choice.add_argument("--replay", type=Path, metavar="FILE", help="replay a selected local record")
  args = parser.parse_args()
  identity = {"task": "CloseFridge", "split": "target", "seed": 42,
              "camera_width": 64, "camera_height": 64}
  record = load_record(args.replay) if args.replay else identity
  hardware = Hardware(environment(record))
  try:
    if args.demo:
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
