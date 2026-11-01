#!/usr/bin/env python3
"""A positive stop waits for old JPEG cancellation; long publication is unknown."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
import time

from strict_stop import call, code


def scenario(binary, scene, preload, delay_ms):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "managed.sock"
        companion = Path(str(path) + ".stop")
        marker = Path(directory) / "jpeg-send-blocked"
        env = dict(os.environ, LD_PRELOAD=preload, R06_SEND_BLOCK_MARKER=str(marker),
                   R06_SEND_BLOCK_MS=str(delay_ms))
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
            generation = call(companion, "health")["generation_id"]
            with ThreadPoolExecutor(max_workers=1) as pool:
                capture = pool.submit(call, path, "camera_capture", "cam-0")
                for _ in range(200):
                    if marker.exists():
                        break
                    time.sleep(0.01)
                assert marker.exists(), "JPEG publication did not reach deterministic barrier"
                start = time.monotonic()
                stopped = call(companion, "stop", command_id="publication-stop",
                               generation_id=generation)
                elapsed = time.monotonic() - start
                if delay_ms < 1000:
                    assert stopped["accepted"] and stopped["base_stop"] == "stopped"
                    assert stopped["arm_stop"] == "stopped", stopped
                    assert elapsed >= delay_ms / 1000 - 0.04, elapsed
                else:
                    code(stopped, "stop_outcome_unknown")
                    assert stopped["base_stop"] == "unknown"
                    assert stopped["arm_stop"] == "unknown"
                    assert elapsed < 1.4, elapsed
                try:
                    capture.result(timeout=5)
                except (AssertionError, OSError):
                    pass  # The old JPEG stream was explicitly cancelled.
                else:
                    raise AssertionError("pre-stop JPEG completed after the stop fence")
        finally:
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=12)
            assert process.returncode == 0, stderr.decode()
            assert not path.exists() and not companion.exists()


def main():
    binary, scene, preload = sys.argv[1:4]
    scenario(binary, scene, preload, 250)
    scenario(binary, scene, preload, 2400)
    print("positive stop waited for JPEG cancellation; long send remained unknown")


if __name__ == "__main__":
    main()
