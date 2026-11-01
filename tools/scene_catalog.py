"""Build and check the package-owned MuJoCo scene/device catalog.

This check runs before a candidate bundle is published. IsOS repeats the
semantic checks after its exact receipt and safe-path verification.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import stat
import xml.etree.ElementTree as ET


CATALOG_VERSION = "0.1.0"
PROFILES = {"eos_benchmark_pick_place_v1", "eos_benchmark_navigation_v1"}
SCENES = (
    {"id": "pick-place", "label": "Pick and place",
     "description": "Reach, grasp and place an object with the simulated arm and base",
     "profile": "eos_benchmark_pick_place_v1", "path": "assets/scene.xml"},
    {"id": "navigation", "label": "Navigation",
     "description": "Move the simulated base to the marked navigation goal",
     "profile": "eos_benchmark_navigation_v1",
     "path": "assets/scenes/navigation/scene.xml"},
)
DEVICES = (
    {"kind": "camera", "id": "cam-0", "label": "Front RGB camera",
     "description": "JPEG observations from the simulated robot camera",
     "scene_ids": ["pick-place", "navigation"]},
    {"kind": "base", "id": "base-0", "label": "Planar base",
     "description": "Bounded body velocity movement in the simulated scene",
     "scene_ids": ["pick-place", "navigation"]},
    {"kind": "manipulator", "id": "arm-0", "label": "Six axis arm",
     "description": "Six joint position movement in the simulated scene",
     "scene_ids": ["pick-place", "navigation"]},
)
DEVICE_KINDS = ("camera", "base", "manipulator")
SCENE_FIELDS = {"id", "path", "label", "description", "profile", "sha256"}
LEGACY_FIELDS = {"schema_version", "package", "entrypoint", "protocol", "scenes",
                 "devices", "runtime"}
TARGET_FIELDS = LEGACY_FIELDS | {"catalog_version", "device_catalog"}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


class CatalogError(ValueError):
    """A stable, sanitized package-catalog classification."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.stage = "descriptor"


def _fail(code: str, message: str) -> None:
    raise CatalogError(code, message)


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _slug(value: object) -> bool:
    return isinstance(value, str) and SLUG.fullmatch(value) is not None


