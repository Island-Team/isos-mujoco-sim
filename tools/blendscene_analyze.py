"""Analyze a .blend inside Blender: units, bbox, object types, collections, materials.

Run headless (tools/blendscene.py analyze does this for you):
  blender --background <model.blend> --python tools/blendscene_analyze.py -- [outfile]
Without an outfile nothing is written; the summary is printed either way.
"""
import bpy
import json
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
outfile = os.path.abspath(argv[0]) if argv else None

D = bpy.data
out = {}

# --- units & scenes ---
out["scenes"] = [s.name for s in D.scenes]
u = bpy.context.scene.unit_settings
out["unit_system"] = u.system
out["unit_scale"] = u.scale_length

# --- count datablocks by type ---
out["counts"] = {
    "objects": len(D.objects),
    "meshes": len(D.meshes),
    "materials": len(D.materials),
    "images": len(D.images),
    "lights": len(D.lights),
    "cameras": len(D.cameras),
    "curves": len(D.curves),
    "collections": len(D.collections),
}

# --- visible mesh objects in the active scene: world bbox ---
scene = bpy.context.scene
mesh_objs = [o for o in scene.objects if o.visible_get() and o.type == "MESH"]
bbox_min = Vector((1e30,) * 3)
bbox_max = Vector((-1e30,) * 3)
for o in mesh_objs:
    for corner in o.bound_box:
        w = o.matrix_world @ Vector(corner)
        bbox_min.x = min(bbox_min.x, w.x); bbox_min.y = min(bbox_min.y, w.y); bbox_min.z = min(bbox_min.z, w.z)
        bbox_max.x = max(bbox_max.x, w.x); bbox_max.y = max(bbox_max.y, w.y); bbox_max.z = max(bbox_max.z, w.z)
out["visible_mesh_objects"] = len(mesh_objs)
if mesh_objs:
    out["world_bbox_min"] = list(bbox_min)
    out["world_bbox_max"] = list(bbox_max)
    out["world_bbox_size"] = list(bbox_max - bbox_min)

# --- object types histogram ---
hist = {}
for o in scene.objects:
    hist[o.type] = hist.get(o.type, 0) + 1
out["object_type_hist"] = hist

# --- collections ---
def coll_info(c, depth=0):
    items = {"name": c.name, "objects": len(c.objects), "children": [coll_info(ch, depth + 1) for ch in c.children]}
    return items
out["collection_tree"] = [coll_info(c) for c in scene.collection.children]

# --- mesh complexity ---
verts = sum(len(m.vertices) for m in D.meshes)
faces = sum(len(m.polygons) for m in D.meshes)
out["mesh_total_vertices"] = verts
out["mesh_total_faces"] = faces

# --- per-material stats (over meshes actually used by objects) ---
mat_stats = {}
for o in mesh_objs:
    for slot in o.material_slots:
        nm = slot.material.name if slot.material else "(none)"
        st = mat_stats.setdefault(nm, {"objects": 0, "images": []})
        st["objects"] += 1
for m in D.materials:
    if m.name in mat_stats:
        try:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    mat_stats[m.name]["images"].append(n.image.filepath or n.image.name)
        except Exception:
            pass
out["material_stats"] = mat_stats

if outfile:
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
print(json.dumps({k: out[k] for k in ("scenes", "unit_system", "unit_scale", "counts", "visible_mesh_objects",
                                      "world_bbox_min", "world_bbox_max", "world_bbox_size",
                                      "object_type_hist", "mesh_total_vertices", "mesh_total_faces")}, indent=1))
if outfile:
    print("WROTE", outfile)
