"""Typed robot endpoints for the pinned RoboCasa PandaOmron Gym wrapper."""

from dataclasses import dataclass
import math
from typing import Any, Mapping

import numpy as np


class HardwareError(ValueError):
  """A hardware endpoint is absent or a command/observation violates its contract."""


@dataclass(frozen=True)
class Node:
  group: str
  name: str
  commands: tuple[str, ...] = ()
  observations: tuple[str, ...] = ()
  unit: str = "normalized"

  @property
  def id(self) -> str:
    return f"robocasa/{self.group}/{self.name}"


CATALOG = (
  Node("arm", "right-arm", ("position", "rotation"),
       ("end_effector_position_relative", "end_effector_rotation_relative")),
  Node("gripper", "right-gripper", ("close",), ("gripper_qpos",), "binary"),
  Node("base", "mobile-base", ("motion",), ("base_position", "base_rotation")),
  Node("torso", "torso", ("motion",)),
  Node("camera", "agentview-left", observations=("image",), unit="RGB8"),
  Node("camera", "agentview-right", observations=("image",), unit="RGB8"),
  Node("camera", "eye-in-hand", observations=("image",), unit="RGB8"),
)

ACTION_SHAPES = {
  "action.end_effector_position": (3,),
  "action.end_effector_rotation": (3,),
  "action.gripper_close": (1,),
  "action.base_motion": (4,),
  "action.control_mode": (1,),
}
STATE_KEYS = {
  "gripper_qpos": "state.gripper_qpos",
  "base_position": "state.base_position",
  "base_rotation": "state.base_rotation",
  "end_effector_position_relative": "state.end_effector_position_relative",
  "end_effector_rotation_relative": "state.end_effector_rotation_relative",
}
STATE_SHAPES = {
  "gripper_qpos": (2,), "base_position": (3,), "base_rotation": (4,),
  "end_effector_position_relative": (3,), "end_effector_rotation_relative": (4,),
}
CAMERA_KEYS = {
  "agentview-left": "video.robot0_agentview_left",
  "agentview-right": "video.robot0_agentview_right",
  "eye-in-hand": "video.robot0_eye_in_hand",
}


