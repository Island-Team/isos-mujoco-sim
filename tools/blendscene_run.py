#!/usr/bin/env python3
"""Interactive MuJoCo 3.3.1 viewer for a blendscene car-navigation scene.

Keyboard (toggle/nudge controls):
  W/S     forward / backward target speed
  A/D     turn left / right
  Space   stop
  R       reset car to spawn
  C       toggle chase camera (follow car) vs free camera
  +/-     overall speed scale

Run: .car-venv/Scripts/python tools/blendscene_run.py [path/to/scene.xml]
"""
import sys
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    scene = Path(argv[0]) if argv else ROOT / "assets" / "car_scene" / "scene.xml"

    model = mujoco.MjModel.from_xml_path(str(scene))
    data = mujoco.MjData(model)

    # diff-drive geometry straight from the model (stays correct if the car grows)
    wheel_gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "wheel_left_geom")
    wheel_radius = float(model.geom_size[wheel_gid][0])
    left_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "wheel_left")
    right_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "wheel_right")
    mujoco.mj_forward(model, data)
    body_span = float(np.linalg.norm(data.xpos[left_bid][:2] - data.xpos[right_bid][:2]))

    left_m = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_wheel_motor")
    right_m = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "right_wheel_motor")
    car_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "car")
    assert left_m >= 0 and right_m >= 0 and car_bid >= 0, "scene is missing the car"

    lin, ang, scale = 0.0, 0.0, 1.0
    chase = True
    spawn = [model.body_pos[car_bid].copy(), np.array(model.body_quat[car_bid], dtype=float)]

    def wheel_targets(lin_mps, ang_radps):
        vl = lin_mps - ang_radps * body_span / 2
        vr = lin_mps + ang_radps * body_span / 2
        return vl / wheel_radius, vr / wheel_radius

    def on_key(key):
        nonlocal lin, ang, scale, chase
        step_lin, step_ang = 0.2, 0.6
        k = chr(key) if 32 <= key < 127 else ""
        if k in ("w", "W"):
            lin = min(lin + step_lin * scale, 1.5 * scale)
        elif k in ("s", "S"):
            lin = max(lin - step_lin * scale, -1.0 * scale)
        elif k in ("a", "A"):
            ang = min(ang + step_ang, 3.0)
        elif k in ("d", "D"):
            ang = max(ang - step_ang, -3.0)
        elif key == 32:  # space
            lin = ang = 0.0
        elif k in ("r", "R"):
            mujoco.mj_resetData(model, data)
            qadr = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "car_root")]
            data.qpos[qadr:qadr + 3] = spawn[0]
            data.qpos[qadr + 3:qadr + 7] = spawn[1]
            mujoco.mj_forward(model, data)
            lin = ang = 0.0
        elif k in ("c", "C"):
            chase = not chase
            print(f"chase camera: {chase}")
        elif k in ("+", "="):
            scale = min(scale + 0.25, 3.0)
        elif k in ("-", "_"):
            scale = max(scale - 0.25, 0.25)
        print(f"lin={lin:+.2f} m/s ang={ang:+.2f} rad/s scale={scale:.2f}")

    print(__doc__)
    with mujoco.viewer.launch_passive(model, data, key_callback=on_key) as v:
        while v.is_running():
            lt, rt = wheel_targets(lin, ang)
            data.ctrl[left_m] = np.clip(lt, -15, 15)
            data.ctrl[right_m] = np.clip(rt, -15, 15)
            mujoco.mj_step(model, data)
            if chase:
                pos = data.xpos[car_bid]
                v.cam.lookat[:] = pos
                v.cam.distance = 3.5
                v.cam.azimuth = 135
                v.cam.elevation = -20
            v.sync()
            time.sleep(0.001)
    return 0


if __name__ == "__main__":
    sys.exit(main())
