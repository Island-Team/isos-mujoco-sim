#!/usr/bin/env python3
"""Exercise the package C ABI against an owner-only strict socket stub."""

import ctypes
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading


EMIT = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t)
LOG = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t)
CREATE = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
                         ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
START = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
INPUT = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t)
HEALTH = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
STOP = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
DESTROY = ctypes.CFUNCTYPE(None, ctypes.c_void_p)


class Host(ctypes.Structure):
    _fields_ = [("abi_version", ctypes.c_uint32), ("struct_size", ctypes.c_uint32),
                ("context", ctypes.c_void_p), ("emit", EMIT), ("log", LOG)]


class Api(ctypes.Structure):
    _fields_ = [("abi_version", ctypes.c_uint32), ("struct_size", ctypes.c_uint32),
                ("create", CREATE), ("start", START), ("input", INPUT),
                ("health", HEALTH), ("stop", STOP), ("destroy", DESTROY)]


def buffer(data):
    payload = json.dumps(data).encode()
    return (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload), len(payload)


def read_exact(connection, size):
    result = b""
    while len(result) < size:
        chunk = connection.recv(size - len(result))
        if not chunk:
            raise AssertionError("short request")
        result += chunk
    return result


def serve(listener, operations):
    for expected in operations:
        connection, _ = listener.accept()
        with connection:
            metadata_size, binary_size = struct.unpack("<II", read_exact(connection, 8))
            assert binary_size == 0
            request = json.loads(read_exact(connection, metadata_size))
            assert request["op"] == expected
            assert request["node"] == "base-0"
            reply = {"version": "2.0.0", "id": request["id"], "ok": True,
                     "accepted": True, "timestamp_ns": 123, "sequence": 4}
            if expected == "health":
                reply["features"] = ["strict-socket-v1"]
            else:
                reply.update(position_m=[1.0, 2.0], linear_velocity_m_s=[0.1, 0.2],
                             yaw_rad=0.5, angular_velocity_rad_s=0.3)
            encoded = json.dumps(reply).encode()
            connection.sendall(struct.pack("<II", len(encoded), 0) + encoded)


def main():
    library = ctypes.CDLL(str(Path(sys.argv[1]).resolve()))
    library.isos_node_v1.restype = ctypes.POINTER(Api)
    api = library.isos_node_v1().contents
    assert api.abi_version == 1 and api.struct_size == ctypes.sizeof(Api)
    emitted = []

    @EMIT
    def emit(_, data, length):
        emitted.append(json.loads(ctypes.string_at(data, length)))
        return 0

    @LOG
    def log(_, level, data, length):
        del level, data, length

    host = Host(1, ctypes.sizeof(Host), None, emit, log)
    with tempfile.TemporaryDirectory() as temporary:
        path = str(Path(temporary) / "sim.sock")
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(path)
        listener.listen(4)
        worker = threading.Thread(target=serve,
                                  args=(listener, ["health", "health", "base_observe"]),
                                  daemon=True)
        worker.start()
        config, length = buffer({"run_id": "test", "revision": "a" * 64,
                                 "instance": {"node": {
                                     "node_type": "eos.hardware.base.device@v0.2",
                                     "adapter": {"settings": {"socket_path": path,
                                                               "simulator_node": "base-0"}}}}})
        handle = ctypes.c_void_p()
        assert api.create(config, length, ctypes.byref(host), ctypes.byref(handle)) == 0
        assert api.start(handle) == 0
        assert api.health(handle) == 1
        command, size = buffer({"op": "base_move", "vx_m_s": 1})
        assert api.input(handle, command, size) != 0
        request, size = buffer({"op": "observe"})
        assert api.input(handle, request, size) == 0
        assert emitted == [{"port": "state", "payload": {
            "sample": {"source_time_ns": 123, "sequence": 4,
                       "clock": "simulation", "frame_id": "base-0"},
            "x_m": 1, "y_m": 2, "yaw_rad": 0.5,
            "vx_m_s": 0.1, "vy_m_s": 0.2, "yaw_rate_rad_s": 0.3}}]
        assert api.stop(handle) == 0
        assert api.health(handle) < 0
        api.destroy(handle)
        worker.join(timeout=2)
        assert not worker.is_alive()
        listener.close()
    print("MuJoCo C ABI strict health, observation, movement rejection and Stop: PASS")


if __name__ == "__main__":
    main()