def _scene_file(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value or value.startswith("/"):
        _fail("mujoco_scene_invalid", "Choose a contained scene file")
    pieces = value.split("/")
    if any(piece in ("", ".", "..") for piece in pieces):
        _fail("mujoco_scene_invalid", "Choose a contained scene file")
    path = root
    for piece in pieces:
        path = path / piece
        if path.is_symlink():
            _fail("mujoco_scene_invalid", "Choose a regular scene file")
    try:
        metadata = path.stat()
    except OSError:
        _fail("mujoco_scene_invalid", "Choose an available scene file")
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 8 * 1024 * 1024:
        _fail("mujoco_scene_invalid", "Choose a bounded regular scene file")
    return path


def _asset_file(bundle_root: Path, scene: Path, reference: str) -> None:
    if not reference or reference.startswith("/") or "\\" in reference:
        _fail("mujoco_scene_invalid", "Use contained scene assets")
    relative = list(scene.parent.relative_to(bundle_root).parts)
    for piece in reference.split("/"):
        if piece == "..":
            if not relative:
                _fail("mujoco_scene_invalid", "Use contained scene assets")
            relative.pop()
        elif piece not in ("", "."):
            relative.append(piece)
            if bundle_root.joinpath(*relative).is_symlink():
                _fail("mujoco_scene_invalid", "Use regular scene assets")
    try:
        metadata = bundle_root.joinpath(*relative).stat()
    except OSError:
        _fail("mujoco_scene_invalid", "Include every scene asset")
    if not stat.S_ISREG(metadata.st_mode):
        _fail("mujoco_scene_invalid", "Use regular scene assets")


def _scene_model(bundle_root: Path, path: Path) -> tuple[str, dict[str, set[str]]]:
    contents = path.read_bytes()
    if b"<!DOCTYPE" in contents.upper() or b"<!ENTITY" in contents.upper():
        _fail("mujoco_scene_profile_mismatch", "Use a supported scene profile")
    try:
        root = ET.fromstring(contents)
    except ET.ParseError:
        _fail("mujoco_scene_profile_mismatch", "Use a supported scene profile")
    if root.tag != "mujoco":
        _fail("mujoco_scene_profile_mismatch", "Use a MuJoCo scene")
    # MJCF resolves file attributes relative to the scene XML. Navigation uses
    # ../../menagerie, which is valid only while it remains inside the bundle.
    for element in root.iter():
        reference = element.get("file")
        if reference is None:
            continue
        _asset_file(bundle_root, path, reference)
    markers = [element.get("name") for element in root.iter("numeric")
               if (element.get("name") or "").startswith("eos_benchmark_")]
    if len(markers) != 1 or markers[0] not in PROFILES:
        _fail("mujoco_scene_profile_mismatch", "Use exactly one supported scene profile")
    names: dict[str, set[str]] = {}
    for element in root.iter():
        name = element.get("name")
        if name:
            names.setdefault(element.tag, set()).add(name)
    required = (
        {"gr_pinch", "attachment_site"} <= names.get("site", set())
        and "benchmark_object" in names.get("body", set())
        and "object_free" in names.get("freejoint", set())
        and "gr_fingers_actuator" in names.get("general", set())
        and {"gr_left_pad1", "gr_right_pad1"} <= names.get("geom", set())
        and (markers[0] != "eos_benchmark_navigation_v1"
             or "navigation_goal" in names.get("site", set()))
    )
    if not required or any(not _supports(kind, markers[0], names) for kind in DEVICE_KINDS):
        _fail("mujoco_scene_profile_mismatch", "Match the supported scene model elements")
    return markers[0], names


def _supports(kind: str, profile: str, names: dict[str, set[str]]) -> bool:
    if kind == "camera":
        return "robot_camera" in names.get("camera", set())
    if kind == "base":
        return {"base_x", "base_y", "base_yaw"} <= names.get("joint", set()) and {
            "base_x_motor", "base_y_motor", "base_yaw_motor"} <= names.get("velocity", set())
    joints = {"shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
              "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"}
    actuators = {"shoulder_pan", "shoulder_lift", "elbow", "wrist_1", "wrist_2", "wrist_3"}
    if profile == "eos_benchmark_navigation_v1" and "navigation_goal" not in names.get("site", set()):
        return False
    return joints <= names.get("joint", set()) and actuators <= names.get("general", set())


def validate_descriptor(root: Path, descriptor: dict) -> str:
    """Return ``legacy`` or ``target`` after strict catalog validation."""
    if not isinstance(descriptor, dict):
        _fail("mujoco_catalog_incomplete", "Provide a complete simulator descriptor")
    version = descriptor.get("catalog_version")
    if version is not None and version != CATALOG_VERSION:
        _fail("mujoco_catalog_unsupported", "Use a supported catalog version")
    target = version == CATALOG_VERSION
    fields = TARGET_FIELDS if target else LEGACY_FIELDS
    if set(descriptor) != fields:
        _fail("mujoco_catalog_incomplete", "Provide one complete catalog format")
    scenes = descriptor.get("scenes")
    devices = descriptor.get("devices")
    if not isinstance(scenes, list) or not scenes or not isinstance(devices, dict):
        _fail("mujoco_catalog_incomplete", "Provide scene and device entries")
    if set(devices) != set(DEVICE_KINDS) or any(not _slug(value) for value in devices.values()):
        _fail("mujoco_device_invalid", "Provide the declared simulator devices")
    if len(set(devices.values())) != len(DEVICE_KINDS):
        _fail("mujoco_device_invalid", "Use distinct simulator device IDs")
    scene_ids: set[str] = set()
    models: dict[str, tuple[str, dict[str, set[str]]]] = {}
    for scene in scenes:
        if not isinstance(scene, dict):
            _fail("mujoco_scene_invalid", "Provide a valid scene entry")
        expected = SCENE_FIELDS if target else {"id", "path"}
        if set(scene) != expected:
            _fail("mujoco_catalog_incomplete", "Provide one complete scene format")
        scene_id = scene["id"]
        if not _slug(scene_id) or scene_id in scene_ids:
            _fail("mujoco_scene_invalid", "Use unique nonblank scene IDs")
        scene_ids.add(scene_id)
        if target:
            if not _nonblank(scene["label"]) or not _nonblank(scene["description"]):
                _fail("mujoco_scene_invalid", "Describe each scene")
            if not isinstance(scene["profile"], str) or scene["profile"] not in PROFILES:
                _fail("mujoco_scene_invalid", "Use a supported scene profile")
            if not isinstance(scene["sha256"], str) or not HASH.fullmatch(scene["sha256"]):
                _fail("mujoco_scene_invalid", "Use a lowercase scene SHA-256")
            path = _scene_file(root, scene["path"])
            if hashlib.sha256(path.read_bytes()).hexdigest() != scene["sha256"]:
                _fail("mujoco_scene_digest_mismatch", "Rebuild the scene catalog digest")
            actual, names = _scene_model(root, path)
            if actual != scene["profile"]:
                _fail("mujoco_scene_profile_mismatch", "Match the scene's benchmark profile")
            models[scene_id] = (actual, names)
        else:
            _scene_file(root, scene["path"])
    if not target:
        return "legacy"
    catalog = descriptor["device_catalog"]
    if not isinstance(catalog, list) or len(catalog) != len(DEVICE_KINDS):
        _fail("mujoco_catalog_incomplete", "Provide every device description")
    seen_kinds: set[str] = set()
    seen_ids: set[str] = set()
    for device in catalog:
        if not isinstance(device, dict) or set(device) != {
                "kind", "id", "label", "description", "scene_ids"}:
            _fail("mujoco_catalog_incomplete", "Provide a complete device entry")
        kind, device_id = device["kind"], device["id"]
        if kind not in DEVICE_KINDS or kind in seen_kinds or not _slug(device_id) or device_id in seen_ids:
            _fail("mujoco_device_invalid", "Use unique registered devices")
        seen_kinds.add(kind)
        seen_ids.add(device_id)
        if devices[kind] != device_id or not _nonblank(device["label"]) or not _nonblank(device["description"]):
            _fail("mujoco_device_invalid", "Match and describe the device map")
        supported = device["scene_ids"]
        if (not isinstance(supported, list) or not supported
                or any(not isinstance(scene_id, str) for scene_id in supported)
                or len(set(supported)) != len(supported)
                or any(scene_id not in scene_ids for scene_id in supported)):
            _fail("mujoco_device_invalid", "Use known unique device scene IDs")
        for scene_id in supported:
            profile, names = models[scene_id]
            if not _supports(kind, profile, names):
                _fail("mujoco_scene_profile_mismatch", "Match devices to scene model elements")
    return "target"


def descriptor_for_bundle(root: Path) -> dict:
    scenes = [{**scene, "sha256": hashlib.sha256(_scene_file(root, scene["path"]).read_bytes()).hexdigest()}
              for scene in SCENES]
    descriptor = {
        "schema_version": "2.0.0", "catalog_version": CATALOG_VERSION,
        "package": {"id": "island/mujoco-sim", "version": "0.1.1"},
        "entrypoint": "bin/eos-mujoco-sim", "protocol": "mujoco-v2",
        "scenes": scenes,
        "devices": {device["kind"]: device["id"] for device in DEVICES},
        "device_catalog": [dict(device) for device in DEVICES],
        "runtime": {"mujoco_version": "3.16.0", "environment_variable": "MUJOCO_ROOT",
                    "library": "lib/libmujoco.so.3.16.0"},
    }
    validate_descriptor(root, descriptor)
    return descriptor
