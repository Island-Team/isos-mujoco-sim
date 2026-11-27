#!/usr/bin/env python3
"""Pack or fetch the generated car-scene meshes (RoboCasa-style asset bundle).

The heavy assets under assets/car_scene (meshes/ and collision/, ~38 MB of
MuJoCo binary MSH + MTL sidecars + textures) are not tracked in git. Instead
they ship as one zip attached to a GitHub release:

  python tools/carscene_assets.py pack                # build dist/<zip>
  python tools/carscene_assets.py check               # are assets present?
  python tools/carscene_assets.py download           # fetch + extract

After re-exporting the scene from 0001.blend, bump ASSET_VERSION, run pack,
upload dist/<zip> to the release tag below, and paste the printed sha256.
"""
import argparse
import hashlib
import os
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "assets" / "car_scene"
PACKED_DIRS = ("meshes", "collision")

ASSET_VERSION = "v1"
RELEASE_TAG = "car-scene-assets-" + ASSET_VERSION
ARCHIVE_NAME = "car_scene_assets_" + ASSET_VERSION + ".zip"
DEFAULT_URL = ("https://github.com/George-Lin-encx/isos-mujoco-sim/releases/download/"
               + RELEASE_TAG + "/" + ARCHIVE_NAME)
DEFAULT_SHA256 = "48f71e9c1d22cb5542fed43c878f9a0432deda3c460afb705acffbf1f782ac36"
BLEND_SOURCE = ROOT / "0001.blend"


def assets_ready(scene: Path) -> bool:
  return (any((scene / "meshes").glob("*.msh"))
          and any((scene / "collision").glob("*.msh")))


def build_archive(output: Path, include_blend: bool) -> None:
  if not assets_ready(SCENE):
    sys.exit("car-scene assets not found under %s" % SCENE)
  members = []
  for name in PACKED_DIRS:
    members += sorted(p for p in (SCENE / name).iterdir() if p.is_file())
  if include_blend:
    if not BLEND_SOURCE.is_file():
      sys.exit("blend source not found: %s" % BLEND_SOURCE)
    members.append(BLEND_SOURCE)
  output.parent.mkdir(parents=True, exist_ok=True)
  with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for path in members:
      arcname = str(path.relative_to(SCENE)) if path.parent != ROOT else path.name
      zf.write(path, arcname)
  sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
  print("wrote %s (%.1f MB)" % (output, output.stat().st_size / 1e6))
  print("sha256: %s" % sha256)
  print("upload it to release %s and set DEFAULT_SHA256 to the sha above" % RELEASE_TAG)


def extract_archive(archive: Path, scene: Path) -> None:
  scene.mkdir(parents=True, exist_ok=True)
  scene_resolved = scene.resolve()
  with zipfile.ZipFile(archive) as zf:
    for member in zf.infolist():
      target = (scene / member.filename).resolve()
      if scene_resolved not in target.parents and target != scene_resolved:
        sys.exit("archive member escapes the scene directory: %s" % member.filename)
    zf.extractall(scene)


def fetch(url: str, sha256: str, scene: Path) -> None:
  print("downloading %s" % url)
  with tempfile.TemporaryDirectory() as tmp:
    archive = Path(tmp) / ARCHIVE_NAME
    with urllib.request.urlopen(url) as response, open(archive, "wb") as out:
      total = int(response.headers.get("Content-Length") or 0)
      done = 0
      while True:
        chunk = response.read(1 << 20)
        if not chunk:
          break
        out.write(chunk)
        done += len(chunk)
        if total:
          print("\r  %d/%d KB" % (done // 1024, total // 1024), end="", flush=True)
      print()
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if sha256 and digest != sha256:
      sys.exit("sha256 mismatch: got %s, expected %s" % (digest, sha256))
    if not sha256:
      print("warning: sha256 not pinned, skipping integrity check (got %s)" % digest)
    extract_archive(archive, scene)


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument("action", choices=("pack", "check", "download"))
  parser.add_argument("--url", default=os.environ.get("CAR_SCENE_ASSETS_URL", DEFAULT_URL))
  parser.add_argument("--sha256", default=os.environ.get("CAR_SCENE_ASSETS_SHA256", DEFAULT_SHA256))
  parser.add_argument("--output", type=Path, default=ROOT / "dist" / ARCHIVE_NAME)
  parser.add_argument("--include-blend", action="store_true",
                      help="also pack the 0001.blend source (author backup)")
  args = parser.parse_args()
  if args.action == "pack":
    build_archive(args.output, args.include_blend)
  elif assets_ready(SCENE):
    print(SCENE)
  elif args.action == "check":
    sys.exit("car-scene assets missing under %s: run "
             "'python tools/carscene_assets.py download'" % SCENE)
  else:
    fetch(args.url, args.sha256, SCENE)
    if not assets_ready(SCENE):
      sys.exit("download finished but the expected meshes are still missing")
    print(SCENE)


if __name__ == "__main__":
  main()
