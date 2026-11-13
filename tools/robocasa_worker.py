#!/usr/bin/env python3
"""IsOS-owned, isolated RoboCasa hardware service.

The private socket accepts one bounded JSON request per connection. This worker
owns the Gym environment and serializes every step, so Python is never loaded
into EOS and the GIL does not cross the native node ABI.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import select
import socket
import struct
import threading
import time
from typing import Any


MAX_REQUEST = 65536


def read_exact(stream: socket.socket, count: int) -> bytes:
    result = bytearray()
    while len(result) < count:
        block = stream.recv(count - len(result))
        if not block:
            raise ConnectionError("short frame")
        result.extend(block)
    return bytes(result)


def response(stream: socket.socket, payload: dict[str, Any], binary: bytes = b"") -> None:
    body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
    if len(body) > MAX_REQUEST or len(binary) > 12 * 1024 * 1024:
        raise ValueError("reply exceeds bound")
    stream.sendall(struct.pack("<II", len(body), len(binary)) + body + binary)


def camera_dimension(value: str) -> int:
    try:
        dimension = int(value)
    except ValueError as error:
        raise ValueError("camera dimension must be an integer from 64 to 2048") from error
    if not 64 <= dimension <= 2048:
        raise ValueError("camera dimension must be an integer from 64 to 2048")
    return dimension


def camera_size_from_environment() -> tuple[int, int]:
    return (camera_dimension(os.environ["ISOS_ROBOCASA_CAMERA_WIDTH"]),
            camera_dimension(os.environ["ISOS_ROBOCASA_CAMERA_HEIGHT"]))


def create_hardware(task: str, seed: int, assets: str, width: int, height: int):
    if not assets or not Path(assets).is_dir():
        raise ValueError("configured RoboCasa assets are unavailable")
    os.environ["ROBOSUITE_ASSETS_ROOT"] = assets
    os.environ.setdefault("MUJOCO_GL", "egl")
    import gymnasium as gym
    import robocasa  # noqa: F401
    import robocasa.wrappers.gym_wrapper  # noqa: F401
    from robocasa_core.hardware import Hardware

    env = gym.make(f"robocasa/{task}", seed=seed, split="target",
                   generative_textures=False, camera_widths=width, camera_heights=height)
    hardware = Hardware(env)
    hardware.reset(seed)
    return hardware


class Service:
    def __init__(self, hardware):
        self.hardware = hardware
        self.lock = threading.Lock()
        self.stopped = False
        self.stop_result: dict[str, Any] | None = None
        self.faulted = False
        self.commands: dict[str, dict[str, Any]] = {}
        self.sequence = 0
        self.generation_id = os.environ.get("ISOS_PACKAGE_GENERATION", "")

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        op = request.get("op")
        with self.lock:
            if op in ("command", "stop") and request.get("generation_id", "") != self.generation_id:
                raise ValueError("stale service generation")
            if op == "health":
                return {"version": "2.0.0", "accepted": not self.stopped and not self.faulted,
                        "features": ["strict-socket-v1", "strict-stop-v1"],
                        "timestamp_ns": time.monotonic_ns(),
                        "generation_id": self.generation_id, "sequence": self.sequence}
            if op == "observe":
                if self.stopped or self.faulted:
                    raise ValueError("service is not ready")
                node = request.get("node")
                observation = self.hardware.observe()
                keys = {
                    "robocasa/base/mobile-base": ("base_position", "base_rotation"),
                    "robocasa/arm/right-arm": ("end_effector_position_relative", "end_effector_rotation_relative"),
                    "robocasa/gripper/right-gripper": ("gripper_qpos",),
                    "robocasa/camera/agentview-left": ("agentview-left",),
                    "robocasa/camera/agentview-right": ("agentview-right",),
                    "robocasa/camera/eye-in-hand": ("eye-in-hand",),
                }.get(node)
                if keys is None:
                    raise ValueError("unknown observation device")
                if node.startswith("robocasa/camera/"):
                    image = observation[keys[0]]
                    height, width, channels = image.shape
                    if channels != 3 or not 64 <= width <= 2048 or not 64 <= height <= 2048:
                        raise ValueError("invalid camera shape")
                    return {"generation_id": self.generation_id, "sequence": self.sequence,
                            "timestamp_ns": time.monotonic_ns(), "node": node,
                            "width_px": width, "height_px": height,
                            "_binary": image.tobytes()}
                values = {key: observation[key].tolist() for key in keys}
                return {"generation_id": self.generation_id, "sequence": self.sequence,
                        "timestamp_ns": time.monotonic_ns(), "node": node, "values": values}
            if op == "command":
                if self.stopped or self.faulted:
                    raise ValueError("service is not ready")
                command_id = request.get("command_id")
                if not isinstance(command_id, str) or not 1 <= len(command_id) <= 128:
                    raise ValueError("invalid command ID")
                prior = self.commands.get(command_id)
                if prior is not None:
                    if prior["node"] != request.get("node") or prior["values"] != request.get("values"):
                        raise ValueError("command ID conflict")
                    return prior["result"]
                node = request.get("node")
                values = request.get("values")
                if request.get("control_mode") == "mode" and node == "robocasa/arm/right-arm":
                    self.hardware.set_control_mode(values)
                elif node == "robocasa/base/mobile-base":
                    self.hardware.command_base(values)
                elif node == "robocasa/torso/torso":
                    self.hardware.command_torso(values)
                elif node == "robocasa/arm/right-arm":
                    if not isinstance(values, dict):
                        raise ValueError("arm requires position and rotation")
                    self.hardware.command_arm(values.get("position"), values.get("rotation"))
                elif node == "robocasa/gripper/right-gripper":
                    self.hardware.command_gripper(values)
                else:
                    raise ValueError("unknown command device")
                try:
                    self.hardware.step()
                except Exception:
                    self.faulted = True
                    raise
                self.sequence += 1
                result = {"accepted": True, "sequence": self.sequence,
                          "generation_id": self.generation_id}
                self.commands[command_id] = {"node": node, "values": values, "result": result}
                return result
            if op == "stop":
                if self.stop_result is not None:
                    return self.stop_result
                self.stopped = True
                outcome = "unknown"
                if not self.faulted:
                    try:
                        if self.hardware.stop_motion():
                            self.sequence += 1
                            outcome = "stopped"
                    except Exception:
                        self.faulted = True
                self.stop_result = {"outcome": outcome, "generation_id": self.generation_id,
                        "sequence": self.sequence, "base_stop": outcome,
                        "arm_stop": outcome, "torso_stop": outcome,
                        "gripper_stop": outcome}
                return self.stop_result
            raise ValueError("unsupported operation")


def serve(socket_path: Path, service: Service, stop_event: threading.Event | None = None) -> None:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        raise ValueError("socket path already exists")
    stop_path = Path(str(socket_path) + ".stop")
    if stop_path.exists():
        raise ValueError("stop socket path already exists")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener, \
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stop_listener:
        listener.bind(str(socket_path))
        socket_path.chmod(0o600)
        listener.listen(8)
        stop_listener.bind(str(stop_path))
        stop_path.chmod(0o600)
        stop_listener.listen(8)
        try:
            data_slots = threading.BoundedSemaphore(8)
            def send_data(connection: socket.socket, result: dict[str, Any], binary: bytes) -> None:
                try:
                    with connection:
                        try:
                            response(connection, result, binary)
                        except OSError:
                            pass
                finally:
                    data_slots.release()
            while stop_event is None or not stop_event.is_set():
                ready, _, _ = select.select([listener, stop_listener], [], [], 0.5)
                if not ready:
                    continue
                for chosen in sorted(ready, key=lambda item: item is not stop_listener):
                    connection, _ = chosen.accept()
                    stop_lane = chosen is stop_listener
                    if not stop_lane and not data_slots.acquire(blocking=False):
                        connection.close()
                        continue
                    connection.settimeout(2)
                    try:
                        size, payload_size = struct.unpack("<II", read_exact(connection, 8))
                        if not 0 < size <= MAX_REQUEST or payload_size:
                            raise ValueError("invalid frame size")
                        request = json.loads(read_exact(connection, size))
                        if not isinstance(request, dict):
                            raise ValueError("request must be an object")
                        if stop_lane and request.get("op") not in ("stop", "health"):
                            raise ValueError("stop lane accepts only stop or health")
                        result = service.dispatch(request)
                        binary = result.pop("_binary", b"")
                        reply = {"ok": True, "id": request.get("id"), **result}
                    except (ValueError, ConnectionError, TimeoutError, KeyError) as error:
                        reply = {"ok": False, "error": type(error).__name__}
                        binary = b""
                    if stop_lane:
                        try:
                            response(connection, reply, binary)
                        except OSError:
                            pass
                        connection.close()
                    else:
                        threading.Thread(target=send_data, args=(connection, reply, binary), daemon=True).start()
        finally:
            socket_path.unlink(missing_ok=True)
            stop_path.unlink(missing_ok=True)
            service.hardware.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    args = parser.parse_args()
    task = os.environ.get("ISOS_ROBOCASA_TASK", "CloseFridge")
    seed = int(os.environ.get("ISOS_ROBOCASA_SEED", "42"))
    assets = os.environ.get("ISOS_ROBOCASA_ASSETS", "")
    width, height = camera_size_from_environment()
    serve(args.socket, Service(create_hardware(task, seed, assets, width, height)))


if __name__ == "__main__":
    main()
