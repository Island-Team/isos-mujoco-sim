#!/usr/bin/env python3
"""Pack a blendscene export: OBJ -> MuJoCo binary MSH, prune unused textures,
re-encode the map_Kd PNGs. Keeps the MTL sidecars (Kd source for the builder).

Usage: python tools/blendscene_pack.py <scene_dir> [--no-textures]

MSH layout (per MuJoCo 3.3.1 src/user/user_mesh.cc LoadMSH; no magic header):
  int32 nvertex(>=4), nnormal, ntexcoord, nface,
  float32 vertices[3*nvertex], float32 normals[3*nnormal],
  float32 texcoords[2*ntexcoord], int32 faces[3*nface]
  nnormal/ntexcoord must be 0 or nvertex. The OBJ loader flips the texcoord v
  axis (v -> 1-v) but LoadMSH does not, so the flip is applied here.
"""
import struct
import sys
from pathlib import Path


def obj_to_msh(obj_path: Path, msh_path: Path) -> tuple[int, int]:
    verts = []
    uvs = []
    faces_txt = []
    for line in obj_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("v "):
            parts = line.split()
            verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif line.startswith("vt "):
            parts = line.split()
            uvs.append((float(parts[1]), float(parts[2])))
        elif line.startswith("f "):
            faces_txt.append(line.split()[1:])
    # Reindex so each vertex carries one texcoord (OBJ allows per-corner UVs).
    out_verts = []
    out_uvs = []
    out_faces = []
    index = {}
    for face in faces_txt:
        tri = []
        for corner in face[:3]:  # faces were triangulated at export
            spec = corner.split("/")
            vi = int(spec[0]) - 1
            ti = int(spec[1]) - 1 if len(spec) > 1 and spec[1] else -1
            key = (vi, ti)
            if key not in index:
                index[key] = len(out_verts)
                out_verts.append(verts[vi])
                u, v = uvs[ti] if 0 <= ti < len(uvs) else (0.0, 0.0)
                out_uvs.append((u, 1.0 - v))  # OBJ loader flips v; MSH must pre-flip
            tri.append(index[key])
        out_faces.append(tri)
    import numpy as np
    v = np.asarray(out_verts, dtype=np.float32)
    uv = np.asarray(out_uvs, dtype=np.float32)
    f = np.asarray(out_faces, dtype=np.int32)
    if len(v) < 4 or len(f) < 1:
        raise ValueError(f"{obj_path.name}: MSH needs >=4 vertices and >=1 face")
    with open(msh_path, "wb") as out:
        out.write(struct.pack("<4i", len(v), 0, len(uv), len(f)))
        out.write(v.tobytes())
        out.write(uv.tobytes())
        out.write(f.tobytes())
    return len(v), len(f)


def prune_and_reencode_textures(scene: Path) -> None:
    """MuJoCo only loads PNG diffuse maps: delete the maps it never loads
    (specular/bump/roughness), convert kept non-PNG map_Kd images to PNG, and
    re-encode kept RGB PNGs when that shrinks them. .exr sidecars are left
    untouched (kept from the original export for provenance)."""
    from PIL import Image

    meshes = scene / "meshes"
    used = set()
    for mtl in meshes.glob("vis_*.mtl"):
        for line in mtl.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("map_Kd"):
                name = line.split()[-1].replace("\\", "/").split("/")[-1]
                used.add(Path(name).stem)
    removed = kept = converted = 0
    for img_path in sorted(meshes.iterdir()):
        suffix = img_path.suffix.lower()
        if suffix == ".exr" or suffix not in (".png", ".jpg", ".jpeg", ".bmp", ".tga", ".tif", ".tiff"):
            continue
        if img_path.stem not in used:
            img_path.unlink()
            removed += 1
            continue
        if suffix == ".png":
            img = Image.open(img_path)
            if img.mode == "RGB":
                img.save(img_path, optimize=True)
            kept += 1
            continue
        png = img_path.with_suffix(".png")
        if png.exists():  # a PNG twin already fills the map_Kd slot
            img_path.unlink()
            removed += 1
            continue
        Image.open(img_path).save(png)
        img_path.unlink()
        converted += 1
    print(f"textures: kept {kept} map_Kd PNGs (re-encoded), converted {converted} to PNG, "
          f"removed {removed} unused/redundant maps")


def pack(scene: Path, do_textures: bool = True) -> None:
    """Convert every vis_*.obj / col_*.obj under scene/ to binary MSH in place."""
    meshes = scene / "meshes"
    total_before = total_after = 0
    for obj in sorted(list(meshes.glob("vis_*.obj")) + list((scene / "collision").glob("col_*.obj"))):
        msh = obj.with_suffix(".msh")
        nv, nf = obj_to_msh(obj, msh)
        before, after = obj.stat().st_size, msh.stat().st_size
        total_before += before
        total_after += after
        obj.unlink()  # the packed MSH replaces the text OBJ
        print(f"{obj.name}: {before // 1024}K -> {after // 1024}K ({nv} verts, {nf} tris)")
    print(f"TOTAL meshes: {total_before // 1024}K -> {total_after // 1024}K "
          f"({100 * total_after / max(total_before, 1):.0f}%)")
    if do_textures:
        prune_and_reencode_textures(scene)


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--no-textures"]
    positions = [a for a in args if not a.startswith("-")]
    if len(positions) != 1:
        sys.exit("usage: python tools/blendscene_pack.py <scene_dir> [--no-textures]")
    scene = Path(positions[0]).resolve()
    if not (scene / "meshes").is_dir():
        sys.exit(f"no blendscene export found under {scene}")
    pack(scene, do_textures="--no-textures" not in sys.argv)


if __name__ == "__main__":
    main()
