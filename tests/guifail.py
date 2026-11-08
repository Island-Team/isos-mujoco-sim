#!/usr/bin/env python3
"""Requested GUI fails cleanly when X11 is unavailable."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    binary, scene = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        sockets = [root / "legacy.sock", root / "bench.sock", root / "v2.sock"]
        result = subprocess.run(
            [binary, "--socket", str(sockets[0]),
             "--benchmark-socket", str(sockets[1]), "--v2-socket", str(sockets[2]),
             "--scene", scene],
            env={**os.environ, "DISPLAY": ":99999", "MUJOCO_GUI": "1"},
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "requires an available X11 display" in result.stderr
        assert all(not socket.exists() for socket in sockets)


if __name__ == "__main__":
    main()
