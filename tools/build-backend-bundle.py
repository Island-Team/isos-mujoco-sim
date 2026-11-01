#!/usr/bin/env python3
"""Stage the local island/mujoco-sim@0.1.1 IsOS backend bundle."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

from node_contributions import contributions
from scene_catalog import descriptor_for_bundle


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "island/mujoco-sim"
PACKAGE_VERSION = "0.1.1"
SOURCE = "https://github.com/Island-Team/isos-mujoco-sim"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binary = args.build_dir / "eos-mujoco-sim"
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"build the simulator first: {binary}")
    bundle = args.output.resolve()
    if bundle.exists() and any(bundle.iterdir()):
        parser.error(f"output bundle must be empty: {bundle}")
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "bin").mkdir(exist_ok=True)
    shutil.copy2(binary, bundle / "bin/eos-mujoco-sim")
    shutil.copytree(ROOT / "assets", bundle / "assets", dirs_exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", bundle / "LICENSE")
    descriptor = descriptor_for_bundle(bundle)
    (bundle / "backend-v2.json").write_text(json.dumps(descriptor, indent=2) + "\n")
    arch = platform.machine()
    asset_name = f"mujoco-sim-v{PACKAGE_VERSION}-linux-{arch}.tar.gz"
    archive = bundle.parent / asset_name
    with tarfile.open(archive, "w:gz") as tar:
        for file in sorted(bundle.rglob("*")):
            tar.add(file, arcname=file.relative_to(bundle).as_posix(), recursive=False)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    release = {
        "schema_version": 4,
        "id": PACKAGE_ID,
        "kind": "backend",
        "version": PACKAGE_VERSION,
        "description": "MuJoCo v2 simulator backend and EOS hardware nodes",
        "source_commit": source_commit,
        "source_url": SOURCE,
        "release_url": f"{SOURCE}/releases/tag/v{PACKAGE_VERSION}",
        "license": "Apache-2.0",
        "contracts": ["mujoco-v2"],
        "node_contributions": contributions(),
        "assets": [{
            "name": asset_name,
            "url": f"{SOURCE}/releases/download/v{PACKAGE_VERSION}/{asset_name}",
            "sha256": digest,
            "size_bytes": archive.stat().st_size,
            "os": "linux",
            "arch": arch,
            "required_libraries": [],
            "tested_ubuntu": [],
        }],
    }
    (bundle / "release.json").write_text(json.dumps(release, indent=2) + "\n")
    print(f"Bundle {bundle}\nArchive {archive}\nSHA-256 {digest}")


if __name__ == "__main__":
    main()
