#!/usr/bin/env python3
"""Exercise managed socket admission against a real loaded MuJoCo scene."""

import json
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time


def exchange(path, message, *, raw=None):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(15)
        client.connect(str(path))
        body = json.dumps(message, ensure_ascii=False).encode() if raw is None else raw
        client.sendall(struct.pack("<II", len(body), 0) + body)
        header = client.recv(8)
        if not header:
            return None
        assert len(header) == 8
        length, payload_length = struct.unpack("<II", header)
        assert 0 < length <= 65536 and payload_length <= 8 * 1024 * 1024
        def read(count):
            data = bytearray()
            while len(data) < count:
                chunk = client.recv(count - len(data))
                assert chunk
                data.extend(chunk)
            return data
        reply = json.loads(read(length))
        payload = read(payload_length)
        return reply, payload


def request(path, op, node, command_id=None, correlation=None, **fields):
    body = {"version": "2.0.0", "id": correlation or op, "node": node, "op": op,
            **fields}
    if command_id is not None:
        body["command_id"] = command_id
    result = exchange(path, body)
    assert result is not None
    reply, payload = result
    assert reply["version"] == "2.0.0" and reply["id"] == body["id"]
    if not reply["ok"]:
        assert "code" in reply["error"] and "message" in reply["error"]
        assert not payload
    return reply, payload


def error(path, code, op, node, command_id=None, **fields):
    reply, _ = request(path, op, node, command_id, **fields)
    assert reply["ok"] is False and reply["error"]["code"] == code, reply


def launch_error(binary, scene, args, expected):
    result = subprocess.run([binary, *args, "--scene", scene], capture_output=True,
                            text=True, timeout=8)
    assert result.returncode != 0 and expected in result.stderr, result


