#!/usr/bin/env python3
"""P02 descriptor discrimination, scene integrity and model catalog tests."""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures/scene_catalog"
sys.path.insert(0, str(ROOT / "tools"))
from scene_catalog import CatalogError, descriptor_for_bundle, validate_descriptor  # noqa: E402


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def mutate(document, mutation):
    pieces = mutation["path"].strip("/").split("/")
    parent = document
    for piece in pieces[:-1]:
        parent = parent[int(piece)] if isinstance(parent, list) else parent[piece]
    final = int(pieces[-1]) if isinstance(parent, list) else pieces[-1]
    if mutation["op"] == "remove":
        del parent[final]
    else:
        parent[final] = mutation["value"]


class SceneCatalogTests(unittest.TestCase):
    def test_builder_matches_frozen_target_and_legacy_is_readable(self):
        self.assertEqual(descriptor_for_bundle(ROOT), fixture("target-descriptor.json"))
        self.assertEqual(validate_descriptor(ROOT, fixture("target-descriptor.json")), "target")
        self.assertEqual(validate_descriptor(ROOT, fixture("legacy-descriptor.json")), "legacy")

    def test_frozen_direct_negative_classifications(self):
        for case in fixture("negative-cases.json")["cases"]:
            if case["mutation"]["target"] != "descriptor" or "expected_direct" not in case:
                continue
            with self.subTest(case=case["id"]):
                descriptor = fixture("target-descriptor.json")
                mutate(descriptor, case["mutation"])
                with self.assertRaises(CatalogError) as caught:
                    validate_descriptor(ROOT, descriptor)
                self.assertEqual(caught.exception.code, case["expected_direct"]["code"])
                self.assertEqual(caught.exception.stage, case["expected_direct"]["stage"])

    def test_changed_scene_bytes_and_redeclared_profile_fail(self):
        with tempfile.TemporaryDirectory(prefix="mujoco-p02-scene-") as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "assets", root / "assets")
            descriptor = descriptor_for_bundle(root)
            scene = root / descriptor["scenes"][0]["path"]
            scene.write_bytes(scene.read_bytes() + b"\n")
            with self.assertRaises(CatalogError) as caught:
                validate_descriptor(root, descriptor)
            self.assertEqual(caught.exception.code, "mujoco_scene_digest_mismatch")
            descriptor["scenes"][0]["sha256"] = hashlib.sha256(scene.read_bytes()).hexdigest()
            contents = scene.read_text().replace("eos_benchmark_pick_place_v1",
                                                 "eos_benchmark_navigation_v1")
            scene.write_text(contents)
            descriptor["scenes"][0]["sha256"] = hashlib.sha256(scene.read_bytes()).hexdigest()
            with self.assertRaises(CatalogError) as caught:
                validate_descriptor(root, descriptor)
            self.assertEqual(caught.exception.code, "mujoco_scene_profile_mismatch")

    def test_missing_declared_device_element_and_unsafe_scene_link_fail(self):
        with tempfile.TemporaryDirectory(prefix="mujoco-p02-device-") as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "assets", root / "assets")
            descriptor = descriptor_for_bundle(root)
            scene = root / descriptor["scenes"][0]["path"]
            scene.write_text(scene.read_text().replace('name="robot_camera"',
                                                      'name="missing_camera"'))
            descriptor["scenes"][0]["sha256"] = hashlib.sha256(scene.read_bytes()).hexdigest()
            with self.assertRaises(CatalogError) as caught:
                validate_descriptor(root, descriptor)
            self.assertEqual(caught.exception.code, "mujoco_scene_profile_mismatch")
            scene.unlink()
            scene.symlink_to(ROOT / "assets/scene.xml")
            with self.assertRaises(CatalogError) as caught:
                validate_descriptor(root, descriptor)
            self.assertEqual(caught.exception.code, "mujoco_scene_invalid")

    def test_navigation_requires_goal_even_if_catalog_hides_a_device(self):
        with tempfile.TemporaryDirectory(prefix="mujoco-p02-goal-") as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "assets", root / "assets")
            descriptor = descriptor_for_bundle(root)
            navigation = root / descriptor["scenes"][1]["path"]
            navigation.write_text(navigation.read_text().replace('name="navigation_goal"',
                                                             'name="missing_goal"'))
            descriptor["scenes"][1]["sha256"] = hashlib.sha256(navigation.read_bytes()).hexdigest()
            descriptor["device_catalog"][2]["scene_ids"] = ["pick-place"]
            with self.assertRaises(CatalogError) as caught:
                validate_descriptor(root, descriptor)
            self.assertEqual(caught.exception.code, "mujoco_scene_profile_mismatch")

    def test_navigation_asset_references_are_present_and_contained(self):
        with tempfile.TemporaryDirectory(prefix="mujoco-p02-assets-") as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "assets", root / "assets")
            descriptor = descriptor_for_bundle(root)
            navigation = root / descriptor["scenes"][1]["path"]
            asset = root / "assets/menagerie/universal_robots_ur5e/assets/base_0.obj"
            asset.unlink()
            with self.assertRaises(CatalogError) as caught:
                validate_descriptor(root, descriptor)
            self.assertEqual(caught.exception.code, "mujoco_scene_invalid")
            asset.symlink_to(ROOT / "assets/menagerie/universal_robots_ur5e/assets/base_0.obj")
            with self.assertRaises(CatalogError) as caught:
                validate_descriptor(root, descriptor)
            self.assertEqual(caught.exception.code, "mujoco_scene_invalid")
            asset.unlink()
            shutil.copy2(ROOT / "assets/menagerie/universal_robots_ur5e/assets/base_0.obj", asset)
            navigation.write_text(navigation.read_text().replace(
                "../../menagerie/universal_robots_ur5e/assets/base_0.obj",
                "../../../../outside.obj"))
            descriptor["scenes"][1]["sha256"] = hashlib.sha256(navigation.read_bytes()).hexdigest()
            with self.assertRaises(CatalogError) as caught:
                validate_descriptor(root, descriptor)
            self.assertEqual(caught.exception.code, "mujoco_scene_invalid")

    def test_legacy_partial_mix_is_never_inferred(self):
        legacy = fixture("legacy-descriptor.json")
        legacy["scenes"][0]["label"] = "A partial target"
        with self.assertRaises(CatalogError) as caught:
            validate_descriptor(ROOT, legacy)
        self.assertEqual(caught.exception.code, "mujoco_catalog_incomplete")
        target = copy.deepcopy(fixture("target-descriptor.json"))
        target.pop("device_catalog")
        with self.assertRaises(CatalogError) as caught:
            validate_descriptor(ROOT, target)
        self.assertEqual(caught.exception.code, "mujoco_catalog_incomplete")

    def test_malformed_nested_types_produce_catalog_errors(self):
        target = fixture("target-descriptor.json")
        target["scenes"][0]["profile"] = []
        with self.assertRaises(CatalogError) as caught:
            validate_descriptor(ROOT, target)
        self.assertEqual(caught.exception.code, "mujoco_scene_invalid")
        target = fixture("target-descriptor.json")
        target["device_catalog"][0]["scene_ids"] = [["pick-place"]]
        with self.assertRaises(CatalogError) as caught:
            validate_descriptor(ROOT, target)
        self.assertEqual(caught.exception.code, "mujoco_device_invalid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
