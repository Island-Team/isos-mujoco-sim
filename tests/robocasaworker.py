#!/usr/bin/env python3
"""Exercise isolated worker admission, deduplication, failure, and Stop."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from robocasa_worker import Service, camera_dimension  # noqa: E402


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
        self.assertEqual(camera_dimension("512"), 512)
        for value in ("0", "63", "513", "1.5", "abc"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                camera_dimension(value)

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
