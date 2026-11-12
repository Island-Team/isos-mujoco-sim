#!/usr/bin/env python3
"""Stage a versioned island/mujoco-sim IsOS backend bundle."""

import argparse
import gzip
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

from nodes import contributions
from catalog import descriptor_for_bundle


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "island/mujoco-sim"
PACKAGE_VERSION = "0.2.0"
SOURCE = "https://github.com/Island-Team/isos-mujoco-sim"
MUJOCO_SONAME = "libmujoco.so.3.3.1"


def write_deterministic_archive(bundle: Path, archive: Path) -> None:
    """Encode a fixed payload tree without host ownership or timestamp metadata."""
    with archive.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                for file in sorted(bundle.rglob("*")):
                    member = tar.gettarinfo(str(file), arcname=file.relative_to(bundle).as_posix())
                    member.uid = member.gid = member.mtime = 0
                    member.uname = member.gname = ""
                    if member.isfile():
                        with file.open("rb") as source:
                            tar.addfile(member, source)
                    else:
                        tar.addfile(member)


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
        raise ValueError("resolved MuJoCo SONAME does not match 3.3.1")
    actual = next(path for name, path in resolved if name == MUJOCO_SONAME)
    if Path(actual).resolve() != library.resolve():
        raise ValueError("MuJoCo SONAME resolved outside MUJOCO_ROOT")
    if any(not path.startswith("/") for _, path in resolved):
        raise ValueError("installed binary has an unlocated library")
    return sorted(names)


