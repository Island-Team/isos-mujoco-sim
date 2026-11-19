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
    for packaging in (False, True):
        # Switch back from ubuntu22 to native and then an unset profile.
        for profile in ("ubuntu22", "native", None):
            env = environment.copy()
            env.pop("MUJOCO_BUILD_PROFILE", None)
            if profile is not None:
                env["MUJOCO_BUILD_PROFILE"] = profile
            command = [str(ROOT / "build.sh")]
            if packaging:
                command += ["--output", str(directory / "bundle"), "--version", "0.2.7"]
            result = subprocess.run(command, cwd=ROOT, env=env,
                                    capture_output=True, text=True, check=False)
            assert result.returncode == 9, result.stderr
            arguments = capture.read_text().splitlines()
            assert f"-DMUJOCO_ROOT={selected}" in arguments
            expected_profile = profile or "native"
            assert f"-DMUJOCO_BUILD_PROFILE={expected_profile}" in arguments
            assert any(arg.startswith("-DPython3_EXECUTABLE=") for arg in arguments) == (profile == "ubuntu22")
            expected_build = ROOT / (
                ".local/package-build-ubuntu22" if profile == "ubuntu22" else
                ".local/package-build" if packaging else "build")
            assert arguments[arguments.index("-B") + 1] == str(expected_build)
print("MuJoCo root precedence, profile switching, and build directory isolation: PASS")
