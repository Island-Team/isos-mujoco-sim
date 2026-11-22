#!/usr/bin/env python3
"""Generate hardware graph bindings and model controls from a live robot manifest.

This is an operator preparation tool. It creates and closes a private episode;
its output is a graph fragment to review and Apply, never actuator authority.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.nodes import PACKAGE_VERSION, contributions
from tools.robocasa_worker import CAMERA_NODES, create_hardware


def build_graph(manifest: dict, instance: str = "primary", camera_size=(256, 256)) -> dict:
    templates = {item["group"]: item["profile"] for group in contributions()["node_sets"]
                 if group["id"] == "robocasa" for item in group["nodes"]}
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    manifest_digest = hashlib.sha256(encoded).hexdigest()
    prefix = f"eos/{instance}/"
    dispatcher = prefix + "dispatcher/parts/control"
    nodes, controls, members, bindings = {}, [], [], []
    for part in manifest["parts"]:
        role = part["role"]
        group = "manipulator" if role == "arm" else role
        if group not in templates:
            continue
        name = part["id"].split("/")[-1]
        path = prefix + f"hardware/{group}/{name}"
        profile = deepcopy(templates[group])
        profile.pop("id", None)
        profile["label"] = name
        profile["description"] = f"Discovered {manifest['robot']} {role}"
        profile["adapter"]["settings"]["device_id"] = part["id"]
        profile["adapter"]["settings"]["robot_manifest_digest"] = manifest_digest
        profile["inputs"] = {}
        if role == "camera":
            profile["settings"] = {"camera_width": camera_size[0], "camera_height": camera_size[1]}
            profile["frame_id"] = part["frame"]
        elif role == "arm":
            profile["frame_id"] = part["frame"]
        elif role == "torso":
            profile["frame_id"] = "joint_local"
        elif role == "gripper":
            profile["frame_id"] = "joint_local"
        if not part["can_observe"]:
            profile.pop("observation", None)
        if part["can_observe"]:
            profile["adapter"]["settings"]["frequency_hz"] = 10.0 if role != "camera" else 30.0
            members.append({"id": part["id"], "node": path, "port": "frame" if role == "camera" else "observation",
                            "type_id": {"arm": "pose_state@v0.2", "base": "pose_state@v0.2",
                              "gripper": "gripper_state@v0.2", "torso": "joint_channels@v0.1",
                              "camera": "image_frame@v0.2"}[role]})
        if part["can_control"]:
            port = name.replace("-", "_")
            bindings.append({"port": port, "hardware_node": path, "hardware_input": "command"})
            profile["inputs"]["command"] = {"node": dispatcher, "output": port}
            control = {"id": part["id"], "part": part["id"], "node": "eos/" + path.removeprefix(prefix),
                       "port": "command", "dispatcher": "eos/" + dispatcher.removeprefix(prefix), "part_port": port,
                       "schema": part["command_schema"], "description": part["semantics"],
                       "units": part["unit"], "frame": part["frame"],
                       "positive_directions": part["positive_directions"],
                       "prerequisites": [part["id"]] if part["can_observe"] else []}
            if "stop_payload" in part:
                control["stop_payload"] = part["stop_payload"]
            control["description"] += "; " + part.get("mapping", "") + "; output/actuator bounds=" + json.dumps(
                {key: part[key] for key in ("output_min", "output_max", "actuator_min", "actuator_max") if key in part},
                separators=(",", ":"))
            if "output_units" in part:
                control["description"] += "; physical output units=" + json.dumps(part["output_units"], separators=(",", ":"))
            controls.append(control)
        nodes[path] = profile
    nodes[dispatcher] = {"node_type": "eos.dispatcher.parts.control@v0.2", "inputs": {},
                         "label": "Discovered robot body Dispatcher", "settings": {"parts": bindings}}
    return {"nodes": nodes, "capabilities": {"controls": controls},
            "members": members, "robot_manifest": manifest, "robot_manifest_digest": manifest_digest,
            "package": {"id": "island/mujoco-sim", "version": PACKAGE_VERSION}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--robot", default="PandaOmron")
    parser.add_argument("--task", default="CloseFridge")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--instance", default="primary")
    parser.add_argument("--camera", action="append", help="selected robocasa/camera/device ID; repeatable")
    parser.add_argument("--camera-size", type=int, default=256)
    parser.add_argument("--camera-width", type=int)
    parser.add_argument("--camera-height", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    width, height = args.camera_width or args.camera_size, args.camera_height or args.camera_size
    if not 64 <= width <= 2048 or not 64 <= height <= 2048 or not 0 <= args.seed <= 4294967295:
        parser.error("camera-size must be 64–2048 and seed uint32")
    sizes = {device: (width, height) for device in (args.camera or CAMERA_NODES)}
    hardware = create_hardware(args.task, args.seed, args.assets, width,
                               height, robot=args.robot, camera_sizes=sizes)
    try:
        result = build_graph(hardware.manifest(), args.instance, (width, height))
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    finally:
        hardware.close()


if __name__ == "__main__":
    main()
