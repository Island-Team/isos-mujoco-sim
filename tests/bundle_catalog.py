#!/usr/bin/env python3
"""Build a real candidate and check its descriptor, sidecar and archive pin."""

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "tests/fixtures/scene_catalog/target-descriptor.json").read_text())


def main() -> None:
    binary = Path(sys.argv[1]).resolve()
    mujoco_root = Path(sys.argv[2]).resolve()
    if binary.name != "eos-mujoco-sim" or not binary.is_file():
        raise SystemExit("expected built eos-mujoco-sim executable")
    with tempfile.TemporaryDirectory(prefix="mujoco-p02-bundle-") as temporary:
        output = Path(temporary) / "bundle"
        subprocess.run([sys.executable, str(ROOT / "tools/build-backend-bundle.py"),
                        "--build-dir", str(binary.parent), "--output", str(output),
                        "--mujoco-root", str(mujoco_root)],
                       check=True, capture_output=True, text=True)
        descriptor = json.loads((output / "backend-v2.json").read_text())
        assert descriptor == EXPECTED
        release = json.loads((output / "release.json").read_text())
        assert (release["id"], release["version"], release["schema_version"]) == (
            "island/mujoco-sim", "0.1.1", 4)
        contributions = release["node_contributions"]
        assert contributions["processes"] == [{
            "node_type": "eos.process.mujoco@v0.1",
            "entrypoint": "bin/eos-mujoco-sim",
            "lifecycle_adapter": "mujoco-v2",
            "resources": [{"setting": "scene", "kind": "scene",
                           "descriptor": "package-resources.json"}],
            "host_inputs": [{"name": "MUJOCO_ROOT", "kind": "directory",
                             "library_dir": "lib", "required": True}],
        }]
        assert {node["id"] for node in contributions["node_types"]} == {
            "eos.process.mujoco@v1.0", "eos.process.mujoco@v0.1"}
        assert len(contributions["node_sets"][0]["nodes"]) == 7
        asset = release["assets"][0]
        assert asset["libc"] == f"glibc>={platform.libc_ver()[1]}", asset
        ubuntu = next(line.split("=", 1)[1].strip('"') for line in
                      Path("/etc/os-release").read_text().splitlines()
                      if line.startswith("VERSION_ID="))
        assert asset["tested_ubuntu"] == [ubuntu], asset
        assert "libmujoco.so.3.16.0" in asset["required_libraries"], asset
        archive = output.parent / asset["name"]
        assert archive.stat().st_size == asset["size_bytes"]
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == asset["sha256"]
        with tarfile.open(archive, "r:gz") as tar:
            members = {member.name for member in tar.getmembers()}
            assert {"backend-v2.json", "package-resources.json", "bin/eos-mujoco-sim", "assets/scene.xml",
                    "assets/scenes/navigation/scene.xml"} <= members
            assert "release.json" not in members
            assert all(not member.name.startswith("/") and ".." not in Path(member.name).parts
                       and (member.isfile() or member.isdir()) for member in tar.getmembers())
            resources = json.load(tar.extractfile("package-resources.json"))
            assert resources["schema_version"] == 1
            assert {entry["id"] for entry in resources["resources"]} == {
                "pick-place", "navigation", "cam-0", "base-0", "arm-0"}
            assert {entry["device_kind"] for entry in resources["resources"]
                    if entry["kind"] == "device"} == {"camera", "base", "manipulator"}
            for scene in descriptor["scenes"]:
                scene_file = output / scene["path"]
                references = [element.get("file") for element in ET.parse(scene_file).iter()
                              if element.get("file")]
                assert references, f"{scene['id']} has no referenced assets"
                for reference in references:
                    asset = (scene_file.parent / reference).resolve()
                    assert asset.is_relative_to(output.resolve()), (scene["id"], reference)
                    assert asset.is_file(), (scene["id"], reference)
                    assert asset.relative_to(output).as_posix() in members, (scene["id"], reference)
            relocated = Path(temporary) / "relocated"
            tar.extractall(relocated, filter="data")
        environment = os.environ.copy()
        environment["LD_LIBRARY_PATH"] = str(mujoco_root / "lib") + (
            ":" + environment["LD_LIBRARY_PATH"] if environment.get("LD_LIBRARY_PATH") else ""
        )
        environment["MUJOCO_ROOT"] = str(mujoco_root)
        dynamic = subprocess.run(["readelf", "-d", str(relocated / "bin/eos-mujoco-sim")],
                                 check=True, capture_output=True, text=True).stdout
        assert "RUNPATH" not in dynamic and "RPATH" not in dynamic, dynamic
        subprocess.run([sys.executable, str(ROOT / "tests/strict_socket.py"),
                        str(relocated / "bin/eos-mujoco-sim"),
                        str(relocated / "assets/scene.xml")],
                       check=True, env=environment, timeout=90)
        print("P02 built bundle descriptor, contributions and archive pin: PASS")


if __name__ == "__main__":
    main()
