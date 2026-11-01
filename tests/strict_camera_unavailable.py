#!/usr/bin/env python3
"""Strict camera health cannot claim readiness when EGL is unavailable."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile


def main():
    binary, scene, preload = sys.argv[1:4]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "strict.sock"
        env = dict(os.environ, LD_PRELOAD=preload)
        result = subprocess.run([binary, "--managed-strict-socket", "--v2-socket",
                                 str(path), "--scene", scene], env=env,
                                capture_output=True, text=True, timeout=10)
        assert result.returncode != 0 and "managed_camera_unavailable" in result.stderr
        assert not path.exists() and not Path(str(path) + ".stop").exists()
        print("unavailable camera fails managed startup before feature advertisement")


if __name__ == "__main__":
    main()
