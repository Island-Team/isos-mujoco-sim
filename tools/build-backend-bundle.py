#!/usr/bin/env python3
"""Stage the local island/mujoco-sim@0.1.1 IsOS backend bundle."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile

from node_contributions import contributions
from scene_catalog import descriptor_for_bundle


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "island/mujoco-sim"
PACKAGE_VERSION = "0.1.1"
SOURCE = "https://github.com/Island-Team/isos-mujoco-sim"
MUJOCO_SONAME = "libmujoco.so.3.16.0"


def host_requirements() -> tuple[str, str]:
    values = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip('"')
    if values.get("ID") != "ubuntu" or not re.fullmatch(r"\d+\.\d+", values.get("VERSION_ID", "")):
        raise ValueError("native release requires a measured Ubuntu build host")
    libc_name, libc_version = platform.libc_ver()
    if libc_name != "glibc" or not re.fullmatch(r"\d+\.\d+", libc_version):
        raise ValueError("native release requires a measured glibc version")
    return libc_version, values["VERSION_ID"]


def inspect_installed_binary(binary: Path, mujoco_root: Path) -> list[str]:
    dynamic = subprocess.run(["readelf", "-d", str(binary)], check=True,
                             capture_output=True, text=True).stdout
    paths = re.findall(r"\((?:RUNPATH|RPATH)\).*?\[(.*?)\]", dynamic)
    if any(part.startswith("/") for path in paths for part in path.split(":")):
        raise ValueError("installed binary contains an absolute RUNPATH/RPATH")
    direct = re.findall(r"\(NEEDED\).*?\[(.*?)\]", dynamic)
    mujoco_direct = [name for name in direct if name.startswith("libmujoco.so")]
    if mujoco_direct != [MUJOCO_SONAME]:
        raise ValueError(f"installed binary needs exactly {MUJOCO_SONAME}: {mujoco_direct}")
    library = mujoco_root / "lib" / MUJOCO_SONAME
    if not library.is_file():
        raise ValueError(f"required MuJoCo library is missing: {library}")
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(library.parent) + (
        ":" + environment["LD_LIBRARY_PATH"] if environment.get("LD_LIBRARY_PATH") else ""
    )
    result = subprocess.run(["ldd", str(binary)], check=True, capture_output=True,
                            text=True, env=environment)
    if "not found" in result.stdout or "not found" in result.stderr:
        raise ValueError(f"installed binary has unresolved libraries:\n{result.stdout}{result.stderr}")
    resolved = re.findall(r"^\s*(\S+\.so(?:\.\S+)?)\s+=>\s+(\S+)",
                          result.stdout, re.MULTILINE)
    names = {name for name, _ in resolved}
    if MUJOCO_SONAME not in names or any(name.startswith("libmujoco.so") and name != MUJOCO_SONAME for name in names):
        raise ValueError("resolved MuJoCo SONAME does not match 3.16.0")
    actual = next(path for name, path in resolved if name == MUJOCO_SONAME)
    if Path(actual).resolve() != library.resolve():
        raise ValueError("MuJoCo SONAME resolved outside MUJOCO_ROOT")
    if any(not path.startswith("/") for _, path in resolved):
        raise ValueError("installed binary has an unlocated library")
    return sorted(names)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mujoco-root", type=Path,
                        default=Path(os.environ["MUJOCO_ROOT"]) if os.environ.get("MUJOCO_ROOT") else None,
                        help="installed MuJoCo 3.16.0 root; defaults to MUJOCO_ROOT")
    args = parser.parse_args()
    binary = args.build_dir / "eos-mujoco-sim"
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"build the simulator first: {binary}")
    if args.mujoco_root is None:
        parser.error("--mujoco-root or MUJOCO_ROOT is required")
    mujoco_root = args.mujoco_root.resolve()
    try:
        libc_version, ubuntu_version = host_requirements()
    except ValueError as error:
        parser.error(str(error))
    bundle = args.output.resolve()
    if bundle.exists() and any(bundle.iterdir()):
        parser.error(f"output bundle must be empty: {bundle}")
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "bin").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mujoco-installed-") as temporary:
        subprocess.run(["cmake", "--install", str(args.build_dir.resolve()),
                        "--prefix", temporary], check=True)
        installed = Path(temporary) / "bin/eos-mujoco-sim"
        if not installed.is_file() or not os.access(installed, os.X_OK):
            parser.error("CMake installation did not produce bin/eos-mujoco-sim")
        try:
            libraries = inspect_installed_binary(installed, mujoco_root)
        except ValueError as error:
            parser.error(str(error))
        shutil.copy2(installed, bundle / "bin/eos-mujoco-sim")
    shutil.copytree(ROOT / "assets", bundle / "assets", dirs_exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", bundle / "LICENSE")
    descriptor = descriptor_for_bundle(bundle)
    (bundle / "backend-v2.json").write_text(json.dumps(descriptor, indent=2) + "\n")
    resources = {
        "schema_version": 1,
        "resources": [{key: scene[key] for key in
                       ("id", "label", "description", "path", "sha256")}
                      | {"kind": "scene"} for scene in descriptor["scenes"]]
                     + [{key: device[key] for key in
                         ("id", "label", "description", "scene_ids")}
                        | {"kind": "device", "device_kind": device["kind"]}
                        for device in descriptor["device_catalog"]],
    }
    (bundle / "package-resources.json").write_text(json.dumps(resources, indent=2) + "\n")
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
            "libc": f"glibc>={libc_version}",
            "required_libraries": libraries,
            "tested_ubuntu": [ubuntu_version],
        }],
    }
    (bundle / "release.json").write_text(json.dumps(release, indent=2) + "\n")
    print(f"Bundle {bundle}\nArchive {archive}\nSHA-256 {digest}")


if __name__ == "__main__":
    main()
