"""Export 0001.blend to MuJoCo-friendly assets.

Visuals: duplicate objects, bake world transforms, join per primary material,
export as OBJ with UVs + MTL (MuJoCo loads textures from MTL automatically).
Collision: largest objects exported one-OBJ-each with pure-python vertex
transforms (fast, no operators); MuJoCo convex-hulls each mesh.
Packed images are unpacked next to the OBJs so map_Kd resolves.

Both Blender and MuJoCo are z-up right-handed: coordinates pass through unchanged.

Run headless:
  blender --background 0001.blend --python tools/carscene_blend_export.py -- <outdir> [opts-json]
Options: {"unit_scale":1.0, "collision_min_size":1.5, "max_collision":350, "skip_visual":false}
"""
import bpy
import json
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
outdir = argv[0] if argv else "assets/car_scene"
opts = json.loads(argv[1]) if len(argv) > 1 else {}
UNIT = float(opts.get("unit_scale", 1.0))
COLL_MIN = float(opts.get("collision_min_size", 1.5))
MAX_COLL = int(opts.get("max_collision", 350))
SKIP_VISUAL = bool(opts.get("skip_visual", False))

D = bpy.data
scene = bpy.context.scene

mesh_objs = [o for o in scene.objects if o.visible_get() and o.type == "MESH"]
print(f"exporting {len(mesh_objs)} visible mesh objects, extra unit scale={UNIT}")

# world bbox over all visible mesh objects (for spawn placement)
bbox_min = [1e30] * 3
bbox_max = [-1e30] * 3
for o in mesh_objs:
    for corner in o.bound_box:
        w = o.matrix_world @ Vector(corner)
        for i in range(3):
            bbox_min[i] = min(bbox_min[i], w[i])
            bbox_max[i] = max(bbox_max[i], w[i])

os.makedirs(outdir, exist_ok=True)
texdir = os.path.join(outdir, "textures")
meshdir = os.path.join(outdir, "meshes")
colldir = os.path.join(outdir, "collision")
for d in (texdir, meshdir, colldir):
    os.makedirs(d, exist_ok=True)

manifest = {"scale": UNIT,
            "world_bbox_min": [round(v * UNIT, 3) for v in bbox_min],
            "world_bbox_max": [round(v * UNIT, 3) for v in bbox_max],
            "visual_groups": [], "collision": [], "lights": [], "materials": {}}

# ---------- 0) unpack packed images into meshdir so MTL map_Kd resolves ----------
for img in D.images:
    if img.packed_file:
        base = os.path.basename(bpy.path.abspath(img.filepath)) if img.filepath else None
        if not base or base.strip(". ") == "":
            base = img.name + ".jpg"
        dst = os.path.join(meshdir, base)
        if not os.path.exists(dst):
            with open(dst, "wb") as f:
                f.write(img.packed_file.data)
            print(f"unpacked image {base}")


