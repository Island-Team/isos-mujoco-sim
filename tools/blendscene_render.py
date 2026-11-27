#!/usr/bin/env python3
"""Offscreen renders + contact report for a blendscene scene (validation).

Usage: python tools/blendscene_render.py [scene_car.xml] [--recolor]

Camera framing derives from the model's <statistic> (center/extent), so it
works for any exported building. --recolor overrides visual geoms with bright
random colors to diagnose dark-render / missing-texture problems (formerly the
carscene_debug_colors one-off).
"""
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    recolor = "--recolor" in argv
    positions = [a for a in argv if not a.startswith("-")]
    if len(positions) > 1:
        sys.exit("usage: python tools/blendscene_render.py [scene_car.xml] [--recolor]")
    scene = Path(positions[0]) if positions else ROOT / "assets" / "car_scene" / "scene_car.xml"
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

    if recolor:
        # geom stats by group, then bright random colors on the visual group
        for g in range(4):
            ids = np.where(model.geom_group == g)[0]
            if len(ids):
                lo = model.geom_aabb[ids[:50], :3].min(axis=0)
                hi = (model.geom_aabb[ids[:50], :3] + model.geom_aabb[ids[:50], 3:6]).max(axis=0)
                print(f"group {g}: {len(ids)} geoms, aabb sample lo={np.round(lo,1)} hi={np.round(hi,1)}")
        print("stat.extent:", model.stat.extent, "center:", model.stat.center)
        rng = np.random.default_rng(0)
        for i in range(model.ngeom):
            if model.geom_group[i] == 2:
                model.geom_rgba[i] = rng.uniform(0.4, 1.0, 4)

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
    cam.lookat[:] = model.stat.center
    cam.distance = model.stat.extent * 0.75

    def top_view():
        mujoco.mjv_updateScene(model, data, mujoco.MjvOption(), None, cam, mujoco.mjtCatBit.mjCAT_ALL, r.scene)

    save(out / "check_top.png", top_view)

    if recolor:
        # extra mid-height perspective over the recolored visual geoms
        cam.orthographic = False
        cam.lookat[:] = model.stat.center
        cam.distance = model.stat.extent * 0.5
        cam.azimuth = -90
        cam.elevation = -35

        def colored_view():
            mujoco.mjv_updateScene(model, data, mujoco.MjvOption(), None, cam, mujoco.mjtCatBit.mjCAT_ALL, r.scene)

        save(out / "check_colored.png", colored_view)
        img = r.render()
        arr = img.reshape(-1, 3)
        print("pixel mean:", arr.mean(axis=0).round(1), "max:", arr.max(axis=0))
        return 0

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
