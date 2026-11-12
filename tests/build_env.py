#!/usr/bin/env python3
"""An explicit build dependency overrides repository defaults for source checks."""

import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    fake = directory / "cmake"
    fake.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$CAPTURE\"\nexit 9\n")
    fake.chmod(0o700)
    selected = directory / "selected-mujoco"
    selected.mkdir()
    capture = directory / "args"
    environment = os.environ | {
        "PATH": str(directory) + os.pathsep + os.environ["PATH"],
        "MUJOCO_ROOT": str(selected),
        "CAPTURE": str(capture),
    }
    result = subprocess.run(
        [str(ROOT / "build.sh"), "--output", str(directory / "bundle"),
         "--version", "0.2.7"], cwd=ROOT, env=environment,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 9, result.stderr
    assert f"-DMUJOCO_ROOT={selected}" in capture.read_text().splitlines()
print("explicit MUJOCO_ROOT source build precedence: PASS")
