#!/usr/bin/env python3
"""Measure fresh native JPEG captures at an unchanged 1280x720 resolution."""

import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import tempfile
import time

from v2 import request


def main() -> None:
    binary, scene = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as directory:
        socket_path = Path(directory) / "strict.sock"
        environment = {**os.environ, "ISOS_NATIVE_CAMERA_SIZES": json.dumps({
            "cam-0": {"camera_width": 1280, "camera_height": 720},
        })}
        process = subprocess.Popen(
            [binary, "--managed-strict-socket", "--v2-socket", str(socket_path),
             "--scene", scene], env=environment, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            for _ in range(200):
                if socket_path.is_socket():
                    break
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read().decode())
                time.sleep(0.025)
            if not socket_path.is_socket():
                raise RuntimeError("native camera socket unavailable")
            times = []
            timestamps = []
            started = time.perf_counter()
            for _ in range(31):
                sample_started = time.perf_counter()
                frame, jpeg = request(socket_path, "camera_capture", node="cam-0")
                times.append((time.perf_counter() - sample_started) * 1000)
                if (frame["width_px"], frame["height_px"]) != (1280, 720):
                    raise RuntimeError("native camera changed resolution")
                if not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
                    raise RuntimeError("native camera returned invalid JPEG")
                timestamps.append(frame["timestamp_ns"])
            elapsed = time.perf_counter() - started
            if len(set(timestamps)) != len(timestamps):
                raise RuntimeError("native camera repeated a capture timestamp")
            print(json.dumps({
                "frames": len(timestamps), "elapsed_s": elapsed,
                "fresh_fps": (len(timestamps) - 1) / elapsed,
                "median_request_ms": statistics.median(times),
                "p99_request_ms": sorted(times)[-1],
                "width_px": 1280, "height_px": 720,
            }, sort_keys=True))
        finally:
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=15)
            if process.returncode != 0:
                raise RuntimeError(stderr.decode())


if __name__ == "__main__":
    main()
