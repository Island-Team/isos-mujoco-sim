"""Discovery and safety cases independent of optional upstream robot assets."""
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest

import numpy as np

from robocasa_core.body import BodyHardware
from robocasa_core import HardwareError
from tools.robot_graph import build_graph


class Model:
  camera_names = ()
  jnt_axis = np.tile([0, 0, 1.0], (16, 1))
  jnt_type = np.array([2] * 16)

  def joint_id2name(self, index):
    return f"joint_{index}"


class MobileBaseJointVelocityController(SimpleNamespace):
  pass


def controller(size, first=0, **fields):
  cls = fields.pop("_class", SimpleNamespace)
  return cls(qpos_index=list(range(first, first + size)),
                         joint_index=list(range(first, first + size)),
                         input_type="delta", name=fields.pop("name", "JOINT_POSITION"), **fields)


class Environment:
  def __init__(self, parts, arms=()):
    self.control_timestep = .05
    split, offset = {}, 0
    for name, ctrl in parts.items():
      width = 6 if name in arms else len(ctrl.qpos_index)
      split[name] = (offset, offset + width)
      offset += width
    self.cc = SimpleNamespace(part_controllers=parts, _action_split_indexes=split,
                              action_limits=(np.full(offset, -1), np.full(offset, 1)))
    self.robots = [SimpleNamespace(arms=arms, robot_model=SimpleNamespace(naming_prefix="robot0_"),
                                  composite_controller=self.cc)]
    self.sim = SimpleNamespace(model=Model(), data=SimpleNamespace(qpos=np.linspace(.1, 1.6, 16), time=0.0))
    self.raw = {"robot0_gripper_qpos": np.array([.1, .2]), "robot0_base_pos": np.zeros(3),
                "robot0_base_quat": np.array([0, 0, 0, 1.0])}
    self.actions = []
    self.closed = False

  def reset(self):
    return self.raw

  def step(self, action):
    self.actions.append(action)
    self.sim.data.time += self.control_timestep
    return self.raw, 0, False, {}

  def close(self):
    self.closed = True