def inspect_installed_plugin(plugin: Path) -> list[str]:
    dynamic = subprocess.run(["readelf", "-d", str(plugin)], check=True,
                             capture_output=True, text=True).stdout
    paths = re.findall(r"\((?:RUNPATH|RPATH)\).*?\[(.*?)\]", dynamic)
    if any(part.startswith("/") for path in paths for part in path.split(":")):
        raise ValueError("installed adapter contains an absolute RUNPATH/RPATH")
    if "libmujoco.so" in dynamic:
        raise ValueError("adapter must communicate through the supervised simulator socket")
    result = subprocess.run(["ldd", str(plugin)], check=True,
                            capture_output=True, text=True)
    if "not found" in result.stdout or "not found" in result.stderr:
        raise ValueError("installed adapter has unresolved libraries")
    names = re.findall(r"^\s*(\S+\.so(?:\.\S+)?)\s+=>\s+\S+",
                       result.stdout, re.MULTILINE)
    return sorted(set(names))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=False, default=PACKAGE_VERSION,
                        help="unpublished v0.2.x package version")
    parser.add_argument("--mujoco-root", type=Path,
                        default=Path(os.environ["MUJOCO_ROOT"]) if os.environ.get("MUJOCO_ROOT") else None,
                        help="installed MuJoCo 3.3.1 root; defaults to MUJOCO_ROOT")
    args = parser.parse_args()
    if not re.fullmatch(r"0\.2\.[0-9]+", args.version):
        parser.error("version must be 0.2.x")
    binary = args.build_dir / "eos-mujoco-sim"
    plugin = args.build_dir / "libmujoco-eos-node.so"
    if not plugin.is_file():
        parser.error(f"build the adapter first: {plugin}")
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
    (bundle / "lib").mkdir(exist_ok=True)
    (bundle / "config").mkdir(exist_ok=True)
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
        installed_plugin = Path(temporary) / "lib/libmujoco-eos-node.so"
        if not installed_plugin.is_file():
            parser.error("CMake installation did not produce lib/libmujoco-eos-node.so")
        try:
            plugin_libraries = inspect_installed_plugin(installed_plugin)
        except ValueError as error:
            parser.error(str(error))
        libraries = sorted(set(libraries + plugin_libraries))
        shutil.copy2(installed_plugin, bundle / "lib/libmujoco-eos-node.so")
    shutil.copytree(ROOT / "assets", bundle / "assets", dirs_exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", bundle / "LICENSE")
    if args.version != "0.2.0":
        shutil.copytree(
            ROOT / "robocasa_core", bundle / "robocasa_core",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copy2(ROOT / "tools/robocasa_worker.py", bundle / "bin/robocasa_worker.py")
        wrapper = bundle / "bin/robocasa-worker"
        wrapper.write_text(
            "#!/bin/sh\nset -eu\n"
            ': "${ISOS_PACKAGE_PYTHON:?configured Python interpreter is required}"\n'
            'root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)\n'
            'PYTHONPATH="$root${PYTHONPATH:+:$PYTHONPATH}" '
            'PYTHONDONTWRITEBYTECODE=1 '
            'exec "$ISOS_PACKAGE_PYTHON" -B "$root/bin/robocasa_worker.py" "$@"\n'
        )
        wrapper.chmod(0o755)
        shutil.copy2(ROOT / "config/package-config.json", bundle / "config/package-config.json")
        shutil.copy2(ROOT / "config/package.toml", bundle / "config/package.toml")
    descriptor = descriptor_for_bundle(bundle, include_gripper=args.version != "0.2.0")
    (bundle / "backend-v2.json").write_text(json.dumps(descriptor, indent=2) + "\n")
    resources = {
        "contract": "isos.package-resources@v1",
        "schema_version": "0.1.0",
        "resources": [{key: scene[key] for key in
                       ("id", "label", "description", "path", "sha256")}
                      | {"kind": "scene"} for scene in descriptor["scenes"]]
                     + [{key: device[key] for key in
                         ("id", "label", "description")}
                        | {"kind": "device", "metadata": {
                            "device_kind": device["kind"],
                            "scene_ids": device["scene_ids"],
                        }}
                        for device in descriptor["device_catalog"]],
    }
    (bundle / "package-resources.json").write_text(json.dumps(resources, indent=2) + "\n")
    plugin_digest = hashlib.sha256((bundle / "lib/libmujoco-eos-node.so").read_bytes()).hexdigest()
    node_contributions = contributions(args.version)
    node_contributions["libraries"] = [{"path": "lib/libmujoco-eos-node.so",
                                          "sha256": plugin_digest}]
    arch = platform.machine()
    asset_name = f"mujoco-sim-v{args.version}-linux-{arch}.tar.gz"
    archive = bundle.parent / asset_name
    write_deterministic_archive(bundle, archive)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    release = {
        "contract": "isos.package@v1",
        "schema_version": "0.2.0" if args.version == "0.2.0" else "0.2.1",
        "id": PACKAGE_ID,
        "kind": "backend",
        "version": args.version,
        "description": "MuJoCo robot hardware: native and isolated RoboCasa services",
        "source_commit": source_commit,
        "source_url": SOURCE,
        "release_url": f"{SOURCE}/releases/tag/v{args.version}",
        "license": "Apache-2.0",
        "contracts": ["mujoco-v2"],
        "compatibility": {
            "isos_min_inclusive": "0.2.3",
            "isos_max_exclusive": "0.3.0",
            "required_owner_capabilities": [
                {"owner": "isos", "capability": "package-process-v1" if args.version == "0.2.0" else "package-service-v1"},
                {"owner": "eos", "capability": "native-plugin-v1" if args.version == "0.2.0" else "native-plugin-v2"},
            ],
        },
        "node_contributions": node_contributions,
        "adapters": [{"family": "mujoco-v2", "library": "lib/libmujoco-eos-node.so",
                      "sha256": plugin_digest}],
        "assets": [{
            "name": asset_name,
            "url": f"{SOURCE}/releases/download/v{args.version}/{asset_name}",
            "sha256": digest,
            "size_bytes": archive.stat().st_size,
            "os": "linux",
            "arch": arch,
            "libc": f"glibc>={libc_version}",
            "required_libraries": libraries,
            "tested_ubuntu": [ubuntu_version],
        }],
    }
    if args.version != "0.2.0":
        descriptor_path = bundle / "config/package-config.json"
        template_path = bundle / "config/package.toml"
        release["package_config"] = {
            "descriptor": "config/package-config.json",
            "descriptor_sha256": hashlib.sha256(descriptor_path.read_bytes()).hexdigest(),
            "template": "config/package.toml",
            "template_sha256": hashlib.sha256(template_path.read_bytes()).hexdigest(),
        }
    (bundle / "release.json").write_text(json.dumps(release, indent=2) + "\n")
    print(f"Bundle {bundle}\nArchive {archive}\nSHA-256 {digest}")


if __name__ == "__main__":
    main()
