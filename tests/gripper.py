#!/usr/bin/env python3
"""Native strict-socket gripper observation, command dedup, and Stop proof."""

from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from strictsocket import exchange


def call(path, op, command_id=None, **fields):
    request = {"version": "2.0.0", "id": op, "node": "gripper-0", "op": op, **fields}
    if command_id:
        request["command_id"] = command_id
    return exchange(path, request)[0]


def main():
    binary, scene = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "gripper.sock"
        process = subprocess.Popen([binary, "--managed-strict-socket", "--v2-socket",
                                    str(path), "--scene", scene], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE)
        try:
            for _ in range(200):
                if path.is_socket() and Path(str(path) + ".stop").is_socket():
                    break
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read().decode())
                time.sleep(0.025)
            health = call(path, "health")
            assert health["ok"] and "strict-stop-v1" in health["features"]
            generation = health["generation_id"]
            observed = call(path, "gripper_observe")
            assert observed["ok"] and 0 <= observed["opening_percent"] <= 100
            command = {"generation_id": generation, "stop_epoch": "0", "close": True}
            first = call(path, "gripper_move", "grip-1", **command)
            second = call(path, "gripper_move", "grip-1", **command)
            assert first["ok"] and first["accepted"] and second["accepted"]
            assert first["sequence"] == second["sequence"]
            mismatch = call(path, "gripper_move", "grip-1", **(command | {"close": False}))
            assert mismatch["error"]["code"] == "command_id_conflict"
            stopped = call(Path(str(path) + ".stop"), "stop", "grip-stop",
                           generation_id=generation)
            assert stopped["ok"] and stopped["accepted"]
            assert all(stopped[key] == "stopped" for key in
                       ("base_stop", "arm_stop", "gripper_stop"))
            late = call(path, "gripper_move", "grip-2", **command)
            assert late["error"]["code"] == "stop_fenced"
        finally:
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=15)
            assert process.returncode == 0, stderr.decode()


if __name__ == "__main__":
    main()
