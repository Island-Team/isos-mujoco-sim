"""Discover supported parts directly from a RoboCasa composite controller.

This adapter deliberately does not use upstream's PandaOmron Gym key converter.
Only robot-prefixed proprioception and selected RGB cameras leave this boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import hashlib
import json
from typing import Any, Mapping

import numpy as np

from .hardware import HardwareError, Node, _binary, _vector


@dataclass
class Part:
  node: Node
  controller_name: str
  start: int
  end: int
  keys: dict[str, str]
  metadata: dict[str, Any]


def _slug(name: str) -> str:
  return name.replace("_", "-").lower()


class BodyHardware:
  """Serialize access to one raw RoboCasa environment and its discovered body."""

  def __init__(self, env: Any, camera_sizes: dict[str, tuple[int, int]] | None = None):
    self._env = env
    self._camera_sizes = camera_sizes or {}
    if len(env.robots) != 1:
      raise HardwareError("RoboCasa adapter supports one robot per world")
    self._robot = env.robots[0]
    self._controller = self._robot.composite_controller
    self._parts: dict[str, Part] = {}
    self._pending: dict[str, np.ndarray] = {}
    self._latched: dict[str, np.ndarray] = {}
    self._observation: dict[str, Any] | None = None
    self._closed = False
    self._faulted = False
    self._done = False
    self._mode = -1.0
    self._controlled_qpos = sorted({int(index) for controller in self._controller.part_controllers.values()
                                    for index in controller.qpos_index})
    self.warnings: list[str] = []
    self._discover()

  def _discover(self) -> None:
    prefix = self._robot.robot_model.naming_prefix
    arms = set(self._robot.arms)
    for name, controller in self._controller.part_controllers.items():
      start, end = self._controller._action_split_indexes[name]
      width = end - start
      keys: dict[str, str] = {}
      meta: dict[str, Any] = {"controller": type(controller).__name__, "unit": "normalized",
                               "input_min": -1, "input_max": 1,
                               "semantics": "one environment control step; no velocity duration integration"}
      if (name in arms and width == 6 and getattr(controller, "input_type", None) == "delta"
          and getattr(controller, "name", "") == "OSC_POSE"):
        group, label = "arm", f"{_slug(name)}-arm"
        frame = getattr(controller, "input_ref_frame", "")
        if frame not in ("base", "world"):
          self.warnings.append(f"{name}: unknown Cartesian command frame; control omitted")
          continue
        meta["semantics"] += ("; Cartesian translation increments and rotation axis-angle vector "
                               "scaled components, not absolute position or Euler angle targets")
        meta["output_units"] = {"translation": "m", "rotation": "rad"}
        meta.update({"axes": ["dx", "dy", "dz", "droll", "dpitch", "dyaw"],
                     "frame": "robot_base" if frame == "base" else "world",
                     "positive_directions": {"dx": "+X", "dy": "+Y", "dz": "+Z",
                       "droll": "right-hand rotation about X", "dpitch": "right-hand rotation about Y",
                       "dyaw": "right-hand rotation about Z"}})
        for attr in ("output_min", "output_max", "actuator_min", "actuator_max"):
          value = getattr(controller, attr, None)
          if value is not None:
            meta[attr] = np.asarray(value).tolist()
        keys = {"end_effector_position_relative": "@eef_position",
                "end_effector_rotation_relative": "@eef_quat"}

      elif name.endswith("_gripper"):
        arm = name.removesuffix("_gripper")
        group, label = "gripper", f"{_slug(arm)}-gripper"
        base = f"{prefix}{arm}_" if len(arms) > 1 else prefix
        keys = {"gripper_qpos": "@qpos"}
        meta.update({"axes": ["close"], "frame": "joint_local",
                     "positive_directions": {"close": "1 closes; 0 opens"},
                     "semantics": "binary latch mapped to the gripper controller's signed input"})
      elif (name == "base" and width == 3 and getattr(controller, "name", "") == "JOINT_VELOCITY"
            and type(controller).__name__ in ("MobileBaseJointVelocityController", "LegacyMobileBaseJointVelocityController")):
        group, label = "base", "mobile-base"
        keys = {"base_position": f"{prefix}base_pos", "base_rotation": f"{prefix}base_quat"}
        meta.update({"axes": ["x", "y", "yaw"], "frame": "base_link",
                     "positive_directions": {"x": "+X in base frame", "y": "+Y in base frame",
                                              "yaw": "right-hand rotation about base Z"}})
      elif (name == "torso" and width == 1 and getattr(controller, "input_type", None) == "delta"
            and getattr(controller, "name", "") == "JOINT_POSITION"):
        group, label = "torso", "torso"
        meta.update({"axes": ["lift"], "frame": "joint_local",
                     "positive_directions": {"lift": "positive controller joint direction; see joint_axis"}})
        # A torso may be prismatic or revolute: preserve actual joint type and axis.
        keys = {"joint_positions": "@qpos"}
        joints = getattr(controller, "qpos_index", [])
        meta["qpos_indices"] = np.asarray(joints).reshape(-1).tolist()
      else:
        self.warnings.append(f"{name}: unsupported {type(controller).__name__} ({width} axes); omitted")
        continue
      for attr in ("output_min", "output_max", "actuator_min", "actuator_max"):
        value = getattr(controller, attr, None)
        if value is not None:
          meta[attr] = np.asarray(value).tolist()
      meta["mapping"] = ("normalized base input uses controller frame transform and actuator bias/weight"
                         if group == "base" else "controller output_min/output_max scaling")
      meta["command_step_ms"] = self.command_step_ms
      if group == "arm" and type(self._controller).__name__ == "HybridMobileBase":
        meta["mode_schema"] = {"type": "object", "additionalProperties": False,
          "required": ["mode"], "properties": {"mode": {"enum": ["0", "1"]}}}
        meta["mode_description"] = "0: arm goals follow achieved pose; 1: goals follow desired pose while base moves"
      if group == "gripper":
        meta["command_schema"] = {"type": "object", "additionalProperties": False,
          "required": ["action"], "properties": {"action": {"enum": ["open", "close"]}}}
      else:
        meta["command_schema"] = {"type": "object", "additionalProperties": False,
          "required": ["axes", "lease_ms"], "properties": {
            "axes": {"type": "object", "additionalProperties": False,
              "required": meta["axes"], "properties": {
                axis: {"type": "number", "minimum": -1, "maximum": 1} for axis in meta["axes"]}},
            "lease_ms": {"type": "integer", "minimum": math.ceil(self.command_step_ms), "maximum": 1000}}}
        meta["stop_payload"] = {"axes": dict.fromkeys(meta["axes"], 0),
                                "lease_ms": math.ceil(self.command_step_ms)}
      meta["joint_axes"] = [self._env.sim.model.jnt_axis[index].tolist()
                              for index in controller.joint_index]
      meta["joint_types"] = [int(self._env.sim.model.jnt_type[index])
                              for index in controller.joint_index]
      meta["joint_names"] = [self._env.sim.model.joint_id2name(index) for index in controller.joint_index]
      meta["qpos_indices"] = np.asarray(controller.qpos_index).reshape(-1).tolist()
      if any(kind not in (2, 3) for kind in meta["joint_types"]):
        self.warnings.append(f"{name}: unsupported non-scalar joint observation; channels omitted")
      if group == "torso":
        meta["positive_directions"]["lift"] = (
          f"positive joint displacement along local axis {meta['joint_axes'][0]}"
          if meta["joint_types"][0] == 2 else
          f"right-hand joint rotation about local axis {meta['joint_axes'][0]}")
      node = Node(group, label, ("command",), tuple(keys))
      self._parts[node.id] = Part(node, name, start, end, keys, meta)
    for camera in self._env.sim.model.camera_names:
      label = _slug(camera.removeprefix(prefix))
      node = Node("camera", label, observations=(label,), unit="RGB8")
      if node.id not in self._camera_sizes:
        continue
      self._parts[node.id] = Part(node, "", 0, 0, {label: f"{camera}_image"},
                                  {"frame": camera, "unit": "RGB8", "axes": []})

    for missing in sorted(set(self._camera_sizes) - set(self._parts)):
      self.warnings.append(f"{missing}: selected camera absent; omitted")

  @property
  def catalog(self) -> tuple[Node, ...]:
    return tuple(part.node for part in self._parts.values())

  @property
  def command_step_ms(self) -> float:
    value = self._env.control_timestep * 1000
    if not math.isfinite(value) or value <= 0:
      raise HardwareError("invalid command timestep")
    return value

  def manifest(self) -> dict[str, Any]:
    return {"robot": type(self._robot.robot_model).__name__, "parts": [
      {"id": part.node.id, "role": part.node.group,
       "can_control": bool(part.node.commands),
       "can_observe": bool(part.keys) and all(f"{part.node.id}:{key}" in (self._observation or {}) for key in part.keys),
       "observation_fields": [key for key in part.keys if f"{part.node.id}:{key}" in (self._observation or {})],
       **part.metadata} for part in self._parts.values()], "warnings": self.warnings[:64]}

  def manifest_digest(self) -> str:
    encoded = json.dumps(self.manifest(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()

  def _ready(self) -> None:
    if self._closed or self._faulted or self._done or self._observation is None:
      raise HardwareError("hardware is not ready; reset the environment")

  def reset(self, seed: int) -> Mapping[str, Any]:
    if self._closed:
      raise HardwareError("hardware is closed")
    self._faulted = True
    self._observation = None
    self._pending.clear()
    self._latched.clear()
    self._mode = -1.0
    self._env.rng = np.random.default_rng(seed)
    self._observation = self._filter(self._env.reset())
    self._faulted = self._done = False
    return self.observe()

  def control(self, device_id: str, payload: Mapping[str, Any]) -> None:
    self._ready()
    part = self._parts.get(device_id)
    if part is None or not part.node.commands:
      raise HardwareError("device has no control interface")
    if part.node.group == "arm" and set(payload) == {"mode"}:
      if "base_mode" not in self._controller._action_split_indexes:
        # HybridMobileBase reserves its last action for mode, outside part splits.
        if type(self._controller).__name__ != "HybridMobileBase":
          raise HardwareError("control mode unavailable")
      self._mode = 1.0 if _binary(payload["mode"], "mode") else -1.0
      return
    if part.node.group == "arm" and set(payload) == {"position", "rotation"}:
      action = np.concatenate((_vector(payload["position"], (3,), "position"),
                               _vector(payload["rotation"], (3,), "rotation")))
    elif part.node.group == "gripper" and set(payload) == {"close"}:
      action = np.full(part.end - part.start,
                       1.0 if _binary(payload["close"], "close") else -1.0)
    elif part.node.group in ("base", "torso") and set(payload) == {"motion"}:
      action = _vector(payload["motion"], (part.end - part.start,), "motion")
    else:
      raise HardwareError("unsupported control fields")
    self._pending[device_id] = action

  def _filter(self, raw: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for part in self._parts.values():
      if part.node.group == "camera":
        width, height = self._camera_sizes[part.node.id]
        camera = part.metadata["frame"]
        raw = dict(raw)
        raw[f"{camera}_image"] = self._env.sim.render(width=width, height=height, camera_name=camera)
      for field, key in tuple(part.keys.items()):
        if key in ("@eef_position", "@eef_quat"):
          from robosuite.utils.transform_utils import mat2quat
          arm = part.controller_name
          controller = self._controller.part_controllers[arm]
          site = self._robot.eef_site_id[arm]
          position = np.asarray(self._env.sim.data.site_xpos[site])
          orientation = np.asarray(self._env.sim.data.site_xmat[site]).reshape(3, 3)
          if part.metadata["frame"] == "robot_base":
            position = controller.origin_ori.T @ (position - controller.origin_pos)
            orientation = controller.origin_ori.T @ orientation
          raw = dict(raw)
          raw[key] = position if key == "@eef_position" else mat2quat(orientation)
        if key == "@qpos":
          raw = dict(raw)
          raw[key] = np.asarray(self._env.sim.data.qpos)[part.metadata["qpos_indices"]]
        if key not in raw:
          warning = f"{part.node.id}: missing observation {key}; field omitted"
          if warning not in self.warnings and len(self.warnings) < 64:
            self.warnings.append(warning)
          continue
        value = np.asarray(raw[key])
        if part.node.group == "camera":
          if value.ndim != 3 or value.shape[-1] != 3 or value.dtype != np.uint8:
            raise HardwareError("invalid RGB observation")
          value = value[::-1].copy()
        elif not np.issubdtype(value.dtype, np.number) or not np.all(np.isfinite(value)):
          raise HardwareError("invalid proprioception")
        result[f"{part.node.id}:{field}"] = value.copy()
    return result

  def observe(self) -> Mapping[str, Any]:
    self._ready()
    return {key: value.copy() for key, value in self._observation.items()}

  def status(self, device_id: str) -> Mapping[str, Any]:
    self._ready()
    part = self._parts.get(device_id)
    if part is None:
      raise HardwareError("unknown status device")
    values = {field: self._observation[f"{device_id}:{field}"].copy()
              for field in part.keys if f"{device_id}:{field}" in self._observation}
    if not values:
      raise HardwareError("status unavailable for device")
    return values

  def channels(self, device_id: str) -> list[dict[str, Any]]:
    self._ready()
    part = self._parts[device_id]
    controller = self._controller.part_controllers[part.controller_name]
    positions = np.asarray(self._env.sim.data.qpos)[controller.qpos_index]
    names = part.metadata["joint_names"]
    kinds = part.metadata["joint_types"]
    if len(names) != len(positions) or any(kind not in (2, 3) for kind in kinds):
      raise HardwareError("joint channels unavailable")
    return [{"name": name, "value": float(value), "unit": "m" if kind == 2 else "rad"}
            for name, value, kind in zip(names, positions, kinds)]

  def step(self) -> Mapping[str, Any]:
    self._ready()
    action = np.zeros(self._controller.action_limits[0].shape, dtype=np.float64)
    for name, controller in self._controller.part_controllers.items():
      start, end = self._controller._action_split_indexes[name]
      kind = getattr(controller, "name", "")
      if name.endswith("_gripper"):
        continue  # Explicit binary latch is filled below.
      if getattr(controller, "input_type", "delta") == "absolute":
        # This pinned controller assigns absolute action directly to goal_qpos.
        # Other controllers may scale/clip, so unknown absolute semantics reject.
        if kind != "JOINT_POSITION" or getattr(controller, "impedance_mode", "fixed") != "fixed":
          raise HardwareError("unsupported absolute controller cannot prove neutral hold")
        indices = getattr(controller, "qpos_index", [])
        current = np.asarray(self._env.sim.data.qpos)[indices]
        if current.shape != (end - start,) or not np.all(np.isfinite(current)):
          raise HardwareError("absolute controller measured hold unavailable")
        action[start:end] = current
      elif kind not in ("OSC_POSE", "JOINT_POSITION", "JOINT_VELOCITY", "JOINT_TORQUE"):
        raise HardwareError("unsupported controller cannot prove neutral action")
      elif type(controller).__name__ in ("MobileBaseJointVelocityController", "LegacyMobileBaseJointVelocityController"):
        if not np.allclose(np.asarray(controller.actuator_min) + np.asarray(controller.actuator_max),
                           0, rtol=0, atol=1e-12):
          raise HardwareError("base actuator bias makes zero input non-neutral")
      elif hasattr(controller, "scale_action"):
        zero = np.asarray(controller.scale_action(np.zeros(end - start)))
        if not np.allclose(zero, 0, rtol=0, atol=1e-12):
          raise HardwareError("controller zero input is not a neutral action")
    pending, self._pending = self._pending, {}
    for identity, part in self._parts.items():
      if not part.node.commands:
        continue
      if part.node.group == "gripper":
        self._latched[identity] = pending.get(identity, self._latched.get(identity, -np.ones(part.end - part.start)))
      action[part.start:part.end] = pending.get(identity, self._latched.get(identity, 0))
    if type(self._controller).__name__ == "HybridMobileBase":
      action[-1] = self._mode
    try:
      raw, _, done, _ = self._env.step(action)
      self._observation = self._filter(raw)
      self._done = bool(done)
    except Exception:
      self._faulted = True
      self._observation = None
      raise
    return self.observe()

  def stop_motion(self) -> bool:
    self._ready()
    self._pending.clear()
    self._mode = -1.0
    # Prove actual commanded joints settled, including control-only torso joints.
    prior = np.asarray(self._env.sim.data.qpos)[self._controlled_qpos].copy()
    stable = 0
    for _ in range(12):
      self.step()
      current = np.asarray(self._env.sim.data.qpos)[self._controlled_qpos].copy()
      stable = stable + 1 if np.allclose(current, prior, rtol=0, atol=1e-4) else 0
      if stable >= 2:
        return True
      prior = current
    return False

  def close(self) -> None:
    if not self._closed:
      self._env.close()
      self._closed = True
      self._pending.clear()
      self._observation = None
