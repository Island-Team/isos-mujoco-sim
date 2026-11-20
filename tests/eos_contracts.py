#!/usr/bin/env python3
"""Check packaged hardware against the real EOS catalog and graph admission.

Usage: python3 tests/eos_contracts.py --eos-profile ../isos-p/target/debug/aether-profile
    --plugin build/libmujoco-eos-node.so

This checks admission, not physical runtime behavior. The EOS CLI does not expose
derived Dispatcher port metadata; its graph validator derives and checks those
ports. The registered hardware metadata is checked against the shared catalog.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from nodes import contributions  # noqa: E402


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def graph_for(preset, definitions, mode=False):
    groups, parts = {}, []
    for selected in preset["nodes"]:
        node = copy.deepcopy(selected["profile"])
        group = selected["group"]
        groups.setdefault(group, {"nodes": {}})["nodes"][node["id"]] = node
        inputs = definitions[node["node_type"]]["inputs"]
        if not inputs:
            continue
        command = next((port for port in inputs if mode and port["name"] == "mode"), inputs[0])
        port_name = node["id"]
        parts.append({"port": port_name, "hardware_node": f"eos/hardware/{group}/{node['id']}",
                      "hardware_input": command["name"]})
        node["inputs"] = {command["name"]: {"node": "eos/dispatcher/parts/control", "output": port_name}}
    return {"version": "0.2.1", "robot": {"id": "contract-test", "name": "Contract test"},
            "cores": {"eos": {"layers": {"hardware": {"groups": groups}, "dispatcher": {
                "groups": {"parts": {"nodes": {"control": {
                    "id": "control", "node_type": "eos.dispatcher.parts.control@v0.2",
                    "label": "Control", "settings": {"parts": parts}}}}}}}}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eos-profile", required=True, type=Path)
    parser.add_argument("--plugin", required=True, type=Path)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/test/20261119-standard-hardware/eos-contracts")
    args = parser.parse_args()
    executable, plugin = args.eos_profile.resolve(), args.plugin.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    current = contributions("0.2.8")
    definitions = {item["id"]: item for item in current["node_types"]}
    with tempfile.TemporaryDirectory(prefix="mujoco-eos-contracts-") as directory:
        stage = Path(directory)
        (stage / "lib").mkdir()
        shutil.copyfile(plugin, stage / "lib/libmujoco-eos-node.so")
        digest = hashlib.sha256(plugin.read_bytes()).hexdigest()
        sidecar = {"package": {"id": "island/mujoco-sim", "version": "0.2.8"},
                   "libraries": [{"path": "lib/libmujoco-eos-node.so", "sha256": digest}],
                   "adapters": [{"family": "mujoco-v2", "library": "lib/libmujoco-eos-node.so", "sha256": digest}]}
        for key in ("node_types", "safety_adapters", "adapter_families"):
            sidecar[key] = current[key]
        sidecar_path = stage / "node-types.json"
        write_json(sidecar_path, sidecar)
        write_json(stage / "receipt.json", {
            "sidecar_sha256": hashlib.sha256(sidecar_path.read_bytes()).hexdigest()})
        write_json(output / "node-types.json", sidecar)

        def invoke(name, command, success=True):
            result = subprocess.run([str(executable), *command, "--node-types", str(sidecar_path)],
                                    capture_output=True, text=True, timeout=30)
            (output / f"{name}.log").write_text(
                f"command: {executable} {' '.join(command)} --node-types {sidecar_path}\n"
                f"exit: {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
            assert (result.returncode == 0) == success, (name, result.stdout, result.stderr)
            return result.stdout

        catalog = json.loads(invoke("catalog", ["catalog"]))
        write_json(output / "catalog.json", catalog)
        types = {item["id"]: item for item in catalog["types"]}
        datatypes = {item["id"]: item for item in catalog["data_types"]}
        for definition in definitions.values():
            registered = types[definition["id"]]
            for direction in ("inputs", "outputs"):
                for declared, actual in zip(definition[direction], registered[direction], strict=True):
                    for key in ("name", "data_type", "data_class", "transport", "delivery_mode", "contract"):
                        assert actual[key] == declared[key], (definition["id"], key)
                    descriptor = datatypes[actual["data_type"]]
                    assert actual["contract"]["id"] == descriptor["id"]
                    assert descriptor["codec"] == "json_v1"
                    assert descriptor["media_type"] == "application/json"

        count = 0
        for preset in current["node_sets"]:
            for mode in ([False, True] if preset["id"] == "robocasa" else [False]):
                name = preset["id"] + ("-mode" if mode else "")
                graph = graph_for(preset, definitions, mode)
                path = output / f"{name}.json"
                write_json(path, graph)
                invoke(name, ["validate", "--file", str(path)])
                count += 1
                for value in (None, 63, 2049, "1280"):
                    invalid = copy.deepcopy(graph)
                    cameras = invalid["cores"]["eos"]["layers"]["hardware"]["groups"]["camera"]["nodes"]
                    settings = next(iter(cameras.values()))["settings"]
                    if value is None:
                        settings.pop("camera_width")
                    else:
                        settings["camera_width"] = value
                    invalid_path = output / f"{name}-camera-{value}.json"
                    write_json(invalid_path, invalid)
                    invoke(f"{name}-camera-{value}", ["validate", "--file", str(invalid_path)], False)
                    count += 1
                bad = copy.deepcopy(graph)
                dispatcher = bad["cores"]["eos"]["layers"]["dispatcher"]["groups"]["parts"]["nodes"]["control"]
                dispatcher["settings"]["parts"].pop()
                bad_path = output / f"{name}-unassigned.json"
                write_json(bad_path, bad)
                invoke(name + "-unassigned", ["validate", "--file", str(bad_path)], False)
                count += 1
                bypass = copy.deepcopy(graph)
                layers = bypass["cores"]["eos"]["layers"]
                layers["skill"] = {"groups": {"demo": {"nodes": {"joint_position": {
                    "id": "joint_position", "node_type": "eos.skill.demo.joint_position@v0.2",
                    "label": "Bypass source"}}}}}
                first = layers["dispatcher"]["groups"]["parts"]["nodes"]["control"]["settings"]["parts"][0]
                _, _, group, node_id = first["hardware_node"].split("/")
                layers["hardware"]["groups"][group]["nodes"][node_id]["inputs"][first["hardware_input"]] = {
                    "node": "eos/skill/demo/joint_position", "output": "command"}
                bypass_path = output / f"{name}-bypass.json"
                write_json(bypass_path, bypass)
                invoke(name + "-bypass", ["validate", "--file", str(bypass_path)], False)
                count += 1

        sample = {"clock": "simulation", "source_time_ns": 1, "sequence": 1, "frame_id": "world"}
        payloads = {
            "base_twist_command@v0.2": {"frame_id": "base_link", "vx_m_s": .1, "vy_m_s": 0,
                                        "yaw_rate_rad_s": 0, "lease_ms": 100},
            "joint_position_command@v0.2": {"joint_names": ["joint"], "position_rad": [.1]},
            "normalized_axes_command@v0.2": {"axes": {"lift": .2}, "lease_ms": 100},
            "control_mode_command@v0.2": {"mode": "delta"},
            "gripper_binary_command@v0.2": {"action": "close"},
            "base_state@v0.2": {"sample": sample, "x_m": 0, "y_m": 0, "yaw_rad": 0,
                                "vx_m_s": 0, "vy_m_s": 0, "yaw_rate_rad_s": 0},
            "joint_state@v0.2": {"sample": sample, "joint_names": ["joint"],
                                 "position_rad": [0], "velocity_rad_s": [0]},
            "pose_state@v0.2": {"sample": sample, "position_m": [0, 0, 0], "orientation_xyzw": [0, 0, 0, 1]},
            "gripper_state@v0.2": {"sample": sample, "channels": [{"name": "opening", "value": 0, "unit": "%"}]},
        }
        for datatype, payload in payloads.items():
            validator = jsonschema.validators.validator_for(datatypes[datatype]["schema"])(datatypes[datatype]["schema"])
            validator.validate(payload)
            assert not validator.is_valid({**payload, "legacy_extra": True}), datatype
        write_json(output / "payloads.json", payloads)
        print(f"EOS hardware interop: seven registered types, {count} graph admission cases, "
              f"{len(payloads)} standard payload schemas: PASS")


if __name__ == "__main__":
    main()
