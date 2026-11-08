"""Check the IsOS package activation bundle without a MuJoCo installation."""

import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mujoco_release", ROOT / "tools/release.py")
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class ReleaseTests(unittest.TestCase):
    def test_stage_uses_current_eos_layout_and_versioned_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            eos = root / "eos/etc/ext/mujoco"
            eos.mkdir(parents=True)
            (eos / "eos.toml").write_text(
                '[[mode.binding]]\nbackend = "../ext/mujoco/binding.toml"\nprofile = "mujoco"\n'
            )
            (eos / "binding.toml").write_text('[profile.mujoco.robot]\nrobot_id = "mujoco-0"\n')
            binary = root / "sim"
            binary.write_text("#!/bin/sh\n")
            stage = root / "stage"
            stage.mkdir()
            with mock.patch.object(BUILDER, "ROOT", ROOT):
                BUILDER.stage_release(stage, binary, root / "eos", "1.0.1")

            module = (stage / "config/module.toml").read_text()
            self.assertIn('version = "1.0.1"', module)
            self.assertIn('{{package_file:bin/eos-mujoco-sim}}', module)
            rendered = module.replace(
                '{{package_file:bin/eos-mujoco-sim}}', '"/pkg/bin/eos-mujoco-sim"'
            ).replace(
                '{{package_file:assets/scene.xml}}', '"/pkg/assets/scene.xml"'
            ).replace(
                '{{package_file:config/binding.toml}}', '"/pkg/config/binding.toml"'
            )
            parsed = tomllib.loads(rendered)
            self.assertEqual(parsed["module"]["package"], "island/mujoco-sim")
            self.assertEqual(parsed["binding"][0]["profile"], "mujoco")
            self.assertIn('backend = {{package_file:config/binding.toml}}',
                          (stage / "config/eos.toml").read_text())


if __name__ == "__main__":
    unittest.main()
