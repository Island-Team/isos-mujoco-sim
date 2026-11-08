#!/usr/bin/env python3
"""List and run registered RoboCasa tasks with explicit episode settings."""

import argparse
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from difflib import get_close_matches
from io import StringIO
import json
import os
import re
import sys

os.environ.setdefault("MUJOCO_GL", "egl")

quiet = any(flag in sys.argv for flag in ("--list", "--list-kitchens", "--validate"))
with redirect_stdout(StringIO()) if quiet else nullcontext(), \
     redirect_stderr(StringIO()) if quiet else nullcontext():
  import gymnasium as gym  # noqa: E402
  import robocasa  # noqa: F401,E402
  import robocasa.wrappers.gym_wrapper  # noqa: F401,E402
  from robocasa.utils.dataset_registry import (  # noqa: E402
    ATOMIC_TASK_DATASETS,
    COMPOSITE_TASK_DATASETS,
  )
  from robosuite.environments.base import REGISTERED_ENVS  # noqa: E402


DEFAULT_TASK = "CloseFridge"
CAMERAS = ("robot0_agentview_left", "robot0_agentview_right", "robot0_eye_in_hand")
DATASETS = {**ATOMIC_TASK_DATASETS, **COMPOSITE_TASK_DATASETS}


def task_name(value: str) -> str:
  return value.removeprefix("robocasa/")


def available_tasks(split: str) -> dict[str, dict]:
  return {
    name: metadata for name, metadata in DATASETS.items()
    if name in REGISTERED_ENVS and (split == "all" or split in metadata)
  }


def list_tasks(split: str, selected: str, filter_text: str) -> None:
  tasks = available_tasks(split)
  matches = [(name, data) for name, data in sorted(tasks.items())
             if filter_text.casefold() in name.casefold()]
  print(f"RoboCasa {split} tasks: {len(matches)} shown of {len(tasks)} registered")
  print("Selected  Task                           Kind       Horizon  Status")
  for name, data in matches:
    kind = "atomic" if name in ATOMIC_TASK_DATASETS else "composite"
    status = "smoke verified" if name == DEFAULT_TASK else "assets unverified"
    print(f"{'*' if name == selected else ' ':8}  {name:30} {kind:10} {data['horizon']:7}  {status}")
  print("Use ./launch.sh --benchmark TASK [--split target|pretrain|all] [--seed N] [--steps N]")


def list_kitchens(split: str) -> None:
  if split == "target":
    print("RoboCasa target kitchen scene candidates (layout:style):")
    for scene_id in range(1, 11):
      print(f"  {scene_id}:{scene_id}  layout{scene_id:03}:style{scene_id:03}")
  else:
    interval = "11–60" if split == "pretrain" else "1–60"
    print(f"RoboCasa {split} kitchen scenes: layout IDs {interval} × style IDs {interval}")
    print("Any layout/style pair within those ranges can be requested.")
  print("Individual tasks may exclude some kitchen scenes.")
  print("Use ./launch.sh --benchmark TASK --kitchen-scene LAYOUT:STYLE")