class BodyTests(unittest.TestCase):
  def test_free_camera_restores_every_shared_camera_field_on_render_failure(self):
    env = Environment({"torso": controller(1)})
    class Camera(SimpleNamespace):
      def __init__(self):
        super().__init__(type=1, fixedcamid=2, trackbodyid=3, orthographic=1,
                         distance=4.0, azimuth=5.0, elevation=6.0, lookat=np.array([7., 8., 9.]))
    camera = Camera()
    env.sim._render_context_offscreen = SimpleNamespace(cam=camera)
    env.sim.model._model = object()
    def defaults(model, target):
      for name in ("type", "fixedcamid", "trackbodyid", "orthographic", "distance", "azimuth", "elevation"):
        setattr(target, name, 0)
      target.lookat[:] = 0
    def render(**kwargs):
      self.assertEqual(kwargs["camera_name"], None)
      self.assertEqual(camera.type, 0)
      raise RuntimeError("render failed")
    env.sim.render = render
    body = BodyHardware(env, {"robocasa/camera/free": (1280, 720)})
    with patch.dict(sys.modules, {"mujoco": SimpleNamespace(MjvCamera=Camera, mjv_defaultFreeCamera=defaults)}):
      with self.assertRaisesRegex(RuntimeError, "render failed"):
        body._filter({})
    expected = Camera()
    for field in ("type", "fixedcamid", "trackbodyid", "orthographic", "distance", "azimuth", "elevation"):
      self.assertEqual(getattr(camera, field), getattr(expected, field))
    np.testing.assert_array_equal(camera.lookat, expected.lookat)

  def test_camera_roles_defaults_and_tuning_do_not_change_control_manifest(self):
    env = Environment({"torso": controller(1)})
    env.sim.model.camera_names = ("robot0_agentview_left",)
    sizes = {"robocasa/camera/agentview-left": (1280, 720), "robocasa/camera/free": (1280, 720)}
    body = BodyHardware(env, sizes)
    roles = {part.node.id: part.metadata.get("view_role") for part in body._parts.values()
             if part.node.group == "camera"}
    self.assertEqual(roles, {"robocasa/camera/agentview-left": "agent",
                             "robocasa/camera/free": "spectator"})
    digest = body.manifest_digest()
    body._camera_sizes = dict.fromkeys(sizes, (640, 360))
    self.assertEqual(body.manifest_digest(), digest)
    graph = build_graph(body.manifest())
    for profile in graph["nodes"].values():
      if profile["node_type"] == "eos.hardware.camera.device@v0.2":
        self.assertEqual(profile["settings"], {"camera_width": 1280, "camera_height": 720,
                         "jpeg_quality": 80, "capture_frequency_hz": 30.0})

  def test_optional_parts_and_real_torso_channels(self):
    env = Environment({"torso": controller(1), "right_gripper": controller(2, 1)})
    body = BodyHardware(env)
    body.reset(42)
    self.assertEqual({item.group for item in body.catalog}, {"torso", "gripper"})
    self.assertEqual(body.channels("robocasa/torso/torso"),
                     [{"name": "joint_0", "value": .1, "unit": "m"}])
    self.assertEqual(body.manifest()["warnings"], [])
    body.control("robocasa/torso/torso", {"motion": [.5]})
    body.step()
    np.testing.assert_array_equal(env.actions[-1], [.5, -1, -1])
    body.step()
    np.testing.assert_array_equal(env.actions[-1], [0, -1, -1])
    graph = build_graph(body.manifest())
    self.assertEqual(len(graph["capabilities"]["controls"]), 2)
    torso = next(item for item in graph["members"] if item["id"] == "robocasa/torso/torso")
    self.assertEqual(torso["type_id"], "joint_channels@v0.1")
    for member in graph["members"]:
      settings = graph["nodes"][member["node"]]["adapter"]["settings"]
      self.assertEqual(settings["frequency_hz"], 10.0)
    self.assertEqual(body.measurement_clock, "simulation")
    self.assertEqual(body.measurement_time_ns, 100_000_000)
    env.sim.data.time += 100  # No measurement occurred: cached sample time stays put.
    body.status("robocasa/torso/torso")
    self.assertEqual(body.measurement_time_ns, 100_000_000)

  def test_missing_optional_observation_does_not_discard_other_parts(self):
    env = Environment({"base": controller(3, name="JOINT_VELOCITY", _class=MobileBaseJointVelocityController,
                                           actuator_min=[-1]*3, actuator_max=[1]*3), "torso": controller(1, 3)})
    del env.raw["robot0_base_pos"]
    body = BodyHardware(env)
    body.reset(0)
    self.assertTrue(body.status("robocasa/torso/torso"))
    self.assertEqual(list(body.status("robocasa/base/mobile-base")), ["base_rotation"])
    self.assertEqual(len(body.manifest()["warnings"]), 1)
    base = next(part for part in body.manifest()["parts"] if part["role"] == "base")
    self.assertFalse(base["can_observe"])
    self.assertFalse(any(member["id"] == base["id"] for member in build_graph(body.manifest())["members"]))
    body.step()
    self.assertEqual(len(body.manifest()["warnings"]), 1)

  def test_unknown_absolute_controller_holds_measured_position(self):
    head = controller(1)
    head.input_type, head.joint_pos = "absolute", np.array([.4])
    env = Environment({"head": head, "torso": controller(1, 1)})
    env.sim.data.qpos[0] = .4
    body = BodyHardware(env)
    body.reset(42)
    body.control("robocasa/torso/torso", {"motion": [.2]})
    body.step()
    np.testing.assert_allclose(env.actions[-1], [.4, .2], atol=1e-7)
    self.assertTrue(body.warnings)

  def test_absolute_torso_is_omitted_and_hold_is_not_scaled(self):
    torso = controller(1, output_min=[10], output_max=[20])
    torso.input_type = "absolute"
    torso.scale_action = lambda value: np.asarray(value) * 5 + 15
    env = Environment({"torso": torso, "right_gripper": controller(2, 1)})
    env.sim.data.qpos[0] = .37
    body = BodyHardware(env)
    body.reset(42)
    self.assertFalse(any(part.group == "torso" for part in body.catalog))
    body.control("robocasa/gripper/right-gripper", {"close": True})
    body.step()
    self.assertEqual(env.actions[-1][0], .37)

  def test_unknown_absolute_and_nonzero_delta_neutral_reject_before_motion(self):
    head = controller(1, name="UNKNOWN")
    head.input_type = "absolute"
    env = Environment({"head": head})
    body = BodyHardware(env)
    body.reset(42)
    with self.assertRaises(HardwareError):
      body.step()
    self.assertEqual(env.actions, [])
    torso = controller(1)
    torso.scale_action = lambda value: np.asarray(value) + 2
    env = Environment({"torso": torso})
    body = BodyHardware(env)
    body.reset(42)
    with self.assertRaises(HardwareError):
      body.step()
    self.assertEqual(env.actions, [])

  def test_generic_multiple_arms_do_not_require_panda_names(self):
    env = Environment({name: controller(7, input_ref_frame="base", name="OSC_POSE") for name in ("left", "right")},
                      arms=("left", "right"))
    body = BodyHardware(env)
    self.assertEqual({part.id for part in body.catalog}, {"robocasa/arm/left-arm", "robocasa/arm/right-arm"})
    for part in body.manifest()["parts"]:
      self.assertIn("axis-angle vector", part["semantics"])
      self.assertIn("not absolute position or Euler", part["semantics"])
      self.assertEqual(part["output_units"], {"translation": "m", "rotation": "rad"})
    for control in build_graph(body.manifest())["capabilities"]["controls"]:
      self.assertIn("axis-angle vector", control["description"])
      self.assertIn('"translation":"m"', control["description"])
    body._observation = {}
    body.control("robocasa/arm/left-arm", {"position": [.1, 0, 0], "rotation": [0, 0, 0]})
    np.testing.assert_allclose(body._pending["robocasa/arm/left-arm"], [.1, 0, 0, 0, 0, 0], atol=1e-7)

  def test_idle_stop_allows_initial_transient_without_weakening_proof(self):
    env = Environment({"torso": controller(1)})
    original = env.step
    def settling(action):
      if len(env.actions) < 13:
        env.sim.data.qpos[0] += .001
      return original(action)
    env.step = settling
    body = BodyHardware(env)
    body.reset(42)
    self.assertTrue(body.stop_motion())
    self.assertEqual(len(env.actions), 15)
    self.assertLessEqual(len(env.actions), 24)

  def test_invalid_control_and_stop_are_fenced(self):
    body = BodyHardware(Environment({"torso": controller(1)}))
    with self.assertRaises(HardwareError):
      body.control("robocasa/torso/torso", {"motion": [0]})
    body.reset(42)
    with self.assertRaises(HardwareError):
      body.control("robocasa/torso/torso", {"motion": [float("nan")]})
    self.assertTrue(body.stop_motion())
    body.close()
    with self.assertRaises(HardwareError):
      body.step()


if __name__ == "__main__":
  unittest.main()
