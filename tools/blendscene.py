#!/usr/bin/env python3
"""Convert any Blender .blend into a MuJoCo car-navigation scene.

  python tools/blendscene.py build <model.blend> [-o assets/<name>_scene] [flags]

Pipeline: headless Blender export (per-material visual OBJ+MTL with textures,
largest-structure collision OBJs, manifest.json) -> OBJ-to-binary-MSH pack ->
scene.xml embedding the differential-drive car -> spawn/goal raycast on
first build -> XML rebuild with the found spawn.

Run under a Python with mujoco+numpy+Pillow (the repo's .car-venv works:
.car-venv/Scripts/python tools/blendscene.py build <model.blend>). Blender is
located via --blender, the BLENDER_EXE environment variable, or PATH.

Stages and validators are also exposed directly:
  analyze <model.blend> [--out FILE]   scene statistics (units, bbox, materials)
  spawn   <scene_dir> [--force ...]    recompute spawn.json (deliberate!)
  run     [SCENE]                      interactive WASD viewer
  drive   [SCENE]                      headless scripted drive check
  render  [SCENE] [--recolor]          offscreen renders + contact report
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

SCENE_XML = "scene.xml"


def find_blender(explicit: str) -> str:
    exe = explicit or os.environ.get("BLENDER_EXE") or "blender"
    found = shutil.which(exe) or (str(Path(exe).resolve()) if Path(exe).is_file() else None)
    if not found:
        sys.exit(f"Blender not found: {exe!r}. Pass --blender PATH, set BLENDER_EXE, "
                 "or put blender on PATH.")
    return found


def run_export(blender: str, blend: Path, out: Path, opts: dict) -> None:
    """Launch the export payload headless. Blender exits 0 even when the payload
    raises, so also require a freshly written, parseable manifest.json."""
    payload = Path(__file__).resolve().parent / "blendscene_export.py"
    cmd = [blender, "--background", str(blend), "--python", str(payload),
           "--", str(out.resolve()), json.dumps(opts)]
    print("+", " ".join(cmd))
    started = time.time()
    proc = subprocess.run(cmd, cwd=str(ROOT))
    manifest = out / "manifest.json"
    ok = proc.returncode == 0 and manifest.is_file()
    if ok:
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            ok = "world_bbox_min" in data and manifest.stat().st_mtime >= started - 1
        except (json.JSONDecodeError, OSError):
            ok = False
    if not ok:
        sys.exit("Blender export failed (see the output above)")


def need_module(stage: str, *names: str) -> None:
    import importlib
    for name in names:
        try:
            importlib.import_module(name)
        except ImportError:
            sys.exit(f"the {stage} stage needs the {name} module; run under a python "
                     f"that has it (e.g. .car-venv/Scripts/python tools/blendscene.py ...)")


def parse_xy(text, what):
    parts = [float(v) for v in text.split(",")]
    if len(parts) not in (2, 3) or (what == "goal" and len(parts) != 2):
        sys.exit(f"--{what} expects {', '.join(['X', 'Y'] if what == 'goal' else ['X', 'Y(, Z)'])}")
    return parts


def _floats(text):
    return [float(v) for v in text.split(",")]


def write_spawn(out: Path, manifest: dict, spawn=None, goal=None) -> None:
    """Write spawn.json from --spawn/--goal, keeping any unspecified side."""
    spawn_file = out / "spawn.json"
    existing = json.loads(spawn_file.read_text(encoding="utf-8")) if spawn_file.exists() else {}
    bmin = manifest["world_bbox_min"]
    pos = spawn or existing.get("pos") or [bmin[0], bmin[1], bmin[2]]
    if len(pos) == 2:
        pos = pos + [existing.get("pos", [0, 0, bmin[2]])[2] if existing.get("pos") else bmin[2]]
    goal = goal or existing.get("goal")
    if goal is None:
        sys.exit("--spawn without --goal needs an existing spawn.json or an explicit --goal")
    out_json = {"pos": pos, "goal": goal}
    spawn_file.write_text(json.dumps(out_json))
    print("wrote spawn.json:", out_json)


def cmd_build(args) -> int:
    blend = args.blend.resolve()
    if not blend.is_file():
        sys.exit(f"blend not found: {blend}")
    out = (args.out.resolve() if args.out
           else ROOT / "assets" / (blend.stem + "_scene"))
    out.mkdir(parents=True, exist_ok=True)
    print(f"building scene in {out}")

    if not args.no_export:
        blender = find_blender(args.blender_exe)
        opts = {"unit_scale": args.unit_scale, "collision_min_size": args.collision_min_size,
                "max_collision": args.max_collision, "skip_visual": args.skip_visual}
        run_export(blender, blend, out, opts)
    manifest_file = out / "manifest.json"
    if not manifest_file.is_file():
        sys.exit(f"no manifest.json in {out}; run without --no-export first")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    if not args.skip_pack:
        has_obj = any((out / "meshes").glob("*.obj")) or any((out / "collision").glob("*.obj"))
        if has_obj:
            need_module("pack", "numpy")
            import blendscene_pack
            blendscene_pack.pack(out, do_textures=not args.no_textures)

    import blendscene_build
    blendscene_build.build(out)

    spawn_file = out / "spawn.json"
    if args.spawn or args.goal:
        write_spawn(out, manifest, parse_xy(args.spawn, "spawn") if args.spawn else None,
                    parse_xy(args.goal, "goal") if args.goal else None)
        blendscene_build.build(out)
    elif args.respawn or not spawn_file.exists():
        need_module("spawn", "mujoco", "numpy")
        import blendscene_spawn
        blendscene_spawn.find_spawn(out, force=True, window=args.window, center=args.center,
                                    inset=args.spawn_inset, seed=args.seed,
                                    trials=args.trials, clearance=args.clearance,
                                    floor_z=args.floor_z)
        blendscene_build.build(out)
    else:
        print(f"reusing {spawn_file} (pass --respawn to recompute)")

    scene_xml = out / SCENE_XML
    print(f"\nscene ready: {scene_xml}")
    print(f"try it: .car-venv/Scripts/python tools/blendscene_run.py {scene_xml}")

    if args.drive:
        need_module("drive", "mujoco", "numpy")
        import blendscene_drive
        if blendscene_drive.main([str(scene_xml)]) != 0:
            sys.exit("drive validation failed")
    if args.render:
        need_module("render", "mujoco", "numpy")
        import blendscene_render
        blendscene_render.main([str(scene_xml)])
    return 0


def cmd_analyze(args) -> int:
    blend = args.blend.resolve()
    if not blend.is_file():
        sys.exit(f"blend not found: {blend}")
    blender = find_blender(args.blender_exe)
    payload = Path(__file__).resolve().parent / "blendscene_analyze.py"
    outfile = args.out or ROOT / ".run" / "blend_analysis.json"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    cmd = [blender, "--background", str(blend), "--python", str(payload), "--", str(outfile)]
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def cmd_spawn(args) -> int:
    need_module("spawn", "mujoco", "numpy")
    import blendscene_spawn
    blendscene_spawn.main([str(args.scene_dir.resolve()), *args.extra])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="blend -> runnable scene (full pipeline)")
    p.add_argument("blend", type=Path)
    p.add_argument("-o", "--out", type=Path, default=None,
                   help="scene directory (default: assets/<blend-stem>_scene)")
    p.add_argument("--blender", dest="blender_exe", default=None, help="blender executable")
    p.add_argument("--unit-scale", type=float, default=1.0)
    p.add_argument("--collision-min-size", type=float, default=1.5)
    p.add_argument("--max-collision", type=int, default=350)
    p.add_argument("--skip-visual", action="store_true")
    p.add_argument("--no-textures", action="store_true")
    p.add_argument("--no-export", action="store_true",
                   help="reuse the existing manifest.json (skip Blender)")
    p.add_argument("--skip-pack", action="store_true", help="meshes are already packed MSH")
    p.add_argument("--respawn", action="store_true",
                   help="recompute spawn.json (invalidates the pose asserted in tests/engine_car.cpp)")
    p.add_argument("--spawn", default=None, metavar="X,Y[,Z]", help="pin the spawn point")
    p.add_argument("--goal", default=None, metavar="X,Y", help="pin the navigation goal")
    # spawn-search passthroughs (defaults live in blendscene_spawn.find_spawn)
    p.add_argument("--window", type=_floats, default=None, metavar="XMIN,YMIN,XMAX,YMAX")
    p.add_argument("--center", type=_floats, default=None, metavar="X,Y")
    p.add_argument("--spawn-inset", type=float, default=2.0)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--trials", type=int, default=6000)
    p.add_argument("--clearance", type=float, default=1.2)
    p.add_argument("--floor-z", type=float, default=0.0)
    p.add_argument("--drive", action="store_true", help="run the drive validation afterwards")
    p.add_argument("--render", action="store_true", help="run the render validation afterwards")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("analyze", help="scene statistics via Blender")
    p.add_argument("blend", type=Path)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--blender", dest="blender_exe", default=None)
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("spawn", help="recompute spawn.json (deliberate)")
    p.add_argument("scene_dir", type=Path)
    p.add_argument("extra", nargs=argparse.REMAINDER,
                   help="options passed through to blendscene_spawn (--force, --window, ...)")
    p.set_defaults(func=cmd_spawn)

    for name, mod, extra_help in (("run", "blendscene_run", "interactive WASD viewer"),
                                  ("drive", "blendscene_drive", "headless drive check"),
                                  ("render", "blendscene_render", "offscreen renders")):
        p = sub.add_parser(name, help=extra_help)
        p.add_argument("scene", nargs="?", default=None,
                       help=f"scene xml (default: assets/car_scene/{SCENE_XML})")
        p.add_argument("extra", nargs=argparse.REMAINDER)
        p.set_defaults(mod=mod)

    args = parser.parse_args()
    if hasattr(args, "func"):
        return args.func(args)
    import importlib
    mod = importlib.import_module(args.mod)
    scene = [str(args.scene)] if args.scene else []
    return mod.main(scene + args.extra)


if __name__ == "__main__":
    sys.exit(main())
