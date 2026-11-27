# Blender scene converter (blendscene)

[中文](../../docs_cn/core/blendscene_cn.md) · [Docs](../README.md)

`tools/blendscene.py` converts any Blender `.blend` into a runnable MuJoCo car-navigation scene: textured visual meshes, structural collision hulls, and an embedded differential-drive car. The tracked `assets/car_scene` is one output of this tool, generated from the author's `0001.blend`; the pipeline itself is scene-agnostic.

## Requirements

- A Python with `mujoco` 3.3.1, `numpy`, and `Pillow`. The repository's `.car-venv` is one (`scripts/` layout on Windows, `bin/` on Linux).
- Blender 4.3.x, located by `--blender PATH`, the `BLENDER_EXE` environment variable, or `PATH`. Only the export and analyze stages need Blender; everything else runs without it.

## Quick start

```sh
.car-venv/Scripts/python tools/blendscene.py building.blend        # -> assets/building_scene/
.car-venv/Scripts/python tools/blendscene.py run                   # interactive WASD viewer
```

`build` runs the whole pipeline:

1. **Export** — headless Blender payload (`tools/blendscene_export.py`) duplicates visible meshes, bakes world transforms, joins objects per primary material into `meshes/vis_<material>.obj` with MTL sidecars and unpacked textures, and writes the largest structures as `collision/col_NNNN.obj`, plus `manifest.json`. Blender exits `0` even when its payload raises, so the orchestrator additionally requires a freshly written, parseable manifest.
2. **Pack** — `tools/blendscene_pack.py` converts OBJs to MuJoCo binary MSH in place, converts non-PNG `map_Kd` images to PNG (MuJoCo only loads PNG), and prunes maps MuJoCo never reads.
3. **Build** — `tools/blendscene_build.py` emits `scene.xml` from the manifest and MTLs, embedding the car, exported point lights, a safety floor, and the `eos_benchmark_car_navigation_v1` profile marker.
4. **Spawn** — on first build, `tools/blendscene_spawn.py` raycasts for an open spawn point plus the farthest open goal and rebuilds the XML with them.

Both Blender and MuJoCo are z-up right-handed; coordinates pass through unchanged. Floors must have thickness in the source model — zero-volume visual meshes fail MuJoCo compilation.

## Command reference

| Command | Purpose |
| --- | --- |
| `build <model.blend> [-o DIR]` | Full pipeline; default output `assets/<blend-stem>_scene` |
| `analyze <model.blend> [--out FILE]` | Scene statistics (units, bbox, materials) via Blender |
| `spawn <scene_dir> [--force]` | Recompute `spawn.json` deliberately |
| `run [SCENE]` | Interactive WASD viewer (default `assets/car_scene/scene.xml`) |
| `drive [SCENE]` | Headless scripted drive check; exits `1` when the car looks flipped |
| `render [SCENE] [--recolor]` | Offscreen renders + contact report; `--recolor` diagnoses dark renders |

Frequently used `build` flags: `--unit-scale`, `--collision-min-size`, `--max-collision` (export tuning), `--spawn X,Y[,Z]` and `--goal X,Y` (pin the endpoints instead of raycasting), `--respawn` (recompute the spawn), `--no-export` (reuse the existing manifest), `--skip-pack`, `--drive`/`--render` (validate after building), `--blender PATH`. Spawn-search tuning (`--window`, `--center`, `--spawn-inset`, `--seed`, `--trials`, `--clearance`, `--floor-z`) defaults to the manifest bbox.

## Scene directory layout

```
assets/<name>_scene/
  scene.xml       # generated MJCF; deterministic given the inputs below
  manifest.json   # export summary: bbox, visual groups, collision list, lights, materials
  spawn.json      # {"pos": [x, y, z], "goal": [x, y]}
  meshes/         # binary MSH + MTL sidecars + PNG textures  (not in git)
  collision/      # binary MSH hulls                           (not in git)
```

The heavy `meshes/` and `collision/` trees are gitignored (`/assets/*_scene/meshes/`, `/assets/*_scene/collision/`) and ship as release asset packs instead; see the next section. Regenerating with unchanged inputs reproduces `scene.xml` byte-identically; `<mujoco model>` derives from the directory name, so do not rename an existing scene directory.

## Distributed asset packs

`tools/blendscene_assets.py` mirrors the RoboCasa source-fetch pattern for scenes whose meshes are not tracked:

```sh
python tools/blendscene_assets.py check       # are the meshes present?
python tools/blendscene_assets.py download    # fetch + sha256-verify + extract
python tools/blendscene_assets.py pack        # rebuild dist/<zip> after a re-export
```

Per-scene pins (release tag, archive name, URL, sha256) live in the `SCENES` registry at the top of the script; `CAR_SCENE_ASSETS_URL` and `CAR_SCENE_ASSETS_SHA256` override them. Fresh clones run `download` before `ctest -R engine-car-test`, which otherwise fails fast with the same instruction. After a re-export: bump the scene's version, `pack`, upload the zip to the release tag, and paste the printed sha256. Do not re-pack an already-published version — zip metadata changes the digest.

## Regeneration and spawn stability

`spawn.json` is written only by the spawn stage and an existing file is never overwritten without `--force`/`--respawn`. This is deliberate: `tests/engine_car.cpp` asserts the spawn pose baked into the tracked scene, and respawning produces a different (still valid) spawn that breaks that assertion until the test is updated. Re-export with the same Blender version used for the current generation; a reordered `manifest.json` diff is a red flag, not noise.

## Engine contract

The car geometry (wheel radius `0.08` m, track `0.36` m, max wheel speed `15` rad/s) and every engine-facing name (`car`, `car_root`, `wheel_{left,right}_spin`, `{left,right}_wheel_motor`, `robot_camera`, `navigation_goal`, the profile marker) are hardcoded in `tools/blendscene_build.py` and must match the constants in `src/mujoco/engine.cpp` (`kCarWheelRadius` and friends). Changing them is a synchronized edit across the builder, the engine, and the tests; the interactive runner instead derives wheel geometry from the loaded model.

## Verification

- `ctest -R engine-car-test` — C++ profile, spawn pose, and drive/navigation invariants (requires downloaded meshes).
- `.car-venv/Scripts/python tools/blendscene.py drive` — headless motion check.
- `.car-venv/Scripts/python tools/blendscene.py render` — offscreen renders land in `.run/`.
- Rebuild a tracked scene from its blend and require a clean `git status` — the round trip must not touch tracked files.
