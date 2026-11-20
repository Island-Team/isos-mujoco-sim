#!/usr/bin/env python3
"""Check that development and package entry points read separate configuration."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "launch.sh",
    "build.sh",
    "tools/launcher.sh",
    "tools/config.py",
    "tools/nodes.py",
    "config/dev.toml",
    "config/package.toml",
    "config/benchmarks/robocasa.toml",
)


class ConfigModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "--quiet", str(self.root)], check=True)
        for name in FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)

    def test_package_config_change_does_not_change_development_selection(self) -> None:
        before = subprocess.run(
            [str(self.root / "launch.sh"), "--show-config"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        package = self.root / "config/package.toml"
        package.write_text(package.read_text().replace('scene = "pick-place"', 'scene = "navigation"'))
        after = subprocess.run(
            [str(self.root / "launch.sh"), "--show-config"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertEqual(after, before)

    def test_development_config_and_env_do_not_change_package_build_input(self) -> None:
        package_root = self.root / "package-mujoco"
        package_root.mkdir()
        package = self.root / "config/package.toml"
        package.write_text(package.read_text().replace('mujoco_root = ""', f'mujoco_root = "{package_root}"'))
        dev = self.root / "config/dev.toml"
        dev.write_text(dev.read_text().replace('MUJOCO_ROOT = ""', 'MUJOCO_ROOT = "/dev-only"'))
        (self.root / ".env").write_text('export MUJOCO_ROOT=/env-only\n')
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        fake_cmake = fake_bin / "cmake"
        fake_cmake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CAPTURE"\nexit 9\n')
        fake_cmake.chmod(0o700)
        capture = self.root / "cmake-args"
        environment = os.environ.copy()
        environment.pop("MUJOCO_ROOT", None)
        environment.update(PATH=f"{fake_bin}{os.pathsep}{environment['PATH']}", CAPTURE=str(capture))
        result = subprocess.run(
            [str(self.root / "build.sh"), "--output", str(self.root / "bundle"), "--version", "0.2.8"],
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertIn(f"-DMUJOCO_ROOT={package_root}", capture.read_text().splitlines())


if __name__ == "__main__":
    unittest.main()
