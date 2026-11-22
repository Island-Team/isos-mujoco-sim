#!/usr/bin/env python3
"""Qualify real native plugin manifest fencing and measured joint channels."""
import ctypes
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading

from plugin import Api, Host, EMIT, LOG, buffer, read_exact


def run_case(api, host, emitted, channels, *, match=True, valid=True, clock=None):
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / "worker.sock")
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(path)
            listener.listen(2)
            def serve():
                for operation in (["health", "observe"] if match else ["health"]):
                    connection, _ = listener.accept()
                    with connection:
                        size, binary = struct.unpack("<II", read_exact(connection, 8))
                        assert binary == 0
                        request = json.loads(read_exact(connection, size))
                        assert request["op"] == operation
                        reply = {"ok": True, "id": request["id"], "version": "2.0.0",
                                 "accepted": True, "features": ["strict-socket-v1"],
                                 "manifest_digest": "expected" if match else "changed"}
                        if operation == "observe":
                            reply.update(sequence=2, timestamp_ns=123,
                                         values={"joint_positions": [.4]}, channels=channels)
                        if operation == "observe" and clock is not None:
                            reply["clock"] = clock
                        data = json.dumps(reply).encode()
                        connection.sendall(struct.pack("<II", len(data), 0) + data)
            worker = threading.Thread(target=serve, daemon=True)
            worker.start()
            data, size = buffer({"instance": {"node": {
                "node_type": "eos.hardware.torso.normalized_axes@v0.2",
                "package": {"version": "0.2.8"}, "frame_id": "joint_local",
                "adapter": {"settings": {"socket_path": path, "device_id": "robocasa/torso/torso",
                    "service_instance": "robocasa", "robot_manifest_digest": "expected"}}}}})
            handle = ctypes.c_void_p()
            assert api.create(data, size, ctypes.byref(host), ctypes.byref(handle)) == 0
            assert (api.start(handle) == 0) == match
            if match:
                request, size = buffer({"op": "observe"})
                assert (api.input(handle, request, size) == 0) == valid
                if valid:
                    assert emitted[-1] == {"port": "observation", "payload": {
                        "sample": {"source_time_ns": 123, "sequence": 2,
                                   "clock": clock or "monotonic", "frame_id": "joint_local"},
                        "channels": channels}}
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
        pass
    host = Host(1, ctypes.sizeof(Host), None, emit, log)
    channels = [{"name": "lift", "value": .4, "unit": "m"},
                {"name": "rotation", "value": .1, "unit": "rad"}]
    run_case(api, host, emitted, channels)
    run_case(api, host, emitted, channels, clock="simulation")
    run_case(api, host, emitted, channels, clock="invalid", valid=False)
    run_case(api, host, emitted, channels, match=False)
    run_case(api, host, emitted, channels * 2, valid=False)
    run_case(api, host, emitted, [{"name": "lift", "value": .4, "unit": "guess"}], valid=False)
    print("Native body adapter measured units, duplicate rejection, manifest fence: PASS")


if __name__ == "__main__":
    main()
