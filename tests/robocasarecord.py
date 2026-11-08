"""Stubbed local recording and selected replay tests."""

import json
from pathlib import Path
import tempfile
import unittest

from robocasa_core import EpisodeRecorder, Hardware, HardwareError, load_record, replay_record
from robocasahardware import Environment


class RecordTests(unittest.TestCase):
  def make_writer(self):
    environment = Environment()
    writer = EpisodeRecorder(Hardware(environment), task="CloseFridge", split="target",
                             seed=42, camera_width=64, camera_height=64)
    writer.reset()
    writer.command_arm([.1, 0, 0], [0, 0, 0])
    writer.command_gripper(1)
    writer.command_base([0, .1, 0])
    writer.command_torso([.1])
    writer.set_control_mode(1)
    writer.step()
    return writer

  def test_save_load_selected_record_and_replay(self):
    with tempfile.TemporaryDirectory() as directory:
      selected = Path(directory) / "selected.json"
      writer = self.make_writer()
      writer.save(selected)
      record = load_record(selected)
      self.assertEqual(record["steps"][0]["command"]["gripper"], 1)
      environment = Environment()
      self.assertEqual(replay_record(Hardware(environment), record), 1)
      self.assertEqual(len(environment.actions), 1)
      self.assertNotIn("success", selected.read_text())
      self.assertNotIn("video.", selected.read_text())

  def test_replay_detects_state_drift(self):
    record = self.make_writer().record
    record["steps"][0]["state"]["base_position"][0] = 1.0
    with self.assertRaisesRegex(HardwareError, "step 1: base_position"):
      replay_record(Hardware(Environment()), record)

  def test_load_rejects_invalid_command_and_version(self):
    with tempfile.TemporaryDirectory() as directory:
      selected = Path(directory) / "selected.json"
      writer = self.make_writer()
      writer.save(selected)
      record = json.loads(selected.read_text())
      record["steps"][0]["command"]["base"] = [2, 0, 0]
      selected.write_text(json.dumps(record))
      with self.assertRaises(HardwareError):
        load_record(selected)
      record["steps"][0]["command"]["base"] = [0, 0, 0]
      record["version"] = 2
      selected.write_text(json.dumps(record))
      with self.assertRaises(HardwareError):
        load_record(selected)


if __name__ == "__main__":
  unittest.main()
