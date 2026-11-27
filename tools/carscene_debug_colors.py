#!/usr/bin/env python3
"""Diagnose why visual meshes render dark: override colors, check AABBs, stats."""
import numpy as np
import mujoco

model = mujoco.MjModel.from_xml_path('assets/car_scene/scene_car.xml')
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)

# geom stats by group
for g in range(4):
    ids = np.where(model.geom_group == g)[0]
    if len(ids):
        lo = model.geom_aabb[ids[:50], :3].min(axis=0)
        hi = (model.geom_aabb[ids[:50], :3] + model.geom_aabb[ids[:50], 3:6]).max(axis=0)
        print(f"group {g}: {len(ids)} geoms, aabb sample lo={np.round(lo,1)} hi={np.round(hi,1)}")
print("stat.extent:", model.stat.extent, "center:", model.stat.center)

# override visual geoms with bright per-geom colors
rng = np.random.default_rng(0)
for i in range(model.ngeom):
    if model.geom_group[i] == 2:
        model.geom_rgba[i] = rng.uniform(0.4, 1.0, 4)

r = mujoco.Renderer(model, 720, 1280)
cam = mujoco.MjvCamera()
cam.type = mujoco.mjtCamera.mjCAMERA_FREE
cam.orthographic = False
car = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'car')
cam.lookat[:] = [25, 27, 1]
cam.distance = 30
cam.azimuth = -90
cam.elevation = -35
mujoco.mjv_updateScene(model, data, mujoco.MjvOption(), None, cam, mujoco.mjtCatBit.mjCAT_ALL, r.scene)
img = r.render()
import PIL.Image
PIL.Image.fromarray(img).save('.run/check_colored.png')
arr = img.reshape(-1, 3)
print("pixel mean:", arr.mean(axis=0).round(1), "max:", arr.max(axis=0))
print("wrote .run/check_colored.png")
