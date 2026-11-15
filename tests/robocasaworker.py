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
from robocasa_worker import Service, camera_dimension, camera_sizes_from_environment, create_hardware, response, serve  # noqa: E402


class FakeHardware:
    def __init__(self):
        self.steps = 0
        self.fail = False
        self.closed = False
        self.commands = []

    def observe(self):
        return {}

    def status(self, node):
        del node
        return self.observe()

    def control(self, node, payload):
        if node == "robocasa/base/mobile-base":
            self.command_base(payload["motion"])
        elif node == "robocasa/torso/torso":
            self.command_torso(payload["motion"])
        elif node == "robocasa/arm/right-arm":
            if "mode" in payload:
                self.set_control_mode(payload["mode"])
            else:
                self.command_arm(payload["position"], payload["rotation"])
        elif node == "robocasa/gripper/right-gripper":
            self.command_gripper(payload["close"])
        else:
            raise ValueError("unknown control device")

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
            camera_sizes_from_environment()
        for value in ('[]', '{"robocasa/camera/agentview-left":{"camera_width":63,"camera_height":192}}',
                      '{"robocasa/camera/agentview-left":{"camera_width":true,"camera_height":192}}',
                      '{"robocasa/camera/agentview-left":{"camera_width":256}}'):
            with self.subTest(value=value), patch.dict("os.environ", {"ISOS_ROBOCASA_CAMERA_SIZES": value}, clear=True), self.assertRaises(ValueError):
                camera_sizes_from_environment()

    def test_per_camera_handoff_and_resize(self):
        sizes = {"robocasa/camera/agentview-left": {"camera_width": 256, "camera_height": 192},
                 "robocasa/camera/agentview-right": {"camera_width": 128, "camera_height": 96},
                 "robocasa/camera/eye-in-hand": {"camera_width": 64, "camera_height": 64}}
        with patch.dict("os.environ", {"ISOS_ROBOCASA_CAMERA_SIZES": json.dumps(sizes)}, clear=True):
            selected = camera_sizes_from_environment()
        self.assertEqual(selected["robocasa/camera/agentview-right"], (128, 96))
        class Image:
            shape = (192, 256, 3)
            def tobytes(self):
                return b"\x7f" * (self.shape[0] * self.shape[1] * 3)
        cv2 = ModuleType("cv2")
        cv2.INTER_AREA = 3
        calls = []
        def resize(image, size, interpolation):
            calls.append((size, interpolation))
            output = Image()
            output.shape = (size[1], size[0], 3)
            return output
        cv2.resize = resize
        hardware = FakeHardware()
        hardware.observe = lambda: {"agentview-left": Image(), "agentview-right": Image(), "eye-in-hand": Image()}
        with patch.dict(sys.modules, {"cv2": cv2}):
            service = Service(hardware, selected)
            for device, expected in selected.items():
                result = service.dispatch({"op": "observe", "node": device})
                self.assertEqual((result["width_px"], result["height_px"], len(result["_binary"])),
                                 (*expected, expected[0] * expected[1] * 3))
        self.assertEqual(calls, [((128, 96), 3), ((64, 64), 3)])
        with self.assertRaises(ValueError):
            Service(hardware, selected).dispatch({"op": "observe", "node": "robocasa/camera/unknown"})
        with self.assertRaises(ValueError):
            Service(hardware, {}).dispatch({"op": "observe", "node": "robocasa/camera/agentview-left"})

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
        self.assertEqual(first, service.dispatch(command | {"control_mode": "unused"}))
        self.assertEqual(hardware.steps, 1)
        with self.assertRaises(ValueError):
            service.dispatch(command | {"values": [0.2, 0, 0]})
        self.assertEqual(service.dispatch({"op": "stop"})["outcome"], "stopped")
        self.assertEqual(hardware.steps, 2)
        self.assertEqual(service.dispatch({"op": "stop"})["outcome"], "stopped")
        self.assertEqual(hardware.steps, 2)
        with self.assertRaises(ValueError):
            service.dispatch(command | {"command_id": "c-2"})

    def test_extra_fields_do_not_change_command_identity(self):
        hardware = FakeHardware()
        service = Service(hardware)
        command = {"op": "command", "node": "robocasa/arm/right-arm",
                   "command_id": "arm-1", "values": {"position": [0, 0, 0],
                                                      "rotation": [0, 0, 0], "unused": 5}}
        first = service.dispatch(command)
        self.assertEqual(first, service.dispatch(command | {
            "values": {"position": [0, 0, 0], "rotation": [0, 0, 0], "other": True}}))
        self.assertEqual(hardware.steps, 1)
        with self.assertRaises(ValueError):
            service.dispatch(command | {"control_mode": "mode", "values": 0})
        self.assertEqual(hardware.steps, 1)

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
