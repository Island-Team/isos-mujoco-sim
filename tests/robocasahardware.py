"""Stubbed boundary tests for RoboCasa robot hardware control."""

import unittest

import numpy as np

from robocasa_core import Hardware, HardwareError
from robocasa_core.hardware import ACTION_SHAPES, CAMERA_KEYS, STATE_KEYS, STATE_SHAPES

class Space:
  def __init__(self, shape):
    self.shape = shape


class Spaces:
  def __init__(self, spaces):
    self.spaces = spaces


class Environment:
  def __init__(self):
    self.action_space = Spaces({key: Space(shape) for key, shape in ACTION_SHAPES.items()})
    self.observation_space = Spaces({key: Space(STATE_SHAPES[name])
                                     for name, key in STATE_KEYS.items()})
    self.observation_space.spaces.update({key: Space((8, 8, 3)) for key in CAMERA_KEYS.values()})
    self.actions = []
    self.closed = False
    self.unwrapped = self
    self.control_timestep = 0.05

  def observation(self):
    values = {key: np.zeros(STATE_SHAPES[name], dtype=np.float32)
              for name, key in STATE_KEYS.items()}
    values.update({key: np.zeros((8, 8, 3), dtype=np.uint8) for key in CAMERA_KEYS.values()})
    values["annotation.human.task_description"] = "close fridge"
    values["success"] = True
    return values

  def reset(self, seed):
    self.seed = seed
    return self.observation(), {}

  def step(self, action):
    self.actions.append(action)
    return self.observation(), 1.0, False, False, {"success": True}

  def close(self):
    self.closed = True


