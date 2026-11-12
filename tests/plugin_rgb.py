#!/usr/bin/env python3
"""Exercise RoboCasa RGB8 socket payload admission through the native plugin."""

import base64
import ctypes
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading

from plugin import Api, Host, EMIT, LOG, buffer, read_exact


def run_case(api, host, emitted, width, height, binary, expected, announced_size=None):
    device = "robocasa/camera/agentview-right"
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / "worker.sock")
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(path)
            listener.listen(2)
            def serve():
                for operation in ("health", "observe"):
                    connection, _ = listener.accept()
                    with connection:
                        size, payload_size = struct.unpack("<II", read_exact(connection, 8))
                        assert payload_size == 0
                        request = json.loads(read_exact(connection, size))
                        assert request["op"] == operation
                        reply = {"version": "2.0.0", "id": request["id"], "ok": True,
                                 "sequence": 1, "timestamp_ns": 1}
                        if operation == "health":
                            reply.update(accepted=True, features=["strict-socket-v1"])
                            payload = b""
                        else:
                            reply.update(width_px=width, height_px=height)
                            payload = binary
                        metadata = json.dumps(reply).encode()
                        wire_size = announced_size if operation == "observe" and announced_size is not None else len(payload)
                        connection.sendall(struct.pack("<II", len(metadata), wire_size) + metadata)
                        if payload and announced_size is None:
                            try:
                                connection.sendall(payload)
                            except BrokenPipeError:
                                pass
            worker = threading.Thread(target=serve, daemon=True)
            worker.start()
            config, size = buffer({"instance": {"node": {
                "node_type": "eos.hardware.camera.device@v0.2",
                "adapter": {"settings": {"socket_path": path, "device_id": device,
                                          "service_instance": "robocasa"}}}}})
            handle = ctypes.c_void_p()
            assert api.create(config, size, ctypes.byref(host), ctypes.byref(handle)) == 0
            assert api.start(handle) == 0
            request, size = buffer({"op": "observe"})
            result = api.input(handle, request, size)
            assert (result == 0) == expected
            if expected:
                assert emitted[-1]["payload"]["width_px"] == width
                assert emitted[-1]["payload"]["height_px"] == height
                assert base64.b64decode(emitted[-1]["payload"]["data"]) == binary
            assert api.stop(handle) == 0
            api.destroy(handle)
            worker.join(3)
            assert not worker.is_alive()


def main():
    library = ctypes.CDLL(str(Path(sys.argv[1]).resolve()))
    library.isos_node_v1.restype = ctypes.POINTER(Api)
    api = library.isos_node_v1().contents
    emitted = []
    @EMIT
    def emit(_, data, length):
        emitted.append(json.loads(ctypes.string_at(data, length)))
        return 0
    @LOG
    def log(_, level, data, length):
        del level, data, length
    host = Host(1, ctypes.sizeof(Host), None, emit, log)
    frame = b"\x7f" * (256 * 192 * 3)
    run_case(api, host, emitted, 256, 192, frame, True)
    run_case(api, host, emitted, 256, 192, frame[:-1], False)
    run_case(api, host, emitted, 255, 192, frame, False)
    run_case(api, host, emitted, 513, 192, frame, False)
    run_case(api, host, emitted, 256, 192, b"", False, 8 * 1024 * 1024 + 1)
    print("RoboCasa RGB8 exact, truncated, mismatched, out-of-bounds and oversized payload: PASS")


if __name__ == "__main__":
    main()
