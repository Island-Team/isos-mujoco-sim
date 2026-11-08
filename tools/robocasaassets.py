#!/usr/bin/env python3
"""Fetch the first task's official RoboCasa asset archives from Hugging Face."""

import argparse
import hashlib
import subprocess
from pathlib import Path
from zipfile import BadZipFile, ZipFile

ARCHIVES = (
  ("textures.zip", "robocasa/robocasa-assets", "1b92c3d02ca4354984fec961357db0bff7b32166", None),
  ("fixtures.zip", "robocasa/robocasa-assets", "1b92c3d02ca4354984fec961357db0bff7b32166", None),
  ("fixtures_lightwheel.zip", "IIFAN/robocasa365-lightwheel-fixtures",
   "0cf51d45ab07fce13c4733ee1fe20bb01399768c",
   "62c1c87776edda9b7c42dda7b00781a1e5a7f90acc3e49d06c39c9545cbd6c3e"),
  ("objects_lightwheel.zip", "IIFAN/robocasa365-lightwheel-objects",
   "3f7f7aee8ef4367dfdc85a86778467cf8527f8fb",
   "a1db739b0e80fc4d56d4be27d89dba3aa60000e9648c5607874700e0f14b7955"),
)
FULL_ARCHIVES = (
  ("objaverse.zip", "robocasa/robocasa-assets", "1b92c3d02ca4354984fec961357db0bff7b32166",
   "66a7eebef3bac855301964d35d905fc2cb44d691f007f97af08d96e83db5cc08"),
  ("aigen_objs.zip", "robocasa/robocasa-assets", "1b92c3d02ca4354984fec961357db0bff7b32166",
   "1f88792322ccce79f775e88482626c324c6e07d002adf23320a124b72764dd19"),
)


def valid_zip(path: Path) -> bool:
  if not path.is_file():
    return False
  try:
    with ZipFile(path) as archive:
      return archive.testzip() is None
  except BadZipFile:
    return False


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("source", type=Path)
  parser.add_argument("--full", action="store_true", help="also fetch object collections for other tasks")
  args = parser.parse_args()
  source = args.source.resolve()
  assets = source / "robocasa/models/assets"
  if not assets.is_dir():
    parser.error(f"RoboCasa asset directory is missing: {assets}")
  downloads = source / ".asset-downloads"
  downloads.mkdir(exist_ok=True)
  base_ready = (source / ".assets-ready").is_file()
  archives = (() if base_ready else ARCHIVES) + (FULL_ARCHIVES if args.full else ())
  for filename, repo, revision, digest in archives:
    archive = downloads / filename
    if not valid_zip(archive):
      url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{filename}"
      subprocess.run(["wget", "-q", "-c", url, "-O", str(archive)], check=True)
    if not valid_zip(archive):
      raise ValueError(f"incomplete asset archive: {filename}")
    if digest:
      with archive.open("rb") as source_file:
        if hashlib.file_digest(source_file, "sha256").hexdigest() != digest:
          raise ValueError(f"asset digest mismatch: {filename}")
    target = assets / "objects" if filename in {
      "objects_lightwheel.zip", "objaverse.zip", "aigen_objs.zip"} else assets
    target.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as contents:
      for item in contents.infolist():
        resolved = (target / item.filename).resolve()
        if not resolved.is_relative_to(target) or item.filename.startswith("/"):
          raise ValueError(f"unsafe archive member: {item.filename}")
      contents.extractall(target)
    print(f"Extracted {filename} into {target}")
  (source / ".assets-ready").write_text("RoboCasa assets from pinned Hugging Face datasets\n")
  if args.full:
    (source / ".assets-full-ready").write_text("RoboCasa full object assets from pinned Hugging Face dataset\n")


if __name__ == "__main__":
  main()
