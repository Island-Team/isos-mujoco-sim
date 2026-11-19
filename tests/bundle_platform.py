#!/usr/bin/env python3
"""Check ELF compatibility admission without requiring a newer build host."""

from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bundle import inspect_glibc_symbols


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


if __name__ == "__main__":
    unittest.main()
