"""Fixed-seed RoboCasa hardware replay; run with PYTHONPATH=. from the repo root."""

import os

os.environ.setdefault("MUJOCO_GL", "glfw" if os.name == "nt" else "egl")

import gymnasium as gym
import numpy as np
import robocasa  # noqa: F401 - registers Gym environments
import robocasa.wrappers.gym_wrapper  # noqa: F401 - registers Gym wrapper

from robocasa_core import Hardware


def replay():
  env = gym.make("robocasa/CloseFridge", seed=42, split="target",
                 generative_textures=False, camera_widths=64, camera_heights=64)
  hardware = Hardware(env)
  try:
    first = hardware.reset(42)
    hardware.command_arm([0, 0, 0], [0, 0, 0])
    hardware.command_gripper(False)
    hardware.command_base([0, 0, 0])
    hardware.command_torso([0])
    hardware.set_control_mode(0)
    second = hardware.step()
    assert set(first) == set(second)
    assert len(second) == 8
    for name in ("agentview-left", "agentview-right", "eye-in-hand"):
      assert second[name].shape == (64, 64, 3)
      assert second[name].dtype == np.uint8
    assert "success" not in second and "annotation.human.task_description" not in second
    return {name: np.asarray(value).copy() for name, value in second.items() if name not in
            ("agentview-left", "agentview-right", "eye-in-hand")}
  finally:
    hardware.close()


if __name__ == "__main__":
  one, two = replay(), replay()
  for key in one:
    np.testing.assert_allclose(one[key], two[key], rtol=0, atol=1e-6)
  print("RoboCasa fixed-seed hardware replay passed")
