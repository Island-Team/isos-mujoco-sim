#!/usr/bin/env python3
"""Locate or download the pinned upstream RoboCasa source checkout."""

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / ".local/robocasa"
URL = "https://github.com/robocasa/robocasa.git"
REVISION = "3443cdf3dd20f9ae8ed41adba442059b506891d0"


def checkout(path: Path) -> bool:
  return (path / "robocasa/environments/kitchen/atomic/kitchen_pick_place.py").is_file()


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("action", choices=("check", "download"))
  parser.add_argument("--path", type=Path, default=DEFAULT)
  args = parser.parse_args()
  path = args.path.expanduser().resolve()
  if checkout(path):
    print(path)
    return
  if args.action == "check":
    parser.error(f"RoboCasa source is missing: {path}")
  if path.exists():
    parser.error(f"download target exists but is not a RoboCasa checkout: {path}")
  path.parent.mkdir(parents=True, exist_ok=True)
  subprocess.run(["git", "clone", "--filter=blob:none", "--depth", "1", URL, str(path)], check=True)
  subprocess.run(["git", "-C", str(path), "fetch", "--depth", "1", "origin", REVISION], check=True)
  subprocess.run(["git", "-C", str(path), "checkout", "--detach", REVISION], check=True)
  if not checkout(path):
    parser.error(f"download did not provide the expected RoboCasa files: {path}")
  print(path)


if __name__ == "__main__":
  main()
