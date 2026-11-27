#!/usr/bin/env python3
"""Isolated diff-drive tuning on a plane: fast parameter search for stable traction.

Lab tool: sweeps kv/armature/friction on a synthetic plane model (no building).
The winning constants were hand-copied into tools/blendscene_build.py — keep the
two in sync when re-tuning (see the cross-language contract note there).
"""
import mujoco
import numpy as np

TEMPLATE = """
<mujoco>
  <option timestep="0.002" integrator="implicitfast" gravity="0 0 -9.81" {cone}/>
  <worldbody>
    <geom name="floor" type="plane" size="50 50 0.1" friction="{floor_fric} 0.02 0.001"/>
    <body name="car" pos="0 0 {z0}">
      <freejoint name="car_root"/>
      <geom name="chassis" type="box" size="{BL} {BW} {BH}" pos="0 0 {cz}" mass="12" rgba="0.15 0.19 0.26 1"/>
      <camera name="robot_camera" pos="{BL} 0 {cz2}" xyaxes="0 -1 0 0 0 1" fovy="78"/>
      {wheels}
      {casters}
    </body>
  </worldbody>
  <actuator>
    <velocity name="left_wheel_motor" joint="wheel_left_spin" kv="{kv}" ctrlrange="-15 15" ctrllimited="true"/>
    <velocity name="right_wheel_motor" joint="wheel_right_spin" kv="{kv}" ctrlrange="-15 15" ctrllimited="true"/>
  </actuator>
</mujoco>
"""

WR = 0.08  # wheel radius


def build(kv, arm, fric, condim_wheel=3, cone="", wheel_y=0.19, caster_x=0.16):
    wheels = ""
    for sign, nm in ((1, "left"), (-1, "right")):
        wheels += f'''
      <body name="wheel_{nm}" pos="0 {sign*wheel_y} {WR}">
        <joint name="wheel_{nm}_spin" type="hinge" axis="0 1 0" armature="{arm}" damping="0.01"/>
        <geom name="wheel_{nm}_geom" type="cylinder" size="{WR} 0.02" quat="0.7071 0.7071 0 0"
              mass="0.8" rgba="0.05 0.05 0.05 1" friction="{fric} 0.005 0.0001" condim="{condim_wheel}"/>
      </body>'''
    casters = ""
    for nm, x in (("front", caster_x), ("rear", -caster_x)):
        casters += f'''
      <body name="caster_{nm}" pos="{x} 0 0.03">
        <geom name="caster_{nm}_geom" type="sphere" size="0.03" mass="0.2" rgba="0.4 0.4 0.4 1"
              friction="0.02 0.005 0.0001" condim="1"/>
      </body>'''
    xml = TEMPLATE.format(cone=cone, floor_fric=1.0, z0=WR + 0.02, BL=0.21, BW=0.15, BH=0.05,
                          cz=WR + 0.02, cz2=WR + 0.05, wheels=wheels, casters=casters, kv=kv)
    return mujoco.MjModel.from_xml_string(xml)


def evaluate(m, cmd=8.0, T=3.0):
    d = mujoco.MjData(m)
    L = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_wheel_motor")
    R = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, "right_wheel_motor")
    for _ in range(400):
        mujoco.mj_step(m, d)
    ramp = int(0.5 / m.opt.timestep)
    for i in range(ramp):
        c = cmd * i / ramp
        d.ctrl[L] = d.ctrl[R] = c
        mujoco.mj_step(m, d)
    speeds, ncons = [], []
    for _ in range(int(T / m.opt.timestep)):
        d.ctrl[L] = d.ctrl[R] = cmd
        mujoco.mj_step(m, d)
        Rm = d.xmat[1].reshape(3, 3)
        vb = Rm.T @ np.array([d.qvel[0], d.qvel[1], 0])
        speeds.append(vb[0])
        ncons.append(d.ncon)
    q = d.xquat[1]
    yaw = np.degrees(np.arctan2(2 * (q[0] * q[3] - q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2)))
    return np.mean(speeds), np.mean(ncons), yaw


for kv in (5, 15, 40):
    for arm in (0.02, 0.1):
        for fric in (1.0, 1.4):
            m = build(kv, arm, fric)
            v, nc, yaw = evaluate(m)
            ideal = 8 * WR
            print(f"kv={kv:3} arm={arm:5} fric={fric}: speed={v:.3f}/{ideal} ({100*v/ideal:3.0f}%) "
                  f"ncon={nc:.1f} yaw={yaw:+.1f}")
