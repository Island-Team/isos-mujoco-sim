#!/usr/bin/env python3
"""Build a real candidate and check its descriptor, sidecar and archive pin."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "tests/fixtures/scene_catalog/target-descriptor.json").read_text())


def main() -> None:
    binary = Path(sys.argv[1]).resolve()
    if binary.name != "eos-mujoco-sim" or not binary.is_file():
        raise SystemExit("expected built eos-mujoco-sim executable")
    with tempfile.TemporaryDirectory(prefix="mujoco-p02-bundle-") as temporary:
        output = Path(temporary) / "bundle"
        subprocess.run([sys.executable, str(ROOT / "tools/build-backend-bundle.py"),
                        "--build-dir", str(binary.parent), "--output", str(output)],
                       check=True, capture_output=True, text=True)
        descriptor = json.loads((output / "backend-v2.json").read_text())
        assert descriptor == EXPECTED
        release = json.loads((output / "release.json").read_text())
        assert (release["id"], release["version"], release["schema_version"]) == (
            "island/mujoco-sim", "0.1.1", 4)
        contributions = release["node_contributions"]
        assert {node["id"] for node in contributions["node_types"]} == {
            "eos.process.mujoco@v1.0", "eos.process.mujoco@v0.1"}
        assert len(contributions["node_sets"][0]["nodes"]) == 7
        asset = release["assets"][0]
        archive = output.parent / asset["name"]
        assert archive.stat().st_size == asset["size_bytes"]
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == asset["sha256"]
        with tarfile.open(archive, "r:gz") as tar:
            members = {member.name for member in tar.getmembers()}
            assert {"backend-v2.json", "bin/eos-mujoco-sim", "assets/scene.xml",
                    "assets/scenes/navigation/scene.xml"} <= members
            assert "release.json" not in members
            assert all(not member.name.startswith("/") and ".." not in Path(member.name).parts
                       and (member.isfile() or member.isdir()) for member in tar.getmembers())
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
        print("P02 built bundle descriptor, contributions and archive pin: PASS")


if __name__ == "__main__":
    main()
