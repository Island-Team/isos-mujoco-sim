"""Local robot command records and deterministic state replay."""

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

import numpy as np

from .hardware import Hardware, HardwareError, STATE_KEYS, STATE_SHAPES, _binary, _vector


VERSION = 1
STATE_NAMES = tuple(STATE_KEYS)
COMMAND_NAMES = ("arm", "gripper", "base", "torso", "mode")


def _state(observation: Mapping[str, Any]) -> dict[str, list[float]]:
  return {name: np.asarray(observation[name], dtype=np.float64).tolist() for name in STATE_NAMES}


def _apply(hardware: Hardware, command: Mapping[str, Any]) -> None:
  if "arm" in command:
    hardware.command_arm(command["arm"]["position"], command["arm"]["rotation"])
  if "gripper" in command:
    hardware.command_gripper(command["gripper"])
  if "base" in command:
    hardware.command_base(command["base"])
  if "torso" in command:
    hardware.command_torso(command["torso"])
  if "mode" in command:
    hardware.set_control_mode(command["mode"])


class EpisodeRecorder:
  """Records explicit group commands and robot state from one reset episode."""

  def __init__(self, hardware: Hardware, *, task: str, split: str, seed: int,
               camera_width: int, camera_height: int):
    if not task or not split or type(seed) is not int or seed < 0:
      raise HardwareError("invalid record identity")
    if not (64 <= camera_width <= 2048 and 64 <= camera_height <= 2048):
      raise HardwareError("invalid camera dimensions")
    self.hardware = hardware
    self.record: dict[str, Any] = {
      "version": VERSION, "layer": "robocasa", "profile": "PandaOmron",
      "task": task, "split": split, "seed": seed,
      "camera_width": camera_width, "camera_height": camera_height,
      "steps": [],
    }
    self._pending: dict[str, Any] = {}
    self._started = False

  def reset(self) -> Mapping[str, Any]:
    self.record["steps"] = []
    self._pending.clear()
    observation = self.hardware.reset(self.record["seed"])
    self.record["initial_state"] = _state(observation)
    self._started = True
    return observation

  def command_arm(self, position: Any, rotation: Any) -> None:
    self.hardware.command_arm(position, rotation)
    self._pending["arm"] = {"position": np.asarray(position).tolist(),
                            "rotation": np.asarray(rotation).tolist()}

  def command_gripper(self, close: bool | int) -> None:
    self.hardware.command_gripper(close)
    self._pending["gripper"] = int(close)

  def command_base(self, motion: Any) -> None:
    self.hardware.command_base(motion)
    self._pending["base"] = np.asarray(motion).tolist()

  def command_torso(self, motion: Any) -> None:
    self.hardware.command_torso(motion)
    self._pending["torso"] = np.asarray(motion).tolist()

  def set_control_mode(self, mode: int) -> None:
    self.hardware.set_control_mode(mode)
    self._pending["mode"] = int(mode)

  def step(self) -> Mapping[str, Any]:
    if not self._started:
      raise HardwareError("reset before recording")
    command, self._pending = self._pending, {}
    observation = self.hardware.step()
    self.record["steps"].append({"command": command, "state": _state(observation)})
    return observation

  def save(self, path: str | Path) -> None:
    if not self._started:
      raise HardwareError("reset before saving")
    target = Path(path)
    if not target.parent.is_dir():
      raise HardwareError("record directory does not exist")
    payload = json.dumps(self.record, sort_keys=True, indent=2, allow_nan=False) + "\n"
    temporary = None
    try:
      with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent,
                                       prefix=f".{target.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
      os.replace(temporary, target)
    finally:
      if temporary is not None:
        temporary.unlink(missing_ok=True)


def load_record(path: str | Path) -> dict[str, Any]:
  source = Path(path)
  if source.stat().st_size > 8_000_000:
    raise HardwareError("record exceeds 8 MB")
  with source.open("r", encoding="utf-8") as stream:
    record = json.load(stream)
  required = {"version", "layer", "profile", "task", "split", "seed", "camera_width",
              "camera_height", "initial_state", "steps"}
  if not isinstance(record, dict) or set(record) != required:
    raise HardwareError("invalid record fields")
  if record["version"] != VERSION or record["layer"] != "robocasa" or record["profile"] != "PandaOmron":
    raise HardwareError("unsupported record version or profile")
  if not isinstance(record["steps"], list) or len(record["steps"]) > 10000:
    raise HardwareError("invalid record steps")
  if not isinstance(record["task"], str) or not record["task"] or not isinstance(record["split"], str):
    raise HardwareError("invalid record identity")
  if type(record["seed"]) is not int or record["seed"] < 0:
    raise HardwareError("invalid record seed")
  for dimension in ("camera_width", "camera_height"):
    if type(record[dimension]) is not int or not 64 <= record[dimension] <= 2048:
      raise HardwareError("invalid camera dimensions")
  _check_state(record["initial_state"])
  for step in record["steps"]:
    if not isinstance(step, dict) or set(step) != {"command", "state"}:
      raise HardwareError("invalid record step")
    command = step["command"]
    if not isinstance(command, dict) or set(command) - set(COMMAND_NAMES):
      raise HardwareError("invalid record command")
    if "arm" in command:
      arm = command["arm"]
      if not isinstance(arm, dict) or set(arm) != {"position", "rotation"}:
        raise HardwareError("invalid recorded arm command")
      _vector(arm["position"], (3,), "recorded arm position")
      _vector(arm["rotation"], (3,), "recorded arm rotation")
    for name, shape in (("base", (3,)), ("torso", (1,))):
      if name in command:
        _vector(command[name], shape, f"recorded {name}")
    for name in ("gripper", "mode"):
      if name in command:
        _binary(command[name], f"recorded {name}")
    _check_state(step["state"])
  return record


def _check_state(state: Any) -> None:
  if not isinstance(state, dict) or set(state) != set(STATE_NAMES):
    raise HardwareError("invalid recorded state")
  for name, value in state.items():
    if not isinstance(value, list):
      raise HardwareError("invalid recorded state values")
    try:
      array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
      raise HardwareError("invalid recorded state values") from error
    if array.shape != STATE_SHAPES[name] or not np.all(np.isfinite(array)):
      raise HardwareError("invalid recorded state values")


def replay_record(hardware: Hardware, record: Mapping[str, Any], *, atol: float = 1e-5) -> int:
  """Reapply selected commands and compare robot state; returns completed step count."""
  if not np.isfinite(atol) or atol < 0:
    raise HardwareError("invalid replay tolerance")
  observation = hardware.reset(record["seed"])
  _compare(observation, record["initial_state"], 0, atol)
  for index, step in enumerate(record["steps"], 1):
    _apply(hardware, step["command"])
    observation = hardware.step()
    _compare(observation, step["state"], index, atol)
  return len(record["steps"])


def _compare(actual: Mapping[str, Any], expected: Mapping[str, Any], step: int,
             atol: float) -> None:
  for name in STATE_NAMES:
    if not np.allclose(actual[name], expected[name], rtol=0, atol=atol):
      raise HardwareError(f"replay state mismatch at step {step}: {name}")
