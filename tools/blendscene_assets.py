#!/usr/bin/env python3
"""Pack or fetch the generated meshes of a distributed blendscene (RoboCasa-style).

Heavy generated assets under assets/<scene> (meshes/ and collision/ — binary
MSH + MTL sidecars + textures) are not tracked in git. Instead each scene ships
one zip attached to a GitHub release:

  python tools/blendscene_assets.py pack                # build dist/<zip>
  python tools/blendscene_assets.py check               # are assets present?
  python tools/blendscene_assets.py download           # fetch + extract

After re-exporting a scene from its .blend, bump its version in SCENES below,
run pack, upload dist/<zip> to the release tag, and paste the printed sha256.
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
PACKED_DIRS = ("meshes", "collision")

# Per-scene release pins. The car_scene v1 zip is live at DEFAULT_URL — its
# tag, archive name, url, and sha256 must not change; re-exports bump to v2.
SCENES = {
    "car_scene": {
        "version": "v1",
        "release_tag": "car-scene-assets-v1",
        "archive": "car_scene_assets_v1.zip",
        "url": ("https://github.com/George-Lin-encx/isos-mujoco-sim/releases/download/"
                "car-scene-assets-v1/car_scene_assets_v1.zip"),
        "sha256": "48f71e9c1d22cb5542fed43c878f9a0432deda3c460afb705acffbf1f782ac36",
        "blend": "0001.blend",
    },
}


def assets_ready(scene: Path) -> bool:
  return (any((scene / "meshes").glob("*.msh"))
          and any((scene / "collision").glob("*.msh")))


def build_archive(scene: Path, pin: dict, output: Path, include_blend: bool) -> None:
  if not assets_ready(scene):
    sys.exit("scene assets not found under %s" % scene)
  members = []
  for name in PACKED_DIRS:
    members += sorted(p for p in (scene / name).iterdir() if p.is_file())
  blend = ROOT / pin["blend"]
  if include_blend:
    if not blend.is_file():
      sys.exit("blend source not found: %s" % blend)
    members.append(blend)
  output.parent.mkdir(parents=True, exist_ok=True)
  with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for path in members:
      arcname = str(path.relative_to(scene)) if path.parent != ROOT else path.name
      zf.write(path, arcname)
  sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
  print("wrote %s (%.1f MB)" % (output, output.stat().st_size / 1e6))
  print("sha256: %s" % sha256)
  print("upload it to release %s and update the pin in SCENES" % pin["release_tag"])


def extract_archive(archive: Path, scene: Path) -> None:
  scene.mkdir(parents=True, exist_ok=True)
  scene_resolved = scene.resolve()
  with zipfile.ZipFile(archive) as zf:
    for member in zf.infolist():
      target = (scene / member.filename).resolve()
      if scene_resolved not in target.parents and target != scene_resolved:
        sys.exit("archive member escapes the scene directory: %s" % member.filename)
    zf.extractall(scene)


def fetch(url: str, archive_name: str, sha256: str, scene: Path) -> None:
  print("downloading %s" % url)
  with tempfile.TemporaryDirectory() as tmp:
    archive = Path(tmp) / archive_name
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
  parser.add_argument("--scene", default="car_scene", choices=sorted(SCENES),
                      help="which distributed scene (default: car_scene)")
  parser.add_argument("--url", default=os.environ.get("CAR_SCENE_ASSETS_URL"))
  parser.add_argument("--sha256", default=os.environ.get("CAR_SCENE_ASSETS_SHA256"))
  parser.add_argument("--output", type=Path, default=None)
  parser.add_argument("--include-blend", action="store_true",
                      help="also pack the scene's .blend source (author backup)")
  args = parser.parse_args()
  pin = SCENES[args.scene]
  scene = ROOT / "assets" / args.scene
  url = args.url or pin["url"]
  sha256 = args.sha256 if args.sha256 is not None else pin["sha256"]
  output = args.output or ROOT / "dist" / pin["archive"]
  if args.action == "pack":
    build_archive(scene, pin, output, args.include_blend)
  elif assets_ready(scene):
    print(scene)
  elif args.action == "check":
    sys.exit("scene assets missing under %s: run "
             "'python tools/blendscene_assets.py download'" % scene)
  else:
    fetch(url, pin["archive"], sha256, scene)
    if not assets_ready(scene):
      sys.exit("download finished but the expected meshes are still missing")
    print(scene)


if __name__ == "__main__":
  main()
