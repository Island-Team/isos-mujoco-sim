#!/usr/bin/env python3
"""Check the packaged node set before IsOS performs full graph admission."""

from pathlib import Path
import json
import re
import sys
import tomllib
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
  def test_package_selectors_match_verified_resources_and_defaults(self) -> None:
    root = Path(__file__).resolve().parents[1]
    descriptor = json.loads((root / "config/package-config.json").read_text())
    sections = {section["id"]: section for section in descriptor["sections"]}
    config = tomllib.loads((root / "config/package.toml").read_text())
    resources = json.loads((root / "tests/fixtures/scene_catalog/target-descriptor.json").read_text())
    scene = next(field for field in sections["services.native"]["fields"]
                 if field["name"] == "scene")
    task = next(field for field in sections["services.robocasa"]["fields"]
                if field["name"] == "task")
    for field in (scene, task):
      self.assertEqual(field["type"], "enum")
      self.assertEqual(len({option["value"] for option in field["options"]}),
                       len(field["options"]))
      for option in field["options"]:
        self.assertTrue(option["label"]["en"])
        self.assertTrue(option["label"]["cn"])
    self.assertEqual({option["value"] for option in scene["options"]},
                     {item["id"] for item in resources["scenes"]})
    self.assertEqual([option["value"] for option in task["options"]], ["CloseFridge"])
    self.assertEqual(scene["default"], config["services"]["native"]["scene"])
    self.assertEqual(task["default"], config["services"]["robocasa"]["task"])

  def test_user_camera_configuration_defaults_and_bounds(self) -> None:
    root = Path(__file__).resolve().parents[1]
    descriptor = json.loads((root / "config/package-config.json").read_text())
    section = next(item for item in descriptor["sections"] if item["id"] == "services.robocasa")
    fields = {item["name"]: item for item in section["fields"]}
    template = tomllib.loads((root / "config/package.toml").read_text())["services"]["robocasa"]
    for name in ("camera_width", "camera_height"):
      self.assertNotIn(name, fields)
      self.assertNotIn(name, template)
    contract = contributions("0.2.5")
    camera = next(item for item in contract["node_types"] if item["id"] == "eos.hardware.camera.device@v0.2")
    for field in camera["settings"]:
      self.assertEqual((field["data_type"], field["min"], field["max"], field["unit"]),
                       ("positive_integer", 64, 2048, "px"))
    presets = [node["profile"] for group in contract["node_sets"] if group["id"] == "robocasa"
               for node in group["nodes"] if node["group"] == "camera"]
    self.assertEqual(len(presets), 3)
    for profile in presets:
      self.assertEqual(profile["settings"], {"camera_width": 1280, "camera_height": 720})

  def test_robocasa_service_receives_configured_camera_size(self) -> None:
    contract = contributions("0.2.5")
    service = next(item for item in contract["runtime_services"] if item["id"] == "robocasa")
    environment = {item["name"]: item["value"] for item in service["environment"]}
    self.assertEqual(environment["ISOS_ROBOCASA_CAMERA_SIZES"], "${selected_nodes.settings_json}")
    self.assertEqual(service["required_node_settings"],
                     {"eos.hardware.camera.device@v0.2": ["camera_width", "camera_height"]})
    old = contributions("0.2.4")
    old_service = next(item for item in old["runtime_services"] if item["id"] == "robocasa")
    old_environment = {item["name"]: item["value"] for item in old_service["environment"]}
    self.assertEqual(old_environment["ISOS_ROBOCASA_CAMERA_WIDTH"], "${config.service.camera_width}")
    self.assertEqual(old_environment["ISOS_ROBOCASA_CAMERA_HEIGHT"], "${config.service.camera_height}")

  def test_native_service_receives_configured_camera_size(self) -> None:
    contract = contributions("0.2.5")
    native = next(item for item in contract["runtime_services"] if item["id"] == "native")
    environment = {item["name"]: item["value"] for item in native["environment"]}
    self.assertEqual(environment["ISOS_NATIVE_CAMERA_SIZES"], "${selected_nodes.settings_json}")
    self.assertEqual(native["required_node_settings"],
                     {"eos.hardware.camera.device@v0.2": ["camera_width", "camera_height"]})
    camera = next(node["profile"] for node_set in contract["node_sets"]
                  if node_set["id"] == "native" for node in node_set["nodes"]
                  if node["group"] == "camera")
    self.assertEqual(camera["settings"], {"camera_width": 1280, "camera_height": 720})

  def test_robocasa_service_requires_prepared_host_paths(self) -> None:
    services = {item["id"]: item for item in contributions("0.2.4")["runtime_services"]}
    self.assertEqual(services["robocasa"]["requirements"], [
      {"path": "${config.host.python_interpreter}", "kind": "file"},
      {"path": "${config.host.robocasa_assets}", "kind": "directory"},
    ])
    self.assertNotIn("python_interpreter", str(services["native"]))

  def test_full_hardware_cameras_allow_2048_rgb_payload(self) -> None:
    contract = contributions("0.2.5")
    cameras = [node["profile"] for node_set in contract["node_sets"]
               for node in node_set["nodes"] if node["profile"]["id"] in ("left", "right", "wrist")]
    self.assertEqual(len(cameras), 3)
    for profile in cameras:
      self.assertEqual(profile["observation"]["max_payload_bytes"], 20 * 1024 * 1024)

  def test_current_camera_ports_and_capture_schedule_match_eos(self) -> None:
    contract = contributions("0.2.5")
    camera = next(node for node in contract["node_types"] if node["id"] == "eos.hardware.camera.device@v0.2")
    self.assertEqual(camera["outputs"][0]["data_class"], "image")
    self.assertEqual(camera["outputs"][0]["frequency_hz"], 30.0)
    for node_set in contract["node_sets"]:
      for node in node_set["nodes"]:
        if node["profile"]["node_type"] == camera["id"]:
          self.assertEqual(node["profile"]["adapter"]["settings"]["frequency_hz"], 30.0)

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
      self.assertEqual(profile["observation"]["max_payload_bytes"], 12582912)
    self.assertNotIn("drive", nodes)
    self.assertNotIn("arm", nodes)

  def test_patch_release_uses_exact_package_pin(self) -> None:
    contract = contributions("0.2.7")
    for node in contract["node_sets"][0]["nodes"]:
      self.assertEqual(node["profile"]["package"],
                       {"id": "island/mujoco-sim", "version": "0.2.7"})
      adapter = node["profile"].get("adapter")
      if adapter:
        self.assertEqual(adapter["package"],
                         {"id": "island/mujoco-sim", "version": "0.2.7"})
      if node["profile"]["node_type"] == "eos.hardware.camera.device@v0.2":
        self.assertEqual(node["profile"]["capabilities"], ["jpeg"])

  def test_current_hardware_types_are_package_declared(self) -> None:
    contract = contributions("0.2.7")
    definitions = {node["id"]: node for node in contract["node_types"]}
    self.assertEqual(len(definitions), 7)
    referenced = {node["profile"]["node_type"]
                  for node_set in contract["node_sets"] for node in node_set["nodes"]}
    self.assertEqual(referenced, set(definitions))
    for node_set in contract["node_sets"]:
      for node in node_set["nodes"]:
        definition = definitions[node["profile"]["node_type"]]
        self.assertEqual((definition["core"], definition["layer"], definition["group"]),
                         (node["core"], node["layer"], node["group"]))
        self.assertEqual(definition["implementation"],
                         {"kind": "native_plugin", "abi": "isos_node_v2",
                          "library": "lib/libmujoco-eos-node.so"})

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
