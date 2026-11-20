#!/usr/bin/env python3
"""Build and relocate the current hardware candidate through the real packager."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from nodes import PACKAGE_VERSION, contributions  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    binary = Path(sys.argv[1]).resolve()
    mujoco_root = Path(sys.argv[2]).resolve()
    with tempfile.TemporaryDirectory(prefix="mujoco-current-bundle-") as temporary:
        output = Path(temporary) / "bundle"
        subprocess.run([sys.executable, str(ROOT / "tools/bundle.py"),
                        "--build-dir", str(binary.parent), "--output", str(output),
                        "--mujoco-root", str(mujoco_root)], check=True)
        release = json.loads((output / "release.json").read_text())
        assert (release["contract"], release["schema_version"], release["id"], release["version"]) == (
            "isos.package@v1", "0.2.2", "island/mujoco-sim", PACKAGE_VERSION)
        expected = contributions()
        expected["libraries"] = [{"path": "lib/libmujoco-eos-node.so",
                                  "sha256": sha256(output / "lib/libmujoco-eos-node.so")}]
        assert release["node_contributions"] == expected
        asset = release["assets"][0]
        archive = output.parent / Path(asset["url"]).name
        assert archive.stat().st_size == asset["size_bytes"]
        assert sha256(archive) == asset["sha256"]
        for field in ("descriptor", "template"):
            assert sha256(output / release["package_config"][field]) == release["package_config"][field + "_sha256"]
        relocated = Path(temporary) / "relocated"
        with tarfile.open(archive, "r:gz") as tar:
            assert "release.json" not in tar.getnames()
            assert all(not member.name.startswith("/") and ".." not in Path(member.name).parts
                       and (member.isfile() or member.isdir()) for member in tar.getmembers())
            tar.extractall(relocated, filter="data")
        for service in expected["runtime_services"]:
            executable = relocated / service["entrypoint"]
            assert executable.is_file() and os.access(executable, os.X_OK)
        descriptor = json.loads((relocated / "config/package-config.json").read_text())
        assert os.access(relocated / descriptor["setup"]["entrypoint"], os.X_OK)
        for helper in ("robocasasource.py", "robocasaassets.py", "robocasa_worker.py"):
            assert (relocated / "bin" / helper).is_file()
        assert (relocated / "robocasa_core/hardware.py").is_file()
        template = tomllib.loads((relocated / "config/package.toml").read_text())
        assert template["package"]["id"] == release["id"]
        resources = json.loads((relocated / "package-resources.json").read_text())
        for resource in resources["resources"]:
            if resource.get("path"):
                scene = relocated / resource["path"]
                assert sha256(scene) == resource["sha256"]
                for element in ET.parse(scene).iter():
                    if reference := element.get("file"):
                        target = (scene.parent / reference).resolve()
                        assert target.is_relative_to(relocated) and target.is_file()
        environment = os.environ | {"LD_LIBRARY_PATH": str(mujoco_root / "lib")}
        for scenario in ("strictsocket.py", "native_camera.py"):
            subprocess.run([sys.executable, str(ROOT / "tests" / scenario),
                            str(relocated / "bin/eos-mujoco-sim"), str(relocated / "assets/scene.xml")],
                           check=True, env=environment, timeout=90)
        # A missing interpreter must fail before importing any host Python modules.
        result = subprocess.run([str(relocated / "bin/robocasa-worker"), "--socket", str(relocated / "worker.sock")],
                                env=environment | {"ISOS_PACKAGE_PYTHON": "/missing/package-python"},
                                capture_output=True, text=True)
        assert result.returncode != 0 and "not executable" in result.stderr
        print("current schema 0.2.2 archive, resources, config, helpers and relocated service: PASS")


if __name__ == "__main__":
    main()
