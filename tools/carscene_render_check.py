#!/usr/bin/env python3
"""Offscreen renders + contact report for the car scene (validation)."""
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
scene = sys.argv[1] if len(sys.argv) > 1 else ROOT / "assets/car_scene/scene_car.xml"
out = ROOT / ".run"
out.mkdir(exist_ok=True)

model = mujoco.MjModel.from_xml_path(str(scene))
data = mujoco.MjData(model)
for _ in range(500):
    mujoco.mj_step(model, data)

bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "car")
print("car pos after settle:", np.round(data.xpos[bid], 3), "quat:", np.round(data.xquat[bid], 3))
for i in range(data.ncon):
    c = data.contact[i]
    g1 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom1)
    g2 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom2)
    print("contact:", g1, "|", g2)

r = mujoco.Renderer(model, 720, 1280)
cam = mujoco.MjvCamera()

def save(path, render_fn):
    render_fn()
    import PIL.Image
    PIL.Image.fromarray(r.render()).save(path)
    print("wrote", path)

# 1) top-down orthographic of the whole building
cam.type = mujoco.mjtCamera.mjCAMERA_FREE
cam.orthographic = True
cam.lookat[:] = [25, 27, 2]
cam.distance = 45


def top_view():
    mujoco.mjv_updateScene(model, data, mujoco.MjvOption(), None, cam, mujoco.mjtCatBit.mjCAT_ALL, r.scene)


save(out / "check_top.png", top_view)

# 2) perspective view near the car
cam.type = mujoco.mjtCamera.mjCAMERA_FREE
cam.lookat[:] = data.xpos[bid]
cam.distance = 8
cam.azimuth = 130
cam.elevation = -25


def near_view():
    mujoco.mjv_updateScene(model, data, mujoco.MjvOption(), None, cam, mujoco.mjtCatBit.mjCAT_ALL, r.scene)


save(out / "check_car.png", near_view)

# 3) on-board camera
cid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "robot_camera")


def onboard():
    r.update_scene(data, camera=cid)


save(out / "check_onboard.png", onboard)
