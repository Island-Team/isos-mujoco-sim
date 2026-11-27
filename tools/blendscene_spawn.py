#!/usr/bin/env python3
"""Find an open spawn point for the car in a built blendscene: downward ray
hits a low floor, 16 horizontal rays all travel > clearance before hitting
anything. The navigation goal is the open spot farthest from the spawn.

Usage: python tools/blendscene_spawn.py <scene_dir> [options]

Sampling window and preference center default to the manifest world bbox
(inset by --spawn-inset). To reproduce the original car_scene values exactly:
  --window 0,2,50,52 --center 25,27 --seed 7 --floor-z 0

Refuses to overwrite an existing spawn.json unless --force: tests/engine_car.cpp
asserts the spawn pose baked into the tracked scene, so respawning is deliberate.
"""
import argparse
import json
import sys
from pathlib import Path

import mujoco
import numpy as np


def _floats(text):
    return [float(v) for v in text.split(",")]


def find_spawn(scene: Path, force=False, window=None, center=None, inset=2.0,
               seed=7, trials=6000, clearance=1.2, floor_z=0.0, quiet=False):
    """Raycast <scene>/scene.xml and write <scene>/spawn.json. Returns it."""
    spawn_file = scene / "spawn.json"
    if spawn_file.exists() and not force:
        if not quiet:
            print(f"{spawn_file} exists; pass --force to recompute "
                  "(this invalidates the spawn pose asserted in tests/engine_car.cpp)")
        return spawn_file
    manifest = json.loads((scene / "manifest.json").read_text(encoding="utf-8"))
    bmin, bmax = manifest["world_bbox_min"], manifest["world_bbox_max"]
    if window is None:
        window = [bmin[0] + inset, bmin[1] + inset, bmax[0] - inset, bmax[1] - inset]
    if center is None:
        center = [(bmin[0] + bmax[0]) / 2, (bmin[1] + bmax[1]) / 2]
    xmin, ymin, xmax, ymax = window
    cx, cy = center

    model = mujoco.MjModel.from_xml_path(str(scene / "scene.xml"))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    car_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "car")
    geomgroup = np.ones(6, dtype=np.uint8)

    def ray(pos, vec):
        geomid = np.zeros(1, dtype=np.int32)
        # bodyexclude = car so the car itself never blocks spawn probing
        return mujoco.mj_ray(model, data, np.asarray(pos), np.asarray(vec), geomgroup, 1, car_id, geomid)

    best = []
    rng = np.random.default_rng(seed)
    probe_z = floor_z + 0.5
    for _ in range(trials):
        x = rng.uniform(xmin, xmax)
        y = rng.uniform(ymin, ymax)
        # floor below: downward ray from knee height hits floor within 0.6m
        d = ray([x, y, probe_z], [0, 0, -1])
        if d < 0 or d > 0.6:
            continue
        # horizontal clearance at wheel height
        ok = True
        for ang in np.linspace(0, 2 * np.pi, 16, endpoint=False):
            v = [np.cos(ang), np.sin(ang), 0]
            dist = ray([x, y, floor_z + 0.3], v)
            if 0 < dist < clearance:
                ok = False
                break
        if ok:
            best.append((x, y, probe_z - d, (x - cx) ** 2 + (y - cy) ** 2))

    best.sort(key=lambda t: t[3])
    print(f"open spots found: {len(best)}")
    for b in best[:10]:
        print(f"  x={b[0]:.2f} y={b[1]:.2f} floor_z={b[2]:.2f}")
    if not best:
        sys.exit(f"no open spawn found in window {window}; widen it or lower --clearance")
    spawn = best[0]
    # navigation goal: the open spot farthest from spawn (straight-line; the car
    # still has to find a drivable route through the building).
    goal = max(best, key=lambda t: (t[0] - spawn[0]) ** 2 + (t[1] - spawn[1]) ** 2)
    out = {"pos": [round(spawn[0], 3), round(spawn[1], 3), round(spawn[2], 3)],
           "goal": [round(goal[0], 3), round(goal[1], 3)]}
    spawn_file.write_text(json.dumps(out))
    print("wrote spawn.json:", out, "goal distance:",
          round(((goal[0] - spawn[0]) ** 2 + (goal[1] - spawn[1]) ** 2) ** 0.5, 1), "m")
    return spawn_file


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scene_dir", type=Path)
    parser.add_argument("--force", action="store_true", help="overwrite an existing spawn.json")
    parser.add_argument("--window", type=_floats, metavar="XMIN,YMIN,XMAX,YMAX",
                        help="sampling window (default: manifest bbox inset by --spawn-inset)")
    parser.add_argument("--center", type=_floats, metavar="X,Y",
                        help="preference center (default: manifest bbox center)")
    parser.add_argument("--spawn-inset", type=float, default=2.0,
                        help="bbox inset for the default window (meters)")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--trials", type=int, default=6000)
    parser.add_argument("--clearance", type=float, default=1.2)
    parser.add_argument("--floor-z", type=float, default=0.0,
                        help="assumed walkable floor height (probes run just above it)")
    args = parser.parse_args(argv)
    scene = args.scene_dir.resolve()
    if not (scene / "manifest.json").is_file():
        sys.exit(f"no manifest.json in {scene}; run the export step first")
    find_spawn(scene, force=args.force, window=args.window, center=args.center,
               inset=args.spawn_inset, seed=args.seed, trials=args.trials,
               clearance=args.clearance, floor_z=args.floor_z)
    return 0


if __name__ == "__main__":
    sys.exit(main())
