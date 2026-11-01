#!/usr/bin/env python3
"""Prove the full process-generation retention bounds without test-only limits."""

from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from strict_socket import request, error


def main():
    binary, scene = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "strict.sock"
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
            assert path.is_socket()
            fields = {"linear_x_m_s": 0, "linear_y_m_s": 0,
                      "angular_z_rad_s": 0, "valid_for_ms": 100}
            for index in range(65536):
                reply, _ = request(path, "base_move", "base-0", f"movement-{index}",
                                   **fields)
                assert reply["ok"] and reply["accepted"], (index, reply)
            error(path, "command_capacity", "base_move", "base-0",
                  "movement-overflow", **fields)
            first, _ = request(path, "base_move", "base-0", "movement-0", **fields)
            assert first["ok"] and first["accepted"]
            for index in range(4096):
                reply, _ = request(path, "stop", "base-0", f"stop-{index}")
                assert reply["ok"] and reply["accepted"], (index, reply)
            error(path, "command_capacity", "stop", "base-0", "stop-overflow")
            last, _ = request(path, "stop", "base-0", "stop-0")
            assert last["ok"] and last["accepted"]
            print("65,536 movement and 4,096 stop keys retained without eviction")
        finally:
            assert process.poll() is None, process.returncode
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=12)
            assert process.returncode == 0, stderr.decode()
            assert not path.exists()


if __name__ == "__main__":
    main()