def main():
    binary, scene = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / "strict.sock"
        launch_error(binary, scene, ["--managed-strict-socket"],
                     "strict_v2_socket_required")
        launch_error(binary, scene, ["--managed-strict-socket", "--v2-socket",
                     str(path), "--socket", str(root / "legacy.sock")],
                     "strict_legacy_socket_forbidden")
        launch_error(binary, scene, ["--managed-strict-socket", "--v2-socket",
                     str(path), "--benchmark-socket", str(root / "bench.sock")],
                     "strict_benchmark_socket_forbidden")
        process = subprocess.Popen([binary, "--managed-strict-socket",
                                    "--v2-socket", str(path), "--scene", scene],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE)
        try:
            for _ in range(200):
                if path.is_socket():
                    break
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read().decode())
                time.sleep(0.025)
            assert path.is_socket() and path.stat().st_mode & 0o777 == 0o600
            assert not (root / "legacy.sock").exists()
            assert not (root / "bench.sock").exists()
            for node in ("cam-0", "base-0", "arm-0"):
                health, _ = request(path, "health", node)
                assert health["ok"] and health["accepted"]
                assert "strict-socket-v1" in health["features"]
            error(path, "node_mismatch", "health", "unknown")
            error(path, "node_mismatch", "camera_capture", "base-0")
            error(path, "node_mismatch", "manipulator_observe", "cam-0")
            error(path, "node_mismatch", "stop", "cam-0", "stop-camera")
            error(path, "invalid_request", "health", "base-0", "unexpected")
            error(path, "unsupported_operation", "teleport", "base-0")
            bad_version = {"version": "2.1.0", "id": "version-1", "node": "base-0",
                           "op": "health"}
            assert exchange(path, bad_version)[0]["error"]["code"] == "unsupported_version"
            error(path, "invalid_command_id", "base_move", "base-0",
                  linear_x_m_s=0, linear_y_m_s=0, angular_z_rad_s=0,
                  valid_for_ms=200)
            error(path, "invalid_movement", "base_move", "base-0", "bad-type",
                  linear_x_m_s="NaN", linear_y_m_s=0, angular_z_rad_s=0,
                  valid_for_ms=200)
            error(path, "out_of_range", "base_move", "base-0", "bad-speed",
                  linear_x_m_s=1.01, linear_y_m_s=0, angular_z_rad_s=0,
                  valid_for_ms=200)
            error(path, "out_of_range", "base_move", "base-0", "bad-lease",
                  linear_x_m_s=0, linear_y_m_s=0, angular_z_rad_s=0,
                  valid_for_ms=5001)
            error(path, "invalid_movement", "manipulator_move", "arm-0", "short",
                  joint_positions_rad=[0] * 5)
            error(path, "out_of_range", "manipulator_move", "arm-0", "joint-range",
                  joint_positions_rad=[100] * 6)
            base = {"linear_x_m_s": 0.2, "linear_y_m_s": 0,
                    "angular_z_rad_s": 0, "valid_for_ms": 200}
            first, _ = request(path, "base_move", "base-0", "命令-1", "first",
                               **base)
            second, _ = request(path, "base_move", "base-0", "命令-1", "second",
                                **base)
            assert first["ok"] and first["accepted"] and second["accepted"]
            assert second["id"] == "second"
            zero, _ = request(path, "base_move", "base-0", "zero-canonical",
                              linear_x_m_s=-0.0, linear_y_m_s=0,
                              angular_z_rad_s=0, valid_for_ms=200)
            zero_again, _ = request(path, "base_move", "base-0",
                                    "zero-canonical", "zero-again",
                                    linear_x_m_s=0, linear_y_m_s=0,
                                    angular_z_rad_s=-0.0, valid_for_ms=200.0)
            assert zero["accepted"] and zero_again["accepted"]
            error(path, "command_id_conflict", "base_move", "base-0", "命令-1",
                  linear_x_m_s=0.3, linear_y_m_s=0, angular_z_rad_s=0,
                  valid_for_ms=200)
            error(path, "command_id_conflict", "stop", "base-0", "命令-1")
            exact = "x" * 128
            ok, _ = request(path, "base_move", "base-0", exact, **base)
            assert ok["ok"] and ok["accepted"]
            error(path, "invalid_command_id", "base_move", "base-0", exact + "x",
                  **base)
            invalid_id = {"version": "2.0.0", "id": "x" * 129,
                          "node": "base-0", "op": "health"}
            assert exchange(path, invalid_id)[0]["error"]["code"] == "invalid_request"
            good_id = {"version": "2.0.0", "id": "x" * 128,
                       "node": "base-0", "op": "health"}
            assert exchange(path, good_id)[0]["accepted"]
            camera, jpeg = request(path, "camera_capture", "cam-0")
            assert camera["ok"] and camera["rgb_length"] == len(jpeg)
            assert jpeg[:2] == b"\xff\xd8"
            stopped, _ = request(path, "stop", "base-0", "stop-1")
            assert stopped["ok"] and stopped["accepted"]
            duplicate, _ = request(path, "stop", "base-0", "stop-1", "stop-again")
            assert duplicate["accepted"] and duplicate["id"] == "stop-again"
            arm_stop, _ = request(path, "stop", "arm-0", "arm-stop-1")
            assert arm_stop["ok"] and arm_stop["accepted"]
            # A malformed frame has no trusted correlation ID and must not release.
            with socket.socket(socket.AF_UNIX) as client:
                client.settimeout(3)
                client.connect(str(path))
                client.sendall(struct.pack("<II", 65537, 0))
                assert client.recv(1) == b""
            assert exchange(path, {}, raw=b"{invalid") is None
            with socket.socket(socket.AF_UNIX) as client:
                client.settimeout(3)
                client.connect(str(path))
                client.sendall(b"1234")
                client.shutdown(socket.SHUT_WR)
                assert client.recv(1) == b""
            print("strict launch, health, scene identity, bounds, dedup, frame checks passed")
        finally:
            assert process.poll() is None, (process.returncode, process.stderr.read().decode())
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=12)
            assert process.returncode == 0, (process.returncode, stderr.decode())
            assert not path.exists()


if __name__ == "__main__":
    main()
