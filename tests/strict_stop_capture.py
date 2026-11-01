#!/usr/bin/env python3
"""A graphics call blocked after a snapshot cannot delay or publish past stop."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
import time

from strict_socket import exchange


def call(path, op, node, command_id=None, generation_id=None):
    body = {"version": "2.0.0", "id": op, "node": node, "op": op}
    if command_id:
        body["command_id"] = command_id
    if generation_id:
        body["generation_id"] = generation_id
    return exchange(path, body)[0]


def main():
    binary, scene, preload = sys.argv[1:4]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "managed.sock"
        companion = Path(str(path) + ".stop")
        marker = Path(directory) / "render-blocked"
        env = dict(os.environ, LD_PRELOAD=preload, R06_RENDER_BLOCK_MARKER=str(marker))
        process = subprocess.Popen([binary, "--managed-strict-socket", "--v2-socket",
                                    str(path), "--scene", scene], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(200):
                if companion.is_socket():
                    break
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read().decode())
                time.sleep(0.025)
            assert companion.is_socket()
            generation = call(companion, "health", "base-0")["generation_id"]
            with ThreadPoolExecutor(max_workers=1) as pool:
                capture = pool.submit(call, path, "camera_capture", "cam-0")
                for _ in range(200):
                    if marker.exists():
                        break
                    time.sleep(0.01)
                assert marker.exists(), "render did not reach deterministic barrier"
                start = time.monotonic()
                stopped = call(companion, "stop", "base-0", "capture-stop", generation)
                elapsed = time.monotonic() - start
                assert elapsed < 1.5, elapsed
                assert stopped["accepted"] and stopped["base_stop"] == "stopped"
                assert stopped["arm_stop"] == "stopped"
                result = capture.result(timeout=4)
                assert result["ok"] is False and result["error"]["code"] == "device_unavailable"
        finally:
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=12)
            assert process.returncode == 0, stderr.decode()
            assert not path.exists() and not companion.exists()
    print("blocked rendering did not delay stop or publish a fenced frame")


if __name__ == "__main__":
    main()
