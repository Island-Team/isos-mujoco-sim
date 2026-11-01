#!/usr/bin/env python3
"""A blocked engine cannot turn a timed-out stop into a later safe claim."""

from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
import time

from strict_stop import call, code


def main():
    binary, scene, preload = sys.argv[1:4]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "managed.sock"
        companion = Path(str(path) + ".stop")
        marker = Path(directory) / "step-blocked"
        arm = Path(directory) / "arm-step-block"
        env = dict(os.environ, LD_PRELOAD=preload, R06_STEP_BLOCK_MARKER=str(marker),
                   R06_STEP_BLOCK_ARM_FILE=str(arm))
        process = subprocess.Popen([binary, "--managed-strict-socket", "--v2-socket",
                                    str(path), "--scene", scene], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(300):
                if companion.is_socket():
                    break
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read().decode())
                time.sleep(0.01)
            assert companion.is_socket()
            arm.touch()
            for _ in range(300):
                if marker.exists():
                    break
                time.sleep(0.01)
            assert marker.exists()
            start = time.monotonic()
            health = call(companion, "health")
            assert time.monotonic() - start < 0.25
            generation = health["generation_id"]
            start = time.monotonic()
            stopped = call(companion, "stop", command_id="blocked-stop",
                           generation_id=generation)
            elapsed = time.monotonic() - start
            assert 0.8 <= elapsed < 1.4, (elapsed, stopped)
            code(stopped, "stop_outcome_unknown")
            assert stopped["accepted"] is False
            assert stopped["base_stop"] == "unknown" and stopped["arm_stop"] == "unknown"
            assert stopped["stop_epoch"] == "1"
            time.sleep(1.6)  # The fixed worker has now completed its late hold.
            movement = {"linear_x_m_s": 0.2, "linear_y_m_s": 0,
                        "angular_z_rad_s": 0, "valid_for_ms": 200,
                        "generation_id": generation, "stop_epoch": "1"}
            code(call(path, "base_move", command_id="forbidden-after-unknown", **movement),
                 "stop_fenced")
            again = call(companion, "stop", command_id="second-stop",
                         generation_id=generation)
            code(again, "stop_outcome_unknown")
            code(call(path, "base_move", command_id="still-forbidden",
                      **{**movement, "stop_epoch": "2"}), "stop_fenced")
        finally:
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=12)
            assert process.returncode == 0, stderr.decode()
            assert not path.exists() and not companion.exists()
    print("health remained responsive; timed-out stop stayed unknown and inhibited")


if __name__ == "__main__":
    main()
