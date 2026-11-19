#!/usr/bin/env python3
"""Check ELF compatibility admission without requiring a newer build host."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bundle import inspect_glibc_symbols, ubuntu22_profile


class GlibcSymbolsTest(unittest.TestCase):
    def inspect(self, symbols: str, baseline: str = "2.35") -> None:
        result = subprocess.CompletedProcess([], 0, stdout=symbols, stderr="")
        with patch("bundle.subprocess.run", return_value=result):
            inspect_glibc_symbols(Path("adapter.so"), baseline)

    def test_ubuntu22_symbols_are_accepted(self):
        self.inspect("GLIBC_2.2.5 GLIBC_2.9 GLIBC_2.35")

    def test_newer_symbols_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires glibc 2.39"):
            self.inspect("GLIBC_2.35 GLIBC_2.39")

    def test_patch_version_above_baseline_is_rejected(self):
        with self.assertRaises(ValueError):
            self.inspect("GLIBC_2.35.1")

    def test_missing_symbol_versions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot determine"):
            self.inspect("GLIBCXX_3.4.30")


class BuildProfileTest(unittest.TestCase):
    def test_default_and_native_builds_do_not_enable_target_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertFalse(ubuntu22_profile(root))
            (root / "CMakeCache.txt").write_text("MUJOCO_BUILD_PROFILE:STRING=native\n")
            self.assertFalse(ubuntu22_profile(root))

    def test_explicit_ubuntu22_build_enables_target_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "CMakeCache.txt").write_text("MUJOCO_BUILD_PROFILE:STRING=ubuntu22\n")
            self.assertTrue(ubuntu22_profile(root))


class Ubuntu22AdmissionTest(unittest.TestCase):
    def test_cross_compilation_is_rejected_before_host_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "cross.cmake"
            module = Path(__file__).resolve().parents[1] / "cmake/Ubuntu22.cmake"
            script.write_text(f'set(CMAKE_CROSSCOMPILING TRUE)\ninclude("{module}")\n')
            result = subprocess.run(["cmake", "-P", str(script)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not support cross-compilation", result.stderr)


if __name__ == "__main__":
    unittest.main()
