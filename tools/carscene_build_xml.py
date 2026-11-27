#!/usr/bin/env python3
"""Build the MuJoCo car-scene XML from the Blender export manifest.

Differential-drive car + full building visuals + structural collision.
Run from repo root:  uv run -q --python .car-venv python tools/carscene_build_xml.py
(or any python3) — writes assets/car_scene/scene_car.xml
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSET = ROOT / "assets" / "car_scene"
MANIFEST = json.loads((ASSET / "manifest.json").read_text(encoding="utf-8"))


def parse_mtl(obj_file):
    """Return (kd_rgba, texture_basename) from the OBJ's MTL sidecar."""
    mtl = obj_file.with_suffix(".mtl")
    if not mtl.exists():
        return None, None
    kd = None
    tex = None
    for line in mtl.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"^\s*Kd\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", line)
        if m and kd is None:
            kd = [float(m.group(i)) for i in (1, 2, 3)] + [1.0]
        m = re.match(r"^\s*map_Kd\s+(?:-[\w.]+\s+)*(.+)$", line)
        if m and tex is None:
            tex = Path(m.group(1).strip().replace("\\", "/")).name
    return kd, tex

# ---- car configuration (meters) ----
WHEEL_RADIUS = 0.08
WHEEL_WIDTH = 0.04
BODY_L = 0.42
BODY_W = 0.30
BODY_H = 0.10
WHEEL_X = 0.0             # driven wheels at center for symmetric support
CASTER_R = 0.03          # ball casters front/back
MAX_WHEEL_SPEED = 15.0   # rad/s -> 1.2 m/s

bmin = MANIFEST["world_bbox_min"]
bmax = MANIFEST["world_bbox_max"]
spawn_xy = ((bmin[0] + bmax[0]) / 2, (bmin[1] + bmax[1]) / 2)
floor_z = bmin[2]
spawn_file = ASSET / "spawn.json"
goal_xy = None
if spawn_file.exists():
    data = json.loads(spawn_file.read_text(encoding="utf-8"))
    sp = data["pos"]
    spawn_xy = (sp[0], sp[1])
    floor_z = sp[2]
    goal_xy = data.get("goal")

lines = []
A = lines.append
A('<?xml version="1.0" encoding="utf-8"?>')
A('<mujoco model="car_scene_v1">')
A('  <custom>')
A('    <numeric name="eos_benchmark_car_navigation_v1" data="1" />')
A('  </custom>')
A('  <compiler angle="radian" autolimits="true" meshdir="." />')
A('  <option timestep="0.002" integrator="implicitfast" gravity="0 0 -9.81" />')
A('  <visual>')
A('    <global offwidth="1280" offheight="720" />')
A('    <headlight ambient="0.4 0.4 0.4" diffuse="0.6 0.6 0.6" />')
A('  </visual>')
A(f'  <statistic center="{(bmin[0]+bmax[0])/2:.1f} {(bmin[1]+bmax[1])/2:.1f} {(bmin[2]+bmax[2])/2:.1f}" extent="{max(bmax[i]-bmin[i] for i in range(3)):.1f}" />')

A('  <asset>')
for g in MANIFEST["visual_groups"]:
    name = Path(g["file"]).stem
    A(f'    <mesh name="{name}" file="meshes/{name}.msh" />')
for c in MANIFEST["collision"]:
    name = Path(c["file"]).stem
    A(f'    <mesh name="{name}" file="collision/{name}.msh" />')
# textures + materials from MTL sidecars (MuJoCo does not auto-load MTL)
def resolve_tex(tex):
    p = ASSET / "meshes" / tex
    if p.exists():
        return tex
    png = p.with_suffix(".png")
    if png.exists():  # jpg textures were converted to png (MuJoCo needs PNG)
        return png.name
    return None


tex_names = {}
for g in MANIFEST["visual_groups"]:
    kd, tex0 = parse_mtl(ASSET / g["file"])
    tex = resolve_tex(tex0) if tex0 else None
    if tex:
        mesh_name = Path(g["file"]).stem
        tex_name = "tx_" + re.sub(r"\W", "_", tex)
        if tex_name not in tex_names:
            tex_names[tex_name] = tex
            A(f'    <texture name="{tex_name}" type="2d" file="meshes/{tex}" />')
            A(f'    <material name="mat_{mesh_name}" texture="{tex_name}" texuniform="true" specular="0.2" />')
A('  </asset>')

A('  <worldbody>')
# lights: fixed directional fill + exported point lights
A('    <light name="sun" pos="0 0 %d" dir="0 0 -1" diffuse="0.7 0.7 0.7" specular="0.2 0.2 0.2" />' % int(bmax[2] + 5))
for i, l in enumerate(MANIFEST["lights"][:8]):
    if l["type"] == "POINT":
        r, g, b = l["color"]
        A(f'    <light name="blender_light_{i}" pos="{l["pos"][0]} {l["pos"][1]} {l["pos"][2]}" '
          f'diffuse="{r:.2f} {g:.2f} {b:.2f}" attenuation="0.05 0.002 0.0005" />')
# safety floor plane (huge, friction like concrete) in case building floor is above it
A(f'    <geom name="safety_floor" type="plane" size="200 200 0.1" pos="0 0 {floor_z - 0.02:.3f}" '
  'rgba="0.25 0.27 0.3 1" friction="1.0 0.02 0.001" />')

