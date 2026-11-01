#!/usr/bin/env python3
"""Check the packaged node set before IsOS performs full graph admission."""

from pathlib import Path
import json
import re
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from node_contributions import contributions  # noqa: E402


def strings(value: object) -> list[str]:
  if isinstance(value, str):
    return [value]
  if isinstance(value, dict):
    return [item for child in value.values() for item in strings(child)]
  if isinstance(value, list):
    return [item for child in value for item in strings(child)]
  return []


class NodeContributionTests(unittest.TestCase):
  def test_node_set_has_resolvable_symbols_and_parameters(self) -> None:
    contract = contributions()
    node_set = contract["node_sets"][0]
    refs = {node["ref"] for node in node_set["nodes"]}
    self.assertEqual(refs, {"simulator", "front", "drive", "arm", "base-velocity",
                            "arm-movej", "camera-gate"})
    contributed_types = {node_type["id"] for node_type in contract["node_types"]}
    self.assertEqual(contributed_types,
                     {"eos.process.mujoco@v1.0", "eos.process.mujoco@v0.1"})
    declared = set(node_set["parameters"])
    for node in node_set["nodes"]:
      if node["profile"]["node_type"] in contributed_types:
        self.assertEqual(node["core"], "eos")
        self.assertEqual(node["group"], "mujoco")
      for value in strings(node["profile"]):
        if value.startswith("@"):
          self.assertIn(value[1:], refs)
        for parameter in re.findall(r"\$\{([^}]+)\}", value):
          self.assertIn(parameter, declared)

  def test_new_graph_uses_generic_types_and_no_unregistered_ui_type(self) -> None:
    nodes = {node["ref"]: node for node in contributions()["node_sets"][0]["nodes"]}
    gate = nodes["camera-gate"]
    self.assertEqual(gate["profile"]["inputs"]["frame"],
                     {"node": "@front", "output": "frame"})
    self.assertEqual((gate["core"], gate["layer"], gate["group"]),
                     ("eos", "interface", "gate"))
    self.assertEqual(gate["profile"]["node_type"], "eos.interface.camera_gate@v0.1")
    self.assertNotIn("vision", nodes)

  def test_each_device_uses_one_package_pinned_adapter_and_typed_binding(self) -> None:
    contract = contributions()
    nodes = {node["ref"]: node for node in contract["node_sets"][0]["nodes"]}
    family = contract["adapter_families"][0]
    self.assertEqual(set(family["device_kinds"]), {"camera", "base", "manipulator"})
    self.assertEqual(set(family["supported_primitives"]),
                     {"base.velocity@1.0.0", "arm.movej@1.0.0"})
    for ref, kind in (("front", "camera"), ("drive", "base"), ("arm", "manipulator")):
      node = nodes[ref]
      self.assertEqual((node["core"], node["layer"], node["group"]),
                       ("eos", "hardware", kind))
      profile = node["profile"]
      self.assertEqual(profile["node_type"], f"eos.hardware.{kind}@v0.1")
      self.assertNotIn("package", profile)
      self.assertEqual(profile["adapter"]["type"], family["id"])
      self.assertEqual(profile["adapter"]["package"],
                       {"id": "island/mujoco-sim", "version": "0.1.1"})
      selected = {"front": "camera_device", "drive": "base_device",
                  "arm": "manipulator_device"}[ref]
      self.assertEqual(profile["adapter"]["settings"]["device_id"], f"${{{selected}}}")
      self.assertEqual(profile["adapter"]["settings"]["simulator_node"], f"${{{selected}}}")
    for device, binding, primitive in (("drive", "base-velocity", "base.velocity"),
                                       ("arm", "arm-movej", "arm.movej")):
      self.assertEqual(nodes[device]["profile"]["inputs"]["command"],
                       [{"node": f"@{binding}", "output": "command"}])
      self.assertEqual(nodes[binding]["profile"]["settings"]["primitive_name"], primitive)
      self.assertEqual(nodes[binding]["profile"]["settings"]["primitive_version"], "1.0.0")

  def test_ports_describe_frequency_transport_and_data_class(self) -> None:
    contract = contributions()
    for node_type in contract["node_types"]:
      for port in node_type["inputs"] + node_type["outputs"]:
        self.assertTrue(port["description"])
        self.assertIn(port["data_class"],
                      {"image", "observation", "command", "event", "state", "opaque"})

  def test_target_contribution_matches_frozen_projection(self) -> None:
    expected = json.loads((Path(__file__).resolve().parent /
                           "fixtures/scene_catalog/expected-contribution.json").read_text())
    contract = contributions()
    types = {entry["id"]: entry for entry in contract["node_types"]}
    current = types[expected["process_type"]["id"]]
    self.assertEqual((current["core"], current["layer"], current["group"]),
                     (expected["process_type"]["core"], expected["process_type"]["layer"],
                      expected["process_type"]["group"]))
    self.assertTrue(current["description"].strip())
    self.assertEqual(next(setting for setting in current["settings"] if setting["name"] == "scene")["selector"],
                     expected["process_type"]["scene_selector"])
    node_set = contract["node_sets"][0]
    self.assertEqual(node_set["id"], expected["node_set"]["id"])
    self.assertEqual({name: item.get("default") for name, item in node_set["parameters"].items()},
                     expected["node_set"]["parameters"])
    self.assertEqual([node["profile"]["node_type"] for node in node_set["nodes"]],
                     expected["node_set"]["types"])


if __name__ == "__main__":
  unittest.main()