def kitchen_scene(value: str, split: str, parser: argparse.ArgumentParser) -> tuple[int, int] | None:
  if not value:
    return None
  if not re.fullmatch(r"[0-9]+:[0-9]+", value):
    parser.error("--kitchen-scene must be LAYOUT:STYLE, for example 1:1")
  layout, style = map(int, value.split(":"))
  if split == "target" and not (1 <= layout <= 10 and layout == style):
    parser.error("target kitchen scenes must be paired 1:1 through 10:10")
  if split == "pretrain" and not (11 <= layout <= 60 and 11 <= style <= 60):
    parser.error("pretrain kitchen layout and style IDs must each be 11–60")
  if split == "all" and not (1 <= layout <= 60 and 1 <= style <= 60):
    parser.error("all kitchen layout and style IDs must each be 1–60")
  return layout, style


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--list", action="store_true", help="list registered tasks for the selected split")
  parser.add_argument("--list-kitchens", action="store_true", help="list kitchen layout and style choices")
  parser.add_argument("--validate", action="store_true", help=argparse.SUPPRESS)
  parser.add_argument("--filter", default="", help="filter listed task names")
  parser.add_argument("--task", "--benchmark", default=DEFAULT_TASK, help="RoboCasa task name")
  parser.add_argument("--split", choices=("target", "pretrain", "all"), default="target")
  parser.add_argument("--kitchen-scene", default="", help="fixed kitchen layout:style pair")
  parser.add_argument("--seed", type=int, default=42)
  parser.add_argument("--steps", type=int, default=20)
  parser.add_argument("--camera", choices=CAMERAS, default=CAMERAS[0], help="camera shown in the GUI")
  parser.add_argument("--camera-width", type=int, default=256, help="rendered observation width")
  parser.add_argument("--camera-height", type=int, default=256, help="rendered observation height")
  parser.add_argument("--gui-width", type=int, default=768, help="display window width in pixels")
  parser.add_argument("--gui", action="store_true", help="show live camera frames and hold the final frame")
  parser.add_argument("--no-gui", dest="gui", action="store_false", help="run without a window")
  args = parser.parse_args()
  selected = task_name(args.task)
  if args.seed < 0 or args.steps < 1:
    parser.error("seed must be nonnegative and steps must be positive")
  if not (64 <= args.camera_width <= 2048 and 64 <= args.camera_height <= 2048):
    parser.error("camera width and height must each be 64–2048")
  if not (256 <= args.gui_width <= 3840):
    parser.error("GUI width must be 256–3840")
  if args.filter and not args.list:
    parser.error("--filter requires --list-benchmarks")
  if args.list:
    list_tasks(args.split, selected, args.filter)
    return
  if args.list_kitchens:
    list_kitchens(args.split)
    return
  scene = kitchen_scene(args.kitchen_scene, args.split, parser)
  tasks = available_tasks(args.split)
  if selected not in tasks:
    suggestions = get_close_matches(selected, tasks, n=3)
    hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
    parser.error(f"task {selected!r} is not registered for split {args.split!r}.{hint} List choices with ./launch.sh --list-benchmarks --split {args.split}")
  if args.validate:
    return
  if args.gui and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    parser.error("GUI needs a desktop display; use --no-gui for a headless run")
  cv2 = None
  if args.gui:
    import cv2 as cv2_module
    cv2 = cv2_module

  def show_frame(observation: dict, delay: int) -> None:
    if cv2 is None:
      return
    frame = observation[f"video.{args.camera}"]
    if frame is not None:
      display_height = round(frame.shape[0] * args.gui_width / frame.shape[1])
      frame = cv2.resize(frame, (args.gui_width, display_height), interpolation=cv2.INTER_LINEAR)
      cv2.imshow("RoboCasa benchmark (press Q or Esc to close)",
                 cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
      cv2.waitKey(delay)

  task = f"robocasa/{selected}"
  scene_kwargs = ({"split": args.split} if scene is None else
                  {"split": None, "obj_instance_split": None if args.split == "all" else args.split,
                   "layout_and_style_ids": [scene]})
  try:
    env = gym.make(task, seed=args.seed, generative_textures=False,
                   camera_widths=args.camera_width, camera_heights=args.camera_height,
                   **scene_kwargs)
  except FileNotFoundError as error:
    parser.error(f"RoboCasa asset is missing: {error.filename}. The local setup provisions the first task's assets; add this task's upstream assets and retry")
  except ValueError as error:
    parser.error(f"RoboCasa could not initialize {task}: {error}. Other tasks may need additional upstream assets")
  try:
    env.action_space.seed(args.seed)
    observation, _ = env.reset(seed=args.seed)
    show_frame(observation, 1)
    instruction = observation["annotation.human.task_description"]
    success = False
    elapsed = 0
    for elapsed in range(1, args.steps + 1):
      action = env.action_space.sample()
      action["action.base_motion"][:] = 0.0
      observation, _, terminated, truncated, info = env.step(action)
      show_frame(observation, 1)
      success = bool(info["success"])
      if success or terminated or truncated:
        break
    actual_scene = f"{env.unwrapped.env.layout_id}:{env.unwrapped.env.style_id}"
    print(json.dumps({"task": task, "split": args.split, "scene": actual_scene,
                      "camera": args.camera, "camera_width": args.camera_width,
                      "camera_height": args.camera_height,
                      "seed": args.seed,
                      "steps": elapsed, "instruction": instruction,
                      "success": success}, sort_keys=True))
    if args.gui:
      print("RoboCasa GUI: press any key in the image window to close.", flush=True)
      cv2.waitKey(0)
  finally:
    env.close()
    if cv2 is not None:
      cv2.destroyAllWindows()


if __name__ == "__main__":
  main()