# visual-only building meshes: material if textured, else Kd color from MTL
for g in MANIFEST["visual_groups"]:
    name = Path(g["file"]).stem
    kd, tex0 = parse_mtl(ASSET / g["file"])
    tex = resolve_tex(tex0) if tex0 else None
    if tex:
        A(f'    <geom name="{name}" type="mesh" mesh="{name}" group="2" contype="0" conaffinity="0" '
          f'material="mat_{name}" />')
    else:
        rgba = kd or MANIFEST["materials"].get(g["group"], {}).get("rgba") or [0.7, 0.7, 0.7, 1.0]
        A(f'    <geom name="{name}" type="mesh" mesh="{name}" group="2" contype="0" conaffinity="0" '
          f'rgba="{rgba[0]:.3f} {rgba[1]:.3f} {rgba[2]:.3f} 1" />')
# collision meshes (MuJoCo convex-hulls each automatically)
for c in MANIFEST["collision"]:
    name = Path(c["file"]).stem
    A(f'    <geom name="{name}_c" type="mesh" mesh="{name}" group="3" rgba="0.3 0.6 0.3 0" '
      'friction="1.2 0.005 0.0001" />')

# ---------------- differential-drive car ----------------
# Notes from tuning (tools/carscene_tune_car.py):
# - casters MUST roll, not slide: MuJoCo combines friction as max(geom1, geom2), so a
#   "frictionless" rigid sphere still brakes against a high-friction floor and the
#   velocity servos then fight the brake until the car hops. Ball-jointed spheres roll.
# - wheel joints need armature so the velocity servo stays stable at dt=0.002.
z0 = floor_z + WHEEL_RADIUS + 0.02
A(f'    <body name="car" pos="{spawn_xy[0]:.3f} {spawn_xy[1]:.3f} {z0:.3f}">')
A('      <freejoint name="car_root" />')
A(f'      <geom name="chassis" type="box" size="{BODY_L/2} {BODY_W/2} {BODY_H/2}" pos="0 0 {WHEEL_RADIUS+0.02:.3f}" '
  'mass="12" rgba="0.15 0.19 0.26 1" />')
A(f'      <geom name="cabin" type="box" size="{BODY_L/4} {BODY_W/2.6} {BODY_H/1.6}" pos="{BODY_L/6:.3f} 0 {WHEEL_RADIUS+BODY_H+0.02:.3f}" '
  'mass="2" rgba="0.13 0.16 0.22 1" contype="0" conaffinity="0" />')
A(f'      <camera name="robot_camera" pos="{BODY_L/2-0.02:.3f} 0 {WHEEL_RADIUS+BODY_H+0.02:.3f}" xyaxes="0 -1 0 0 0 1" fovy="78" />')
A(f'      <site name="car_center" pos="0 0 {WHEEL_RADIUS:.3f}" size="0.01" rgba="1 0 0 0.5" />')
for sign, yoff, nm in ((1, 1, "left"), (-1, 1, "right")):
    yy = sign * (BODY_W / 2 + WHEEL_WIDTH / 2 + 0.01)
    A(f'      <body name="wheel_{nm}" pos="{WHEEL_X:.3f} {yy:.3f} {WHEEL_RADIUS:.3f}">')
    A(f'        <joint name="wheel_{nm}_spin" type="hinge" axis="0 1 0" armature="0.05" damping="0.01" />')
    A(f'        <geom name="wheel_{nm}_geom" type="cylinder" size="{WHEEL_RADIUS} {WHEEL_WIDTH/2}" quat="0.7071 0.7071 0 0" '
      'mass="0.8" rgba="0.05 0.05 0.05 1" friction="1.2 0.005 0.0001" />')
    A('      </body>')
for nm, xoff in (("front", BODY_L / 2 - 0.05), ("rear", -BODY_L / 2 + 0.05)):
    A(f'      <body name="caster_{nm}" pos="{xoff:.3f} 0 {CASTER_R:.3f}">')
    A(f'        <joint name="caster_{nm}_ball" type="ball" damping="0.002" />')
    A(f'        <geom name="caster_{nm}_geom" type="sphere" size="{CASTER_R}" mass="0.2" '
      'rgba="0.4 0.4 0.4 1" friction="1.2 0.005 0.0001" />')
    A('      </body>')
A('    </body>')
if goal_xy is not None:
    A(f'    <site name="navigation_goal" pos="{goal_xy[0]:.3f} {goal_xy[1]:.3f} 0.02" type="ellipsoid" '
      'size="0.35 0.35 0.005" rgba="0.08 0.75 0.25 0.65" />')
A('  </worldbody>')

A('  <actuator>')
A(f'    <velocity name="left_wheel_motor" joint="wheel_left_spin" kv="15" ctrlrange="-{MAX_WHEEL_SPEED} {MAX_WHEEL_SPEED}" ctrllimited="true" />')
A(f'    <velocity name="right_wheel_motor" joint="wheel_right_spin" kv="15" ctrlrange="-{MAX_WHEEL_SPEED} {MAX_WHEEL_SPEED}" ctrllimited="true" />')
A('  </actuator>')
A('</mujoco>')

out = ASSET / "scene_car.xml"
text = "\n".join(l for l in lines if l)
out.write_text(text, encoding="utf-8")
print(f"wrote {out} ({len(text)} bytes), visual groups: {len(MANIFEST['visual_groups'])}, "
      f"collision: {len(MANIFEST['collision'])}, spawn: {spawn_xy}, floor_z: {floor_z}")
