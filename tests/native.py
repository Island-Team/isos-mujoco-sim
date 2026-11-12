#!/usr/bin/env python3
"""Check installed ELF release requirements and fail-closed native diagnostics."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("native_bundle", ROOT / "tools/bundle.py")
assert SPEC and SPEC.loader
sys.path.insert(0, str(ROOT / "tools"))
BUNDLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUNDLE)


class NativeReleaseTests(unittest.TestCase):
    def test_installed_binary_has_measured_soname_closure(self):
        binary = Path(sys.argv[1]).resolve()
        mujoco_root = Path(sys.argv[2]).resolve()
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run(["cmake", "--install", str(binary.parent), "--prefix", temporary],
                           check=True, capture_output=True, text=True)
            installed = Path(temporary) / "bin/eos-mujoco-sim"
            names = BUNDLE.inspect_installed_binary(installed, mujoco_root)
            self.assertIn("libmujoco.so.3.3.1", names)
            self.assertIn("libc.so.6", names)

    def test_plugin_has_independent_dependency_closure(self):
        plugin = Path(sys.argv[1]).resolve().parent / "libmujoco-eos-node.so"
        names = BUNDLE.inspect_installed_plugin(plugin)
        self.assertTrue(any(name.startswith("libprotobuf.so.") for name in names))
        self.assertNotIn("libmujoco.so.3.3.1", names)

    def test_rejects_plugin_absolute_runpath(self):
        with mock.patch.object(BUNDLE.subprocess, "run", return_value=mock.Mock(
                stdout="(RUNPATH) Library runpath: [/home/build/lib]\n")):
            with self.assertRaisesRegex(ValueError, "absolute RUNPATH"):
                BUNDLE.inspect_installed_plugin(Path("/not-used"))

    def test_rejects_absolute_runpath(self):
        actual = subprocess.run

        def fake(command, **kwargs):
            if command[0] == "readelf":
                return mock.Mock(stdout="(RUNPATH) Library runpath: [/home/build/lib]\n")
            return actual(command, **kwargs)

        with mock.patch.object(BUNDLE.subprocess, "run", side_effect=fake):
            with self.assertRaisesRegex(ValueError, "absolute RUNPATH"):
                BUNDLE.inspect_installed_binary(Path("/not-used"), Path("/not-used"))

    def test_rejects_wrong_mujoco_soname(self):
        with mock.patch.object(BUNDLE.subprocess, "run", return_value=mock.Mock(
                stdout="(NEEDED) Shared library: [libmujoco.so.3.15.0]\n")):
            with self.assertRaisesRegex(ValueError, "exactly libmujoco.so.3.3.1"):
                BUNDLE.inspect_installed_binary(Path("/not-used"), Path("/not-used"))

    def test_rejects_unresolved_library(self):
        mujoco_root = Path(sys.argv[2]).resolve()
        def fake(command, **kwargs):
            if command[0] == "readelf":
                return mock.Mock(stdout="(NEEDED) Shared library: [libmujoco.so.3.3.1]\n")
            if command[0] == "ldd":
                return mock.Mock(stdout="libmujoco.so.3.3.1 => not found\n", stderr="")
            raise AssertionError(command)

        with mock.patch.object(BUNDLE.subprocess, "run", side_effect=fake):
            with self.assertRaisesRegex(ValueError, "unresolved libraries"):
                BUNDLE.inspect_installed_binary(Path(sys.argv[1]).resolve(), mujoco_root)

    def test_rejects_mujoco_resolved_outside_selected_root(self):
        mujoco_root = Path(sys.argv[2]).resolve()

        def fake(command, **kwargs):
            if command[0] == "readelf":
                return mock.Mock(stdout="(NEEDED) Shared library: [libmujoco.so.3.3.1]\n")
            if command[0] == "ldd":
                return mock.Mock(stdout="libmujoco.so.3.3.1 => /other/libmujoco.so.3.3.1\n",
                                 stderr="")
            raise AssertionError(command)

        with mock.patch.object(BUNDLE.subprocess, "run", side_effect=fake):
            with self.assertRaisesRegex(ValueError, "outside MUJOCO_ROOT"):
                BUNDLE.inspect_installed_binary(Path(sys.argv[1]).resolve(), mujoco_root)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