def export_obj_textured(obj, path):
    """Native exporter: UVs + mtl; MuJoCo reads usemtl/Kd/map_Kd for shading."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(
        filepath=path,
        export_selected_objects=True,
        export_animation=False,
        apply_modifiers=True,
        export_smooth_groups=False,
        export_normals=False,
        export_uv=True,
        export_triangulated_mesh=True,
        export_object_groups=False,
        export_materials=True,
        export_pbr_extensions=False,
        path_mode="COPY",
        global_scale=UNIT,
        forward_axis="Y",  # identity mapping: keep Blender z-up coords untouched for MuJoCo
        up_axis="Z",
    )


if not SKIP_VISUAL:
    # ---------- 1) merged visual groups by primary material ----------
    mat_to_objs = {}
    for o in mesh_objs:
        mats = [s.material.name for s in o.material_slots if s.material]
        mat_to_objs.setdefault(mats[0] if mats else "__none__", []).append(o)

    copies = []
    for o in mesh_objs:
        c = o.copy()
        c.data = o.data.copy()
        mw = o.matrix_world.copy()
        c.parent = None  # bake parenting: transform_apply works in parent space otherwise
        scene.collection.objects.link(c)
        c.matrix_world = mw
        copies.append(c)

    bpy.ops.object.select_all(action="DESELECT")
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    mat_to_copies = {}
    for c in copies:
        mats = [s.material.name for s in c.material_slots if s.material]
        mat_to_copies.setdefault(mats[0] if mats else "__none__", []).append(c)

    for key, cs in mat_to_copies.items():
        if not cs:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for c in cs:
            c.select_set(True)
        bpy.context.view_layer.objects.active = cs[0]
        if len(cs) > 1:
            bpy.ops.object.join()
        joined = cs[0]
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in key)[:40] or "none"
        fname = f"vis_{safe}.obj"
        export_obj_textured(joined, os.path.join(meshdir, fname))
        manifest["visual_groups"].append({"group": key, "file": f"meshes/{fname}",
                                          "verts": len(joined.data.vertices)})
        print(f"visual group '{key}': {len(joined.data.vertices)} verts")

    # material colors + texture file names (informational; shading comes from MTL)
    for m in D.materials:
        if m.name not in mat_to_objs:
            continue
        entry = {"rgba": [0.8, 0.8, 0.8, 1.0], "texture": None}
        if m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    b = n.inputs["Base Color"].default_value
                    entry["rgba"] = [round(b[0], 4), round(b[1], 4), round(b[2], 4), 1.0]
                if n.type == "TEX_IMAGE" and n.image:
                    base = os.path.basename(bpy.path.abspath(n.image.filepath or n.image.name)) or None
                    if base and os.path.exists(os.path.join(meshdir, base)):
                        entry["texture"] = base
        manifest["materials"][m.name] = entry

    for cs in mat_to_copies.values():
        for c in cs:
            try:
                bpy.data.objects.remove(c, do_unlink=True)
            except ReferenceError:
                pass
else:
    old_path = os.path.join(outdir, "manifest.json")
    if os.path.exists(old_path):
        old = json.loads(open(old_path, encoding="utf-8").read())
        manifest["visual_groups"] = old.get("visual_groups", [])
        manifest["materials"] = old.get("materials", {})

# ---------- 2) collision objects: largest structures, pure-python transform ----------
# wipe stale collision files first
for fn in os.listdir(colldir):
    os.remove(os.path.join(colldir, fn))

candidates = []
for o in mesh_objs:
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    size = [max(p[i] for p in bb) - min(p[i] for p in bb) for i in range(3)]
    if max(size) * UNIT >= COLL_MIN:
        center = [(bb[0][i] + bb[6][i]) / 2 for i in range(3)]
        candidates.append((max(size), o, size, center))
candidates.sort(key=lambda t: -t[0])
candidates = candidates[:MAX_COLL]
print(f"collision candidates: {len(candidates)}")

for rank, (maxdim, o, size, center) in enumerate(candidates):
    me = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh(preserve_all_data_layers=False)
    mw = o.matrix_world
    fname = f"col_{rank:04d}.obj"
    with open(os.path.join(colldir, fname), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"o col{rank}\n")
        for v in me.vertices:
            w = mw @ v.co
            f.write(f"v {w.x:.5f} {w.y:.5f} {w.z:.5f}\n")
        for p in me.polygons:
            vs = list(p.vertices)
            for k in range(1, len(vs) - 1):
                f.write(f"f {vs[0] + 1} {vs[k] + 1} {vs[k + 1] + 1}\n")
    o.to_mesh_clear()
    manifest["collision"].append({"file": f"collision/{fname}", "object": o.name,
                                  "size": [round(s * UNIT, 3) for s in size],
                                  "center": [round(c * UNIT, 3) for c in center]})
    if (rank + 1) % 50 == 0:
        print(f"collision {rank + 1}/{len(candidates)}")
print(f"collision objects: {len(manifest['collision'])}")

# ---------- 3) lights ----------
for o in scene.objects:
    if o.type == "LIGHT" and o.visible_get() and len(manifest["lights"]) < 10:
        l = o.data
        p = o.matrix_world.translation
        col = l.color
        manifest["lights"].append({
            "name": o.name, "type": str(l.type),
            "pos": [round(p.x * UNIT, 3), round(p.y * UNIT, 3), round(p.z * UNIT, 3)],
            "energy": getattr(l, "energy", 100),
            "color": [round(col.r, 3), round(col.g, 3), round(col.b, 3)],
        })

with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=1, ensure_ascii=False)
print("WROTE", os.path.join(outdir, "manifest.json"))