class HardwareTests(unittest.TestCase):
  def setUp(self):
    self.env = Environment()
    self.hardware = Hardware(self.env)
    self.hardware.reset(42)

  def test_command_step_uses_selected_environment_timestep(self):
    self.assertEqual(self.hardware.command_step_ms, 50)
    self.env.control_timestep = 0.025
    self.assertEqual(self.hardware.command_step_ms, 25)
    for value in (None, True, 0, -1, float("inf"), float("nan")):
      self.env.control_timestep = value
      with self.subTest(value=value), self.assertRaises(HardwareError):
        _ = self.hardware.command_step_ms
    del self.env.control_timestep
    with self.assertRaises(HardwareError):
      _ = self.hardware.command_step_ms

  def test_catalog_rejects_missing_endpoint(self):
    del self.env.action_space.spaces["action.base_motion"]
    with self.assertRaises(HardwareError):
      Hardware(self.env)

  def test_catalog_rejects_wrong_state_shape(self):
    self.env.observation_space.spaces["state.base_rotation"].shape = (3,)
    with self.assertRaises(HardwareError):
      Hardware(self.env)

  def test_step_rejects_wrong_state_shape(self):
    original = self.env.observation
    def malformed():
      observation = original()
      observation["state.base_rotation"] = np.zeros(3, dtype=np.float32)
      return observation
    self.env.observation = malformed
    with self.assertRaises(HardwareError):
      self.hardware.step()

  def test_combines_groups_and_clears_pending(self):
    self.hardware.command_arm([.1, .2, .3], [-.1, 0, .1])
    self.hardware.command_gripper(True)
    self.hardware.command_base([.2, 0, -.2])
    self.hardware.command_torso([.4])
    self.hardware.set_control_mode(1)
    self.hardware.step()
    action = self.env.actions[-1]
    np.testing.assert_allclose(action["action.end_effector_position"], [.1, .2, .3], atol=1e-7)
    np.testing.assert_allclose(action["action.base_motion"], [.2, 0, -.2, .4], atol=1e-7)
    np.testing.assert_array_equal(action["action.gripper_close"], [1])
    np.testing.assert_array_equal(action["action.control_mode"], [1])
    self.hardware.step()
    neutral = self.env.actions[-1]
    np.testing.assert_array_equal(neutral["action.base_motion"], [0, 0, 0, 0])
    np.testing.assert_array_equal(neutral["action.gripper_close"], [1])
    np.testing.assert_array_equal(neutral["action.control_mode"], [1])

  def test_stop_motion_requires_settled_gripper_and_neutral_motion(self):
    self.hardware.command_gripper(True)
    self.hardware.step()
    self.assertTrue(self.hardware.stop_motion())
    self.assertGreaterEqual(len(self.env.actions), 3)
    for action in self.env.actions[-2:]:
      np.testing.assert_array_equal(action["action.base_motion"], [0, 0, 0, 0])
      np.testing.assert_array_equal(action["action.end_effector_position"], [0, 0, 0])
      np.testing.assert_array_equal(action["action.control_mode"], [0])

  def test_rejects_invalid_commands_without_changing_pending(self):
    self.hardware.command_base([.1, 0, 0])
    for call in (lambda: self.hardware.command_base([float("nan"), 0, 0]),
                 lambda: self.hardware.command_torso([2]),
                 lambda: self.hardware.command_gripper(.5),
                 lambda: self.hardware.command_arm([0, 0], [0, 0, 0])):
      with self.assertRaises(HardwareError):
        call()
    self.hardware.step()
    np.testing.assert_allclose(self.env.actions[-1]["action.base_motion"], [.1, 0, 0, 0], atol=1e-7)

  def test_observation_excludes_benchmark_truth_and_is_copied(self):
    observation = self.hardware.observe()
    self.assertNotIn("success", observation)
    self.assertNotIn("annotation.human.task_description", observation)
    observation["agentview-left"][:] = 255
    self.assertEqual(int(self.hardware.observe()["agentview-left"].max()), 0)

  def test_general_control_ignores_extra_fields_and_requires_usable_control(self):
    self.hardware.control("robocasa/base/mobile-base", {"motion": [.2, 0, 0], "unused": 9})
    with self.assertRaises(HardwareError):
      self.hardware.control("robocasa/base/mobile-base", {"unused": 9})
    with self.assertRaises(HardwareError):
      self.hardware.control("robocasa/camera/agentview-left", {"motion": [0, 0, 0]})
    self.hardware.step()
    np.testing.assert_allclose(self.env.actions[-1]["action.base_motion"], [.2, 0, 0, 0], atol=1e-7)

  def test_general_status_exposes_only_selected_device(self):
    self.assertEqual(set(self.hardware.status("robocasa/base/mobile-base")),
                     {"base_position", "base_rotation"})
    self.assertEqual(set(self.hardware.status("robocasa/camera/agentview-left")),
                     {"agentview-left"})
    with self.assertRaises(HardwareError):
      self.hardware.status("robocasa/torso/torso")

  def test_close_prevents_control(self):
    self.hardware.close()
    self.assertTrue(self.env.closed)
    with self.assertRaises(HardwareError):
      self.hardware.step()

  def test_terminated_episode_requires_reset(self):
    original = self.env.step
    self.env.step = lambda action: (self.env.observation(), 0, True, False, {})
    self.assertIn("base_position", self.hardware.step())
    with self.assertRaises(HardwareError):
      self.hardware.command_base([0, 0, 0])
    self.env.step = original
    self.hardware.reset(42)
    self.hardware.command_base([0, 0, 0])

  def test_failed_step_clears_queue_and_requires_reset(self):
    self.hardware.command_base([.5, 0, 0])
    original = self.env.step
    self.env.step = lambda action: (_ for _ in ()).throw(RuntimeError("step failed"))
    with self.assertRaises(RuntimeError):
      self.hardware.step()
    with self.assertRaises(HardwareError):
      self.hardware.step()
    self.env.step = original
    self.hardware.reset(42)
    self.hardware.step()
    np.testing.assert_array_equal(self.env.actions[-1]["action.base_motion"], [0, 0, 0, 0])


if __name__ == "__main__":
  unittest.main()
