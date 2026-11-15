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
     {"axes": {"x": 0.1, "y": 0, "yaw": 0, "ignored": 7}, "extra": True}, [0.1, 0, 0]),
    ("eos.hardware.manipulator.normalized_cartesian@v0.2", "robocasa/arm/right-arm", "command",
     {"axes": {"dx": 0.1, "dy": 0, "dz": 0, "droll": 0, "dpitch": 0, "dyaw": 0,
               "ignored": 7}}, {"position": [0.1, 0, 0], "rotation": [0, 0, 0]}),
    ("eos.hardware.manipulator.normalized_cartesian@v0.2", "robocasa/arm/right-arm", "mode",
     {"mode": 1, "extra": True}, 1),
    ("eos.hardware.gripper.binary@v0.2", "robocasa/gripper/right-gripper", "command",
     {"close": True, "extra": True}, True),
    ("eos.hardware.torso.normalized_axes@v0.2", "robocasa/torso/torso", "command",
     {"axes": {"lift": 0.2, "ignored": 7}}, [0.2]),
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
    for node_type, device, port, payload, expected in CASES:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "service.sock")
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(path)
                listener.listen(2)
                seen = []

                def serve():
                    for operation in ("health", "command"):
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
                    "node_type": node_type, "adapter": {"settings": {
                        "socket_path": path, "service_instance": "robocasa", "device_id": device}}}}})
                handle = ctypes.c_void_p()
                assert api.create(config, size, ctypes.byref(host), ctypes.byref(handle)) == 0
                try:
                    assert api.start(handle) == 0
                    command, size = argument({"run_id": "run-test", "command_id": "control-1",
                                              "port": port, "payload": payload})
                    assert api.command(handle, command, size) == 0
                    assert emitted[-1]["port"] == "command_result"
                    assert seen[-1]["values"] == expected
                    assert "extra" not in seen[-1] and "axes" not in seen[-1]
                    if port == "mode":
                        assert seen[-1]["control_mode"] == "mode"
                    invalid, size = argument({"run_id": "run-test", "command_id": "control-2",
                                              "port": port, "payload": {"unrelated": 1}})
                    assert api.command(handle, invalid, size) == -1
                finally:
                    api.destroy(handle)
                worker.join(3)
                assert not worker.is_alive()


if __name__ == "__main__":
    main()
