#!/usr/bin/env python3
"""Scripted drive test: straight, turn left, turn right, reverse. Reports motion."""
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
model = mujoco.MjModel.from_xml_path(str(ROOT / "assets/car_scene/scene_car.xml"))
data = mujoco.MjData(model)

L = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_wheel_motor")
R = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "right_wheel_motor")
bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "car")


def settle(n=500):
    for _ in range(n):
        mujoco.mj_step(model, data)


def drive(left, right, seconds):
    data.ctrl[L] = left
    data.ctrl[R] = right
    p0 = data.xpos[bid].copy()
    q0 = data.xquat[bid].copy()
    for _ in range(int(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)
    dp = data.xpos[bid] - p0
    yaw0 = np.degrees(np.arctan2(2 * (q0[0] * q0[3] - q0[1] * q0[2]),
                                 1 - 2 * (q0[2] ** 2 + q0[3] ** 2)))
    q1 = data.xquat[bid]
    yaw1 = np.degrees(np.arctan2(2 * (q1[0] * q1[3] - q1[1] * q1[2]),
                                 1 - 2 * (q1[2] ** 2 + q1[3] ** 2)))
    print(f"  moved dx={dp[0]:+.2f} dy={dp[1]:+.2f} dz={dp[2]:+.3f} | yaw {yaw1 - yaw0:+.1f} deg | ncon={data.ncon}")


settle()
print("start:", data.xpos[bid].round(2))
print("forward 2s (8 rad/s):")
drive(8, 8, 2.0)
print("turn left in place 2s (+6/-6):")
drive(6, -6, 2.0)
print("forward-right arc 2s (8/4):")
drive(8, 4, 2.0)
print("reverse 2s (-8/-8):")
drive(-8, -8, 2.0)
print("stop 1s:")
drive(0, 0, 1.0)
print("final:", data.xpos[bid].round(2), "contacts:", data.ncon)
print("OK" if data.ncon >= 3 and abs(data.xpos[bid][2]) < 0.2 else "SUSPECT: car may have flipped/fallen")
