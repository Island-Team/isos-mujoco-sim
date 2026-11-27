#!/usr/bin/env python3
"""Find an open spawn point for the car: downward ray hits low floor, 16 horizontal
rays all travel > clearance before hitting anything. Writes assets/car_scene/spawn.json."""
import json
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
model = mujoco.MjModel.from_xml_path(str(ROOT / "assets/car_scene/scene_car.xml"))
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)

car_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "car")
geomgroup = np.ones(6, dtype=np.uint8)


def ray(pos, vec):
    geomid = np.zeros(1, dtype=np.int32)
    # bodyexclude = car so the car itself never blocks spawn probing
    return mujoco.mj_ray(model, data, np.asarray(pos), np.asarray(vec), geomgroup, 1, car_id, geomid)


best = []
rng = np.random.default_rng(7)
CLEAR = 1.2
for _ in range(6000):
    x = rng.uniform(0, 50)
    y = rng.uniform(2, 52)
    # floor below: downward ray from knee height hits floor within 0.6m
    d = ray([x, y, 0.5], [0, 0, -1])
    if d < 0 or d > 0.6:
        continue
    # horizontal clearance at wheel height
    ok = True
    for ang in np.linspace(0, 2 * np.pi, 16, endpoint=False):
        v = [np.cos(ang), np.sin(ang), 0]
        dist = ray([x, y, 0.3], v)
        if 0 < dist < CLEAR:
            ok = False
            break
    if ok:
        best.append((x, y, 0.5 - d, (x - 25) ** 2 + (y - 27) ** 2))

best.sort(key=lambda t: t[3])
print(f"open spots found: {len(best)}")
for b in best[:10]:
    print(f"  x={b[0]:.2f} y={b[1]:.2f} floor_z={b[2]:.2f}")
if best:
    spawn = best[0]
    # navigation goal: the open spot farthest from spawn (straight-line; the car
    # still has to find a drivable route through the building).
    goal = max(best, key=lambda t: (t[0] - spawn[0]) ** 2 + (t[1] - spawn[1]) ** 2)
    out = {"pos": [round(spawn[0], 3), round(spawn[1], 3), round(spawn[2], 3)],
           "goal": [round(goal[0], 3), round(goal[1], 3)]}
    (ROOT / "assets/car_scene/spawn.json").write_text(json.dumps(out))
    print("wrote spawn.json:", out, "goal distance:",
          round(((goal[0] - spawn[0]) ** 2 + (goal[1] - spawn[1]) ** 2) ** 0.5, 1), "m")
