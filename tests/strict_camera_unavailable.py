#!/usr/bin/env python3
"""Strict camera health cannot claim readiness when EGL is unavailable."""

from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
import time

from strict_socket import request


def main():
    binary, scene, preload = sys.argv[1:4]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "strict.sock"
        env = dict(os.environ, LD_PRELOAD=preload)
        process = subprocess.Popen([binary, "--managed-strict-socket",
                                    "--v2-socket", str(path), "--scene", scene],
                                   env=env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE)
        try:
            for _ in range(200):
                if path.is_socket():
                    break
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read().decode())
                time.sleep(0.025)
            assert path.is_socket()
            camera, _ = request(path, "health", "cam-0")
            assert camera["ok"] is False and camera["error"]["code"] == "device_unavailable"
            assert "strict-socket-v1" not in camera.get("features", [])
            base, _ = request(path, "health", "base-0")
            assert base["ok"] and base["accepted"]
            print("unavailable camera refuses strict health feature")
        finally:
            assert process.poll() is None, process.returncode
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=12)
            assert process.returncode == 0, stderr.decode()
            assert not path.exists()


if __name__ == "__main__":
    main()
