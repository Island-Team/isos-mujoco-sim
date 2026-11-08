#!/usr/bin/env python3
"""List native scenes from the package-owned scene catalog."""

from catalog import SCENES


def main() -> None:
  print("Native compatibility scenes:")
  for scene in SCENES:
    print(f"  {scene['id']:12} {scene['label']:16} {scene['path']}")
  print("Use ./launch.sh --scene NAME or set SIM_SCENE and run ./launch.sh --native")


if __name__ == "__main__":
  main()