def _vector(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
  try:
    vector = np.asarray(value, dtype=np.float32)
  except (TypeError, ValueError) as error:
    raise HardwareError(f"{name}: expected numeric values") from error
  if vector.shape != shape or not np.all(np.isfinite(vector)) or np.any(np.abs(vector) > 1):
    raise HardwareError(f"{name}: expected finite normalized values with shape {shape}")
  return vector.copy()


def _binary(value: Any, name: str) -> int:
  if isinstance(value, (bool, np.bool_)):
    return int(value)
  if isinstance(value, (int, np.integer)) and value in (0, 1):
    return int(value)
  raise HardwareError(f"{name}: expected 0 or 1")


class Hardware:
  """Owns one Gym environment; callers serialize reset, command, step and close.

  Commands are queued until step. A failed environment step clears the queue and
  leaves the episode outcome unknown; callers must reset before further control.
  """

  def __init__(self, env: Any):
    self._env = env
    self._pending: dict[str, Any] = {}
    self._observation: dict[str, Any] | None = None
    self._closed = False
    self._faulted = False
    self._done = False
    self._gripper = 0
    self._mode = 0
    self._check_catalog()

  def _check_catalog(self) -> None:
    action = self._env.action_space.spaces
    observation = self._env.observation_space.spaces
    for key, shape in ACTION_SHAPES.items():
      if key not in action or tuple(action[key].shape) != shape:
        raise HardwareError(f"unsupported RoboCasa action endpoint: {key}")
    for name, key in STATE_KEYS.items():
      if key not in observation or tuple(observation[key].shape) != STATE_SHAPES[name]:
        raise HardwareError(f"unsupported RoboCasa observation endpoint: {key}")
    for key in CAMERA_KEYS.values():
      if key not in observation:
        raise HardwareError(f"unsupported RoboCasa observation endpoint: {key}")
    for key in CAMERA_KEYS.values():
      shape = tuple(observation[key].shape)
      if len(shape) != 3 or shape[2] != 3:
        raise HardwareError(f"unsupported RoboCasa RGB camera shape: {key}")

  @property
  def catalog(self) -> tuple[Node, ...]:
    return CATALOG

  @property
  def command_step_ms(self) -> float:
    """Simulation time advanced by one command, from the selected environment."""
    try:
      seconds = self._env.unwrapped.control_timestep
    except AttributeError as error:
      raise HardwareError("environment command timestep is unavailable") from error
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
      raise HardwareError("environment command timestep must be finite and positive")
    milliseconds = seconds * 1000
    if not math.isfinite(milliseconds):
      raise HardwareError("environment command timestep exceeds bound")
    return milliseconds

  def _ready(self) -> None:
    if self._closed or self._faulted or self._done or self._observation is None:
      raise HardwareError("hardware is not ready; reset the environment")

  def reset(self, seed: int) -> Mapping[str, Any]:
    if self._closed:
      raise HardwareError("hardware is closed")
    self._pending.clear()
    self._observation = None
    self._faulted = True
    self._done = False
    self._gripper = 0
    self._mode = 0
    observation, _ = self._env.reset(seed=seed)
    self._observation = self._filter(observation)
    self._faulted = False
    return self.observe()

  def command_arm(self, position: Any, rotation: Any) -> None:
    self._ready()
    position = _vector(position, (3,), "right-arm position")
    rotation = _vector(rotation, (3,), "right-arm rotation")
    self._pending["arm"] = (position, rotation)

  def command_gripper(self, close: bool | int) -> None:
    self._ready()
    self._pending["gripper"] = _binary(close, "right-gripper")

  def command_base(self, motion: Any) -> None:
    self._ready()
    self._pending["base"] = _vector(motion, (3,), "mobile-base")

  def command_torso(self, motion: Any) -> None:
    self._ready()
    self._pending["torso"] = _vector(motion, (1,), "torso")

  def set_control_mode(self, mode: int) -> None:
    self._ready()
    self._pending["mode"] = _binary(mode, "control mode")

  def control(self, device_id: str, payload: Mapping[str, Any]) -> None:
    """Apply only the selected device's supported control fields."""
    if not isinstance(payload, Mapping):
      raise HardwareError("control payload must be an object")
    if device_id == "robocasa/arm/right-arm":
      if "position" in payload or "rotation" in payload:
        if "position" not in payload or "rotation" not in payload:
          raise HardwareError("arm control requires position and rotation")
        self.command_arm(payload["position"], payload["rotation"])
      elif "mode" in payload:
        self.set_control_mode(payload["mode"])
      else:
        raise HardwareError("arm control has no supported field")
    elif device_id == "robocasa/gripper/right-gripper":
      if "close" not in payload:
        raise HardwareError("gripper control requires close")
      self.command_gripper(payload["close"])
    elif device_id == "robocasa/base/mobile-base":
      if "motion" not in payload:
        raise HardwareError("base control requires motion")
      self.command_base(payload["motion"])
    elif device_id == "robocasa/torso/torso":
      if "motion" not in payload:
        raise HardwareError("torso control requires motion")
      self.command_torso(payload["motion"])
    else:
      raise HardwareError("device has no control interface")

  def status(self, device_id: str) -> Mapping[str, Any]:
    """Return only measured fields of one selected device."""
    self._ready()
    node = next((item for item in CATALOG if item.id == device_id), None)
    if node is None:
      raise HardwareError("unknown status device")
    if not node.observations:
      raise HardwareError("status is unavailable for this device")
    keys = (node.name,) if node.group == "camera" else node.observations
    return {key: self._observation[key].copy() for key in keys}

  def step(self) -> Mapping[str, Any]:
    self._ready()
    pending, self._pending = self._pending, {}
    self._gripper = pending.get("gripper", self._gripper)
    self._mode = pending.get("mode", self._mode)
    arm = pending.get("arm", (np.zeros(3, dtype=np.float32), np.zeros(3, dtype=np.float32)))
    action = {
      "action.end_effector_position": arm[0],
      "action.end_effector_rotation": arm[1],
      "action.gripper_close": np.array([self._gripper], dtype=np.float32),
      "action.base_motion": np.concatenate((pending.get("base", np.zeros(3, dtype=np.float32)),
                                             pending.get("torso", np.zeros(1, dtype=np.float32)))),
      "action.control_mode": np.array([self._mode], dtype=np.float32),
    }
    try:
      observation, _, terminated, truncated, _ = self._env.step(action)
      self._observation = self._filter(observation)
      self._done = bool(terminated or truncated)
    except Exception:
      self._faulted = True
      self._observation = None
      raise
    return {key: value.copy() for key, value in self._observation.items()}

  def stop_motion(self) -> bool:
    """Fence queued motion and prove the latched gripper has settled.

    RoboCasa has no separate gripper brake. A bounded sequence of neutral
    motion steps must show stable finger positions before Stop can be proven.
    """
    self._ready()
    self._pending.clear()
    self._mode = 0
    prior = self._observation["gripper_qpos"].copy()
    stable = 0
    for _ in range(12):
      self.command_arm([0, 0, 0], [0, 0, 0])
      self.command_base([0, 0, 0])
      self.command_torso([0])
      observed = self.step()["gripper_qpos"]
      stable = stable + 1 if np.allclose(observed, prior, rtol=0, atol=1e-4) else 0
      if stable >= 2:
        return True
      prior = observed
    return False

  def _filter(self, observation: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, key in STATE_KEYS.items():
      if key not in observation:
        raise HardwareError(f"missing robot observation: {key}")
      value = np.asarray(observation[key])
      if value.shape != STATE_SHAPES[name] or not np.issubdtype(value.dtype, np.number) or not np.all(np.isfinite(value)):
        raise HardwareError(f"invalid robot observation: {key}")
      result[name] = value.copy()
    for name, key in CAMERA_KEYS.items():
      if key not in observation:
        raise HardwareError(f"missing RGB camera: {key}")
      image = np.asarray(observation[key])
      if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise HardwareError(f"invalid RGB camera: {key}")
      result[name] = image.copy()
    return result

  def observe(self) -> Mapping[str, Any]:
    self._ready()
    return {key: value.copy() for key, value in self._observation.items()}

  def close(self) -> None:
    if not self._closed:
      self._env.close()
      self._closed = True
      self._pending.clear()
      self._observation = None
