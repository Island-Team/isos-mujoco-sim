#!/usr/bin/env python3
"""Real managed child: independent stop ingress, generation and epoch fences."""

from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time

from strict_socket import exchange


def call(path, op, node="base-0", command_id=None, **fields):
    request = {"version": "2.0.0", "id": fields.pop("request_id", op),
               "node": node, "op": op, **fields}
    if command_id is not None:
        request["command_id"] = command_id
    reply, payload = exchange(path, request)
    assert not payload or op == "camera_capture"
    return reply


def code(reply, expected):
    assert reply["ok"] is False and reply["error"]["code"] == expected, reply


def launch(binary, scene, path):
    process = subprocess.Popen([binary, "--managed-strict-socket", "--v2-socket",
                                str(path), "--scene", scene], stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
    for _ in range(200):
        if path.is_socket() and Path(str(path) + ".stop").is_socket():
            return process
        if process.poll() is not None:
            raise RuntimeError(process.stderr.read().decode())
        time.sleep(0.025)
    raise AssertionError("both managed sockets did not start")


def stop_process(process, path):
    process.send_signal(signal.SIGTERM)
    _, stderr = process.communicate(timeout=12)
    assert process.returncode == 0, stderr.decode()
    assert not path.exists() and not Path(str(path) + ".stop").exists()


def partial(path):
    client = socket.socket(socket.AF_UNIX)
    client.settimeout(2)
    client.connect(str(path))
    client.sendall(b"\x20\x00")
    return client


def main():
    binary, scene = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "managed.sock"
        companion = Path(str(path) + ".stop")
        long_path = Path(directory) / ("x" * (103 - len(directory) - 1))
        result = subprocess.run([binary, "--managed-strict-socket", "--v2-socket",
                                 str(long_path), "--scene", scene],
                                capture_output=True, text=True, timeout=8)
        assert result.returncode != 0 and "socket_path_too_long" in result.stderr
        assert not long_path.exists() and not Path(str(long_path) + ".stop").exists()
        process = launch(binary, scene, path)
        try:
            assert path.stat().st_mode & 0o777 == 0o600
            assert companion.stat().st_mode & 0o777 == 0o600
            main_health = call(path, "health")
            stop_health = call(companion, "health")
            generation = main_health["generation_id"]
            assert len(generation) == 32 and all(c in "0123456789abcdef" for c in generation)
            assert stop_health["generation_id"] == generation
            assert "strict-stop-v1" in main_health["features"]
            assert "strict-stop-v1" in stop_health["features"]
            code(call(companion, "base_move"), "unsupported_operation")
            code(call(companion, "health", "cam-0"), "node_mismatch")

            movement = {"linear_x_m_s": 0.2, "linear_y_m_s": 0,
                        "angular_z_rad_s": 0, "valid_for_ms": 200}
            code(call(path, "base_move", command_id="missing-generation",
                      stop_epoch="0", **movement), "stale_generation")
            code(call(path, "base_move", command_id="missing-epoch",
                      generation_id=generation, **movement), "stop_fenced")
            code(call(path, "base_move", command_id="bad-epoch",
                      generation_id=generation, stop_epoch="00", **movement), "stop_fenced")
            first = call(path, "base_move", command_id="first", request_id="first-transport",
                         generation_id=generation, stop_epoch="0", **movement)
            assert first["ok"] and first["accepted"], first

            blocked = [partial(path) for _ in range(8)]
            try:
                start = time.monotonic()
                stop = call(companion, "stop", command_id="first-stop",
                            generation_id=generation)
                assert time.monotonic() - start < 1.5
            finally:
                for client in blocked:
                    client.close()
            assert stop["ok"] and stop["accepted"] and stop["base_stop"] == "stopped"
            assert stop["arm_stop"] == "stopped" and stop["stop_epoch"] == "1", stop
            assert stop["generation_id"] == generation
            assert stop["sequence"] >= first["sequence"]
            duplicate = call(companion, "stop", command_id="first-stop",
                             generation_id=generation, request_id="duplicate-stop")
            assert duplicate["id"] == "duplicate-stop"
            for field in ("base_stop", "arm_stop", "stop_epoch", "timestamp_ns", "sequence"):
                assert duplicate[field] == stop[field]
            replay = call(path, "base_move", command_id="first", request_id="replay",
                          generation_id=generation, stop_epoch="0", **movement)
            assert replay["accepted"] and replay["timestamp_ns"] == first["timestamp_ns"]
            code(call(path, "base_move", command_id="first", generation_id=generation,
                      stop_epoch="1", **movement), "command_id_conflict")
            code(call(path, "base_move", command_id="late", generation_id=generation,
                      stop_epoch="0", **movement), "stop_fenced")
            current = call(path, "base_move", command_id="new", generation_id=generation,
                           stop_epoch="1", **movement)
            assert current["ok"] and current["accepted"], current
            code(call(companion, "stop", command_id="old-generation",
                      generation_id="0" * 32), "stale_generation")

            partial_stop = [partial(companion) for _ in range(2)]
            try:
                start = time.monotonic()
                second = call(companion, "stop", command_id="second-stop",
                              generation_id=generation)
                assert time.monotonic() - start < 1.5
                assert second["stop_epoch"] == "2" and second["accepted"], second
            finally:
                for client in partial_stop:
                    client.close()
        finally:
            stop_process(process, path)

        replacement = launch(binary, scene, path)
        try:
            next_generation = call(path, "health")["generation_id"]
            assert next_generation != generation
            code(call(path, "base_move", command_id="previous-child",
                      generation_id=generation, stop_epoch="0", **movement),
                 "stale_generation")
            code(call(companion, "stop", command_id="previous-stop",
                      generation_id=generation), "stale_generation")
        finally:
            stop_process(replacement, path)
    print("strict stop lane, replay fence, bounded ingress and generation restart passed")


if __name__ == "__main__":
    main()
