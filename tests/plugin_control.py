#!/usr/bin/env python3
"""Exercise device-scoped RoboCasa command extraction through the v2 plugin."""

import ctypes
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading

from plugin_v2 import Api, Host, EMIT, LOG, argument
from plugin import read_exact


CASES = (
    ("eos.hardware.base.normalized_axes@v0.2", "robocasa/base/mobile-base", "command",
     {"axes": {"x": 0.1, "y": 0, "yaw": 0}, "lease_ms": 100}, [0.1, 0, 0]),
    ("eos.hardware.manipulator.normalized_cartesian@v0.2", "robocasa/arm/right-arm", "command",
     {"axes": {"dx": 0.1, "dy": 0, "dz": 0, "droll": 0, "dpitch": 0, "dyaw": 0}, "lease_ms": 100}, {"position": [0.1, 0, 0], "rotation": [0, 0, 0]}),
    ("eos.hardware.manipulator.normalized_cartesian@v0.2", "robocasa/arm/right-arm", "mode",
     {"mode": "1"}, 1),
    ("eos.hardware.gripper.binary@v0.2", "robocasa/gripper/right-gripper", "command",
     {"action": "close"}, True),
    ("eos.hardware.torso.normalized_axes@v0.2", "robocasa/torso/torso", "command",
     {"axes": {"lift": 0.2}, "lease_ms": 100}, [0.2]),
)


def main() -> None:
    library = ctypes.CDLL(str(Path(sys.argv[1]).resolve()))
    library.isos_node_v2.restype = ctypes.POINTER(Api)
    api = library.isos_node_v2().contents
    emitted = []

    @EMIT
    def emit(_, data, length):
        emitted.append(json.loads(ctypes.string_at(data, length)))
        return 0

    @LOG
    def log(_, level, data, length):
        del level, data, length

    host = Host(2, ctypes.sizeof(Host), None, emit, log, emit)
    native_cases = (
        ("eos.hardware.base.device@v0.2", "base-0", "command",
         {"frame_id": "base_link", "vx_m_s": 0.1, "vy_m_s": 0,
          "yaw_rate_rad_s": 0, "lease_ms": 100}, None),
        ("eos.hardware.manipulator.device@v0.2", "arm-0", "command",
         {"joint_names": ["joint-" + str(i) for i in range(6)], "position_rad": [0] * 6}, None),
        ("eos.hardware.gripper.binary@v0.2", "gripper-0", "command",
         {"action": "open"}, None),
    )
    legacy_case = (("eos.hardware.gripper.binary@v0.2", "robocasa/gripper/right-gripper",
                    "command", {"close": True, "ignored": 7}, True),)
    for node_type, device, port, payload, expected in CASES + native_cases + legacy_case:
        legacy = "close" in payload
        native = device in ("base-0", "arm-0", "gripper-0")
        operation_name = {"base-0": "base_move", "arm-0": "manipulator_move",
                          "gripper-0": "gripper_move"}.get(device, "command")
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "service.sock")
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(path)
                listener.listen(2)
                seen = []

                def serve():
                    for operation in ("health", operation_name):
                        connection, _ = listener.accept()
                        with connection:
                            size, binary_size = struct.unpack("<II", read_exact(connection, 8))
                            assert binary_size == 0
                            request = json.loads(read_exact(connection, size))
                            assert request["op"] == operation and request["node"] == device
                            seen.append(request)
                            reply = {"version": "2.0.0", "id": request["id"], "ok": True,
                                     "accepted": True, "generation_id": "generation"}
                            if operation == "health":
                                reply["features"] = ["strict-socket-v1"]
                            body = json.dumps(reply).encode()
                            connection.sendall(struct.pack("<II", len(body), 0) + body)

                worker = threading.Thread(target=serve, daemon=True)
                worker.start()
                config, size = argument({"run_id": "run-test", "instance": {"node": {
                    "node_type": node_type, "package": {"version": "0.2.7" if legacy else "0.2.8"},
                    "frame_id": "base_link" if device == "base-0" else device,
                    "joint_names": ["joint-" + str(i) for i in range(6)],
                    "movement": {"limits": {"max_velocity_lease_ms": 1000,
                        "max_linear_m_s": 1, "max_angular_rad_s": 1.5,
                        "max_joint_position_rad": 3.14}}, "adapter": {"settings": {
                        "socket_path": path, "service_instance": "native" if native else "robocasa", "device_id": device}}}}})
                handle = ctypes.c_void_p()
                assert api.create(config, size, ctypes.byref(host), ctypes.byref(handle)) == 0
                try:
                    assert api.start(handle) == 0
                    command, size = argument({"run_id": "run-test", "command_id": "control-1",
                                              "port": port, "stop_epoch": "0", "payload": payload})
                    assert api.command(handle, command, size) == 0
                    assert emitted[-1]["port"] == "command_result"
                    if native:
                        key = {"base-0": "linear_x_m_s", "arm-0": "joint_positions_rad",
                               "gripper-0": "close"}[device]
                        assert seen[-1][key] == {"base-0": 0.1, "arm-0": [0] * 6,
                                                "gripper-0": False}[device]
                    else:
                        assert seen[-1]["values"] == expected
                    if not native and "lease_ms" in payload:
                        assert seen[-1]["lease_ms"] == payload["lease_ms"]
                    assert "extra" not in seen[-1] and "axes" not in seen[-1]
                    if port == "mode":
                        assert seen[-1]["control_mode"] == "mode"
                    invalid_payloads = [{**payload, "extra": True},
                        {key: value for key, value in payload.items() if key != next(iter(payload))}]
                    if "lease_ms" in payload:
                        invalid_payloads += [{**payload, "lease_ms": value} for value in (0, 1001, 1.5, True)]
                    if "axes" in payload:
                        invalid_payloads += [{**payload, "axes": {**payload["axes"], "unknown": 0}},
                                             {**payload, "axes": {name: 2 for name in payload["axes"]}}]
                    if device == "base-0":
                        invalid_payloads += [{**payload, "frame_id": "wrong"}, {**payload, "vx_m_s": 2}]
                    if device == "arm-0":
                        invalid_payloads += [{**payload, "joint_names": list(reversed(payload["joint_names"]))},
                                             {**payload, "position_rad": [4] * 6}]
                    if legacy:
                        invalid_payloads = [{"close": "invalid"}]
                    for bad in invalid_payloads:
                        invalid, size = argument({"run_id": "run-test", "command_id": "bad",
                                                  "stop_epoch": "0", "port": port, "payload": bad})
                        assert api.command(handle, invalid, size) == -1
                    invalid, size = argument({"run_id": "run-test", "command_id": "control-2",
                                              "stop_epoch": "0", "port": port, "payload": {"unrelated": 1}})
                    assert api.command(handle, invalid, size) == -1
                    worker.join(3)
                    assert len(seen) == 2 and not worker.is_alive()
                    listener.close()
                    failed, size = argument({"run_id": "run-test", "command_id": "failure",
                                              "stop_epoch": "0", "port": port, "payload": payload})
                    assert api.command(handle, failed, size) == -1
                finally:
                    api.destroy(handle)
                worker.join(3)
                assert not worker.is_alive()


if __name__ == "__main__":
    main()
