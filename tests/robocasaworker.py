#!/usr/bin/env python3
"""Exercise isolated worker admission, deduplication, failure, and Stop."""

import sys
import json
import socket
import struct
import threading
import time
from contextlib import closing
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from robocasa_worker import Service, camera_dimension, camera_size_from_environment, create_hardware, response, serve  # noqa: E402


class FakeHardware:
    def __init__(self):
        self.steps = 0
        self.fail = False
        self.closed = False
        self.commands = []

    def observe(self):
        return {}

    def command_base(self, values):
        self.commands.append(("base", values))

    def command_arm(self, position, rotation):
        self.commands.append(("arm", position, rotation))

    def command_torso(self, values):
        self.commands.append(("torso", values))

    def command_gripper(self, value):
        self.commands.append(("gripper", value))

    def set_control_mode(self, value):
        self.commands.append(("mode", value))

    def step(self):
        if self.fail:
            raise RuntimeError("step failed")
        self.steps += 1

    def stop_motion(self):
        self.step()
        return True

    def close(self):
        self.closed = True


class WorkerTests(unittest.TestCase):
    def test_camera_dimensions_are_bounded(self):
        self.assertEqual(camera_dimension("64"), 64)
        self.assertEqual(camera_dimension("2048"), 2048)
        for value in ("0", "63", "2049", "1.5", "abc"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                camera_dimension(value)

    def test_missing_camera_handoff_is_rejected(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(KeyError):
            camera_size_from_environment()
        with patch.dict("os.environ", {"ISOS_ROBOCASA_CAMERA_WIDTH": "256"}, clear=True), self.assertRaises(KeyError):
            camera_size_from_environment()

    def test_camera_dimensions_reach_gym(self):
        calls = []
        gym = ModuleType("gymnasium")
        gym.make = lambda *args, **kwargs: calls.append((args, kwargs)) or object()
        robocasa = ModuleType("robocasa")
        robocasa.__path__ = []
        wrappers = ModuleType("robocasa.wrappers")
        wrappers.__path__ = []
        gym_wrapper = ModuleType("robocasa.wrappers.gym_wrapper")
        hardware_module = ModuleType("robocasa_core.hardware")
        class HardwareStub:
            def __init__(self, env):
                self.env = env
            def reset(self, seed):
                self.seed = seed
        hardware_module.Hardware = HardwareStub
        modules = {"gymnasium": gym, "robocasa": robocasa,
                   "robocasa.wrappers": wrappers,
                   "robocasa.wrappers.gym_wrapper": gym_wrapper,
                   "robocasa_core.hardware": hardware_module}
        with TemporaryDirectory() as assets, patch.dict(sys.modules, modules):
            hardware = create_hardware("CloseFridge", 42, assets, 1280, 720)
        self.assertEqual(hardware.seed, 42)
        self.assertEqual(calls[0][1]["camera_widths"], 1280)
        self.assertEqual(calls[0][1]["camera_heights"], 720)

    def test_camera_observation_uses_bounded_binary_payload(self):
        class Image:
            shape = (192, 256, 3)
            def tobytes(self):
                return b"\x7f" * (192 * 256 * 3)
        hardware = FakeHardware()
        hardware.observe = lambda: {"agentview-right": Image()}
        result = Service(hardware).dispatch({"op": "observe", "node": "robocasa/camera/agentview-right"})
        binary = result.pop("_binary")
        self.assertEqual((result["width_px"], result["height_px"]), (256, 192))
        sender, receiver = socket.socketpair()
        with closing(sender), closing(receiver):
            response(sender, result, binary)
            metadata_size, payload_size = struct.unpack("<II", receiver.recv(8))
            self.assertLess(metadata_size, 65536)
            self.assertEqual(payload_size, len(binary))
            self.assertEqual(json.loads(receiver.recv(metadata_size))["width_px"], 256)

    def test_maximum_camera_observation(self):
        class Image:
            shape = (2048, 2048, 3)
            def tobytes(self):
                return b"\x7f" * (2048 * 2048 * 3)
        hardware = FakeHardware()
        hardware.observe = lambda: {"agentview-right": Image()}
        result = Service(hardware).dispatch({"op": "observe", "node": "robocasa/camera/agentview-right"})
        self.assertEqual((result["width_px"], result["height_px"]), (2048, 2048))
        self.assertEqual(len(result["_binary"]), 12 * 1024 * 1024)

    def test_stop_lane_preempts_slow_camera_reader(self):
        class Image:
            shape = (512, 512, 3)
            def tobytes(self):
                return b"\x7f" * (512 * 512 * 3)
        hardware = FakeHardware()
        hardware.observe = lambda: {"agentview-right": Image()}
        service = Service(hardware)
        stopped = threading.Event()
        with TemporaryDirectory() as root:
            path = Path(root) / "worker.sock"
            server = threading.Thread(target=serve, args=(path, service, stopped), daemon=True)
            server.start()
            for _ in range(100):
                if path.exists() and Path(str(path) + ".stop").exists():
                    break
                time.sleep(0.01)
            with socket.socket(socket.AF_UNIX) as slow:
                slow.connect(str(path))
                request = json.dumps({"op": "observe", "node": "robocasa/camera/agentview-right"}).encode()
                slow.sendall(struct.pack("<II", len(request), 0) + request)
                time.sleep(0.05)
                started = time.monotonic()
                with socket.socket(socket.AF_UNIX) as stop:
                    stop.settimeout(1)
                    stop.connect(str(path) + ".stop")
                    request = json.dumps({"op": "stop", "generation_id": service.generation_id}).encode()
                    stop.sendall(struct.pack("<II", len(request), 0) + request)
                    metadata_size, payload_size = struct.unpack("<II", stop.recv(8))
                    self.assertEqual(payload_size, 0)
                    self.assertEqual(json.loads(stop.recv(metadata_size))["outcome"], "stopped")
                self.assertLess(time.monotonic() - started, 1)
            stopped.set()
            server.join(2)
            self.assertFalse(server.is_alive())

    def test_duplicate_command_does_not_step_twice(self):
        hardware = FakeHardware()
        service = Service(hardware)
        command = {"op": "command", "node": "robocasa/base/mobile-base",
                   "command_id": "c-1", "values": [0.1, 0, 0]}
        first = service.dispatch(command)
        self.assertEqual(first, service.dispatch(command))
        self.assertEqual(hardware.steps, 1)
        with self.assertRaises(ValueError):
            service.dispatch(command | {"values": [0.2, 0, 0]})
        self.assertEqual(service.dispatch({"op": "stop"})["outcome"], "stopped")
        self.assertEqual(hardware.steps, 2)
        self.assertEqual(service.dispatch({"op": "stop"})["outcome"], "stopped")
        self.assertEqual(hardware.steps, 2)
        with self.assertRaises(ValueError):
            service.dispatch(command | {"command_id": "c-2"})

    def test_step_failure_fences_commands_and_unknown_stop(self):
        hardware = FakeHardware()
        hardware.fail = True
        service = Service(hardware)
        with self.assertRaises(RuntimeError):
            service.dispatch({"op": "command", "node": "robocasa/gripper/right-gripper",
                              "command_id": "c-1", "values": 1})
        self.assertFalse(service.dispatch({"op": "health"})["accepted"])
        self.assertEqual(service.dispatch({"op": "stop"})["outcome"], "unknown")


if __name__ == "__main__":
    unittest.main()
