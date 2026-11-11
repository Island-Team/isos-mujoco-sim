#!/usr/bin/env python3
"""Check the packaged node set before IsOS performs full graph admission."""

from pathlib import Path
import json
import re
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from nodes import contributions  # noqa: E402


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
    self.assertEqual(refs, {"simulator", "front"})
    contributed_types = {node_type["id"] for node_type in contract["node_types"]}
    self.assertEqual(contributed_types, {"eos.process.mujoco.simulator@v0.2"})
    for definition in contract["node_types"]:
      self.assertTrue(definition["description"].strip())
      for setting in definition["settings"]:
        self.assertTrue(setting["description"].strip())
      for port in definition["inputs"] + definition["outputs"]:
        self.assertTrue(port["description"].strip())
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

  def test_each_device_uses_one_package_pinned_observation_adapter(self) -> None:
    contract = contributions()
    nodes = {node["ref"]: node for node in contract["node_sets"][0]["nodes"]}
    family = contract["adapter_families"][0]
    self.assertEqual(set(family["device_kinds"]), {"camera", "base", "manipulator"})
    self.assertEqual(family["supported_primitives"], [])
    for ref, kind in (("front", "camera"),):
      node = nodes[ref]
      self.assertEqual((node["core"], node["layer"], node["group"]),
                       ("eos", "hardware", kind))
      profile = node["profile"]
      self.assertEqual(profile["node_type"], f"eos.hardware.{kind}.device@v0.2")
      self.assertNotIn("package", profile)
      self.assertEqual(profile["adapter"]["type"], family["id"])
      self.assertEqual(profile["adapter"]["package"],
                       {"id": "island/mujoco-sim", "version": "0.2.0"})
      selected = {"front": "camera_device"}[ref]
      self.assertEqual(profile["adapter"]["settings"]["device_id"], f"${{{selected}}}")
      self.assertEqual(profile["adapter"]["settings"]["simulator_node"], f"${{{selected}}}")
      self.assertEqual(profile["capabilities"], ["jpeg"])
    self.assertNotIn("drive", nodes)
    self.assertNotIn("arm", nodes)

  def test_patch_release_uses_exact_package_pin(self) -> None:
    contract = contributions("0.2.7")
    for node in contract["node_sets"][0]["nodes"]:
      adapter = node["profile"].get("adapter")
      if adapter:
        self.assertEqual(adapter["package"],
                         {"id": "island/mujoco-sim", "version": "0.2.7"})

  def test_managed_process_declares_verified_inputs(self) -> None:
    process = contributions()["processes"][0]
    self.assertEqual(process["args"], ["--managed-strict-socket", "--v2-socket",
                                       "${socket}", "--scene", "${resource.scene.path}"])

  def test_ports_describe_frequency_transport_and_data_class(self) -> None:
    contract = contributions()
    for node_type in contract["node_types"]:
      for port in node_type["inputs"] + node_type["outputs"]:
        self.assertTrue(port["description"])
        self.assertIn(port["data_class"],
                      {"image", "observation", "command", "event", "state", "opaque"})
        self.assertEqual(port["contract"],
                         {"owner": "eos", "id": port["data_type"], "version": "0.2"})

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
    self.assertEqual(current["implementation"],
                     {"kind": "managed_process", "interface": "mujoco-v2",
                      "version": "1", "lifecycle_adapter": "mujoco-v2"})
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
