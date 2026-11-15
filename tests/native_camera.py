#!/usr/bin/env python3
"""Selected native camera dimensions reach the strict service's emitted JPEG."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from v2 import request


def main() -> None:
    binary, scene = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "strict.sock"
        env = {**os.environ, "ISOS_NATIVE_CAMERA_SIZES": json.dumps({
            "cam-0": {"camera_width": 1280, "camera_height": 720},
            "base-0": {},
        })}
        process = subprocess.Popen(
            [binary, "--managed-strict-socket", "--v2-socket", str(path), "--scene", scene],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            for _ in range(200):
                if path.is_socket():
                    break
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read().decode())
                time.sleep(0.025)
            assert path.is_socket(), "native service failed to start"
            frame, jpeg = request(path, "camera_capture", node="cam-0")
            assert (frame["width_px"], frame["height_px"]) == (1280, 720), frame
            assert jpeg[:2] == b"\xff\xd8" and jpeg[-2:] == b"\xff\xd9"
        finally:
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=15)
            assert process.returncode == 0, stderr.decode()

        for invalid in ({"camera_width": 1280},
                        {"camera_width": 1280.5, "camera_height": 720},
                        {"camera_width": 0, "camera_height": 720}):
            env["ISOS_NATIVE_CAMERA_SIZES"] = json.dumps({"cam-0": invalid})
            failed = subprocess.run(
                [binary, "--managed-strict-socket", "--v2-socket", str(path), "--scene", scene],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=10,
                check=False,
            )
            assert failed.returncode == 1, failed.stderr.decode()
            assert not path.exists(), "rejected service left a socket"


if __name__ == "__main__":
    main()
