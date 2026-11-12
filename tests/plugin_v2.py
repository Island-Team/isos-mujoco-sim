#!/usr/bin/env python3
"""Exercise v2 native C ABI against the real IsOS-managed simulator socket."""

import ctypes
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


EMIT = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t)
LOG = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t)
CREATE = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
                         ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
START = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
CALL = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t)
HEALTH = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
DESTROY = ctypes.CFUNCTYPE(None, ctypes.c_void_p)


class Host(ctypes.Structure):
    _fields_ = [("abi_version", ctypes.c_uint32), ("struct_size", ctypes.c_uint32),
                ("context", ctypes.c_void_p), ("emit", EMIT), ("log", LOG),
                ("stop_proof", EMIT)]


class Api(ctypes.Structure):
    _fields_ = [("abi_version", ctypes.c_uint32), ("struct_size", ctypes.c_uint32),
                ("create", CREATE), ("start", START), ("observe", CALL),
                ("command", CALL), ("health", HEALTH), ("stop", CALL),
                ("destroy", DESTROY)]


def argument(data):
    encoded = json.dumps(data).encode()
    return (ctypes.c_uint8 * len(encoded)).from_buffer_copy(encoded), len(encoded)


def main():
    binary, plugin, scene = sys.argv[1:4]
    library = ctypes.CDLL(str(Path(plugin).resolve()))
    library.isos_node_v2.restype = ctypes.POINTER(Api)
    api = library.isos_node_v2().contents
    assert api.abi_version == 2 and api.struct_size == ctypes.sizeof(Api)
    emitted, proofs = [], []

    @EMIT
    def emit(_, data, length):
        emitted.append(json.loads(ctypes.string_at(data, length)))
        return 0

    @EMIT
    def proof(_, data, length):
        proofs.append(json.loads(ctypes.string_at(data, length)))
        return 0

    @LOG
    def log(_, level, data, length):
        del level, data, length

    host = Host(2, ctypes.sizeof(Host), None, emit, log, proof)
    with tempfile.TemporaryDirectory() as directory:
        socket_path = Path(directory) / "sim.sock"
        process = subprocess.Popen([binary, "--managed-strict-socket", "--v2-socket",
                                    str(socket_path), "--scene", scene],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        handle = ctypes.c_void_p()
        try:
            for _ in range(200):
                if socket_path.is_socket() and Path(str(socket_path) + ".stop").is_socket():
                    break
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read().decode())
                time.sleep(0.025)
            config, size = argument({"run_id": "run-test", "revision": "revision-test",
                                     "instance": {"node": {"node_type": "eos.hardware.gripper.binary@v0.2",
                                                           "adapter": {"settings": {"socket_path": str(socket_path),
                                                                                    "service_instance": "native",
                                                                                    "device_id": "gripper-0"}}}}})
            assert api.create(config, size, ctypes.byref(host), ctypes.byref(handle)) == 0
            assert api.start(handle) == 0 and api.health(handle) == 1
            observe, size = argument({"op": "observe"})
            assert api.observe(handle, observe, size) == 0
            assert emitted[-1]["port"] == "state"
            command, size = argument({"run_id": "run-test", "revision": "revision-test",
                                      "command_id": "command-1", "stop_epoch": "0",
                                      "payload": {"close": True}})
            assert api.command(handle, command, size) == 0
            assert emitted[-1]["port"] == "command_result"
            stop, size = argument({"run_id": "run-test", "revision": "revision-test",
                                   "stop_epoch": 1})
            assert api.stop(handle, stop, size) == 0
            assert proofs[-1]["outcome"] == "stopped"
            assert proofs[-1]["actuators"] == {"base": "stopped", "manipulator": "stopped",
                                                "gripper": "stopped"}
        finally:
            if handle:
                api.destroy(handle)
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=15)
            assert process.returncode == 0, stderr.decode()


if __name__ == "__main__":
    main()
