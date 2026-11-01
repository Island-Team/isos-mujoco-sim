#!/usr/bin/env python3
"""Two live clients sharing one command ID do not extend a base lease."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

from strict_socket import request


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
            before, _ = request(path, "base_observe", "base-0")
            start = threading.Barrier(3)
            command = {"linear_x_m_s": 0.4, "linear_y_m_s": 0,
                       "angular_z_rad_s": 0, "valid_for_ms": 200}

            def send(correlation):
                start.wait(timeout=5)
                return request(path, "base_move", "base-0", "concurrent-1",
                               correlation, **command)[0]

            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(send, "first-connection")
                second = pool.submit(send, "second-connection")
                start.wait(timeout=5)
                started = time.monotonic()
                responses = [first.result(timeout=5), second.result(timeout=5)]
            assert time.monotonic() - started < 5
            assert {reply["id"] for reply in responses} == {
                "first-connection", "second-connection"}
            assert all(reply["ok"] and reply["accepted"] for reply in responses)
            assert responses[0]["timestamp_ns"] == responses[1]["timestamp_ns"]
            assert responses[0]["sequence"] == responses[1]["sequence"]

            # The first release moves the base. Once its lease expires, a
            # retransmission cannot restart it, even with a new request ID.
            time.sleep(0.34)
            settled, _ = request(path, "base_observe", "base-0")
            assert settled["position_m"][0] > before["position_m"][0] + 0.025
            replay, _ = request(path, "base_move", "base-0", "concurrent-1",
                                "late-replay", **command)
            assert replay["accepted"]
            assert replay["timestamp_ns"] == responses[0]["timestamp_ns"]
            assert replay["sequence"] == responses[0]["sequence"]
            time.sleep(0.14)
            after, _ = request(path, "base_observe", "base-0")
            assert abs(after["position_m"][0] - settled["position_m"][0]) < 0.02, (
                settled, after)
            print("two live duplicate clients returned one result; lease did not restart")
        finally:
            assert process.poll() is None, process.returncode
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=12)
            assert process.returncode == 0, stderr.decode()
            assert not path.exists()


if __name__ == "__main__":
    main()
